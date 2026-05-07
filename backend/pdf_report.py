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

PAGE_W, PAGE_H = A4


def _header_footer(canvas, doc):
    """Draw header bar and footer on every page."""
    canvas.saveState()

    # Top navy bar
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - 18*mm, PAGE_W, 18*mm, fill=1, stroke=0)

    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawString(20*mm, PAGE_H - 12*mm, "SaaSCostCompare")
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(PAGE_W - 20*mm, PAGE_H - 12*mm, "CONFIDENTIAL — FOR AUTHORISED USE ONLY")

    # Footer
    canvas.setStrokeColor(SLATE_MID)
    canvas.setLineWidth(0.5)
    canvas.line(20*mm, 14*mm, PAGE_W - 20*mm, 14*mm)

    canvas.setFillColor(SLATE)
    canvas.setFont("Helvetica", 7.5)
    canvas.drawString(20*mm, 9*mm,
        "© {} SaaSCostCompare. Independent SaaS Benchmarking. Vendor-neutral. Conflict-free.".format(
            datetime.now().year))
    canvas.drawRightString(PAGE_W - 20*mm, 9*mm, f"Page {doc.page}")

    canvas.restoreState()


# ── Helper functions ───────────────────────────────────────────────────────

def _fmt_currency(val):
    if val is None:
        return "—"
    try:
        return "${:,.0f}".format(float(val))
    except Exception:
        return "—"


def _fmt_number(val):
    if val is None:
        return "—"
    try:
        return "{:,.0f}".format(float(val))
    except Exception:
        return "—"


def _compute_variance_pct(user_cost, peer_median):
    if not peer_median or peer_median == 0:
        return 0.0
    return ((user_cost - peer_median) / peer_median) * 100


def _fmt_variance(pct):
    if pct > 0:
        return "+{:.0f}%".format(pct)
    elif pct < 0:
        return "{:.0f}%".format(pct)
    return "0%"


def _derive_recommendation(item):
    assessment = item.get("assessment", "")
    variance = _compute_variance_pct(
        item.get("user_unit_cost_annual", 0),
        item.get("peer_median", 0),
    )
    abs_var = abs(variance)

    if assessment == "above_market":
        if abs_var > 25:
            return "Consider alternative tier"
        elif abs_var > 10:
            return "Negotiate volume discount"
        else:
            return "Renegotiate at renewal"
    elif assessment == "at_market":
        return "Standard pricing"
    elif assessment == "below_market":
        return "Competitive rate"
    elif assessment == "well_below_market":
        return "Well positioned"
    return "Monitor"


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


def _get_section_body(sections, title):
    """Find a section by title (case-insensitive partial match)."""
    title_lower = title.lower()
    for sec in sections:
        if title_lower in sec["title"].lower():
            return sec["body"]
    return ""


def _render_narrative_body(body, styles, story):
    """Render a narrative section body (bullets and paragraphs) into the story."""
    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 2*mm))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            txt = stripped[2:].replace("**", "")
            if txt.startswith("*") and txt.endswith("*"):
                # Italicized CTA line
                story.append(Spacer(1, 3*mm))
                story.append(Paragraph(f"<i>{txt.strip('*')}</i>", styles["cta"]))
            else:
                story.append(Paragraph(f"•&nbsp;&nbsp;{txt}", styles["bullet"]))
        elif stripped.startswith("*") and stripped.endswith("*"):
            # Standalone italicized CTA
            story.append(Spacer(1, 3*mm))
            story.append(Paragraph(f"<i>{stripped.strip('*')}</i>", styles["cta"]))
        else:
            txt = stripped.replace("**", "")
            story.append(Paragraph(txt, styles["body"]))


def _build_results_table(comparison_data, styles):
    """Build the Section 4 detailed benchmarking results table from structured data."""
    if not comparison_data or "items" not in comparison_data:
        return None

    items = [i for i in comparison_data["items"] if i.get("has_sufficient_peers")]
    if not items:
        return None

    cell_style = ParagraphStyle("cell", fontName="Helvetica", fontSize=8,
                                leading=10, textColor=BLACK)
    cell_bold = ParagraphStyle("cell_bold", fontName="Helvetica-Bold", fontSize=8,
                               leading=10, textColor=BLACK)
    header_style = ParagraphStyle("hdr", fontName="Helvetica-Bold", fontSize=8,
                                  leading=10, textColor=WHITE, alignment=TA_CENTER)

    headers = [
        Paragraph("SKU", header_style),
        Paragraph("Quantity", header_style),
        Paragraph("Unit Price<br/>(USD)", header_style),
        Paragraph("Peer<br/>Median", header_style),
        Paragraph("Peer<br/>Range", header_style),
        Paragraph("Variance", header_style),
        Paragraph("Recommendation", header_style),
    ]

    rows = [headers]

    total_user_spend = 0
    total_peer_median_spend = 0
    total_peer_low = 0
    total_peer_high = 0
    highest_var_sku = ""
    highest_var = 0

    for item in items:
        user_cost = item.get("user_unit_cost_annual", 0)
        peer_med = item.get("peer_median", 0)
        peer_p25 = item.get("peer_p25", 0)
        peer_p75 = item.get("peer_p75", 0)
        qty = item.get("user_quantity", 1)
        variance = _compute_variance_pct(user_cost, peer_med)

        total_user_spend += item.get("user_total_annual", user_cost * qty)
        total_peer_median_spend += peer_med * qty
        total_peer_low += peer_p25 * qty
        total_peer_high += peer_p75 * qty

        if abs(variance) > abs(highest_var):
            highest_var = variance
            highest_var_sku = item.get("product_name", "")

        peer_range = f"{_fmt_number(peer_p25)}–{_fmt_number(peer_p75)}"

        row = [
            Paragraph(item.get("product_name", ""), cell_style),
            Paragraph(str(int(qty)), cell_style),
            Paragraph(_fmt_number(user_cost), cell_style),
            Paragraph(_fmt_number(peer_med), cell_style),
            Paragraph(peer_range, cell_style),
            Paragraph(_fmt_variance(variance), cell_style),
            Paragraph(_derive_recommendation(item), cell_style),
        ]
        rows.append(row)

    # Total row
    total_var = _compute_variance_pct(total_user_spend, total_peer_median_spend)
    opt_hint = f"optimize {highest_var_sku[:20]}" if highest_var_sku else "review pricing"
    total_row = [
        Paragraph("Total Spend", cell_bold),
        Paragraph("-", cell_style),
        Paragraph(_fmt_number(total_user_spend), cell_bold),
        Paragraph(_fmt_number(total_peer_median_spend), cell_bold),
        Paragraph(f"{_fmt_number(total_peer_low)}–{_fmt_number(total_peer_high)}", cell_style),
        Paragraph(_fmt_variance(total_var), cell_bold),
        Paragraph(f"Renegotiate contract; {opt_hint}", cell_style),
    ]
    rows.append(total_row)

    usable_w = PAGE_W - 40*mm
    col_widths = [
        usable_w * 0.25,  # SKU
        usable_w * 0.08,  # Qty
        usable_w * 0.13,  # Unit Price
        usable_w * 0.13,  # Peer Median
        usable_w * 0.15,  # Peer Range
        usable_w * 0.10,  # Variance
        usable_w * 0.16,  # Recommendation
    ]

    table = Table(rows, colWidths=col_widths, repeatRows=1)
    last_data_row = len(rows) - 2  # row before total
    total_row_idx = len(rows) - 1

    style_cmds = [
        ("BACKGROUND",    (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 8),
        ("BACKGROUND",    (0, 1), (-1, last_data_row), WHITE),
        ("ROWBACKGROUNDS",(0, 1), (-1, last_data_row), [WHITE, SLATE_LIGHT]),
        ("FONTNAME",      (0, 1), (-1, last_data_row), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 8),
        ("TEXTCOLOR",     (0, 1), (-1, -1), BLACK),
        # Total row styling
        ("BACKGROUND",    (0, total_row_idx), (-1, total_row_idx), BLUE_LIGHT),
        ("FONTNAME",      (0, total_row_idx), (0, total_row_idx), "Helvetica-Bold"),
        # Grid
        ("GRID",          (0, 0), (-1, -1), 0.4, SLATE_MID),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]
    table.setStyle(TableStyle(style_cmds))
    return table


def _revenue_band_label(revenue_band):
    mapping = {
        "under_1m": "under $1M",
        "1m_10m": "$1–10M",
        "10m_100m": "$10–100M",
        "100m_500m": "$100–500M",
        "500m_1b": "$500M–1B",
        "over_1b": "over $1B",
    }
    return mapping.get(revenue_band, revenue_band or "N/A")


def _size_band_label(size_band):
    mapping = {
        "1-50": "1–50 employees",
        "51-200": "51–200 employees",
        "201-1000": "201–1,000 employees",
        "1001-5000": "1,001–5,000 employees",
        "5001+": "5,001+ employees",
    }
    return mapping.get(size_band, size_band or "N/A")


# ── Main PDF generator ─────────────────────────────────────────────────────

def generate_pdf_report(report, org, benchmark_result, analysis_text,
                        comparison_data=None, contract_term=None) -> bytes:
    """
    Generate a professional PDF benchmarking report matching the 7-section layout.
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
    S = {
        "report_title": ParagraphStyle("report_title",
            fontName="Helvetica-Bold", fontSize=24, textColor=NAVY,
            leading=30, spaceAfter=16),
        "section_header": ParagraphStyle("section_header",
            fontName="Helvetica-Bold", fontSize=14, textColor=NAVY,
            spaceBefore=16, spaceAfter=6),
        "kv_line": ParagraphStyle("kv_line",
            fontName="Helvetica", fontSize=10, textColor=BLACK,
            leading=16, spaceAfter=2),
        "body": ParagraphStyle("body",
            fontName="Helvetica", fontSize=9.5, textColor=BLACK,
            leading=14, spaceAfter=4, alignment=TA_JUSTIFY),
        "bullet": ParagraphStyle("bullet",
            fontName="Helvetica", fontSize=9.5, textColor=BLACK,
            leading=14, spaceAfter=6, leftIndent=18, bulletIndent=0),
        "cta": ParagraphStyle("cta",
            fontName="Helvetica-Oblique", fontSize=9, textColor=SLATE,
            leading=13, spaceAfter=4, spaceBefore=6),
        "small": ParagraphStyle("small",
            fontName="Helvetica", fontSize=8, textColor=SLATE,
            leading=12, spaceAfter=2),
    }

    story = []
    vendor_name = report.get("category", "SaaS")
    org_name = org.get("name", "Organisation")
    org_industry = org.get("industry", "N/A")
    org_size = org.get("size", 0)
    org_revenue = org.get("revenue", 0)

    summary = comparison_data.get("summary", {}) if comparison_data else {}
    total_spend = summary.get("total_annual_spend", benchmark_result.get("total_spend", 0))

    # Parse AI narrative sections
    sections = _parse_benchmark_sections(analysis_text) if analysis_text else []

    # ── TITLE ───────────────────────────────────────────────────────────────
    title_text = f"{vendor_name} Benchmarking Report –<br/>{org_name}"
    story.append(Paragraph(title_text, S["report_title"]))
    story.append(Spacer(1, 4*mm))

    # ── SECTION 1: Benchmarking Overview ────────────────────────────────────
    story.append(Paragraph("1. Benchmarking Overview", S["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SLATE_MID, spaceAfter=8))

    scope = vendor_name
    if comparison_data and "items" in comparison_data:
        product_names = list({i.get("product_name", "") for i in comparison_data["items"] if i.get("product_name")})
        if len(product_names) == 1:
            scope = f"{vendor_name} — {product_names[0]}"
        elif len(product_names) > 1:
            scope = f"{vendor_name} + Add-ons"

    kv_pairs = [
        ("Client", f"{org_name} ({org_industry})" if org_industry != "N/A" else org_name),
        ("Employees", f"{org_size:,}" if org_size else "N/A"),
        ("Revenue", _fmt_currency(org_revenue) if org_revenue else "N/A"),
        ("Scope", scope),
        ("Contract Term", contract_term or "N/A"),
        ("Total Spend", f"USD {total_spend:,.0f}" if total_spend else "N/A"),
    ]
    for label, value in kv_pairs:
        story.append(Paragraph(f"<b>{label}:</b> {value}", S["kv_line"]))
    story.append(Spacer(1, 4*mm))

    # ── SECTION 2: Executive Summary ────────────────────────────────────────
    story.append(Paragraph("2. Executive Summary", S["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SLATE_MID, spaceAfter=8))

    exec_body = _get_section_body(sections, "Executive Summary")
    if exec_body:
        _render_narrative_body(exec_body, S, story)
    else:
        story.append(Paragraph("Executive summary not available.", S["body"]))
    story.append(Spacer(1, 4*mm))

    # ── SECTION 3: Details of Benchmarking Dataset ──────────────────────────
    story.append(Paragraph("3. Details of Benchmarking Dataset", S["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SLATE_MID, spaceAfter=8))

    # Derive peer group description
    size_label = _size_band_label(org.get("size_band"))
    rev_label = _revenue_band_label(org.get("revenue_band"))
    industry_label = org_industry if org_industry != "N/A" else "cross-industry"
    peer_group = f"{industry_label}-sector organizations ({size_label}, {rev_label} revenue)"

    # Count peer orgs from comparison data
    peer_org_count = 0
    if comparison_data and "items" in comparison_data:
        peer_counts = [i.get("peer_org_count", 0) for i in comparison_data["items"] if i.get("has_sufficient_peers")]
        peer_org_count = max(peer_counts) if peer_counts else 0

    dataset_pairs = [
        ("Peer Group", peer_group),
        ("Number of Peer Organizations", str(peer_org_count) if peer_org_count else "N/A"),
        ("Data Age", "Less than 12 months old"),
        ("Regions", "North America (US + Canada)"),
    ]
    for label, value in dataset_pairs:
        story.append(Paragraph(f"<b>{label}:</b> {value}", S["kv_line"]))
    story.append(Spacer(1, 4*mm))

    # ── SECTION 4: Detailed Benchmarking Results ────────────────────────────
    story.append(Paragraph("4. Detailed Benchmarking Results", S["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SLATE_MID, spaceAfter=8))

    results_table = _build_results_table(comparison_data, S)
    if results_table:
        story.append(results_table)
    else:
        story.append(Paragraph(
            "Detailed comparison data not available. Ensure the peer comparison has been run.",
            S["body"]))
    story.append(Spacer(1, 4*mm))

    # ── SECTION 5: Aggregated Fee Benchmarks ────────────────────────────────
    story.append(Paragraph("5. Aggregated Fee Benchmarks", S["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SLATE_MID, spaceAfter=8))

    agg_body = _get_section_body(sections, "Aggregated Fee Benchmarks")
    if agg_body:
        _render_narrative_body(agg_body, S, story)
    else:
        story.append(Paragraph("Aggregated benchmarks not available.", S["body"]))
    story.append(Spacer(1, 4*mm))

    # ── SECTION 6: Additional Levers for Optimization ───────────────────────
    story.append(Paragraph("6. Additional Levers for Optimization", S["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SLATE_MID, spaceAfter=8))

    opt_body = _get_section_body(sections, "Additional Levers")
    if opt_body:
        _render_narrative_body(opt_body, S, story)
    else:
        story.append(Paragraph("Optimization levers not available.", S["body"]))
    story.append(Spacer(1, 4*mm))

    # ── SECTION 7: Negotiation Insights ─────────────────────────────────────
    story.append(Paragraph("7. Negotiation Insights", S["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=SLATE_MID, spaceAfter=8))

    neg_body = _get_section_body(sections, "Negotiation Insights")
    if neg_body:
        _render_narrative_body(neg_body, S, story)
    else:
        story.append(Paragraph("Negotiation insights not available.", S["body"]))
    story.append(Spacer(1, 6*mm))

    # ── DISCLAIMER ──────────────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=SLATE_MID))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(
        "<b>Disclaimer:</b> This report is prepared by SaaSCostCompare for the exclusive use of the "
        "commissioning organisation. Benchmark figures are indicative and based on anonymised peer data. "
        "SaaSCostCompare provides no warranty as to the accuracy of vendor pricing. "
        "This document is confidential and must not be shared with vendors.",
        S["small"]
    ))

    doc.build(story)
    buf.seek(0)
    return buf.read()
