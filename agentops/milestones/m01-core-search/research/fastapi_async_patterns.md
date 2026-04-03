# Research: FastAPI Async Patterns for Blocking Libraries

Source: https://fastapi.tiangolo.com/async/
Source: https://anyio.readthedocs.io/en/stable/threads.html
Source: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

## Problem

The `amadeus` SDK uses `urllib.request.urlopen` — a blocking, synchronous HTTP call.
Using it inside an `async def` FastAPI route would block the event loop during the
entire network round-trip (typically 500ms–3s for Amadeus test API).

## Solution Options

### Option A: Declare routes as `def` (not `async def`)

FastAPI automatically runs `def` path operation functions in an external threadpool
(starlette's `run_in_threadpool`), preventing event loop blocking:

```python
@router.post("/search")
def search_flights(request: SearchRequest):
    result = amadeus_service.search(request)
    return result
```

Pros: Simplest approach, zero extra code, idiomatic FastAPI.
Cons: Cannot use `await` inside these functions; slightly less control over concurrency.

### Option B: `asyncio.get_event_loop().run_in_executor()` inside `async def`

```python
import asyncio

@router.post("/search")
async def search_flights(request: SearchRequest):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, amadeus_service.search, request)
    return result
```

Pros: Can mix awaitable calls in same handler; explicit threadpool usage.
Cons: More verbose; `asyncio.get_event_loop()` deprecated in favor of `asyncio.get_running_loop()`.

### Option C: `anyio.to_thread.run_sync()` (preferred for async services)

```python
import anyio

@router.post("/search")
async def search_flights(request: SearchRequest):
    result = await anyio.to_thread.run_sync(amadeus_service.search, request)
    return result
```

Pros: Works with both asyncio and trio (FastAPI uses anyio internally); explicit, clean.
Cons: Requires anyio (already a FastAPI/Starlette transitive dependency).

## Chosen Pattern

**Option A: `def` routes** for endpoint handlers that purely call the Amadeus service.
**Option C: `anyio.to_thread.run_sync()`** inside `async def` service methods that
need to be awaited from other async contexts (e.g., if service layer is async).

For this project, since the service functions are simple wrappers around sync SDK calls,
declaring route handlers as `def` is the cleanest approach. Service layer functions
that do blocking I/O should also be defined as regular `def` (not `async def`) and
called directly from `def` route handlers.

## pydantic-settings Pattern

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    amadeus_client_id: str
    amadeus_client_secret: str
    amadeus_hostname: str = 'test'
    cors_origins: str = 'http://localhost:5173'
```

## Caching Pattern (cachetools TTLCache)

TTLCache is **not thread-safe** by default. In a multi-threaded threadpool context
(FastAPI `def` handlers), the cache must be protected with `threading.Lock()`:

```python
import threading
from cachetools import TTLCache
from cachetools import cached

cache = TTLCache(maxsize=128, ttl=900)  # 15 min TTL
cache_lock = threading.Lock()

@cached(cache=cache, lock=cache_lock)
def search_flights(origin, destination, ...):
    ...
```

Alternatively, use a dict with manual lock or `functools.lru_cache` for simpler cases.

## FastAPI APIRouter Structure

```python
# api/search.py
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1", tags=["flights"])

@router.post("/search")
def search_flights(...): ...

# main.py
app = FastAPI()
app.include_router(router)
```
