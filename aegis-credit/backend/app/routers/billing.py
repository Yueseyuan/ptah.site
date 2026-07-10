"""Stripe billing endpoints for the client portal."""
import stripe
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

from app.database import get_db
from app.models import User
from app.dependencies import get_current_user
from app.config import settings
from app.services.email_service import (
    send_subscription_confirmed_email,
    send_payment_failed_email,
    send_subscription_cancelled_email,
)

router = APIRouter(prefix="/api/portal/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    promo_code: Optional[str] = None


def _sync_subscription(user: User, sub: stripe.Subscription, db: Session) -> None:
    """Update user's subscription fields from a Stripe Subscription object."""
    user.stripe_subscription_id = sub.id
    user.subscription_status = sub.status
    period_end = getattr(sub, "current_period_end", None)
    if period_end:
        user.subscription_period_end = datetime.fromtimestamp(period_end)
    db.commit()


@router.get("/status")
def billing_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current subscription status for the portal client."""
    return {
        "subscription_status": current_user.subscription_status,
        "subscription_period_end": (
            current_user.subscription_period_end.isoformat()
            if current_user.subscription_period_end else None
        ),
        "stripe_customer_id": current_user.stripe_customer_id,
        "publishable_key": settings.STRIPE_PUBLISHABLE_KEY,
    }


@router.post("/create-checkout")
def create_checkout_session(
    body: CheckoutRequest = CheckoutRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Checkout session for the monthly subscription.
    Optionally pre-applies a promotion code; falls back to Stripe's
    built-in promo code field if none is provided."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    if not stripe.api_key:
        raise HTTPException(503, "Billing not configured — STRIPE_SECRET_KEY missing")
    if not settings.STRIPE_PRICE_ID:
        raise HTTPException(503, "Subscription price not configured — STRIPE_PRICE_ID missing")

    if current_user.subscription_status == "active":
        raise HTTPException(400, "You already have an active subscription")

    customer_id = current_user.stripe_customer_id

    try:
        if not customer_id:
            customer = stripe.Customer.create(
                email=current_user.email,
                name=current_user.full_name,
                metadata={"user_id": str(current_user.id), "username": current_user.username},
            )
            customer_id = customer.id
            current_user.stripe_customer_id = customer_id
            db.commit()

        session_params: dict = {
            "customer": customer_id,
            "mode": "subscription",
            "line_items": [{"price": settings.STRIPE_PRICE_ID, "quantity": 1}],
            "success_url": f"{settings.PORTAL_BASE_URL}/portal/dashboard?payment=success",
            "cancel_url": f"{settings.PORTAL_BASE_URL}/portal/billing",
            "client_reference_id": str(current_user.id),
            "subscription_data": {
                "metadata": {
                    "user_id": str(current_user.id),
                    "username": current_user.username,
                }
            },
        }

        if body.promo_code:
            # Resolve the promotion code to its ID
            codes = stripe.PromotionCode.list(code=body.promo_code, active=True, limit=1)
            if not codes.data:
                raise HTTPException(400, "Invalid or expired promo code")
            session_params["discounts"] = [{"promotion_code": codes.data[0].id}]
        else:
            # Let Stripe show its built-in promo code field at checkout
            session_params["allow_promotion_codes"] = True

        session = stripe.checkout.Session.create(**session_params)
        return {"checkout_url": session.url}
    except HTTPException:
        raise
    except stripe.error.StripeError as e:
        raise HTTPException(502, f"Stripe error: {e.user_message or str(e)}")


@router.post("/customer-portal")
def customer_portal_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a Stripe Customer Portal session so the client can manage/cancel."""
    stripe.api_key = settings.STRIPE_SECRET_KEY
    if not stripe.api_key:
        raise HTTPException(503, "Billing not configured — STRIPE_SECRET_KEY missing")
    if not current_user.stripe_customer_id:
        raise HTTPException(400, "No billing account found")

    try:
        session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=f"{settings.PORTAL_BASE_URL}/portal/billing",
        )
        return {"portal_url": session.url}
    except stripe.error.StripeError as e:
        raise HTTPException(502, f"Stripe error: {e.user_message or str(e)}")


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    if settings.STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except stripe.error.SignatureVerificationError:
            raise HTTPException(400, "Invalid webhook signature")
    else:
        import json
        event = json.loads(payload)

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        user_id = int(data.get("client_reference_id") or 0)
        if user_id:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                sub_id = data.get("subscription")
                if sub_id:
                    sub = stripe.Subscription.retrieve(sub_id)
                    _sync_subscription(user, sub, db)
                    next_billing = (
                        user.subscription_period_end.strftime("%B %d, %Y")
                        if user.subscription_period_end else "—"
                    )
                    first_name = (user.full_name or "").split()[0] if user.full_name else ""
                    send_subscription_confirmed_email(user.email, first_name, next_billing)

    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        sub = data
        customer_id = sub.get("customer")
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            old_status = user.subscription_status
            user.stripe_subscription_id = sub["id"]
            user.subscription_status = sub["status"]
            period_end = sub.get("current_period_end")
            if period_end:
                user.subscription_period_end = datetime.fromtimestamp(period_end)
            db.commit()
            first_name = (user.full_name or "").split()[0] if user.full_name else ""
            if sub["status"] in ("canceled", "cancelled") and old_status not in ("canceled", "cancelled"):
                end_date = (
                    user.subscription_period_end.strftime("%B %d, %Y")
                    if user.subscription_period_end else "—"
                )
                send_subscription_cancelled_email(user.email, first_name, end_date)

    elif event_type == "invoice.payment_failed":
        customer_id = data.get("customer")
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.subscription_status = "past_due"
            db.commit()
            first_name = (user.full_name or "").split()[0] if user.full_name else ""
            send_payment_failed_email(user.email, first_name)

    return JSONResponse({"received": True})
