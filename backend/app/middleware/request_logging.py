"""Per-request logging + x-request-id.
For every HTTP request this middleware:
  1. reuses a valid incoming ``x-request-id`` UUID, or generates a new uuid4;
  2. stores it in a context variable, so every log line during the request has it;
  3. adds ``x-request-id`` to the response headers;
  4. logs one line when the request finishes: method, path, status code, duration;
  5. catches any unhandled exception, logs it (redacted) and returns a generic 500.

Query strings, headers and bodies are deliberately NOT logged; they are where
client PII usually lives.
"""

# 50% or more AI-generated
from __future__ import annotations

import json
import logging
import time
import uuid

from app.logging_config import request_id_var

logger = logging.getLogger("app.http")

REQUEST_ID_HEADER = "x-request-id"


def _valid_uuid(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return str(uuid.UUID(value))
    except ValueError:
        return None


class RequestLoggingMiddleware:
    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            k.decode("latin-1").lower(): v.decode("latin-1")
            for k, v in scope["headers"]
        }
        request_id = _valid_uuid(headers.get(REQUEST_ID_HEADER)) or str(uuid.uuid4())
        token = request_id_var.set(request_id)

        status_code = 500
        response_started = False
        start = time.perf_counter()

        async def send_with_request_id(message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                message.setdefault("headers", [])
                message["headers"] = [
                    (k, v)
                    for k, v in message["headers"]
                    if k.lower() != REQUEST_ID_HEADER.encode()
                ] + [(REQUEST_ID_HEADER.encode(), request_id.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception:
            status_code = 500
            logger.exception(
                "Unhandled exception while processing request",
                extra={"method": scope["method"], "path": scope["path"]},
            )
            if not response_started:
                body = json.dumps(
                    {"detail": "Internal Server Error", "request_id": request_id}
                ).encode()
                await send(
                    {
                        "type": "http.response.start",
                        "status": 500,
                        "headers": [
                            (b"content-type", b"application/json"),
                            (b"content-length", str(len(body)).encode()),
                            (REQUEST_ID_HEADER.encode(), request_id.encode()),
                        ],
                    }
                )
                await send({"type": "http.response.body", "body": body})
            # Not re-raised: re-raising makes Uvicorn print the raw traceback.
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            level = (
                logging.ERROR
                if status_code >= 500
                else logging.WARNING
                if status_code >= 400
                else logging.INFO
            )
            logger.log(
                level,
                "Request completed",
                extra={
                    "method": scope["method"],
                    "path": scope["path"],  # no query string on purpose
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                },
            )
            request_id_var.reset(token)
