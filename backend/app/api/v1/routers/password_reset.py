import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, Field

from app.core.config import settings
from app.dependencies.db import get_connection
from app.security.passwords import hash_password
from app.services.email import send_email

router = APIRouter(prefix="/auth", tags=["Authentication"])

RESET_TOKEN_TTL_MINUTES = 30

GENERIC_FORGOT_MESSAGE = (
    "If an account exists for that email, a password reset link has been sent."
)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=12, max_length=128)


class MessageResponse(BaseModel):
    message: str


@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest):
    email = str(payload.email).lower()
    email_details = None

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, username FROM t_advisors WHERE email = %s", (email,))
        advisor = cur.fetchone()

        if advisor is not None:
            advisor_id, username = advisor

            # Invalidate any earlier outstanding links for this advisor.
            cur.execute(
                """
                UPDATE password_reset_tokens
                SET used_at = now()
                WHERE advisor_id = %s AND used_at IS NULL
                """,
                (advisor_id,),
            )

            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(UTC) + timedelta(minutes=RESET_TOKEN_TTL_MINUTES)

            cur.execute(
                """
                INSERT INTO password_reset_tokens (advisor_id, token_hash, expires_at)
                VALUES (%s, %s, %s)
                """,
                (advisor_id, _hash_token(token), expires_at),
            )

            reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

            email_details = {
                "to": email,
                "subject": "Reset your Orbit password",
                "body": (
                    f"Hi {username},\n\n"
                    "We received a request to reset your Orbit password. "
                    f"Use the link below within {RESET_TOKEN_TTL_MINUTES} minutes:\n\n"
                    f"{reset_link}\n\n"
                    "If you did not request this, you can safely ignore this email."
                ),
            }

    # Send the email only after the database transaction has completed.
    if email_details is not None:
        send_email(**email_details)

    return {"message": GENERIC_FORGOT_MESSAGE}


@router.get("/reset-password/validate", response_model=MessageResponse)
def validate_reset_token(token: str):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM password_reset_tokens
            WHERE token_hash = %s AND used_at IS NULL AND expires_at > now()
            """,
            (_hash_token(token),),
        )
        if cur.fetchone() is None:
            raise HTTPException(
                status_code=400,
                detail="This reset link is invalid or has expired.",
            )

    return {"message": "Token is valid."}


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest):
    token_hash = _hash_token(payload.token)
    password_hash = hash_password(payload.password)

    with get_connection() as conn, conn.cursor() as cur:
        # Atomically consume the token so it can only be used once.
        cur.execute(
            """
            UPDATE password_reset_tokens
            SET used_at = now()
            WHERE token_hash = %s AND used_at IS NULL AND expires_at > now()
            RETURNING advisor_id
            """,
            (token_hash,),
        )
        row = cur.fetchone()

        if row is None:
            raise HTTPException(
                status_code=400,
                detail="This reset link is invalid or has expired.",
            )

        cur.execute(
            "UPDATE t_advisors SET password_hash = %s WHERE id = %s",
            (password_hash, row[0]),
        )

    return {"message": "Your password has been reset. You can now sign in."}
