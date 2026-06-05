"""Summarization pipeline routes.

``POST /api/summarize`` drives the full pipeline (list -> download -> parse ->
summarize) and caches the result per session. ``GET /api/results`` re-reads the
cached result so a page refresh doesn't re-run an expensive job.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from google.oauth2.credentials import Credentials

from app.cache import ResultStore
from app.config import get_settings
from app.dependencies import (
    get_current_credentials,
    get_drive_service,
    get_llm_service,
    get_parser_service,
    get_result_store,
    get_session_id,
)
from app.exceptions import FolderNotFoundError, NoResultsError, RateLimitedError
from app.models.schemas import (
    DocumentSummary,
    DriveFile,
    ParsedDocument,
    SummarizeRequest,
    SummarizeResponse,
    SummarizeStats,
)
from app.services.drive_service import DriveService
from app.services.llm_service import LLMService
from app.services.parser_service import EMPTY_DOCUMENT, PARSE_ERROR, ParserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["summarize"])


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize(
    payload: SummarizeRequest,
    credentials: Credentials = Depends(get_current_credentials),
    drive: DriveService = Depends(get_drive_service),
    parser: ParserService = Depends(get_parser_service),
    llm: LLMService = Depends(get_llm_service),
    store: ResultStore = Depends(get_result_store),
    session_id: str = Depends(get_session_id),
) -> SummarizeResponse:
    settings = get_settings()

    # Per-session rate limit to protect the Drive and Gemini quotas.
    elapsed = store.seconds_since_last_run(session_id)
    if elapsed is not None and elapsed < settings.summarize_cooldown_seconds:
        wait = int(settings.summarize_cooldown_seconds - elapsed) + 1
        raise RateLimitedError(
            f"Please wait {wait}s before starting another summarization."
        )
    store.mark_run(session_id)

    started = time.perf_counter()
    logger.info("Listing files in folder %s", payload.folder_id)
    files = await drive.list_files(payload.folder_id, credentials)

    # If a specific file was requested, narrow down to just that one.
    if payload.file_id:
        files = [f for f in files if f.id == payload.file_id]

    if not files:
        raise FolderNotFoundError(
            "No supported documents (.pdf, .docx, .txt) were found in this folder."
        )

    logger.info("Downloading + parsing %d file(s)", len(files))
    parsed = await _download_and_parse(files, credentials, drive, parser)

    logger.info("Summarizing %d document(s)", len(parsed))
    summaries = await llm.summarize_batch(parsed)

    elapsed_seconds = round(time.perf_counter() - started, 2)
    response = SummarizeResponse(
        folder_id=payload.folder_id,
        generated_at=datetime.now(timezone.utc).isoformat(),
        stats=_build_stats(summaries, elapsed_seconds),
        summaries=summaries,
    )
    store.save(session_id, response)
    logger.info(
        "Done: %d ok / %d empty / %d error in %ss",
        response.stats.success,
        response.stats.empty,
        response.stats.error,
        elapsed_seconds,
    )
    return response


@router.get("/results", response_model=SummarizeResponse)
def results(
    store: ResultStore = Depends(get_result_store),
    session_id: str = Depends(get_session_id),
) -> SummarizeResponse:
    cached = store.get(session_id)
    if cached is None:
        raise NoResultsError()
    return cached


# -- Pipeline helpers -------------------------------------------------------
async def _download_and_parse(
    files: list[DriveFile],
    credentials: Credentials,
    drive: DriveService,
    parser: ParserService,
) -> list[ParsedDocument]:
    """Download + extract text for every file concurrently; isolate failures."""

    async def process(file: DriveFile) -> ParsedDocument:
        try:
            data, parse_mime = await drive.download_for_parsing(file, credentials)
        except Exception as exc:  # noqa: BLE001 - one bad file must not abort
            logger.warning("Download failed for '%s': %s", file.name, exc)
            return _parsed(file, PARSE_ERROR, "error", str(exc))

        # PDF/DOCX parsing is CPU-bound; keep it off the event loop.
        text = await run_in_threadpool(parser.extract_text, data, parse_mime)
        status = "ok"
        if text == EMPTY_DOCUMENT:
            status = "empty"
        elif text == PARSE_ERROR:
            status = "error"
        return _parsed(file, text, status)

    return await asyncio.gather(*(process(f) for f in files))


def _parsed(
    file: DriveFile, text: str, status: str, note: str | None = None
) -> ParsedDocument:
    return ParsedDocument(
        file_id=file.id,
        file_name=file.name,
        web_view_link=file.web_view_link,
        mime_type=file.mime_type,
        text=text,
        parse_status=status,  # type: ignore[arg-type]
        note=note,
    )


def _build_stats(
    summaries: list[DocumentSummary], elapsed_seconds: float
) -> SummarizeStats:
    stats = SummarizeStats(total=len(summaries), elapsed_seconds=elapsed_seconds)
    for item in summaries:
        if item.status == "success":
            stats.success += 1
        elif item.status == "empty":
            stats.empty += 1
        else:
            stats.error += 1
    return stats
