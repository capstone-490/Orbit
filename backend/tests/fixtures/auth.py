import pytest

from app.auth import create_access_token


@pytest.fixture
def auth_headers():
    token = create_access_token(1)

    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.fixture
def user_headers():
    return {"User-ID": "user1"}
