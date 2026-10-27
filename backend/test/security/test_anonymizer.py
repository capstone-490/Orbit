from datetime import date

from security.anonymizer import ClientAnonymizer, TokenStore


def client_payload():
    return {
        "name": "Alice Smith",
        "email": "alice@example.com",
        "phone_number": "514-555-1234",
        "address": "123 Main Street",
        "date_of_birth": date(1988, 4, 12),
        "occupation": "Engineer",
        "timeline": "Financial Plan",
    }


def test_anonymizer_is_deterministic_without_retaining_raw_values():
    store = TokenStore(secret=b"test-secret")
    anonymizer = ClientAnonymizer(store)

    first = anonymizer.anonymize(client_payload())
    second = anonymizer.anonymize(client_payload())

    assert first == second
    assert first["name"] != "Alice Smith"
    assert first["email"].endswith("@invalid.test")
    assert first["phone_number"].startswith("+1-555-555-")
    assert first["date_of_birth"] != date(1988, 4, 12)
    assert "Alice Smith" not in repr(store.__dict__)
    assert "alice@example.com" not in repr(store.__dict__)


def test_anonymizer_preserves_non_pii_classification_fields():
    result = ClientAnonymizer(TokenStore(secret=b"test-secret")).anonymize(
        client_payload()
    )

    assert result["timeline"] == "Financial Plan"


def test_anonymizer_is_deterministic_across_instances_with_same_secret():
    payload = client_payload()

    first = ClientAnonymizer(TokenStore(secret=b"stable-secret")).anonymize(payload)
    second = ClientAnonymizer(TokenStore(secret=b"stable-secret")).anonymize(payload)

    assert first == second


def test_anonymizer_does_not_change_input():
    payload = client_payload()
    original = payload.copy()

    ClientAnonymizer(TokenStore(secret=b"test-secret")).anonymize(payload)

    assert payload == original