import re
from datetime import date
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.db.db import get_connection
from security.anonymizer import ClientAnonymizer

router = APIRouter(prefix="/clients", tags=["Clients"])
client_anonymizer: ClientAnonymizer | None = None


# Client data model and validation
class ClientCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    phone_number: str = Field(min_length=1)
    address: str | None = None
    date_of_birth: date | None = None
    occupation: str | None = None
    timeline: (
        Literal[
            "Corporate Introduction",
            "Investment Education",
            "Tax Education",
            "Insurance Education",
            "Financial Needs Analysis",
            "Financial Plan",
        ]
        | None
    ) = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        phone = value.strip()

        if not re.fullmatch(r"\+?[\d\s().-]+", phone):
            raise ValueError("Please enter a valid Canadian or US phone number.")

        digits = re.sub(r"\D", "", phone)

        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        elif len(digits) != 10:
            raise ValueError("Please enter a valid 10-digit phone number.")

        if digits[0] not in "23456789" or digits[3] not in "23456789":
            raise ValueError("Please enter a valid Canadian or US phone number.")

        return phone


# Create a new client
@router.post("", status_code=201)
def create_client(client: ClientCreate):
    global client_anonymizer
    if client_anonymizer is None:
        client_anonymizer = ClientAnonymizer()
    data = client_anonymizer.anonymize(
        client.model_dump(mode="json"),
        client_key=str(uuid4()),
    )

    # Convert optional blank fields to SQL NULL
    for field in (
        "address",
        "age",
        "occupation",
        "timeline",
        "anonymized_client_id",
    ):
        if data[field] == "":
            data[field] = None

    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO clients (
                    name, email, phone_number, address,
                    age, occupation, timeline, anonymized_client_id
                )
                VALUES (
                    %(name)s, %(email)s, %(phone_number)s,
                    %(address)s, %(age)s, %(occupation)s,
                    %(timeline)s, %(anonymized_client_id)s
                )
                RETURNING id
                """,
                data,
            )
            client_id = cur.fetchone()[0]

        return {
            "id": client_id,
            "message": "Client created successfully",
        }

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail=("A client with this email or phone number already exists."),
        )


# Retrieve all existing clients
@router.get("")
def list_clients():
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, email, phone_number,
                   address, age, occupation, anonymized_client_id,
                   timeline, created_at
            FROM clients
            ORDER BY created_at DESC, id DESC
            """
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]
