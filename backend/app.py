"""FastAPI application factory for ORION."""

from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import __version__
from backend.api.routes import router as api_router
from backend.core.config import get_settings
from backend.core.database import init_db
from backend.core.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize logging and database on startup."""
    settings = get_settings()
    configure_logging(settings.log_level)
    logger = get_logger("app")
    init_db(settings)
    logger.info(
        "orion started",
        extra={
            "version": __version__,
            "demo_mode": settings.demo_mode,
            "paper_trading": settings.alpaca_paper_trade,
        },
    )
    yield
    logger.info("orion stopped")


def create_app() -> FastAPI:
    """Build and configure the ORION FastAPI application."""
    app = FastAPI(
        title="ORION — Autonomous Options Alpha Agent",
        description="The agent that has to prove its trade.",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)
    return app


app = create_app()
