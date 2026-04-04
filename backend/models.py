from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base



class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    domain = Column(String)
    revenue = Column(Float)  # annual revenue in USD
    size = Column(Integer)  # number of employees
    created_at = Column(DateTime, default=datetime.utcnow)

    users = relationship("User", back_populates="organization")
    reports = relationship("Report", back_populates="organization")


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
    __tablename__ = "reports"

    id = Column(String, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"))
    owner_id = Column(Integer, ForeignKey("users.id"))
    filename = Column(String)
    file_path = Column(String)
    status = Column(String, default="uploaded")  # uploaded, processing, completed
    category = Column(String)  # AWS, Microsoft, Google, Salesforce, Pega, SAP
    created_at = Column(DateTime, default=datetime.utcnow)
    comparison_result = Column(Text)  # JSON summary/analysis
    payment_status = Column(String, default="pending")  # pending, completed

    organization = relationship("Organization", back_populates="reports")
    owner = relationship("User", back_populates="reports")
    benchmark = relationship("BenchmarkReport", back_populates="report", uselist=False)


class BenchmarkReport(Base):
    __tablename__ = "benchmark_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String, ForeignKey("reports.id"), unique=True, index=True)
    result = Column(Text)       # JSON: {report: str, peer_count: int, generated_at: str}
    peer_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    report = relationship("Report", back_populates="benchmark")


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
