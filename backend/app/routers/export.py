"""Report export routes: CSV and PDF download."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.cache import ResultStore
from app.dependencies import (
    get_export_service,
    get_result_store,
    get_session_id,
)
from app.exceptions import NoResultsError
from app.services.export_service import ExportService

router = APIRouter(prefix="/api/export", tags=["export"])


def _require_result(store: ResultStore, session_id: str):
    result = store.get(session_id)
    if result is None:
        raise NoResultsError()
    return result


@router.get("/csv")
def export_csv(
    store: ResultStore = Depends(get_result_store),
    session_id: str = Depends(get_session_id),
    exporter: ExportService = Depends(get_export_service),
) -> StreamingResponse:
    result = _require_result(store, session_id)
    data = exporter.build_csv(result.summaries)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="document_summaries.csv"'
        },
    )


@router.get("/pdf")
def export_pdf(
    store: ResultStore = Depends(get_result_store),
    session_id: str = Depends(get_session_id),
    exporter: ExportService = Depends(get_export_service),
) -> StreamingResponse:
    result = _require_result(store, session_id)
    data = exporter.build_pdf(result.summaries, result.folder_id)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="document_summaries.pdf"'
        },
    )
