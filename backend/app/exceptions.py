"""Application-specific exceptions.

Each exception carries the HTTP status code and a user-safe ``detail`` message.
A single exception handler (see :mod:`app.main`) translates them into clean
JSON responses, so routers and services can raise domain errors without
worrying about HTTP plumbing.
"""
from __future__ import annotations

from typing import Optional


class AppError(Exception):
    """Base class for all expected, user-facing application errors."""

    status_code: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: Optional[str] = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotAuthenticatedError(AppError):
    status_code = 401
    detail = "Not authenticated. Please connect your Google Drive account."


class FolderNotFoundError(AppError):
    status_code = 404
    detail = "Folder not found, empty, or not accessible with this account."


class DrivePermissionError(AppError):
    status_code = 403
    detail = (
        "Permission denied. Make sure the folder is shared with the "
        "authenticated Google account."
    )


class DriveApiError(AppError):
    status_code = 502
    detail = "Google Drive API request failed. Please try again."


class InvalidFolderIdError(AppError):
    status_code = 400
    detail = "The supplied folder ID is not a valid Google Drive folder ID."


class RateLimitedError(AppError):
    status_code = 429
    detail = "Too many requests. Please wait a moment before trying again."


class NoResultsError(AppError):
    status_code = 404
    detail = "No summaries are available yet. Run a summarization first."
