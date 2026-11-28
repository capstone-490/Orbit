import pytest

from app.api.v1.routers.clients import ClientCreate
from app.core.security.anonymizer import (
    MaskingContext,
    TokenStore,
    mask_for_ai,
)


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


def test_reversible_masking_of_client_details():
    client = client_payload()
    context = MaskingContext([client])

    original = (
        "Contact Alice Smith at alice@example.com "
        "or 514-555-1234. Address: 123 Main Street."
    )

    masked = context.mask(original)

    for field in ("name", "email", "phone_number", "address"):
        assert client[field] not in masked

    assert context.restore(masked) == original


def test_masking_repeated_values_is_consistent():
    context = MaskingContext([client_payload()])

    masked = context.mask("Alice Smith and Alice Smith")

    first, second = masked.split(" and ")

    assert first == second
    assert first != "Alice Smith"


def test_masking_multiple_clients():
    alice = client_payload()
    bob = {
        "id": 43,
        "name": "Bob Jones",
        "email": "bob@example.com",
        "phone_number": "438-555-9876",
        "address": "456 Oak Avenue",
    }

    context = MaskingContext([alice, bob])

    original = {
        "first": "Contact Alice Smith at alice@example.com",
        "second": "Contact Bob Jones at bob@example.com",
    }

    masked = context.mask(original)

    assert "Alice Smith" not in repr(masked)
    assert "Bob Jones" not in repr(masked)
    assert masked["first"] != masked["second"]

    assert context.restore(masked["first"]) == original["first"]
    assert context.restore(masked["second"]) == original["second"]


@pytest.mark.parametrize(
    "phone",
    [
        "514-555-1234",
        "(514) 555-1234",
        "+1 514 555 1234",
        "5145551234",
        "514.555.1234",
    ],
)
def test_masking_different_phone_formats(phone):
    context = MaskingContext([])

    masked = context.mask(phone)

    assert phone not in masked
    assert context.restore(masked) == phone


def test_masking_nested_data_without_mutation():
    context = MaskingContext([client_payload()])

    original = {
        "notes": [
            "Contact Alice Smith",
            {"email": "alice@example.com"},
        ]
    }

    masked = context.mask(original)

    assert "Alice Smith" not in repr(masked)
    assert "alice@example.com" not in repr(masked)

    assert original["notes"][0] == "Contact Alice Smith"
    assert original["notes"][1]["email"] == "alice@example.com"


def test_placeholder_isolation_between_contexts():
    first = MaskingContext([client_payload()])
    second = MaskingContext([client_payload()])

    first_token = first.mask("Alice Smith")
    second_token = second.mask("Alice Smith")

    assert first_token != second_token
    assert second.restore(first_token) == first_token
    assert first.restore(second_token) == second_token


def test_sin_is_not_restored():
    context = MaskingContext([])

    masked = context.mask("SIN: 123-456-789")

    assert "123-456-789" not in masked
    assert context.restore(masked) == "SIN: [REDACTED]"


def test_empty_and_missing_client_details():
    context = MaskingContext([{"name": None, "email": "", "address": None}])

    assert context.mask("") == ""
    assert context.mask(None) is None
    assert context.mask("Review documents") == "Review documents"


def test_unknown_placeholder_is_not_restored():
    context = MaskingContext([client_payload()])

    context.mask("Alice Smith")

    unknown = "[NAME_unknown_999]"

    assert context.restore(unknown) == unknown


def test_name_overlapping_email_is_fully_masked():
    context = MaskingContext([{"name": "Alice"}])

    original = "Contact alice@anotherdomain.com"
    masked = context.mask(original)

    assert "alice" not in masked.lower()
    assert "anotherdomain.com" not in masked
    assert "[EMAIL_" in masked
    assert context.restore(masked) == original


def test_name_overlapping_address_is_fully_masked():
    context = MaskingContext(
        [
            {
                "name": "Alice",
                "address": "123 Alice Street",
            }
        ]
    )

    original = "Visit 123 Alice Street"
    masked = context.mask(original)

    assert "Alice" not in masked
    assert "123" not in masked
    assert "Street" not in masked
    assert context.restore(masked) == original


def test_case_insensitive_name_masking():
    context = MaskingContext([{"name": "Alice Smith"}])

    original = "Contact ALICE SMITH"
    masked = context.mask(original)

    assert "ALICE SMITH" not in masked
    assert context.restore(masked) == original


def test_detects_foreign_placeholders():
    first = MaskingContext([{"name": "Alice"}])
    second = MaskingContext([{"name": "Bob"}])

    alice_token = first.mask("Alice")
    bob_token = second.mask("Bob")

    assert not first.has_unknown_placeholders(alice_token)
    assert first.has_unknown_placeholders(bob_token)
    assert second.has_unknown_placeholders(alice_token)
