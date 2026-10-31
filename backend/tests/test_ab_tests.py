# Below 50% AI-generated
import pytest

from app.core.feature_flags import set_flag


@pytest.mark.parametrize(
    ("rollout_percent", "expected_variant"),
    [
        (100, "B"),
        (0, "A"),
    ],
    ids=["full-rollout", "zero-rollout"],
)
def test_ab_test_returns_expected_variant(
    client,
    rollout_percent: int,
    expected_variant: str,
) -> None:
    set_flag(
        "demo-ab",
        True,
        rollout_percent,
        changed_by="test_user",
    )

    response = client.get(
        "/ab-test",
        headers={"User-ID": "user1"},
    )

    assert response.status_code == 200
    assert response.json() == {"Variant": expected_variant}


def test_ab_test_response_excludes_user_id(client) -> None:
    set_flag("demo-ab", True, 50, changed_by="test_user")
    response = client.get("/ab-test", headers={"User-ID": "user1"})
    assert response.status_code == 200
    assert response.json() == {"Variant": response.json()["Variant"]}
    assert set(response.json()) == {"Variant"}


def test_same_user_receives_consistent_variant(client) -> None:
    set_flag("demo-ab", True, 50, changed_by="test_user")
    headers = {"User-ID": "user1"}
    response1 = client.get("/ab-test", headers=headers)
    response2 = client.get("/ab-test", headers=headers)
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response1.json() == response2.json()
