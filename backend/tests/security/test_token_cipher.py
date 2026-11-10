import pytest
from cryptography.fernet import Fernet

from app.core.security.token_cipher import InvalidToken, decrypt_token, encrypt_token

TOKEN_JSON = '{"token": "ya29.secret", "refresh_token": "1//refresh"}'


def test_round_trip():
    assert decrypt_token(encrypt_token(TOKEN_JSON)) == TOKEN_JSON


def test_ciphertext_does_not_contain_the_token():
    ciphertext = encrypt_token(TOKEN_JSON)

    assert "ya29.secret" not in ciphertext
    assert "refresh" not in ciphertext


def test_same_token_encrypts_differently_each_time():
    assert encrypt_token(TOKEN_JSON) != encrypt_token(TOKEN_JSON)


def test_wrong_key_is_rejected():
    ciphertext = encrypt_token(TOKEN_JSON, key=Fernet.generate_key().decode())

    with pytest.raises(InvalidToken):
        decrypt_token(ciphertext)


def test_tampered_ciphertext_is_rejected():
    ciphertext = encrypt_token(TOKEN_JSON)
    tampered = ciphertext[:-4] + ("AAAA" if not ciphertext.endswith("AAAA") else "BBBB")

    with pytest.raises(InvalidToken):
        decrypt_token(tampered)
