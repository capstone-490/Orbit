
import logging
import os
import smtplib
from email.message import EmailMessage

import resend

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    """Send an email using Resend or SMTP.

    Resend is preferred when RESEND_API_KEY is configured.
    SMTP is used as a fallback when Resend is not configured.
    If neither is configured, log the message for local development.
    """
    resend_api_key = os.getenv("RESEND_API_KEY")

    # Prefer Resend when an API key is available.
    if resend_api_key:
        resend.api_key = resend_api_key

        sender = os.getenv(
            "RESEND_FROM_EMAIL",
            "Orbit <onboarding@resend.dev>",
        )

        try:
            resend.Emails.send(
                {
                    "from": sender,
                    "to": [to],
                    "subject": subject,
                    "text": body,
                }
            )
            logger.info("Email accepted by Resend. Recipient: %s", to)
        except Exception:
            logger.exception("Failed to send email through Resend to %s", to)

        return

    # Use SMTP if Resend is not configured.
    host = os.getenv("SMTP_HOST")

    if host:
        message = EmailMessage()
        message["From"] = os.getenv("SMTP_FROM", "no-reply@orbit.local")
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        port = int(os.getenv("SMTP_PORT", "587"))
        username = os.getenv("SMTP_USERNAME")
        password = os.getenv("SMTP_PASSWORD")

        try:
            with smtplib.SMTP(host, port, timeout=10) as smtp:
                smtp.starttls()
                if username and password:
                    smtp.login(username, password)
                smtp.send_message(message)
        except Exception:
            logger.exception("Failed to send email through SMTP to %s", to)

        return

    # Local development fallback.
    logger.warning(
        "No email provider configured. Email to %s:\n%s\n%s",
        to,
        subject,
        body,
    )
