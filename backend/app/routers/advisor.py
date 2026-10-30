
from fastapi import APIRouter, HTTPException
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.db.db import get_connection
from app.security.passwords import hash_password

router = APIRouter(prefix="/auth", tags=["Authentication"])


class AdvisorRegistration(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Username cannot be empty.")

        return value


class AdvisorResponse(BaseModel):
    id: int
    username: str
    email: EmailStr


@router.post("/register", response_model=AdvisorResponse, status_code=201)
def register_advisor(advisor: AdvisorRegistration):
    email = str(advisor.email).lower()
    password_hash = hash_password(advisor.password)

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO advisors (username, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id, username, email
                    """,
                    (advisor.username, email, password_hash),
                )

                result = cur.fetchone()

        if result is None:
            raise HTTPException(
                status_code=500,
                detail="Unable to create account.",
            )

        return {
            "id": result[0],
            "username": result[1],
            "email": result[2],
        }

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )
