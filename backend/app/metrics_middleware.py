# Below 50% AI-generated

import time

from app.metrics import ERRORS, REQUEST_LATENCY, REQUESTS


class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] in (
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc",
        ):
            await self.app(scope, receive, send)
            return
        start = time.perf_counter()
        status = 500

        async def send_wrapper(message):
            nonlocal status

            if message["type"] == "http.response.start":
                status = message["status"]

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed = time.perf_counter() - start

            route = scope.get("route")
            template = route.path if route else "unmatched"

            variant = scope.get("state", {}).get("ab_variant", "none")
            method = scope["method"]

            REQUEST_LATENCY.labels(method, template, variant).observe(elapsed)

            REQUESTS.labels(method, template, str(status), variant).inc()

            if status >= 400:
                ERRORS.labels(method, template, str(status), variant).inc()
