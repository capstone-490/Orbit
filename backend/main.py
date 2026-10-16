
from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from psycopg.errors import UniqueViolation

from db import get_connection

app = FastAPI()

# Allow the React development server to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class ClientCreate(BaseModel):
    name: str = Field(min_length=1)
    email: EmailStr
    phone_number: str = Field(min_length=1)
    address: str | None = None
    date_of_birth: date | None = None
    occupation: str | None = None
    risk_tolerance: Literal["Conservative", "Moderate", "Aggressive"] | None = None
    target_retirement_age: int | None = Field(default=None, ge=0, le=120)
    timeline: Literal[
        "Corporate Introduction",
        "Investment Education",
        "Tax Education",
        "Insurance Education",
        "Financial Needs Analysis",
        "Financial Plan",
    ] | None = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/clients", status_code=201)
def create_client(client: ClientCreate):
    data = client.model_dump(mode="json")

    # Optional blank form fields should become SQL NULL
    for field in (
        "address",
        "date_of_birth",
        "occupation",
        "risk_tolerance",
        "target_retirement_age",
        "timeline",
    ):
        if data[field] == "":
            data[field] = None

    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO clients (
                        name, email, phone_number, address,
                        date_of_birth, occupation, risk_tolerance,
                        target_retirement_age, timeline
                    )
                    VALUES (
                        %(name)s, %(email)s, %(phone_number)s,
                        %(address)s, %(date_of_birth)s, %(occupation)s,
                        %(risk_tolerance)s, %(target_retirement_age)s,
                        %(timeline)s
                    )
                    RETURNING id
                    """,
                    data,
                )
                client_id = cur.fetchone()[0]

        return {"id": client_id, "message": "Client created successfully"}

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail="A client with this email or phone number already exists.",
        )


@app.get("/clients")
def list_clients():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, email, phone_number,
                       address, date_of_birth, occupation,
                       risk_tolerance, target_retirement_age,
                       timeline, created_at
                FROM clients
                ORDER BY created_at DESC, id DESC
                """
            )

            columns = [column.name for column in cur.description]
            rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]
