from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, status, Request
from fastapi.responses import FileResponse, PlainTextResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import timedelta
import uuid
import os
import json
import threading
from pydantic import BaseModel

from database import engine, get_db, Base
from models import User, Organization, Report, BenchmarkReport, PasswordResetToken
from auth import hash_password, verify_password, create_access_token, verify_token
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
)
import stripe
from payment import create_payment_session, handle_stripe_webhook
from ai_analysis import generate_benchmark_report, read_saas_report, process_report
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
                process_report(report_id, file_path, org_id, db)
            finally:
                db.close()
        t = threading.Thread(target=run, daemon=True)
        t.start()
        return f"thread-{report_id}"

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# CORS middleware — restrict to configured origins
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

REQUIRED_CSV_COLUMNS = {
    "vendor", "product_name", "sku", "quantity",
    "unit_price", "total_cost", "billing_frequency", "currency",
}


def validate_csv_columns(content: bytes) -> None:
    """Raise HTTPException if the CSV is missing required columns."""
    import csv, io
    try:
        text = content.decode("utf-8-sig")  # handle BOM
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
    db_org = Organization(**org.dict())
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
def register_user(user: UserCreate, db: Session = Depends(get_db)):
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
    return db_user


@app.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == credentials.email).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=timedelta(hours=24)
    )
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
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    from email_utils import send_password_reset_email
    import secrets
    from datetime import datetime

    # Always return success to avoid leaking whether email exists
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        return {"message": "If that email exists, a reset link has been sent."}

    # Invalidate any existing unused tokens for this user
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False,
    ).update({"used": True})

    # Create new token (expires in 1 hour)
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

    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters.")

    user = db.query(User).filter(User.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="User not found.")

    user.hashed_password = hash_password(req.new_password)
    reset_token.used = True
    db.commit()

    return {"message": "Password has been reset successfully. You can now sign in."}



# --- Test/Dev: Mark report as paid (bypass Stripe) ---
@app.post("/reports/{report_id}/mark-paid")
def mark_report_paid(
    report_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")
    report.payment_status = "completed"
    db.commit()
    return {"message": "Report marked as paid", "payment_status": "completed"}


# --- Report endpoints ---
VALID_CATEGORIES = {"AWS", "Microsoft", "Google", "Salesforce", "Pega", "SAP"}

@app.post("/upload")
async def upload_report(
    file: UploadFile = File(...),
    category: str = Form(...),
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    if category not in VALID_CATEGORIES:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of: {', '.join(sorted(VALID_CATEGORIES))}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    if file.filename.endswith(".csv"):
        validate_csv_columns(content)

    file_id = str(uuid.uuid4())
    dest = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")
    with open(dest, "wb") as buffer:
        buffer.write(content)

    report = Report(
        id=file_id,
        org_id=user.org_id,
        owner_id=user_id,
        filename=file.filename,
        file_path=dest,
        status="uploaded",
        category=category,
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # Enqueue report for processing (Redis if available, else background thread)
    job_id = _try_enqueue(file_id, dest, user.org_id)

    return {
        "id": file_id,
        "filename": file.filename,
        "status": "uploaded",
        "category": category,
        "job_id": job_id,
    }


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
    
    return {
        "id": report.id,
        "status": report.status,
        "category": report.category,
        "payment_status": report.payment_status,
        "analysis": json.loads(report.comparison_result) if report.comparison_result else None,
    }


# --- Benchmark endpoints ---

@app.post("/reports/{report_id}/benchmark")
def create_benchmark(
    report_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.status != "completed":
        raise HTTPException(status_code=400, detail="Report must be completed before benchmarking")

    org = db.query(Organization).filter(Organization.id == report.org_id).first()
    org_profile = {
        "name": org.name,
        "domain": org.domain,
        "revenue": org.revenue or 0,
        "size": org.size or 0,
    }

    # Find peer orgs: similar revenue (0.4x–2.5x) and size (0.4x–2.5x), exclude own org
    revenue = org.revenue or 0
    size = org.size or 0
    peer_query = db.query(Organization).filter(Organization.id != org.id)
    if revenue > 0:
        peer_query = peer_query.filter(
            Organization.revenue >= revenue * 0.4,
            Organization.revenue <= revenue * 2.5,
        )
    if size > 0:
        peer_query = peer_query.filter(
            Organization.size >= size * 0.4,
            Organization.size <= size * 2.5,
        )
    peers = peer_query.limit(10).all()

    # Collect peer report data (only completed reports with accessible files)
    peer_data = []
    for peer in peers:
        peer_report = (
            db.query(Report)
            .filter(Report.org_id == peer.id, Report.status == "completed")
            .first()
        )
        if peer_report and peer_report.file_path and os.path.exists(peer_report.file_path):
            try:
                peer_report_data = read_saas_report(peer_report.file_path)
                peer_data.append(
                    {
                        "org": {"revenue": peer.revenue, "size": peer.size},
                        "report": peer_report_data,
                    }
                )
            except Exception:
                pass

    # Read target report data
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=400, detail="Report file not found on disk")
    target_data = read_saas_report(report.file_path)

    # Generate benchmark with Claude
    result = generate_benchmark_report(target_data, org_profile, peer_data)
    if "error" in result:
        raise HTTPException(status_code=500, detail=f"Benchmark generation failed: {result['error']}")

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


# --- Payment endpoints ---
class PaymentRequest(BaseModel):
    report_id: str
    amount: int  # in cents


@app.post("/payment/checkout")
def create_checkout(
    payment_req: PaymentRequest,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == payment_req.report_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")

    session = create_payment_session(payment_req.report_id, payment_req.amount, db)
    if not session:
        raise HTTPException(status_code=400, detail="Failed to create payment session")

    return {"session_id": session.id, "url": session.url}



@app.post("/webhook/stripe")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")

    if not webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook error: {str(e)}")

    handle_stripe_webhook(event, db)
    return {"success": True}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/download/{report_id}")
def download_report(
    report_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(report.file_path, filename=report.filename)


@app.get("/download/{report_id}/full-report")
def download_full_report(
    report_id: str,
    user_id: int = Depends(verify_token),
    db: Session = Depends(get_db),
):
    from pdf_report import generate_pdf_report

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report or report.owner_id != user_id:
        raise HTTPException(status_code=404, detail="Report not found")

    org = db.query(Organization).filter(Organization.id == report.org_id).first()
    benchmark = db.query(BenchmarkReport).filter(BenchmarkReport.report_id == report_id).first()
    if not benchmark:
        raise HTTPException(status_code=400, detail="Benchmark not generated yet. Please generate the benchmark report first.")

    bm_result = json.loads(benchmark.result)
    analysis_text = ""
    if report.comparison_result:
        try:
            analysis_text = json.loads(report.comparison_result).get("analysis", "")
            if isinstance(analysis_text, dict):
                analysis_text = analysis_text.get("analysis", "")
        except Exception:
            pass

    org_profile = {
        "name": org.name if org else "N/A",
        "domain": org.domain if org else "N/A",
        "revenue": org.revenue if org else 0,
        "size": org.size if org else 0,
    }
    report_meta = {
        "filename": report.filename,
        "category": report.category,
        "created_at": str(report.created_at),
    }

    pdf_bytes = generate_pdf_report(report_meta, org_profile, bm_result, analysis_text)
    filename = f"SaaSCostCompare_{org_profile['name'].replace(' ','_')}_Report.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
