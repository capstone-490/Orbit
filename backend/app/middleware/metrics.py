# Below 50% AI-generated

import time

from prometheus_client import Counter, Histogram

REQUEST_LATENCY = Histogram(
    "api_latency_seconds",
    "API request latency in seconds",
    ["method", "route", "variant"],
)

REQUESTS = Counter(
    "api_requests_total",
    "Total API requests",
    [
        "method",
        "route",
        "status_code",
        "variant",
    ],
)

ERRORS = Counter(
    "api_errors_total",
    "Total failed API requests",
    [
        "method",
        "route",
        "status_code",
        "variant",
    ],
)


class MetricsMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] in (
            "/metrics",
            # "/health",
            # "/api/v1/health",
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
            root_path = scope.get("root_path", "").rstrip("/")

            if route:
                route_template = route.path
                if root_path and not route_template.startswith(root_path):
                    route_template = f"{root_path}{route_template}"
                elif not route_template.startswith("/api/v1") and scope.get(
                    "path", ""
                ).startswith("/api/v1"):
                    route_template = f"/api/v1{route_template}"
                template = route_template
            else:
                template = "unmatched"

            state = scope.get("state", {})
            variant = state.get("ab_variant") or state.get("variant") or "none"
            method = scope["method"]

            REQUEST_LATENCY.labels(method, template, variant).observe(elapsed)
            REQUESTS.labels(method, template, str(status), variant).inc()

            if status >= 400:
                ERRORS.labels(method, template, str(status), variant).inc()
