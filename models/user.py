from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from database.connection import Base
from typing import Optional, Dict, Any
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    # Primary identification
    id = Column(String, primary_key=True, index=True)  # Auth0 user ID
    auth0_sub = Column(String, unique=True, index=True, nullable=False)  # Full Auth0 sub
    
    # Basic profile information
    email = Column(String, unique=True, index=True, nullable=False)
    email_verified = Column(Boolean, default=False)
    name = Column(String, nullable=True)
    given_name = Column(String, nullable=True)
    family_name = Column(String, nullable=True)
    nickname = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    
    # Additional profile information
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    location = Column(String, nullable=True)
    how_heard_about_us = Column(String, nullable=True)
    
    # Profile completion
    profile_completed = Column(Boolean, default=False)
    onboarding_completed = Column(Boolean, default=False)
    
    # Health information (for profile completion)
    age = Column(Integer, nullable=True)
    conditions = Column(JSON, nullable=True)  # List of conditions (legacy)
    health_conditions = Column(JSON, nullable=True)  # List of health conditions (new)
    symptoms = Column(JSON, nullable=True)   # List of symptoms
    medications = Column(JSON, nullable=True) # List of medications
    
    # Usage tracking
    question_count = Column(Integer, default=0)
    daily_question_count = Column(Integer, default=0)
    last_question_date = Column(DateTime, nullable=True)
    total_conversations = Column(Integer, default=0)
    
    # Subscription and premium features
    is_premium = Column(Boolean, default=False)
    subscription_status = Column(String, default="free")  # free, premium, cancelled
    subscription_id = Column(String, nullable=True)  # Stripe subscription ID
    premium_expires_at = Column(DateTime, nullable=True)
    
    # Preferences
    preferences = Column(JSON, nullable=True)  # User preferences as JSON
    notification_settings = Column(JSON, nullable=True)
    
    # Tracking and analytics
    first_login = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0)
    
    # HubSpot integration
    hubspot_contact_id = Column(String, nullable=True)
    hubspot_synced = Column(Boolean, default=False)
    hubspot_last_sync = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Soft delete
    is_active = Column(Boolean, default=True)
    deleted_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, premium={self.is_premium})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            "id": self.id,
            "auth0_sub": self.auth0_sub,
            "email": self.email,
            "email_verified": self.email_verified,
            "name": self.name,
            "given_name": self.given_name,
            "family_name": self.family_name,
            "nickname": self.nickname,
            "picture": self.picture,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone_number": self.phone_number,
            "location": self.location,
            "how_heard_about_us": self.how_heard_about_us,
            "profile_completed": self.profile_completed,
            "onboarding_completed": self.onboarding_completed,
            "age": self.age,
            "conditions": self.conditions,
            "health_conditions": self.health_conditions,
            "symptoms": self.symptoms,
            "medications": self.medications,
            "total_questions": self.question_count,  # Alias for compatibility
            "question_count": self.question_count,
            "daily_question_count": self.daily_question_count,
            "last_question_date": self.last_question_date.isoformat() if self.last_question_date else None,
            "total_conversations": self.total_conversations,
            "is_premium": self.is_premium,
            "subscription_status": self.subscription_status,
            "subscription_id": self.subscription_id,
            "premium_expires_at": self.premium_expires_at.isoformat() if self.premium_expires_at else None,
            "preferences": self.preferences,
            "notification_settings": self.notification_settings,
            "first_login": self.first_login.isoformat() if self.first_login else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "login_count": self.login_count,
            "hubspot_contact_id": self.hubspot_contact_id,
            "hubspot_synced": self.hubspot_synced,
            "hubspot_last_sync": self.hubspot_last_sync.isoformat() if self.hubspot_last_sync else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active
        }

    def to_session_dict(self) -> Dict[str, Any]:
        """Convert user to session dictionary (safe for frontend)"""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "given_name": self.given_name,
            "picture": self.picture,
            "profile_completed": self.profile_completed,
            "onboarding_completed": self.onboarding_completed,
            "question_count": self.question_count,
            "daily_question_count": self.daily_question_count,
            "is_premium": self.is_premium,
            "subscription_status": self.subscription_status,
            "preferences": self.preferences or {},
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def can_ask_questions(self, daily_limit: int = 5) -> bool:
        """Check if user can ask more questions"""
        if self.is_premium:
            return True
        
        # Check if it's a new day
        today = datetime.now().date()
        if self.last_question_date:
            last_question_date = self.last_question_date.date()
            if last_question_date != today:
                # Reset daily count for new day
                return True
        
        return self.daily_question_count < daily_limit

    def reset_daily_count_if_needed(self):
        """Reset daily question count if it's a new day"""
        today = datetime.now().date()
        if self.last_question_date:
            last_question_date = self.last_question_date.date()
            if last_question_date != today:
                self.daily_question_count = 0