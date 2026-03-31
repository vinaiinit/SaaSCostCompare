import stripe
import os
from sqlalchemy.orm import Session
from models import Report

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def create_payment_session(report_id: str, amount: int, db: Session):
    """
    Create a Stripe checkout session for the report.
    Amount should be in cents (e.g., 9999 for $99.99)
    """
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "SaaS Cost Comparison Report",
                            "description": "AI-powered SaaS cost comparison and benchmarking analysis",
                        },
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            success_url=f"{FRONTEND_URL}/dashboard?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/dashboard?payment=cancelled",
            metadata={"report_id": report_id},
        )
        return session
    except stripe.error.StripeError as e:
        print(f"Error creating Stripe session: {str(e)}")
        return None


def verify_payment(session_id: str, report_id: str, db: Session):
    """
    Verify payment completion and update report status.
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == "paid":
            report = db.query(Report).filter(Report.id == report_id).first()
            if report:
                report.payment_status = "completed"
                db.commit()
                return True
        return False
    except stripe.error.StripeError as e:
        print(f"Error verifying payment: {str(e)}")
        return False


def handle_stripe_webhook(event: dict, db: Session):
    """
    Handle Stripe webhook events.
    """
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        report_id = session.get("metadata", {}).get("report_id")
        if report_id:
            verify_payment(session["id"], report_id, db)
