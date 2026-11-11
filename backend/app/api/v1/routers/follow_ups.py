from fastapi import APIRouter, Depends, HTTPException
from psycopg import Error as PsycopgError
from psycopg.rows import dict_row

from app.auth import get_current_advisor
from app.classes.follow_up import FollowUpCreate, FollowUpStatusUpdate, FollowUpUpdate
from app.dependencies.db import get_connection
from app.observability.logging_config import get_logger

router = APIRouter(prefix="/follow-ups", tags=["Follow-Ups"])
logger = get_logger("app.api.follow_ups")


def _follow_up_or_404(follow_up_id: int, advisor_id: int) -> dict:
    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, advisor_id, client_id, reason,
                       financial_planning_stage::text AS financial_planning_stage,
                       due_date, priority::text AS priority,
                       status::text AS status, discussion_notes, created_at, updated_at
                FROM follow_ups
                WHERE id = %s AND advisor_id = %s
                """,
                (follow_up_id, advisor_id),
            )
            follow_up = cur.fetchone()
    except PsycopgError as error:
        logger.exception(
            "Failed to retrieve follow-up",
            extra={"advisor_id": advisor_id, "follow_up_id": follow_up_id},
        )
        raise HTTPException(
            status_code=500, detail="Unable to retrieve follow-up."
        ) from error

    if follow_up is None:
        raise HTTPException(status_code=404, detail="Follow-up not found.")
    return follow_up


@router.post("", status_code=201)
def create_follow_up(
    follow_up: FollowUpCreate,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO follow_ups (
                    advisor_id, client_id, reason, financial_planning_stage,
                    due_date, priority, status
                )
                SELECT %s, id, %s, %s, %s, %s, %s
                FROM clients
                WHERE id = %s AND advisor_id = %s
                RETURNING id, advisor_id, client_id, reason,
                          financial_planning_stage::text AS financial_planning_stage,
                          due_date, priority::text AS priority,
                          status::text AS status, discussion_notes, created_at, updated_at
                """,
                (
                    advisor["id"],
                    follow_up.reason,
                    follow_up.financial_planning_stage,
                    follow_up.due_date,
                    follow_up.priority,
                    follow_up.status,
                    follow_up.client_id,
                    advisor["id"],
                ),
            )
            created = cur.fetchone()
            conn.commit()
    except PsycopgError as error:
        logger.exception(
            "Failed to create follow-up", extra={"advisor_id": advisor["id"]}
        )
        raise HTTPException(
            status_code=500, detail="Unable to create follow-up."
        ) from error

    if created is None:
        raise HTTPException(
            status_code=404,
            detail="Client not found or not assigned to this advisor.",
        )
    return created


@router.get("")
def list_follow_ups(advisor: dict[str, int] = Depends(get_current_advisor)):
    try:
        with get_connection() as conn, conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, advisor_id, client_id, reason,
                       financial_planning_stage::text AS financial_planning_stage,
                       due_date, priority::text AS priority,
                       status::text AS status, discussion_notes, created_at, updated_at
                FROM follow_ups
                WHERE advisor_id = %s
                ORDER BY due_date ASC, id ASC
                """,
                (advisor["id"],),
            )
            return cur.fetchall()
    except PsycopgError as error:
        logger.exception(
            "Failed to list follow-ups", extra={"advisor_id": advisor["id"]}
        )
        raise HTTPException(
            status_code=500, detail="Unable to retrieve follow-ups."
        ) from error


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
    return _update_follow_up(
        follow_up_id,
        advisor["id"],
        follow_up.model_dump(exclude_unset=True),
    )


def _update_follow_up(
    follow_up_id: int,
    advisor_id: int,
    values: dict,
):
    if not values:
        raise HTTPException(
            status_code=422, detail="At least one field must be provided."
        )

    if "client_id" in values:
        raise HTTPException(status_code=422, detail="Client cannot be changed.")

    assignments = ", ".join(f"{field} = %({field})s" for field in values)
    values["follow_up_id"] = follow_up_id
    values["advisor_id"] = advisor_id

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
                          status::text AS status, discussion_notes, created_at, updated_at
                """,
                values,
            )
            updated = cur.fetchone()
            conn.commit()
    except PsycopgError as error:
        logger.exception(
            "Failed to update follow-up",
            extra={"advisor_id": advisor_id, "follow_up_id": follow_up_id},
        )
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
    return _update_follow_up(
        follow_up_id,
        advisor["id"],
        {"status": update.status},
    )
