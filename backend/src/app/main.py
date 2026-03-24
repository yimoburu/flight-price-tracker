from amadeus import ResponseError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.error_handlers import amadeus_exception_handler
from app.api.search import router as search_router
from app.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title="Flight Price Tracker", version="0.1.0")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    application.include_router(search_router)
    application.add_exception_handler(ResponseError, amadeus_exception_handler)
    return application


app = create_app()
