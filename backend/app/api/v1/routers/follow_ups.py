from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Error as PsycopgError
from psycopg.rows import dict_row
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.auth import get_current_advisor
from app.dependencies.db import get_connection

FollowUpPriority = Literal["Low", "Medium", "High"]
FollowUpStatus = Literal["Pending", "In Progress", "Completed", "Cancelled"]
FinancialPlanningStage = Literal[
    "Corporate Introduction",
    "Investment Education",
    "Tax Education",
    "Insurance Education",
    "Financial Needs Analysis",
    "Financial Plan",
]

router = APIRouter(prefix="/follow-ups", tags=["Follow-Ups"])


class FollowUpCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=2000)
    financial_planning_stage: FinancialPlanningStage
    due_date: date
    priority: FollowUpPriority = "Medium"
    status: FollowUpStatus = "Pending"

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str) -> str:
        reason = value.strip()
        if not reason:
            raise ValueError("Reason cannot be blank.")
        return reason


class FollowUpUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, min_length=1, max_length=2000)
    financial_planning_stage: FinancialPlanningStage | None = None
    due_date: date | None = None
    priority: FollowUpPriority | None = None
    status: FollowUpStatus | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, value: str | None) -> str | None:
        if value is None:
            return None
        reason = value.strip()
        if not reason:
            raise ValueError("Reason cannot be blank.")
        return reason


class FollowUpStatusUpdate(BaseModel):
    status: FollowUpStatus


def _client_belongs_to_advisor(client_id: int, advisor_id: int) -> bool:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM clients WHERE id = %s AND advisor_id = %s",
            (client_id, advisor_id),
        )
        return cur.fetchone() is not None


def _follow_up_or_404(follow_up_id: int, advisor_id: int) -> dict:
    with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, advisor_id, client_id, reason,
                   financial_planning_stage::text AS financial_planning_stage,
                   due_date, priority::text AS priority,
                   status::text AS status, created_at, updated_at
            FROM follow_ups
            WHERE id = %s AND advisor_id = %s
            """,
            (follow_up_id, advisor_id),
        )
        follow_up = cur.fetchone()

    if follow_up is None:
        raise HTTPException(status_code=404, detail="Follow-up not found.")
    return follow_up


@router.post("", status_code=201)
def create_follow_up(
    follow_up: FollowUpCreate,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    if not _client_belongs_to_advisor(follow_up.client_id, advisor["id"]):
        raise HTTPException(
            status_code=404,
            detail="Client not found or not assigned to this advisor.",
        )

    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO follow_ups (
                    advisor_id, client_id, reason, financial_planning_stage,
                    due_date, priority, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, advisor_id, client_id, reason,
                          financial_planning_stage::text AS financial_planning_stage,
                          due_date, priority::text AS priority,
                          status::text AS status, created_at, updated_at
                """,
                (
                    advisor["id"],
                    follow_up.client_id,
                    follow_up.reason,
                    follow_up.financial_planning_stage,
                    follow_up.due_date,
                    follow_up.priority,
                    follow_up.status,
                ),
            )
            created = cur.fetchone()
            conn.commit()
    except PsycopgError as error:
        raise HTTPException(
            status_code=500, detail="Unable to create follow-up."
        ) from error

    if created is None:
        raise HTTPException(status_code=500, detail="Unable to create follow-up.")
    return created


@router.get("")
def list_follow_ups(advisor: dict[str, int] = Depends(get_current_advisor)):
    with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT id, advisor_id, client_id, reason,
                   financial_planning_stage::text AS financial_planning_stage,
                   due_date, priority::text AS priority,
                   status::text AS status, created_at, updated_at
            FROM follow_ups
            WHERE advisor_id = %s
            ORDER BY due_date ASC, id ASC
            """,
            (advisor["id"],),
        )
        return cur.fetchall()


@router.get("/{follow_up_id}")
def get_follow_up(
    follow_up_id: int,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    return _follow_up_or_404(follow_up_id, advisor["id"])


@router.patch("/{follow_up_id}")
def update_follow_up(
    follow_up_id: int,
    follow_up: FollowUpUpdate,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    values = follow_up.model_dump(exclude_unset=True)
    if not values:
        raise HTTPException(
            status_code=422, detail="At least one field must be provided."
        )

    if "client_id" in values:
        raise HTTPException(status_code=422, detail="Client cannot be changed.")

    assignments = ", ".join(f"{field} = %({field})s" for field in values)
    values["follow_up_id"] = follow_up_id
    values["advisor_id"] = advisor["id"]

    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                UPDATE follow_ups
                SET {assignments}, updated_at = NOW()
                WHERE id = %(follow_up_id)s AND advisor_id = %(advisor_id)s
                RETURNING id, advisor_id, client_id, reason,
                          financial_planning_stage::text AS financial_planning_stage,
                          due_date, priority::text AS priority,
                          status::text AS status, created_at, updated_at
                """,
                values,
            )
            updated = cur.fetchone()
            conn.commit()
    except PsycopgError as error:
        raise HTTPException(
            status_code=500, detail="Unable to update follow-up."
        ) from error

    if updated is None:
        raise HTTPException(status_code=404, detail="Follow-up not found.")
    return updated


@router.patch("/{follow_up_id}/status")
def update_follow_up_status(
    follow_up_id: int,
    update: FollowUpStatusUpdate,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    return update_follow_up(
        follow_up_id,
        FollowUpUpdate(status=update.status),
        advisor,
    )
