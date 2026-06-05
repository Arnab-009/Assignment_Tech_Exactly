"""Shared MIME-type helpers."""
from __future__ import annotations

PDF_MIME = "application/pdf"
DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
TXT_MIME = "text/plain"
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"

_FRIENDLY_TYPES = {
    PDF_MIME: "PDF",
    DOCX_MIME: "DOCX",
    TXT_MIME: "TXT",
    GOOGLE_DOC_MIME: "Google Doc",
}


def friendly_type(mime_type: str) -> str:
    """Return a short, human-readable label for a MIME type."""
    return _FRIENDLY_TYPES.get(mime_type, (mime_type or "Unknown"))
