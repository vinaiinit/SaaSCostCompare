from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status, Request
from typing import List, Optional
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta
import uuid
import os
import json
import re
import threading
from pydantic import BaseModel

from database import engine, get_db, Base
from models import (
    User, Organization, Report, BenchmarkReport, PasswordResetToken,
    ContactInquiry, ContractLineItem, VendorCatalog, DataCoverageStats,
    CampaignSubmission, LicenseAnalysis, AuditLog, Subscription,
)
from auth import hash_password, verify_password, create_access_token, verify_token
from audit import log_event
from schemas import (
    OrgCreate,
    OrgResponse,
    UserCreate,
    UserResponse,
    LoginRequest,
    TokenResponse,
    ReportResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    LineItemResponse,
    LineItemUpdate,
    CampaignSubmitRequest,
    CreateCheckoutRequest,
    CheckoutSessionResponse,
    SubscriptionStatusResponse,
    PlanInfo,
)
from ai_analysis import process_upload, generate_narrative
from comparison_engine import generate_comparison, feasibility_check, refresh_coverage_stats
from s3_storage import is_s3_enabled, upload_directory as s3_upload_directory, download_to_temp
from database import SessionLocal


def _try_enqueue(report_id: str, file_path: str, org_id: int) -> str:
    """Try Redis queue first; fall back to background thread if Redis is unavailable."""
    try:
        from job_queue import enqueue_report_processing
        return enqueue_report_processing(report_id, file_path, org_id)
    except Exception:
        def run():
            db = SessionLocal()
            try:
                process_upload(report_id, file_path, org_id, db)
            finally:
                db.close()
        t = threading.Thread(target=run, daemon=True)
        t.start()
        return f"thread-{report_id}"


# Create tables
Base.metadata.create_all(bind=engine)

# Seed vendor catalog
_seed_db = SessionLocal()
try:
    from vendor_normalization import seed_vendor_catalog
    seed_vendor_catalog(_seed_db)
finally:
    _seed_db.close()

app = FastAPI()

# CORS middleware
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _validate_password(password: str) -> None:
    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not re.search(r"[A-Z]", password):
        errors.append("one uppercase letter")
    if not re.search(r"[a-z]", password):
        errors.append("one lowercase letter")
    if not re.search(r"\d", password):
        errors.append("one digit")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        errors.append("one special character")
    if errors:
        raise HTTPException(
            status_code=400,
            detail=f"Password must contain: {', '.join(errors)}.",
        )


UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".csv", ".pdf", ".zip", ".doc", ".docx"}


def _safe_org_folder(org: Organization) -> str:
    """Build a filesystem/S3-safe folder name for an organization."""
    import re
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "_", (org.name or "unknown")).strip("_")[:50]
    return f"org_{org.id}_{safe_name}"

REQUIRED_CSV_COLUMNS = {
    "vendor", "product_name", "sku", "quantity",
    "unit_price", "total_cost", "billing_frequency", "currency",
}


def validate_csv_columns(content: bytes) -> None:
    """Raise HTTPException if the CSV is missing required columns."""
    import csv, io
    try:
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        headers = {h.strip().lower() for h in (reader.fieldnames or [])}
        missing = REQUIRED_CSV_COLUMNS - headers
        if missing:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"CSV is missing required columns: {', '.join(sorted(missing))}. "
                    "Please use the provided template."
                ),
            )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Could not parse CSV. Please use the provided template.")


# --- Organization endpoints ---
@app.post("/orgs", response_model=OrgResponse)
def create_organization(org: OrgCreate, db: Session = Depends(get_db)):
    db_org = Organization(
        name=org.name,
        industry=org.industry,
        revenue=org.revenue,
        size=org.size,
    )
    db_org.compute_bands()
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    return db_org


@app.get("/orgs/{org_id}", response_model=OrgResponse)
def get_organization(org_id: int, db: Session = Depends(get_db)):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org


# --- User endpoints ---
@app.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, request: Request, db: Session = Depends(get_db)):
    _validate_password(user.password)

    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hash_password(user.password),
        org_id=user.org_id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    free_sub = Subscription(
        user_id=db_user.id,
        org_id=db_user.org_id,
        plan="free",
        status="active",
        reports_limit=0,
    )
    db.add(free_sub)
    db.commit()

    log_event(db, action="user.register", user_id=db_user.id,
              resource_type="user", resource_id=str(db_user.id),
              ip_address=_get_client_ip(request))
    return db_user


@app.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        log_event(db, action="login.failed", detail=f"email={credentials.email}",
                  ip_address=_get_client_ip(request))
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(hours=24)
    )

    log_event(db, action="login.success", user_id=user.id,
              resource_type="user", resource_id=str(user.id),
              ip_address=_get_client_ip(request))
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/me", response_model=UserResponse)
def get_current_user(
    user_id: int = Depends(verify_token), db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# --- Password reset endpoints ---
@app.post("/forgot-password")
@limiter.limit("3/minute")
def forgot_password(request: Request, req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    from email_utils import send_password_reset_email
    import secrets
    from datetime import datetime

    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        return {"message": "If that email exists, a reset link has been sent."}

    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False,
    ).update({"used": True})

    token = secrets.token_urlsafe(48)
    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=1),
    )
    db.add(reset_token)
    db.commit()

    send_password_reset_email(user.email, token)
    return {"message": "If that email exists, a reset link has been sent."}


@app.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    from datetime import datetime

    reset_token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == req.token,
        PasswordResetToken.used == False,
    ).first()

    if not reset_token:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link.")

    if reset_token.expires_at < datetime.utcnow():
        reset_token.used = True
        db.commit()
        raise HTTPException(status_code=400, detail="Reset link has expired. Please request a new one.")

    _validate_password(req.new_password)

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found.")

    user.hashed_password = hash_password(req.new_password)
    reset_token.used = True
    db.commit()

    return {"message": "Password has been reset successfully. You can now sign in."}


# --- Upload endpoint (extraction, not AI analysis) ---
@app.post("/upload")
async def upload_report(
    request: Request,
    files: List[UploadFile] = File(...),
    category: str = Form(...),
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    org = db.query(Organization).filter(Organization.id == user.org_id).first()
    if not org:
        raise HTTPException(status_code=400, detail="Organization not found for user")

    file_id = str(uuid.uuid4())
    org_folder = _safe_org_folder(org)
    report_dir = os.path.join(UPLOAD_DIR, org_folder, file_id)
    os.makedirs(report_dir, exist_ok=True)

    saved_files = []
    filenames = []
    total_size = 0

    for file in files:
        content = await file.read()
        total_size += len(content)
        if total_size > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="Total upload size too large. Maximum is 50MB.")

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {ext}. Allowed: CSV, PDF, ZIP",
            )

        dest = os.path.join(report_dir, file.filename)
        with open(dest, "wb") as buffer:
            buffer.write(content)
        saved_files.append(dest)
        filenames.append(file.filename)

        if ext == ".zip":
            from file_processor import process_zip
            extracted = process_zip(dest, report_dir)
            saved_files.extend(extracted)

    # For single CSV uploads, validate columns
    csv_files = [f for f in saved_files if f.lower().endswith(".csv")]
    if len(saved_files) == 1 and len(csv_files) == 1:
        with open(csv_files[0], "rb") as f:
            validate_csv_columns(f.read())

    display_name = filenames[0] if len(filenames) == 1 else f"{len(filenames)} files ({', '.join(filenames)})"

    # Upload to S3 if configured, otherwise keep local path
    if is_s3_enabled():
        import shutil
        s3_key = f"{org_folder}/{file_id}"
        s3_uri = s3_upload_directory(report_dir, s3_key)
        stored_path = s3_uri
        shutil.rmtree(report_dir, ignore_errors=True)  # clean up local temp
    else:
        stored_path = report_dir

    report = Report(
        id=file_id,
        org_id=user.org_id,
        owner_id=user_id,
        filename=display_name,
        file_path=stored_path,
        status="uploaded",
        category=category,  # vendor name
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Enqueue extraction (not AI analysis)
    job_id = _try_enqueue(file_id, stored_path, user.org_id)

    log_event(db, action="file.upload", user_id=user_id,
              resource_type="report", resource_id=file_id,
              detail=f"files={len(filenames)}, vendor={category}",
              ip_address=_get_client_ip(request))

    return {
        "id": file_id,
        "filename": display_name,
        "status": "uploaded",
        "category": category,
        "job_id": job_id,
        "files_uploaded": len(filenames),
    }


# --- Report / Upload endpoints ---
@app.get("/reports", response_model=list[ReportResponse])
def list_reports(
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    return db.query(Report).filter(Report.owner_id == user_id).order_by(Report.created_at.desc()).all()


@app.get("/reports/{report_id}", response_model=ReportResponse)
def get_report(
    report_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/reports/{report_id}/status")
def get_report_status(
    report_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")

    parsed = json.loads(report.comparison_result) if report.comparison_result else None
    warnings = parsed.get("warnings", []) if parsed else []

    # Count extracted line items
    line_item_count = db.query(ContractLineItem).filter(
        ContractLineItem.upload_id == report_id
    ).count()

    return {
        "id": report.id,
        "status": report.status,
        "category": report.category,
        "payment_status": report.payment_status,
        "line_item_count": line_item_count,
        "extraction_summary": parsed.get("extraction_summary") if parsed else None,
        "warnings": warnings,
    }


# --- Line item endpoints (review/edit extracted data) ---
@app.get("/uploads/{upload_id}/line-items", response_model=list[LineItemResponse])
def get_line_items(
    upload_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == upload_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Upload not found")

    items = db.query(ContractLineItem).filter(
        ContractLineItem.upload_id == upload_id
    ).all()
    return items


@app.put("/uploads/{upload_id}/line-items/{item_id}")
def update_line_item(
    upload_id: str,
    item_id: int,
    update: LineItemUpdate,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == upload_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Upload not found")

    item = db.query(ContractLineItem).filter(
        ContractLineItem.id == item_id,
        ContractLineItem.upload_id == upload_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Line item not found")

    # Apply updates
    if update.vendor_name is not None:
        from vendor_normalization import normalize_line_item
        vendor, _ = normalize_line_item(update.vendor_name, item.product_name, db)
        item.vendor_name = vendor
    if update.product_name is not None:
        from vendor_normalization import normalize_line_item
        _, product = normalize_line_item(item.vendor_name, update.product_name, db)
        item.product_name = product
    if update.sku is not None:
        item.sku = update.sku
    if update.quantity is not None:
        item.quantity = update.quantity
    if update.unit_price is not None:
        item.unit_price = update.unit_price
    if update.total_cost is not None:
        item.total_cost = update.total_cost
    if update.billing_frequency is not None:
        from extraction import _normalize_billing_frequency
        item.billing_frequency = _normalize_billing_frequency(update.billing_frequency)

    # Recompute annual costs
    from extraction import compute_annual_costs
    item.cost_per_unit_annual, item.total_cost_annual = compute_annual_costs(
        item.unit_price, item.total_cost, item.billing_frequency,
        item.contract_start_date, item.contract_end_date,
    )
    item.extraction_source = "manual"  # user corrected

    db.commit()
    db.refresh(item)
    return {"message": "Line item updated", "item_id": item.id}


# --- Feasibility check ---
@app.post("/uploads/{upload_id}/feasibility")
def check_feasibility(
    upload_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == upload_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Upload not found")

    return feasibility_check(upload_id, db)


# --- Peer comparison ---
@app.post("/uploads/{upload_id}/compare")
def run_comparison(
    upload_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == upload_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Upload not found")

    if report.status not in ("extracted", "completed"):
        raise HTTPException(status_code=400, detail="Data must be extracted before comparison. Current status: " + report.status)

    comparison = generate_comparison(upload_id, db)
    if "error" in comparison:
        raise HTTPException(status_code=400, detail=comparison["error"])

    # Store comparison result
    report.comparison_result = json.dumps(comparison)
    report.status = "completed"
    db.commit()

    return comparison


@app.get("/uploads/{upload_id}/comparison")
def get_comparison(
    upload_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == upload_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Upload not found")

    if not report.comparison_result:
        raise HTTPException(status_code=404, detail="Comparison not generated yet")

    return json.loads(report.comparison_result)


# --- Benchmark (AI narrative of comparison results) ---
@app.post("/reports/{report_id}/benchmark")
def create_benchmark(
    report_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.comparison_result:
        raise HTTPException(status_code=400, detail="Run peer comparison first before generating narrative report.")

    comparison_data = json.loads(report.comparison_result)
    if "items" not in comparison_data:
        raise HTTPException(status_code=400, detail="Invalid comparison data. Please re-run the comparison.")

    org = db.query(Organization).filter(Organization.id == report.org_id).first()
    org_profile = {
        "name": org.name,
        "industry": org.industry,
        "size_band": org.size_band,
        "revenue_band": org.revenue_band,
        "revenue": org.revenue or 0,
        "size": org.size or 0,
    }

    # Generate AI narrative from structured comparison data
    result = generate_narrative(comparison_data, org_profile)
    if "error" in result:
        raise HTTPException(status_code=500, detail=f"Narrative generation failed: {result['error']}")

    # Upsert benchmark record
    existing = db.query(BenchmarkReport).filter(BenchmarkReport.report_id == report_id).first()
    if existing:
        existing.result = json.dumps(result)
        existing.peer_count = result.get("peer_count", 0)
    else:
        db.add(BenchmarkReport(
            report_id=report_id,
            result=json.dumps(result),
            peer_count=result.get("peer_count", 0),
        ))
    db.commit()

    return result


@app.get("/reports/{report_id}/benchmark")
def get_benchmark(
    report_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")

    benchmark = db.query(BenchmarkReport).filter(BenchmarkReport.report_id == report_id).first()
    if not benchmark:
        raise HTTPException(status_code=404, detail="Benchmark not generated yet")

    return json.loads(benchmark.result)


# --- Data coverage (public) ---
@app.get("/data-coverage")
def get_data_coverage(db: Session = Depends(get_db)):
    """Public endpoint showing what vendors/products have peer data."""
    from sqlalchemy import func, distinct

    stats = db.query(
        ContractLineItem.vendor_name,
        func.count(ContractLineItem.id).label("line_item_count"),
        func.count(distinct(ContractLineItem.org_id)).label("org_count"),
    ).group_by(ContractLineItem.vendor_name).all()

    return [
        {
            "vendor_name": s.vendor_name,
            "line_item_count": s.line_item_count,
            "org_count": s.org_count,
        }
        for s in stats
    ]


@app.get("/data-coverage/{vendor_name}")
def get_vendor_coverage(vendor_name: str, db: Session = Depends(get_db)):
    """Detailed coverage for a specific vendor."""
    from sqlalchemy import func, distinct

    stats = db.query(
        ContractLineItem.product_name,
        func.count(ContractLineItem.id).label("line_item_count"),
        func.count(distinct(ContractLineItem.org_id)).label("org_count"),
    ).filter(
        ContractLineItem.vendor_name == vendor_name
    ).group_by(ContractLineItem.product_name).all()

    return [
        {
            "product_name": s.product_name,
            "line_item_count": s.line_item_count,
            "org_count": s.org_count,
        }
        for s in stats
    ]


# --- Campaign submission (anonymous data collection) ---
@app.post("/campaign/submit")
async def campaign_submit(
    files: List[UploadFile] = File(...),
    vendor_name: str = Form(...),
    email: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    industry: Optional[str] = Form(None),
    company_size: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    """Anonymous/semi-anonymous contract upload for data collection campaign."""
    import re
    file_id = str(uuid.uuid4())
    safe_company = re.sub(r"[^a-zA-Z0-9_-]", "_", (company_name or "anonymous")).strip("_")[:50]
    campaign_folder = f"campaign/{safe_company}"
    campaign_dir = os.path.join(UPLOAD_DIR, campaign_folder, file_id)
    os.makedirs(campaign_dir, exist_ok=True)

    for file in files:
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(status_code=400, detail="File too large. Maximum is 50MB.")

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

        dest = os.path.join(campaign_dir, file.filename)
        with open(dest, "wb") as buffer:
            buffer.write(content)

    # Upload to S3 if configured
    if is_s3_enabled():
        import shutil
        s3_key = f"{campaign_folder}/{file_id}"
        s3_uri = s3_upload_directory(campaign_dir, s3_key)
        stored_path = s3_uri
        shutil.rmtree(campaign_dir, ignore_errors=True)
    else:
        stored_path = campaign_dir

    submission = CampaignSubmission(
        email=email,
        company_name=company_name,
        industry=industry,
        company_size=company_size,
        vendor_name=vendor_name,
        file_path=stored_path,
        status="submitted",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    return {
        "id": submission.id,
        "status": "submitted",
        "message": "Thank you for contributing. Your data will be processed and added to our benchmark database.",
    }


@app.get("/campaign/status/{submission_id}")
def campaign_status(submission_id: int, db: Session = Depends(get_db)):
    submission = db.query(CampaignSubmission).filter(
        CampaignSubmission.id == submission_id
    ).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    return {
        "id": submission.id,
        "status": submission.status,
        "line_items_extracted": submission.line_items_extracted,
    }


# --- Subscription & Payment endpoints ---

PLANS = [
    {
        "id": "free",
        "name": "Free",
        "price": 0,
        "reports_limit": 0,
        "features": ["Upload contracts", "AI extraction", "Data coverage view"],
        "stripe_price_id": None,
    },
    {
        "id": "starter",
        "name": "Starter",
        "price": 499,
        "reports_limit": 3,
        "features": ["Everything in Free", "3 peer comparison reports/month", "Benchmark narratives", "PDF download"],
        "stripe_price_id": os.getenv("STRIPE_STARTER_PRICE_ID", ""),
    },
    {
        "id": "professional",
        "name": "Professional",
        "price": 999,
        "reports_limit": 10,
        "features": ["Everything in Starter", "10 reports/month", "License analysis connectors", "Priority support"],
        "stripe_price_id": os.getenv("STRIPE_PROFESSIONAL_PRICE_ID", ""),
    },
    {
        "id": "enterprise",
        "name": "Enterprise",
        "price": -1,
        "reports_limit": -1,
        "features": ["Everything in Professional", "Unlimited reports", "Dedicated account manager", "Custom integrations"],
        "stripe_price_id": None,
    },
]


@app.get("/subscription/plans")
def get_plans():
    return [
        {**p, "stripe_price_id": p["stripe_price_id"] or None}
        for p in PLANS
    ]


@app.get("/subscription/status")
def subscription_status(
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    from payment import get_subscription_status
    return get_subscription_status(user_id, db)


@app.post("/subscription/create-checkout-session")
def create_subscription_checkout(
    req: CreateCheckoutRequest,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    from payment import create_subscription_checkout_session
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        client_secret = create_subscription_checkout_session(user, req.price_id, db)
        return {"client_secret": client_secret}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/subscription/portal")
def create_portal(
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    from payment import create_customer_portal_session
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        url = create_customer_portal_session(user, db)
        return {"url": url}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/subscription/checkout-status")
def checkout_session_status(
    session_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    import stripe
    session = stripe.checkout.Session.retrieve(session_id)
    return {"status": session.status}


class PaymentRequest(BaseModel):
    report_id: str
    amount: int

@app.post("/payment/checkout")
def create_checkout(
    payment_req: PaymentRequest,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    from payment import create_payment_session
    report = db.query(Report).filter(Report.id == payment_req.report_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")
    session = create_payment_session(payment_req.report_id, payment_req.amount, db)
    if not session:
        raise HTTPException(status_code=400, detail="Failed to create payment session")
    return {"session_id": session.id, "url": session.url}


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    import stripe
    from payment import handle_stripe_webhook
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")
    handle_stripe_webhook(event, db)
    return {"success": True}


# --- Download endpoints ---
@app.get("/download/{report_id}")
def download_report(
    report_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    from fastapi.responses import RedirectResponse
    from s3_storage import generate_presigned_url, S3_PREFIX

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.file_path.startswith("s3://"):
        # Generate a presigned URL and redirect the client
        # Extract the S3 key relative to the prefix
        s3_key = report.id  # files stored under uploads/<report_id>/
        url = generate_presigned_url(s3_key)
        if not url:
            raise HTTPException(status_code=500, detail="Could not generate download link")
        return RedirectResponse(url=url)
    else:
        if not os.path.exists(report.file_path):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(report.file_path, filename=report.filename)


@app.get("/download/{report_id}/full-report")
def download_full_report(
    report_id: str,
    request: Request,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    from pdf_report import generate_pdf_report

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")

    log_event(db, action="report.download", user_id=user_id,
              resource_type="report", resource_id=report_id,
              ip_address=_get_client_ip(request))

    org = db.query(Organization).filter(Organization.id == report.org_id).first()
    benchmark = db.query(BenchmarkReport).filter(BenchmarkReport.report_id == report_id).first()
    if not benchmark:
        raise HTTPException(status_code=400, detail="Generate the benchmark report first.")

    bm_result = json.loads(benchmark.result)

    # Get comparison data for the PDF
    comparison_data = None
    if report.comparison_result:
        try:
            comparison_data = json.loads(report.comparison_result)
        except Exception:
            pass

    org_profile = {
        "name": org.name if org else "N/A",
        "industry": org.industry if org else "N/A",
        "revenue": org.revenue if org else 0,
        "size": org.size if org else 0,
    }
    report_meta = {
        "filename": report.filename,
        "category": report.category,
        "created_at": str(report.created_at),
    }

    # Pass narrative text as analysis_text for PDF generation
    analysis_text = bm_result.get("narrative", "")

    pdf_bytes = generate_pdf_report(report_meta, org_profile, bm_result, analysis_text)
    filename = f"SaaSCostCompare_{org_profile['name'].replace(' ', '_')}_Report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/health")
def health_check():
    return {"status": "ok"}


# --- Contact form ---
class ContactRequest(BaseModel):
    name: str
    email: str
    company: str
    message: str


@app.post("/contact")
def submit_contact(req: ContactRequest, db: Session = Depends(get_db)):
    if not req.name.strip() or not req.email.strip() or not req.message.strip():
        raise HTTPException(status_code=400, detail="Name, email, and message are required.")
    inquiry = ContactInquiry(
        name=req.name.strip(),
        email=req.email.strip(),
        company=req.company.strip(),
        message=req.message.strip(),
    )
    db.add(inquiry)
    db.commit()
    return {"message": "Thank you for reaching out. We'll get back to you shortly."}


# --- License Analysis ---

@app.post("/generate-certificate")
def generate_certificate(current_user: User = Depends(get_current_user)):
    """Generate a private key + self-signed certificate for Salesforce JWT auth."""
    from cryptography import x509
    from cryptography.x509.oid import NameOID
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from datetime import datetime, timedelta

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "SaaSCostCompare"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "SaaSCostCompare"),
    ])

    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.utcnow())
        .not_valid_after(datetime.utcnow() + timedelta(days=365))
        .sign(private_key, hashes.SHA256())
    )

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    cert_pem = cert.public_bytes(serialization.Encoding.PEM).decode("utf-8")

    return {
        "private_key": private_key_pem,
        "certificate": cert_pem,
    }


class LicenseAnalysisRequest(BaseModel):
    vendor_name: str
    credentials: dict

@app.post("/license-analysis")
def run_license_analysis(
    req: LicenseAnalysisRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from vendor_connectors import get_connector

    connector = get_connector(req.vendor_name)
    if not connector:
        raise HTTPException(status_code=400, detail=f"Unsupported vendor: {req.vendor_name}")

    if not connector.authenticate(req.credentials):
        log_event(db, action="license_analysis.auth_failed", user_id=current_user.id,
                  resource_type="vendor", resource_id=req.vendor_name,
                  ip_address=_get_client_ip(request))
        raise HTTPException(
            status_code=401,
            detail=f"Failed to authenticate with {req.vendor_name}. Please check your credentials.",
        )

    try:
        summary = connector.get_license_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving license data: {str(e)}")

    analysis = LicenseAnalysis(
        org_id=current_user.org_id,
        owner_id=current_user.id,
        vendor_name=req.vendor_name,
        status="connected",
        result=json.dumps(summary),
    )
    db.add(analysis)
    db.commit()

    log_event(db, action="license_analysis.completed", user_id=current_user.id,
              resource_type="license_analysis", resource_id=str(analysis.id),
              detail=f"vendor={req.vendor_name}", ip_address=_get_client_ip(request))
    return summary


@app.get("/license-analysis")
def list_license_analyses(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analyses = (
        db.query(LicenseAnalysis)
        .filter(LicenseAnalysis.org_id == current_user.org_id)
        .order_by(LicenseAnalysis.created_at.desc())
        .all()
    )
    results = []
    for a in analyses:
        data = json.loads(a.result) if a.result else {}
        results.append({
            "id": a.id,
            "vendor_name": a.vendor_name,
            "status": a.status,
            "result": data,
            "created_at": str(a.created_at),
        })
    return results


@app.get("/license-analysis/{analysis_id}")
def get_license_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analysis = (
        db.query(LicenseAnalysis)
        .filter(
            LicenseAnalysis.id == analysis_id,
            LicenseAnalysis.org_id == current_user.org_id,
        )
        .first()
    )
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    data = json.loads(analysis.result) if analysis.result else {}
    return {
        "id": analysis.id,
        "vendor_name": analysis.vendor_name,
        "status": analysis.status,
        "result": data,
        "created_at": str(analysis.created_at),
    }
