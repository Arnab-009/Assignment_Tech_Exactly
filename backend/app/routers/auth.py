"""Google OAuth2 authentication routes."""
from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow

from app.config import Settings, get_settings
from app.dependencies import (
    SESSION_CREDENTIALS_KEY,
    SESSION_EMAIL_KEY,
    credentials_to_dict,
)
from app.models.schemas import AuthStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Read-only Drive access plus the user's email for display.
SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

_STATE_KEY = "oauth_state"
_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def _build_flow(settings: Settings, state: str | None = None) -> Flow:
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES, state=state)
    flow.redirect_uri = settings.google_redirect_uri
    return flow


@router.get("/login")
def login(request: Request) -> RedirectResponse:
    """Build the Google consent URL and redirect the user to it."""
    settings = get_settings()
    flow = _build_flow(settings)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session[_STATE_KEY] = state
    return RedirectResponse(auth_url, status_code=307)


@router.get("/callback")
async def callback(request: Request) -> RedirectResponse:
    """Handle the OAuth redirect: validate state, exchange code, store token."""
    settings = get_settings()

    if error := request.query_params.get("error"):
        return _redirect_with_error(settings, error)

    state = request.session.get(_STATE_KEY)
    if not state or state != request.query_params.get("state"):
        return _redirect_with_error(settings, "invalid_state")

    code = request.query_params.get("code")
    if not code:
        return _redirect_with_error(settings, "missing_code")

    flow = _build_flow(settings, state=state)
    try:
        # Exchange the code directly (robust behind a reverse proxy, where the
        # raw request URL host/scheme may differ from the public redirect URI).
        flow.fetch_token(code=code)
    except Exception as exc:  # noqa: BLE001
        logger.warning("OAuth token exchange failed: %s", exc)
        return _redirect_with_error(settings, "token_exchange_failed")

    creds = flow.credentials
    request.session[SESSION_CREDENTIALS_KEY] = credentials_to_dict(creds)
    request.session.pop(_STATE_KEY, None)

    if email := await _fetch_email(creds.token):
        request.session[SESSION_EMAIL_KEY] = email

    return RedirectResponse(settings.post_login_redirect, status_code=307)


@router.get("/logout")
@router.post("/logout")
def logout(request: Request) -> JSONResponse:
    request.session.clear()
    return JSONResponse({"authenticated": False})


@router.get("/status", response_model=AuthStatus)
def status(request: Request) -> AuthStatus:
    settings = get_settings()
    return AuthStatus(
        authenticated=bool(request.session.get(SESSION_CREDENTIALS_KEY)),
        email=request.session.get(SESSION_EMAIL_KEY),
        default_folder_id=settings.default_folder_id,
    )


async def _fetch_email(access_token: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                _USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
        if resp.status_code == 200:
            return resp.json().get("email")
    except Exception as exc:  # noqa: BLE001 - email is best-effort only
        logger.info("Could not fetch user email: %s", exc)
    return None


def _redirect_with_error(settings: Settings, code: str) -> RedirectResponse:
    separator = "&" if "?" in settings.post_login_redirect else "?"
    return RedirectResponse(
        f"{settings.post_login_redirect}{separator}auth_error={code}",
        status_code=307,
    )
