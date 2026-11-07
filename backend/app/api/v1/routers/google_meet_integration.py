# Below 50% AI-generated
import os

from fastapi import APIRouter, Cookie, Depends, HTTPException
from fastapi.responses import RedirectResponse
from google.api_core.exceptions import GoogleAPICallError
from google.apps import meet_v2
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.auth import get_current_advisor
from app.core.config import settings
from app.dependencies.db import get_connection
from app.logging_config import get_logger

logger = get_logger("google_meet_integration")

# If modifying these scopes, every advisor must reconnect their Google account.
SCOPES = ["https://www.googleapis.com/auth/meetings.space.created"]

OAUTH_STATE_COOKIE = "google_oauth_state"
OAUTH_STATE_MAX_AGE = 600

router = APIRouter(
    prefix="/google-meet-integration",
    tags=["Google Meet Integration"],
    dependencies=[Depends(get_current_advisor)],
)


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
    creds = _load_credentials(advisor["id"])
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
        _save_credentials(advisor["id"], creds)

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
    return Credentials.from_authorized_user_info(row[0], SCOPES)


def _save_credentials(advisor_id: int, creds: Credentials) -> None:
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
                INSERT INTO google_oauth_credentials (advisor_id, credentials)
                VALUES (%s, %s::jsonb)
                ON CONFLICT (advisor_id) DO UPDATE
                SET credentials = EXCLUDED.credentials, updated_at = NOW()
                """,
            (advisor_id, creds.to_json()),
        )
        conn.commit()
