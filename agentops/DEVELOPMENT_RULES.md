# Development Rules

## Language & Runtime
- **Backend**: Python 3.12
- **Frontend**: TypeScript, React 18, Vite

## Frameworks & Libraries
- **Backend framework**: FastAPI (async)
- **ORM**: SQLAlchemy 2.x (async) with SQLite
- **Flight API client**: `amadeus` Python SDK
- **Scheduler**: APScheduler 3.x
- **Email**: smtplib (stdlib)
- **Frontend**: React 18 + TypeScript + Vite
- **HTTP client (frontend)**: axios or native fetch

## Package Managers
- **Backend**: uv (`pyproject.toml`)
- **Frontend**: npm (`package.json`)

## Testing
- **Backend**: pytest + pytest-asyncio; httpx for API client tests
- **Frontend**: Vitest + React Testing Library
- **Coverage**: minimum 80% for backend business logic
- **TDD**: write failing tests first, then implement

## Code Style
- **Backend**: ruff (linting), black (formatting); type hints required on all functions
- **Frontend**: ESLint + Prettier; strict TypeScript (`strict: true`)

## Conventions
- All backend routes are async
- Database sessions via dependency injection (FastAPI `Depends`)
- Environment variables via `.env` + `python-dotenv`; never hardcode credentials
- API keys (Amadeus, SMTP) loaded from environment only
- Frontend communicates with backend via REST API at `/api/v1/`
- CORS configured for local development (localhost:5173 -> localhost:8000)
- Error responses follow `{"detail": "..."}` FastAPI convention
- Dates use ISO 8601 format (YYYY-MM-DD) throughout

## Project Structure
```
flight_price_tracker/
  backend/
    pyproject.toml
    src/
      app/
        main.py         # FastAPI app entry point
        api/            # Route handlers
        models/         # SQLAlchemy models
        schemas/        # Pydantic schemas
        services/       # Business logic (flight search, scheduler, alerts)
        db.py           # Database setup
        config.py       # Settings via pydantic-settings
  frontend/
    package.json
    vite.config.ts
    src/
      components/
      pages/
      api/              # API client functions
      types/
```

## Git
- Commit messages: imperative mood, lowercase, e.g. `add flight search endpoint`
- No secrets in git history; `.env` is gitignored
