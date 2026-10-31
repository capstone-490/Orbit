
import os 
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Header, Query
from fastapi.middleware.cors import CORSMiddleware

from app.feature_flags import get_variant
from app.logging_config import configure_logging, get_logger
from app.middleware.request_logging import RequestLoggingMiddleware
from app.routers.clients import router as clients_router
from app.routers.meetings import router as meetings_router
from security.anonymizer import TokenStore

configure_logging()
logger = get_logger("app")

@asynccontextmanager
async def lifespan(_app: FastAPI):
    TokenStore._load_secret()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(RequestLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
    expose_headers=["x-request-id"],
)

app.include_router(clients_router)
app.include_router(meetings_router)


if os.getenv("ENABLE_DEBUG_ROUTES", "").lower() in {"1", "true", "yes"}:
    from app.routers.debug import router as debug_router

    app.include_router(debug_router)
    logger.warning("Debug routes enabled; do not use in production")


def get_user_id(user_id: str | None = Header(default=None)) -> str:
    # Temporary: to be replaced with authenticated user when login is implemented.
    return user_id or "unknown"


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def health():
    return {"status": "ok"}


# Temporary endpoint for testing A/B feature flags.
@app.get("/ab-test")
def ab_test(user_id: str = Depends(get_user_id)):
    variant = get_variant("demo-ab", user_id)
    return {"Variant": variant}


@app.get("/flag")
def read_flag(
    name: str = Query(..., min_length=1, max_length=100),
    user_id: str = Depends(get_user_id),
):
    variant = get_variant(name, user_id)
    return {
        "name": name,
        "variant": variant,
        "use_new_feature": variant == "B",
    }
