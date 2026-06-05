"""FastAPI dependencies: auth credentials, session id, service singletons."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from functools import lru_cache

from fastapi import Request
from fastapi.concurrency import run_in_threadpool
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials

from app.cache import ResultStore
from app.config import get_settings
from app.exceptions import NotAuthenticatedError
from app.services.drive_service import DriveService
from app.services.export_service import ExportService
from app.services.llm_service import LLMService
from app.services.parser_service import ParserService

logger = logging.getLogger(__name__)

SESSION_CREDENTIALS_KEY = "credentials"
SESSION_EMAIL_KEY = "email"
SESSION_ID_KEY = "sid"


# -- Credential (de)serialization ------------------------------------------
def credentials_to_dict(creds: Credentials) -> dict:
    """Serialize OAuth credentials for storage in the signed session cookie."""
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }


def dict_to_credentials(data: dict) -> Credentials:
    creds = Credentials(
        token=data.get("token"),
        refresh_token=data.get("refresh_token"),
        token_uri=data.get("token_uri"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        scopes=data.get("scopes"),
    )
    raw_expiry = data.get("expiry")
    if raw_expiry:
        try:
            creds.expiry = datetime.fromisoformat(raw_expiry)
        except ValueError:
            creds.expiry = None
    return creds


# -- Request-scoped dependencies -------------------------------------------
def get_session_id(request: Request) -> str:
    """Return a stable per-session id, creating one on first use."""
    sid = request.session.get(SESSION_ID_KEY)
    if not sid:
        sid = uuid.uuid4().hex
        request.session[SESSION_ID_KEY] = sid
    return sid


async def get_current_credentials(request: Request) -> Credentials:
    """Return valid Google credentials for the session or raise 401.

    Expired access tokens are refreshed transparently (in a threadpool, since
    the Google refresh call is blocking) and persisted back to the session.
    """
    data = request.session.get(SESSION_CREDENTIALS_KEY)
    if not data:
        raise NotAuthenticatedError()

    creds = dict_to_credentials(data)
    if creds.expired and creds.refresh_token:
        try:
            await run_in_threadpool(creds.refresh, GoogleAuthRequest())
            request.session[SESSION_CREDENTIALS_KEY] = credentials_to_dict(creds)
        except Exception as exc:  # noqa: BLE001 - any refresh failure => re-auth
            logger.warning("Token refresh failed: %s", exc)
            raise NotAuthenticatedError(
                "Your session has expired. Please reconnect Google Drive."
            ) from exc
    return creds


# -- Service singletons -----------------------------------------------------
# Services are stateless (or hold only config + a client), so a single cached
# instance per process is both correct and efficient.
@lru_cache
def get_drive_service() -> DriveService:
    settings = get_settings()
    return DriveService(
        max_files=settings.max_files_per_run,
        max_file_size_bytes=settings.max_file_size_bytes,
    )


@lru_cache
def get_parser_service() -> ParserService:
    return ParserService(max_chars=get_settings().max_text_chars)


@lru_cache
def get_llm_service() -> LLMService:
    settings = get_settings()
    return LLMService(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        concurrency=settings.llm_concurrency,
        max_chars=settings.max_text_chars,
        timeout_seconds=settings.llm_timeout_seconds,
    )


@lru_cache
def get_export_service() -> ExportService:
    return ExportService()


@lru_cache
def get_result_store() -> ResultStore:
    return ResultStore(ttl_seconds=get_settings().result_ttl_seconds)
