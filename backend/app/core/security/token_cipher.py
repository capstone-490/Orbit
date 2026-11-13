"""Encrypt OAuth tokens before they are stored in the database."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

__all__ = ["InvalidToken", "decrypt_token", "encrypt_token"]


def encrypt_token(plaintext: str, key: str | None = None) -> str:
    return _fernet(key).encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str, key: str | None = None) -> str:
    """Raises InvalidToken if the value was encrypted with a different key."""
    return _fernet(key).decrypt(ciphertext.encode()).decode()


def _fernet(key: str | None) -> Fernet:
    return Fernet(key or settings.GOOGLE_TOKEN_ENCRYPTION_KEY)
