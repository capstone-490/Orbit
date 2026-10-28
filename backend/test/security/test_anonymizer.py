from datetime import date

import pytest
from fastapi.testclient import TestClient

from app.main import app
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

    first = anonymizer.anonymize(client_payload(), client_key="client-1")
    second = anonymizer.anonymize(client_payload(), client_key="client-1")

    assert first == second
    assert first["name"] != "Alice Smith"
    assert first["email"] != "alice@example.com"
    assert first["email"].startswith("client-")
    assert first["phone_number"].startswith("+1-555-")
    assert first["age"] == date.today().year - 1988 - (
        (date.today().month, date.today().day) < (4, 12)
    )
    assert "date_of_birth" not in first
    assert "Alice Smith" not in repr(store.__dict__)
    assert "alice@example.com" not in repr(store.__dict__)


def test_anonymizer_preserves_non_pii_classification_fields():
    result = ClientAnonymizer(TokenStore(secret=b"test-secret")).anonymize(
        client_payload(), client_key="client-1"
    )

    assert result["timeline"] == "Financial Plan"


def test_anonymizer_is_deterministic_across_instances_with_same_secret():
    payload = client_payload()

    first = ClientAnonymizer(TokenStore(secret=b"stable-secret")).anonymize(
        payload, client_key="client-1"
    )
    second = ClientAnonymizer(TokenStore(secret=b"stable-secret")).anonymize(
        payload, client_key="client-1"
    )

    assert first == second


def test_anonymized_client_passes_client_validation():
    anonymized = ClientAnonymizer(TokenStore(secret=b"test-secret")).anonymize(
        client_payload(), client_key="client-1"
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
            },
            client_key=f"client-{index}",
        )
        for index in range(100)
    ]

    assert len({client["email"] for client in results}) == len(results)
    assert len({client["phone_number"] for client in results}) == len(results)


def test_environment_secret_is_used(monkeypatch):
    monkeypatch.setenv(
        "ORBIT_ANONYMIZATION_SECRET",
        "environment-secret-with-at-least-32-chars",
    )
    payload = client_payload()

    first = ClientAnonymizer(TokenStore()).anonymize(payload, client_key="client-1")
    second = ClientAnonymizer(TokenStore()).anonymize(payload, client_key="client-1")

    assert first == second


@pytest.mark.parametrize(
    "configured",
    [None, "", " " * 32, "short"],
)
def test_missing_or_invalid_environment_secret_is_rejected(monkeypatch, configured):
    if configured is None:
        monkeypatch.delenv("ORBIT_ANONYMIZATION_SECRET", raising=False)
    else:
        monkeypatch.setenv("ORBIT_ANONYMIZATION_SECRET", configured)

    with pytest.raises(RuntimeError, match="ORBIT_ANONYMIZATION_SECRET"):
        TokenStore()


def test_valid_environment_secret_allows_startup(monkeypatch):
    monkeypatch.setenv(
        "ORBIT_ANONYMIZATION_SECRET",
        "valid-anonymization-secret-with-32-chars",
    )

    assert TokenStore()._secret


@pytest.mark.parametrize("configured", [None, "", " " * 32, "short"])
def test_application_refuses_invalid_anonymization_secret(monkeypatch, configured):
    if configured is None:
        monkeypatch.delenv("ORBIT_ANONYMIZATION_SECRET", raising=False)
    else:
        monkeypatch.setenv("ORBIT_ANONYMIZATION_SECRET", configured)

    with (
        pytest.raises(RuntimeError, match="ORBIT_ANONYMIZATION_SECRET"),
        TestClient(app),
    ):
        pass


def test_fields_share_stable_client_identity_and_do_not_store_pii():
    payload = client_payload()
    first = ClientAnonymizer(TokenStore(secret=b"test-secret")).anonymize(
        payload, client_key="client-1"
    )
    second = ClientAnonymizer(TokenStore(secret=b"test-secret")).anonymize(
        payload, client_key="client-1"
    )
    other = ClientAnonymizer(TokenStore(secret=b"test-secret")).anonymize(
        payload, client_key="client-2"
    )

    assert first == second
    assert first["anonymized_client_id"] == "client-1"
    assert first["name"] != other["name"]
    assert first["email"] != other["email"]
    assert first["phone_number"] != other["phone_number"]
    assert first["address"] != other["address"]
    assert first["occupation"] != other["occupation"]
    assert "Alice Smith" not in repr(first)
    assert "alice@example.com" not in repr(first)


def test_values_remain_stable_after_cache_eviction():
    store = TokenStore(secret=b"test-secret", max_entries=1)
    anonymizer = ClientAnonymizer(store)
    original = client_payload()

    first = anonymizer.anonymize(original, client_key="client-1")
    anonymizer.anonymize(
        {**original, "email": "other@example.com"}, client_key="client-2"
    )
    second = anonymizer.anonymize(original, client_key="client-1")

    assert first == second


def test_anonymizer_does_not_change_input():
    payload = client_payload()
    original = payload.copy()

    ClientAnonymizer(TokenStore(secret=b"test-secret")).anonymize(
        payload, client_key="client-1"
    )

    assert payload == original
