import stripe
from typing import Dict, Any, Optional
from config.settings import settings
import asyncio

class StripeService:
    def __init__(self):
        if settings.STRIPE_SECRET_KEY:
            stripe.api_key = settings.STRIPE_SECRET_KEY
        else:
            print("⚠️  Warning: STRIPE_SECRET_KEY not set")
        
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    async def create_checkout_session(
        self,
        customer_email: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> stripe.checkout.Session:
        """Create a Stripe checkout session"""
        
        try:
            session = await asyncio.to_thread(
                stripe.checkout.Session.create,
                customer_email=customer_email,
                payment_method_types=['card'],
                line_items=[{
                    'price': price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=success_url,
                cancel_url=cancel_url,
                metadata=metadata or {},
                allow_promotion_codes=True,
                billing_address_collection='required',
                customer_creation='always'
            )
            
            return session
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")

    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str
    ) -> stripe.billing_portal.Session:
        """Create a Stripe customer portal session"""
        
        try:
            session = await asyncio.to_thread(
                stripe.billing_portal.Session.create,
                customer=customer_id,
                return_url=return_url
            )
            
            return session
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")

    async def get_or_create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """Get existing customer or create new one"""
        
        try:
            # Search for existing customer
            customers = await asyncio.to_thread(
                stripe.Customer.list,
                email=email,
                limit=1
            )
            
            if customers.data:
                return customers.data[0].id
            
            # Create new customer
            customer = await asyncio.to_thread(
                stripe.Customer.create,
                email=email,
                name=name,
                metadata=metadata or {}
            )
            
            return customer.id
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")

    async def get_subscription(self, subscription_id: str) -> stripe.Subscription:
        """Get subscription details"""
        
        try:
            subscription = await asyncio.to_thread(
                stripe.Subscription.retrieve,
                subscription_id
            )
            
            return subscription
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")

    async def cancel_subscription(self, subscription_id: str) -> stripe.Subscription:
        """Cancel a subscription"""
        
        try:
            subscription = await asyncio.to_thread(
                stripe.Subscription.delete,
                subscription_id
            )
            
            return subscription
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")

    async def process_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """Process Stripe webhook"""
        
        if not self.webhook_secret:
            raise Exception("Webhook secret not configured")
        
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            
            return event
            
        except ValueError as e:
            raise Exception(f"Invalid payload: {str(e)}")
        except stripe.error.SignatureVerificationError as e:
            raise Exception(f"Invalid signature: {str(e)}")

    async def create_price(
        self,
        amount: int,  # in cents
        currency: str = "usd",
        interval: str = "month",
        product_name: str = "ChatDys Premium"
    ) -> stripe.Price:
        """Create a new price (for testing/setup)"""
        
        try:
            # First create or get product
            products = await asyncio.to_thread(
                stripe.Product.list,
                limit=1
            )
            
            if products.data:
                product_id = products.data[0].id
            else:
                product = await asyncio.to_thread(
                    stripe.Product.create,
                    name=product_name,
                    description="Premium subscription for ChatDys"
                )
                product_id = product.id
            
            # Create price
            price = await asyncio.to_thread(
                stripe.Price.create,
                unit_amount=amount,
                currency=currency,
                recurring={"interval": interval},
                product=product_id
            )
            
            return price
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")

    async def get_customer_subscriptions(self, customer_id: str) -> list:
        """Get all subscriptions for a customer"""
        
        try:
            subscriptions = await asyncio.to_thread(
                stripe.Subscription.list,
                customer=customer_id,
                status='all'
            )
            
            return subscriptions.data
            
        except stripe.error.StripeError as e:
            raise Exception(f"Stripe error: {str(e)}")

# Create global instance
stripe_service = StripeService()
