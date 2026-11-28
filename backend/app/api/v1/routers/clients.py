# Substantial AI assistance used; verified with backend tests and livetime import date
import re
from datetime import date
from decimal import Decimal
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
    annual_income: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )
    risk_tolerance: Literal["Conservative", "Moderate", "Aggressive"] | None = None
    target_retirement_age: int | None = Field(default=None, ge=0, le=130)

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


class ClientUpdate(BaseModel):
    name: str | None = None
    phone_number: str | None = None
    email: EmailStr | None = None
    address: str | None = None
    age: int | None = Field(default=None, ge=0, le=130)
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
    annual_income: Decimal | None = Field(
        default=None, ge=0, max_digits=14, decimal_places=2
    )
    risk_tolerance: Literal["Conservative", "Moderate", "Aggressive"] | None = None
    target_retirement_age: int | None = Field(default=None, ge=0, le=130)


ExpenseFrequency = Literal["weekly", "monthly", "annually"]


class ClientExpenseInput(BaseModel):
    description: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    frequency: ExpenseFrequency

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        description = value.strip()
        if not description:
            raise ValueError("Expense description cannot be blank.")
        return description


IncomeFrequency = Literal["weekly", "monthly", "annually"]


class ClientIncomeInput(BaseModel):
    description: str = Field(min_length=1, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    frequency: IncomeFrequency

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        description = value.strip()
        if not description:
            raise ValueError("Income description cannot be blank.")
        return description


class ClientAssetInput(BaseModel):
    description: str = Field(min_length=1, max_length=120)
    value: Decimal = Field(gt=0, max_digits=14, decimal_places=2)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        description = value.strip()
        if not description:
            raise ValueError("Asset description cannot be blank.")
        return description


class ClientDebtInput(BaseModel):
    description: str = Field(min_length=1, max_length=120)
    balance: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    interest_rate: Decimal = Field(ge=0, max_digits=5, decimal_places=2)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str) -> str:
        description = value.strip()
        if not description:
            raise ValueError("Debt description cannot be blank.")
        return description


class ClientFinancialSnapshotInput(BaseModel):
    expenses: list[ClientExpenseInput] = Field(default_factory=list, max_length=100)
    income: list[ClientIncomeInput] = Field(default_factory=list, max_length=100)
    assets: list[ClientAssetInput] = Field(default_factory=list, max_length=100)
    debts: list[ClientDebtInput] = Field(default_factory=list, max_length=100)


CLIENT_SELECT = """
    SELECT c.id, c.name, c.email, c.phone_number,
           c.address, c.age, c.occupation,
           c.timeline, c.created_at, c.updated_at,
           s.annual_income, s.risk_tolerance, s.target_retirement_age
    FROM t_clients AS c
    LEFT JOIN t_client_financial_summaries AS s ON s.client_id = c.id
"""


def _snapshot_totals(
    expenses: list[dict], income: list[dict], assets: list[dict], debts: list[dict]
) -> dict[str, Decimal]:
    weekly_to_monthly = Decimal(52) / Decimal(12)

    # Calculate expense totals
    expense_weekly = Decimal("0")
    expense_monthly = Decimal("0")
    expense_annual = Decimal("0")
    for expense in expenses:
        amount = Decimal(expense["amount"])
        if expense["frequency"] == "weekly":
            expense_weekly += amount
            expense_monthly += amount * weekly_to_monthly
            expense_annual += amount * 52
        elif expense["frequency"] == "monthly":
            expense_weekly += amount / weekly_to_monthly
            expense_monthly += amount
            expense_annual += amount * 12
        else:
            expense_weekly += amount / 52
            expense_monthly += amount / 12
            expense_annual += amount

    # Calculate income totals
    income_weekly = Decimal("0")
    income_monthly = Decimal("0")
    income_annual = Decimal("0")
    for inc in income:
        amount = Decimal(inc["amount"])
        if inc["frequency"] == "weekly":
            income_weekly += amount
            income_monthly += amount * weekly_to_monthly
            income_annual += amount * 52
        elif inc["frequency"] == "monthly":
            income_weekly += amount / weekly_to_monthly
            income_monthly += amount
            income_annual += amount * 12
        else:
            income_weekly += amount / 52
            income_monthly += amount / 12
            income_annual += amount

    # Calculate asset and debt totals (one-time values)
    total_assets = sum(
        (Decimal(asset["value"]) for asset in assets), Decimal("0")
    )
    total_debts = sum(
        (Decimal(debt["balance"]) for debt in debts), Decimal("0")
    )
    net_worth = total_assets - total_debts

    # Calculate revenue (income - expenses)
    revenue_weekly = income_weekly - expense_weekly
    revenue_monthly = income_monthly - expense_monthly
    revenue_annual = income_annual - expense_annual

    return {
        "expenses": {
            "weekly_total": expense_weekly.quantize(Decimal("0.01")),
            "monthly_total": expense_monthly.quantize(Decimal("0.01")),
            "annual_total": expense_annual.quantize(Decimal("0.01")),
        },
        "income": {
            "weekly_total": income_weekly.quantize(Decimal("0.01")),
            "monthly_total": income_monthly.quantize(Decimal("0.01")),
            "annual_total": income_annual.quantize(Decimal("0.01")),
        },
        "revenue": {
            "weekly_total": revenue_weekly.quantize(Decimal("0.01")),
            "monthly_total": revenue_monthly.quantize(Decimal("0.01")),
            "annual_total": revenue_annual.quantize(Decimal("0.01")),
        },
        "assets": {
            "total": total_assets.quantize(Decimal("0.01")),
        },
        "debts": {
            "total": total_debts.quantize(Decimal("0.01")),
        },
        "net_worth": net_worth.quantize(Decimal("0.01")),
    }



@router.get("")
def list_clients(advisor: dict[str, int] = Depends(get_current_advisor)):
    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:
        cur.execute(
            CLIENT_SELECT
            + """
            WHERE c.advisor_id = %(advisor_id)s
            ORDER BY c.created_at DESC, c.id DESC
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
    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:
        cur.execute(
            CLIENT_SELECT
            + """
            WHERE c.id = %(client_id)s AND c.advisor_id = %(advisor_id)s
            """,
            {"client_id": client_id, "advisor_id": advisor["id"]},
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Client not found")

        columns = [column.name for column in cur.description]
        return dict(zip(columns, row))


# Create a new client
@router.post("", status_code=201)
def create_client(
    client: ClientCreate,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    data = client.model_dump()
    data["advisor_id"] = advisor["id"]
    data["age"] = calculate_age(client.date_of_birth)
    data.pop("date_of_birth", None)
    summary_fields = {
        "annual_income": data.pop("annual_income"),
        "risk_tolerance": data.pop("risk_tolerance"),
        "target_retirement_age": data.pop("target_retirement_age"),
    }

    # Convert optional blank fields to SQL NULL
    for field in (
        "address",
        "age",
        "occupation",
        "timeline",
    ):
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
                    name, email, phone_number, address,
                    age, occupation, timeline, advisor_id
                )
                VALUES (
                    %(name)s, %(email)s, %(phone_number)s,
                    %(address)s, %(age)s, %(occupation)s,
                    %(timeline)s, %(advisor_id)s
                )
                RETURNING id
                """,
                data,
            )
            client_id = cur.fetchone()[0]

            summary_values = {
                key: value for key, value in summary_fields.items() if value is not None
            }
            if summary_values:
                fields = ", ".join(summary_values)
                placeholders = ", ".join(f"%({field})s" for field in summary_values)
                cur.execute(
                    f"""
                    INSERT INTO t_client_financial_summaries (client_id, {fields})
                    VALUES (%(client_id)s, {placeholders})
                    """,
                    {"client_id": client_id, **summary_values},
                )

        return {
            "id": client_id,
            "message": "Client created successfully",
        }

    except UniqueViolation:
        raise HTTPException(
            status_code=409,
            detail=("A client with this email or phone number already exists."),
        )


@router.patch("/{client_id}")
def update_client(
    client_id: int,
    client: ClientUpdate,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    updates = client.model_dump(exclude_unset=True)
    client_fields = {
        "name",
        "phone_number",
        "email",
        "address",
        "age",
        "occupation",
        "timeline",
    }
    summary_fields = {
        "annual_income",
        "risk_tolerance",
        "target_retirement_age",
    }

    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No valid fields provided for update",
        )

    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id
            FROM t_clients
            WHERE id = %(client_id)s AND advisor_id = %(advisor_id)s
            FOR UPDATE
            """,
            {"client_id": client_id, "advisor_id": advisor["id"]},
        )
        if cur.fetchone() is None:
            raise HTTPException(
                status_code=404,
                detail="Client not found",
            )

        client_updates = {
            key: value for key, value in updates.items() if key in client_fields
        }
        if client_updates:
            set_clause = ", ".join(
                f"{field} = %({field})s" for field in client_updates
            )
            cur.execute(
                f"""
                UPDATE t_clients
                SET {set_clause}, updated_at = NOW() AT TIME ZONE 'UTC'
                WHERE id = %(client_id)s AND advisor_id = %(advisor_id)s
                """,
                {
                    **client_updates,
                    "client_id": client_id,
                    "advisor_id": advisor["id"],
                },
            )

        summary_updates = {
            key: value for key, value in updates.items() if key in summary_fields
        }
        if summary_updates:
            fields = ", ".join(summary_updates)
            placeholders = ", ".join(f"%({field})s" for field in summary_updates)
            set_clause = ", ".join(
                f"{field} = EXCLUDED.{field}" for field in summary_updates
            )
            cur.execute(
                f"""
                INSERT INTO t_client_financial_summaries (client_id, {fields})
                VALUES (%(client_id)s, {placeholders})
                ON CONFLICT (client_id) DO UPDATE
                SET {set_clause}, updated_at = NOW() AT TIME ZONE 'UTC'
                """,
                {"client_id": client_id, **summary_updates},
            )

        cur.execute(
            CLIENT_SELECT
            + """
            WHERE c.id = %(client_id)s AND c.advisor_id = %(advisor_id)s
            """,
            {"client_id": client_id, "advisor_id": advisor["id"]},
        )
        updated_client = cur.fetchone()
        columns = [column.name for column in cur.description]
        result = dict(zip(columns, updated_client))

    result["message"] = "Client updated successfully"
    return result


@router.get("/{client_id}/financial-snapshot")
def get_client_financial_snapshot(
    client_id: int,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM t_clients
            WHERE id = %(client_id)s AND advisor_id = %(advisor_id)s
            """,
            {"client_id": client_id, "advisor_id": advisor["id"]},
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Client not found")

        # Fetch expenses
        cur.execute(
            """
            SELECT id, description, amount, frequency
            FROM t_client_expenses
            WHERE client_id = %(client_id)s
            ORDER BY id
            """,
            {"client_id": client_id},
        )
        columns = [column.name for column in cur.description]
        expenses = [dict(zip(columns, row)) for row in cur.fetchall()]

        # Fetch income
        cur.execute(
            """
            SELECT id, description, amount, frequency
            FROM t_client_income
            WHERE client_id = %(client_id)s
            ORDER BY id
            """,
            {"client_id": client_id},
        )
        columns = [column.name for column in cur.description]
        income = [dict(zip(columns, row)) for row in cur.fetchall()]

        # Fetch assets
        cur.execute(
            """
            SELECT id, description, value
            FROM t_client_assets
            WHERE client_id = %(client_id)s
            ORDER BY id
            """,
            {"client_id": client_id},
        )
        columns = [column.name for column in cur.description]
        assets = [dict(zip(columns, row)) for row in cur.fetchall()]

        # Fetch debts
        cur.execute(
            """
            SELECT id, description, balance, interest_rate
            FROM t_client_debts
            WHERE client_id = %(client_id)s
            ORDER BY id
            """,
            {"client_id": client_id},
        )
        columns = [column.name for column in cur.description]
        debts = [dict(zip(columns, row)) for row in cur.fetchall()]

    return {
        "expenses": expenses,
        "income": income,
        "assets": assets,
        "debts": debts,
        "totals": _snapshot_totals(expenses, income, assets, debts),
    }
@router.put("/{client_id}/financial-snapshot")
def replace_client_financial_snapshot(
    client_id: int,
    snapshot: ClientFinancialSnapshotInput,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id FROM t_clients
            WHERE id = %(client_id)s AND advisor_id = %(advisor_id)s
            FOR UPDATE
            """,
            {"client_id": client_id, "advisor_id": advisor["id"]},
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Client not found")

        cur.execute(
            """
            INSERT INTO t_client_financial_snapshots (client_id)
            VALUES (%(client_id)s)
            ON CONFLICT (client_id) DO UPDATE
            SET updated_at = NOW()
            """,
            {"client_id": client_id},
        )

        # Delete and insert expenses
        cur.execute(
            "DELETE FROM t_client_expenses WHERE client_id = %(client_id)s",
            {"client_id": client_id},
        )
        for expense in snapshot.expenses:
            cur.execute(
                """
                INSERT INTO t_client_expenses (
                    client_id, description, amount, frequency
                )
                VALUES (%(client_id)s, %(description)s, %(amount)s, %(frequency)s)
                """,
                {"client_id": client_id, **expense.model_dump()},
            )

        # Delete and insert income
        cur.execute(
            "DELETE FROM t_client_income WHERE client_id = %(client_id)s",
            {"client_id": client_id},
        )
        for inc in snapshot.income:
            cur.execute(
                """
                INSERT INTO t_client_income (
                    client_id, description, amount, frequency
                )
                VALUES (%(client_id)s, %(description)s, %(amount)s, %(frequency)s)
                """,
                {"client_id": client_id, **inc.model_dump()},
            )

        # Delete and insert assets
        cur.execute(
            "DELETE FROM t_client_assets WHERE client_id = %(client_id)s",
            {"client_id": client_id},
        )
        for asset in snapshot.assets:
            cur.execute(
                """
                INSERT INTO t_client_assets (
                    client_id, description, value
                )
                VALUES (%(client_id)s, %(description)s, %(value)s)
                """,
                {"client_id": client_id, **asset.model_dump()},
            )

        # Delete and insert debts
        cur.execute(
            "DELETE FROM t_client_debts WHERE client_id = %(client_id)s",
            {"client_id": client_id},
        )
        for debt in snapshot.debts:
            cur.execute(
                """
                INSERT INTO t_client_debts (
                    client_id, description, balance, interest_rate
                )
                VALUES (%(client_id)s, %(description)s, %(balance)s, %(interest_rate)s)
                """,
                {"client_id": client_id, **debt.model_dump()},
            )

        # Fetch all data to return
        cur.execute(
            """
            SELECT id, description, amount, frequency
            FROM t_client_expenses
            WHERE client_id = %(client_id)s
            ORDER BY id
            """,
            {"client_id": client_id},
        )
        columns = [column.name for column in cur.description]
        expenses = [dict(zip(columns, row)) for row in cur.fetchall()]

        cur.execute(
            """
            SELECT id, description, amount, frequency
            FROM t_client_income
            WHERE client_id = %(client_id)s
            ORDER BY id
            """,
            {"client_id": client_id},
        )
        columns = [column.name for column in cur.description]
        income = [dict(zip(columns, row)) for row in cur.fetchall()]

        cur.execute(
            """
            SELECT id, description, value
            FROM t_client_assets
            WHERE client_id = %(client_id)s
            ORDER BY id
            """,
            {"client_id": client_id},
        )
        columns = [column.name for column in cur.description]
        assets = [dict(zip(columns, row)) for row in cur.fetchall()]

        cur.execute(
            """
            SELECT id, description, balance, interest_rate
            FROM t_client_debts
            WHERE client_id = %(client_id)s
            ORDER BY id
            """,
            {"client_id": client_id},
        )
        columns = [column.name for column in cur.description]
        debts = [dict(zip(columns, row)) for row in cur.fetchall()]

    return {
        "expenses": expenses,
        "income": income,
        "assets": assets,
        "debts": debts,
        "totals": _snapshot_totals(expenses, income, assets, debts),
    }
