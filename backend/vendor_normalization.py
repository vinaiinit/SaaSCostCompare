from __future__ import annotations

"""
Vendor and product name normalization.
Maps raw input (messy CSV values, PDF-extracted text) to canonical names.

Pipeline: Clean → Alias lookup → Fuzzy match → (optional AI fallback for PDFs)
"""
import re
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from models import VendorCatalog, ProductCatalog


# ── Seed data (loaded into DB on first run) ─────────────────────────────────

VENDOR_SEED = [
    {"canonical_name": "AWS", "aliases": ["amazon web services", "aws", "amazon aws", "amazon.com services"], "category": "Cloud"},
    {"canonical_name": "Microsoft", "aliases": ["microsoft", "msft", "microsoft corporation", "microsoft 365", "ms", "azure"], "category": "Productivity"},
    {"canonical_name": "Google", "aliases": ["google", "google cloud", "gcp", "google workspace", "alphabet", "google llc"], "category": "Cloud"},
    {"canonical_name": "Salesforce", "aliases": ["salesforce", "sfdc", "salesforce.com", "salesforce inc"], "category": "CRM"},
    {"canonical_name": "SAP", "aliases": ["sap", "sap se", "sap america", "sap ag"], "category": "ERP"},
    {"canonical_name": "Pega", "aliases": ["pega", "pegasystems", "pega systems", "pegasystems inc"], "category": "BPM"},
    {"canonical_name": "Oracle", "aliases": ["oracle", "oracle corporation", "oracle america"], "category": "ERP"},
    {"canonical_name": "Datadog", "aliases": ["datadog", "data dog", "datadog inc"], "category": "Observability"},
    {"canonical_name": "Snowflake", "aliases": ["snowflake", "snowflake computing", "snowflake inc"], "category": "Data"},
    {"canonical_name": "Slack", "aliases": ["slack", "slack technologies"], "category": "Collaboration"},
    {"canonical_name": "Zoom", "aliases": ["zoom", "zoom video", "zoom communications", "zoom video communications"], "category": "Collaboration"},
    {"canonical_name": "Atlassian", "aliases": ["atlassian", "atlassian corporation", "atlassian pty"], "category": "Dev Tools"},
    {"canonical_name": "ServiceNow", "aliases": ["servicenow", "service now", "service-now", "servicenow inc"], "category": "ITSM"},
    {"canonical_name": "Workday", "aliases": ["workday", "workday inc"], "category": "HR"},
    {"canonical_name": "Adobe", "aliases": ["adobe", "adobe systems", "adobe inc"], "category": "Creative"},
    {"canonical_name": "Cisco", "aliases": ["cisco", "cisco systems", "cisco webex"], "category": "Networking"},
    {"canonical_name": "IBM", "aliases": ["ibm", "international business machines", "ibm corporation"], "category": "Enterprise"},
    {"canonical_name": "Okta", "aliases": ["okta", "okta inc"], "category": "Security"},
    {"canonical_name": "Twilio", "aliases": ["twilio", "twilio inc"], "category": "Communications"},
    {"canonical_name": "HubSpot", "aliases": ["hubspot", "hub spot", "hubspot inc"], "category": "Marketing"},
    {"canonical_name": "Zendesk", "aliases": ["zendesk", "zendesk inc"], "category": "Support"},
    {"canonical_name": "Splunk", "aliases": ["splunk", "splunk inc"], "category": "Observability"},
    {"canonical_name": "GitHub", "aliases": ["github", "github inc"], "category": "Dev Tools"},
    {"canonical_name": "DocuSign", "aliases": ["docusign", "docu sign", "docusign inc"], "category": "Productivity"},
    {"canonical_name": "Crowdstrike", "aliases": ["crowdstrike", "crowd strike", "crowdstrike inc"], "category": "Security"},
]

PRODUCT_SEED = [
    # ── AWS ──
    {"vendor": "AWS", "canonical_name": "EC2", "aliases": ["elastic compute cloud", "ec2", "ec2 instances", "amazon ec2"]},
    {"vendor": "AWS", "canonical_name": "S3", "aliases": ["simple storage service", "s3", "s3 storage", "amazon s3"]},
    {"vendor": "AWS", "canonical_name": "RDS", "aliases": ["relational database service", "rds", "amazon rds"]},
    {"vendor": "AWS", "canonical_name": "Lambda", "aliases": ["lambda", "aws lambda"]},
    {"vendor": "AWS", "canonical_name": "CloudFront", "aliases": ["cloudfront", "cloud front", "cdn"]},
    # ── Salesforce — Core CRM Licenses ──
    {"vendor": "Salesforce", "canonical_name": "Sales & Service Cloud - Unlimited", "aliases": [
        "sales & service cloud - unlimited edition",
        "sales & service cloud - unlimited edit",
        "sales & service cloud - unlimited edition (service)",
        "sales & service cloud - unlimited",
        "sales and service cloud - unlimited edition",
        "sales and service cloud unlimited",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Sales & Service Cloud - Enterprise", "aliases": [
        "sales & service cloud - enterprise edition",
        "sales & service cloud - enterprise",
        "sales and service cloud - enterprise edition",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Sales Cloud", "aliases": [
        "sales cloud", "salesforce sales", "sfdc sales",
        "sales cloud - enterprise edition", "sales cloud - unlimited edition",
        "sales cloud - professional edition",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Service Cloud", "aliases": [
        "service cloud", "salesforce service",
        "service cloud - enterprise edition", "service cloud - unlimited edition",
        "service cloud - professional edition",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Financial Services Cloud", "aliases": [
        "financial services cloud - sales & service - unlimited edition",
        "financial services cloud - service - einstein 1 edition",
        "financial services cloud - service - agentforce 1 edition",
        "financial services cloud - client segmentation",
        "financial services cloud - managed package",
        "fsc - service - data services provisioning - einstein 1 edition",
    ]},
    # ── Salesforce — Platform & Add-ons ──
    {"vendor": "Salesforce", "canonical_name": "Salesforce Shield", "aliases": [
        "salesforce shield", "shield",
        "salesforce shield - fee",
        "salesforce shield - fee financial services cloud - sales & service - unlimited edition (new license)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Salesforce Data Mask", "aliases": [
        "salesforce data mask", "data mask",
        "salesforce data mask - fee",
        "salesforce data mask - fee financial services cloud - sales & service - unlimited edition (new license)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Salesforce Maps", "aliases": [
        "salesforce maps", "salesforce maps - unlimited edition",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Salesforce Connect", "aliases": ["salesforce connect"]},
    {"vendor": "Salesforce", "canonical_name": "Salesforce Backup & Recover", "aliases": [
        "salesforce backup & recover (1 gb)", "salesforce backup & recover",
        "backup & recover blockchain verify add-on",
        "byok for recover and archive",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Salesforce Inbox", "aliases": ["salesforce inbox"]},
    {"vendor": "Salesforce", "canonical_name": "Salesforce Accelerate", "aliases": ["salesforce accelerate"]},
    {"vendor": "Salesforce", "canonical_name": "Encryption At Rest", "aliases": [
        "encryption at rest - shared database", "encryption at rest",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Audit Trail", "aliases": ["audit trail", "field audit trail"]},
    {"vendor": "Salesforce", "canonical_name": "Sandbox - Full Copy", "aliases": [
        "sandbox (full copy)", "sandbox - full copy",
        "sandbox (full copy) - fee financial services cloud - sales & service - unlimited edition (new license)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Sandbox - Developer Pro", "aliases": [
        "sandbox (developer pro)", "sandbox - developer pro",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Data Storage", "aliases": [
        "data storage (10gb)", "data storage (gb)", "data storage",
    ]},
    {"vendor": "Salesforce", "canonical_name": "File Storage", "aliases": [
        "file storage (1tb)", "file storage",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Data Cloud", "aliases": [
        "data cloud provisioning", "data cloud provisioning - agentforce 1 edition",
        "data services provisioning - agentforce 1 edition",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Data Services Credits", "aliases": [
        "data services credits", "flex credits",
    ]},
    {"vendor": "Salesforce", "canonical_name": "CRM Analytics", "aliases": [
        "crm analytics growth", "crm analytics", "crm analytics plus",
        "customer experience intelligence signals",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Einstein", "aliases": [
        "einstein requests", "einstein analytics",
    ]},
    {"vendor": "Salesforce", "canonical_name": "High Volume Platform Events", "aliases": [
        "high volume platform events", "platform events",
    ]},
    # ── Salesforce — Marketing Cloud ──
    {"vendor": "Salesforce", "canonical_name": "Marketing Cloud Engagement", "aliases": [
        "marketing cloud", "sfdc marketing",
        "marketing cloud engagement - enterprise edition",
        "marketing cloud engagement",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Marketing Cloud Advertising", "aliases": [
        "marketing cloud advertising professional",
        "marketing cloud advertising professional - contacts (1,000)",
        "marketing cloud advertising",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Email Messaging", "aliases": [
        "email attachments", "email file attachments (1,000)",
        "super messages - excluding sms/mms",
    ]},
    {"vendor": "Salesforce", "canonical_name": "SMS/MMS Messaging", "aliases": [
        "sms/mms mobile messages", "sms/mms mobile messages (1,000)",
        "private sms/mms code lease - (ar, be, jp, my, se, sg, uae, uk, us vanity)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Private Domain / Dedicated IP", "aliases": [
        "private domain", "private ip / dedicated ip", "ssl certificate",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Intelligence Reports", "aliases": [
        "intelligence reports for engagement advanced",
    ]},
    # ── Salesforce — Slack ──
    {"vendor": "Salesforce", "canonical_name": "Slack Enterprise Grid", "aliases": [
        "slack enterprise grid", "grid active users", "enterprise+ active users",
        "slack provisioning - agentforce 1 edition",
        "slack provisioning for service - einstein 1 edition",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Slack Enterprise Key Management", "aliases": [
        "slack enterprise key management",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Slack AI", "aliases": [
        "slack ai for enterprise grid workspaces", "slack ai",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Slack Grid Team Management", "aliases": [
        "slack grid team management",
    ]},
    # ── Salesforce — Tableau ──
    {"vendor": "Salesforce", "canonical_name": "Tableau Cloud - Creator", "aliases": [
        "tableau cloud - enterprise creator", "tableau cloud - creator",
        "tableau creator",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Tableau Cloud - Explorer", "aliases": [
        "tableau cloud - enterprise explorer", "tableau cloud - explorer",
        "tableau explorer",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Tableau Cloud - Viewer", "aliases": [
        "tableau cloud - enterprise viewer", "tableau cloud - viewer",
        "tableau viewer",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Tableau Cloud - Additional Site", "aliases": [
        "tableau cloud - additional site",
    ]},
    # ── Salesforce — Support Plans ──
    {"vendor": "Salesforce", "canonical_name": "Premier Success Plan", "aliases": [
        "premier success plan - marketing cloud engagement",
        "premier support - backup & recover, discover, accelerate",
        "tableau - premier success plan",
        "premier success plan",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Signature Success Plan", "aliases": [
        "signature success - marketing cloud engagement",
        "signature success plan",
    ]},
    {"vendor": "Salesforce", "canonical_name": "Slack Premium Support", "aliases": [
        "slack premium support",
    ]},
    # ── Salesforce — Professional Services (by role & location) ──
    {"vendor": "Salesforce", "canonical_name": "PS - Developer (Offshore)", "aliases": [
        "developer (offshore)", "developer (india)", "developer (off-shore)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - Senior Developer (Offshore)", "aliases": [
        "senior developer (offshore)", "senior developer (india)", "senior developer (off-shore)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - Developer (Onshore)", "aliases": [
        "developer (us)", "developer (onshore)", "developer (on-shore)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - Senior Developer (Onshore)", "aliases": [
        "senior developer (us)", "senior developer (onshore)", "senior developer (on-shore)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - Technical Architect (Offshore)", "aliases": [
        "technical architect (offshore)", "technical architect (india)", "technical architect (off-shore)",
        "technical architect - offshore lead (offshore)",
        "technical architect - release architect (offshore)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - Technical Architect (Onshore)", "aliases": [
        "technical architect (us)", "technical architect (onshore)", "technical architect (on-shore)",
        "senior technical architect (us)",
        "salesforce cto - principal technical architect (on-shore)",
        "senior technical architect (phase 1 - core team & program management)",
        "senior technical architect / senior integration architect (phase 1 - core team & program management)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - Project Manager (Offshore)", "aliases": [
        "project manager (offshore)", "project manager (india)", "project manager (off-shore)",
        "project manager - scrum master (offshore)",
        "associate project manager - controller (offshore)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - Project Manager (Onshore)", "aliases": [
        "project manager (us)", "project manager (onshore)", "project manager (on-shore)",
        "project manager - build pm (onshore)",
        "senior project manager (us)",
        "senior program manager (us)",
        "senior program manager (phase 1 - core team & program management)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - QA Consultant (Offshore)", "aliases": [
        "quality assurance consultant (offshore)", "quality assurance consultant (india)",
        "quality assurance consultant (off-shore)",
        "quality assurance lead (offshore)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - QA Consultant (Onshore)", "aliases": [
        "quality assurance consultant (us)", "quality assurance consultant (onshore)",
        "quality assurance lead (us)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - Solution Consultant (Onshore)", "aliases": [
        "solution consultant (us)", "solution consultant (onshore)", "solution consultant (on-shore)",
        "senior solution architect (us)",
        "senior solution architect (phase 1 - core team & program management)",
        "business strategy consultant (phase 1 - core team & program management)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - Experience Designer (Onshore)", "aliases": [
        "experience designer (onshore)", "experience designer (on-shore)",
        "experience architect (us)",
        "experience architect (phase 1 - core team & program management)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - Engagement Manager", "aliases": [
        "engagement manager (us)", "engagement manager (onshore)",
        "engagement manager (phase 1 - core team & program management)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - Change Consultant (Onshore)", "aliases": [
        "human centered change consultant - training lead (onshore)",
        "senior human centered change consultant (us)",
        "senior human centered change consultant (phase 1 - core team & program management)",
    ]},
    {"vendor": "Salesforce", "canonical_name": "PS - Technical Consultant (Onshore)", "aliases": [
        "technical consultant (us)", "technical consultant (onshore)",
    ]},
    # ── Microsoft ──
    {"vendor": "Microsoft", "canonical_name": "M365 E3", "aliases": ["microsoft 365 e3", "office 365 e3", "m365 e3", "o365 e3"]},
    {"vendor": "Microsoft", "canonical_name": "M365 E5", "aliases": ["microsoft 365 e5", "office 365 e5", "m365 e5", "o365 e5"]},
    {"vendor": "Microsoft", "canonical_name": "Azure", "aliases": ["azure", "microsoft azure", "azure cloud"]},
    {"vendor": "Microsoft", "canonical_name": "Teams", "aliases": ["teams", "microsoft teams", "ms teams"]},
    # ── Google ──
    {"vendor": "Google", "canonical_name": "Workspace", "aliases": ["workspace", "google workspace", "gsuite", "g suite"]},
    {"vendor": "Google", "canonical_name": "GCP Compute", "aliases": ["compute engine", "gcp compute", "gce"]},
]


# ── Step 1: Clean raw name ──────────────────────────────────────────────────

SUFFIXES_TO_STRIP = [
    ", incorporated", " incorporated",
    ", inc.", " inc.", ", inc", " inc",
    ", ltd.", " ltd.", ", ltd", " ltd",
    ", llc", " llc",
    ", corp.", " corp.", ", corp", " corp",
    " corporation", " limited", " pty",
    " co.", " company",
]


def clean_name(raw: str) -> str:
    """Lowercase, strip whitespace and common company suffixes."""
    name = raw.strip().lower()
    for suffix in SUFFIXES_TO_STRIP:
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
    return name


# ── Step 2: Alias lookup ────────────────────────────────────────────────────

def alias_lookup_vendor(cleaned: str, db: Session) -> str | None:
    """Check vendor_catalog aliases for exact match."""
    vendors = db.query(VendorCatalog).all()
    for v in vendors:
        if cleaned == v.canonical_name.lower():
            return v.canonical_name
        for alias in (v.aliases or []):
            if cleaned == alias.lower():
                return v.canonical_name
    return None


def alias_lookup_product(cleaned: str, vendor_canonical: str, db: Session) -> str | None:
    """Check product_catalog aliases for exact match within a vendor."""
    vendor = db.query(VendorCatalog).filter(
        VendorCatalog.canonical_name == vendor_canonical
    ).first()
    if not vendor:
        return None
    products = db.query(ProductCatalog).filter(
        ProductCatalog.vendor_id == vendor.id
    ).all()
    for p in products:
        if cleaned == p.canonical_name.lower():
            return p.canonical_name
        for alias in (p.aliases or []):
            if cleaned == alias.lower():
                return p.canonical_name
    return None


# ── Step 3: Fuzzy match ─────────────────────────────────────────────────────

def fuzzy_match_vendor(cleaned: str, db: Session, threshold: float = 0.85) -> str | None:
    """Fuzzy match against all vendor aliases using SequenceMatcher."""
    best_match = None
    best_score = 0.0
    for v in db.query(VendorCatalog).all():
        candidates = [v.canonical_name.lower()] + [a.lower() for a in (v.aliases or [])]
        for candidate in candidates:
            score = SequenceMatcher(None, cleaned, candidate).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = v.canonical_name
    return best_match


def fuzzy_match_product(cleaned: str, vendor_canonical: str, db: Session, threshold: float = 0.85) -> str | None:
    """Fuzzy match against product aliases for a specific vendor."""
    vendor = db.query(VendorCatalog).filter(
        VendorCatalog.canonical_name == vendor_canonical
    ).first()
    if not vendor:
        return None
    best_match = None
    best_score = 0.0
    for p in db.query(ProductCatalog).filter(ProductCatalog.vendor_id == vendor.id).all():
        candidates = [p.canonical_name.lower()] + [a.lower() for a in (p.aliases or [])]
        for candidate in candidates:
            score = SequenceMatcher(None, cleaned, candidate).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = p.canonical_name
    return best_match


# ── Step 4: Pre-clean product names ────────────────────────────────────────

_PS_PREFIX_RE = re.compile(
    r'^(?:phase \d+ - .+ stream - )|^(?:professional services - (?:.*?\(phase[^)]+\) - )?)',
    re.IGNORECASE,
)


def _strip_ps_prefix(cleaned: str) -> str:
    """Strip project/stream prefixes from professional services product names."""
    return _PS_PREFIX_RE.sub('', cleaned).strip()


# ── Main normalization function ──────────────────────────────────────────────

def normalize_line_item(raw_vendor: str, raw_product: str, db: Session) -> tuple[str, str]:
    """
    Normalize vendor and product names through the pipeline:
    Pre-clean → Clean → Alias lookup → Fuzzy match → fallback to cleaned input.

    Returns (canonical_vendor_name, canonical_product_name).
    """
    cleaned_vendor = clean_name(raw_vendor)
    cleaned_product = clean_name(raw_product)

    # Vendor normalization
    vendor = alias_lookup_vendor(cleaned_vendor, db)
    if not vendor:
        vendor = fuzzy_match_vendor(cleaned_vendor, db)
    if not vendor:
        vendor = raw_vendor.strip().title() if raw_vendor.strip() else "Unknown"

    # Product normalization — try raw first, then with prefix stripped
    product = alias_lookup_product(cleaned_product, vendor, db)
    if not product:
        stripped = _strip_ps_prefix(cleaned_product)
        if stripped != cleaned_product:
            product = alias_lookup_product(stripped, vendor, db)
    if not product:
        product = fuzzy_match_product(cleaned_product, vendor, db)
    if not product:
        stripped = _strip_ps_prefix(cleaned_product)
        if stripped != cleaned_product:
            product = fuzzy_match_product(stripped, vendor, db)
    if not product:
        product = raw_product.strip().title() if raw_product.strip() else "Unknown"

    return vendor, product


# ── Seed the catalog tables ──────────────────────────────────────────────────

def seed_vendor_catalog(db: Session):
    """Insert or update seed vendors and products."""
    for v in VENDOR_SEED:
        existing = db.query(VendorCatalog).filter(
            VendorCatalog.canonical_name == v["canonical_name"]
        ).first()
        if not existing:
            db.add(VendorCatalog(
                canonical_name=v["canonical_name"],
                aliases=v["aliases"],
                category=v["category"],
            ))
        else:
            existing.aliases = v["aliases"]
            existing.category = v["category"]
    db.flush()

    for p in PRODUCT_SEED:
        vendor = db.query(VendorCatalog).filter(
            VendorCatalog.canonical_name == p["vendor"]
        ).first()
        if not vendor:
            continue
        existing = db.query(ProductCatalog).filter(
            ProductCatalog.vendor_id == vendor.id,
            ProductCatalog.canonical_name == p["canonical_name"],
        ).first()
        if not existing:
            db.add(ProductCatalog(
                vendor_id=vendor.id,
                canonical_name=p["canonical_name"],
                aliases=p["aliases"],
            ))
        else:
            existing.aliases = p["aliases"]

    db.commit()
