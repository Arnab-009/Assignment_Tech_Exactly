"""Pydantic schemas shared across routers and services."""
from __future__ import annotations

import re
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

# A Google Drive file/folder ID is a URL-safe base64-ish token. We validate
# loosely: a reasonable length and character set, which catches obvious junk
# (e.g. a full URL pasted in) without rejecting legitimate IDs.
_DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,200}$")

ParseStatus = Literal["ok", "empty", "error"]
SummaryStatus = Literal["success", "empty", "error"]


class DriveFolder(BaseModel):
    """A folder listed from Google Drive."""

    id: str
    name: str


class DriveFile(BaseModel):
    """A file listed from a Google Drive folder."""

    id: str
    name: str
    mime_type: str
    web_view_link: str = ""
    size: Optional[int] = None


class ParsedDocument(BaseModel):
    """A downloaded + text-extracted document, ready for summarization."""

    file_id: str
    file_name: str
    web_view_link: str = ""
    mime_type: str
    text: str = ""
    parse_status: ParseStatus = "ok"
    note: Optional[str] = None


class DocumentSummary(BaseModel):
    """The final, user-facing summary for a single document."""

    file_id: str
    file_name: str
    web_view_link: str = ""
    mime_type: str
    summary: str
    status: SummaryStatus
    error_message: Optional[str] = None


class SummarizeRequest(BaseModel):
    """Body for ``POST /api/summarize``."""

    folder_id: str = Field(..., description="Google Drive folder ID to process.")
    file_id: Optional[str] = Field(None, description="If provided, only this single file is summarized.")

    @field_validator("folder_id")
    @classmethod
    def _validate_folder_id(cls, value: str) -> str:
        value = value.strip()
        # Allow users to paste a full Drive folder URL and extract the ID.
        match = re.search(r"/folders/([A-Za-z0-9_-]{10,})", value)
        if match:
            value = match.group(1)
        if not _DRIVE_ID_RE.match(value):
            raise ValueError("Invalid Google Drive folder ID.")
        return value

    @field_validator("file_id")
    @classmethod
    def _validate_file_id(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        value = value.strip()
        if not _DRIVE_ID_RE.match(value):
            raise ValueError("Invalid Google Drive file ID.")
        return value


class SummarizeStats(BaseModel):
    total: int = 0
    success: int = 0
    empty: int = 0
    error: int = 0
    elapsed_seconds: float = 0.0


class SummarizeResponse(BaseModel):
    folder_id: str
    generated_at: str
    stats: SummarizeStats
    summaries: list[DocumentSummary]


class AuthStatus(BaseModel):
    authenticated: bool
    email: Optional[str] = None
    default_folder_id: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "document-summarizer"
    version: str
