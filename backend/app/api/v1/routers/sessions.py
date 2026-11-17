# Substantial AI assistance used; verified with backend tests and live auth smoke test.
import os

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.exc import SQLAlchemyError

from app.auth import create_access_token, get_current_advisor
from app.dependencies.db import get_connection
from app.security.passwords import verify_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
def login(credentials: LoginRequest, response: Response):
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, password_hash FROM t_advisors WHERE lower(email) = lower(%s)",
                (str(credentials.email),),
            )
            advisor = cur.fetchone()
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        ) from exc

    if advisor is None or not verify_password(credentials.password, advisor[1]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    token = create_access_token(advisor[0])

    response.set_cookie(
        key="orbit_session",
        value=token,
        max_age=3600,
        httponly=True,
        secure=os.environ.get("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/",
    )
    return {
        "expires_in": 3600,
        "advisor": {"id": advisor[0], "email": str(credentials.email)},
    }


@router.get("/me")
def current_session(advisor: dict[str, int] = Depends(get_current_advisor)):
    return advisor


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("orbit_session", path="/")
    return {"message": "Signed out."}
