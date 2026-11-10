import pytest

from app.api.v1.routers.clients import ClientCreate
from app.core.security.anonymizer import TokenStore, mask_for_ai


@pytest.fixture(autouse=True)
def clear_settings_cache():
    from app.core.config import get_settings

    get_settings.cache_clear()

    yield

    get_settings.cache_clear()


def client_payload():
    return {
        "id": 42,
        "name": "Alice Smith",
        "email": "alice@example.com",
        "phone_number": "514-555-1234",
        "address": "123 Main Street",
        "age": 38,
        "occupation": "Engineer",
        "timeline": "Financial Plan",
    }


TEST_SECRET = b"test-secret-for-anonymization-32"


def test_masking_is_deterministic_for_same_id_and_secret():
    payload = client_payload()

    first = mask_for_ai(
        payload,
        TokenStore(secret=TEST_SECRET),
    )

    second = mask_for_ai(
        payload,
        TokenStore(secret=TEST_SECRET),
    )

    assert first == second


def test_masking_differs_for_different_ids():
    store = TokenStore(secret=TEST_SECRET)

    first = mask_for_ai(client_payload(), store)
    second = mask_for_ai({**client_payload(), "id": 43}, store)

    assert first["name"] != second["name"]
    assert first["email"] != second["email"]
    assert first["phone_number"] != second["phone_number"]


def test_masking_does_not_mutate_input_or_expose_pii():
    payload = client_payload()
    original = payload.copy()

    masked = mask_for_ai(payload, TokenStore(secret=TEST_SECRET))

    assert payload == original
    assert "Alice Smith" not in repr(masked)
    assert "alice@example.com" not in repr(masked)
    assert "123 Main Street" not in repr(masked)
    assert "Engineer" not in repr(masked)
    assert masked["age"] == 38
    assert masked["timeline"] == "Financial Plan"


def test_masked_phone_passes_client_validation():
    masked = mask_for_ai(client_payload(), TokenStore(secret=TEST_SECRET))

    validated = ClientCreate(
        name=masked["name"],
        email=masked["email"],
        phone_number=masked["phone_number"],
    )

    assert validated.phone_number == masked["phone_number"]


def test_empty_optional_values_are_none():
    payload = {**client_payload(), "address": "", "occupation": None}

    masked = mask_for_ai(payload, TokenStore(secret=TEST_SECRET))

    assert masked["address"] is None
    assert masked["occupation"] is None


def test_valid_environment_secret_allows_token_store(monkeypatch):
    monkeypatch.setenv(
        "ORBIT_ANONYMIZATION_SECRET",
        "valid-anonymization-secret-with-32-chars",
    )

    assert TokenStore()._secret


def test_masking_requires_stable_client_id():
    with pytest.raises(ValueError, match="stable id"):
        mask_for_ai(
            {"name": "Alice Smith"},
            TokenStore(secret=TEST_SECRET),
        )
