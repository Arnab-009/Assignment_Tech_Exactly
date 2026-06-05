"""Tests for app.services.export_service."""
from __future__ import annotations

import csv
import io

import pytest

from app.models.schemas import DocumentSummary
from app.services.export_service import ExportService, friendly_type


@pytest.fixture()
def exporter() -> ExportService:
    return ExportService()


@pytest.fixture()
def sample_summaries() -> list[DocumentSummary]:
    return [
        DocumentSummary(
            file_id="id1",
            file_name="Annual Report.pdf",
            web_view_link="https://drive.google.com/file/d/id1/view",
            mime_type="application/pdf",
            summary="This report covers the annual financial performance of the company.",
            status="success",
        ),
        DocumentSummary(
            file_id="id2",
            file_name="Notes.txt",
            web_view_link="https://drive.google.com/file/d/id2/view",
            mime_type="text/plain",
            summary="Meeting notes from the Q3 strategy session.",
            status="success",
        ),
        DocumentSummary(
            file_id="id3",
            file_name="Empty File.docx",
            web_view_link="",
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            summary="No readable text could be extracted from this document.",
            status="empty",
        ),
    ]


# ── friendly_type helper ─────────────────────────────────────────────────────
class TestFriendlyType:
    def test_pdf_label(self):
        assert friendly_type("application/pdf") == "PDF"

    def test_docx_label(self):
        assert "DOCX" in friendly_type(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    def test_txt_label(self):
        assert friendly_type("text/plain") == "TXT"

    def test_unknown_passthrough(self):
        assert friendly_type("application/octet-stream") == "application/octet-stream"

    def test_empty_string(self):
        assert friendly_type("") == "Unknown"


# ── CSV export ───────────────────────────────────────────────────────────────
class TestBuildCsv:
    def test_returns_bytes(self, exporter: ExportService, sample_summaries):
        result = exporter.build_csv(sample_summaries)
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_csv_has_header_row(self, exporter: ExportService, sample_summaries):
        raw = exporter.build_csv(sample_summaries)
        # utf-8-sig BOM is 3 bytes; skip it for reliable parsing
        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        header = next(reader)
        assert "File Name" in header
        assert "Summary" in header
        assert "Drive Link" in header

    def test_csv_has_correct_row_count(self, exporter: ExportService, sample_summaries):
        raw = exporter.build_csv(sample_summaries)
        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        # 1 header + 3 data rows
        assert len(rows) == 4

    def test_csv_file_names_match(self, exporter: ExportService, sample_summaries):
        raw = exporter.build_csv(sample_summaries)
        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        next(reader)  # skip header
        names = [row[0] for row in reader]
        assert "Annual Report.pdf" in names
        assert "Notes.txt" in names

    def test_empty_summaries_produces_header_only(self, exporter: ExportService):
        raw = exporter.build_csv([])
        text = raw.decode("utf-8-sig")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        assert len(rows) == 1  # header only


# ── PDF export ───────────────────────────────────────────────────────────────
class TestBuildPdf:
    def test_returns_bytes(self, exporter: ExportService, sample_summaries):
        result = exporter.build_pdf(sample_summaries, "test-folder-id")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_pdf_starts_with_magic_bytes(self, exporter: ExportService, sample_summaries):
        result = exporter.build_pdf(sample_summaries, "test-folder-id")
        # All valid PDFs start with %PDF-
        assert result[:5] == b"%PDF-"

    def test_empty_summaries_still_produces_pdf(self, exporter: ExportService):
        result = exporter.build_pdf([], "empty-folder")
        assert result[:5] == b"%PDF-"
