from fastapi.testclient import TestClient

from app.api.v1.routers import feature_flags
from app.main import app

base_client = TestClient(app)


def test_root_returns_hello():
    response = base_client.get("/")

    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_health_returns_ok():
    response = base_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ab_test_uses_provided_user_id(client, monkeypatch):
    seen = {}

    def fake_get_variant(name, user_id):
        seen.update(name=name, user_id=user_id)
        return "B"

    monkeypatch.setattr(
        feature_flags,
        "get_variant",
        fake_get_variant,
    )

    response = client.get("/feature-flags/ab-test", headers={"User-ID": "advisor-7"})

    assert response.status_code == 200
    assert response.json() == {"Variant": "B"}
    assert seen == {"name": "demo-ab", "user_id": "advisor-7"}


def test_ab_test_defaults_missing_user_id(client, monkeypatch):
    seen = {}

    def fake_get_variant(name, user_id):
        seen["user_id"] = user_id
        return "A"

    monkeypatch.setattr(
        feature_flags,
        "get_variant",
        fake_get_variant,
    )

    response = client.get(
        "/feature-flags/ab-test",
    )

    assert response.status_code == 200
    assert seen["user_id"] == "unknown"


def test_flag_returns_variant_and_boolean(client, monkeypatch):
    seen = {}

    def fake_get_variant(name, user_id):
        seen.update(name=name, user_id=user_id)
        return "B"

    monkeypatch.setattr(
        feature_flags,
        "get_variant",
        fake_get_variant,
    )

    response = client.get("/feature-flags/demo", headers={"User-ID": "advisor-7"})

    assert response.status_code == 200
    assert seen == {"name": "demo", "user_id": "advisor-7"}
    assert response.json() == {
        "name": "demo",
        "variant": "B",
        "use_new_feature": True,
    }


def test_flag_requires_nonempty_name(client):
    response = client.get("/feature-flags/")

    assert response.status_code == 422


def test_cors_allows_frontend_origin(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "PATCH" in response.headers["access-control-allow-methods"]
