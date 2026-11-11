# Below 50% AI-generated
import pytest

from app.core.feature_flags import set_flag


@pytest.mark.parametrize(
    ("rollout_percent", "expected_variant"),
    [
        pytest.param(100, "B", id="full-rollout"),
        pytest.param(0, "A", id="zero-rollout"),
    ],
)
def test_ab_test_returns_expected_variant(
    client,
    user_headers,
    rollout_percent,
    expected_variant,
):
    set_flag(
        "demo-ab",
        True,
        rollout_percent,
        changed_by="test_user",
    )

    response = client.get(
        "/feature-flags/ab-test",
        headers=user_headers,
    )

    assert response.status_code == 200
    assert response.json() == {"Variant": expected_variant}


def test_ab_test_response_does_not_expose_user_id(
    client,
    user_headers,
):
    set_flag(
        "demo-ab",
        True,
        50,
        changed_by="test_user",
    )
    response = client.get(
        "/feature-flags/ab-test",
        headers=user_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"Variant"}
    assert data["Variant"] in {"A", "B"}


def test_same_user_receives_consistent_variant(
    client,
    user_headers,
):
    set_flag(
        "demo-ab",
        True,
        50,
        changed_by="test_user",
    )

    first_response = client.get(
        "/feature-flags/ab-test",
        headers=user_headers,
    )
    second_response = client.get(
        "/feature-flags/ab-test",
        headers=user_headers,
    )
    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_response.json() == second_response.json()


def test_read_named_feature_flag(
    client,
    user_headers,
):
    set_flag(
        "new-dashboard",
        True,
        100,
        changed_by="test_user",
    )

    response = client.get(
        "/feature-flags/new-dashboard",
        headers=user_headers,
    )

    assert response.status_code == 200

    assert response.json() == {
        "name": "new-dashboard",
        "variant": "B",
        "use_new_feature": True,
    }
