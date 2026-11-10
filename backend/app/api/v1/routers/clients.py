import re
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from psycopg.errors import UniqueViolation
from pydantic import BaseModel, EmailStr, Field, field_validator

from app.auth import get_current_advisor
from app.dependencies.db import get_connection

router = APIRouter(
    prefix="/clients",
    tags=["Clients"],
    dependencies=[Depends(get_current_advisor)],
)


def calculate_age(birth_date: date | None, today: date | None = None) -> int | None:
    if birth_date is None:
        return None
    current_date = today or date.today()
    return (
        current_date.year
        - birth_date.year
        - ((current_date.month, current_date.day) < (birth_date.month, birth_date.day))
    )


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


@router.get("")
def list_clients(advisor: dict[str, int] = Depends(get_current_advisor)):
    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, email, phone_number,
                   address, age, occupation,
                   timeline, created_at
            FROM t_clients
            WHERE advisor_id = %(advisor_id)s
            ORDER BY created_at DESC, id DESC
                 """,
            {"advisor_id": advisor["id"]},
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


@router.get("/{client_id}")
def get_client(
    client_id: int,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, email, phone_number,
                   address, age, occupation,
                   timeline, created_at
            FROM t_clients
            WHERE id = %(client_id)s AND advisor_id = %(advisor_id)s
            """,
            {"client_id": client_id, "advisor_id": advisor["id"]},
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Client not found")

        columns = [column.name for column in cur.description]
        return dict(zip(columns, row))


@router.post("", status_code=201)
def create_client(
    client: ClientCreate,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    data = client.model_dump(mode="json")
    data["advisor_id"] = advisor["id"]
    data["age"] = calculate_age(client.date_of_birth)
    data.pop("date_of_birth", None)

    for field in ("address", "age", "occupation", "timeline"):
        if data[field] == "":
            data[field] = None

    try:
        with (
            get_connection(str(advisor["id"]), "Advisor") as conn,
            conn.cursor() as cur,
        ):
            cur.execute(
                """
                INSERT INTO t_clients (
                    advisor_id, name, email, phone_number,
                    address, age, occupation, timeline
                )
                VALUES (
                    %(advisor_id)s, %(name)s, %(email)s, %(phone_number)s,
                    %(address)s, %(age)s, %(occupation)s, %(timeline)s
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
            detail="A client with this email or phone number already exists.",
        )


# Temporary patch as US-15.1 needed a patch client API for testing purposes
@router.patch("/{client_id}")
def update_client(
    client_id: int,
    client: dict,
    advisor: dict[str, int] = Depends(get_current_advisor),
):

    allowed_fields = {
        "name",
        "phone_number",
        "email",
        "address",
        "age",
        "occupation",
        "timeline",
    }

    updates = {key: value for key, value in client.items() if key in allowed_fields}

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No valid fields provided for update",
        )

    set_clause = ", ".join(f"{field} = %({field})s" for field in updates)

    set_clause += ", updated_at = NOW() AT TIME ZONE 'UTC'"

    query = f"""
        UPDATE t_clients
        SET {set_clause}
        WHERE id = %(client_id)s
          AND advisor_id = %(advisor_id)s
        RETURNING id, name, phone_number, email, address,
                  age, occupation, timeline, created_at, updated_at
    """

    updates["client_id"] = client_id
    updates["advisor_id"] = advisor["id"]

    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:
        cur.execute(query, updates)

        updated_client = cur.fetchone()

        if updated_client is None:
            raise HTTPException(
                status_code=404,
                detail="Client not found",
            )

    return {
        "id": updated_client[0],
        "name": updated_client[1],
        "phone_number": updated_client[2],
        "email": updated_client[3],
        "address": updated_client[4],
        "age": updated_client[5],
        "occupation": updated_client[6],
        "timeline": updated_client[7],
        "created_at": updated_client[8],
        "updated_at": updated_client[9],
        "message": "Client updated successfully",
    }
