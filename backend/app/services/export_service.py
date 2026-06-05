"""Report export service: CSV and PDF generation from summaries."""
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
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.models.schemas import DocumentSummary

# Friendly, human-readable labels for the MIME types we handle.
_TYPE_LABELS = {
    "application/pdf": "PDF",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
    "text/plain": "TXT",
    "application/vnd.google-apps.document": "Google Doc",
}


def friendly_type(mime_type: str) -> str:
    return _TYPE_LABELS.get(mime_type, mime_type or "Unknown")


class ExportService:
    """Build downloadable CSV and PDF reports from a list of summaries."""

    # -- CSV ----------------------------------------------------------------
    def build_csv(self, summaries: list[DocumentSummary]) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer, quoting=csv.QUOTE_ALL)
        writer.writerow(
            ["File Name", "File Type", "Status", "Summary", "Drive Link"]
        )
        for item in summaries:
            writer.writerow(
                [
                    item.file_name,
                    friendly_type(item.mime_type),
                    item.status,
                    item.summary,
                    item.web_view_link,
                ]
            )
        # utf-8-sig adds a BOM so Excel opens unicode summaries correctly.
        return buffer.getvalue().encode("utf-8-sig")

    # -- PDF ----------------------------------------------------------------
    def build_pdf(
        self, summaries: list[DocumentSummary], folder_id: str
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            title="Document Summarizer Report",
            author="Document Summarizer",
            topMargin=2 * cm,
            bottomMargin=2 * cm,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=22,
            textColor=colors.HexColor("#1d4ed8"),
            alignment=TA_CENTER,
        )
        subtitle_style = ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#475569"),
            alignment=TA_CENTER,
        )
        heading_style = ParagraphStyle(
            "FileHeading",
            parent=styles["Heading2"],
            fontSize=13,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=14,
            spaceAfter=2,
        )
        meta_style = ParagraphStyle(
            "FileMeta",
            parent=styles["Normal"],
            fontSize=8.5,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "Body",
            parent=styles["Normal"],
            fontSize=10.5,
            leading=15,
            spaceAfter=4,
        )
        link_style = ParagraphStyle(
            "DriveLink",
            parent=styles["Normal"],
            fontSize=9,
            textColor=colors.HexColor("#1d4ed8"),
            spaceAfter=4,
        )

        generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        total = len(summaries)
        success = sum(1 for s in summaries if s.status == "success")

        story: list = [
            Paragraph("Document Summarizer Report", title_style),
            Spacer(1, 6),
            Paragraph(
                f"Folder ID: {escape(folder_id or 'N/A')}", subtitle_style
            ),
            Paragraph(f"Generated: {generated}", subtitle_style),
            Paragraph(
                f"{success} of {total} document(s) summarized successfully",
                subtitle_style,
            ),
            Spacer(1, 10),
            HRFlowable(width="100%", color=colors.HexColor("#e2e8f0")),
        ]

        for index, item in enumerate(summaries, start=1):
            story.append(
                Paragraph(f"{index}. {escape(item.file_name)}", heading_style)
            )
            story.append(
                Paragraph(
                    f"Type: {friendly_type(item.mime_type)} &nbsp;|&nbsp; "
                    f"Status: {item.status.upper()}",
                    meta_style,
                )
            )
            body = item.summary or item.error_message or "No summary available."
            story.append(
                Paragraph(escape(body).replace("\n", "<br/>"), body_style)
            )
            if item.web_view_link:
                story.append(
                    Paragraph(
                        f'<link href="{escape(item.web_view_link)}">'
                        f"Open in Google Drive</link>",
                        link_style,
                    )
                )
            story.append(Spacer(1, 4))
            story.append(HRFlowable(width="100%", color=colors.HexColor("#f1f5f9")))

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return buffer.getvalue()


def _footer(canvas, doc) -> None:
    """Draw a page-number footer on every page."""
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawCentredString(
        A4[0] / 2.0, 1.1 * cm, f"Document Summarizer  ·  Page {doc.page}"
    )
    canvas.restoreState()
