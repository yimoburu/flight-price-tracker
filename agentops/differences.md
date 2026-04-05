# Comprehensive Review: Implementations vs. Documentation (Agentops)

This report details the deviations, bug fixes, and undocumented adaptations discovered when comparing the initial project requirements in `agentops/milestones` to the active codebase implementation. 

## 1. Frontend & Backend Schema Mismatch (`SearchParams` vs. `SearchRequest`)
- **Documentation**: `m01-core-search/tasks.yaml` defined the frontend `SearchParams` payload to send `origin` and `destination` directly as `AirportResult | null` objects.
- **Implementation Reality**: The backend Pydantic schema (`SearchRequest`) strictly expects 3-character IATA `str` codes. 
- **Deviation**: The frontend `search.ts` API wrapper was adapted to explicitly map `params.origin?.iata_code` and `params.destination?.iata_code` out of the rich object before submitting to avoid `HTTP 422 Unprocessable Content` backend validation errors.

## 2. Pydantic Strict Date Parsing vs. Frontend State
- **Documentation**: `m01-core-search` documentation states `return_date_from` and `return_date_to` are `date | None = None` in Python but formatted as simple `string` values in the React UI state.
- **Implementation Reality**: By default, the React state management resets cleared input boxes to empty strings (`""`), which the API blindly sent along. Pydantic interprets `""` as an invalid date length, throwing `422` errors.
- **Deviation**: An intermediary mapping layer was added in the frontend to explicitly nullify falsy empty string date fields (`params.return_date_from || null`).

## 3. Amadeus Flight Dates API (`404 Not Found` Edge Case)
- **Documentation**: `m01-core-search/tasks.yaml` specifies an algorithm where `client.shopping.flight_dates.get()` is invoked globally as Step 1 to discover a calendar matrix of the absolute cheapest dates within a user's selection window.
- **Implementation Reality**: The Amadeus `flight-dates` API relies heavily on cached historical pricing configurations. If a specific city-pair and date combination is obscure or not cached by carriers yet, Amadeus crashes via an `amadeus.errors.ResponseError` returning a `404 Not Found`. 
- **Deviation**: The backend service (`flight_service.py`) was augmented with a robust `try/except` fallback loop. Instead of throwing a 500 server error, it intercepts the `404`, and programmatically synthesizes a list of consecutive test dates generated via Python `timedelta` (max 5 days) starting from the user's `departure_date_from`, seamlessly bypassing the missing API cache dynamically.

## 4. Frontend Array Error Rendering 
- **Documentation**: Implementations must "throw an Error with a human-readable message on non-2xx responses".
- **Implementation Reality**: Naively consuming Pydantic 422 `{"detail": [...]}` error logs into `throw new Error(body.detail)` in TypeScript coerced the arrays implicitly into `[object Object],[object Object]`. 
- **Deviation**: The frontend error handling was drastically improved to perform conditional formatting: traversing error payloads to gracefully stringify nested `loc` keys and `msg` properties so backend validation errors explicitly appear in the UI.

## 5. Environment Pollution During Pytest Configuration Validations
- **Documentation**: Pydantic v2 `Settings` object defaults are routinely tested (e.g., `smtp_username` should initialize as `None`). 
- **Implementation Reality**: When users copy `.env.example` to `.env` (a local startup prerequisite), default empty definitions such as `SMTP_USERNAME=` naturally override `SettingsConfigDict` expectations with explicit empty strings `""`.
- **Deviation**: Test cases throughout `test_config_db.py` had to be heavily patched to execute `Settings(_env_file=None)` in isolated assertions so that configuration testing asserts pure application schemas, irrespective of any active environmental `.env` files present.

## 6. Vitest JSDOM Emulation Failures 
- **Documentation**: `m01` specifies that React tests enforce UI flows using `@testing-library/react` and Vitest across internal API wrappers that persist tokens over `localStorage` (`tracking-api.test.ts`).
- **Implementation Reality**: The default unconfigured Vitest execution runs inside `node`, not the browser emulator, meaning native variables like `localStorage` crash during API unit tests when attempting to access local authentication cookies.
- **Deviation**: Manual file-level pragmas (`/** @vitest-environment jsdom */`) alongside manual synthetic `localStorage` Object proxies were required directly above test boundaries to mock persistence correctly natively bypassing `node` boundaries.
