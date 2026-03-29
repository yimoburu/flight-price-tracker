from amadeus import ResponseError
from fastapi import Request
from fastapi.responses import JSONResponse


async def amadeus_exception_handler(request: Request, exc: ResponseError) -> JSONResponse:
    """Map amadeus ResponseError to HTTP responses."""
    status_code = exc.response.status_code
    if status_code == 401:
        return JSONResponse(
            status_code=503, content={"detail": "Invalid Amadeus API credentials."}
        )
    elif status_code == 429:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please wait 60 seconds before retrying."},
        )
    elif status_code == 400:
        return JSONResponse(
            status_code=422, content={"detail": f"Invalid search parameters: {exc}"}
        )
    elif status_code >= 500:
        return JSONResponse(
            status_code=502, content={"detail": "Flight data service temporarily unavailable."}
        )
    else:
        return JSONResponse(status_code=500, content={"detail": "Unexpected error."})
