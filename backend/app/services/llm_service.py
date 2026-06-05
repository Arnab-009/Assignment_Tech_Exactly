"""LLM summarization service backed by Google Gemini.

Uses the modern ``google-genai`` SDK (the successor to ``google-generativeai``)
which exposes a first-class async client via ``client.aio``. Summarization runs
concurrently with a bounded semaphore, individual failures are isolated, and
transient errors are retried with exponential backoff.
"""
from __future__ import annotations

import asyncio
import logging

from google import genai
from google.genai import types
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.models.schemas import DocumentSummary, ParsedDocument
from app.services.parser_service import EMPTY_DOCUMENT, PARSE_ERROR

logger = logging.getLogger(__name__)

# The google-genai error hierarchy may differ slightly across versions, so we
# import defensively and fall back to string inspection for retry decisions.
try:  # pragma: no cover - import shape varies by SDK version
    from google.genai import errors as genai_errors

    _SERVER_ERROR: tuple = (genai_errors.ServerError,)
    _CLIENT_ERROR: tuple = (genai_errors.ClientError,)
except Exception:  # pragma: no cover
    _SERVER_ERROR = ()
    _CLIENT_ERROR = ()

SYSTEM_INSTRUCTION = (
    "You are a professional document analyst. Your job is to produce accurate, "
    "concise summaries of documents for business users."
)

USER_PROMPT = (
    "Summarize the following document in 5 to 10 clear sentences.\n"
    "Cover: the main topic, key points, and any conclusions or "
    "recommendations.\n"
    "Do not add any preamble — output only the summary paragraph.\n\n"
    "Document Title: {file_name}\n"
    "Document Content:\n{text}"
)

_EMPTY_NOTE = "No readable text could be extracted from this document."
_PARSE_NOTE = "The document could not be parsed (corrupt or unsupported)."


def _is_retryable(exc: BaseException) -> bool:
    """Retry on server (5xx) errors and rate limits (429); not other 4xx."""
    if _SERVER_ERROR and isinstance(exc, _SERVER_ERROR):
        return True
    if _CLIENT_ERROR and isinstance(exc, _CLIENT_ERROR):
        return getattr(exc, "code", None) == 429
    message = str(exc).lower()
    return "429" in message or "rate" in message or "unavailable" in message


class LLMEmptyResponseError(RuntimeError):
    """Raised when Gemini returns no usable text."""


class LLMService:
    """Summarize documents with Gemini, with bounded concurrency + retries."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        concurrency: int = 5,
        max_chars: int = 50_000,
        timeout_seconds: int = 120,
    ) -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._semaphore = asyncio.Semaphore(concurrency)
        self._max_chars = max_chars
        self._timeout = timeout_seconds

    # -- Public API ---------------------------------------------------------
    async def summarize(self, file_name: str, text: str) -> str:
        """Summarize a single document's text and return the summary string."""
        prompt = USER_PROMPT.format(
            file_name=file_name, text=text[: self._max_chars]
        )

        @retry(
            retry=retry_if_exception(_is_retryable),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=20),
            reraise=True,
        )
        async def _call() -> str:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=self._generation_config(),
                ),
                timeout=self._timeout,
            )
            try:
                output = (response.text or "").strip()
            except Exception:  # noqa: BLE001 - blocked/empty candidates
                output = ""
            if not output:
                raise LLMEmptyResponseError("Gemini returned an empty response.")
            return output

        return await _call()

    async def summarize_batch(
        self, documents: list[ParsedDocument]
    ) -> list[DocumentSummary]:
        """Summarize many documents concurrently; failures are isolated."""
        tasks = [self._summarize_one(doc) for doc in documents]
        return await asyncio.gather(*tasks)

    # -- Internals ----------------------------------------------------------
    def _generation_config(self) -> types.GenerateContentConfig:
        kwargs: dict = {
            "system_instruction": SYSTEM_INSTRUCTION,
            "temperature": 0.3,
            "max_output_tokens": 2048,
        }
        # Disable "thinking" for gemini-2.5 models: summarization needs none,
        # and it keeps the whole token budget available for the answer.
        try:  # pragma: no cover - depends on SDK version
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        except Exception:  # pragma: no cover
            pass
        return types.GenerateContentConfig(**kwargs)

    async def _summarize_one(self, doc: ParsedDocument) -> DocumentSummary:
        async with self._semaphore:
            # Short-circuit documents the parser already flagged.
            if doc.parse_status == "empty" or doc.text == EMPTY_DOCUMENT:
                return self._summary(doc, _EMPTY_NOTE, "empty", _EMPTY_NOTE)
            if doc.parse_status == "error" or doc.text == PARSE_ERROR:
                return self._summary(doc, _PARSE_NOTE, "error", _PARSE_NOTE)

            try:
                summary = await self.summarize(doc.file_name, doc.text)
                return self._summary(doc, summary, "success")
            except Exception as exc:  # noqa: BLE001 - isolate per-document failures
                logger.exception("Summarization failed for '%s'", doc.file_name)
                message = f"Summarization failed: {exc}"
                return self._summary(doc, message, "error", str(exc))

    @staticmethod
    def _summary(
        doc: ParsedDocument,
        summary: str,
        status: str,
        error_message: str | None = None,
    ) -> DocumentSummary:
        return DocumentSummary(
            file_id=doc.file_id,
            file_name=doc.file_name,
            web_view_link=doc.web_view_link,
            mime_type=doc.mime_type,
            summary=summary,
            status=status,  # type: ignore[arg-type]
            error_message=error_message,
        )
