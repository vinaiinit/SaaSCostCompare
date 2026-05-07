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

    org_name = org_profile.get('name', 'N/A')
    org_industry = org_profile.get('industry', 'N/A')
    org_size = org_profile.get('size', 0)
    org_revenue = org_profile.get('revenue', 0)
    vendor_name = summary.get('org_name', org_name)
    total_spend = summary.get('total_annual_spend', 0)
    cost_per_employee = round(total_spend / org_size, 0) if org_size else 0

    prompt = f"""You are a professional report writer for a SaaS cost benchmarking platform called SaaSCostCompare.

Given the STRUCTURED COMPARISON DATA below (already computed from real peer contract data),
write narrative sections for a benchmarking report.

CRITICAL RULES:
- Do NOT perform any additional analysis or generate any numbers not in the data below.
- Use the EXACT dollar amounts, percentiles, and assessments from the data.
- Do NOT invent, estimate, or extrapolate any figures.
- Do NOT name any research firms, reports, or external sources.
- Do NOT produce markdown tables or numbered section prefixes (no "1.", "2." etc. before section titles).
- Do NOT produce sections called "Peer Comparison Results" or "Items With Limited Data" — those are handled separately.
- Write each bullet point as a substantive paragraph (3-4 sentences), not a single sentence.
- Refer to the client as "{org_name}" throughout.

ORGANIZATION PROFILE:
- Client Name: {org_name}
- Industry: {org_industry}
- Employees: {org_size:,}
- Revenue: ${org_revenue:,.0f}
- Cost per Employee: ${cost_per_employee:,.0f}

COMPARISON SUMMARY:
- Total line items analyzed: {summary.get('total_items', 0)}
- Items with sufficient peer data: {summary.get('benchmarkable_items', 0)}
- Items with insufficient data: {summary.get('insufficient_data_items', 0)}
- Data coverage: {summary.get('coverage_pct', 0)}%
- Total annual spend: ${total_spend:,.2f}
- Items above market: {summary.get('spend_above_market', 0)}
- Total potential savings: ${summary.get('total_potential_savings', 0):,.2f}

ASSESSMENT BREAKDOWN:
{json.dumps(summary.get('assessment_breakdown', {}), indent=2)}

DETAILED ITEM COMPARISONS:
{json.dumps(items, indent=2)}

Write the report with these EXACT four sections (use ## headings exactly as shown):

## Executive Summary
Exactly 3 bullet points (use "- " prefix for each):
1. State {org_name}'s overall spend relative to the peer median as a percentage (e.g., "approximately X% above the peer median"). Explain what this means for the organization's cost position.
2. Identify the single highest-variance SKU by name. Explain why it is an outlier and what specific action could reduce costs.
3. Identify a moderate-variance area. Explain the opportunity to optimize and how proactive adjustments can help.

## Aggregated Fee Benchmarks
Exactly 3 bullet points (use "- " prefix for each):
1. Compare total annual spend (USD {total_spend:,.0f}) against a computed peer median total. State the variance amount.
2. Compare cost per employee (USD {cost_per_employee:,.0f}) against a peer median cost per employee. Note what this indicates about ROI.
3. Provide a module/category breakdown by spend percentage (e.g., "CRM accounting for X% of spend, Sandbox Y%, Analytics Z%"). Comment on whether the distribution is typical.

## Additional Levers for Optimization
Exactly 3 bullet points (use "- " prefix for each) with specific, actionable strategies based on the data above. Each should reference specific SKUs or categories and explain the rationale.
After the bullets, add this exact line:
*For a deeper exploration of tailored optimization strategies beyond pricing, please contact us at advisory@saascostcompare.com to arrange a bespoke consulting engagement.*

## Negotiation Insights
Exactly 3 bullet points (use "- " prefix for each):
1. How renewal timing can be leveraged for better terms.
2. What discount ranges are typical among peers in this sector.
3. What target pricing should be for the highest-cost SKU to align with peer medians.
After the bullets, add this exact line:
*Need help turning these insights into a signed contract? SaaSCostCompare offers end-to-end negotiation support to right-size your stack and secure these target rates on your behalf. To discuss a dedicated advisory engagement, reach out to advisory@saascostcompare.com*

Use specific dollar amounts and percentages throughout. Be direct and actionable.
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=3000,
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
