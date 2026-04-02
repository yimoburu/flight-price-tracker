from contextlib import asynccontextmanager

from amadeus import ResponseError
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models.tracked_search  # noqa: F401 — registers models with Base metadata
from app.api.error_handlers import amadeus_exception_handler
from app.api.search import router as search_router
from app.api.tracking import router as tracking_router
from app.config import get_settings
from app.db import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db import Base
    from app.services.scheduler import create_scheduler

    Base.metadata.create_all(bind=engine)
    scheduler = create_scheduler()
    scheduler.start()
    app.state.scheduler = scheduler
    yield
    scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="Flight Price Tracker",
        version="0.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    application.include_router(search_router)
    application.include_router(tracking_router)
    application.add_exception_handler(ResponseError, amadeus_exception_handler)
    return application


app = create_app()
