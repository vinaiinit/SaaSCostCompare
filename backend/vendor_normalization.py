"""
Vendor and product name normalization.
Maps raw input (messy CSV values, PDF-extracted text) to canonical names.

Pipeline: Clean → Alias lookup → Fuzzy match → (optional AI fallback for PDFs)
"""
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
    {"vendor": "AWS", "canonical_name": "EC2", "aliases": ["elastic compute cloud", "ec2", "ec2 instances", "amazon ec2"]},
    {"vendor": "AWS", "canonical_name": "S3", "aliases": ["simple storage service", "s3", "s3 storage", "amazon s3"]},
    {"vendor": "AWS", "canonical_name": "RDS", "aliases": ["relational database service", "rds", "amazon rds"]},
    {"vendor": "AWS", "canonical_name": "Lambda", "aliases": ["lambda", "aws lambda"]},
    {"vendor": "AWS", "canonical_name": "CloudFront", "aliases": ["cloudfront", "cloud front", "cdn"]},
    {"vendor": "Salesforce", "canonical_name": "Sales Cloud", "aliases": ["sales cloud", "salesforce sales", "sfdc sales"]},
    {"vendor": "Salesforce", "canonical_name": "Service Cloud", "aliases": ["service cloud", "salesforce service"]},
    {"vendor": "Salesforce", "canonical_name": "Marketing Cloud", "aliases": ["marketing cloud", "sfdc marketing"]},
    {"vendor": "Microsoft", "canonical_name": "M365 E3", "aliases": ["microsoft 365 e3", "office 365 e3", "m365 e3", "o365 e3"]},
    {"vendor": "Microsoft", "canonical_name": "M365 E5", "aliases": ["microsoft 365 e5", "office 365 e5", "m365 e5", "o365 e5"]},
    {"vendor": "Microsoft", "canonical_name": "Azure", "aliases": ["azure", "microsoft azure", "azure cloud"]},
    {"vendor": "Microsoft", "canonical_name": "Teams", "aliases": ["teams", "microsoft teams", "ms teams"]},
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


# ── Main normalization function ──────────────────────────────────────────────

def normalize_line_item(raw_vendor: str, raw_product: str, db: Session) -> tuple[str, str]:
    """
    Normalize vendor and product names through the pipeline:
    Clean → Alias lookup → Fuzzy match → fallback to cleaned input.

    Returns (canonical_vendor_name, canonical_product_name).
    """
    cleaned_vendor = clean_name(raw_vendor)
    cleaned_product = clean_name(raw_product)

    # Vendor normalization
    vendor = alias_lookup_vendor(cleaned_vendor, db)
    if not vendor:
        vendor = fuzzy_match_vendor(cleaned_vendor, db)
    if not vendor:
        # Use title-case cleaned name as-is
        vendor = raw_vendor.strip().title() if raw_vendor.strip() else "Unknown"

    # Product normalization
    product = alias_lookup_product(cleaned_product, vendor, db)
    if not product:
        product = fuzzy_match_product(cleaned_product, vendor, db)
    if not product:
        # Use original product name as-is (title case)
        product = raw_product.strip().title() if raw_product.strip() else "Unknown"

    return vendor, product


# ── Seed the catalog tables ──────────────────────────────────────────────────

def seed_vendor_catalog(db: Session):
    """Insert seed vendors and products if catalog is empty."""
    existing = db.query(VendorCatalog).count()
    if existing > 0:
        return  # already seeded

    for v in VENDOR_SEED:
        vendor = VendorCatalog(
            canonical_name=v["canonical_name"],
            aliases=v["aliases"],
            category=v["category"],
        )
        db.add(vendor)
    db.flush()

    for p in PRODUCT_SEED:
        vendor = db.query(VendorCatalog).filter(
            VendorCatalog.canonical_name == p["vendor"]
        ).first()
        if vendor:
            product = ProductCatalog(
                vendor_id=vendor.id,
                canonical_name=p["canonical_name"],
                aliases=p["aliases"],
            )
            db.add(product)

    db.commit()
