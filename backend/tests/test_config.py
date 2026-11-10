import pytest

from app.core.config import Settings


def test_anonymization_secret_must_be_at_least_32_bytes():
    with pytest.raises(ValueError):
        Settings(
            DB_USER="test",
            DB_PASSWORD="test",
            DB_NAME="test",
            POSTGRES_PASSWORD="test",
            ORBIT_ANONYMIZATION_SECRET="short",
        )


def test_anonymization_secret_accepts_valid_value():
    settings = Settings(
        DB_USER="test",
        DB_PASSWORD="test",
        DB_NAME="test",
        POSTGRES_PASSWORD="test",
        ORBIT_ANONYMIZATION_SECRET="a" * 32,
    )

    assert settings.ORBIT_ANONYMIZATION_SECRET == "a" * 32
