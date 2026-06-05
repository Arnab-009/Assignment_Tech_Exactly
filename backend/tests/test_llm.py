"""Tests for app.services.llm_service."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.schemas import DocumentSummary, ParsedDocument
from app.services.llm_service import LLMService
from app.services.parser_service import EMPTY_DOCUMENT, PARSE_ERROR


@pytest.fixture()
def llm_service() -> LLMService:
    """LLMService wired to a fake API key (Gemini calls will be mocked)."""
    return LLMService(
        api_key="fake-key",
        model="gemini-2.5-flash",
        concurrency=3,
        max_chars=10_000,
        timeout_seconds=30,
    )


def _make_doc(
    *,
    text: str = "Some document content about finance.",
    parse_status: str = "ok",
    file_name: str = "report.pdf",
) -> ParsedDocument:
    return ParsedDocument(
        file_id="abc123",
        file_name=file_name,
        web_view_link="https://drive.google.com/file/d/abc123/view",
        mime_type="application/pdf",
        text=text,
        parse_status=parse_status,
    )


def _mock_gemini_response(text: str) -> MagicMock:
    resp = MagicMock()
    resp.text = text
    return resp


# ── Single document summarization ────────────────────────────────────────────
class TestSummarize:
    @pytest.mark.asyncio
    async def test_returns_summary_text(self, llm_service: LLMService):
        expected = "This document discusses quarterly financial results."
        mock_response = _mock_gemini_response(expected)

        llm_service._client = MagicMock()
        llm_service._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        result = await llm_service.summarize("report.pdf", "Some financial data")
        assert result == expected

    @pytest.mark.asyncio
    async def test_raises_on_empty_response(self, llm_service: LLMService):
        mock_response = _mock_gemini_response("")

        llm_service._client = MagicMock()
        llm_service._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        with pytest.raises(Exception):
            await llm_service.summarize("report.pdf", "Some text")


# ── Batch summarization ─────────────────────────────────────────────────────
class TestSummarizeBatch:
    @pytest.mark.asyncio
    async def test_batch_returns_correct_count(self, llm_service: LLMService):
        mock_response = _mock_gemini_response("Summary of the document.")

        llm_service._client = MagicMock()
        llm_service._client.aio.models.generate_content = AsyncMock(return_value=mock_response)

        docs = [_make_doc(file_name=f"file_{i}.pdf") for i in range(3)]
        results = await llm_service.summarize_batch(docs)

        assert len(results) == 3
        assert all(isinstance(r, DocumentSummary) for r in results)
        assert all(r.status == "success" for r in results)

    @pytest.mark.asyncio
    async def test_empty_document_skips_llm(self, llm_service: LLMService):
        doc = _make_doc(text=EMPTY_DOCUMENT, parse_status="empty")

        llm_service._client = MagicMock()
        llm_service._client.aio.models.generate_content = AsyncMock()

        results = await llm_service.summarize_batch([doc])
        assert results[0].status == "empty"
        # LLM should NOT have been called
        llm_service._client.aio.models.generate_content.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_parse_error_document_skips_llm(self, llm_service: LLMService):
        doc = _make_doc(text=PARSE_ERROR, parse_status="error")

        llm_service._client = MagicMock()
        llm_service._client.aio.models.generate_content = AsyncMock()

        results = await llm_service.summarize_batch([doc])
        assert results[0].status == "error"
        llm_service._client.aio.models.generate_content.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_one_failure_does_not_abort_batch(self, llm_service: LLMService):
        """If one document's LLM call fails, other docs still succeed."""
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise RuntimeError("Simulated API error")
            return _mock_gemini_response("Good summary.")

        llm_service._client = MagicMock()
        llm_service._client.aio.models.generate_content = AsyncMock(side_effect=side_effect)

        docs = [_make_doc(file_name=f"f{i}.pdf") for i in range(3)]
        results = await llm_service.summarize_batch(docs)

        statuses = [r.status for r in results]
        assert statuses.count("success") == 2
        assert statuses.count("error") == 1
