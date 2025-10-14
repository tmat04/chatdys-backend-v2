from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

from database.connection import get_db
from models.user import User
from api.user_routes import get_current_user_from_db
from payments.stripe_service import StripeService
from config.settings import settings

router = APIRouter()

# Initialize Stripe service
stripe_service = StripeService()

class CreateCheckoutSessionRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str

class CreatePortalSessionRequest(BaseModel):
    return_url: str

@router.post("/create-checkout-session")
async def create_checkout_session(
    request: CreateCheckoutSessionRequest,
    current_user: User = Depends(get_current_user_from_db)
):
    """Create Stripe checkout session for premium subscription"""
    
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Payment processing is not configured"
        )
    
    try:
        session = await stripe_service.create_checkout_session(
            customer_email=current_user.email,
            price_id=request.price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
            metadata={
                "user_id": current_user.id,
                "auth0_sub": current_user.auth0_sub
            }
        )
        
        return {"checkout_url": session.url}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create checkout session: {str(e)}"
        )

@router.post("/create-portal-session")
async def create_portal_session(
    request: CreatePortalSessionRequest,
    current_user: User = Depends(get_current_user_from_db)
):
    """Create Stripe customer portal session"""
    
    if not settings.STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Payment processing is not configured"
        )
    
    if not current_user.is_premium:
        raise HTTPException(
            status_code=403,
            detail="Customer portal is only available for premium subscribers"
        )
    
    try:
        # Get or create Stripe customer
        customer_id = await stripe_service.get_or_create_customer(
            email=current_user.email,
            name=current_user.name,
            metadata={"user_id": current_user.id}
        )
        
        session = await stripe_service.create_portal_session(
            customer_id=customer_id,
            return_url=request.return_url
        )
        
        return {"portal_url": session.url}
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create portal session: {str(e)}"
        )

@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_db)
):
    """Handle Stripe webhooks"""
    
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Webhook processing is not configured"
        )
    
    try:
        # Get raw body and signature
        body = await request.body()
        signature = request.headers.get("stripe-signature")
        
        if not signature:
            raise HTTPException(
                status_code=400,
                detail="Missing Stripe signature"
            )
        
        # Process webhook
        event = await stripe_service.process_webhook(body, signature)
        
        if event["type"] == "checkout.session.completed":
            await handle_checkout_completed(event["data"]["object"], db)
        elif event["type"] == "customer.subscription.updated":
            await handle_subscription_updated(event["data"]["object"], db)
        elif event["type"] == "customer.subscription.deleted":
            await handle_subscription_deleted(event["data"]["object"], db)
        elif event["type"] == "invoice.payment_succeeded":
            await handle_payment_succeeded(event["data"]["object"], db)
        elif event["type"] == "invoice.payment_failed":
            await handle_payment_failed(event["data"]["object"], db)
        
        return {"status": "success"}
        
    except Exception as e:
        print(f"❌ Webhook error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Webhook processing failed: {str(e)}"
        )

@router.get("/subscription-status")
async def get_subscription_status(
    current_user: User = Depends(get_current_user_from_db)
):
    """Get current subscription status"""
    
    return {
        "is_premium": current_user.is_premium,
        "subscription_status": current_user.subscription_status,
        "subscription_id": current_user.subscription_id,
        "premium_expires_at": current_user.premium_expires_at.isoformat() if current_user.premium_expires_at else None
    }

# Webhook handlers
async def handle_checkout_completed(session: Dict[str, Any], db: Session):
    """Handle successful checkout completion"""
    try:
        user_id = session["metadata"].get("user_id")
        if not user_id:
            print("❌ No user_id in checkout session metadata")
            return
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ User not found: {user_id}")
            return
        
        # Update user to premium
        user.is_premium = True
        user.subscription_status = "active"
        user.subscription_id = session.get("subscription")
        user.premium_expires_at = datetime.now() + timedelta(days=30)  # Monthly subscription
        
        db.commit()
        print(f"✅ User {user.email} upgraded to premium")
        
    except Exception as e:
        print(f"❌ Error handling checkout completion: {str(e)}")

async def handle_subscription_updated(subscription: Dict[str, Any], db: Session):
    """Handle subscription updates"""
    try:
        subscription_id = subscription["id"]
        status = subscription["status"]
        
        user = db.query(User).filter(User.subscription_id == subscription_id).first()
        if not user:
            print(f"❌ User not found for subscription: {subscription_id}")
            return
        
        user.subscription_status = status
        
        if status == "active":
            user.is_premium = True
            # Update expiration based on current period end
            current_period_end = subscription.get("current_period_end")
            if current_period_end:
                user.premium_expires_at = datetime.fromtimestamp(current_period_end)
        elif status in ["canceled", "unpaid", "past_due"]:
            user.is_premium = False
        
        db.commit()
        print(f"✅ Updated subscription for {user.email}: {status}")
        
    except Exception as e:
        print(f"❌ Error handling subscription update: {str(e)}")

async def handle_subscription_deleted(subscription: Dict[str, Any], db: Session):
    """Handle subscription cancellation"""
    try:
        subscription_id = subscription["id"]
        
        user = db.query(User).filter(User.subscription_id == subscription_id).first()
        if not user:
            print(f"❌ User not found for subscription: {subscription_id}")
            return
        
        user.is_premium = False
        user.subscription_status = "canceled"
        
        db.commit()
        print(f"✅ Canceled subscription for {user.email}")
        
    except Exception as e:
        print(f"❌ Error handling subscription deletion: {str(e)}")

async def handle_payment_succeeded(invoice: Dict[str, Any], db: Session):
    """Handle successful payment"""
    try:
        subscription_id = invoice.get("subscription")
        if not subscription_id:
            return
        
        user = db.query(User).filter(User.subscription_id == subscription_id).first()
        if not user:
            return
        
        # Extend premium access
        period_end = invoice.get("period_end")
        if period_end:
            user.premium_expires_at = datetime.fromtimestamp(period_end)
            user.is_premium = True
            user.subscription_status = "active"
        
        db.commit()
        print(f"✅ Payment succeeded for {user.email}")
        
    except Exception as e:
        print(f"❌ Error handling payment success: {str(e)}")

async def handle_payment_failed(invoice: Dict[str, Any], db: Session):
    """Handle failed payment"""
    try:
        subscription_id = invoice.get("subscription")
        if not subscription_id:
            return
        
        user = db.query(User).filter(User.subscription_id == subscription_id).first()
        if not user:
            return
        
        user.subscription_status = "past_due"
        # Don't immediately revoke premium access, give some grace period
        
        db.commit()
        print(f"⚠️  Payment failed for {user.email}")
        
    except Exception as e:
        print(f"❌ Error handling payment failure: {str(e)}")
