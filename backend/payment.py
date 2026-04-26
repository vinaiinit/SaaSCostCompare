import stripe
import os
from datetime import datetime
from sqlalchemy.orm import Session
from models import Report, Subscription, User

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

PLAN_LIMITS = {
    "free": 0,
    "starter": 3,
    "professional": 10,
    "enterprise": -1,
}

PRICE_TO_PLAN = {}


def _load_price_mapping():
    global PRICE_TO_PLAN
    starter_id = os.getenv("STRIPE_STARTER_PRICE_ID", "")
    pro_id = os.getenv("STRIPE_PROFESSIONAL_PRICE_ID", "")
    if starter_id:
        PRICE_TO_PLAN[starter_id] = "starter"
    if pro_id:
        PRICE_TO_PLAN[pro_id] = "professional"


def get_or_create_stripe_customer(user: User, db: Session) -> str:
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if sub and sub.stripe_customer_id:
        return sub.stripe_customer_id

    customer = stripe.Customer.create(
        email=user.email,
        name=user.full_name,
        metadata={"user_id": str(user.id), "org_id": str(user.org_id)},
    )

    if not sub:
        sub = Subscription(
            user_id=user.id,
            org_id=user.org_id,
            stripe_customer_id=customer.id,
            plan="free",
            status="active",
            reports_limit=0,
        )
        db.add(sub)
    else:
        sub.stripe_customer_id = customer.id

    db.commit()
    return customer.id


def create_subscription_checkout_session(user: User, price_id: str, db: Session) -> str:
    _load_price_mapping()
    customer_id = get_or_create_stripe_customer(user, db)

    session = stripe.checkout.Session.create(
        ui_mode="embedded",
        mode="subscription",
        customer=customer_id,
        line_items=[{"price": price_id, "quantity": 1}],
        return_url=f"{FRONTEND_URL}/checkout/return?session_id={{CHECKOUT_SESSION_ID}}",
    )
    return session.client_secret


def create_customer_portal_session(user: User, db: Session) -> str:
    sub = db.query(Subscription).filter(Subscription.user_id == user.id).first()
    if not sub or not sub.stripe_customer_id:
        raise ValueError("No Stripe customer found")

    session = stripe.billing_portal.Session.create(
        customer=sub.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/dashboard",
    )
    return session.url


def get_subscription_status(user_id: int, db: Session) -> dict:
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if not sub:
        return {
            "plan": "free",
            "status": "active",
            "reports_used": 0,
            "reports_limit": 0,
            "current_period_end": None,
            "cancel_at_period_end": False,
        }
    return {
        "plan": sub.plan,
        "status": sub.status,
        "reports_used": sub.reports_used_this_period,
        "reports_limit": sub.reports_limit,
        "current_period_end": sub.current_period_end,
        "cancel_at_period_end": sub.cancel_at_period_end,
    }


def handle_stripe_webhook(event: dict, db: Session):
    _load_price_mapping()
    event_type = event["type"]
    obj = event["data"]["object"]

    if event_type == "checkout.session.completed":
        if obj.get("mode") == "subscription":
            _handle_subscription_checkout(obj, db)
        else:
            report_id = obj.get("metadata", {}).get("report_id")
            if report_id:
                _handle_report_payment(obj, report_id, db)

    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(obj, db)

    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(obj, db)

    elif event_type == "invoice.paid":
        _handle_invoice_paid(obj, db)

    elif event_type == "invoice.payment_failed":
        _handle_invoice_failed(obj, db)


def _handle_subscription_checkout(session: dict, db: Session):
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    if not customer_id:
        return

    sub = db.query(Subscription).filter(
        Subscription.stripe_customer_id == customer_id
    ).first()
    if not sub:
        return

    sub.stripe_subscription_id = subscription_id

    stripe_sub = stripe.Subscription.retrieve(subscription_id)
    price_id = stripe_sub["items"]["data"][0]["price"]["id"]
    plan = PRICE_TO_PLAN.get(price_id, "starter")

    sub.plan = plan
    sub.status = "active"
    sub.reports_limit = PLAN_LIMITS.get(plan, 0)
    sub.reports_used_this_period = 0
    sub.current_period_start = datetime.fromtimestamp(stripe_sub["current_period_start"])
    sub.current_period_end = datetime.fromtimestamp(stripe_sub["current_period_end"])
    sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
    db.commit()


def _handle_subscription_updated(stripe_sub: dict, db: Session):
    sub = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub["id"]
    ).first()
    if not sub:
        return

    price_id = stripe_sub["items"]["data"][0]["price"]["id"]
    plan = PRICE_TO_PLAN.get(price_id, sub.plan)

    sub.plan = plan
    sub.status = stripe_sub["status"]
    sub.reports_limit = PLAN_LIMITS.get(plan, sub.reports_limit)
    sub.current_period_start = datetime.fromtimestamp(stripe_sub["current_period_start"])
    sub.current_period_end = datetime.fromtimestamp(stripe_sub["current_period_end"])
    sub.cancel_at_period_end = stripe_sub.get("cancel_at_period_end", False)
    db.commit()


def _handle_subscription_deleted(stripe_sub: dict, db: Session):
    sub = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == stripe_sub["id"]
    ).first()
    if not sub:
        return

    sub.plan = "free"
    sub.status = "canceled"
    sub.reports_limit = 0
    sub.stripe_subscription_id = None
    db.commit()


def _handle_invoice_paid(invoice: dict, db: Session):
    sub_id = invoice.get("subscription")
    if not sub_id:
        return
    sub = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == sub_id
    ).first()
    if sub:
        sub.reports_used_this_period = 0
        sub.status = "active"
        db.commit()


def _handle_invoice_failed(invoice: dict, db: Session):
    sub_id = invoice.get("subscription")
    if not sub_id:
        return
    sub = db.query(Subscription).filter(
        Subscription.stripe_subscription_id == sub_id
    ).first()
    if sub:
        sub.status = "past_due"
        db.commit()


def _handle_report_payment(session: dict, report_id: str, db: Session):
    if session.get("payment_status") == "paid":
        report = db.query(Report).filter(Report.id == report_id).first()
        if report:
            report.payment_status = "completed"
            db.commit()


def create_payment_session(report_id: str, amount: int, db: Session):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {
                        "name": "SaaS Cost Comparison Report",
                        "description": "AI-powered SaaS cost comparison and benchmarking analysis",
                    },
                    "unit_amount": amount,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"{FRONTEND_URL}/dashboard?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/dashboard?payment=cancelled",
            metadata={"report_id": report_id},
        )
        return session
    except stripe.error.StripeError as e:
        print(f"Error creating Stripe session: {str(e)}")
        return None
