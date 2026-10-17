import pytest

from security.redactor import (
    redact_data,
    redact_exception,
    redact_text,
)


@pytest.mark.parametrize(
    "value",
    [
        "client@example.com",
        "CLIENT@EXAMPLE.COM",
        "first.last+tag@example.co.uk",
        "123456789",
        "123-456-789",
        "123 456 789",
        "514-555-0198",
        "(514) 555-0198",
        "+1 514 555 0198",
    ],
)
def test_redacts_supported_pii(value):
    assert redact_text(value) == "[REDACTED]"


def test_redacts_pii_inside_sentence():
    text = "Contact client@example.com or call 514-555-0198."
    result = redact_text(text)
    assert result == "Contact [REDACTED] or call [REDACTED]."


def test_preserves_non_sensitive_text():
    text = "Client status: Active. Meeting scheduled tomorrow."
    assert redact_text(text) == text


def test_redacts_nested_dictionary():
    payload = {
        "client": {
            "email": "client@example.com",
            "phone": "514-555-0198",
            "status": "Active",
        },
        "notes": [
            "SIN: 123-456-789",
            "Follow-up required",
        ],
    }

    result = redact_data(payload)

    assert result == {
        "client": {
            "email": "[REDACTED]",
            "phone": "[REDACTED]",
            "status": "Active",
        },
        "notes": [
            "SIN: [REDACTED]",
            "Follow-up required",
        ],
    }


def test_preserves_original_payload():
    payload = {"email": "client@example.com"}
    result = redact_data(payload)
    assert payload["email"] == "client@example.com"
    assert result["email"] == "[REDACTED]"


def test_redacts_tuples():
    value = ("client@example.com", "Active")
    assert redact_data(value) == ("[REDACTED]", "Active")


def test_preserves_non_string_values():
    payload = {
        "age": 35,
        "active": True,
        "balance": 1500.50,
        "metadata": None,
    }

    assert redact_data(payload) == payload


def test_redacts_exception_traceback():
    try:
        raise ValueError("Invalid email: client@example.com")
    except ValueError as exc:
        result = redact_exception(exc)

    assert "client@example.com" not in result
    assert "[REDACTED]" in result
    assert "ValueError" in result


def test_redact_text_rejects_non_strings():
    with pytest.raises(TypeError):
        redact_text(123)


def test_redact_exception_rejects_non_exceptions():
    with pytest.raises(TypeError):
        redact_exception("Not an exception")


@pytest.mark.parametrize(
    "value",
    [
        "1234567890",  # Longer than a SIN
        "abc123456789xyz",  # SIN embedded in a word
        "123-456 789",  # Mixed SIN separators
        "client@localhost",  # Email without a public-style domain
        "123-555-0198",  # Invalid NANP area code
    ],
)
def test_does_not_redact_unsupported_or_invalid_formats(value):
    assert redact_text(value) == value


def test_redacts_multiple_pii_types():
    text = "Email: client@example.com, SIN: 123-456-789, Phone: 514-555-0198"

    result = redact_text(text)

    assert result.count("[REDACTED]") == 3
    assert "client@example.com" not in result
    assert "123-456-789" not in result
    assert "514-555-0198" not in result


def test_redacts_sensitive_dictionary_keys():
    payload = {
        "client@example.com": "contact",
        "status": "Active",
    }

    result = redact_data(payload)

    assert "[REDACTED]" in result
    assert "client@example.com" not in result
    assert result["status"] == "Active"
