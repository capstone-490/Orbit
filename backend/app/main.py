#!/usr/bin/env python3
# No substantial AI-generated code
from fastapi import Depends, FastAPI, Header, Query
from fastapi.middleware.cors import CORSMiddleware

from app.feature_flags import get_variant
from app.routers.sessions import router as sessions_router
from app.routers.clients import router as clients_router
from app.routers.meetings import router as meetings_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(sessions_router)
app.include_router(clients_router)
app.include_router(meetings_router)


def get_user_id(user_id: str | None = Header(default=None)) -> str:
    # Temporary: to be replaced with authenticated user when login is implemented.
    return user_id or "unknown"


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def health():
    return {"status": "ok"}


# Temporary endpoint for testing A/B feature flags. Add flag check to feature endpoint when needed.
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
