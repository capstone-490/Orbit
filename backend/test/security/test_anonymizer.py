from datetime import date

from app.routers.clients import ClientCreate
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
    assert first["email"] != "alice@example.com"
    assert first["email"].startswith("client-")
    assert first["phone_number"].startswith("+1-514-")
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


def test_anonymized_client_passes_client_validation():
    anonymized = ClientAnonymizer(TokenStore(secret=b"test-secret")).anonymize(
        client_payload()
    )

    validated = ClientCreate(**anonymized)

    assert validated.phone_number == anonymized["phone_number"]


def test_many_clients_have_unique_fake_contacts():
    anonymizer = ClientAnonymizer(TokenStore(secret=b"test-secret"))

    results = [
        anonymizer.anonymize(
            {
                "name": f"Client {index}",
                "email": f"client-{index}@example.com",
                "phone_number": f"514-555-{index:04d}",
                "address": None,
                "date_of_birth": None,
                "occupation": None,
                "timeline": None,
            }
        )
        for index in range(100)
    ]

    assert len({client["email"] for client in results}) == len(results)
    assert len({client["phone_number"] for client in results}) == len(results)


def test_environment_secret_is_used(monkeypatch):
    monkeypatch.setenv("ORBIT_ANONYMIZATION_SECRET", "environment-secret")
    payload = client_payload()

    first = ClientAnonymizer(TokenStore()).anonymize(payload)
    second = ClientAnonymizer(TokenStore()).anonymize(payload)

    assert first == second


def test_values_remain_stable_after_cache_eviction():
    store = TokenStore(secret=b"test-secret", max_entries=1)
    anonymizer = ClientAnonymizer(store)
    original = client_payload()

    first = anonymizer.anonymize(original)
    anonymizer.anonymize({**original, "email": "other@example.com"})
    second = anonymizer.anonymize(original)

    assert first == second


def test_anonymizer_does_not_change_input():
    payload = client_payload()
    original = payload.copy()

    ClientAnonymizer(TokenStore(secret=b"test-secret")).anonymize(payload)

    assert payload == original