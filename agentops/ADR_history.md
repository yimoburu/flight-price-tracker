# Architecture Decision Records

## ADR-001: Sync Amadeus SDK Integration via Starlette Threadpool
**Status:** [active]
**Scope:** m01-core-search — all route handlers calling the Amadeus Python SDK
**Decision:** Declare FastAPI route handlers that call the Amadeus SDK as `def` (not
`async def`). FastAPI/Starlette automatically offloads `def` path operation functions
to a managed thread pool executor, preventing the synchronous `urllib.request.urlopen`
calls inside the SDK from blocking the async event loop.
**Alternatives:**
- `asyncio.get_running_loop().run_in_executor()` inside `async def` handlers: viable
  but more verbose and provides no additional benefit for this use case.
- `anyio.to_thread.run_sync()`: equally valid but adds explicit async machinery where
  the simpler `def` pattern suffices.
- Replace SDK with an async HTTP client (e.g., `httpx.AsyncClient`): would require
  reimplementing Amadeus OAuth2 token management and all endpoint wrappers; not
  justified given the SDK is actively maintained and well-tested.
**Rationale:** The `def` handler pattern is explicitly recommended by FastAPI
documentation for blocking third-party libraries. It is the simplest, most idiomatic
approach with zero extra boilerplate. The Starlette threadpool default (40 threads)
is more than sufficient for this project's scale.
**POC evidence:** poc/amadeus-sdk-async.md — VIABLE — confirmed SDK uses urllib
synchronously; `def` route handlers confirmed to run in Starlette threadpool per
FastAPI documentation.

## ADR-002: Two-Step Amadeus Search (flight_dates then flight_offers_search)
**Status:** [active]
**Scope:** m01-core-search — FlightService.search_flights() implementation
**Decision:** For date-range searches, call `flight_dates.get()` once to retrieve the
cheapest-date calendar for the origin→destination pair, filter the returned dates to
the user's requested window, take the top-5 cheapest, then call
`flight_offers_search.get()` once per selected date (max 5 calls) to get detailed
flight offers. Maximum Amadeus API calls per search: 6 (1 calendar + 5 offers).
**Alternatives:**
- Call `flight_offers_search.get()` once per day in the date range: would require
  up to 30 API calls for a 30-day window, quickly exhausting the free-tier quota
  (2000 calls/month for test environment).
- Use only `flight_dates.get()` for results: cheapest dates only returns price
  summaries without segment details (airline, times, duration) which are required
  by the PRD.
**Rationale:** The `flight_dates` endpoint is purpose-built for multi-date price
discovery in a single call, returning a calendar of cheapest prices. Using it as
the first step with top-5 selection provides a good balance of coverage and API
efficiency. The `links.flightOffers` field in each date result provides a direct
URL to the corresponding offers search, confirming Amadeus intends this two-step
workflow.
**POC evidence:** poc/amadeus-date-range-behavior.md — VIABLE — flight_dates returns
multi-date calendar in one call; date filtering done client-side.

## ADR-003: cachetools TTLCache for In-Memory Search Caching
**Status:** [active]
**Scope:** m01-core-search — search result caching
**Decision:** Use `cachetools.TTLCache` (maxsize=128, ttl=900 seconds / 15 minutes)
to cache identical search results in memory. Protect with `threading.Lock()` since
the cache is shared across multiple threadpool threads (from `def` route handlers).
Cache key is a hashable tuple of all normalized search parameters.
**Alternatives:**
- Redis: overkill for a single-process development app with no persistence requirement;
  adds operational dependency.
- `functools.lru_cache` on the service function: does not support TTL expiry, which
  is required (free-tier Amadeus quota and 15-min freshness requirement in PRD).
- No caching: would exhaust the Amadeus free-tier quota (2000 test calls/month) during
  normal development use.
**Rationale:** `cachetools` is a minimal, pure-Python library with no external
dependencies. TTLCache satisfies the 15-minute freshness requirement. Threading.Lock
wrapping is straightforward. The 128-entry maxsize handles typical development usage
patterns. No persistence is needed since cache warming is fast (single API call).

## ADR-004: Vite Dev Proxy for Frontend-Backend Communication
**Status:** [active]
**Scope:** m01-core-search — frontend development environment
**Decision:** Configure Vite's `server.proxy` to forward all `/api` requests to
`http://localhost:8000` in development. In production (if ever deployed), the FastAPI
backend's `CORSMiddleware` handles cross-origin requests from the frontend.
**Alternatives:**
- Configure CORS only (no proxy): requires the frontend to know the backend URL and
  CORS to be correctly configured; adds complexity in development.
- Use a single-server setup (FastAPI serves static frontend files): requires a build
  step on every frontend change; breaks hot module replacement (HMR).
**Rationale:** The Vite proxy is the standard React development pattern and eliminates
CORS configuration during development entirely. Both CORS middleware (backend) and
proxy (frontend dev) are configured so the app works in both modes without code
changes. The Vite proxy is a zero-cost development convenience — it does not affect
the production build.

## ADR-005: SQLAlchemy Synchronous Engine with Per-Thread Session Pattern
**Status:** [active]
**Scope:** m02-tracking-alerts — database layer
**Decision:** Use SQLAlchemy's synchronous `create_engine` + `sessionmaker` (not
`AsyncSession`). FastAPI route handlers use `Depends(get_db)` which yields a new
`Session` per request. The APScheduler background jobs call `SessionLocal()` directly,
creating and closing a fresh session per job invocation. `check_same_thread=False` is
set for the SQLite engine to allow safe access from multiple threads (FastAPI threadpool
+ APScheduler worker threads).
**Alternatives:**
- `AsyncSession` with `create_async_engine`: would require converting route handlers to
  `async def` and using `await` for all DB operations. Incompatible with the synchronous
  Amadeus SDK pattern (ADR-001) and adds complexity without benefit at this scale.
- Scoped session registry (`scoped_session`): viable but unnecessary complexity — jobs
  are short-lived and sequential within one worker, so fresh-session-per-invocation is
  simpler and equivalent.
**Rationale:** Synchronous SQLAlchemy is consistent with ADR-001's established pattern
(sync I/O in threads). Fresh sessions per invocation avoid session sharing bugs across
thread boundaries. `check_same_thread=False` is the standard SQLite multi-thread option
and is safe when sessions are not shared across threads.

## ADR-006: APScheduler BackgroundScheduler with Delayed First Run
**Status:** [active]
**Scope:** m02-tracking-alerts — scheduler lifecycle
**Decision:** Use APScheduler's `BackgroundScheduler` (thread-based) with an
`IntervalTrigger`. The first job execution is delayed by one full interval (no
immediate first run on startup).
**Alternatives:**
- `AsyncIOScheduler`: incompatible with synchronous SQLAlchemy sessions and synchronous
  Amadeus SDK calls inside job functions (would require running them in a thread executor
  anyway, losing the benefit of async scheduling).
- Immediate first run (`next_run_time=datetime.now()`): more user-friendly but spikes
  Amadeus API calls on every server restart, which is especially problematic during
  development with `--reload`. Rejected to conserve free-tier API quota.
- `ProcessPoolScheduler`: not needed; jobs are I/O-bound (network + SQLite), not CPU-bound.
**Rationale:** `BackgroundScheduler` runs jobs in daemon threads compatible with the
existing sync patterns. The delayed first run protects the Amadeus free-tier quota
during iterative development.

## ADR-007: BrowserRouter (HTML5 History API) for React Router
**Status:** [active]
**Scope:** m02-tracking-alerts — frontend routing
**Decision:** Use `BrowserRouter` from `react-router-dom` v6 for client-side routing.
Two routes: `/` (HomePage) and `/tracked` (TrackedSearchesPage).
**Alternatives:**
- `HashRouter`: produces `/#/tracked` URLs. Functional without any server config but
  aesthetically inferior and non-standard. Rejected in favor of clean URLs.
- No routing (manual conditional rendering in App.tsx): would require reinventing
  URL-synced navigation. `react-router-dom` is PRD-specified.
**Rationale:** Vite's dev server returns `index.html` for all non-asset requests by
default (via the `index.html` fallback), so deep-links like `/tracked` load correctly
without extra server configuration. `BrowserRouter` is the standard choice for
single-page apps and produces clean, bookmarkable URLs.
