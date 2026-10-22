<<<<<<< HEAD
<<<<<<< HEAD
=======

>>>>>>> 0b70d36 (used ruff to fix formatting issues)
=======
>>>>>>> 00dd710 (fixed issues again with ruff)
from fastapi import APIRouter

from app.db.db import get_connection

router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.get("/{advisor_id}")
def list_meetings(advisor_id: int):
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
def list_scheduled_meetings(advisor_id: int):
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
def list_completed_meetings(advisor_id: int):
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
def list_meetings_for_client(advisor_id: int, client_id: int):
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
