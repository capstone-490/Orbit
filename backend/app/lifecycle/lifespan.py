from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.auth import _secret
from app.core.security.anonymizer import TokenStore
from app.observability.logging_config import configure_logging, get_logger

logger = get_logger("app.lifecycle")


@asynccontextmanager
async def lifespan(
    app: FastAPI,
) -> AsyncGenerator[None]:
    configure_logging()  # Ensure Uvicorn's loggers stay after cli startup
    logger.info("Starting Orbit API")
    _secret()
    TokenStore._load_secret()
    yield
    logger.info("Shutting down Orbit API")
