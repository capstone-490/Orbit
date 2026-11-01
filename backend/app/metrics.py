#  Below 50% AI-generated
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
