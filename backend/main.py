import re
from datetime import date
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.db.db import get_connection

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
        with get_connection() as conn, conn.cursor() as cur:
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
    with get_connection() as conn, conn.cursor() as cur:
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


@app.get("/meetings/{advisor_id}")
def list_meetings(advisor_id: int):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, client_id, advisor_id, meeting_date, completion_status
                FROM meetings
                WHERE advisor_id = %s
                ORDER BY meeting_date DESC, id DESC
                """,
            (advisor_id,),
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


@app.get("/scheduled_meetings/{advisor_id}")
def list_scheduled_meetings(advisor_id: int):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, client_id, advisor_id, meeting_date, completion_status
                FROM meetings
                WHERE advisor_id = %s AND completion_status = 'Scheduled'
                ORDER BY meeting_date DESC, id DESC
                """,
            (advisor_id,),
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


@app.get("/completed_meetings/{advisor_id}")
def list_completed_meetings(advisor_id: int):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, client_id, advisor_id, meeting_date, completion_status
                FROM meetings
                WHERE advisor_id = %s AND completion_status = 'Completed'
                ORDER BY meeting_date DESC, id DESC
                """,
            (advisor_id,),
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


@app.get("/meetings/{advisor_id}/{client_id}")
def list_meetings_for_client(advisor_id: int, client_id: int):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, client_id, advisor_id, meeting_date, completion_status
                FROM meetings
                WHERE advisor_id = %s AND client_id = %s
                ORDER BY meeting_date DESC, id DESC
                """,
            (advisor_id, client_id),
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]
