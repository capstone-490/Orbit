# Below 50% AI-generated
import json
import os
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Cookie, Depends, HTTPException
from fastapi.responses import RedirectResponse
from google.api_core.exceptions import GoogleAPICallError
from google.apps import meet_v2
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from psycopg.errors import UniqueViolation
from pydantic import AwareDatetime, BaseModel, EmailStr, Field

from app.auth import get_current_advisor
from app.core.config import settings
from app.core.security.token_cipher import (
    InvalidToken,
    decrypt_token,
    encrypt_token,
)
from app.dependencies.db import get_connection
from app.logging_config import get_logger

logger = get_logger("google_meet_integration")

# If modifying these scopes, every advisor must reconnect their Google account.
SCOPES = [
    "https://www.googleapis.com/auth/meetings.space.created",
    # Scheduled meetings are Calendar events with a Meet link attached. This
    # scope only covers calendars Orbit creates, so meetings go on a dedicated
    # secondary calendar and Orbit never sees the advisor's other events.
    "https://www.googleapis.com/auth/calendar.app.created",
]

OAUTH_STATE_COOKIE = "google_oauth_state"
OAUTH_STATE_MAX_AGE = 600

ORBIT_CALENDAR_NAME = "Orbit Meetings"

router = APIRouter(
    prefix="/google-meet-integration",
    tags=["Google Meet Integration"],
    dependencies=[Depends(get_current_advisor)],
)

# Routes for users who aren't advisors; no Orbit login required.
public_router = APIRouter(
    prefix="/google-meet-integration",
    tags=["Google Meet Integration"],
)


class MeetingCreate(BaseModel):
    client_id: int = Field(gt=0)
    title: str = Field(default="Meeting", min_length=1, max_length=200)
    # Must include a UTC offset, e.g. 2026-11-10T14:00:00-05:00
    start: AwareDatetime
    duration_minutes: int = Field(default=60, ge=1, le=24 * 60)


class BookingCreate(BaseModel):
    # The user is invited to the meeting at this email
    email: EmailStr
    # name and phone_number are required to create a client record
    name: str = Field(min_length=1, max_length=200)
    phone_number: str = Field(min_length=1, max_length=32)
    title: str = Field(default="Meeting", min_length=1, max_length=200)
    # Must include a UTC offset, e.g. 2026-11-10T14:00:00-05:00
    start: AwareDatetime
    duration_minutes: int = Field(default=60, ge=1, le=24 * 60)


@router.get("/authorize")
def authorize():
    flow = _build_flow()

    authorization_url, state = flow.authorization_url(
        # Offline access returns a refresh token so we can create meetings later
        # without re-prompting; prompt=consent guarantees one on reconnect too.
        access_type="offline",
        prompt="consent",
    )

    response = RedirectResponse(authorization_url)
    # The callback needs the state (CSRF check) and the PKCE code verifier
    # generated for this flow.
    response.set_cookie(
        key=OAUTH_STATE_COOKIE,
        value=f"{state}:{flow.code_verifier}",
        max_age=OAUTH_STATE_MAX_AGE,
        httponly=True,
        secure=os.environ.get("ORBIT_COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path=router.prefix,
    )
    return response


@router.get("/oauth2callback")
def oauth2callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    oauth_state: str = Cookie(default="", alias=OAUTH_STATE_COOKIE),
    advisor: dict[str, int] = Depends(get_current_advisor),
):
    stored_state, _, code_verifier = oauth_state.partition(":")

    if error == "access_denied":
        # The advisor cancelled on the consent screen
        raise HTTPException(status_code=403, detail="Google authorization denied.")
    if error:
        raise HTTPException(status_code=400, detail="Google authorization failed.")
    if not code or not state or not stored_state or state != stored_state:
        raise HTTPException(status_code=400, detail="Invalid OAuth state.")

    flow = _build_flow(state=state, code_verifier=code_verifier)
    try:
        flow.fetch_token(code=code)
    except Exception:
        # Usually an expired or already-used authorization code
        logger.exception("Google OAuth token exchange failed")
        raise HTTPException(
            status_code=400, detail="Google authorization failed."
        ) from None

    _save_credentials(advisor["id"], flow.credentials)

    # Redirect so the one-time code leaves the address bar and a refresh
    # doesn't try to exchange it again.
    response = RedirectResponse(router.url_path_for("authorized"), status_code=303)
    response.delete_cookie(OAUTH_STATE_COOKIE, path=router.prefix)
    return response


@router.get("/authorized")
def authorized():
    return {"message": "Google authorization has been given."}


@router.get("/status")
def connection_status(advisor: dict[str, int] = Depends(get_current_advisor)):
    return {"connected": _load_credentials(advisor["id"]) is not None}


@router.post("/spaces", status_code=201)
def create_space(advisor: dict[str, int] = Depends(get_current_advisor)):
    creds = _get_valid_credentials(advisor["id"])

    try:
        client = meet_v2.SpacesServiceClient(credentials=creds)
        space = client.create_space(request=meet_v2.CreateSpaceRequest())
    except GoogleAPICallError:
        logger.exception("Google Meet space creation failed")
        raise HTTPException(
            status_code=502, detail="Could not create Google Meet space."
        ) from None

    return {
        "name": space.name,
        "meeting_uri": space.meeting_uri,
        "meeting_code": space.meeting_code,
    }


@router.post("/meetings", status_code=201)
def create_meeting(
    meeting: MeetingCreate, advisor: dict[str, int] = Depends(get_current_advisor)
):
    creds = _get_valid_credentials(advisor["id"])
    event_body = _build_event_body(
        meeting.title, meeting.start, meeting.duration_minutes
    )

    meeting_id, event = _schedule_calendar_event(
        creds, advisor["id"], meeting.client_id, meeting.start, event_body
    )

    return {
        "meeting_id": meeting_id,
        "client_id": meeting.client_id,
        "event_id": event["id"],
        "title": event.get("summary"),
        "start": event["start"]["dateTime"],
        "end": event["end"]["dateTime"],
        "meeting_uri": event.get("hangoutLink"),
        "meeting_code": _meeting_code(event),
        "calendar_link": event.get("htmlLink"),
    }


@public_router.post("/book/{advisor_id}", status_code=201)
def book_meeting(advisor_id: int, booking: BookingCreate):
    if booking.start <= datetime.now(UTC):
        raise HTTPException(status_code=422, detail="Meeting must be in the future.")

    try:
        creds = _get_valid_credentials(advisor_id)
    except HTTPException:
        # Unknown advisor, or one whose Google account isn't connected
        raise HTTPException(
            status_code=404, detail="Advisor is not accepting bookings."
        ) from None

    client_id = _get_or_create_booking_client(advisor_id, booking)
    event_body = _build_event_body(
        booking.title,
        booking.start,
        booking.duration_minutes,
        attendees=[{"email": booking.email, "displayName": booking.name}],
    )

    meeting_id, event = _schedule_calendar_event(
        creds, advisor_id, client_id, booking.start, event_body
    )

    return {
        "meeting_id": meeting_id,
        "title": event.get("summary"),
        "start": event["start"]["dateTime"],
        "end": event["end"]["dateTime"],
        "meeting_uri": event.get("hangoutLink"),
        "meeting_code": _meeting_code(event),
    }


def _get_or_create_booking_client(advisor_id: int, booking: BookingCreate) -> int:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT id, advisor_id FROM clients WHERE lower(email) = lower(%s)",
            (booking.email,),
        )
        row = cur.fetchone()
        if row is not None:
            if row[1] != advisor_id:
                # Deliberately vague: don't reveal who another advisor's clients are
                raise HTTPException(
                    status_code=409,
                    detail="This email can't be used to book with this advisor.",
                )
            return row[0]

        try:
            cur.execute(
                """
                    INSERT INTO clients (name, email, phone_number, advisor_id)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                (booking.name, booking.email, booking.phone_number, advisor_id),
            )
        except UniqueViolation:
            raise HTTPException(
                status_code=409,
                detail="This phone number can't be used to book with this advisor.",
            ) from None
        client_id = cur.fetchone()[0]
        conn.commit()

    return client_id


def _build_event_body(
    title: str,
    start: datetime,
    duration_minutes: int,
    attendees: list[dict] | None = None,
) -> dict:
    end = start + timedelta(minutes=duration_minutes)
    event_body: dict[str, Any] = {
        "summary": title,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
        "conferenceData": {
            "createRequest": {
                # Unique per request so Google doesn't dedupe separate meetings
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }
    if attendees:
        event_body["attendees"] = attendees
    return event_body


def _meeting_code(event: dict) -> str | None:
    # The Meet code, e.g. abc-defg-hij
    return event.get("conferenceData", {}).get("conferenceId")


def _schedule_calendar_event(
    creds: Credentials,
    advisor_id: int,
    client_id: int,
    meeting_date: datetime,
    event_body: dict,
) -> tuple[int, dict]:
    # Check the client first so no Google event is created for a client that
    # isn't this advisor's.
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM clients WHERE id = %s AND advisor_id = %s",
            (client_id, advisor_id),
        )
        if cur.fetchone() is None:
            raise HTTPException(status_code=404, detail="Client not found.")

    try:
        calendar = build("calendar", "v3", credentials=creds, cache_discovery=False)
        calendar_id = _load_calendar_id(advisor_id)
        if calendar_id is None:
            calendar_id = _create_orbit_calendar(calendar, advisor_id)

        try:
            event = _insert_event(calendar, calendar_id, event_body)
        except HttpError as error:
            if error.resp.status != 404:
                raise
            # The advisor deleted the Orbit calendar in Google; make a new one.
            calendar_id = _create_orbit_calendar(calendar, advisor_id)
            event = _insert_event(calendar, calendar_id, event_body)
    except HttpError:
        logger.exception("Google Calendar meeting creation failed")
        raise HTTPException(
            status_code=502, detail="Could not create Google Meet meeting."
        ) from None

    # Only record the meeting in Orbit once Google has created it.
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO meetings (
                    advisor_id, client_id, meeting_date, meeting_uri, meeting_code
                )
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
            (
                advisor_id,
                client_id,
                meeting_date,
                event.get("hangoutLink"),
                _meeting_code(event),
            ),
        )
        meeting_id = cur.fetchone()[0]
        conn.commit()

    return meeting_id, event


def _insert_event(calendar, calendar_id: str, event_body: dict) -> dict:
    return (
        calendar.events()
        .insert(
            calendarId=calendar_id,
            body=event_body,
            conferenceDataVersion=1,
            # Email invites to any attendees (bookings add the user)
            sendUpdates="all",
        )
        .execute()
    )


def _create_orbit_calendar(calendar, advisor_id: int) -> str:
    created = (
        calendar.calendars().insert(body={"summary": ORBIT_CALENDAR_NAME}).execute()
    )

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE google_oauth_credentials SET calendar_id = %s WHERE advisor_id = %s",
            (created["id"], advisor_id),
        )
        conn.commit()

    return created["id"]


def _load_calendar_id(advisor_id: int) -> str | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT calendar_id FROM google_oauth_credentials WHERE advisor_id = %s",
            (advisor_id,),
        )
        row = cur.fetchone()

    return row[0] if row else None


def _get_valid_credentials(advisor_id: int) -> Credentials:
    creds = _load_credentials(advisor_id)
    if creds is None:
        raise HTTPException(status_code=409, detail="Google account not connected.")

    if not creds.valid:
        try:
            creds.refresh(GoogleRequest())
        except RefreshError:
            # Refresh token was revoked or expired; the advisor must reconnect.
            raise HTTPException(
                status_code=409, detail="Google account must be reconnected."
            ) from None
        _save_credentials(advisor_id, creds)

    return creds


def _build_flow(state: str | None = None, code_verifier: str | None = None) -> Flow:
    try:
        flow = Flow.from_client_secrets_file(
            settings.GOOGLE_CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            state=state,
            code_verifier=code_verifier or None,
            autogenerate_code_verifier=code_verifier is None,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=503, detail="Google integration is not configured."
        ) from None

    # Google redirects back to this backend's oauth2callback route. It must
    # exactly match an authorized redirect URI on the OAuth client in the Google
    # Cloud Console, and Google requires an absolute URI, hence the backend host.
    flow.redirect_uri = f"{settings.BACKEND_URL}{router.url_path_for('oauth2callback')}"
    return flow


def _load_credentials(advisor_id: int) -> Credentials | None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT credentials FROM google_oauth_credentials WHERE advisor_id = %s",
            (advisor_id,),
        )
        row = cur.fetchone()

    if row is None:
        return None

    try:
        info = json.loads(decrypt_token(row[0]))
    except InvalidToken:
        # Encrypted with a different key (e.g. it was rotated); treat the
        # account as disconnected so the advisor reconnects and overwrites it.
        logger.warning("Stored Google credentials could not be decrypted")
        return None
    return Credentials.from_authorized_user_info(info, SCOPES)


def _save_credentials(advisor_id: int, creds: Credentials) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO google_oauth_credentials (advisor_id, credentials)
                VALUES (%s, %s)
                ON CONFLICT (advisor_id) DO UPDATE
                SET credentials = EXCLUDED.credentials, updated_at = NOW()
                """,
            (advisor_id, encrypt_token(creds.to_json())),
        )
        conn.commit()
