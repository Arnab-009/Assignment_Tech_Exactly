"""FastAPI application entry point and wiring."""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware

from app import __version__
from app.config import get_settings
from app.exceptions import AppError
from app.logging_config import configure_logging
from app.models.schemas import HealthResponse
from app.routers import auth, drive, export, summarize

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    # Instantiating settings here makes the app fail fast (with a clear error)
    # if any required secret is missing, rather than at first request.
    settings = get_settings()
    configure_logging(settings.log_level)

    # Google appends the `openid` scope to what we request; relaxing the scope
    # check avoids a spurious mismatch warning/error. INSECURE_TRANSPORT lets
    # the OAuth flow run over plain http for local development only.
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    if settings.insecure_oauth:
        os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

    app = FastAPI(
        title="Document Summarizer",
        description="Summarize Google Drive documents (PDF/DOCX/TXT) with Gemini.",
        version=__version__,
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        session_cookie=settings.session_cookie,
        max_age=settings.session_max_age,
        same_site="lax",
        https_only=settings.session_https_only,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(drive.router)
    app.include_router(summarize.router)
    app.include_router(export.router)

    _register_exception_handlers(app)

    @app.get("/api/health", response_model=HealthResponse, tags=["meta"])
    def health() -> HealthResponse:
        return HealthResponse(version=__version__)

    logger.info("Document Summarizer v%s initialised", __version__)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code, content={"detail": exc.detail}
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": "Invalid request.", "errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "Unhandled error on %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=500, content={"detail": "Internal server error."}
        )


app = create_app()
