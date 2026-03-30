# PRD: m02 — Tracking & Alerts

## 1. Milestone Overview

This milestone adds persistent price tracking and email alerting on top of the core search built in m01. Users can save any search they have run, and the system will automatically re-run that search on a configurable schedule, record the best price found each time, and send an email when the price drops to or below a user-set threshold.

By the end of this milestone the app supports:
- Saving a search with an alert threshold and a recipient email address
- Viewing all tracked searches and their price history on a dedicated page
- Receiving an email notification when a tracked search's best price meets the alert condition
- Deleting a tracked search

No user authentication is added. Searches are identified by a UUID stored client-side in browser localStorage and sent with API requests. This keeps the scope small while delivering the tracking value.

---

## 2. User Stories

**Save a search for tracking**
As a traveler who has just run a search, I want to click "Track this search" so that the system re-checks prices automatically and notifies me when they drop.

**Set an alert threshold**
As a traveler saving a search, I want to enter an email address and a maximum price I am willing to pay (my alert threshold) so that I only receive an email when the fare is at or below that price.

**View tracked searches**
As a traveler, I want to see a list of all my tracked searches showing origin, destination, date range, my threshold, the current best price, and the date it was last checked so I can monitor them at a glance.

**View price history**
As a traveler, I want to click on a tracked search and see a price-over-time chart so I can understand whether prices are trending up or down.

**Delete a tracked search**
As a traveler, I want to delete a tracked search when I no longer care about the route so it stops generating checks and I stop receiving emails.

**Receive an email alert**
As a traveler, I want to receive an email when the best price for a tracked search drops to or below my threshold so I know to book immediately.

---

## 3. Acceptance Criteria

These are milestone-level criteria; all must pass before m02 is considered complete.

### AC-1: Save and retrieve tracked searches
- `POST /api/v1/tracked-searches` with valid body returns 201 and a JSON object containing an `id` (UUID), the saved parameters, `threshold_price`, and `alert_email`.
- `GET /api/v1/tracked-searches` with the `X-Client-ID` header returns 200 and a list of only the tracked searches belonging to that client ID.
- A tracked search persisted to SQLite survives a server restart.

### AC-2: Delete a tracked search
- `DELETE /api/v1/tracked-searches/{id}` returns 204 when the tracked search exists and belongs to the requesting client ID.
- After deletion, `GET /api/v1/tracked-searches` does not include that record.
- `DELETE` on an unknown ID returns 404.

### AC-3: Price history recording
- After the scheduler runs a check for a tracked search, a new row exists in the `price_snapshots` table containing the `tracked_search_id`, `checked_at` timestamp, and `best_price`.
- `GET /api/v1/tracked-searches/{id}/history` returns 200 with an array of `{checked_at, best_price}` entries sorted oldest-to-newest.
- If the Amadeus API returns no results for a scheduled check, no snapshot row is written and no alert is sent.

### AC-4: Scheduler execution
- On application startup the scheduler starts automatically and begins periodic checks within the configured interval.
- The scheduler interval is controlled by the environment variable `SCHEDULER_INTERVAL_MINUTES` (default: 60).
- Each enabled tracked search is checked no more than once per scheduler interval cycle.
- On application shutdown the scheduler stops cleanly without hanging.

### AC-5: Email alert delivery
- When a check finds a best price <= `threshold_price` AND the current best price is strictly less than the previous best price recorded for that search, an email is sent to `alert_email`.
- The email subject is: `Price alert: {origin} → {destination} now {currency}{best_price}`.
- The email body includes: origin, destination, date range, best price, currency, and the alert threshold.
- When a check finds a best price that does NOT meet the threshold, no email is sent.
- When there is no previous snapshot (first check ever), an email IS sent if the price is at or below the threshold.
- SMTP errors are caught, logged at ERROR level, and do not crash the scheduler or mark the tracked search as failed.

### AC-6: Frontend — tracked searches page
- A "My Tracked Searches" page (route `/tracked`) is accessible from the main navigation.
- The page lists all tracked searches stored for the current client ID, each showing: origin, destination, trip type, departure date range, return date range (if round-trip), alert threshold, current best price (most recent snapshot or "–" if none yet), and last-checked timestamp.
- Clicking "Delete" on a tracked search shows a confirmation and, on confirm, calls `DELETE /api/v1/tracked-searches/{id}` and removes the row from the list.

### AC-7: Frontend — save search flow
- A "Track this search" button appears on the search results page after results are returned.
- Clicking it opens a modal or inline form asking for `alert_email` and `threshold_price`.
- Both fields are required; `threshold_price` must be a positive number; `alert_email` must be a valid email format. The form shows validation errors before submission.
- On successful save, a success message is shown and the button label changes to "Tracking" (disabled) for the remainder of the session.

### AC-8: Frontend — price history view
- Clicking a tracked search row on `/tracked` expands or navigates to a detail view showing a line chart of price snapshots over time.
- The chart renders correctly with 0, 1, and 10+ data points. With 0 points it shows "No price data yet."

### AC-9: Test coverage
- All new backend modules have pytest tests with >= 80% line coverage.
- The scheduler's check logic is tested with a mocked Amadeus client and mocked SMTP.
- API endpoints are integration-tested with a real SQLite test database (not mocks of the DB layer).

### AC-10: Configuration
- The following environment variables are documented in `.env.example` (or an updated README section):
  - `DATABASE_URL` (default: `sqlite:///./flight_tracker.db`)
  - `SCHEDULER_INTERVAL_MINUTES` (default: `60`)
  - `SMTP_HOST` (required for email; default: `localhost`)
  - `SMTP_PORT` (default: `25`)
  - `SMTP_USERNAME` (optional)
  - `SMTP_PASSWORD` (optional)
  - `SMTP_FROM_ADDRESS` (default: `alerts@flighttracker.local`)
  - `SMTP_USE_TLS` (default: `false`)

---

## 4. Backend Requirements

### 4.1 Database — SQLite via SQLAlchemy (synchronous)

The existing `backend/src/app/db.py` stub must be filled in with a SQLAlchemy synchronous engine, session factory, and `Base`.

**Table: `tracked_searches`**

| Column | Type | Constraints |
|---|---|---|
| id | UUID (stored as CHAR(36)) | PK, not null |
| client_id | VARCHAR(36) | not null, indexed |
| origin | CHAR(3) | not null |
| destination | CHAR(3) | not null |
| trip_type | VARCHAR(10) | not null (`one_way` or `round_trip`) |
| departure_date_from | DATE | not null |
| departure_date_to | DATE | not null |
| return_date_from | DATE | nullable |
| return_date_to | DATE | nullable |
| adults | INTEGER | not null, default 1 |
| max_stops | INTEGER | nullable |
| threshold_price | NUMERIC(10,2) | not null |
| alert_email | VARCHAR(254) | not null |
| created_at | DATETIME | not null, default UTC now |
| is_active | BOOLEAN | not null, default true |

**Table: `price_snapshots`**

| Column | Type | Constraints |
|---|---|---|
| id | INTEGER | PK, autoincrement |
| tracked_search_id | CHAR(36) | FK -> tracked_searches.id, not null, indexed |
| checked_at | DATETIME | not null |
| best_price | NUMERIC(10,2) | not null |
| currency | VARCHAR(3) | not null |

The schema must be created via `Base.metadata.create_all()` at application startup (inside the existing lifespan context manager in `main.py`). No Alembic migrations are required for this milestone.

### 4.2 New API Endpoints

All new endpoints are registered under `/api/v1/` and return JSON.

**Client identification**: all tracked-search endpoints require the `X-Client-ID` header (a UUID v4 string generated by and persisted in the browser). Return 400 if the header is missing or not a valid UUID.

---

**`POST /api/v1/tracked-searches`**

Request body (JSON):
```
{
  "origin": "JFK",
  "destination": "LAX",
  "trip_type": "one_way",
  "departure_date_from": "2026-06-01",
  "departure_date_to": "2026-06-07",
  "return_date_from": null,
  "return_date_to": null,
  "adults": 1,
  "max_stops": null,
  "threshold_price": 299.99,
  "alert_email": "user@example.com"
}
```

Response 201:
```
{
  "id": "<uuid>",
  "client_id": "<uuid from header>",
  "origin": "JFK",
  "destination": "LAX",
  "trip_type": "one_way",
  "departure_date_from": "2026-06-01",
  "departure_date_to": "2026-06-07",
  "return_date_from": null,
  "return_date_to": null,
  "adults": 1,
  "max_stops": null,
  "threshold_price": "299.99",
  "alert_email": "user@example.com",
  "created_at": "<ISO-8601 UTC datetime>",
  "is_active": true,
  "current_best_price": null,
  "last_checked_at": null
}
```

Validation errors → 422.

---

**`GET /api/v1/tracked-searches`**

Response 200: array of tracked search objects (same schema as POST response), filtered to the `client_id` in `X-Client-ID`. `current_best_price` and `last_checked_at` are populated from the most recent `price_snapshots` row for each tracked search.

---

**`DELETE /api/v1/tracked-searches/{id}`**

- Sets `is_active = false` (soft delete) rather than removing the row, so price history is preserved.
- Returns 204 on success.
- Returns 404 if not found or if `client_id` does not match.

---

**`GET /api/v1/tracked-searches/{id}/history`**

Response 200:
```
{
  "tracked_search_id": "<uuid>",
  "snapshots": [
    {"checked_at": "<ISO-8601 UTC>", "best_price": "199.50", "currency": "USD"},
    ...
  ]
}
```
Snapshots ordered oldest-to-newest. Returns 404 if the tracked search is not found or does not belong to the requesting client ID.

---

### 4.3 Scheduler

Use **APScheduler** (`apscheduler>=3.10`) with `BackgroundScheduler` (thread-based, compatible with the synchronous SQLAlchemy session and Amadeus SDK patterns established in ADR-001).

- The scheduler is instantiated once and stored as application state (accessible via `request.app.state.scheduler`).
- The scheduler starts inside the FastAPI lifespan `startup` phase and is shut down in the `shutdown` phase.
- A single recurring job (`check_all_tracked_searches`) runs every `SCHEDULER_INTERVAL_MINUTES` minutes using an `IntervalTrigger`.
- `check_all_tracked_searches` fetches all `tracked_searches` where `is_active = true` and dispatches `check_single_tracked_search(tracked_search)` for each.
- `check_single_tracked_search` must:
  1. Call `search_flights()` (reusing the existing `FlightService`) with the saved parameters.
  2. If results are empty, log a warning and return without writing a snapshot.
  3. Find the minimum price across all returned offers.
  4. Write a new `price_snapshots` row.
  5. Compare the new best price to the threshold and the previous best price; send an alert email if the conditions in AC-5 are met.
- All exceptions inside `check_single_tracked_search` must be caught, logged at ERROR level, and must not propagate (the scheduler must continue to its next cycle).

### 4.4 Email Service

A standalone module `backend/src/app/services/email_service.py` with a single public function:

```python
def send_price_alert(
    to_address: str,
    origin: str,
    destination: str,
    departure_date_from: date,
    departure_date_to: date,
    return_date_from: date | None,
    return_date_to: date | None,
    best_price: Decimal,
    currency: str,
    threshold_price: Decimal,
) -> None: ...
```

- Uses Python's standard library `smtplib` and `email.mime` — no third-party email library.
- Reads SMTP settings from `Settings` (see AC-10).
- If `SMTP_USERNAME` and `SMTP_PASSWORD` are set, performs SMTP authentication.
- If `SMTP_USE_TLS` is `true`, uses `SMTP_SSL`.
- The function raises no exceptions; all SMTP errors are caught and logged at `ERROR` level.

### 4.5 Updated `config.py`

Add the following fields to `Settings`:

```python
database_url: str = "sqlite:///./flight_tracker.db"
scheduler_interval_minutes: int = 60
smtp_host: str = "localhost"
smtp_port: int = 25
smtp_username: Optional[str] = None
smtp_password: Optional[str] = None
smtp_from_address: str = "alerts@flighttracker.local"
smtp_use_tls: bool = False
```

---

## 5. Frontend Requirements

### 5.1 Client ID Management

- On first load, generate a UUID v4 and store it in `localStorage` under the key `flight_tracker_client_id`.
- On subsequent loads, read the existing value.
- All API calls to `/api/v1/tracked-searches*` include the header `X-Client-ID: <uuid>`.
- This logic lives in a utility module `src/api/client.ts` (or similar) used by all tracking API calls.

### 5.2 "Track This Search" Button and Modal

- After a successful search returns results, a "Track this search" button appears below the results header.
- Clicking the button opens a modal dialog with:
  - A read-only summary of the search (origin, destination, dates, trip type).
  - An "Alert email" text input (required, email format validated on submit).
  - A "Price threshold" number input (required, must be > 0, labelled with the currency from the first result or defaulting to "USD").
  - "Save" and "Cancel" buttons.
- On successful `POST /api/v1/tracked-searches` response, close the modal and replace the button with a disabled "Tracking" indicator for the remainder of the browser session (tracked per search in component state).
- On API error, display the error message inside the modal without closing it.

### 5.3 Tracked Searches Page (`/tracked`)

- Accessible via a navigation link "My Tracked Searches" in the app header or nav bar.
- On mount, calls `GET /api/v1/tracked-searches` and renders the results.
- Loading, error, and empty states must all be handled.
- Each row in the list shows:
  - Origin → Destination
  - Trip type badge ("One Way" / "Round Trip")
  - Departure date range
  - Return date range (only for round-trip)
  - Alert threshold (formatted as currency)
  - Current best price (from `current_best_price`; show "–" if null)
  - Last checked (from `last_checked_at`; show "Never" if null)
  - "History" button (expands or navigates to history view)
  - "Delete" button
- Clicking "Delete" shows a browser `confirm()` dialog. On confirm, calls `DELETE /api/v1/tracked-searches/{id}` and removes the row. On error, shows an inline error message.
- Clicking "History" expands an inline panel (accordion) below the row, calls `GET /api/v1/tracked-searches/{id}/history`, and renders a line chart.
  - Use **Recharts** (`recharts`) for the chart. X axis: `checked_at` (formatted as date). Y axis: `best_price`.
  - If 0 snapshots, render "No price data yet."
  - If 1 snapshot, render the chart with a single data point (dot visible).

### 5.4 Routing

Add client-side routing using **React Router** (`react-router-dom`). Two routes:
- `/` — existing `HomePage`
- `/tracked` — new `TrackedSearchesPage`

The `App.tsx` component wraps routes in a `<BrowserRouter>`.

### 5.5 TypeScript Types

Add the following types to `src/types/tracking.ts`:

```typescript
export interface TrackedSearch {
  id: string;
  client_id: string;
  origin: string;
  destination: string;
  trip_type: 'one_way' | 'round_trip';
  departure_date_from: string;
  departure_date_to: string;
  return_date_from: string | null;
  return_date_to: string | null;
  adults: number;
  max_stops: number | null;
  threshold_price: string;
  alert_email: string;
  created_at: string;
  is_active: boolean;
  current_best_price: string | null;
  last_checked_at: string | null;
}

export interface PriceSnapshot {
  checked_at: string;
  best_price: string;
  currency: string;
}

export interface PriceHistory {
  tracked_search_id: string;
  snapshots: PriceSnapshot[];
}

export interface CreateTrackedSearchRequest {
  origin: string;
  destination: string;
  trip_type: 'one_way' | 'round_trip';
  departure_date_from: string;
  departure_date_to: string;
  return_date_from: string | null;
  return_date_to: string | null;
  adults: number;
  max_stops: number | null;
  threshold_price: number;
  alert_email: string;
}
```

---

## 6. Out of Scope

- **User authentication**: there are no user accounts, passwords, or sessions. Identity is a client-side UUID only.
- **Push notifications / SMS**: only email alerts are delivered.
- **Alert deduplication cooldown**: once a price meets the threshold and is strictly lower than the previous recorded price, an email is sent; there is no cooldown period to suppress repeated alerts.
- **Amadeus booking links**: the alert email does not include a link to book the flight.
- **Multiple alert recipients**: one email address per tracked search.
- **Editing a tracked search**: users can delete and re-create but not update an existing tracked search.
- **Alembic database migrations**: schema is created fresh at startup via `create_all()`. No migration tooling.
- **Search result caching integration**: the scheduler bypasses the existing TTL cache (it calls the service directly; cache hits from manual searches are unrelated).
- **Mobile optimization**: same as m01, minimum supported width is 768px.
- **Deployment / containerization**: no Docker, no cloud hosting.
- **Pagination**: the tracked searches list is not paginated; a single client ID is not expected to have more than ~50 tracked searches.

---

## 7. Tech Stack Constraints

| Concern | Technology | Notes |
|---|---|---|
| Backend framework | FastAPI (existing) | No change |
| Python package manager | uv (existing) | No change |
| Database | SQLite via SQLAlchemy (synchronous, Core + ORM) | Fills the existing `db.py` stub |
| DB sessions | SQLAlchemy `sessionmaker` + `Session` | Dependency-injected via `Depends()` into route handlers |
| Scheduler | APScheduler `BackgroundScheduler` | Thread-based; consistent with ADR-001 (sync threadpool pattern) |
| Email | Python stdlib `smtplib` | No third-party email library |
| Frontend framework | React + TypeScript + Vite (existing) | No change |
| Frontend routing | React Router v6 (`react-router-dom`) | New dependency |
| Chart library | Recharts (`recharts`) | New dependency; chosen for React-native API and zero-config |
| Frontend package manager | npm (existing) | No change |
| Amadeus SDK | `amadeus` Python SDK (existing) | Reused as-is for scheduler checks |
| Testing (backend) | pytest + pytest-cov (existing) | |
| Testing (frontend) | Vitest + Testing Library (existing) | |

SQLAlchemy must use the **synchronous** API throughout (`create_engine`, `Session`, not `AsyncSession`). This is consistent with ADR-001's established pattern of synchronous database and HTTP I/O dispatched from a threadpool, not the async event loop.

---

## 8. Open Questions

The architect must resolve these during the design phase:

1. **DB session lifecycle in the scheduler**: APScheduler jobs run in background threads, not in FastAPI request contexts. How should SQLAlchemy sessions be scoped and closed inside `check_single_tracked_search`? (Options: create/close a new session per job invocation; use a scoped session registry.)

2. **First-run alert behavior**: On the very first scheduler check for a newly created tracked search, there is no prior snapshot to compare against. The PRD specifies an alert IS sent if price <= threshold. Should "first-run" checks be treated differently in any other way (e.g., no "price dropped" language in email, just "price found")?

3. **Scheduler interval granularity and start delay**: Should the first job execution happen immediately on startup (to populate an initial snapshot) or only after the first `SCHEDULER_INTERVAL_MINUTES` delay? An immediate first run is more user-friendly but increases startup API calls.

4. **Currency normalization**: Amadeus returns prices in the currency of the offer. If tracked searches produce results in different currencies (e.g., EUR vs USD), how should `threshold_price` comparison work? Should the system enforce that `threshold_price` is always compared in the offer's native currency?

5. **`X-Client-ID` header handling in Vite proxy**: The existing Vite proxy config forwards `/api` requests. Does it need any change to pass custom headers through, or does Vite forward all request headers by default?

6. **React Router vs hash routing**: Should the app use `BrowserRouter` (HTML5 history API, requires server-side catch-all for deep links) or `HashRouter` (works with the Vite dev server without configuration)? Given this is a dev-only milestone, either is acceptable, but the choice must be documented.

7. **Recharts dependency size**: Recharts adds ~300 KB to the bundle. Is this acceptable, or should a lighter alternative (e.g., a canvas-based micro-chart) be considered for the single price-history chart use case?
