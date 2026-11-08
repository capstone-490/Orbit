
"""Tests for the email delivery service."""

from unittest.mock import MagicMock

import pytest

from app.services import email as email_service


@pytest.fixture
def email_settings(monkeypatch):
    """Reset email settings before each test."""
    monkeypatch.setattr(email_service.settings, "RESEND_API_KEY", None)
    monkeypatch.setattr(
        email_service.settings,
        "RESEND_FROM_EMAIL",
        "Orbit <test@example.com>",
    )
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", None)
    monkeypatch.setattr(email_service.settings, "SMTP_PORT", 587)
    monkeypatch.setattr(
        email_service.settings, "SMTP_FROM", "no-reply@example.com"
    )
    monkeypatch.setattr(email_service.settings, "SMTP_USERNAME", None)
    monkeypatch.setattr(email_service.settings, "SMTP_PASSWORD", None)


def test_send_email_uses_resend(email_settings, monkeypatch):
    monkeypatch.setattr(email_service.settings, "RESEND_API_KEY", "test-key")
    send = MagicMock()
    monkeypatch.setattr(email_service.resend.Emails, "send", send)

    email_service.send_email("user@example.com", "Subject", "Body")

    assert email_service.resend.api_key == "test-key"
    send.assert_called_once_with(
        {
            "from": "Orbit <test@example.com>",
            "to": ["user@example.com"],
            "subject": "Subject",
            "text": "Body",
        }
    )


def test_send_email_logs_resend_success(email_settings, monkeypatch, caplog):
    monkeypatch.setattr(email_service.settings, "RESEND_API_KEY", "test-key")
    monkeypatch.setattr(
        email_service.resend.Emails, "send", MagicMock()
    )

    with caplog.at_level("INFO"):
        email_service.send_email("user@example.com", "Subject", "Body")

    assert "Email accepted by Resend" in caplog.text


def test_send_email_handles_resend_failure(
    email_settings, monkeypatch, caplog
):
    monkeypatch.setattr(email_service.settings, "RESEND_API_KEY", "test-key")
    send = MagicMock(side_effect=RuntimeError("Resend unavailable"))
    monkeypatch.setattr(email_service.resend.Emails, "send", send)

    with caplog.at_level("ERROR"):
        email_service.send_email("user@example.com", "Subject", "Body")

    assert "Failed to send email through Resend" in caplog.text


def test_send_email_uses_smtp_with_authentication(
    email_settings, monkeypatch
):
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "smtp.example.com")
    monkeypatch.setattr(email_service.settings, "SMTP_USERNAME", "test-user")
    monkeypatch.setattr(email_service.settings, "SMTP_PASSWORD", "test-password")

    smtp = MagicMock()
    smtp_context = MagicMock()
    smtp.__enter__.return_value = smtp_context

    smtp_constructor = MagicMock(return_value=smtp)
    monkeypatch.setattr(email_service.smtplib, "SMTP", smtp_constructor)

    email_service.send_email("user@example.com", "Subject", "Body")

    smtp_constructor.assert_called_once_with(
        "smtp.example.com", 587, timeout=10
    )
    smtp_context.starttls.assert_called_once()
    smtp_context.login.assert_called_once_with("test-user", "test-password")
    smtp_context.send_message.assert_called_once()

    message = smtp_context.send_message.call_args.args[0]
    assert message["To"] == "user@example.com"
    assert message["Subject"] == "Subject"
    assert message.get_content().strip() == "Body"


def test_send_email_uses_smtp_without_authentication(
    email_settings, monkeypatch
):
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "smtp.example.com")

    smtp = MagicMock()
    smtp_context = MagicMock()
    smtp.__enter__.return_value = smtp_context

    monkeypatch.setattr(
        email_service.smtplib, "SMTP", MagicMock(return_value=smtp)
    )

    email_service.send_email("user@example.com", "Subject", "Body")

    smtp_context.starttls.assert_called_once()
    smtp_context.login.assert_not_called()
    smtp_context.send_message.assert_called_once()


def test_send_email_handles_smtp_failure(
    email_settings, monkeypatch, caplog
):
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "smtp.example.com")

    smtp = MagicMock()
    smtp.__enter__.side_effect = RuntimeError("SMTP unavailable")

    monkeypatch.setattr(
        email_service.smtplib, "SMTP", MagicMock(return_value=smtp)
    )

    with caplog.at_level("ERROR"):
        email_service.send_email("user@example.com", "Subject", "Body")

    assert "Failed to send email through SMTP" in caplog.text


def test_send_email_uses_local_fallback(email_settings, caplog):
    with caplog.at_level("WARNING"):
        email_service.send_email("user@example.com", "Subject", "Body")

    assert "No email provider configured" in caplog.text
    assert "user@example.com" in caplog.text
    assert "Subject" in caplog.text
    assert "Body" in caplog.text


def test_send_email_prefers_resend_over_smtp(
    email_settings, monkeypatch
):
    monkeypatch.setattr(email_service.settings, "RESEND_API_KEY", "test-key")
    monkeypatch.setattr(email_service.settings, "SMTP_HOST", "smtp.example.com")

    resend_send = MagicMock()
    smtp_constructor = MagicMock()

    monkeypatch.setattr(email_service.resend.Emails, "send", resend_send)
    monkeypatch.setattr(email_service.smtplib, "SMTP", smtp_constructor)

    email_service.send_email("user@example.com", "Subject", "Body")

    resend_send.assert_called_once()
    smtp_constructor.assert_not_called()
