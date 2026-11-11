import logging
import smtplib
from email.message import EmailMessage

import resend

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    """Send an email using Resend or SMTP.

    Resend is preferred when RESEND_API_KEY is configured.
    SMTP is used as a fallback when Resend is not configured.
    If neither is configured, log the message for local development.
    """
    # Prefer Resend when an API key is available.
    if settings.RESEND_API_KEY:
        resend.api_key = settings.RESEND_API_KEY

        try:
            resend.Emails.send(
                {
                    "from": settings.RESEND_FROM_EMAIL,
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
    if settings.SMTP_HOST:
        message = EmailMessage()
        message["From"] = settings.SMTP_FROM
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        try:
            with smtplib.SMTP(
                settings.SMTP_HOST,
                settings.SMTP_PORT,
                timeout=10,
            ) as smtp:
                smtp.starttls()
                if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                    smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
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
