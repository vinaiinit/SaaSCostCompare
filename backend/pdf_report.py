import io
import json
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.platypus import BaseDocTemplate, Frame, PageTemplate


# ── Brand colours ──────────────────────────────────────────────────────────
NAVY      = colors.HexColor("#003366")
NAVY_DARK = colors.HexColor("#001f4d")
BLUE      = colors.HexColor("#0284c7")
BLUE_LIGHT= colors.HexColor("#e0f0ff")
GOLD      = colors.HexColor("#f59e0b")
SLATE     = colors.HexColor("#475569")
SLATE_LIGHT = colors.HexColor("#f8fafc")
SLATE_MID   = colors.HexColor("#e2e8f0")
WHITE     = colors.white
BLACK     = colors.HexColor("#0f172a")
GREEN     = colors.HexColor("#16a34a")
RED       = colors.HexColor("#dc2626")


def _header_footer(canvas, doc):
    """Draw header bar and footer on every page."""
    canvas.saveState()
    w, h = A4

    # Top navy bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, h - 18*mm, w, 18*mm, fill=1, stroke=0)

    # Logo text in header
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(20*mm, h - 12*mm, "SaaSCostCompare")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(w - 20*mm, h - 12*mm, "CONFIDENTIAL — FOR AUTHORISED USE ONLY")

    # Footer line
    canvas.setStrokeColor(SLATE_MID)
    canvas.setLineWidth(0.5)
    canvas.line(20*mm, 14*mm, w - 20*mm, 14*mm)

    canvas.setFillColor(SLATE)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(20*mm, 9*mm,
        "© {} SaaSCostCompare. Independent SaaS Benchmarking. Vendor-neutral. Conflict-free.".format(
            datetime.now().year))
    canvas.drawRightString(w - 20*mm, 9*mm, f"Page {doc.page}")

    canvas.restoreState()


def _fmt_currency(val):
    if val is None:
        return "—"
    try:
        return "${:,.0f}".format(float(val))
    except Exception:
        return "—"


def _fmt_pct(val):
    if val is None:
        return "—"
    try:
        return "{:.1f}%".format(float(val))
    except Exception:
        return "—"


def _parse_benchmark_sections(text):
    """Split markdown-style benchmark report into section dicts {title, body}."""
    sections = []
    current_title = None
    current_lines = []
    for line in text.split("\n"):
        if line.startswith("## "):
            if current_title is not None:
                sections.append({"title": current_title, "body": "\n".join(current_lines).strip()})
            current_title = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_title:
        sections.append({"title": current_title, "body": "\n".join(current_lines).strip()})
    return sections


def _is_table_line(line: str) -> bool:
    return line.strip().startswith("|") and line.strip().endswith("|")


def _build_table_from_lines(lines):
    rows = []
    for line in lines:
        if not line.strip():
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c.replace("-", "").replace(":", "").replace(" ", "")) == set() for c in cells):
            continue  # separator row
        rows.append(cells)
    if len(rows) < 2:
        return None

    col_count = max(len(r) for r in rows)
    # Normalise row lengths
    rows = [r + [""] * (col_count - len(r)) for r in rows]

    col_width = (A4[0] - 40*mm) / col_count
    table = Table(rows, colWidths=[col_width] * col_count, repeatRows=1)
    style = TableStyle([
        ("BACKGROUND",  (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",   (0, 0), (-1, 0), WHITE),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 8),
        ("BACKGROUND",  (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, SLATE_LIGHT]),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 8),
        ("TEXTCOLOR",   (0, 1), (-1, -1), BLACK),
        ("GRID",        (0, 0), (-1, -1), 0.4, SLATE_MID),
        ("TOPPADDING",  (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN",      (0, 0), (-1, -1), "MIDDLE"),
    ])
    table.setStyle(style)
    return table


def generate_pdf_report(report, org, benchmark_result, analysis_text) -> bytes:
    """
    Generate a professional PDF benchmarking report.
    Returns raw PDF bytes.
    """
    buf = io.BytesIO()
    doc = BaseDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=25*mm,
        bottomMargin=22*mm,
        title="SaaSCostCompare Benchmarking Report",
        author="SaaSCostCompare",
    )

    frame = Frame(
        doc.leftMargin, doc.bottomMargin,
        doc.width, doc.height,
        id="main"
    )
    template = PageTemplate(id="main", frames=frame, onPage=_header_footer)
    doc.addPageTemplates([template])

    # ── Styles ──────────────────────────────────────────────────────────────
    base = getSampleStyleSheet()

    def style(name, **kw):
        return ParagraphStyle(name, **kw)

    S = {
        "cover_title": style("cover_title",
            fontName="Helvetica-Bold", fontSize=28, textColor=WHITE,
            leading=34, spaceAfter=6),
        "cover_sub": style("cover_sub",
            fontName="Helvetica", fontSize=13, textColor=colors.HexColor("#93c5fd"),
            leading=18, spaceAfter=4),
        "cover_meta": style("cover_meta",
            fontName="Helvetica", fontSize=9, textColor=colors.HexColor("#cbd5e1"),
            leading=14),
        "section_title": style("section_title",
            fontName="Helvetica-Bold", fontSize=13, textColor=NAVY,
            spaceBefore=14, spaceAfter=6, borderPad=0,
            leftIndent=0),
        "body": style("body",
            fontName="Helvetica", fontSize=9, textColor=BLACK,
            leading=14, spaceAfter=4, alignment=TA_JUSTIFY),
        "bullet": style("bullet",
            fontName="Helvetica", fontSize=9, textColor=BLACK,
            leading=13, spaceAfter=3, leftIndent=12, bulletIndent=0),
        "small": style("small",
            fontName="Helvetica", fontSize=8, textColor=SLATE,
            leading=12, spaceAfter=2),
        "label": style("label",
            fontName="Helvetica-Bold", fontSize=8, textColor=SLATE,
            leading=11, spaceAfter=1),
        "metric_val": style("metric_val",
            fontName="Helvetica-Bold", fontSize=22, textColor=NAVY,
            leading=26, spaceAfter=0),
        "metric_label": style("metric_label",
            fontName="Helvetica", fontSize=8, textColor=SLATE,
            leading=10),
        "tag": style("tag",
            fontName="Helvetica-Bold", fontSize=7.5, textColor=WHITE,
            leading=10),
    }

    story = []

    # ── COVER PAGE ──────────────────────────────────────────────────────────
    # Full-bleed navy cover block via a tall table
    cover_data = [[""]]
    cover_table = Table(cover_data, colWidths=[doc.width], rowHeights=[80*mm])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY_DARK),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(cover_table)
    story.append(Spacer(1, -80*mm))  # overlap

    # Text over the cover block
    story.append(Spacer(1, 10*mm))
    story.append(Paragraph("SaaS Cost Benchmarking", S["cover_sub"]))
    story.append(Paragraph(
        f"{org.get('name', 'Organisation')} — Cost Intelligence Report",
        S["cover_title"]
    ))
    story.append(Paragraph(
        f"Industry: {org.get('domain', 'N/A')}  &nbsp;|&nbsp;  "
        f"Employees: {org.get('size', 'N/A')}  &nbsp;|&nbsp;  "
        f"Revenue: {_fmt_currency(org.get('revenue'))}",
        S["cover_meta"]
    ))
    story.append(Paragraph(
        f"Report generated: {datetime.now().strftime('%d %B %Y')}  &nbsp;|&nbsp;  "
        f"File: {report.get('filename', 'N/A')}  &nbsp;|&nbsp;  "
        f"Category: {report.get('category', 'N/A')}",
        S["cover_meta"]
    ))
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#1e3a5f")))
    story.append(Spacer(1, 4*mm))

    # ── KEY METRICS STRIP ───────────────────────────────────────────────────
    total_spend       = benchmark_result.get("total_spend")
    spend_per_emp     = benchmark_result.get("spend_per_employee")
    spend_pct_rev     = benchmark_result.get("spend_pct_revenue")
    peer_count        = benchmark_result.get("peer_count", 0)
    generated_at      = benchmark_result.get("generated_at", "")

    def metric_cell(val, label, bg=BLUE_LIGHT):
        return [
            Paragraph(val, ParagraphStyle("mv", fontName="Helvetica-Bold",
                fontSize=20, textColor=NAVY, leading=24, alignment=TA_CENTER)),
            Spacer(1, 2),
            Paragraph(label, ParagraphStyle("ml", fontName="Helvetica",
                fontSize=8, textColor=SLATE, leading=10, alignment=TA_CENTER)),
        ]

    metrics_table = Table(
        [[
            metric_cell(_fmt_currency(total_spend), "Total SaaS Spend"),
            metric_cell(_fmt_currency(spend_per_emp), "Per Employee"),
            metric_cell(_fmt_pct(spend_pct_rev), "% of Revenue"),
            metric_cell(str(peer_count), "Peer Orgs Compared"),
        ]],
        colWidths=[doc.width / 4] * 4,
        rowHeights=[22*mm],
    )
    metrics_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), BLUE_LIGHT),
        ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#ede9fe")),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#dcfce7")),
        ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#fef9c3")),
        ("BOX",        (0, 0), (-1, -1), 0.5, SLATE_MID),
        ("INNERGRID",  (0, 0), (-1, -1), 0.5, SLATE_MID),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(metrics_table)
    story.append(Spacer(1, 3*mm))

    # Data source note
    if peer_count > 0:
        source_text = (f"Benchmarks based on <b>{peer_count} peer organisation(s)</b> "
                       f"from the SaaSCostCompare panel with similar revenue and headcount.")
    else:
        source_text = ("No peer organisations with matching revenue/size found in the current panel. "
                       "Benchmarks are based on AI-derived industry knowledge.")
    story.append(Paragraph(source_text, S["small"]))
    story.append(Spacer(1, 6*mm))

    # ── BENCHMARK REPORT SECTIONS ───────────────────────────────────────────
    bm_text = benchmark_result.get("report", "")
    sections = _parse_benchmark_sections(bm_text)

    for sec in sections:
        story.append(HRFlowable(width="100%", thickness=1, color=BLUE_LIGHT, spaceAfter=4))
        story.append(Paragraph(sec["title"], S["section_title"]))

        lines = sec["body"].split("\n")
        i = 0
        table_lines = []
        while i < len(lines):
            line = lines[i]
            if _is_table_line(line):
                table_lines.append(line)
                i += 1
                continue
            else:
                # flush any buffered table
                if table_lines:
                    tbl = _build_table_from_lines(table_lines)
                    if tbl:
                        story.append(Spacer(1, 2*mm))
                        story.append(tbl)
                        story.append(Spacer(1, 3*mm))
                    table_lines = []

                stripped = line.strip()
                if not stripped:
                    story.append(Spacer(1, 2*mm))
                elif stripped.startswith("- ") or stripped.startswith("* "):
                    # Remove bold markers
                    txt = stripped[2:].replace("**", "")
                    story.append(Paragraph(f"• &nbsp; {txt}", S["bullet"]))
                elif stripped[:2].isdigit() and stripped[1] in ".)" or \
                        stripped[:1].isdigit() and len(stripped) > 1 and stripped[1] in ".)":
                    txt = stripped.split(".", 1)[-1].strip().replace("**", "")
                    story.append(Paragraph(f"{stripped[0]}. &nbsp; {txt}", S["bullet"]))
                else:
                    txt = stripped.replace("**", "")
                    story.append(Paragraph(txt, S["body"]))
                i += 1

        # flush remaining table
        if table_lines:
            tbl = _build_table_from_lines(table_lines)
            if tbl:
                story.append(Spacer(1, 2*mm))
                story.append(tbl)
                story.append(Spacer(1, 3*mm))

    # ── AI ANALYSIS SECTION ─────────────────────────────────────────────────
    if analysis_text:
        story.append(PageBreak())
        story.append(HRFlowable(width="100%", thickness=1, color=BLUE_LIGHT, spaceAfter=4))
        story.append(Paragraph("AI Cost Analysis", S["section_title"]))
        story.append(Paragraph(
            "The following analysis was generated by the SaaSCostCompare AI engine upon processing "
            "the uploaded expense report.",
            S["small"]
        ))
        story.append(Spacer(1, 3*mm))
        for line in analysis_text.split("\n"):
            stripped = line.strip()
            if not stripped:
                story.append(Spacer(1, 2*mm))
            elif stripped.startswith("- ") or stripped.startswith("* "):
                story.append(Paragraph(f"• &nbsp; {stripped[2:].replace('**','')}", S["bullet"]))
            else:
                story.append(Paragraph(stripped.replace("**", ""), S["body"]))

    # ── DISCLAIMER ──────────────────────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_MID))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "<b>Disclaimer:</b> This report is prepared by SaaSCostCompare for the exclusive use of the "
        "commissioning organisation. Benchmark figures are indicative and based on anonymised peer data "
        "and/or AI-derived industry knowledge. SaaSCostCompare provides no warranty as to the accuracy "
        "of vendor pricing. This document is confidential and must not be shared with vendors.",
        S["small"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
