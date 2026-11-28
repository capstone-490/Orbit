# Substantial AI assistance used; verified with backend tests and live auth smoke test.
import hashlib
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator

from app.auth import get_current_advisor
from app.dependencies.db import get_connection

CONTINUING_SESSION_DURATION = timedelta(hours=1)

router = APIRouter(
    prefix="/meetings",
    tags=["Meetings"],
    dependencies=[Depends(get_current_advisor)],
)
public_router = APIRouter(prefix="/meetings", tags=["Meetings"])


@router.get("/{meeting_id}/briefing-notes")
def get_meeting_briefing_notes(
    meeting_id: int,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    """Retrieve a meeting's client notes for the authenticated advisor."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.client_id
            FROM t_meetings AS m
            JOIN t_clients AS c ON c.id = m.client_id
            WHERE m.id = %(meeting_id)s
              AND m.advisor_id = %(advisor_id)s
              AND c.advisor_id = %(advisor_id)s
            """,
            {
                "meeting_id": meeting_id,
                "advisor_id": advisor["id"],
            },
        )

        meeting = cur.fetchone()

        if meeting is None:
            raise HTTPException(
                status_code=404,
                detail="Meeting not found.",
            )

        client_id = meeting[0]

        cur.execute(
            """
            SELECT id, title, content, created_at, updated_at
            FROM t_notes
            WHERE client_id = %(client_id)s
            ORDER BY created_at DESC, id DESC
            """,
            {"client_id": client_id},
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


class RescheduleMeetingRequest(BaseModel):
    new_start: datetime

    @field_validator("new_start")
    @classmethod
    def validate_new_start(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("new_start must include a timezone offset")

        if value <= datetime.now(UTC):
            raise ValueError("new_start must be in the future")

        return value


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
            "SELECT id FROM t_clients WHERE id = %(client_id)s AND advisor_id = %(advisor_id)s",
            {"client_id": booking.client_id, "advisor_id": advisor["id"]},
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Client not found.")

        cur.execute(
            """
                SELECT id FROM t_meetings
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
                INSERT INTO t_meetings (advisor_id, client_id, meeting_date)
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
    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                m.id,
                m.client_id,
                m.advisor_id,
                m.meeting_date,
                m.duration_minutes,
                m.completion_status,
                m.meeting_uri,
                m.meeting_code,
                c.name AS client_name,
                c.timeline::text AS client_timeline
            FROM t_meetings m
            JOIN t_clients c ON c.id = m.client_id
            WHERE m.advisor_id = %(advisor_id)s
            ORDER BY m.meeting_date ASC, m.id ASC
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
    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, client_id, advisor_id, meeting_date, completion_status,
                       meeting_uri, meeting_code
                FROM t_meetings
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
    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, client_id, advisor_id, meeting_date, completion_status,
                       meeting_uri, meeting_code
                FROM t_meetings
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
    with get_connection(str(advisor["id"]), "Advisor") as conn, conn.cursor() as cur:
        cur.execute(
            """
                SELECT id, client_id, advisor_id, meeting_date, completion_status,
                       meeting_uri, meeting_code
                FROM t_meetings
                WHERE advisor_id = %(advisor_id)s AND client_id = %(client_id)s
                ORDER BY meeting_date DESC, id DESC
                """,
            {"advisor_id": advisor_id, "client_id": client_id},
        )

        columns = [column.name for column in cur.description]
        rows = cur.fetchall()

    return [dict(zip(columns, row)) for row in rows]


@router.patch("/{meeting_id}/reschedule")
def reschedule_meeting(
    meeting_id: int,
    payload: RescheduleMeetingRequest,
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    updated = _reschedule_meeting(
        payload.new_start,
        advisor_id=advisor["id"],
        meeting_id=meeting_id,
    )

    return {
        **updated,
        "notification_status": "sent",
    }


@public_router.get("/client-reschedule")
def get_client_reschedule(token: str = Query(min_length=40, max_length=100)):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.meeting_date, m.duration_minutes,
                   a.username, m.completion_status
            FROM t_meetings m
            JOIN t_advisors a ON a.id = m.advisor_id
            WHERE m.reschedule_token_hash = %s
            """,
            (_hash_reschedule_token(token),),
        )
        meeting = cur.fetchone()

    if meeting is None or str(meeting[3]) != "Scheduled":
        raise HTTPException(status_code=404, detail="Reschedule link is invalid.")

    return {
        "meeting_date": meeting[0],
        "duration_minutes": meeting[1],
        "advisor_name": meeting[2],
    }


@public_router.patch("/client-reschedule")
def client_reschedule_meeting(
    payload: RescheduleMeetingRequest,
    token: str = Query(min_length=40, max_length=100),
):
    updated = _reschedule_meeting(
        payload.new_start,
        token_hash=_hash_reschedule_token(token),
    )
    return {
        "id": updated["id"],
        "meeting_date": updated["meeting_date"],
        "duration_minutes": updated["duration_minutes"],
    }


def _reschedule_meeting(
    new_start: datetime,
    *,
    advisor_id: int | None = None,
    meeting_id: int | None = None,
    token_hash: str | None = None,
) -> dict:
    with get_connection() as conn, conn.cursor() as cur:
        if token_hash is not None:
            cur.execute(
                "SELECT advisor_id FROM t_meetings WHERE reschedule_token_hash = %s",
                (token_hash,),
            )
            token_owner = cur.fetchone()
            if token_owner is None:
                raise HTTPException(status_code=404, detail="Reschedule link is invalid.")
            advisor_id = token_owner[0]

        if advisor_id is None:
            raise HTTPException(status_code=404, detail="Meeting not found.")
        cur.execute(
            "SELECT pg_advisory_xact_lock(%s, %s)",
            (26, advisor_id),
        )

        if token_hash is not None:
            cur.execute(
                """
                SELECT id, client_id, advisor_id, meeting_date,
                       duration_minutes, completion_status, google_calendar_id,
                       google_event_id
                FROM t_meetings
                WHERE reschedule_token_hash = %s
                FOR UPDATE
                """,
                (token_hash,),
            )
        else:
            cur.execute(
                """
                SELECT id, client_id, advisor_id, meeting_date,
                       duration_minutes, completion_status, google_calendar_id,
                       google_event_id
                FROM t_meetings
                WHERE id = %s AND advisor_id = %s
                FOR UPDATE
                """,
                (meeting_id, advisor_id),
            )

        meeting = cur.fetchone()

        if meeting is None:
            raise HTTPException(
                status_code=404,
                detail="Meeting not found.",
            )

        (
            current_id,
            _client_id,
            _current_advisor_id,
            _old_start,
            duration_minutes,
            status,
            google_calendar_id,
            google_event_id,
        ) = meeting

        if str(status) != "Scheduled":
            raise HTTPException(
                status_code=409,
                detail="Only scheduled meetings can be rescheduled.",
            )

        if not google_calendar_id or not google_event_id:
            raise HTTPException(
                status_code=409,
                detail="The meeting has no linked Google Calendar event.",
            )

        new_start = new_start.astimezone(UTC)
        new_end = new_start + timedelta(minutes=duration_minutes)

        # Find any overlapping scheduled meeting for this advisor.
        cur.execute(
            """
            SELECT id
            FROM t_meetings
            WHERE advisor_id = %s
              AND id <> %s
              AND completion_status = 'Scheduled'
              AND meeting_date < %s
              AND meeting_date
                  + (duration_minutes * INTERVAL '1 minute') > %s
            LIMIT 1
            """,
            (
                advisor_id,
                current_id,
                new_end,
                new_start,
            ),
        )

        if cur.fetchone() is not None:
            raise HTTPException(
                status_code=409,
                detail="The requested time conflicts with another meeting.",
            )

        _update_calendar_event(
            advisor_id,
            google_calendar_id,
            google_event_id,
            new_start,
            duration_minutes,
        )

        cur.execute(
            """
            UPDATE t_meetings
            SET meeting_date = %s,
                updated_at = NOW()
            WHERE id = %s AND advisor_id = %s
            RETURNING id, client_id, advisor_id, meeting_date,
                      duration_minutes, completion_status
            """,
            (new_start, current_id, advisor_id),
        )

        updated = cur.fetchone()

    return {
        "id": updated[0],
        "client_id": updated[1],
        "advisor_id": updated[2],
        "meeting_date": updated[3],
        "duration_minutes": updated[4],
        "completion_status": str(updated[5]),
    }


def _hash_reschedule_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _update_calendar_event(
    advisor_id: int,
    calendar_id: str,
    event_id: str,
    start: datetime,
    duration_minutes: int,
) -> None:
    from app.api.v1.routers.google_meet_integration import update_calendar_event

    update_calendar_event(advisor_id, calendar_id, event_id, start, duration_minutes)


def _require_matching_advisor(advisor_id: int, advisor: dict[str, int]) -> None:
    if int(advisor_id) != int(advisor["id"]):
        raise HTTPException(status_code=403, detail="Not authorized for this advisor.")
