from typing import Annotated

from fastapi import Depends, Request

from app.core.security.anonymizer import TokenStore


def get_token_store(request: Request) -> TokenStore:
    return request.app.state.token_store


TokenStoreDep = Annotated[
    TokenStore,
    Depends(get_token_store),
]
