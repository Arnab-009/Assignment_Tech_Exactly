"""Report export service: CSV and PDF generation from document summaries."""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.mime import friendly_type
from app.models.schemas import DocumentSummary

# ---------------------------------------------------------------------------
# Register DejaVu Sans (ships with fonts-dejavu-core on Debian/Ubuntu).
# DejaVu covers Latin, Cyrillic, Greek, currency symbols (₹ £ € etc.) and
# many more Unicode blocks that Helvetica/Times cannot render.
# ---------------------------------------------------------------------------
_DEJAVU_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
_DEJAVU_BOLD    = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

try:
    pdfmetrics.registerFont(TTFont("DejaVuSans", _DEJAVU_REGULAR))
    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", _DEJAVU_BOLD))
    pdfmetrics.registerFontFamily(
        "DejaVuSans",
        normal="DejaVuSans",
        bold="DejaVuSans-Bold",
    )
    _BODY_FONT      = "DejaVuSans"
    _BODY_FONT_BOLD = "DejaVuSans-Bold"
except Exception:
    # Fallback to built-in fonts if DejaVu is not installed
    _BODY_FONT      = "Helvetica"
    _BODY_FONT_BOLD = "Helvetica-Bold"

# Emoji / surrogate range regex – strip characters outside the BMP that
# ReportLab cannot render even with DejaVu.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001F9FF"  # Misc symbols, emoticons
    "\U00002702-\U000027B0"  # Dingbats
    "\U0001FA00-\U0001FA6F"  # Chess/other
    "\U0001FA70-\U0001FAFF"
    "]+",
    flags=re.UNICODE,
)


def _clean(text: str) -> str:
    """Strip emoji and escape XML special characters for ReportLab markup."""
    return escape(_EMOJI_RE.sub("", text))


def _join(values: list[str]) -> str:
    return "; ".join(values) if values else ""


class ExportService:
    """Build downloadable CSV and PDF reports from a list of summaries."""

    # -- CSV ----------------------------------------------------------------
    def build_csv(self, summaries: list[DocumentSummary]) -> bytes:
        buffer = io.StringIO()
        writer = csv.writer(buffer, quoting=csv.QUOTE_ALL)
        
        # Metadata header rows
        generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        total = len(summaries)
        success = sum(1 for item in summaries if item.status == "success")
        empty = sum(1 for item in summaries if item.status == "empty")
        error = sum(1 for item in summaries if item.status == "error")
        
        writer.writerow(["DOCUMENT INTELLIGENCE EXPORT"])
        writer.writerow([])
        writer.writerow(["Generated", generated])
        writer.writerow(["Total Documents", total])
        writer.writerow(["Successfully Analyzed", success])
        writer.writerow(["Empty Documents", empty])
        writer.writerow(["Errors", error])
        writer.writerow([])
        writer.writerow([])
        
        # Column headers
        writer.writerow([
            "File Name",
            "File Type",
            "Document Category",
            "Status",
            "Pages",
            "Word Count",
            "Tables Found",
            "Confidence",
            "Document Quality",
            "Key Topics",
            "Important Numbers",
            "Table Insights",
            "Organizations",
            "Monetary Values",
            "Percentages",
            "Dates",
            "Locations",
            "Executive Summary",
            "Drive Link",
        ])
        
        # Data rows
        for item in summaries:
            ent = item.entities
            writer.writerow([
                item.file_name,
                item.file_type or friendly_type(item.mime_type),
                item.document_category,
                item.status,
                item.pages if item.pages is not None else "",
                item.word_count if item.word_count else "",
                item.tables_found if item.tables_found else "",
                f"{item.confidence:.0%}" if item.confidence else "",
                item.document_quality,
                _join(item.key_topics),
                _join(item.important_numbers),
                item.table_insights,
                _join(ent.organizations),
                _join(ent.monetary_values),
                _join(ent.percentages),
                _join(ent.dates),
                _join(ent.locations),
                item.summary or item.error_message or "",
                item.web_view_link,
            ])
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
            Paragraph(f"Generated: {generated}", s["subtitle"]),
            Paragraph(f"Folder ID: {_clean(folder_id or 'N/A')}", s["subtitle"]),
            Paragraph(
                f"{success} of {total} document(s) analyzed successfully",
                s["subtitle"],
            ),
            Spacer(1, 10),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")),
        ]

        for index, item in enumerate(summaries, start=1):
            story.extend(self._document_section(index, item, s))

        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
        return buffer.getvalue()

    def _document_section(self, index: int, item: DocumentSummary, s: dict) -> list:
        is_success = item.status == "success"

        # Status bar color
        status_color = {
            "success": colors.HexColor("#10b981"),
            "empty": colors.HexColor("#f59e0b"),
            "error": colors.HexColor("#ef4444"),
        }.get(item.status, colors.HexColor("#94a3b8"))

        flow: list = [
            Spacer(1, 10),
            # Colored status rule above heading
            HRFlowable(width="100%", thickness=3, color=status_color, spaceAfter=6),
            Paragraph(f"{index}. {_clean(item.file_name)}", s["heading"]),
        ]

        # Badges row: Type | Category | Status | Quality
        badges: list[str] = [
            f"<b>Type:</b> {_clean(item.file_type or friendly_type(item.mime_type))}",
            f"<b>Status:</b> {item.status.upper()}",
        ]
        if item.document_category:
            badges.append(f"<b>Category:</b> {_clean(item.document_category)}")
        if item.document_quality:
            badges.append(f"<b>Quality:</b> {_clean(item.document_quality)}")
        flow.append(Paragraph("  |  ".join(badges), s["meta"]))

        if is_success:
            # Metrics grid: Pages · Words · Tables · Confidence
            metrics_data = [[
                f"Pages\n{item.pages if item.pages is not None else '—'}",
                f"Words\n{item.word_count:,}" if item.word_count else "Words\n—",
                f"Tables\n{item.tables_found}",
                f"Confidence\n{item.confidence:.0%}" if item.confidence else "Confidence\n—",
            ]]
            metrics_tbl = Table(metrics_data, colWidths=["25%", "25%", "25%", "25%"])
            metrics_tbl.setStyle(TableStyle([
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), _BODY_FONT_BOLD),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.HexColor("#f8fafc")]),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            flow.append(Spacer(1, 6))
            flow.append(metrics_tbl)
            flow.append(Spacer(1, 6))

            # Key Topics
            if item.key_topics:
                flow.append(Paragraph("KEY TOPICS", s["section_label"]))
                flow.append(Paragraph(
                    "  ·  ".join(_clean(t) for t in item.key_topics),
                    s["chip"],
                ))

            # Important Numbers
            if item.important_numbers:
                flow.append(Paragraph("IMPORTANT NUMBERS", s["section_label"]))
                for num in item.important_numbers:
                    flow.append(Paragraph(f"• {_clean(num)}", s["bullet"]))

            # Table Insights
            if item.table_insights:
                flow.append(Paragraph("TABLE INSIGHTS", s["section_label"]))
                flow.append(Paragraph(
                    _clean(item.table_insights),
                    s["insight_box"],
                ))

            # Executive Summary
            flow.append(Paragraph("EXECUTIVE SUMMARY", s["section_label"]))
            body = item.summary or "No summary available."
            flow.append(Paragraph(_clean(body).replace("\n", "<br/>"), s["body"]))

            # Extracted Entities
            ent = item.entities
            entity_groups = [
                ("ORGANIZATIONS", ent.organizations, "#7c3aed"),
                ("MONETARY VALUES", ent.monetary_values, "#059669"),
                ("PERCENTAGES", ent.percentages, "#0284c7"),
                ("DATES", ent.dates, "#d97706"),
                ("LOCATIONS", ent.locations, "#e11d48"),
            ]
            has_entities = any(grp[1] for grp in entity_groups)
            if has_entities:
                flow.append(Paragraph("EXTRACTED ENTITIES", s["section_label"]))
                for group_label, items_list, hex_color in entity_groups:
                    if not items_list:
                        continue
                    flow.append(Paragraph(
                        f"<b>{group_label}:</b>  "
                        + "  ·  ".join(_clean(e) for e in items_list),
                        ParagraphStyle(
                            f"entity_{group_label}",
                            parent=s["chip"],
                            fontName=_BODY_FONT,
                            textColor=colors.HexColor(hex_color),
                        ),
                    ))

        else:
            # Error / empty
            flow.append(Paragraph("SUMMARY", s["section_label"]))
            flow.append(Paragraph(
                _clean(item.summary or item.error_message or "No content available."),
                s["body"],
            ))

        # Drive link
        if item.web_view_link:
            flow.append(Paragraph(
                f'<link href="{escape(item.web_view_link)}">Open in Google Drive</link>',
                s["link"],
            ))

        flow.append(Spacer(1, 6))
        flow.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#f1f5f9")))
        return flow


def _styles() -> dict:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=base["Title"],
            fontName=_BODY_FONT_BOLD,
            fontSize=22,
            textColor=colors.HexColor("#1d4ed8"),
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=9.5,
            textColor=colors.HexColor("#64748b"),
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "heading": ParagraphStyle(
            "FileHeading",
            parent=base["Heading2"],
            fontName=_BODY_FONT_BOLD,
            fontSize=13,
            textColor=colors.HexColor("#0f172a"),
            spaceBefore=4,
            spaceAfter=3,
        ),
        "meta": ParagraphStyle(
            "FileMeta",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=8.5,
            textColor=colors.HexColor("#64748b"),
            spaceAfter=6,
        ),
        "section_label": ParagraphStyle(
            "SectionLabel",
            parent=base["Normal"],
            fontName=_BODY_FONT_BOLD,
            fontSize=7.5,
            textColor=colors.HexColor("#94a3b8"),
            spaceBefore=8,
            spaceAfter=3,
            alignment=TA_LEFT,
        ),
        "chip": ParagraphStyle(
            "Chip",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=9,
            textColor=colors.HexColor("#334155"),
            leading=13,
            spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "Bullet",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=9,
            textColor=colors.HexColor("#334155"),
            leftIndent=10,
            spaceAfter=2,
            leading=13,
        ),
        "insight_box": ParagraphStyle(
            "InsightBox",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=9,
            textColor=colors.HexColor("#1e40af"),
            backColor=colors.HexColor("#eff6ff"),
            borderPad=5,
            leading=13,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#374151"),
            spaceBefore=2,
            spaceAfter=4,
        ),
        "link": ParagraphStyle(
            "DriveLink",
            parent=base["Normal"],
            fontName=_BODY_FONT,
            fontSize=8.5,
            textColor=colors.HexColor("#1d4ed8"),
            spaceAfter=4,
        ),
    }


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont(_BODY_FONT, 8)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawCentredString(
        A4[0] / 2.0, 1.1 * cm, f"Document Intelligence Report  ·  Page {doc.page}"
    )
    canvas.restoreState()
