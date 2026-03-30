# Design: m02 — Tracking & Alerts

## Open Questions Resolved

Before detailing the architecture, the following PRD open questions are resolved:

**1. DB session lifecycle in the scheduler**
Create a new `Session` instance at the start of each `check_single_tracked_search`
invocation and close it in a `finally` block. `sessionmaker` is a module-level factory;
each background thread calls `SessionLocal()` to get an independent session. This is the
standard SQLAlchemy pattern for multi-threaded non-request contexts. A scoped-session
registry is not needed — the jobs are short-lived and sequential within one worker.

**2. First-run alert email language**
When `previous_best_price` is `None` (no prior snapshot exists), an alert IS sent if
`best_price <= threshold_price`. The email body uses "Price found" language instead of
"Price dropped". The subject line is exactly as specified in AC-5 regardless of whether
it is a first run.

**3. Scheduler start delay**
The first job fires after one full `SCHEDULER_INTERVAL_MINUTES` delay, not immediately
on startup. Reason: an immediate first run would spike Amadeus API calls every time the
server restarts (especially during development). The "Never" last-checked state shown in
the UI until the first cycle is an acceptable tradeoff.

**4. Currency normalization**
`threshold_price` is compared directly to `best_price` in the offer's native currency
(no currency conversion). The user sets the threshold knowing the currency displayed in
search results. This constraint is documented in the Track modal UI as "(in [currency])".
If an offer returns a different currency than the first result, the comparison still
proceeds — the Amadeus test API consistently returns USD for US routes.

**5. Vite proxy and X-Client-ID header**
The existing Vite proxy with `changeOrigin: true` forwards all request headers by
default, including `X-Client-ID`. No `vite.config.ts` changes are required.

**6. React Router strategy**
Use `BrowserRouter` (HTML5 history API). Vite's dev server returns `index.html` for all
non-asset 404s by default, so deep-links like `/tracked` work without any server
configuration. `HashRouter` is rejected for producing ugly `/#/tracked` URLs.

**7. Recharts bundle size**
Accept the ~300 KB addition. Recharts is PRD-specified and bundle size optimization is
out of scope for this milestone (section 6).

---

## Architecture Overview

```
Browser (React/TS/Vite)
  ├── /          → HomePage (existing, extended with TrackButton + TrackModal)
  └── /tracked   → TrackedSearchesPage (new)
        |
        | X-Client-ID header on all /api/v1/tracked-searches* calls
        v
FastAPI Backend (port 8000)
  ├── POST   /api/v1/tracked-searches
  ├── GET    /api/v1/tracked-searches
  ├── DELETE /api/v1/tracked-searches/{id}
  ├── GET    /api/v1/tracked-searches/{id}/history
  └── (existing search/airports endpoints unchanged)
        |
        ├── SQLAlchemy Session (synchronous) → SQLite file
        └── APScheduler BackgroundScheduler (background thread)
                |
                ├── FlightService.search_flights() (reused)
                └── EmailService.send_price_alert() → smtplib → SMTP server
```

**Key new components:**

- `app/db.py` — SQLAlchemy engine, `SessionLocal` factory, `Base`
- `app/models/tracked_search.py` — ORM models for `tracked_searches` and `price_snapshots`
- `app/schemas/tracking.py` — Pydantic request/response schemas for tracking endpoints
- `app/api/tracking.py` — Route handlers for tracking endpoints
- `app/services/scheduler.py` — APScheduler setup, `check_all_tracked_searches`, `check_single_tracked_search`
- `app/services/email_service.py` — `send_price_alert()` via smtplib
- `frontend/src/api/tracking.ts` — Client-side API calls with X-Client-ID header
- `frontend/src/api/client.ts` — Client ID generation/retrieval from localStorage
- `frontend/src/types/tracking.ts` — TypeScript types
- `frontend/src/components/TrackButton/` — "Track this search" button + modal
- `frontend/src/components/TrackedSearchRow/` — Single tracked search row with history
- `frontend/src/components/PriceHistoryChart/` — Recharts line chart
- `frontend/src/pages/TrackedSearchesPage.tsx` — `/tracked` route page

---

## Data Flow

### POST /api/v1/tracked-searches

```
1. Request: POST /api/v1/tracked-searches
   Headers: X-Client-ID: <uuid>, Content-Type: application/json
   Body: CreateTrackedSearchRequest JSON

2. get_client_id() dependency extracts and validates X-Client-ID header
   → 400 if missing or not a valid UUID format

3. Pydantic validates CreateTrackedSearchRequest body → 422 on invalid

4. Route handler opens a DB session (via Depends(get_db))
   Creates a TrackedSearch ORM model instance with a new uuid.uuid4() id
   Commits to SQLite

5. Returns 201 TrackedSearchResponse (with current_best_price=null, last_checked_at=null)
```

### GET /api/v1/tracked-searches

```
1. Headers: X-Client-ID: <uuid>
2. Query: SELECT * FROM tracked_searches WHERE client_id = ? AND is_active = true
3. For each result: LEFT JOIN price_snapshots to get most recent snapshot
   (subquery: SELECT MAX(id) FROM price_snapshots WHERE tracked_search_id = ?)
4. Returns list of TrackedSearchResponse with current_best_price and last_checked_at populated
```

### DELETE /api/v1/tracked-searches/{id}

```
1. Headers: X-Client-ID: <uuid>
2. Query: SELECT FROM tracked_searches WHERE id = ? AND client_id = ?
   → 404 if not found or client_id mismatch
3. UPDATE tracked_searches SET is_active = false WHERE id = ?
4. Returns 204
```

### GET /api/v1/tracked-searches/{id}/history

```
1. Headers: X-Client-ID: <uuid>
2. Query: SELECT FROM tracked_searches WHERE id = ? AND client_id = ?
   → 404 if not found or client_id mismatch
3. Query: SELECT checked_at, best_price, currency FROM price_snapshots
          WHERE tracked_search_id = ? ORDER BY checked_at ASC
4. Returns PriceHistoryResponse
```

### Scheduler cycle

```
1. BackgroundScheduler fires check_all_tracked_searches() every N minutes
2. Opens a new SessionLocal(), queries: SELECT * FROM tracked_searches WHERE is_active = true
3. For each tracked_search: calls check_single_tracked_search(tracked_search)
4. Session closed in finally block

Per tracked_search:
  a. Build SearchRequest from saved parameters
  b. Call search_flights(request, amadeus_client) — reuses FlightService
  c. If empty results: log warning, return
  d. Find min(float(offer.price)) across all offers — get currency from that offer
  e. Query: SELECT best_price FROM price_snapshots WHERE tracked_search_id = ?
            ORDER BY checked_at DESC LIMIT 1
  f. Write new price_snapshots row (tracked_search_id, checked_at=utcnow(), best_price, currency)
  g. Alert condition: best_price <= threshold_price AND
       (previous_best_price is None OR best_price < previous_best_price)
  h. If alert condition met: call send_price_alert()
  i. All exceptions caught at step level, logged ERROR, scheduler continues
```

---

## Database Schema

### SQLAlchemy Models (`app/models/tracked_search.py`)

```python
import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey,
    Integer, Numeric, String
)
from sqlalchemy.orm import relationship

from app.db import Base


class TrackedSearch(Base):
    __tablename__ = "tracked_searches"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String(36), nullable=False, index=True)
    origin = Column(String(3), nullable=False)
    destination = Column(String(3), nullable=False)
    trip_type = Column(String(10), nullable=False)            # 'one_way' | 'round_trip'
    departure_date_from = Column(Date, nullable=False)
    departure_date_to = Column(Date, nullable=False)
    return_date_from = Column(Date, nullable=True)
    return_date_to = Column(Date, nullable=True)
    adults = Column(Integer, nullable=False, default=1)
    max_stops = Column(Integer, nullable=True)
    threshold_price = Column(Numeric(10, 2), nullable=False)
    alert_email = Column(String(254), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    is_active = Column(Boolean, nullable=False, default=True)

    snapshots = relationship(
        "PriceSnapshot", back_populates="tracked_search",
        cascade="all, delete-orphan"
    )


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tracked_search_id = Column(
        String(36), ForeignKey("tracked_searches.id"), nullable=False, index=True
    )
    checked_at = Column(DateTime, nullable=False)
    best_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)

    tracked_search = relationship("TrackedSearch", back_populates="snapshots")
```

### `app/db.py`

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    return create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},  # required for SQLite + multi-thread
    )


engine = _make_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency: yields a DB session, closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**Notes:**
- `check_same_thread=False` is required for SQLite when sessions are used across threads
  (the scheduler's background thread + FastAPI threadpool threads share the same file).
- `Base.metadata.create_all(engine)` is called inside the FastAPI lifespan at startup.
- The `models` package must be imported before `create_all` so SQLAlchemy discovers all
  table definitions.

---

## API Endpoints

### Router: `app/api/tracking.py`

```python
router = APIRouter(prefix="/api/v1", tags=["tracking"])
```

All handlers are `def` (not `async def`) — consistent with ADR-001: DB access via
synchronous SQLAlchemy is a blocking operation, just like the Amadeus SDK.

#### Shared dependency: `get_client_id()`

```python
def get_client_id(x_client_id: str = Header(..., alias="X-Client-ID")) -> str:
    """Validates X-Client-ID header is a valid UUID v4 string."""
    try:
        uuid.UUID(x_client_id, version=4)
    except ValueError:
        raise HTTPException(status_code=400, detail="X-Client-ID must be a valid UUID v4")
    return x_client_id
```

#### POST /api/v1/tracked-searches

```python
@router.post("/tracked-searches", response_model=TrackedSearchResponse, status_code=201)
def create_tracked_search(
    body: CreateTrackedSearchRequest,
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db),
) -> TrackedSearchResponse: ...
```

#### GET /api/v1/tracked-searches

```python
@router.get("/tracked-searches", response_model=list[TrackedSearchResponse])
def list_tracked_searches(
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db),
) -> list[TrackedSearchResponse]: ...
```

The handler enriches each result with `current_best_price` and `last_checked_at` by
querying `price_snapshots` for the most recent row per tracked search.

Implementation strategy: for each TrackedSearch returned, do a single additional query:
```python
latest = db.query(PriceSnapshot)\
    .filter(PriceSnapshot.tracked_search_id == ts.id)\
    .order_by(PriceSnapshot.checked_at.desc())\
    .first()
```
This is N+1 queries but acceptable for the expected data scale (<=50 tracked searches).

#### DELETE /api/v1/tracked-searches/{id}

```python
@router.delete("/tracked-searches/{search_id}", status_code=204)
def delete_tracked_search(
    search_id: str,
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db),
) -> None: ...
```

Sets `is_active = False` (soft delete). Returns 204 with no body.

#### GET /api/v1/tracked-searches/{id}/history

```python
@router.get(
    "/tracked-searches/{search_id}/history",
    response_model=PriceHistoryResponse,
)
def get_price_history(
    search_id: str,
    client_id: str = Depends(get_client_id),
    db: Session = Depends(get_db),
) -> PriceHistoryResponse: ...
```

---

## Pydantic Schemas (`app/schemas/tracking.py`)

```python
from datetime import date, datetime
from decimal import Decimal
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field


class CreateTrackedSearchRequest(BaseModel):
    origin: str = Field(..., pattern=r'^[A-Z]{3}$')
    destination: str = Field(..., pattern=r'^[A-Z]{3}$')
    trip_type: Literal['one_way', 'round_trip']
    departure_date_from: date
    departure_date_to: date
    return_date_from: Optional[date] = None
    return_date_to: Optional[date] = None
    adults: int = Field(default=1, ge=1, le=9)
    max_stops: Optional[int] = Field(default=None, ge=0, le=2)
    threshold_price: Decimal = Field(..., gt=0, decimal_places=2)
    alert_email: EmailStr


class PriceSnapshotResponse(BaseModel):
    checked_at: datetime
    best_price: Decimal
    currency: str

    model_config = {"from_attributes": True}


class TrackedSearchResponse(BaseModel):
    id: str
    client_id: str
    origin: str
    destination: str
    trip_type: str
    departure_date_from: date
    departure_date_to: date
    return_date_from: Optional[date]
    return_date_to: Optional[date]
    adults: int
    max_stops: Optional[int]
    threshold_price: Decimal
    alert_email: str
    created_at: datetime
    is_active: bool
    current_best_price: Optional[Decimal]
    last_checked_at: Optional[datetime]

    model_config = {"from_attributes": True}


class PriceHistoryResponse(BaseModel):
    tracked_search_id: str
    snapshots: list[PriceSnapshotResponse]
```

**Note on `EmailStr`**: Pydantic v2's `EmailStr` requires `pydantic[email]` extra
(which pulls in `email-validator`). Add `pydantic[email]` to `pyproject.toml`
dependencies. Alternatively, use `str` + a regex validator to avoid the extra dep.
The design chooses `pydantic[email]` / `email-validator` for correctness.

---

## Updated `config.py`

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    # existing
    amadeus_client_id: Optional[str] = None
    amadeus_client_secret: Optional[str] = None
    amadeus_hostname: str = "test"
    cors_origins: str = "http://localhost:5173"
    # new in m02
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

## Scheduler Design (`app/services/scheduler.py`)

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

def create_scheduler() -> BackgroundScheduler:
    """Create and configure the APScheduler BackgroundScheduler."""
    scheduler = BackgroundScheduler()
    settings = get_settings()
    scheduler.add_job(
        check_all_tracked_searches,
        trigger=IntervalTrigger(minutes=settings.scheduler_interval_minutes),
        id="check_all_tracked_searches",
        replace_existing=True,
    )
    return scheduler


def check_all_tracked_searches() -> None:
    """Fetch all active tracked searches and check each one."""
    db = SessionLocal()
    try:
        searches = db.query(TrackedSearch).filter(TrackedSearch.is_active == True).all()
    finally:
        db.close()
    for ts in searches:
        check_single_tracked_search(ts)


def check_single_tracked_search(ts: TrackedSearch) -> None:
    """Run one search, record snapshot, send alert if threshold met."""
    db = SessionLocal()
    try:
        # 1. Build SearchRequest from TrackedSearch fields
        # 2. Call search_flights(request, get_amadeus_client())
        # 3. If no results: log warning, return
        # 4. Find min price offer
        # 5. Get previous best price from DB
        # 6. Write new PriceSnapshot
        # 7. Evaluate alert condition
        # 8. Call send_price_alert() if met
    except Exception:
        logger.error("check_single_tracked_search failed for %s", ts.id, exc_info=True)
    finally:
        db.close()
```

**Lifecycle in `main.py`:**

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    Base.metadata.create_all(bind=engine)
    scheduler = create_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    yield
    # shutdown
    scheduler.shutdown(wait=False)

app = FastAPI(lifespan=lifespan, ...)
```

**Thread safety notes:**
- `SessionLocal()` is called fresh inside each job function — no shared session state
  between scheduler threads and FastAPI threadpool threads.
- `get_amadeus_client()` returns the same singleton `Client` instance but the Amadeus
  Python SDK is thread-safe (each call creates its own HTTP connection).
- The TTLCache in `flight_service.py` is already protected by `threading.Lock()`.

---

## Email Service Design (`app/services/email_service.py`)

```python
import logging
import smtplib
from datetime import date
from decimal import Decimal
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.config import get_settings

logger = logging.getLogger(__name__)


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
    previous_best_price: Decimal | None = None,
) -> None:
    """Send a price alert email. All SMTP errors are caught and logged."""
    settings = get_settings()
    subject = f"Price alert: {origin} → {destination} now {currency}{best_price}"
    body = _build_body(
        origin, destination, departure_date_from, departure_date_to,
        return_date_from, return_date_to, best_price, currency,
        threshold_price, previous_best_price,
    )
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_address
    msg["To"] = to_address
    msg.attach(MIMEText(body, "plain"))
    try:
        if settings.smtp_use_tls:
            smtp_cls = smtplib.SMTP_SSL
        else:
            smtp_cls = smtplib.SMTP
        with smtp_cls(settings.smtp_host, settings.smtp_port) as server:
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_from_address, to_address, msg.as_string())
    except Exception:
        logger.error("Failed to send price alert to %s", to_address, exc_info=True)
```

**Email body (`_build_body`):**
- Plain text only (no HTML template dependency).
- If `previous_best_price is None`: "A price has been found for your tracked route."
- Else: "The price has dropped for your tracked route."
- Includes: origin, destination, date ranges, best price with currency, alert threshold.

---

## Frontend Routing

### `App.tsx` (updated)

```tsx
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { HomePage } from './pages/HomePage';
import { TrackedSearchesPage } from './pages/TrackedSearchesPage';
import { NavBar } from './components/NavBar';

export default function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/tracked" element={<TrackedSearchesPage />} />
      </Routes>
    </BrowserRouter>
  );
}
```

### `NavBar` component

A simple `<nav>` with two `<Link>` elements: "Search" → `/`, "My Tracked Searches" → `/tracked`.

---

## Frontend Component Architecture

```
src/
  api/
    client.ts           # getClientId() → reads/writes localStorage
    tracking.ts         # createTrackedSearch(), listTrackedSearches(),
                        # deleteTrackedSearch(), getPriceHistory()
  types/
    tracking.ts         # TrackedSearch, PriceSnapshot, PriceHistory, CreateTrackedSearchRequest
  components/
    NavBar/
      index.tsx         # Navigation links
      NavBar.test.tsx
    TrackButton/
      index.tsx         # Button + modal; accepts searchParams + currency prop
      TrackButton.test.tsx
    TrackedSearchRow/
      index.tsx         # Single row with inline history accordion
      TrackedSearchRow.test.tsx
    PriceHistoryChart/
      index.tsx         # Recharts LineChart wrapper
      PriceHistoryChart.test.tsx
  pages/
    TrackedSearchesPage.tsx
    TrackedSearchesPage.test.tsx
```

### `src/api/client.ts`

```typescript
const CLIENT_ID_KEY = 'flight_tracker_client_id';

export function getClientId(): string {
  let id = localStorage.getItem(CLIENT_ID_KEY);
  if (!id) {
    id = crypto.randomUUID();
    localStorage.setItem(CLIENT_ID_KEY, id);
  }
  return id;
}

export function getAuthHeaders(): Record<string, string> {
  return { 'X-Client-ID': getClientId() };
}
```

### `src/api/tracking.ts`

```typescript
import { getAuthHeaders } from './client';
import type {
  TrackedSearch, PriceHistory, CreateTrackedSearchRequest
} from '../types/tracking';

export async function createTrackedSearch(
  body: CreateTrackedSearchRequest
): Promise<TrackedSearch>;

export async function listTrackedSearches(): Promise<TrackedSearch[]>;

export async function deleteTrackedSearch(id: string): Promise<void>;

export async function getPriceHistory(id: string): Promise<PriceHistory>;
```

All functions include `getAuthHeaders()` in `fetch` headers, throw `Error` with
`detail` message on non-OK responses.

### `TrackButton` component

```typescript
interface TrackButtonProps {
  searchParams: SearchParams;   // from HomePage state
  currency: string;             // from first result, default 'USD'
}
```

Internal state: `isTracking: boolean` (persisted only in component state, not
localStorage). When `isTracking` is true, renders a disabled "Tracking" indicator.
When false, renders "Track this search" button that opens the modal on click.

Modal state: `{ email: string, threshold: string, error: string | null, submitting: boolean }`.
Validation on submit: email must match `/^[^\s@]+@[^\s@]+\.[^\s@]+$/`, threshold must
parse as a positive number. On success: close modal, set `isTracking = true`.

### `PriceHistoryChart` component

```typescript
interface PriceHistoryChartProps {
  snapshots: PriceSnapshot[];
}
```

- 0 snapshots: renders `<p>No price data yet.</p>`
- 1+ snapshots: renders a Recharts `LineChart` with:
  - `XAxis` dataKey: formatted `checked_at` as `YYYY-MM-DD`
  - `YAxis` dataKey: `best_price` (parsed as float)
  - `Dot` shown on each data point (important for 1-point case)
  - `CartesianGrid`, `Tooltip`, `Legend`

### `TrackedSearchesPage`

Page state: `{ searches: TrackedSearch[], status: 'loading'|'success'|'error', errorMessage: string }`.
On mount: calls `listTrackedSearches()`.
Renders: loading spinner (text "Loading..."), error message, empty state ("No tracked searches yet."), or list of `TrackedSearchRow`.

### `TrackedSearchRow`

Props: `{ search: TrackedSearch, onDeleted: (id: string) => void }`.
Internal state: `{ expanded: boolean, history: PriceHistory | null, historyStatus: 'idle'|'loading'|'error' }`.
- "History" button click: sets `expanded = !expanded`. When expanding for the first time,
  calls `getPriceHistory(search.id)` and renders `PriceHistoryChart`.
- "Delete" button: calls `window.confirm()`. On confirm, calls `deleteTrackedSearch(search.id)`,
  then calls `onDeleted(search.id)` to remove from parent list. On API error, sets inline
  error message in the row.

---

## Task Interface Contracts

The following exports must exist exactly as specified so that dependent tasks can stub/mock them:

**Backend:**
- `app.db`: exports `Base`, `engine`, `SessionLocal`, `get_db`
- `app.models.tracked_search`: exports `TrackedSearch`, `PriceSnapshot`
- `app.schemas.tracking`: exports `CreateTrackedSearchRequest`, `TrackedSearchResponse`, `PriceHistoryResponse`, `PriceSnapshotResponse`
- `app.services.email_service`: exports `send_price_alert`
- `app.services.scheduler`: exports `create_scheduler`, `check_all_tracked_searches`, `check_single_tracked_search`
- `app.api.tracking`: exports `router` (an `APIRouter`)

**Frontend:**
- `src/api/client.ts`: exports `getClientId`, `getAuthHeaders`
- `src/api/tracking.ts`: exports `createTrackedSearch`, `listTrackedSearches`, `deleteTrackedSearch`, `getPriceHistory`
- `src/types/tracking.ts`: exports `TrackedSearch`, `PriceSnapshot`, `PriceHistory`, `CreateTrackedSearchRequest`
- `src/components/NavBar/index.tsx`: default + named export `NavBar`
- `src/components/TrackButton/index.tsx`: named export `TrackButton`
- `src/components/PriceHistoryChart/index.tsx`: named export `PriceHistoryChart`
- `src/components/TrackedSearchRow/index.tsx`: named export `TrackedSearchRow`
- `src/pages/TrackedSearchesPage.tsx`: named export `TrackedSearchesPage`

---

## Error Handling

| Scenario | Backend Response | Frontend Behavior |
|---|---|---|
| Missing X-Client-ID header | 400 `{"detail": "X-Client-ID header required"}` | Modal shows error; page shows error banner |
| Invalid UUID in X-Client-ID | 400 `{"detail": "X-Client-ID must be a valid UUID v4"}` | Same as above |
| Tracked search not found | 404 | TrackedSearchRow shows inline error on delete |
| Wrong client_id for search | 404 (same response as not found) | Same as above |
| Validation error in POST body | 422 | Modal shows first validation error |
| SMTP failure | Logged ERROR, not propagated | No user-facing impact (scheduler continues) |
| Amadeus error in scheduler | Logged ERROR, not propagated | Snapshot not written, no alert sent |
| DB error in scheduler | Logged ERROR, not propagated | Scheduler continues next cycle |

---

## Development Server

Backend (same as m01, now also starts scheduler):
```bash
cd backend
uv run uvicorn src.app.main:app --reload --port 8000
```

Frontend (no change):
```bash
cd frontend
npm run dev
```

For email testing during development: use a local SMTP debug server:
```bash
python -m smtpd -n -c DebuggingServer localhost:1025
# Set SMTP_HOST=localhost, SMTP_PORT=1025 in .env
```

---

## New Dependencies

**Backend** (add to `pyproject.toml`):
```
apscheduler>=3.10
email-validator>=2.0   # required by pydantic[email] for EmailStr
sqlalchemy>=2.0
```

The `pydantic[email]` extra is activated by adding `email-validator` directly.

**Frontend** (add to `package.json`):
```
react-router-dom: ^6.0
recharts: ^2.0
@types/recharts: (built-in, not needed — recharts ships its own types)
```

---

## ADR References

Existing ADRs this design is consistent with:
- **ADR-001**: Scheduler uses `check_same_thread=False` SQLite option to allow safe use
  from background threads, same pattern of blocking I/O in threads. Route handlers
  remain `def` for DB + Amadeus calls.
- **ADR-002**: Scheduler reuses `search_flights()` directly — same two-step Amadeus
  search pattern, same ADR-bounded API call count.
- **ADR-003**: Scheduler bypasses TTLCache by design (out of scope per PRD section 6).
  Cache is still used for manual searches.
- **ADR-004**: No Vite proxy changes needed; custom headers forwarded automatically.

New ADRs recorded:
- **ADR-005**: SQLAlchemy synchronous engine + per-thread session pattern
- **ADR-006**: APScheduler BackgroundScheduler with delayed first run
- **ADR-007**: BrowserRouter (HTML5 history) for React Router
