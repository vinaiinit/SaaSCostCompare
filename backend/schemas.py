from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


# ── Organization ─────────────────────────────────────────────────────────────

class OrgBase(BaseModel):
    name: str
    industry: str  # was "domain"
    revenue: float
    size: int


class OrgCreate(OrgBase):
    pass


class OrgResponse(OrgBase):
    id: int
    size_band: Optional[str] = None
    revenue_band: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ── User ─────────────────────────────────────────────────────────────────────

class UserBase(BaseModel):
    email: str
    full_name: str


class UserCreate(UserBase):
    password: str
    org_id: int


class UserResponse(UserBase):
    id: int
    org_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Auth ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# ── Report (Upload) ─────────────────────────────────────────────────────────

class ReportResponse(BaseModel):
    id: str
    org_id: int
    filename: str
    status: str
    category: Optional[str] = None
    payment_status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ── Contract Line Items ──────────────────────────────────────────────────────

class LineItemResponse(BaseModel):
    id: int
    vendor_name: str
    product_name: str
    sku: Optional[str] = None
    quantity: int
    unit_price: float
    total_cost: float
    billing_frequency: str
    currency: str
    contract_start_date: Optional[date] = None
    contract_end_date: Optional[date] = None
    cost_per_unit_annual: float
    total_cost_annual: float
    extraction_source: str
    extraction_confidence: Optional[float] = None

    class Config:
        from_attributes = True


class LineItemUpdate(BaseModel):
    vendor_name: Optional[str] = None
    product_name: Optional[str] = None
    sku: Optional[str] = None
    quantity: Optional[int] = None
    unit_price: Optional[float] = None
    total_cost: Optional[float] = None
    billing_frequency: Optional[str] = None


# ── Data Coverage ────────────────────────────────────────────────────────────

class DataCoverageResponse(BaseModel):
    vendor_name: str
    product_name: Optional[str] = None
    org_count: int
    line_item_count: int

    class Config:
        from_attributes = True


# ── Campaign Submission ──────────────────────────────────────────────────────

class CampaignSubmitRequest(BaseModel):
    vendor_name: str
    email: Optional[str] = None
    company_name: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[int] = None


# ── Subscription / Payment ──────────────────────────────────────────────────

class CreateCheckoutRequest(BaseModel):
    price_id: str


class CheckoutSessionResponse(BaseModel):
    client_secret: str


class SubscriptionStatusResponse(BaseModel):
    plan: str
    status: str
    reports_used: int
    reports_limit: int
    current_period_end: Optional[datetime] = None
    cancel_at_period_end: bool = False

    class Config:
        from_attributes = True


class PlanInfo(BaseModel):
    id: str
    name: str
    price: int
    reports_limit: int
    features: List[str]
    stripe_price_id: Optional[str] = None
