# 50% or more AI-generated
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY, generate_latest

from app.auth import create_access_token
from app.main import app

client = TestClient(app)


def count(route, status="200", method="GET", variant="none"):
    return (
        REGISTRY.get_sample_value(
            "api_requests_total",
            {
                "method": method,
                "route": route,
                "status_code": status,
                "variant": variant,
            },
        )
        or 0
    )


def test_request_counter_increments_by_n():
    n = 5
    before = count("/health")
    for _ in range(n):
        client.get("/health")
    after = count("/health")
    assert after - before == n


def api_metrics_text():
    lines = generate_latest().decode().splitlines()
    return "\n".join(ln for ln in lines if ln.startswith("api_"))


def test_no_pii_in_labels():
    # Use an advisor id  to test the dynamic route
    access_token = create_access_token(123456)
    response = client.get(
        "/api/v1/meetings/123456?email=secret@example.com",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    text = api_metrics_text()
    assert response.status_code == 200
    assert 'route="/api/v1/meetings/{advisor_id}"' in text
    assert "123456" not in text
    assert "secret@example.com" not in text


def test_ab_route_has_variant_label():
    response = client.get("/api/v1/feature-flags/ab-test")
    assert response.status_code == 200

    variant = response.json()["Variant"]
    assert variant in ("A", "B")

    assert count("/api/v1/feature-flags/ab-test", variant=variant) >= 1


def test_metrics_endpoint_is_not_counted():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert 'route="/api/v1/metrics"' not in api_metrics_text()


def test_latency_histogram_records_requests():
    labels = {"method": "GET", "route": "/health", "variant": "none"}
    before = REGISTRY.get_sample_value("api_latency_seconds_count", labels) or 0
    client.get("/health")
    after = REGISTRY.get_sample_value("api_latency_seconds_count", labels) or 0
    assert after - before == 1


def test_unknown_routes_count_as_error():
    labels = {
        "method": "GET",
        "route": "unmatched",
        "status_code": "404",
        "variant": "none",
    }
    before = REGISTRY.get_sample_value("api_errors_total", labels) or 0
    client.get("/does-not-exist-123456")
    after = REGISTRY.get_sample_value("api_errors_total", labels) or 0
    assert after - before == 1
    assert "does-not-exist-123456" not in api_metrics_text()


def test_metrics_endpoint_exposes_api_metrics():
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "api_requests_total" in response.text
