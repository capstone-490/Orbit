# Substantial AI assistance used; verified with backend tests and live auth smoke test.
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from app.auth import get_current_advisor
from app.dependencies.db import get_connection

CONTINUING_SESSION_DURATION = timedelta(hours=1)

router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"],
    dependencies=[Depends(get_current_advisor)],
)


class ContinuingSessionCreate(BaseModel):
    client_id: int
    meeting_date: datetime

    @field_validator("meeting_date")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("meeting_date must include a timezone.")
        return value


@router.post("/continuing-session", status_code=201)
def create_continuing_session(
    booking: ContinuingSessionCreate,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    meeting_date = booking.meeting_date.astimezone(UTC)
    meeting_end = meeting_date + CONTINUING_SESSION_DURATION
    lock_key = f"meeting-advisor:{advisor['id']}"

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%(lock_key)s, 0))",
            {"lock_key": lock_key},
        )
        cur.execute(
            "SELECT id FROM clients WHERE id = %(client_id)s AND advisor_id = %(advisor_id)s",
            {"client_id": booking.client_id, "advisor_id": advisor["id"]},
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Client not found.")

        cur.execute(
            """
                SELECT id FROM meetings
                WHERE advisor_id = %(advisor_id)s
                  AND completion_status = 'Scheduled'
                  AND meeting_date < %(meeting_end)s
                  AND meeting_date + %(duration)s > %(meeting_date)s
                LIMIT 1
                """,
            {
                "advisor_id": advisor["id"],
                "meeting_date": meeting_date,
                "meeting_end": meeting_end,
                "duration": CONTINUING_SESSION_DURATION,
            },
        )
        if cur.fetchone() is not None:
            raise HTTPException(status_code=409, detail="Time slot is unavailable.")

        cur.execute(
            """
                INSERT INTO meetings (advisor_id, client_id, meeting_date)
                VALUES (%(advisor_id)s, %(client_id)s, %(meeting_date)s)
                RETURNING id, client_id, advisor_id, meeting_date, completion_status
                """,
            {
                "advisor_id": advisor["id"],
                "client_id": booking.client_id,
                "meeting_date": meeting_date,
            },
        )
        columns = [column.name for column in cur.description]
        row = cur.fetchone()

    return dict(zip(columns, row))


@router.get("/{advisor_id}")
def list_meetings(
    advisor_id: int, advisor: dict[str, int] = Depends(get_current_advisor)
):
    _require_matching_advisor(advisor_id, advisor)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, client_id, advisor_id, meeting_date, completion_status
                FROM meetings
                WHERE advisor_id = %(advisor_id)s
                ORDER BY meeting_date DESC, id DESC
                """,
            {"advisor_id": advisor_id},
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


@router.get("/scheduled/{advisor_id}")
def list_scheduled_meetings(
    advisor_id: int,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    _require_matching_advisor(advisor_id, advisor)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, client_id, advisor_id, meeting_date, completion_status
                FROM meetings
                WHERE advisor_id = %(advisor_id)s AND completion_status = 'Scheduled'
                ORDER BY meeting_date DESC, id DESC
                """,
            {"advisor_id": advisor_id},
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


@router.get("/completed/{advisor_id}")
def list_completed_meetings(
    advisor_id: int,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    _require_matching_advisor(advisor_id, advisor)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, client_id, advisor_id, meeting_date, completion_status
                FROM meetings
                WHERE advisor_id = %(advisor_id)s AND completion_status = 'Completed'
                ORDER BY meeting_date DESC, id DESC
                """,
            {"advisor_id": advisor_id},
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


@router.get("/{advisor_id}/{client_id}")
def list_meetings_for_client(
    advisor_id: int,
    client_id: int,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    _require_matching_advisor(advisor_id, advisor)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, client_id, advisor_id, meeting_date, completion_status
                FROM meetings
                WHERE advisor_id = %(advisor_id)s AND client_id = %(client_id)s
                ORDER BY meeting_date DESC, id DESC
                """,
            {"advisor_id": advisor_id, "client_id": client_id},
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


def _require_matching_advisor(advisor_id: int, advisor: dict[str, int]) -> None:
    if advisor_id != advisor["id"]:
        raise HTTPException(status_code=403, detail="Not authorized for this advisor.")
