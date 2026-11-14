# Below 50% AI-generated
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import httplib2
import pytest
from fastapi.testclient import TestClient
from google.api_core.exceptions import PermissionDenied
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from app.api.v1.routers import google_meet_integration as gmi
from app.api.versions import APIVersion, api_prefix
from app.auth import create_access_token
from app.core.config import settings
from app.core.security.token_cipher import decrypt_token, encrypt_token
from app.main import app

API_VERSION = APIVersion.V1
PREFIX = f"{api_prefix(API_VERSION)}/google-meet-integration"


# Stored credentials are encrypted at rest
CREDS_ROW = (encrypt_token(json.dumps({"token": "t"})),)

client = TestClient(
    app,
    headers={"Authorization": f"Bearer {create_access_token(1)}"},
    follow_redirects=False,
)


@pytest.fixture
def mock_db(monkeypatch):
    conn = MagicMock()
    cursor = MagicMock()

    conn.__enter__.return_value = conn
    conn.cursor.return_value.__enter__.return_value = cursor
    # Lets tests check whether the meeting transaction was committed
    cursor.connection = conn

    monkeypatch.setattr(gmi, "get_connection", lambda: conn)

    return cursor


@pytest.fixture
def mock_flow(monkeypatch):
    flow = MagicMock()
    flow.authorization_url.return_value = (
        "https://accounts.google.com/o/oauth2/auth?state=abc123",
        "abc123",
    )
    flow.code_verifier = "verifier-xyz"
    flow.credentials.to_json.return_value = json.dumps({"token": "t"})

    from_file = MagicMock(return_value=flow)
    monkeypatch.setattr(gmi.Flow, "from_client_secrets_file", from_file)

    return SimpleNamespace(flow=flow, from_file=from_file)


@pytest.fixture
def stored_creds(monkeypatch):
    creds = MagicMock()
    creds.valid = True
    creds.to_json.return_value = json.dumps({"token": "refreshed"})
    monkeypatch.setattr(
        gmi.Credentials, "from_authorized_user_info", MagicMock(return_value=creds)
    )
    return creds


@pytest.fixture
def mock_meet(monkeypatch):
    meet_client = MagicMock()
    meet_client.create_space.return_value = SimpleNamespace(
        name="spaces/abc",
        meeting_uri="https://meet.google.com/abc-defg-hij",
        meeting_code="abc-defg-hij",
    )
    monkeypatch.setattr(
        gmi.meet_v2, "SpacesServiceClient", MagicMock(return_value=meet_client)
    )
    return meet_client


def test_routes_require_authentication():
    anonymous = TestClient(app, follow_redirects=False)

    assert anonymous.get(f"{PREFIX}/authorize").status_code == 401
    assert anonymous.get(f"{PREFIX}/oauth2callback").status_code == 401
    assert anonymous.get(f"{PREFIX}/authorized").status_code == 401
    assert anonymous.get(f"{PREFIX}/status").status_code == 401
    assert anonymous.post(f"{PREFIX}/spaces").status_code == 401
    assert anonymous.post(f"{PREFIX}/meetings").status_code == 401


def test_authorized_returns_confirmation_message():
    response = client.get(f"{PREFIX}/authorized")

    assert response.status_code == 200
    assert response.json() == {"message": "Google authorization has been given."}


def test_authorize_redirects_to_google_and_sets_state_cookie(mock_flow):
    response = client.get(f"{PREFIX}/authorize")

    assert response.status_code == 307
    assert response.headers["location"].startswith("https://accounts.google.com/")
    assert response.cookies[gmi.OAUTH_STATE_COOKIE] == "abc123:verifier-xyz"

    mock_flow.flow.authorization_url.assert_called_once_with(
        access_type="offline", prompt="consent"
    )
    assert mock_flow.flow.redirect_uri == (
        f"{settings.api_url(API_VERSION)}/google-meet-integration/oauth2callback"
    )


def test_authorize_without_client_secrets_returns_503(monkeypatch):
    monkeypatch.setattr(
        gmi.Flow,
        "from_client_secrets_file",
        MagicMock(side_effect=FileNotFoundError),
    )

    response = client.get(f"{PREFIX}/authorize")

    assert response.status_code == 503


def test_callback_stores_credentials(mock_flow, mock_db):
    client.cookies.set(gmi.OAUTH_STATE_COOKIE, "abc123:verifier-xyz")
    try:
        response = client.get(
            f"{PREFIX}/oauth2callback", params={"code": "c0de", "state": "abc123"}
        )
    finally:
        client.cookies.clear()

    assert response.status_code == 303
    assert response.headers["location"] == f"{PREFIX}/authorized"

    # The state cookie is cleared once it has been used
    assert f'{gmi.OAUTH_STATE_COOKIE}=""' in response.headers["set-cookie"]

    kwargs = mock_flow.from_file.call_args.kwargs
    assert kwargs["state"] == "abc123"
    assert kwargs["code_verifier"] == "verifier-xyz"
    mock_flow.flow.fetch_token.assert_called_once_with(code="c0de")

    query, params = mock_db.execute.call_args.args
    assert "INSERT INTO google_oauth_credentials" in query
    advisor_id, stored = params
    assert advisor_id == 1
    # Tokens are stored encrypted, never as plain JSON
    assert '"token"' not in stored
    assert decrypt_token(stored) == json.dumps({"token": "t"})


def test_callback_rejects_mismatched_state(mock_flow, mock_db):
    client.cookies.set(gmi.OAUTH_STATE_COOKIE, "abc123:verifier-xyz")
    try:
        response = client.get(
            f"{PREFIX}/oauth2callback", params={"code": "c0de", "state": "forged"}
        )
    finally:
        client.cookies.clear()

    assert response.status_code == 400
    mock_flow.flow.fetch_token.assert_not_called()
    mock_db.execute.assert_not_called()


def test_callback_rejects_missing_state_cookie(mock_flow, mock_db):
    response = client.get(
        f"{PREFIX}/oauth2callback", params={"code": "c0de", "state": "abc123"}
    )

    assert response.status_code == 400
    mock_db.execute.assert_not_called()


def test_callback_handles_denied_consent(mock_flow, mock_db):
    response = client.get(f"{PREFIX}/oauth2callback", params={"error": "access_denied"})

    assert response.status_code == 403
    mock_db.execute.assert_not_called()


def test_callback_handles_other_google_errors(mock_flow, mock_db):
    response = client.get(f"{PREFIX}/oauth2callback", params={"error": "server_error"})

    assert response.status_code == 400
    mock_db.execute.assert_not_called()


def test_callback_handles_token_exchange_failure(mock_flow, mock_db):
    mock_flow.flow.fetch_token.side_effect = Exception("invalid_grant")
    client.cookies.set(gmi.OAUTH_STATE_COOKIE, "abc123:verifier-xyz")
    try:
        response = client.get(
            f"{PREFIX}/oauth2callback", params={"code": "c0de", "state": "abc123"}
        )
    finally:
        client.cookies.clear()

    assert response.status_code == 400
    mock_db.execute.assert_not_called()


def test_status_not_connected(mock_db):
    mock_db.fetchone.return_value = None

    response = client.get(f"{PREFIX}/status")

    assert response.status_code == 200
    assert response.json() == {"connected": False}


def test_status_connected(mock_db, stored_creds):
    mock_db.fetchone.return_value = CREDS_ROW

    response = client.get(f"{PREFIX}/status")

    assert response.json() == {"connected": True}
    _, params = mock_db.execute.call_args.args
    assert params == (1,)
    # The stored value is decrypted before Google's Credentials are built
    info, _ = gmi.Credentials.from_authorized_user_info.call_args.args
    assert info == {"token": "t"}


def test_credentials_encrypted_with_another_key_count_as_disconnected(mock_db):
    other_key = "b3RoZXIta2V5LWZvci10ZXN0aW5nLW9ubHktMzJieXQ="
    mock_db.fetchone.return_value = (
        encrypt_token(json.dumps({"token": "t"}), key=other_key),
    )

    response = client.get(f"{PREFIX}/status")

    assert response.json() == {"connected": False}


def test_create_space_without_connection_returns_409(mock_db):
    mock_db.fetchone.return_value = None

    response = client.post(f"{PREFIX}/spaces")

    assert response.status_code == 409


def test_create_space_returns_meeting_details(mock_db, stored_creds, mock_meet):
    mock_db.fetchone.return_value = CREDS_ROW

    response = client.post(f"{PREFIX}/spaces")

    assert response.status_code == 201
    assert response.json() == {
        "name": "spaces/abc",
        "meeting_uri": "https://meet.google.com/abc-defg-hij",
        "meeting_code": "abc-defg-hij",
    }
    stored_creds.refresh.assert_not_called()
    mock_meet.create_space.assert_called_once()


def test_create_space_refreshes_and_saves_expired_credentials(
    mock_db, stored_creds, mock_meet
):
    mock_db.fetchone.return_value = CREDS_ROW
    stored_creds.valid = False

    response = client.post(f"{PREFIX}/spaces")

    assert response.status_code == 201
    stored_creds.refresh.assert_called_once()
    query, params = mock_db.execute.call_args.args
    assert "INSERT INTO google_oauth_credentials" in query
    assert params[0] == 1
    assert decrypt_token(params[1]) == json.dumps({"token": "refreshed"})


def test_create_space_with_revoked_token_returns_409(mock_db, stored_creds, mock_meet):
    mock_db.fetchone.return_value = CREDS_ROW
    stored_creds.valid = False
    stored_creds.refresh.side_effect = RefreshError("revoked")

    response = client.post(f"{PREFIX}/spaces")

    assert response.status_code == 409
    mock_meet.create_space.assert_not_called()


def test_create_space_meet_api_error_returns_502(mock_db, stored_creds, mock_meet):
    mock_db.fetchone.return_value = CREDS_ROW
    mock_meet.create_space.side_effect = PermissionDenied("nope")

    response = client.post(f"{PREFIX}/spaces")

    assert response.status_code == 502


CLIENT_ROW = (1,)
MEETING_ROW = (42,)

EVENT = {
    "id": "evt123",
    "summary": "Portfolio review",
    "start": {"dateTime": "2026-11-10T14:00:00-05:00"},
    "end": {"dateTime": "2026-11-10T14:45:00-05:00"},
    "hangoutLink": "https://meet.google.com/abc-defg-hij",
    "htmlLink": "https://www.google.com/calendar/event?eid=evt123",
    "conferenceData": {"conferenceId": "abc-defg-hij"},
}


def _http_error(status: int) -> HttpError:
    return HttpError(httplib2.Response({"status": str(status)}), b"{}")


def _executed(mock_db, sql: str):
    return [call.args for call in mock_db.execute.call_args_list if sql in call.args[0]]


def _insert_calls(mock_db):
    return _executed(mock_db, "INSERT INTO t_meetings")


def _calendar_id_updates(mock_db):
    return [
        params
        for _, params in _executed(
            mock_db, "UPDATE google_oauth_credentials SET calendar_id"
        )
    ]


@pytest.fixture
def mock_calendar(monkeypatch):
    calendar = MagicMock()
    calendar.events.return_value.insert.return_value.execute.return_value = EVENT
    calendar.calendars.return_value.insert.return_value.execute.return_value = {
        "id": "orbit-cal"
    }
    build = MagicMock(return_value=calendar)
    monkeypatch.setattr(gmi, "build", build)
    return calendar


def test_create_meeting_schedules_calendar_event_with_meet(
    mock_db, stored_creds, mock_calendar
):
    # Credentials, client check, the advisor's Orbit calendar, inserted meeting id
    mock_db.fetchone.side_effect = [CREDS_ROW, CLIENT_ROW, ("cal-1",), MEETING_ROW]

    response = client.post(
        f"{PREFIX}/meetings",
        json={
            "client_id": 7,
            "title": "Portfolio review",
            "start": "2026-11-10T14:00:00-05:00",
            "duration_minutes": 45,
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "meeting_id": 42,
        "client_id": 7,
        "event_id": "evt123",
        "title": "Portfolio review",
        "start": "2026-11-10T14:00:00-05:00",
        "end": "2026-11-10T14:45:00-05:00",
        "meeting_uri": "https://meet.google.com/abc-defg-hij",
        "meeting_code": "abc-defg-hij",
        "calendar_link": "https://www.google.com/calendar/event?eid=evt123",
    }

    mock_calendar.calendars.assert_not_called()
    kwargs = mock_calendar.events.return_value.insert.call_args.kwargs
    assert kwargs["calendarId"] == "cal-1"
    assert kwargs["conferenceDataVersion"] == 1
    assert kwargs["sendUpdates"] == "all"
    body = kwargs["body"]
    assert "attendees" not in body
    assert body["summary"] == "Portfolio review"
    assert body["start"] == {"dateTime": "2026-11-10T14:00:00-05:00"}
    assert body["end"] == {"dateTime": "2026-11-10T14:45:00-05:00"}
    create_request = body["conferenceData"]["createRequest"]
    assert create_request["conferenceSolutionKey"] == {"type": "hangoutsMeet"}
    assert create_request["requestId"]


def test_create_meeting_saves_orbit_meeting(mock_db, stored_creds, mock_calendar):
    mock_db.fetchone.side_effect = [CREDS_ROW, CLIENT_ROW, ("cal-1",), MEETING_ROW]

    response = client.post(
        f"{PREFIX}/meetings",
        json={"client_id": 7, "start": "2026-11-10T14:00:00-05:00"},
    )

    assert response.status_code == 201
    # The client must belong to the advisor
    [(_, client_params)] = _executed(mock_db, "FROM t_clients")
    assert client_params == (7, 1)

    [(_, params)] = _insert_calls(mock_db)
    advisor_id, client_id, meeting_date, meeting_uri, meeting_code, duration = params
    assert (advisor_id, client_id) == (1, 7)
    assert duration == 60
    assert meeting_date.isoformat() == "2026-11-10T14:00:00-05:00"
    # The Meet link and code from Google are stored with the meeting
    assert meeting_uri == "https://meet.google.com/abc-defg-hij"
    assert meeting_code == "abc-defg-hij"
    mock_db.connection.commit.assert_called_once()


def test_create_meeting_uses_defaults(mock_db, stored_creds, mock_calendar):
    mock_db.fetchone.side_effect = [CREDS_ROW, CLIENT_ROW, ("cal-1",), MEETING_ROW]

    response = client.post(
        f"{PREFIX}/meetings", json={"client_id": 7, "start": "2026-11-10T19:00:00Z"}
    )

    assert response.status_code == 201
    body = mock_calendar.events.return_value.insert.call_args.kwargs["body"]
    assert body["summary"] == "Meeting"
    assert body["end"] == {"dateTime": "2026-11-10T20:00:00+00:00"}


def test_create_meeting_for_unknown_client_returns_404(
    mock_db, stored_creds, mock_calendar
):
    # The client check finds nothing when the client isn't this advisor's
    mock_db.fetchone.side_effect = [CREDS_ROW, None]

    response = client.post(
        f"{PREFIX}/meetings", json={"client_id": 99, "start": "2026-11-10T19:00:00Z"}
    )

    assert response.status_code == 404
    mock_calendar.events.assert_not_called()
    assert _insert_calls(mock_db) == []


def test_first_meeting_creates_orbit_calendar(mock_db, stored_creds, mock_calendar):
    mock_db.fetchone.side_effect = [CREDS_ROW, CLIENT_ROW, (None,), MEETING_ROW]

    response = client.post(
        f"{PREFIX}/meetings", json={"client_id": 7, "start": "2026-11-10T19:00:00Z"}
    )

    assert response.status_code == 201
    mock_calendar.calendars.return_value.insert.assert_called_once_with(
        body={"summary": gmi.ORBIT_CALENDAR_NAME}
    )
    assert _calendar_id_updates(mock_db) == [("orbit-cal", 1)]
    kwargs = mock_calendar.events.return_value.insert.call_args.kwargs
    assert kwargs["calendarId"] == "orbit-cal"


def test_deleted_orbit_calendar_is_recreated(mock_db, stored_creds, mock_calendar):
    mock_db.fetchone.side_effect = [
        CREDS_ROW,
        CLIENT_ROW,
        ("deleted-cal",),
        MEETING_ROW,
    ]
    mock_calendar.events.return_value.insert.return_value.execute.side_effect = [
        _http_error(404),
        EVENT,
    ]

    response = client.post(
        f"{PREFIX}/meetings", json={"client_id": 7, "start": "2026-11-10T19:00:00Z"}
    )

    assert response.status_code == 201
    calendar_ids = [
        call.kwargs["calendarId"]
        for call in mock_calendar.events.return_value.insert.call_args_list
    ]
    assert calendar_ids == ["deleted-cal", "orbit-cal"]
    assert _calendar_id_updates(mock_db) == [("orbit-cal", 1)]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"start": "2026-11-10T14:00:00Z"},  # no client
        {"client_id": 0, "start": "2026-11-10T14:00:00Z"},
        {"client_id": 7},  # no start
        {"client_id": 7, "start": "2026-11-10T14:00:00"},  # no UTC offset
        {"client_id": 7, "start": "not-a-date"},
        {"client_id": 7, "start": "2026-11-10T14:00:00Z", "duration_minutes": 0},
        {
            "client_id": 7,
            "start": "2026-11-10T14:00:00Z",
            "duration_minutes": 24 * 60 + 1,
        },
        {"client_id": 7, "start": "2026-11-10T14:00:00Z", "title": ""},
    ],
)
def test_create_meeting_rejects_invalid_payload(mock_db, mock_calendar, payload):
    response = client.post(f"{PREFIX}/meetings", json=payload)

    assert response.status_code == 422
    mock_db.execute.assert_not_called()
    mock_calendar.events.assert_not_called()


def test_create_meeting_without_connection_returns_409(mock_db, mock_calendar):
    mock_db.fetchone.return_value = None

    response = client.post(
        f"{PREFIX}/meetings", json={"client_id": 7, "start": "2026-11-10T14:00:00Z"}
    )

    assert response.status_code == 409
    assert _insert_calls(mock_db) == []
    mock_calendar.events.assert_not_called()


def test_create_meeting_calendar_api_error_returns_502(
    mock_db, stored_creds, mock_calendar
):
    mock_db.fetchone.side_effect = [CREDS_ROW, CLIENT_ROW, ("cal-1",)]
    mock_calendar.events.return_value.insert.return_value.execute.side_effect = (
        _http_error(403)
    )

    response = client.post(
        f"{PREFIX}/meetings", json={"client_id": 7, "start": "2026-11-10T14:00:00Z"}
    )

    assert response.status_code == 502
    # No Orbit meeting is recorded when Google didn't create one
    assert _insert_calls(mock_db) == []


# Public booking route; no Orbit login
public_client = TestClient(app)

BOOKING = {
    "email": "jane@example.com",
    "name": "Jane Doe",
    "phone_number": "555-0100",
    "start": "2030-01-15T14:00:00-05:00",
}


def test_book_meeting_for_existing_client(mock_db, stored_creds, mock_calendar):
    # Credentials, existing client of advisor 1, then _schedule_calendar_event's
    # client check, Orbit calendar and inserted meeting id
    mock_db.fetchone.side_effect = [
        CREDS_ROW,
        (7, 1),
        CLIENT_ROW,
        ("cal-1",),
        MEETING_ROW,
    ]

    response = public_client.post(f"{PREFIX}/book/1", json=BOOKING)

    assert response.status_code == 201
    assert response.json() == {
        "meeting_id": 42,
        "title": "Portfolio review",
        "start": "2026-11-10T14:00:00-05:00",
        "end": "2026-11-10T14:45:00-05:00",
        "meeting_uri": "https://meet.google.com/abc-defg-hij",
        "meeting_code": "abc-defg-hij",
    }

    kwargs = mock_calendar.events.return_value.insert.call_args.kwargs
    assert kwargs["calendarId"] == "cal-1"
    assert kwargs["sendUpdates"] == "all"
    body = kwargs["body"]
    # The user is invited at the email they entered
    assert body["attendees"] == [
        {"email": "jane@example.com", "displayName": "Jane Doe"}
    ]
    assert body["summary"] == "Meeting"
    assert body["start"] == {"dateTime": "2030-01-15T14:00:00-05:00"}
    assert body["end"] == {"dateTime": "2030-01-15T15:00:00-05:00"}

    assert _executed(mock_db, "INSERT INTO t_clients") == []
    [(_, params)] = _insert_calls(mock_db)
    assert params[:2] == (1, 7)
    assert params[3:] == ("https://meet.google.com/abc-defg-hij", "abc-defg-hij", 60)


def test_book_meeting_creates_new_client(mock_db, stored_creds, mock_calendar):
    mock_db.fetchone.side_effect = [
        CREDS_ROW,
        None,  # no client with this email
        (8,),  # new client id
        CLIENT_ROW,
        ("cal-1",),
        MEETING_ROW,
    ]

    response = public_client.post(f"{PREFIX}/book/1", json=BOOKING)

    assert response.status_code == 201
    [(_, client_params)] = _executed(mock_db, "INSERT INTO t_clients")
    assert client_params == ("Jane Doe", "jane@example.com", "555-0100", 1)
    [(_, meeting_params)] = _insert_calls(mock_db)
    assert meeting_params[:2] == (1, 8)


def test_book_meeting_uses_title_and_duration(mock_db, stored_creds, mock_calendar):
    mock_db.fetchone.side_effect = [
        CREDS_ROW,
        (7, 1),
        CLIENT_ROW,
        ("cal-1",),
        MEETING_ROW,
    ]

    response = public_client.post(
        f"{PREFIX}/book/1",
        json={**BOOKING, "title": "Retirement planning", "duration_minutes": 30},
    )

    assert response.status_code == 201
    body = mock_calendar.events.return_value.insert.call_args.kwargs["body"]
    assert body["summary"] == "Retirement planning"
    assert body["end"] == {"dateTime": "2030-01-15T14:30:00-05:00"}
    # The duration is also saved on the Orbit meeting
    [(_, params)] = _insert_calls(mock_db)
    assert params[5] == 30


def test_book_meeting_in_the_past_returns_422(mock_db, mock_calendar):
    response = public_client.post(
        f"{PREFIX}/book/1", json={**BOOKING, "start": "2020-01-15T14:00:00-05:00"}
    )

    assert response.status_code == 422
    mock_db.execute.assert_not_called()
    mock_calendar.events.assert_not_called()


@pytest.mark.parametrize(
    "changes",
    [
        {"email": "not-an-email"},
        {"name": ""},
        {"phone_number": ""},
        {"phone_number": "5" * 33},
        {"start": "2030-01-15T14:00:00"},  # no UTC offset
        {"duration_minutes": 0},
        {"title": ""},
    ],
)
def test_book_meeting_rejects_invalid_payload(mock_db, mock_calendar, changes):
    response = public_client.post(f"{PREFIX}/book/1", json={**BOOKING, **changes})

    assert response.status_code == 422
    mock_db.execute.assert_not_called()


def test_book_meeting_with_unconnected_advisor_returns_404(mock_db, mock_calendar):
    mock_db.fetchone.return_value = None

    response = public_client.post(f"{PREFIX}/book/99", json=BOOKING)

    assert response.status_code == 404
    mock_calendar.events.assert_not_called()


def test_book_meeting_with_another_advisors_client_returns_409(
    mock_db, stored_creds, mock_calendar
):
    mock_db.fetchone.side_effect = [CREDS_ROW, (7, 2)]

    response = public_client.post(f"{PREFIX}/book/1", json=BOOKING)

    assert response.status_code == 409
    mock_calendar.events.assert_not_called()
    assert _insert_calls(mock_db) == []


def test_book_meeting_with_taken_phone_number_returns_409(
    mock_db, stored_creds, mock_calendar
):
    mock_db.fetchone.side_effect = [CREDS_ROW, None]

    def execute(query, params=None):
        if "INSERT INTO t_clients" in query:
            raise gmi.UniqueViolation()

    mock_db.execute.side_effect = execute

    response = public_client.post(f"{PREFIX}/book/1", json=BOOKING)

    assert response.status_code == 409
    mock_calendar.events.assert_not_called()
