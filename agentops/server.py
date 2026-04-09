#!/usr/bin/env python3
"""DevAgent status dashboard server.

Usage:
    python agentops/server.py [--port PORT]

Serves the status dashboard HTML and provides a REST API for reading project files.
Singleton: only one instance per project (uses .status-server.pid lockfile).
Auto-selects port starting from 50101 if the default is occupied.
"""

import json
import os
import signal
import socket
import sys
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = os.getcwd()
AGENTOPS_DIR = os.path.join(PROJECT_ROOT, "agentops")
PID_FILE = os.path.join(AGENTOPS_DIR, ".status-server.pid")
DEFAULT_PORT = 50101
MAX_PORT_TRIES = 20
POLL_CACHE_TTL = 1  # seconds

# Cache for tree endpoint
_tree_cache = {"data": None, "time": 0}


def is_safe_path(path: str) -> bool:
    """Prevent path traversal — resolved path must be under PROJECT_ROOT."""
    try:
        resolved = os.path.realpath(os.path.join(PROJECT_ROOT, path))
        return resolved.startswith(os.path.realpath(PROJECT_ROOT))
    except (ValueError, OSError):
        return False


def scan_tree(root: str, prefix: str = "") -> list:
    """Recursively scan directory into a JSON-serializable tree."""
    entries = []
    try:
        items = sorted(os.listdir(root))
    except PermissionError:
        return entries

    # Skip heavy/irrelevant directories
    skip_dirs = {
        "node_modules", ".git", ".git-worktrees", "__pycache__",
        ".next", ".nuxt", "dist", "build", ".venv", "venv",
        ".playwright-mcp", ".turbo", ".ruff_cache", "target",
    }

    for name in items:
        if name.startswith(".") and name not in (".gitignore",):
            # Skip hidden files except .gitignore
            if os.path.isdir(os.path.join(root, name)):
                if name in (".git", ".git-worktrees", ".playwright-mcp"):
                    continue
            else:
                if name == ".status-server.pid":
                    continue

        full = os.path.join(root, name)
        rel = os.path.join(prefix, name) if prefix else name

        if os.path.isdir(full):
            if name in skip_dirs:
                continue
            children = scan_tree(full, rel)
            entries.append({"name": name, "path": rel, "type": "dir", "children": children})
        else:
            size = 0
            try:
                size = os.path.getsize(full)
            except OSError:
                pass
            entries.append({"name": name, "path": rel, "type": "file", "size": size})

    return entries


def parse_yaml_simple(path: str) -> dict:
    """Minimal YAML parser for project.yaml — handles our specific schema."""
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    import re
    result = {"milestones": []}
    current_milestone = None

    for line in lines:
        stripped = line.rstrip("\n")
        for key in ("goal", "status", "version", "current_milestone", "retry_limit"):
            if stripped.startswith(f"{key}:") and not stripped.startswith("  "):
                val = stripped.split(":", 1)[1].strip().strip("'\"")
                result[key] = val
                break
        if re.match(r"^\s{2}- id:\s*", stripped):
            current_milestone = {"id": stripped.split(":", 1)[1].strip().strip("'\"") }
            result["milestones"].append(current_milestone)
        elif current_milestone is not None and re.match(r"^\s{4}\w+:", stripped):
            key, val = stripped.strip().split(":", 1)
            current_milestone[key.strip()] = val.strip().strip("'\"")
        elif current_milestone is not None and not stripped.startswith("  "):
            current_milestone = None

    return result


def parse_tasks_yaml(path: str) -> list:
    """Parse tasks.yaml into a list of task dicts."""
    if not os.path.isfile(path):
        return []
    import re
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    tasks = []
    chunks = re.split(r"(?m)^  - id:", content)
    for chunk in chunks[1:]:
        task = {"id": chunk.split("\n")[0].strip().strip("'\"") }
        for line in chunk.split("\n")[1:]:
            m = re.match(r"^    (\w+):\s*(.*)", line)
            if m:
                key, val = m.group(1), m.group(2).strip()
                if val and not val.startswith("|"):
                    task[key] = val.strip("'\"")
        tasks.append(task)
    return tasks


class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler for the status dashboard."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self._serve_html()
        elif path == "/api/project":
            self._api_project()
        elif path == "/api/tree":
            self._api_tree()
        elif path == "/api/file":
            qs = parse_qs(parsed.query)
            file_path = qs.get("path", [None])[0]
            self._api_file(file_path)
        elif path == "/api/milestone":
            qs = parse_qs(parsed.query)
            milestone_id = qs.get("id", [None])[0]
            self._api_milestone(milestone_id)
        else:
            self.send_error(404)

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text, content_type="text/plain", status=200):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _serve_html(self):
        html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status.html")
        # Also check agentops/ dir (when deployed to target project)
        if not os.path.isfile(html_path):
            html_path = os.path.join(AGENTOPS_DIR, "status.html")
        if not os.path.isfile(html_path):
            self.send_error(404, "status.html not found")
            return
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        self._send_text(html, "text/html")

    def _api_project(self):
        project = parse_yaml_simple(os.path.join(AGENTOPS_DIR, "project.yaml"))
        if not project:
            self._send_json({"error": "project.yaml not found"}, 404)
            return

        # Include project root so probes can identify which project this server serves
        project["_project_root"] = os.path.realpath(PROJECT_ROOT)

        # Enrich milestones with task counts
        for m in project.get("milestones", []):
            mdir = os.path.join(AGENTOPS_DIR, "milestones", f"{m['id']}-{m.get('name', '')}")
            tasks_path = os.path.join(mdir, "tasks.yaml")
            tasks = parse_tasks_yaml(tasks_path)
            total = len(tasks)
            complete = sum(1 for t in tasks if t.get("status") == "complete")
            m["task_total"] = total
            m["task_complete"] = complete

        self._send_json(project)

    def _api_tree(self):
        now = time.time()
        if _tree_cache["data"] and (now - _tree_cache["time"]) < POLL_CACHE_TTL:
            self._send_json(_tree_cache["data"])
            return
        tree = scan_tree(PROJECT_ROOT)
        _tree_cache["data"] = tree
        _tree_cache["time"] = now
        self._send_json(tree)

    def _api_file(self, file_path: str | None):
        if not file_path:
            self._send_json({"error": "path parameter required"}, 400)
            return
        if not is_safe_path(file_path):
            self._send_json({"error": "invalid path"}, 403)
            return

        full_path = os.path.join(PROJECT_ROOT, file_path)
        if not os.path.isfile(full_path):
            self._send_json({"error": "file not found"}, 404)
            return

        # Check if binary
        ext = os.path.splitext(file_path)[1].lower()
        image_exts = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico"}

        if ext in image_exts:
            # Serve binary image
            mime = {
                ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                ".gif": "image/gif", ".svg": "image/svg+xml", ".webp": "image/webp",
                ".ico": "image/x-icon",
            }.get(ext, "application/octet-stream")
            try:
                with open(full_path, "rb") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", len(data))
                self.end_headers()
                self.wfile.write(data)
            except Exception:
                self._send_json({"error": "failed to read file"}, 500)
            return

        # Text file
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(512_000)  # 512KB limit
        except Exception:
            self._send_json({"error": "failed to read file"}, 500)
            return

        self._send_json({"path": file_path, "content": content, "size": os.path.getsize(full_path)})

    def _api_milestone(self, milestone_id: str | None):
        if not milestone_id:
            self._send_json({"error": "id parameter required"}, 400)
            return

        project = parse_yaml_simple(os.path.join(AGENTOPS_DIR, "project.yaml"))
        milestone = None
        for m in project.get("milestones", []):
            if m.get("id") == milestone_id:
                milestone = m
                break

        if not milestone:
            self._send_json({"error": f"milestone {milestone_id} not found"}, 404)
            return

        mdir = os.path.join(AGENTOPS_DIR, "milestones", f"{milestone['id']}-{milestone.get('name', '')}")

        # Tasks
        tasks = parse_tasks_yaml(os.path.join(mdir, "tasks.yaml"))

        # Progress log
        log_path = os.path.join(mdir, "progress.log")
        log_lines = []
        if os.path.isfile(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                log_lines = [l.strip() for l in f if l.strip()]

        # Markdown files
        docs = {}
        for name in ("prd.md", "design.md", "feedback.md", "release_notes.md"):
            doc_path = os.path.join(mdir, name)
            if os.path.isfile(doc_path):
                with open(doc_path, "r", encoding="utf-8", errors="replace") as f:
                    docs[name] = f.read()

        # Research files
        research = []
        research_dir = os.path.join(mdir, "research")
        if os.path.isdir(research_dir):
            for fname in sorted(os.listdir(research_dir)):
                if fname.endswith(".md"):
                    fpath = os.path.join(research_dir, fname)
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        research.append({"name": fname, "content": f.read()})

        # POC files
        pocs = []
        poc_dir = os.path.join(mdir, "poc")
        if os.path.isdir(poc_dir):
            for fname in sorted(os.listdir(poc_dir)):
                if fname.endswith(".md"):
                    fpath = os.path.join(poc_dir, fname)
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        pocs.append({"name": fname, "content": f.read()})

        result = {
            "milestone": milestone,
            "tasks": tasks,
            "progress_log": log_lines,
            "docs": docs,
            "research": research,
            "pocs": pocs,
        }
        self._send_json(result)


# ---------------------------------------------------------------------------
# Singleton management
# ---------------------------------------------------------------------------

def read_pid_file() -> tuple[int, int] | None:
    """Read PID file, return (pid, port) or None."""
    if not os.path.isfile(PID_FILE):
        return None
    try:
        with open(PID_FILE, "r") as f:
            data = json.load(f)
        return (data["pid"], data["port"])
    except (json.JSONDecodeError, KeyError, OSError):
        return None


def is_pid_alive(pid: int) -> bool:
    """Check if a process with the given PID is running."""
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError):
        return False


def write_pid_file(port: int):
    """Write PID file with current process info."""
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w") as f:
        json.dump({"pid": os.getpid(), "port": port}, f)


def remove_pid_file():
    """Remove PID file on shutdown."""
    try:
        os.remove(PID_FILE)
    except OSError:
        pass


def probe_devagent_server(port: int, must_match_root: bool = True) -> bool:
    """Check if a devagent status server for THIS project is running on the given port.

    If must_match_root is True, the server's _project_root must match our PROJECT_ROOT.
    This prevents accidentally claiming another project's server as our own.
    """
    import http.client
    try:
        conn = http.client.HTTPConnection("localhost", port, timeout=2)
        conn.request("GET", "/api/project")
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
        conn.close()
        if resp.status != 200:
            return False
        data = json.loads(body)
        if not isinstance(data, dict) or "milestones" not in data:
            return False
        if must_match_root:
            server_root = data.get("_project_root", "")
            return os.path.realpath(PROJECT_ROOT) == server_root
        return True
    except Exception:
        return False


def find_existing_server(start: int = DEFAULT_PORT, tries: int = MAX_PORT_TRIES) -> int | None:
    """Scan ports for an already-running devagent server (PID file may be missing)."""
    for offset in range(tries):
        port = start + offset
        # Quick check: is port in use?
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                # Port is free — not our server
                continue
            except OSError:
                pass
        # Port is occupied — probe it
        if probe_devagent_server(port):
            return port
    return None


def find_open_port(start: int = DEFAULT_PORT, tries: int = MAX_PORT_TRIES) -> int:
    """Find an available port starting from `start`."""
    for offset in range(tries):
        port = start + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No open port found in range {start}-{start + tries - 1}")


def main():
    # Check singleton — PID file first
    existing = read_pid_file()
    if existing:
        pid, port = existing
        if is_pid_alive(pid):
            print(f"Status server already running (PID {pid}) at http://localhost:{port}")
            sys.exit(0)
        else:
            remove_pid_file()

    # PID file missing or stale — probe ports for an orphaned server
    orphan_port = find_existing_server()
    if orphan_port:
        print(f"Status server already running at http://localhost:{orphan_port} (PID file was missing, recovered)")
        sys.exit(0)

    # Parse args
    port = DEFAULT_PORT
    if "--port" in sys.argv:
        idx = sys.argv.index("--port")
        if idx + 1 < len(sys.argv):
            port = int(sys.argv[idx + 1])

    # Find open port
    try:
        port = find_open_port(port)
    except RuntimeError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    # Register cleanup
    def cleanup(signum=None, frame=None):
        remove_pid_file()
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Write PID file
    write_pid_file(port)

    # Start server
    server = HTTPServer(("", port), DashboardHandler)
    print(f"DevAgent Status Dashboard: http://localhost:{port}")
    print(f"Serving project: {PROJECT_ROOT}")
    print("Press Ctrl+C to stop.")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        remove_pid_file()


if __name__ == "__main__":
    main()
