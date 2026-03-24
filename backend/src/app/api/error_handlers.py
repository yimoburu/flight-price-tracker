from amadeus import ResponseError
from fastapi import Request
from fastapi.responses import JSONResponse


async def amadeus_exception_handler(request: Request, exc: ResponseError) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})
