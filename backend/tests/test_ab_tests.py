# Below 50% AI-generated
from app.feature_flags import set_flag


def test_ab_test_returns_b(client):
    set_flag("demo-ab", True, 100, changed_by="test_user")
    response = client.get("/ab-test", headers={"User-ID": "user1"})
    assert response.status_code == 200
    assert response.json() == {"Variant": "B"}


def test_ab_test_returns_a(client):
    set_flag("demo-ab", True, 0, changed_by="test_user")
    response = client.get("/ab-test", headers={"User-ID": "user1"})
    assert response.status_code == 200
    assert response.json() == {"Variant": "A"}


def test_response_does_not_include_user_id(client):
    set_flag("demo-ab", True, 50, changed_by="test_user")
    response = client.get("/ab-test", headers={"User-ID": "user1"})
    assert response.status_code == 200
    assert set(response.json().keys()) == {"Variant"}


def test_same_user_id_consistency(client):
    set_flag("demo-ab", True, 50, changed_by="test_user")
    user_id = "user1"
    response1 = client.get("/ab-test", headers={"User-ID": user_id})
    response2 = client.get("/ab-test", headers={"User-ID": user_id})
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()
