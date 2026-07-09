"""
Payments API — Stripe Integration
Handles checkout sessions and webhooks.
"""
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import stripe
import os
import json
from datetime import datetime
from src.utils.logging import logger

router = APIRouter(prefix="/api/payments", tags=["payments"])

# Stripe keys
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")

stripe.api_key = STRIPE_SECRET_KEY

# Plan definitions
PLANS = {
    "basic": {
        "name": "Xythe Basic",
        "price": 9900,  # RM99 in sen
        "currency": "myr",
        "features": ["WhatsApp auto-reply", "50 documents", "5,000 queries/month", "Cloud storage"],
    },
    "pro": {
        "name": "Xythe Pro",
        "price": 29900,  # RM299 in sen
        "currency": "myr",
        "features": ["Everything in Basic", "Unlimited queries", "Follow-up automation", "Full analytics"],
    },
    "max": {
        "name": "Xythe Max",
        "price": 59900,  # RM599 in sen
        "currency": "myr",
        "features": ["Everything in Pro", "Team management (5 users)", "Custom branding", "Dedicated support"],
    },
}

# File-based subscription store (replace with database later)
SUBSCRIPTIONS_FILE = "./data/subscriptions.json"
os.makedirs("./data", exist_ok=True)


def load_subscriptions():
    try:
        with open(SUBSCRIPTIONS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}


def save_subscriptions(data):
    with open(SUBSCRIPTIONS_FILE, "w") as f:
        json.dump(data, f, indent=2)


class CreateCheckoutRequest(BaseModel):
    tenant_id: str
    plan: str
    success_url: str = "https://xythe.my/success"
    cancel_url: str = "https://xythe.my/pricing"


@router.post("/create-checkout")
async def create_checkout(data: CreateCheckoutRequest):
    """Create a Stripe checkout session for a plan."""
    if data.plan not in PLANS:
        raise HTTPException(400, "Invalid plan")

    plan = PLANS[data.plan]

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card", "fpx"],
            line_items=[{
                "price_data": {
                    "currency": plan["currency"],
                    "product_data": {
                        "name": plan["name"],
                        "description": "Monthly subscription",
                    },
                    "unit_amount": plan["price"],
                    "recurring": {
                        "interval": "month",
                    },
                },
                "quantity": 1,
            }],
            mode="subscription",
            success_url=data.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=data.cancel_url,
            metadata={
                "tenant_id": data.tenant_id,
                "plan": data.plan,
            },
        )

        return {
            "url": session.url,
            "session_id": session.id,
        }

    except Exception as e:
        logger.error(f"Stripe checkout error: {e}")
        raise HTTPException(500, str(e))


@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Receive Stripe events (payment success, failure, cancellation)."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise HTTPException(400, "Invalid signature")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        tenant_id = session.get("metadata", {}).get("tenant_id")
        plan = session.get("metadata", {}).get("plan")
        customer_email = session.get("customer_details", {}).get("email")

        logger.info(f"✅ Payment success: {tenant_id} → {plan} ({customer_email})")

        # Update subscription
        subs = load_subscriptions()
        subs[tenant_id] = {
            "plan": plan,
            "status": "active",
            "stripe_customer_id": session.get("customer"),
            "subscription_id": session.get("subscription"),
            "started_at": datetime.utcnow().isoformat(),
        }
        save_subscriptions(subs)

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        # Find and update tenant
        subs = load_subscriptions()
        for tid, sub in subs.items():
            if sub.get("subscription_id") == subscription["id"]:
                subs[tid]["status"] = "cancelled"
                logger.info(f"❌ Subscription cancelled: {tid}")
                break
        save_subscriptions(subs)

    elif event["type"] == "invoice.payment_failed":
        invoice = event["data"]["object"]
        logger.warning(f"⚠️ Payment failed: {invoice.get('customer_email')}")

    return {"status": "ok"}


@router.get("/subscription/{tenant_id}")
async def get_subscription(tenant_id: str):
    """Get current subscription status for a tenant."""
    subs = load_subscriptions()
    sub = subs.get(tenant_id)

    if not sub:
        return {
            "plan": "free",
            "status": "active",
        }

    return sub