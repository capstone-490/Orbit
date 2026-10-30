from fastapi.testclient import TestClient

from app import main
from app.main import app

client = TestClient(app)


def test_root_returns_hello():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ab_test_uses_provided_user_id(monkeypatch):
    seen = {}

    def fake_get_variant(name, user_id):
        seen.update(name=name, user_id=user_id)
        return "B"

    monkeypatch.setattr(main, "get_variant", fake_get_variant)

    response = client.get("/ab-test", headers={"User-ID": "advisor-7"})

    assert response.status_code == 200
    assert response.json() == {"Variant": "B"}
    assert seen == {"name": "demo-ab", "user_id": "advisor-7"}


def test_ab_test_defaults_missing_user_id(monkeypatch):
    monkeypatch.setattr(main, "get_variant", lambda name, user_id: user_id)

    response = client.get("/ab-test")

    assert response.status_code == 200
    assert response.json() == {"Variant": "unknown"}


def test_flag_returns_variant_and_boolean(monkeypatch):
    seen = {}

    def fake_get_variant(name, user_id):
        seen.update(name=name, user_id=user_id)
        return "B"

    monkeypatch.setattr(main, "get_variant", fake_get_variant)

    response = client.get("/flag?name=demo", headers={"User-ID": "advisor-7"})

    assert response.status_code == 200
    assert seen == {"name": "demo", "user_id": "advisor-7"}
    assert response.json() == {
        "name": "demo",
        "variant": "B",
        "use_new_feature": True,
    }


def test_flag_requires_nonempty_name():
    response = client.get("/flag?name=")

    assert response.status_code == 422


def test_cors_allows_frontend_origin():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
