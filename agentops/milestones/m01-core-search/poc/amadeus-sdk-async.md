# POC: Amadeus SDK Async Integration

## Question

The `amadeus` Python SDK is synchronous (uses `urllib.request.urlopen` blocking calls).
How should it be integrated into an async FastAPI application without blocking the
event loop for the duration of each Amadeus API call (typically 500ms–3s)?

## Success Criteria

- **VIABLE**: A pattern exists that allows the sync SDK to be called from FastAPI
  without blocking the event loop, keeping the server responsive to other requests.
- **NOT_VIABLE**: No standard pattern exists; requires replacing the SDK or forking it
  to add async support.

## Approach

Investigation via:
1. Reading Amadeus SDK source (`amadeus-python` on GitHub) to confirm it uses
   `urllib.request.urlopen` (blocking, no async/await).
2. Reading FastAPI official documentation on `async def` vs `def` route handlers and
   how blocking libraries should be handled.
3. Reading AnyIO documentation on `to_thread.run_sync()`.
4. Verifying Python stdlib `asyncio.run_in_executor()` as an alternative.

## Results

### SDK is fully synchronous

Confirmed via SDK source code investigation:
- `amadeus/mixins/http.py` `__fetch()` method calls `self.http(request.http_request)`
- `self.http` defaults to `urllib.request.urlopen` (documented in `Client.__init__`
  docstring: "a urllib.request.urlopen compatible client... Default: urlopen")
- No `async def` methods, no `asyncio`, no `await` anywhere in the SDK
- SDK has zero external dependencies (stdlib only)

### FastAPI's built-in threadpool pattern

FastAPI (via Starlette) automatically runs `def` (non-async) route handler functions
in a thread pool executor. From FastAPI docs:

> "When you declare a path operation function with normal `def` instead of `async def`,
> it is run in an external threadpool that is then awaited, instead of being called
> directly (as it would block the server)."

This means **declaring route handlers as `def` (not `async def`) is sufficient** to
prevent event loop blocking. No extra code needed.

### Alternative: `asyncio.get_event_loop().run_in_executor()`

For cases where an `async def` function must call blocking code:
```python
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, blocking_function, arg1, arg2)
```

Modern equivalent (Python 3.10+):
```python
loop = asyncio.get_running_loop()
result = await loop.run_in_executor(None, blocking_function, arg1, arg2)
```

### Alternative: `anyio.to_thread.run_sync()`

AnyIO is a transitive dependency of FastAPI/Starlette:
```python
import anyio
result = await anyio.to_thread.run_sync(blocking_function, arg1)
```

Supports cancellation via `cancellable=True` parameter.

## Conclusion

**Verdict:** VIABLE

Two clean patterns exist for integrating the sync Amadeus SDK into async FastAPI:

**Chosen approach: declare route handlers as `def`** (not `async def`).

FastAPI automatically offloads `def` handlers to Starlette's built-in threadpool,
preventing event loop blocking. This is the simplest and most idiomatic pattern for
wrapping sync libraries in FastAPI. No additional imports or boilerplate required.

```python
# This is safe — FastAPI runs it in a thread automatically
@router.post("/search")
def search_flights(body: SearchRequest) -> list[FlightOffer]:
    return flight_service.search(body)
```

**Secondary consideration: caching thread-safety.** Since `def` handlers run in a
threadpool, shared in-memory cache (e.g., `cachetools.TTLCache`) must be protected
with `threading.Lock()`.

**Design implication**:
- All route handlers that call the Amadeus SDK: declare as `def`, not `async def`
- Service layer functions: declare as `def`
- Cache access: wrap TTLCache with `threading.Lock()`
- No need to replace or fork the SDK; no async HTTP client needed

## Limitations

- The `def` threadpool approach has a default concurrency limit of 40 threads
  (Starlette default). For this project's scale (single-user development app) this is
  more than sufficient.
- Running many concurrent sync SDK calls would consume threads proportionally — not
  relevant for this milestone but worth noting for future scaling.
- The `http=` parameter on `Client()` could accept a mock HTTP callable for unit
  testing without network calls; this enables fast test execution.
