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
from app.auth import create_access_token
from app.main import app

PREFIX = "/google-meet-integration"

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
        f"{gmi.settings.BACKEND_URL}{PREFIX}/oauth2callback"
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
    assert params == (1, json.dumps({"token": "t"}))


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
    mock_db.fetchone.return_value = ({"token": "t"},)

    response = client.get(f"{PREFIX}/status")

    assert response.json() == {"connected": True}
    _, params = mock_db.execute.call_args.args
    assert params == (1,)


def test_create_space_without_connection_returns_409(mock_db):
    mock_db.fetchone.return_value = None

    response = client.post(f"{PREFIX}/spaces")

    assert response.status_code == 409


def test_create_space_returns_meeting_details(mock_db, stored_creds, mock_meet):
    mock_db.fetchone.return_value = ({"token": "t"},)

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
    mock_db.fetchone.return_value = ({"token": "t"},)
    stored_creds.valid = False

    response = client.post(f"{PREFIX}/spaces")

    assert response.status_code == 201
    stored_creds.refresh.assert_called_once()
    query, params = mock_db.execute.call_args.args
    assert "INSERT INTO google_oauth_credentials" in query
    assert params == (1, json.dumps({"token": "refreshed"}))


def test_create_space_with_revoked_token_returns_409(mock_db, stored_creds, mock_meet):
    mock_db.fetchone.return_value = ({"token": "t"},)
    stored_creds.valid = False
    stored_creds.refresh.side_effect = RefreshError("revoked")

    response = client.post(f"{PREFIX}/spaces")

    assert response.status_code == 409
    mock_meet.create_space.assert_not_called()


def test_create_space_meet_api_error_returns_502(mock_db, stored_creds, mock_meet):
    mock_db.fetchone.return_value = ({"token": "t"},)
    mock_meet.create_space.side_effect = PermissionDenied("nope")

    response = client.post(f"{PREFIX}/spaces")

    assert response.status_code == 502


CREDS_ROW = ({"token": "t"},)
CLIENT_ROW = (1,)
MEETING_ROW = (42,)

EVENT = {
    "id": "evt123",
    "summary": "Portfolio review",
    "start": {"dateTime": "2026-11-10T14:00:00-05:00"},
    "end": {"dateTime": "2026-11-10T14:45:00-05:00"},
    "hangoutLink": "https://meet.google.com/abc-defg-hij",
    "htmlLink": "https://www.google.com/calendar/event?eid=evt123",
}


def _http_error(status: int) -> HttpError:
    return HttpError(httplib2.Response({"status": str(status)}), b"{}")


def _executed(mock_db, sql: str):
    return [call.args for call in mock_db.execute.call_args_list if sql in call.args[0]]


def _insert_calls(mock_db):
    return _executed(mock_db, "INSERT INTO meetings")


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
        "calendar_link": "https://www.google.com/calendar/event?eid=evt123",
    }

    mock_calendar.calendars.assert_not_called()
    kwargs = mock_calendar.events.return_value.insert.call_args.kwargs
    assert kwargs["calendarId"] == "cal-1"
    assert kwargs["conferenceDataVersion"] == 1
    body = kwargs["body"]
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
    [(_, client_params)] = _executed(mock_db, "FROM clients")
    assert client_params == (7, 1)

    [(_, params)] = _insert_calls(mock_db)
    advisor_id, client_id, meeting_date = params
    assert (advisor_id, client_id) == (1, 7)
    assert meeting_date.isoformat() == "2026-11-10T14:00:00-05:00"
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
