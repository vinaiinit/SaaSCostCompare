from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean, Date, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    industry = Column(String)  # was "domain" — renamed for clarity
    revenue = Column(Float)  # annual revenue in USD
    size = Column(Integer)  # number of employees
    size_band = Column(String)  # "1-50", "51-200", "201-1000", "1001-5000", "5001+"
    revenue_band = Column(String)  # "under_1m", "1m_10m", "10m_100m", "100m_500m", "500m+"
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="organization")
    reports = relationship("Report", back_populates="organization")
    line_items = relationship("ContractLineItem", back_populates="organization")

    def compute_bands(self):
        """Set size_band and revenue_band from raw values."""
        s = self.size or 0
        if s <= 50:
            self.size_band = "1-50"
        elif s <= 200:
            self.size_band = "51-200"
        elif s <= 1000:
            self.size_band = "201-1000"
        elif s <= 5000:
            self.size_band = "1001-5000"
        else:
            self.size_band = "5001+"

        r = self.revenue or 0
        if r < 1_000_000:
            self.revenue_band = "under_1m"
        elif r < 10_000_000:
            self.revenue_band = "1m_10m"
        elif r < 100_000_000:
            self.revenue_band = "10m_100m"
        elif r < 500_000_000:
            self.revenue_band = "100m_500m"
        else:
            self.revenue_band = "500m+"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    full_name = Column(String)
    org_id = Column(Integer, ForeignKey("organizations.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, default=1)

    organization = relationship("Organization", back_populates="users")
    reports = relationship("Report", back_populates="owner")


class Report(Base):
    """An upload submission. Keeps the 'reports' table name for backward compat."""
    __tablename__ = "reports"

    id = Column(String, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"))
    owner_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String)
    file_path = Column(String)
    status = Column(String, default="uploaded")  # uploaded, extracting, extracted, comparing, completed, failed
    category = Column(String)  # vendor name (was fixed set, now free-text)
    created_at = Column(DateTime, default=datetime.utcnow)
    comparison_result = Column(Text)  # JSON: structured comparison output
    payment_status = Column(String, default="pending")  # pending, completed

    organization = relationship("Organization", back_populates="reports")
    owner = relationship("User", back_populates="reports")
    benchmark = relationship("BenchmarkReport", back_populates="report", uselist=False)
    line_items = relationship("ContractLineItem", back_populates="upload")


class BenchmarkReport(Base):
    """Stores AI-generated narrative of comparison results (presentation only)."""
    __tablename__ = "benchmark_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String, ForeignKey("reports.id"), unique=True, index=True)
    result = Column(Text)       # JSON: {narrative: str, peer_count: int, generated_at: str}
    peer_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="benchmark")


class ContractLineItem(Base):
    """Individual contract line items — the core peer comparison data pool."""
    __tablename__ = "contract_line_items"

    id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(String, ForeignKey("reports.id"), index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), index=True)
    vendor_name = Column(String, index=True)  # canonical (normalized)
    product_name = Column(String, index=True)  # canonical (normalized)
    sku = Column(String, nullable=True)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, default=0.0)
    total_cost = Column(Float, default=0.0)
    billing_frequency = Column(String, default="annual")  # monthly, annual, multi_year
    currency = Column(String, default="USD")
    contract_start_date = Column(Date, nullable=True)
    contract_end_date = Column(Date, nullable=True)
    cost_per_unit_annual = Column(Float, default=0.0)  # normalized annual per-unit cost
    total_cost_annual = Column(Float, default=0.0)  # normalized to annual
    extraction_source = Column(String, default="csv")  # csv, pdf_ai, manual
    extraction_confidence = Column(Float, nullable=True)  # 0.0–1.0, only for pdf_ai
    is_validated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    upload = relationship("Report", back_populates="line_items")
    organization = relationship("Organization", back_populates="line_items")


class VendorCatalog(Base):
    """Reference table for vendor name normalization."""
    __tablename__ = "vendor_catalog"

    id = Column(Integer, primary_key=True, index=True)
    canonical_name = Column(String, unique=True, index=True)
    aliases = Column(JSON, default=list)  # ["amazon web services", "aws"]
    category = Column(String)  # Cloud, CRM, Productivity, ERP, etc.
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("ProductCatalog", back_populates="vendor")


class ProductCatalog(Base):
    """Reference table for product/SKU name normalization."""
    __tablename__ = "product_catalog"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendor_catalog.id"), index=True)
    canonical_name = Column(String, index=True)
    aliases = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    vendor = relationship("VendorCatalog", back_populates="products")


class DataCoverageStats(Base):
    """Cached statistics for feasibility checks and coverage dashboard."""
    __tablename__ = "data_coverage_stats"

    id = Column(Integer, primary_key=True, index=True)
    vendor_name = Column(String, index=True)
    product_name = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    size_band = Column(String, nullable=True)
    org_count = Column(Integer, default=0)
    line_item_count = Column(Integer, default=0)
    p25_cost = Column(Float, nullable=True)
    median_cost = Column(Float, nullable=True)
    p75_cost = Column(Float, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow)


class CampaignSubmission(Base):
    """Anonymous/semi-anonymous uploads during data collection campaigns."""
    __tablename__ = "campaign_submissions"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=True)
    company_name = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    company_size = Column(Integer, nullable=True)
    vendor_name = Column(String)
    file_path = Column(String)
    status = Column(String, default="submitted")  # submitted, processing, extracted, rejected
    line_items_extracted = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    converted_to_org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class ContactInquiry(Base):
    __tablename__ = "contact_inquiries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String)
    company = Column(String)
    message = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
