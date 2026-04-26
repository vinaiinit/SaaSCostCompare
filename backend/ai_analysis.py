"""
AI layer — used ONLY for:
1. Structured data extraction from PDFs (in extraction.py, not here)
2. Narrative generation from pre-computed comparison results

AI does NOT perform any analysis or comparison. All numbers come from
the peer comparison engine. AI only formats and presents them.
"""
import anthropic
import json
import os
from datetime import datetime
from sqlalchemy.orm import Session

from models import Report, Organization, BenchmarkReport


def generate_narrative(comparison_data: dict, org_profile: dict) -> dict:
    """
    Given structured comparison results (already computed from real peer data),
    generate a customer-friendly narrative report.

    Claude does NOT perform any analysis — it formats pre-computed data.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    items = comparison_data.get("items", [])
    summary = comparison_data.get("summary", {})

    prompt = f"""You are a professional report writer for a SaaS cost benchmarking platform.

Given the STRUCTURED COMPARISON DATA below (already computed from real peer contract data),
write a clear, professional narrative report.

CRITICAL RULES:
- Do NOT perform any additional analysis or generate any numbers not in the data below.
- Use the EXACT dollar amounts, percentiles, and assessments from the data.
- Do NOT invent, estimate, or extrapolate any figures.
- Do NOT name any research firms, reports, or external sources.
- Present the data in a customer-friendly, actionable format.

ORGANIZATION PROFILE:
- Name: {org_profile.get('name', 'N/A')}
- Industry: {org_profile.get('industry', 'N/A')}
- Company Size: {org_profile.get('size_band', 'N/A')}

COMPARISON SUMMARY:
- Total line items analyzed: {summary.get('total_items', 0)}
- Items with sufficient peer data: {summary.get('benchmarkable_items', 0)}
- Items with insufficient data: {summary.get('insufficient_data_items', 0)}
- Data coverage: {summary.get('coverage_pct', 0)}%
- Total annual spend (uploaded data): ${summary.get('total_annual_spend', 0):,.2f}
- Items above market: {summary.get('spend_above_market', 0)}
- Total potential savings: ${summary.get('total_potential_savings', 0):,.2f}

ASSESSMENT BREAKDOWN:
{json.dumps(summary.get('assessment_breakdown', {}), indent=2)}

DETAILED ITEM COMPARISONS:
{json.dumps(items, indent=2)}

Write the report with these EXACT sections:

## Executive Summary
2-3 sentences summarizing the overall position using the data above. State the coverage percentage,
how many items are above/below market, and the total potential savings figure.

## Peer Comparison Results
For each item that has sufficient peers, present:
- Product name and the user's annual cost
- Peer median and percentile position (use exact numbers from the data)
- Assessment (well below / below / at / above market)
- Potential savings if above market

## Items With Limited Data
List any items where peer data was insufficient. Explain that as more organizations
contribute data, these items will become benchmarkable.

## Key Findings
3-5 bullet points drawn directly from the data. Use specific dollar amounts.

## Recommendations
Prioritized actions based on which items are above market, ordered by potential savings.

Use specific dollar amounts and percentages throughout. Be direct and actionable.
Do NOT use markdown table separator lines (|---|).
"""

    try:
        message = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "narrative": message.content[0].text,
            "peer_count": summary.get("benchmarkable_items", 0),
            "total_spend": summary.get("total_annual_spend", 0),
            "total_potential_savings": summary.get("total_potential_savings", 0),
            "coverage_pct": summary.get("coverage_pct", 0),
            "generated_at": str(datetime.now()),
        }
    except Exception as e:
        print(f"Error generating narrative: {e}")
        return {"error": str(e)}


def process_upload(report_id: str, file_path: str, org_id: int, db: Session):
    """
    Main processing function: extract structured data from uploaded files.
    Replaces the old AI-analysis process_report function.
    """
    from extraction import run_extraction

    try:
        result = run_extraction(report_id, file_path, org_id, db)
        return {"status": "extracted", "report_id": report_id, **result}
    except Exception as e:
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.status = "failed"
            report.comparison_result = json.dumps({"error": str(e)})
            db.commit()
        return {"error": str(e), "report_id": report_id}
