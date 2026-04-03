# Design: m01 — Core Search

## Architecture Overview

The application follows a client-server architecture with a clear separation between
the React/TypeScript frontend (port 5173) and the FastAPI backend (port 8000).

```
Browser (React/TS/Vite)
  |
  | /api/v1/*  (dev: Vite proxy → localhost:8000; prod: CORS)
  v
FastAPI Backend
  ├── GET  /api/v1/health
  ├── GET  /api/v1/airports?q={query}
  └── POST /api/v1/search
         |
         | (blocking SDK call, run in Starlette threadpool)
         v
     FlightService
         |
         ├── amadeus.shopping.flight_dates.get()        → calendar of cheapest dates
         └── amadeus.shopping.flight_offers_search.get() → detailed offers per date
              (+ amadeus.reference_data.locations.get()  for airports endpoint)
         |
         v
     Amadeus Self-Service API (test.api.amadeus.com)
```

**Key architectural decisions:**

1. **Sync SDK in threadpool** — The `amadeus` Python SDK is fully synchronous
   (`urllib.request.urlopen`). All route handlers that call the SDK are declared as
   `def` (not `async def`). FastAPI/Starlette automatically offloads these to a
   managed threadpool, keeping the event loop unblocked.
   (Evidence: POC `amadeus-sdk-async.md`)

2. **Two-step search** — For date-range searches, the service calls
   `flight_dates.get()` once to get the cheapest-date calendar, filters it to the
   user's requested window, then calls `flight_offers_search.get()` for the top-5
   cheapest dates to retrieve detailed offers. This bounds Amadeus API calls to a
   maximum of 6 per search (1 calendar + 5 offer lookups).
   (Evidence: POC `amadeus-date-range-behavior.md`)

3. **In-memory TTL cache** — `cachetools.TTLCache` with 15-minute TTL caches search
   results keyed on all search parameters. Protected by `threading.Lock()` for safe
   concurrent access from the threadpool.

4. **No database for m01** — This milestone stores nothing persistently. SQLAlchemy
   is not used until m02 (tracking/alerts). The `db.py` stub can be created empty.

## Data Flow

### POST /api/v1/search (one-way, date range)

```
1. Client sends:
   { origin, destination, trip_type, departure_date_from, departure_date_to,
     adults, max_stops }

2. SearchRequest Pydantic model validates:
   - IATA codes: 3 uppercase letters (regex validator)
   - Dates: valid ISO-8601, not in past
   - Date range: <= 30 days
   - adults: 1–9

3. FlightService.search(request) is called:
   a. Build cache key from all normalized params
   b. Check TTLCache — if hit, return cached result
   c. Call amadeus.shopping.flight_dates.get(origin, destination, oneWay=True)
   d. Filter response.data to entries where:
      departure_date_from <= departureDate <= departure_date_to
   e. Sort filtered entries by price ascending, take top 5
   f. For each of top 5 dates:
      - Call amadeus.shopping.flight_offers_search.get(
          originLocationCode=origin,
          destinationLocationCode=destination,
          departureDate=date,
          adults=adults,
          nonStop=(max_stops == 0),
          max=10
        )
   g. Flatten all offer results, apply max_stops filter if set
   h. Sort by total price ascending
   i. Map to FlightOfferResponse schema
   j. Store in cache with cache key
   k. Return list

4. Client receives: list of FlightOfferResponse objects
```

### POST /api/v1/search (round-trip, date range)

Same as above with differences:
- `flight_dates.get()` call includes `oneWay=False` (or omits oneWay, which defaults
  to round-trip behavior)
- Filter calendar on both `departureDate` and `returnDate` within respective ranges
- Top-5 selection considers combined outbound+return price
- `flight_offers_search.get()` is called with `returnDate` parameter for each pair

### GET /api/v1/airports?q={query}

```
1. Validate: q >= 3 characters
2. Call amadeus.reference_data.locations.get(
     keyword=q,
     subType='AIRPORT,CITY',
     **{'page[limit]': 10}
   )
3. Map to AirportResult schema: {iata_code, name, city, country}
4. Return list (max 10)
```

## Component Details

### Backend

#### `app/config.py` — Settings

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env')
    amadeus_client_id: str
    amadeus_client_secret: str
    amadeus_hostname: str = 'test'
    cors_origins: str = 'http://localhost:5173'
```

Uses `functools.lru_cache` to create a singleton `get_settings()` dependency.

#### `app/main.py` — FastAPI App Entry Point

- Creates `FastAPI()` instance
- Configures `CORSMiddleware` using `settings.cors_origins`
- Includes routers from `app/api/`
- Lifespan handler initializes the Amadeus `Client` singleton

#### `app/services/amadeus_client.py` — Amadeus Client Singleton

Holds the `amadeus.Client` instance (initialized once at startup). Raises
`ServiceUnavailableError` if credentials are missing.

```python
def get_amadeus_client() -> Client:
    return Client(
        client_id=settings.amadeus_client_id,
        client_secret=settings.amadeus_client_secret,
        hostname=settings.amadeus_hostname
    )
```

#### `app/services/flight_service.py` — Core Business Logic

Responsibilities:
- Two-step search orchestration (flight_dates → flight_offers_search)
- Date range filtering
- max_stops filtering
- Result mapping to response schemas
- In-memory cache management (TTLCache + Lock)

Functions:
```python
def search_flights(request: SearchRequest) -> list[FlightOfferResponse]: ...
def search_airports(query: str) -> list[AirportResult]: ...
```

#### `app/schemas/` — Pydantic Models

**`search.py`** — request/response schemas:
```python
class SearchRequest(BaseModel):
    origin: str              # validated: 3 uppercase letters
    destination: str         # validated: 3 uppercase letters
    trip_type: Literal['one_way', 'round_trip']
    departure_date_from: date
    departure_date_to: date
    return_date_from: date | None = None
    return_date_to: date | None = None
    adults: int = Field(default=1, ge=1, le=9)
    max_stops: int | None = Field(default=None, ge=0, le=2)

class SegmentInfo(BaseModel):
    airline: str
    flight_number: str
    departure_airport: str
    departure_time: str      # ISO datetime string
    arrival_airport: str
    arrival_time: str        # ISO datetime string
    duration: str            # ISO 8601 duration e.g. "PT2H30M"
    stops: int

class FlightOfferResponse(BaseModel):
    price: str
    currency: str
    departure_date: date
    return_date: date | None
    outbound_segments: list[SegmentInfo]
    return_segments: list[SegmentInfo]

class AirportResult(BaseModel):
    iata_code: str
    name: str
    city: str
    country: str
```

#### `app/api/search.py` — Route Handlers

```python
router = APIRouter(prefix="/api/v1", tags=["flights"])

@router.get("/health")
def health() -> dict: ...

@router.get("/airports")
def airports(q: str = Query(min_length=3)) -> list[AirportResult]: ...

@router.post("/search")
def search(body: SearchRequest) -> list[FlightOfferResponse]: ...
```

All handlers are `def` (not `async def`) to allow Starlette threadpool execution of
blocking Amadeus SDK calls.

#### Error Handling

```python
# app/api/error_handlers.py
from amadeus import ResponseError

def amadeus_exception_handler(request, exc: ResponseError) -> JSONResponse:
    status = exc.response.status_code
    if status == 429:
        return JSONResponse({"detail": "Rate limit exceeded. Retry after 60 seconds."}, 429)
    elif status == 401:
        return JSONResponse({"detail": "Invalid API credentials."}, 503)
    elif status >= 500:
        return JSONResponse({"detail": "Upstream flight data service error."}, 502)
    else:
        return JSONResponse({"detail": str(exc)}, status)
```

Registered via `app.add_exception_handler(ResponseError, amadeus_exception_handler)`.

### Frontend

#### Project Structure

```
frontend/src/
  api/
    airports.ts     # GET /api/v1/airports
    search.ts       # POST /api/v1/search
  types/
    flight.ts       # TypeScript interfaces matching backend schemas
  components/
    SearchForm/
      SearchForm.tsx
      SearchForm.test.tsx
    ResultsList/
      ResultsList.tsx
      FlightCard.tsx
    PriceGrid/
      PriceGrid.tsx
      PriceGrid.test.tsx
    AirportAutocomplete/
      AirportAutocomplete.tsx
  pages/
    HomePage.tsx
  App.tsx
  main.tsx
```

#### State Management

Single `HomePage` component manages application state:
- `searchParams` — current form values
- `results` — `FlightOfferResponse[]`
- `status` — `'idle' | 'loading' | 'success' | 'error'`
- `errorMessage` — string
- `viewMode` — `'list' | 'grid'`

No external state manager (Redux/Zustand) needed for m01 scope.

#### Key Components

**`SearchForm`** — controlled form component, emits `onSearch(params)` on submit.
Validates: date range ≤ 30 days, departure not in past, IATA code format, round-trip
requires return dates.

**`AirportAutocomplete`** — input with dropdown. Debounces 300ms via `useEffect` +
`clearTimeout`. Calls `GET /api/v1/airports?q=...`. Uses AbortController to cancel
in-flight requests on new keystrokes.

**`ResultsList`** — renders sorted list of `FlightCard` components, plus loading /
error / empty states. Shows "Showing X results" count.

**`FlightCard`** — displays single offer: price, dates, outbound + return segments
with airline code, flight number, times, duration, stops.

**`PriceGrid`** — toggle from list view:
- One-way: single-column table `departureDate → price`
- Round-trip: 2D matrix `departureDate (rows) × returnDate (cols)`, cells color-coded
  green→red via `hsl()` interpolation

#### Vite Dev Proxy

```typescript
// vite.config.ts
server: {
  proxy: {
    '/api': { target: 'http://localhost:8000', changeOrigin: true }
  }
}
```

This eliminates CORS issues in development. Production uses FastAPI's CORS middleware.

## Error Handling

| Scenario | Backend Response | Frontend Behavior |
|---|---|---|
| Amadeus rate limit | 429 `{"detail": "Rate limit exceeded..."}` | Error banner with retry message |
| Invalid IATA code | 422 validation error | Inline form validation (prevented before submit) |
| No results found | 200 `[]` | Empty state component |
| Amadeus server error | 502 `{"detail": "Upstream..."}` | Error banner "Service temporarily unavailable" |
| Invalid date range | 422 (backend) or form validation | Form error message |
| Network error | N/A | Error banner "Network error. Check your connection." |
| Missing credentials | 503 `{"detail": "Invalid API credentials"}` | Error banner |

## Development Server

Backend:
```bash
cd backend
uv run uvicorn src.app.main:app --reload --port 8000
```

Frontend:
```bash
cd frontend
npm run dev
# Starts on http://localhost:5173 with Vite proxy to :8000
```

## ADR References

New ADRs recorded in `ADR_history.md`:
- **ADR-001**: Sync SDK in Starlette threadpool (`def` route handlers)
- **ADR-002**: Two-step Amadeus search (flight_dates then flight_offers_search)
- **ADR-003**: cachetools TTLCache for in-memory caching
- **ADR-004**: Vite proxy for frontend dev (no CORS in development)
