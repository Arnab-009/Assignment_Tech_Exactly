"""Report export service: CSV and PDF generation from document summaries."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

from app.mime import friendly_type
from app.models.schemas import DocumentSummary


def _join(values: list[str]) -> str:
    return "; ".join(values) if values else ""


class ExportService:
    """Build downloadable CSV and PDF reports from a list of summaries."""

    # -- CSV ----------------------------------------------------------------
    def build_csv(self, summaries: list[DocumentSummary]) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer, quoting=csv.QUOTE_ALL)
        writer.writerow(
            [
                "File Name",
                "File Type",
                "Document Category",
                "Pages",
                "Word Count",
                "Tables Found",
                "Confidence",
                "Quality",
                "Key Topics",
                "Important Numbers",
                "Organizations",
                "Status",
                "Summary",
                "Drive Link",
            ]
        )
        for item in summaries:
            writer.writerow(
                [
                    item.file_name,
                    item.file_type or friendly_type(item.mime_type),
                    item.document_category,
                    item.pages if item.pages is not None else "",
                    item.word_count,
                    item.tables_found,
                    f"{item.confidence:.0%}" if item.confidence else "",
                    item.document_quality,
                    _join(item.key_topics),
                    _join(item.important_numbers),
                    _join(item.entities.organizations),
                    item.status,
                    item.summary,
                    item.web_view_link,
                ]
            )
        # utf-8-sig adds a BOM so Excel opens unicode summaries correctly.
        return buffer.getvalue().encode("utf-8-sig")

    # -- PDF ----------------------------------------------------------------
    def build_pdf(self, summaries: list[DocumentSummary], folder_id: str) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            title="Document Intelligence Report",
            author="Document Summarizer",
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
        )

        s = _styles()
        generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        total = len(summaries)
        success = sum(1 for item in summaries if item.status == "success")

        story: list = [
            Paragraph("Document Intelligence Report", s["title"]),
            Spacer(1, 6),
            Paragraph(f"Folder ID: {escape(folder_id or 'N/A')}", s["subtitle"]),
            Paragraph(f"Generated: {generated}", s["subtitle"]),
            Paragraph(
                f"{success} of {total} document(s) analyzed successfully",
                s["subtitle"],
            ),
            Spacer(1, 10),
            HRFlowable(width="100%", color=colors.HexColor("#e2e8f0")),
        ]

        for index, item in enumerate(summaries, start=1):
            story.extend(self._document_section(index, item, s))

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return buffer.getvalue()

    def _document_section(self, index: int, item: DocumentSummary, s: dict) -> list:
        flow: list = [
            Paragraph(f"{index}. {escape(item.file_name)}", s["heading"])
        ]

        meta_bits = [
            f"Type: {escape(item.file_type or friendly_type(item.mime_type))}",
            f"Status: {item.status.upper()}",
        ]
        if item.document_category:
            meta_bits.append(f"Category: {escape(item.document_category)}")
        if item.pages is not None:
            meta_bits.append(f"Pages: {item.pages}")
        if item.word_count:
            meta_bits.append(f"Words: {item.word_count:,}")
        meta_bits.append(f"Tables: {item.tables_found}")
        if item.confidence:
            meta_bits.append(f"Confidence: {item.confidence:.0%}")
        flow.append(Paragraph(" &nbsp;|&nbsp; ".join(meta_bits), s["meta"]))

        if item.key_topics:
            flow.append(
                Paragraph(
                    f"<b>Key Topics:</b> {escape(', '.join(item.key_topics))}",
                    s["chip"],
                )
            )
        if item.important_numbers:
            flow.append(
                Paragraph(
                    "<b>Important Numbers:</b> "
                    + escape(" · ".join(item.important_numbers)),
                    s["chip"],
                )
            )
        if item.table_insights:
            flow.append(
                Paragraph(
                    f"<b>Table Insights:</b> {escape(item.table_insights)}",
                    s["chip"],
                )
            )

        entity_line = self._entity_line(item)
        if entity_line:
            flow.append(Paragraph(entity_line, s["chip"]))

        body = item.summary or item.error_message or "No summary available."
        flow.append(Paragraph(escape(body).replace("\n", "<br/>"), s["body"]))

        if item.web_view_link:
            flow.append(
                Paragraph(
                    f'<link href="{escape(item.web_view_link)}">'
                    "Open in Google Drive</link>",
                    s["link"],
                )
            )
        flow.append(Spacer(1, 4))
        flow.append(HRFlowable(width="100%", color=colors.HexColor("#f1f5f9")))
        return flow

    @staticmethod
    def _entity_line(item: DocumentSummary) -> str:
        parts: list[str] = []
        ent = item.entities
        if ent.organizations:
            parts.append(f"Orgs: {escape(', '.join(ent.organizations))}")
        if ent.monetary_values:
            parts.append(f"Money: {escape(', '.join(ent.monetary_values))}")
        if ent.percentages:
            parts.append(f"Percent: {escape(', '.join(ent.percentages))}")
        if ent.dates:
            parts.append(f"Dates: {escape(', '.join(ent.dates))}")
        if ent.locations:
            parts.append(f"Locations: {escape(', '.join(ent.locations))}")
        if not parts:
            return ""
        return "<b>Entities:</b> " + " &nbsp;|&nbsp; ".join(parts)


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontSize=22,
            textColor=colors.HexColor("#1d4ed8"),
            alignment=TA_CENTER,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#475569"),
            alignment=TA_CENTER,
        ),
        "heading": ParagraphStyle(
            "FileHeading",
            parent=base["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=14,
            spaceAfter=2,
        ),
        "meta": ParagraphStyle(
            "FileMeta",
            parent=base["Normal"],
            fontSize=8.5,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=5,
        ),
        "chip": ParagraphStyle(
            "Chip",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#334155"),
            leading=13,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontSize=10.5,
            leading=15,
            spaceBefore=4,
            spaceAfter=4,
        ),
        "link": ParagraphStyle(
            "DriveLink",
            parent=base["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#1d4ed8"),
            spaceAfter=4,
        ),
    }


def _footer(canvas, doc) -> None:
    """Draw a page-number footer on every page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawCentredString(
        A4[0] / 2.0, 1.1 * cm, f"Document Intelligence Report  ·  Page {doc.page}"
    )
    canvas.restoreState()
