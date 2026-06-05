"""LLM document-intelligence service backed by Google Gemini.

Rather than returning a plain paragraph, this service asks Gemini for a
*structured* analysis (summary + category + key topics + important numbers +
table insights + named entities + a confidence score) using the model's native
JSON / response-schema mode. This turns a simple "summarizer" into a lightweight
document-intelligence pipeline.

Uses the modern ``google-genai`` SDK (successor to ``google-generativeai``),
runs documents concurrently with a bounded semaphore, isolates per-document
failures, and retries transient errors with exponential backoff.
"""
from __future__ import annotations

import asyncio
import logging

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.mime import friendly_type
from app.models.schemas import DocumentEntities, DocumentSummary, ParsedDocument
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
    "You are a senior document-intelligence analyst. You read business and "
    "technical documents and produce accurate, structured analyses for "
    "decision-makers. You never invent facts: every number, entity and claim "
    "must come from the document. When tables are present you interpret the "
    "trends they show rather than merely noting that a table exists. You always "
    "respond with a single valid JSON object matching the requested schema."
)

DOCUMENT_CATEGORIES = [
    "Business Report",
    "Financial Statement",
    "Research Paper",
    "Resume/CV",
    "Invoice",
    "Employee Handbook",
    "Legal Contract",
    "Technical Documentation",
    "Meeting Notes",
    "Marketing Material",
    "Email/Letter",
    "Other",
]

USER_PROMPT = """Analyze the following document and return a JSON object.

Guidance for each field:
- summary: A polished executive summary of 5-10 sentences (roughly 100-200 \
words) in plain prose (no bullet points, no preamble). Cover the main topic, \
the key points, concrete insights drawn from any tables/numbers, and the main \
conclusion or recommendation. Never produce a one-line summary.
- document_category: Choose the SINGLE best fit from: {categories}.
- key_topics: 3 to 6 short topic phrases (2-4 words each).
- important_numbers: Up to 8 of the most important numbers/metrics, each a short \
string WITH context, e.g. "$420M revenue", "18% YoY growth", "91% satisfaction". \
Use [] if the document has no meaningful figures.
- table_insights: If tables are present, 1-3 sentences describing the most \
important trend or comparison, citing actual values (e.g. revenue grew from \
$300M in 2023 to $420M in 2025, a 40% increase). Use "" if there are no tables.
- organizations / locations / dates / monetary_values / percentages: \
De-duplicated lists of entities found in the document. Use [] when none.
- confidence: Your confidence in this analysis, from 0.0 to 1.0.

Document Title: {file_name}
Document Type: {file_type}
Pages: {pages} | Word count: {word_count} | Tables detected: {tables_found}

Extracted Tables:
{tables_text}

Document Content:
{text}
"""

_EMPTY_NOTE = "No readable text could be extracted from this document."
_PARSE_NOTE = "The document could not be parsed (corrupt, encrypted or unsupported)."


class LLMAnalysis(BaseModel):
    """Structured analysis returned by Gemini (used as the response schema)."""

    summary: str = ""
    document_category: str = "Other"
    key_topics: list[str] = Field(default_factory=list)
    important_numbers: list[str] = Field(default_factory=list)
    table_insights: str = ""
    organizations: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    monetary_values: list[str] = Field(default_factory=list)
    percentages: list[str] = Field(default_factory=list)
    confidence: float = 0.0


def _is_retryable(exc: BaseException) -> bool:
    """Retry on server (5xx) errors and rate limits (429); not other 4xx."""
    if _SERVER_ERROR and isinstance(exc, _SERVER_ERROR):
        return True
    if _CLIENT_ERROR and isinstance(exc, _CLIENT_ERROR):
        return getattr(exc, "code", None) == 429
    message = str(exc).lower()
    return "429" in message or "rate" in message or "unavailable" in message


class LLMEmptyResponseError(RuntimeError):
    """Raised when Gemini returns no usable content."""


class LLMService:
    """Produce structured document intelligence with Gemini."""

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
    async def analyze(self, doc: ParsedDocument) -> LLMAnalysis:
        """Return a structured :class:`LLMAnalysis` for one parsed document."""
        prompt = USER_PROMPT.format(
            categories=", ".join(DOCUMENT_CATEGORIES),
            file_name=doc.file_name,
            file_type=friendly_type(doc.mime_type),
            pages=doc.page_count if doc.page_count is not None else "n/a",
            word_count=doc.word_count,
            tables_found=doc.table_count,
            tables_text=doc.tables_text or "(none detected)",
            text=doc.text[: self._max_chars],
        )

        @retry(
            retry=retry_if_exception(_is_retryable),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=2, max=20),
            reraise=True,
        )
        async def _call() -> LLMAnalysis:
            response = await asyncio.wait_for(
                self._client.aio.models.generate_content(
                    model=self._model,
                    contents=prompt,
                    config=self._generation_config(),
                ),
                timeout=self._timeout,
            )
            return self._parse_response(response)

        return await _call()

    async def summarize_batch(
        self, documents: list[ParsedDocument]
    ) -> list[DocumentSummary]:
        """Analyze many documents concurrently; failures are isolated."""
        tasks = [self._analyze_one(doc) for doc in documents]
        return await asyncio.gather(*tasks)

    # Kept for backwards compatibility / simple callers.
    async def summarize(self, file_name: str, text: str) -> str:
        doc = ParsedDocument(
            file_id="", file_name=file_name, mime_type="text/plain", text=text
        )
        return (await self.analyze(doc)).summary

    # -- Internals ----------------------------------------------------------
    def _generation_config(self) -> types.GenerateContentConfig:
        kwargs: dict = {
            "system_instruction": SYSTEM_INSTRUCTION,
            "temperature": 0.3,
            "max_output_tokens": 3072,
            "response_mime_type": "application/json",
            "response_schema": LLMAnalysis,
        }
        # Disable "thinking" for gemini-2.5 models: it keeps the whole token
        # budget available for the structured answer and speeds things up.
        try:  # pragma: no cover - depends on SDK version
            kwargs["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        except Exception:  # pragma: no cover
            pass
        return types.GenerateContentConfig(**kwargs)

    @staticmethod
    def _parse_response(response) -> LLMAnalysis:
        # Prefer the SDK's parsed object; fall back to parsing the raw JSON.
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, LLMAnalysis):
            analysis = parsed
        else:
            raw = ""
            try:
                raw = (response.text or "").strip()
            except Exception:  # noqa: BLE001 - blocked/empty candidates
                raw = ""
            if not raw:
                raise LLMEmptyResponseError("Gemini returned an empty response.")
            try:
                analysis = LLMAnalysis.model_validate_json(raw)
            except Exception:
                # Last resort: keep the raw text as the summary so the user
                # still gets something useful instead of a hard failure.
                analysis = LLMAnalysis(summary=raw, confidence=0.4)
        if not (analysis.summary or "").strip():
            raise LLMEmptyResponseError("Gemini returned an empty summary.")
        return analysis

    async def _analyze_one(self, doc: ParsedDocument) -> DocumentSummary:
        async with self._semaphore:
            # Short-circuit documents the parser already flagged.
            if doc.parse_status == "empty" or doc.text == EMPTY_DOCUMENT:
                return self._failed(doc, "empty", doc.note or _EMPTY_NOTE)
            if doc.parse_status == "error" or doc.text == PARSE_ERROR:
                return self._failed(doc, "error", doc.note or _PARSE_NOTE)

            try:
                analysis = await self.analyze(doc)
            except Exception as exc:  # noqa: BLE001 - isolate per-document failures
                logger.exception("Analysis failed for '%s'", doc.file_name)
                return self._failed(doc, "error", f"Summarization failed: {exc}")

            return DocumentSummary(
                file_id=doc.file_id,
                file_name=doc.file_name,
                web_view_link=doc.web_view_link,
                mime_type=doc.mime_type,
                file_type=friendly_type(doc.mime_type),
                status="success",
                pages=doc.page_count,
                word_count=doc.word_count,
                tables_found=doc.table_count,
                summary=analysis.summary.strip(),
                document_category=analysis.document_category or "Other",
                key_topics=_clean_list(analysis.key_topics),
                important_numbers=_clean_list(analysis.important_numbers),
                table_insights=analysis.table_insights.strip(),
                entities=DocumentEntities(
                    organizations=_clean_list(analysis.organizations),
                    locations=_clean_list(analysis.locations),
                    dates=_clean_list(analysis.dates),
                    monetary_values=_clean_list(analysis.monetary_values),
                    percentages=_clean_list(analysis.percentages),
                ),
                confidence=round(_clamp(analysis.confidence), 2),
                document_quality=_quality_label(analysis.confidence, doc.word_count),
            )

    @staticmethod
    def _failed(
        doc: ParsedDocument, status: str, message: str
    ) -> DocumentSummary:
        return DocumentSummary(
            file_id=doc.file_id,
            file_name=doc.file_name,
            web_view_link=doc.web_view_link,
            mime_type=doc.mime_type,
            file_type=friendly_type(doc.mime_type),
            status=status,  # type: ignore[arg-type]
            pages=doc.page_count,
            word_count=doc.word_count,
            tables_found=doc.table_count,
            summary=message,
            error_message=message,
        )


def _clamp(value: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _quality_label(confidence: float, word_count: int) -> str:
    confidence = _clamp(confidence)
    if word_count < 40:
        return "Low"
    if confidence >= 0.8:
        return "High"
    if confidence >= 0.5:
        return "Medium"
    return "Low"


def _clean_list(values: list[str], limit: int = 12) -> list[str]:
    """Trim, drop blanks, and de-duplicate (case-insensitively) a string list."""
    seen: set[str] = set()
    out: list[str] = []
    for value in values or []:
        item = " ".join(str(value).split())
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            out.append(item)
        if len(out) >= limit:
            break
    return out
