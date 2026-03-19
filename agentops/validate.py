#!/usr/bin/env python3
"""DevAgent validation script — enforces workflow and bookkeeping consistency.

Usage:
    python agentops/validate.py check    # Full validation
    python agentops/validate.py pre-qa   # QA gate (block if errors)
    python agentops/validate.py status   # Quick human-readable summary

Exit codes: 0=clean, 1=warnings, 2=errors
"""

import os
import re
import subprocess
import sys
import yaml  # PyYAML not needed — we use a minimal parser below


# ---------------------------------------------------------------------------
# Minimal YAML helpers (stdlib only, no PyYAML dependency)
# ---------------------------------------------------------------------------

def _parse_yaml_value(raw: str) -> str:
    """Strip quotes and whitespace from a YAML scalar value."""
    v = raw.strip()
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
    return v


def parse_project_yaml(path: str) -> dict:
    """Parse project.yaml into a dict with goal, status, version, current_milestone, milestones."""
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    result = {"milestones": []}
    current_milestone = None

    for line in lines:
        stripped = line.rstrip("\n")

        # Top-level scalars
        for key in ("goal", "status", "version", "current_milestone", "retry_limit"):
            if stripped.startswith(f"{key}:") and not stripped.startswith("  "):
                result[key] = _parse_yaml_value(stripped.split(":", 1)[1])
                break

        # Milestone list entries
        if re.match(r"^\s{2}- id:\s*", stripped):
            current_milestone = {"id": _parse_yaml_value(stripped.split(":", 1)[1])}
            result["milestones"].append(current_milestone)
        elif current_milestone is not None and re.match(r"^\s{4}\w+:", stripped):
            key, val = stripped.strip().split(":", 1)
            current_milestone[key.strip()] = _parse_yaml_value(val)
        elif current_milestone is not None and not stripped.startswith("  "):
            current_milestone = None

    return result


def parse_tasks_yaml(path: str) -> list[dict]:
    """Parse tasks.yaml and return list of task dicts with at least id, name, status."""
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    tasks = []
    # Split on task entries: lines starting with "  - id:"
    chunks = re.split(r"(?m)^  - id:", content)
    for chunk in chunks[1:]:  # skip preamble before first task
        task = {"id": _parse_yaml_value(chunk.split("\n")[0])}
        for line in chunk.split("\n")[1:]:
            # Match top-level task fields (4-space indent)
            m = re.match(r"^    (\w+):\s*(.*)", line)
            if m:
                key, val = m.group(1), m.group(2).strip()
                if val and not val.startswith("|"):
                    task[key] = _parse_yaml_value(val)
        tasks.append(task)
    return tasks


def read_progress_log(path: str) -> list[str]:
    """Read progress.log lines, return empty list if missing."""
    if not os.path.isfile(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def git_branch_exists(branch: str) -> bool:
    """Check if a git branch exists locally."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{branch}"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def is_git_repo() -> bool:
    """Check if current directory is inside a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def list_worktrees() -> list[str]:
    """List directories in .git-worktrees/."""
    wt_dir = ".git-worktrees"
    if not os.path.isdir(wt_dir):
        return []
    return [
        d for d in os.listdir(wt_dir)
        if os.path.isdir(os.path.join(wt_dir, d))
    ]


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------

class ValidationResult:
    def __init__(self, mode: str):
        self.mode = mode
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: dict = {}
        self.checks_passed = 0

    def error(self, check_id: str, msg: str):
        self.errors.append(f"  [{check_id}] {msg}")

    def warning(self, check_id: str, msg: str):
        self.warnings.append(f"  [{check_id}] {msg}")

    def ok(self):
        self.checks_passed += 1

    @property
    def exit_code(self) -> int:
        if self.errors:
            return 2
        if self.warnings:
            return 1
        return 0

    def __str__(self) -> str:
        milestone_name = self.info.get("milestone", "unknown")
        milestone_status = self.info.get("milestone_status", "unknown")
        header = f"=== DevAgent Validation ({self.mode}) ==="

        if self.mode == "status":
            return self._format_status()

        parts = [header]
        if milestone_name != "unknown":
            parts.append(f"Milestone: {milestone_name} (status: {milestone_status})")
        parts.append("")

        if self.errors:
            parts.append("ERRORS:")
            parts.extend(self.errors)
            parts.append("")
        if self.warnings:
            parts.append("WARNINGS:")
            parts.extend(self.warnings)
            parts.append("")

        summary_parts = []
        if self.checks_passed:
            summary_parts.append(f"{self.checks_passed} checks passed")
        if self.errors:
            summary_parts.append(f"{len(self.errors)} errors")
        if self.warnings:
            summary_parts.append(f"{len(self.warnings)} warnings")

        if not self.errors and not self.warnings:
            if self.mode == "pre-qa":
                task_count = self.info.get("task_count", 0)
                parts.append(f"OK: all {task_count} tasks complete, progress.log consistent, branch exists")
                parts.append("Ready for QA.")
            else:
                parts.append(f"OK: {', '.join(summary_parts)}")
        else:
            parts.append(f"RESULT: {', '.join(summary_parts)}")

        return "\n".join(parts)

    def _format_status(self) -> str:
        parts = ["=== DevAgent Status (quick) ==="]
        project = self.info.get("project", {})
        parts.append(f"Goal: {project.get('goal', 'unknown')}")
        parts.append(f"Status: {project.get('status', 'unknown')} | Version: {project.get('version', '0.0.0')}")
        parts.append("")

        milestones = self.info.get("milestones_summary", [])
        if milestones:
            parts.append("Milestones:")
            for m in milestones:
                parts.append(f"  {m['id']} {m['name']}: {m.get('status', 'unknown')}")
        parts.append("")

        current = self.info.get("current_tasks", [])
        if current:
            parts.append(f"Current milestone tasks:")
            for t in current:
                parts.append(f"  {t['id']} {t.get('name', '?')}: {t.get('status', 'no status')}")

        if self.warnings:
            parts.append("")
            parts.append("WARNINGS:")
            parts.extend(self.warnings)

        return "\n".join(parts)


def find_current_milestone(project: dict) -> dict | None:
    """Find the current milestone dict from project data."""
    current_id = project.get("current_milestone", "")
    for m in project.get("milestones", []):
        if m.get("id") == current_id:
            return m
    return None


def milestone_dir(milestone: dict) -> str:
    """Compute milestone directory path."""
    mid = milestone.get("id", "")
    name = milestone.get("name", "")
    return os.path.join("agentops", "milestones", f"{mid}-{name}")


def check_task_status_fields(tasks: list[dict], result: ValidationResult):
    """Check that every task has a status field."""
    for t in tasks:
        if "status" not in t:
            result.error("task_status", f"{t['id']}: missing status field in tasks.yaml")
        else:
            result.ok()


def check_all_tasks_complete(tasks: list[dict], result: ValidationResult):
    """Check that all tasks have status: complete (pre-qa gate)."""
    incomplete = [t for t in tasks if t.get("status") != "complete"]
    if incomplete:
        for t in incomplete:
            result.error("task_complete", f"{t['id']}: status={t.get('status', 'missing')} (must be complete for QA)")
    else:
        result.ok()


def check_tasks_stuck(tasks: list[dict], log_lines: list[str], result: ValidationResult):
    """Check for in-progress tasks without a started log entry."""
    for t in tasks:
        if t.get("status") == "in-progress":
            tid = t["id"]
            has_started = any(f"[DEV:{tid}] started" in line for line in log_lines)
            if not has_started:
                result.warning("task_stuck", f"{tid}: status=in-progress but no [DEV:{tid}] started in progress.log")
            else:
                result.ok()


def check_progress_sync(tasks: list[dict], log_lines: list[str], result: ValidationResult):
    """Check that complete tasks have finished entries in progress.log."""
    for t in tasks:
        if t.get("status") == "complete":
            tid = t["id"]
            has_finished = any(f"[DEV:{tid}] finished" in line for line in log_lines)
            # Also check for reconciliation entries
            has_reconciliation = any(f"reconciliation: {tid}" in line for line in log_lines)
            if not has_finished and not has_reconciliation:
                result.warning("progress_sync", f"{tid}: status=complete but no [DEV:{tid}] finished entry in progress.log")
            else:
                result.ok()


def check_milestone_drift(milestone: dict, tasks: list[dict], log_lines: list[str], result: ValidationResult):
    """Check if milestone status matches evidence."""
    yaml_status = milestone.get("status", "unknown")

    # Infer status from evidence
    has_tasks = len(tasks) > 0
    all_complete = has_tasks and all(t.get("status") == "complete" for t in tasks)
    has_qa_pass = any("[QA] finished: PASS" in line for line in log_lines)
    has_user_approved = any("user approved" in line for line in log_lines)
    any_in_progress = any(t.get("status") in ("in-progress", "in-review") for t in tasks)

    if has_user_approved:
        inferred = "complete"
    elif has_qa_pass:
        inferred = "feedback"
    elif all_complete:
        inferred = "ready-for-qa"
    elif any_in_progress:
        inferred = "in-progress"
    elif has_tasks:
        inferred = "in-progress"
    else:
        inferred = yaml_status  # can't infer without tasks

    if inferred != yaml_status and inferred != "ready-for-qa":
        # ready-for-qa is a transient state, not in project.yaml
        # only warn if there's a real mismatch
        if not (inferred == "ready-for-qa" and yaml_status == "in-progress"):
            result.warning("milestone_drift", f"project.yaml says '{yaml_status}' but evidence suggests '{inferred}'")
            return

    result.ok()


def check_branch_exists(milestone: dict, result: ValidationResult):
    """Check that the milestone branch exists in git."""
    if not is_git_repo():
        result.warning("branch", "not a git repo — skipping branch check")
        return

    branch = milestone.get("branch", "")
    if not branch:
        result.error("branch", "milestone has no branch field in project.yaml")
        return

    if git_branch_exists(branch):
        result.ok()
    else:
        result.error("branch", f"milestone branch '{branch}' does not exist")


def check_stale_worktrees(tasks: list[dict], result: ValidationResult):
    """Check for orphaned worktree directories."""
    worktrees = list_worktrees()
    if not worktrees:
        result.ok()
        return

    in_progress_ids = {t["id"] for t in tasks if t.get("status") in ("in-progress", "in-review")}
    has_stale = False

    for wt in worktrees:
        # Skip POC worktrees
        if wt.startswith("poc-"):
            continue
        # Extract task id from worktree name (e.g., m06-t01 -> t01)
        parts = wt.split("-")
        task_id = parts[-1] if len(parts) >= 2 else wt
        if task_id not in in_progress_ids:
            result.warning("stale_worktree", f".git-worktrees/{wt}/ exists but {task_id} is not in-progress")
            has_stale = True

    if not has_stale:
        result.ok()


# ---------------------------------------------------------------------------
# Main validation runners
# ---------------------------------------------------------------------------

def run_check(project: dict, milestone: dict | None) -> ValidationResult:
    """Full validation — all checks."""
    result = ValidationResult("check")

    if milestone is None:
        result.info["milestone"] = "none"
        result.info["milestone_status"] = "no active milestone"
        return result

    mdir = milestone_dir(milestone)
    result.info["milestone"] = f"{milestone.get('id')}-{milestone.get('name')}"
    result.info["milestone_status"] = milestone.get("status", "unknown")

    tasks_path = os.path.join(mdir, "tasks.yaml")
    log_path = os.path.join(mdir, "progress.log")

    tasks = parse_tasks_yaml(tasks_path)
    log_lines = read_progress_log(log_path)

    if not tasks and milestone.get("status") in ("in-progress", "qa", "feedback"):
        result.warning("no_tasks", "milestone is active but no tasks.yaml found")

    check_task_status_fields(tasks, result)
    check_tasks_stuck(tasks, log_lines, result)
    check_progress_sync(tasks, log_lines, result)
    check_milestone_drift(milestone, tasks, log_lines, result)
    check_stale_worktrees(tasks, result)

    return result


def run_pre_qa(project: dict, milestone: dict | None) -> ValidationResult:
    """QA gate — must pass before dispatching QA."""
    result = ValidationResult("pre-qa")

    if milestone is None:
        result.error("no_milestone", "no active milestone found")
        return result

    mdir = milestone_dir(milestone)
    result.info["milestone"] = f"{milestone.get('id')}-{milestone.get('name')}"
    result.info["milestone_status"] = milestone.get("status", "unknown")

    tasks_path = os.path.join(mdir, "tasks.yaml")
    log_path = os.path.join(mdir, "progress.log")

    tasks = parse_tasks_yaml(tasks_path)
    log_lines = read_progress_log(log_path)

    if not tasks:
        result.error("no_tasks", "no tasks found in tasks.yaml — cannot proceed to QA")
        return result

    result.info["task_count"] = len(tasks)

    check_task_status_fields(tasks, result)
    check_all_tasks_complete(tasks, result)
    check_progress_sync(tasks, log_lines, result)
    check_branch_exists(milestone, result)

    return result


def run_status(project: dict, milestone: dict | None) -> ValidationResult:
    """Quick status summary for humans."""
    result = ValidationResult("status")
    result.info["project"] = project

    result.info["milestones_summary"] = project.get("milestones", [])

    if milestone:
        mdir = milestone_dir(milestone)
        tasks_path = os.path.join(mdir, "tasks.yaml")
        tasks = parse_tasks_yaml(tasks_path)
        result.info["current_tasks"] = tasks

        # Add drift warning if applicable
        log_path = os.path.join(mdir, "progress.log")
        log_lines = read_progress_log(log_path)
        check_milestone_drift(milestone, tasks, log_lines, result)

    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("check", "pre-qa", "status"):
        print(__doc__.strip())
        sys.exit(2)

    mode = sys.argv[1]

    project_path = os.path.join("agentops", "project.yaml")
    if not os.path.isfile(project_path):
        print(f"ERROR: {project_path} not found — not a devagent project.")
        sys.exit(2)

    try:
        project = parse_project_yaml(project_path)
    except Exception as e:
        print(f"ERROR: failed to parse {project_path}: {e}")
        sys.exit(2)

    milestone = find_current_milestone(project)

    if mode == "check":
        result = run_check(project, milestone)
    elif mode == "pre-qa":
        result = run_pre_qa(project, milestone)
    elif mode == "status":
        result = run_status(project, milestone)
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(2)

    print(result)
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
