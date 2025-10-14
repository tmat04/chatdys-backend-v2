from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime, date
from pydantic import BaseModel, EmailStr

from database.connection import get_db
from models.user import User
from auth.auth0_manager import auth0_manager
from config.settings import settings

router = APIRouter()

# Pydantic models for request/response
class ProfileCompletionRequest(BaseModel):
    age: Optional[int] = None
    conditions: Optional[List[str]] = None
    symptoms: Optional[List[str]] = None
    medications: Optional[List[str]] = None
    preferences: Optional[Dict[str, Any]] = None

class UserPreferencesRequest(BaseModel):
    preferences: Dict[str, Any]
    notification_settings: Optional[Dict[str, Any]] = None

class UserSessionResponse(BaseModel):
    id: str
    email: str
    name: Optional[str]
    given_name: Optional[str]
    picture: Optional[str]
    profile_completed: bool
    onboarding_completed: bool
    question_count: int
    daily_question_count: int
    is_premium: bool
    subscription_status: str
    preferences: Dict[str, Any]
    created_at: Optional[str]

# Dependency to get current user from database
async def get_current_user_from_db(
    token_user: Dict = Depends(auth0_manager.validate_token),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from database, create if doesn't exist"""
    
    auth0_sub = token_user.get("sub")
    if not auth0_sub:
        raise HTTPException(
            status_code=400,
            detail="Invalid token: missing sub claim"
        )
    
    # Extract clean user ID
    user_id = auth0_manager.extract_user_id(token_user)
    
    # Try to find existing user
    user = db.query(User).filter(User.auth0_sub == auth0_sub).first()
    
    if not user:
        # Create new user
        user = User(
            id=user_id,
            auth0_sub=auth0_sub,
            email=token_user.get("email"),
            email_verified=token_user.get("email_verified", False),
            name=token_user.get("name"),
            given_name=token_user.get("given_name"),
            family_name=token_user.get("family_name"),
            nickname=token_user.get("nickname"),
            picture=token_user.get("picture"),
            first_login=datetime.now(),
            last_login=datetime.now(),
            login_count=1
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        print(f"✅ Created new user: {user.email}")
    else:
        # Update login info
        user.last_login = datetime.now()
        user.login_count += 1
        
        # Update profile info from token if changed
        user.email = token_user.get("email", user.email)
        user.email_verified = token_user.get("email_verified", user.email_verified)
        user.name = token_user.get("name", user.name)
        user.given_name = token_user.get("given_name", user.given_name)
        user.family_name = token_user.get("family_name", user.family_name)
        user.nickname = token_user.get("nickname", user.nickname)
        user.picture = token_user.get("picture", user.picture)
        
        # Reset daily count if needed
        user.reset_daily_count_if_needed()
        
        db.commit()
        db.refresh(user)
    
    return user

@router.get("/session", response_model=UserSessionResponse)
async def get_user_session(
    current_user: User = Depends(get_current_user_from_db)
):
    """Get current user session data"""
    return UserSessionResponse(**current_user.to_session_dict())

@router.get("/profile")
async def get_user_profile(
    current_user: User = Depends(get_current_user_from_db)
):
    """Get detailed user profile"""
    return current_user.to_dict()

@router.post("/increment-question")
async def increment_question_count(
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """Increment user's question count"""
    
    # Check if user can ask questions
    if not current_user.can_ask_questions(settings.FREE_USER_DAILY_LIMIT):
        raise HTTPException(
            status_code=429,
            detail="Daily question limit reached. Upgrade to Premium for unlimited questions."
        )
    
    # Reset daily count if it's a new day
    current_user.reset_daily_count_if_needed()
    
    # Increment counters
    current_user.question_count += 1
    current_user.daily_question_count += 1
    current_user.last_question_date = datetime.now()
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "question_count": current_user.question_count,
        "daily_question_count": current_user.daily_question_count,
        "can_ask_more": current_user.can_ask_questions(settings.FREE_USER_DAILY_LIMIT),
        "is_premium": current_user.is_premium
    }

@router.post("/complete-profile")
async def complete_profile(
    profile_data: ProfileCompletionRequest,
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """Complete user profile during onboarding"""
    
    # Update profile fields
    if profile_data.age is not None:
        current_user.age = profile_data.age
    
    if profile_data.conditions is not None:
        current_user.conditions = profile_data.conditions
    
    if profile_data.symptoms is not None:
        current_user.symptoms = profile_data.symptoms
    
    if profile_data.medications is not None:
        current_user.medications = profile_data.medications
    
    if profile_data.preferences is not None:
        current_user.preferences = profile_data.preferences
    
    # Mark profile as completed
    current_user.profile_completed = True
    current_user.onboarding_completed = True
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Profile completed successfully",
        "profile_completed": current_user.profile_completed,
        "onboarding_completed": current_user.onboarding_completed
    }

@router.put("/preferences")
async def update_preferences(
    preferences_data: UserPreferencesRequest,
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """Update user preferences"""
    
    current_user.preferences = preferences_data.preferences
    
    if preferences_data.notification_settings is not None:
        current_user.notification_settings = preferences_data.notification_settings
    
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Preferences updated successfully",
        "preferences": current_user.preferences,
        "notification_settings": current_user.notification_settings
    }

@router.get("/usage")
async def get_usage_stats(
    current_user: User = Depends(get_current_user_from_db)
):
    """Get user usage statistics"""
    
    # Reset daily count if needed
    current_user.reset_daily_count_if_needed()
    
    return {
        "question_count": current_user.question_count,
        "daily_question_count": current_user.daily_question_count,
        "total_conversations": current_user.total_conversations,
        "is_premium": current_user.is_premium,
        "subscription_status": current_user.subscription_status,
        "daily_limit": settings.FREE_USER_DAILY_LIMIT if not current_user.is_premium else settings.PREMIUM_USER_DAILY_LIMIT,
        "can_ask_questions": current_user.can_ask_questions(settings.FREE_USER_DAILY_LIMIT),
        "last_question_date": current_user.last_question_date.isoformat() if current_user.last_question_date else None
    }

@router.delete("/account")
async def delete_account(
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """Soft delete user account"""
    
    current_user.is_active = False
    current_user.deleted_at = datetime.now()
    
    db.commit()
    
    return {"message": "Account deleted successfully"}

@router.get("/check-premium")
async def check_premium_status(
    current_user: User = Depends(get_current_user_from_db)
):
    """Check if user has premium access"""
    
    # Check if premium subscription is still valid
    if current_user.is_premium and current_user.premium_expires_at:
        if datetime.now() > current_user.premium_expires_at:
            # Premium expired, update status
            current_user.is_premium = False
            current_user.subscription_status = "expired"
    
    return {
        "is_premium": current_user.is_premium,
        "subscription_status": current_user.subscription_status,
        "premium_expires_at": current_user.premium_expires_at.isoformat() if current_user.premium_expires_at else None
    }
