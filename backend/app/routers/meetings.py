# Substantial AI assistance used; verified with backend tests and live auth smoke test.
from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_advisor
from app.db.db import get_connection

router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"],
    dependencies=[Depends(get_current_advisor)],
)


@router.get("/{advisor_id}")
def list_meetings(advisor_id: int, advisor: dict[str, int] = Depends(get_current_advisor)):
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
