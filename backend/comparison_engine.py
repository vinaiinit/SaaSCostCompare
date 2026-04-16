"""
Peer comparison engine — pure database-driven, no AI.

Matches user's contract line items against peers by:
  1. Vendor + Product + Industry + Size Band  (exact)
  2. Vendor + Product + Industry              (industry_only)
  3. Vendor + Product + Size Band             (size_only)
  4. Vendor + Product                         (broad)

Uses the first tier with >= MINIMUM_PEERS data points.
Calculates percentiles using sorted arrays (no numpy dependency).
"""
import json
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import ContractLineItem, Organization, Report


MINIMUM_PEERS = 5


def _percentile(sorted_values: list[float], pct: float) -> float:
    """Calculate percentile from a sorted list. pct in [0, 100]."""
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    k = (pct / 100) * (n - 1)
    f = int(k)
    c = f + 1
    if c >= n:
        return sorted_values[-1]
    d = k - f
    return sorted_values[f] + d * (sorted_values[c] - sorted_values[f])


def _percentile_of_score(sorted_values: list[float], score: float) -> float:
    """What percentile does `score` fall at within sorted_values? Returns 0-100."""
    if not sorted_values:
        return 50.0
    count_below = sum(1 for v in sorted_values if v < score)
    count_equal = sum(1 for v in sorted_values if v == score)
    return ((count_below + 0.5 * count_equal) / len(sorted_values)) * 100


def _classify(percentile: float) -> str:
    """Classify user's spend position."""
    if percentile <= 25:
        return "well_below_market"
    elif percentile <= 50:
        return "below_market"
    elif percentile <= 75:
        return "at_market"
    else:
        return "above_market"


def _get_peer_costs(
    db: Session,
    vendor_name: str,
    product_name: str,
    exclude_org_id: int,
    industry: str | None = None,
    size_band: str | None = None,
) -> list[float]:
    """Query peer cost_per_unit_annual for matching criteria."""
    q = db.query(ContractLineItem.cost_per_unit_annual).join(
        Organization, ContractLineItem.org_id == Organization.id
    ).filter(
        ContractLineItem.vendor_name == vendor_name,
        ContractLineItem.product_name == product_name,
        ContractLineItem.org_id != exclude_org_id,
        ContractLineItem.cost_per_unit_annual > 0,
    )
    if industry:
        q = q.filter(Organization.industry == industry)
    if size_band:
        q = q.filter(Organization.size_band == size_band)

    results = q.all()
    return sorted([r[0] for r in results])


def compare_line_item(item: ContractLineItem, org: Organization, db: Session) -> dict:
    """
    Compare a single line item against peers.
    Tries match tiers in order: exact → industry_only → size_only → broad.
    """
    result = {
        "line_item_id": item.id,
        "vendor_name": item.vendor_name,
        "product_name": item.product_name,
        "user_quantity": item.quantity,
        "user_unit_cost_annual": round(item.cost_per_unit_annual, 2),
        "user_total_annual": round(item.total_cost_annual, 2),
    }

    tiers = [
        ("exact", org.industry, org.size_band),
        ("industry_only", org.industry, None),
        ("size_only", None, org.size_band),
        ("broad", None, None),
    ]

    for tier_name, industry, size_band in tiers:
        peer_costs = _get_peer_costs(
            db, item.vendor_name, item.product_name, org.id,
            industry=industry, size_band=size_band,
        )
        if len(peer_costs) >= MINIMUM_PEERS:
            p25 = _percentile(peer_costs, 25)
            p50 = _percentile(peer_costs, 50)
            p75 = _percentile(peer_costs, 75)
            user_pct = _percentile_of_score(peer_costs, item.cost_per_unit_annual)
            assessment = _classify(user_pct)

            potential_savings = None
            if assessment == "above_market" and item.cost_per_unit_annual > p50:
                potential_savings = round((item.cost_per_unit_annual - p50) * item.quantity, 2)

            # Count distinct orgs contributing peer data
            org_count_q = db.query(func.count(func.distinct(ContractLineItem.org_id))).join(
                Organization, ContractLineItem.org_id == Organization.id
            ).filter(
                ContractLineItem.vendor_name == item.vendor_name,
                ContractLineItem.product_name == item.product_name,
                ContractLineItem.org_id != org.id,
                ContractLineItem.cost_per_unit_annual > 0,
            )
            if industry:
                org_count_q = org_count_q.filter(Organization.industry == industry)
            if size_band:
                org_count_q = org_count_q.filter(Organization.size_band == size_band)
            peer_org_count = org_count_q.scalar() or 0

            result.update({
                "has_sufficient_peers": True,
                "match_tier": tier_name,
                "peer_count": len(peer_costs),
                "peer_org_count": peer_org_count,
                "peer_p25": round(p25, 2),
                "peer_median": round(p50, 2),
                "peer_p75": round(p75, 2),
                "peer_min": round(peer_costs[0], 2),
                "peer_max": round(peer_costs[-1], 2),
                "user_percentile": round(user_pct, 1),
                "assessment": assessment,
                "potential_annual_savings": potential_savings,
            })
            return result

    # Not enough peers in any tier
    # Get whatever data exists for context
    all_peers = _get_peer_costs(db, item.vendor_name, item.product_name, org.id)
    result.update({
        "has_sufficient_peers": False,
        "match_tier": None,
        "peer_count": len(all_peers),
        "peer_org_count": 0,
        "insufficient_data": True,
    })
    return result


def generate_comparison(upload_id: str, db: Session) -> dict:
    """
    Main comparison entry point. Compare all line items for an upload
    against peer data in the database.

    Returns the full comparison output (Interface 2 format):
    {"items": [...], "summary": {...}}
    """
    report = db.query(Report).filter(Report.id == upload_id).first()
    if not report:
        return {"error": "Upload not found"}

    org = db.query(Organization).filter(Organization.id == report.org_id).first()
    if not org:
        return {"error": "Organization not found"}

    # Ensure org has bands computed
    if not org.size_band or not org.revenue_band:
        org.compute_bands()
        db.commit()

    # Get this upload's line items
    user_items = db.query(ContractLineItem).filter(
        ContractLineItem.upload_id == upload_id
    ).all()

    if not user_items:
        return {"error": "No line items found for this upload. Please check extraction results."}

    # Compare each item
    item_results = []
    for item in user_items:
        result = compare_line_item(item, org, db)
        item_results.append(result)

    # Build summary
    benchmarkable = [r for r in item_results if r.get("has_sufficient_peers")]
    insufficient = [r for r in item_results if r.get("insufficient_data")]
    above_market = [r for r in benchmarkable if r.get("assessment") == "above_market"]

    total_spend = sum(r["user_total_annual"] for r in item_results)
    total_savings = sum(r.get("potential_annual_savings", 0) or 0 for r in item_results)

    assessment_breakdown = {
        "well_below_market": sum(1 for r in benchmarkable if r.get("assessment") == "well_below_market"),
        "below_market": sum(1 for r in benchmarkable if r.get("assessment") == "below_market"),
        "at_market": sum(1 for r in benchmarkable if r.get("assessment") == "at_market"),
        "above_market": len(above_market),
    }

    coverage_pct = round((len(benchmarkable) / len(item_results)) * 100, 1) if item_results else 0

    summary = {
        "org_name": org.name,
        "industry": org.industry or "Not specified",
        "size_band": org.size_band or "Unknown",
        "revenue_band": org.revenue_band or "Unknown",
        "total_items": len(item_results),
        "benchmarkable_items": len(benchmarkable),
        "insufficient_data_items": len(insufficient),
        "coverage_pct": coverage_pct,
        "total_annual_spend": round(total_spend, 2),
        "spend_at_or_below_market": assessment_breakdown["well_below_market"] + assessment_breakdown["below_market"] + assessment_breakdown["at_market"],
        "spend_above_market": len(above_market),
        "total_potential_savings": round(total_savings, 2),
        "assessment_breakdown": assessment_breakdown,
        "generated_at": str(datetime.now()),
    }

    return {"items": item_results, "summary": summary}


def feasibility_check(upload_id: str, db: Session) -> dict:
    """
    Quick check: how many of this upload's line items have sufficient peer data?
    Returns coverage info without generating full comparison.
    """
    report = db.query(Report).filter(Report.id == upload_id).first()
    if not report:
        return {"error": "Upload not found"}

    org = db.query(Organization).filter(Organization.id == report.org_id).first()
    if not org:
        return {"error": "Organization not found"}

    if not org.size_band:
        org.compute_bands()
        db.commit()

    user_items = db.query(ContractLineItem).filter(
        ContractLineItem.upload_id == upload_id
    ).all()

    if not user_items:
        return {
            "total_items": 0,
            "benchmarkable_items": 0,
            "coverage_pct": 0,
            "recommendation": "no_data",
            "details": [],
        }

    details = []
    benchmarkable = 0
    for item in user_items:
        # Check broad tier (most relaxed) for quick feasibility
        all_peers = _get_peer_costs(db, item.vendor_name, item.product_name, org.id)
        has_data = len(all_peers) >= MINIMUM_PEERS
        if has_data:
            benchmarkable += 1
        details.append({
            "vendor_name": item.vendor_name,
            "product_name": item.product_name,
            "peer_count": len(all_peers),
            "has_sufficient_peers": has_data,
        })

    coverage_pct = round((benchmarkable / len(user_items)) * 100, 1) if user_items else 0

    if coverage_pct >= 50:
        recommendation = "proceed"
    elif coverage_pct > 0:
        recommendation = "partial"
    else:
        recommendation = "insufficient_data"

    return {
        "total_items": len(user_items),
        "benchmarkable_items": benchmarkable,
        "coverage_pct": coverage_pct,
        "recommendation": recommendation,
        "details": details,
    }


def refresh_coverage_stats(db: Session):
    """
    Refresh the data_coverage_stats table with current aggregates.
    Called periodically or after new data is ingested.
    """
    from models import DataCoverageStats

    # Clear existing stats
    db.query(DataCoverageStats).delete()

    # Aggregate by vendor + product
    from sqlalchemy import distinct
    combos = db.query(
        ContractLineItem.vendor_name,
        ContractLineItem.product_name,
    ).distinct().all()

    for vendor_name, product_name in combos:
        costs = db.query(ContractLineItem.cost_per_unit_annual).filter(
            ContractLineItem.vendor_name == vendor_name,
            ContractLineItem.product_name == product_name,
            ContractLineItem.cost_per_unit_annual > 0,
        ).all()
        cost_list = sorted([c[0] for c in costs])

        org_count = db.query(func.count(func.distinct(ContractLineItem.org_id))).filter(
            ContractLineItem.vendor_name == vendor_name,
            ContractLineItem.product_name == product_name,
        ).scalar() or 0

        stat = DataCoverageStats(
            vendor_name=vendor_name,
            product_name=product_name,
            org_count=org_count,
            line_item_count=len(cost_list),
            p25_cost=round(_percentile(cost_list, 25), 2) if cost_list else None,
            median_cost=round(_percentile(cost_list, 50), 2) if cost_list else None,
            p75_cost=round(_percentile(cost_list, 75), 2) if cost_list else None,
            last_updated=datetime.now(),
        )
        db.add(stat)

    db.commit()
