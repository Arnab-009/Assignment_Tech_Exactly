"""Document parsing service.

Extracts plain text from PDF, DOCX and TXT byte streams. The service never
raises on bad input: a corrupt file yields :data:`PARSE_ERROR` and an empty
document yields :data:`EMPTY_DOCUMENT`, so one bad file can never abort a whole
batch.
"""
from __future__ import annotations

import io
import logging

import fitz  # PyMuPDF
from docx import Document

logger = logging.getLogger(__name__)

# Sentinel values returned in place of extracted text.
EMPTY_DOCUMENT = "[EMPTY_DOCUMENT]"
PARSE_ERROR = "[PARSE_ERROR]"

PDF_MIME = "application/pdf"
DOCX_MIME = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
TXT_MIME = "text/plain"


class ParserService:
    """Extract clean text from supported document byte streams."""

    def __init__(self, max_chars: int = 50_000) -> None:
        self._max_chars = max_chars

    def extract_text(self, file_bytes: bytes, mime_type: str) -> str:
        """Return extracted text, or a sentinel flag on empty/failed parsing.

        The returned text is stripped and truncated to ``max_chars`` so it
        comfortably fits within the LLM context window.
        """
        if not file_bytes:
            return EMPTY_DOCUMENT

        try:
            normalized = (mime_type or "").split(";")[0].strip().lower()
            if normalized == PDF_MIME:
                text = self._parse_pdf(file_bytes)
            elif normalized == DOCX_MIME:
                text = self._parse_docx(file_bytes)
            elif normalized == TXT_MIME or normalized.startswith("text/"):
                text = self._parse_txt(file_bytes)
            else:
                logger.warning("Unsupported mime type for parsing: %s", mime_type)
                return PARSE_ERROR
        except Exception:  # noqa: BLE001 - parser must never crash the batch
            logger.exception("Failed to parse document (mime=%s)", mime_type)
            return PARSE_ERROR

        text = (text or "").strip()
        if not text:
            return EMPTY_DOCUMENT
        return text[: self._max_chars]

    # -- Per-format parsers -------------------------------------------------
    def _parse_pdf(self, file_bytes: bytes) -> str:
        parts: list[str] = []
        with fitz.open(stream=file_bytes, filetype="pdf") as doc:
            for page in doc:
                parts.append(page.get_text("text"))
        return "\n".join(parts)

    def _parse_docx(self, file_bytes: bytes) -> str:
        document = Document(io.BytesIO(file_bytes))
        parts: list[str] = [
            para.text for para in document.paragraphs if para.text.strip()
        ]
        # Tables hold meaningful content that paragraph iteration misses.
        for table in document.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    parts.append(" | ".join(cells))
        return "\n".join(parts)

    def _parse_txt(self, file_bytes: bytes) -> str:
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin-1", errors="replace")
