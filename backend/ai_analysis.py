import anthropic
import json
import os
import csv
from datetime import datetime
from sqlalchemy.orm import Session
from models import Report, Organization, BenchmarkReport


def read_saas_report(file_path: str) -> dict:
    """
    Read and parse SaaS expense report (CSV/JSON).
    Returns structured data: {software: cost, category, etc.}
    """
    data = {"items": []}

    if file_path.endswith(".csv"):
        try:
            with open(file_path, "r") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    data["items"].append(row)
        except Exception as e:
            print(f"Error reading CSV: {e}")
    elif file_path.endswith(".json"):
        try:
            with open(file_path, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading JSON: {e}")

    return data


def analyze_with_claude(report_data: dict, org_profile: dict) -> str:
    """
    Use Claude to analyze SaaS expenses and generate insights.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""
Analyze this organisation's SaaS spending data and provide insights.

The data uses a standardised schema with columns:
vendor, product_name, sku, sku_description, quantity, unit_price, total_cost,
billing_frequency, currency, contract_start_date, contract_end_date, notes.

Organisation Profile:
- Name: {org_profile.get('name')}
- Domain: {org_profile.get('domain')}
- Annual Revenue: ${org_profile.get('revenue', 0):,.0f}
- Employees: {org_profile.get('size', 0)}

SaaS Spend Data:
{json.dumps(report_data, indent=2)}

Please provide:
1. Total spend and per-employee cost
2. Top 5 most expensive SKUs by total_cost
3. Spend breakdown by vendor
4. Any SKUs with unusually high unit_price or quantity relative to the organisation's size
5. Contracts expiring within 90 days (use contract_end_date)
6. Immediate optimisation recommendations (consolidation, tier downgrades, etc.)

Format the response as clear, actionable insights using specific dollar amounts.
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
    except Exception as e:
        print(f"Error calling Claude API: {e}")
        return f"Analysis failed: {str(e)}"


def calculate_total_spend(report_data: dict) -> float:
    """Sum total_cost column across all line items."""
    total = 0.0
    for item in report_data.get("items", []):
        # Normalise key lookup (strip whitespace, lowercase)
        normalised = {k.strip().lower(): v for k, v in item.items()}
        raw = normalised.get("total_cost") or normalised.get("cost") or normalised.get("amount") or "0"
        try:
            total += float(str(raw).replace("$", "").replace(",", ""))
        except (ValueError, TypeError):
            pass
    return total


def generate_benchmark_report(
    target_data: dict, target_org: dict, peer_data: list
) -> dict:
    """
    Generate an AI benchmarking report comparing target org's SaaS spend vs peers.
    peer_data: list of {"org": {revenue, size}, "report": {items: [...]}}
    Falls back to Claude's training knowledge of industry benchmarks when peer data is sparse.
    """
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    total_spend = calculate_total_spend(target_data)
    employees = max(target_org.get("size", 1), 1)
    revenue = max(target_org.get("revenue", 1), 1)
    spend_per_employee = total_spend / employees
    spend_pct_revenue = (total_spend / revenue) * 100

    peer_section = ""
    if peer_data:
        peer_section = f"\n\nACTUAL PEER DATA ({len(peer_data)} similar organizations in database):\n"
        for i, peer in enumerate(peer_data, 1):
            peer_total = calculate_total_spend(peer["report"])
            peer_emp = max(peer["org"].get("size", 1), 1)
            peer_rev = max(peer["org"].get("revenue", 1), 1)
            peer_section += (
                f"\nPeer {i}: Revenue=${peer['org']['revenue']:,.0f}, "
                f"Employees={peer['org']['size']}, "
                f"Total SaaS Spend=${peer_total:,.0f} "
                f"(${peer_total/peer_emp:,.0f}/employee, {peer_total/peer_rev*100:.1f}% of revenue)\n"
            )
            # Include top items (truncated)
            items_preview = peer["report"].get("items", [])[:10]
            if items_preview:
                peer_section += f"Top tools: {json.dumps(items_preview)[:500]}\n"
    else:
        peer_section = (
            "\n\nNo peer organizations found in database with similar revenue/size. "
            "Use your expert knowledge of SaaS spending benchmarks for the industry inferred from the org's domain and name."
        )

    prompt = f"""You are a SaaS cost benchmarking expert. Generate a detailed benchmarking report comparing this organization's SaaS spending against industry peers.

TARGET ORGANIZATION:
- Name: {target_org.get("name")}
- Domain: {target_org.get("domain")}
- Annual Revenue: ${revenue:,.0f}
- Employees: {employees}
- Total SaaS Spend: ${total_spend:,.0f}
- SaaS Spend per Employee: ${spend_per_employee:,.0f}
- SaaS as % of Revenue: {spend_pct_revenue:.2f}%

TARGET ORG SAAS SPEND DATA:
{json.dumps(target_data, indent=2)[:3000]}
{peer_section}

Generate a comprehensive benchmarking report with EXACTLY these sections:

## Executive Summary
2-3 sentence overview of how this org compares to peers. Include a clear verdict (e.g., "above average spender", "well-optimized", "under-invested in key areas").

## Spend Benchmarks
| Metric | This Org | Industry Benchmark | Assessment |
|--------|----------|-------------------|------------|
| SaaS per employee | ${spend_per_employee:,.0f} | [typical range] | [rating] |
| SaaS % of revenue | {spend_pct_revenue:.1f}% | [typical range] | [rating] |
| Total SaaS tools | [count] | [typical range] | [rating] |

## Category Breakdown & Benchmarks
For each spending category present in the data (Productivity, CRM, DevTools, HR, Security, Marketing, etc.):
- This org's spend and % of total
- Industry benchmark for this category (for similar size/revenue)
- Assessment: Under-invested / On-target / Over-spending

## Tool-Level Analysis
Top tools by spend with benchmark context. Flag any tools that appear redundant, overpriced, or where a cheaper alternative exists.

## Percentile Ranking
Provide an estimated percentile ranking for overall SaaS spend efficiency (e.g., "65th percentile — you spend more than 65% of similar organizations"). Explain the ranking.

## Key Findings
3-5 specific, data-backed findings. Be precise with numbers.

## Prioritized Recommendations
Numbered list of specific actions, ordered by potential savings impact. Include estimated savings where possible.

Use specific dollar amounts and percentages throughout. Make the report actionable and direct.
"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        return {
            "report": message.content[0].text,
            "peer_count": len(peer_data),
            "total_spend": total_spend,
            "spend_per_employee": spend_per_employee,
            "spend_pct_revenue": spend_pct_revenue,
            "generated_at": str(datetime.now()),
        }
    except Exception as e:
        print(f"Error calling Claude API for benchmark: {e}")
        return {"error": str(e)}


def process_report(report_id: str, file_path: str, org_id: int, db: Session):
    """
    Main processing function: parse file, analyze with Claude, store results.
    """
    try:
        # Update report status
        report = db.query(Report).filter(Report.id == report_id).first()
        if not report:
            return {"error": "Report not found"}

        report.status = "processing"
        db.commit()

        # Read and parse the report file
        report_data = read_saas_report(file_path)

        # Get organization profile for context
        org = db.query(Organization).filter(Organization.id == org_id).first()
        org_profile = {
            "name": org.name,
            "domain": org.domain,
            "revenue": org.revenue,
            "size": org.size,
        }

        # Analyze with Claude
        analysis = analyze_with_claude(report_data, org_profile)

        # Store results
        report.comparison_result = json.dumps(
            {
                "analysis": analysis,
                "data_summary": {
                    "item_count": len(report_data.get("items", [])),
                    "analysis_date": str(datetime.now()),
                },
            }
        )
        report.status = "completed"
        db.commit()

        return {"status": "completed", "report_id": report_id}

    except Exception as e:
        report.status = "failed"
        report.comparison_result = json.dumps({"error": str(e)})
        db.commit()
        return {"error": str(e), "report_id": report_id}
