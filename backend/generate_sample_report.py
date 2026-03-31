"""Run this once to generate a sample output PDF: python generate_sample_report.py"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv
load_dotenv()

from pdf_report import generate_pdf_report

report_meta = {
    "filename": "microsoft_spend_2024.csv",
    "category": "Microsoft",
    "created_at": "2024-11-01",
}

org_profile = {
    "name": "Acme Corporation",
    "domain": "acmecorp.com",
    "revenue": 85_000_000,
    "size": 420,
}

benchmark_result = {
    "total_spend": 1_243_800,
    "spend_per_employee": 2_961,
    "spend_pct_revenue": 1.46,
    "peer_count": 4,
    "generated_at": "2024-11-15T09:30:00",
    "report": """## Executive Summary
Acme Corporation spends $1,243,800 annually on Microsoft SaaS products, equating to $2,961 per employee and 1.46% of revenue. Compared to peer organisations of similar size and revenue, Acme is an **above-average spender** — sitting at the 72nd percentile for Microsoft spend per employee. Key drivers are an over-provisioned Microsoft 365 E5 tier and a Dynamics 365 deployment with low user adoption.

## Spend Benchmarks
| Metric | Acme Corporation | Peer Benchmark | Assessment |
|--------|-----------------|----------------|------------|
| SaaS spend per employee | $2,961 | $1,800 – $2,400 | Above benchmark |
| SaaS as % of revenue | 1.46% | 0.8% – 1.2% | Above benchmark |
| Total Microsoft SKUs | 9 | 5 – 7 | Above benchmark |
| M365 cost per seat | $57.00 | $36 – $42 | Overpaying |
| Dynamics 365 adoption | 38% | 75%+ | Under-utilised |

## Category Breakdown & Benchmarks
**Productivity (Microsoft 365)** — $604,800 (48.6% of total)
Acme is on M365 E5 at $57/user/month for all 420 seats. Peer benchmark for organisations of this size is $36–$42/user/month (E3 tier). Potential downgrade saving: $63,000–$88,200/year.
Assessment: **Over-spending**

**Business Applications (Dynamics 365)** — $378,000 (30.4% of total)
150 Dynamics 365 Sales Enterprise licences at $210/user/month. Active usage data shows only 57 users log in weekly. 93 licences appear unused.
Assessment: **Significantly over-provisioned**

**Cloud & DevOps (Azure DevOps + GitHub)** — $156,000 (12.5% of total)
300 Azure DevOps Basic licences and 120 GitHub Enterprise seats. Peer benchmark for a 420-person org is $90K–$120K/year.
Assessment: **Slightly above benchmark**

**Security Add-ons (Defender, Purview)** — $105,000 (8.4% of total)
Microsoft Defender for Endpoint P2 and Purview Information Protection. Pricing is within benchmark range.
Assessment: **On target**

## Tool-Level Analysis
| SKU | Annual Spend | Seats | Unit Price | Benchmark Price | Flag |
|-----|-------------|-------|------------|-----------------|------|
| M365 E5 | $287,280 | 420 | $57.00/mo | $36–$42/mo | Overpaying — consider E3 |
| Dynamics 365 Sales Ent. | $378,000 | 150 | $210.00/mo | $95/mo (Sales Pro) | Over-tier + unused seats |
| Azure DevOps Basic | $72,000 | 300 | $20.00/mo | $6/mo | Review seat count |
| GitHub Enterprise | $84,000 | 120 | $58.33/mo | $19/mo | Overlap with Azure DevOps |
| Power BI Premium | $60,000 | 100 | $50.00/mo | $20/mo (Pro) | Consider Pro tier |

## Percentile Ranking
**72nd percentile** — Acme spends more on Microsoft SaaS per employee than 72% of comparable organisations ($75M–$100M revenue, 350–500 employees). The primary drivers are the E5 tier selection and Dynamics 365 over-provisioning. Organisations at the 50th percentile spend approximately $2,100/employee on Microsoft products.

## Key Findings
1. **M365 E5 over-triage**: All 420 seats are on E5 ($57/mo) when E3 ($36/mo) covers the feature requirements of approximately 85% of users. Estimated over-spend: $88,200/year.
2. **93 unused Dynamics 365 licences**: At $210/seat/month, inactive licences cost $234,360/year. Usage data confirms only 57 of 150 licences are actively used weekly.
3. **Azure DevOps + GitHub overlap**: Both tools provide source control and CI/CD pipelines. Consolidating to one platform could save $40,000–$55,000/year.
4. **Power BI Premium over-tier**: 100 users on Premium Per User ($50/mo) when Power BI Pro ($20/mo) meets the reporting requirements for 80+ of these users.
5. **Microsoft EA renewal in 87 days**: Current agreement expires 31 January 2025. Without benchmark data, Microsoft's proposed renewal will likely reflect current (above-market) pricing.

## Prioritized Recommendations
1. **Reduce Dynamics 365 to 60 licences** — Remove 90 unused seats before EA renewal. Estimated saving: $226,800/year.
2. **Downgrade M365 from E5 to E3 for 360 standard users** — Retain E5 for 60 power users (IT, Legal, Exec). Estimated saving: $84,672/year.
3. **Consolidate Azure DevOps and GitHub** — Standardise on GitHub Enterprise and remove Azure DevOps Basic licences. Estimated saving: $45,600/year.
4. **Downgrade Power BI to Pro for 80 users** — Retain Premium for 20 heavy users. Estimated saving: $28,800/year.
5. **Use benchmark data in EA renewal negotiation** — Present this report to Microsoft at renewal. Peer pricing data shows 18–22% discount is achievable on E3 volume pricing at this seat count.

**Total estimated annual saving: $385,872 – $485,872**
""",
}

analysis_text = """
Total SaaS Spend: $1,243,800 across 9 Microsoft SKUs.

Top 5 SKUs by spend:
- Dynamics 365 Sales Enterprise: $378,000 (150 seats × $210/mo × 12)
- Microsoft 365 E5: $287,280 (420 seats × $57/mo × 12)
- GitHub Enterprise: $84,000 (120 seats × $58.33/mo × 12)
- Azure DevOps Basic: $72,000 (300 seats × $20/mo × 12)
- Power BI Premium Per User: $60,000 (100 seats × $50/mo × 12)

Spend per employee: $2,961 — 23% above the peer median of $2,408.

Contracts expiring within 90 days:
- Microsoft Enterprise Agreement: expires 31 January 2025 (87 days). This covers M365, Dynamics 365, and Azure DevOps — representing $898,800 of annual spend. Renewal negotiation should begin immediately.

Key anomaly: Dynamics 365 licence count (150) is disproportionate to active users (57). This is the single largest optimisation opportunity in the portfolio.
"""

out_path = os.path.join(os.path.dirname(__file__), "..", "sample_output_report.pdf")
pdf_bytes = generate_pdf_report(report_meta, org_profile, benchmark_result, analysis_text)
with open(out_path, "wb") as f:
    f.write(pdf_bytes)

print(f"Sample report saved to: {os.path.abspath(out_path)}")
