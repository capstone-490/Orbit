import pytest
from faker import Faker

from security.redactor import redact_data

@pytest.fixture
def fake():
    """Create a reproducible Canadian Faker instance."""
    generator = Faker("en_CA")
    generator.seed_instance(42)
    return generator


def test_redaction_with_100_fake_clients(fake):
    total_clients = 1000
    passed = 0

    for _ in range(total_clients):
        # 1. Generate fake client information
        email = fake.email()
        phone = f"514-555-{fake.random_int(1000, 9999)}"
        sin = (
            f"{fake.random_int(100, 999)}-"
            f"{fake.random_int(100, 999)}-"
            f"{fake.random_int(100, 999)}"
        )

        client = {
            "name": fake.name(),
            "email": email,
            "phone": phone,
            "sin": sin,
            "notes": f"Contact {email} for follow-up.",
        }

        # 2. Pass the client through redactor
        result = redact_data(client)

        # 3. Check to verify that all PII fields have been redacted
        success = (
            result["email"] == "[REDACTED]"
            and result["phone"] == "[REDACTED]"
            and result["sin"] == "[REDACTED]"
            and result["notes"] == "Contact [REDACTED] for follow-up."
        )

        if success:
            passed += 1

    # 4. Display the results
    print(f"\nClients tested: {total_clients}")
    print(f"Clients successfully redacted: {passed}")
    print(f"Success rate: {passed / total_clients * 100:.1f}%")

    # 5. Fail the test if any client was not redacted
    assert passed == total_clients

