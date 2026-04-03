from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class OrgBase(BaseModel):
    name: str
    domain: str
    revenue: float
    size: int


class OrgCreate(OrgBase):
    pass


class OrgResponse(OrgBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


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


class ReportResponse(BaseModel):
    id: str
    org_id: int
    filename: str
    status: str
    category: Optional[str]
    payment_status: str
    created_at: datetime

    class Config:
        from_attributes = True
