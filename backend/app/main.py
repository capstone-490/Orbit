#!/usr/bin/env python3
# Below 50% AI-generated

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.v1.routers.public_booking import register_booking_exception_handlers
from app.core.config import settings
from app.health.router import health_router
from app.lifecycle.lifespan import lifespan
from app.middleware.metrics import MetricsMiddleware
from app.middleware.request_logging import RequestLoggingMiddleware
from app.observability.logging_config import configure_logging, get_logger
from app.observability.metrics import metrics_router

configure_logging()
logger = get_logger("app")


def create_application() -> FastAPI:
    """Application factory."""
    is_prod = settings.ENVIRONMENT in ("staging", "production")

    application = FastAPI(
        title="Orbit API",
        description="Orbit backend API",
        version="1.0.0",
        lifespan=lifespan,
        debug=settings.DEBUG and not is_prod,
        docs_url=None if is_prod else "/docs",
        redoc_url=None if is_prod else "/redoc",
        openapi_url=None if is_prod else "/openapi.json",
    )
    register_booking_exception_handlers(application)
    register_middleware(application)
    register_routers(application)

    return application

    del app.state.token_store


def register_middleware(application: FastAPI) -> None:
    """Register application middleware."""

    if settings.METRICS_ENABLED:
        application.add_middleware(MetricsMiddleware)

    application.add_middleware(RequestLoggingMiddleware)

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )


def register_routers(application: FastAPI) -> None:
    application.include_router(api_router)
    application.include_router(health_router)

    if settings.METRICS_ENABLED:
        application.include_router(metrics_router)

    if settings.ENABLE_DEBUG_ROUTES:
        if settings.ENVIRONMENT in ("staging", "production"):
            raise RuntimeError(
                "Debug routes cannot be enabled in staging or production"
            )

        from app.api.v1.routers.debug import router as debug_router

        application.include_router(debug_router)
        logger.warning("Debug routes enabled")


app = create_application()
