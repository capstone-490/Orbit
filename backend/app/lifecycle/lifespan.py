from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth import _secret
from app.core.config import settings
from app.core.security.anonymizer import TokenStore
from app.infrastructure.database import build_async_engine, build_session_factory
from app.observability.logging_config import configure_logging, get_logger

logger = get_logger("app.lifecycle")


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncGenerator[None]:
    configure_logging()
    logger.info("Starting Orbit API")
    _secret()
    TokenStore._load_secret()

    engine = build_async_engine(
        settings.sqlalchemy_database_uri,
        echo=False,
        pool_size=getattr(settings, "DB_POOL_SIZE", 10),
        max_overflow=getattr(settings, "DB_MAX_OVERFLOW", 20),
    )
    session_factory = build_session_factory(engine)

    app.state.db_engine = engine
    app.state.session_factory = session_factory

    try:
        yield
    finally:
        logger.info("Shutting down Orbit API and closing DB pool")
        await engine.dispose()
