"""Demo-only route for the logging story. Mounted only when ENABLE_DEBUG_ROUTES=true.
Simulates a realistic bug: a handler that puts the raw request body into an
exception message. The logging pipeline must still redact it.
"""
# 50% or more AI-generated
import logging

from fastapi import APIRouter, Body

logger = logging.getLogger("app.debug")

router = APIRouter(prefix="/debug", tags=["debug"])


@router.post("/clients")
def create_client_demo(payload: dict = Body(...)):
    logger.info("Received client payload: %s", payload)
    if "name" not in payload:
        raise ValueError(f"Malformed client payload, missing 'name': {payload}")
    return {"status": "created"}