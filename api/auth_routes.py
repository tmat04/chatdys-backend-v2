from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from datetime import datetime
from pydantic import BaseModel

from database.connection import get_db
from models.user import User
from auth.auth0_manager import auth0_manager
from api.user_routes import get_current_user_from_db

router = APIRouter()

class TokenValidationResponse(BaseModel):
    valid: bool
    user_id: str
    email: str
    message: str

@router.post("/validate-token", response_model=TokenValidationResponse)
async def validate_token(
    current_user: User = Depends(get_current_user_from_db)
):
    """Validate Auth0 token and return user info"""
    return TokenValidationResponse(
        valid=True,
        user_id=current_user.id,
        email=current_user.email,
        message="Token is valid"
    )

@router.get("/user-info")
async def get_auth_user_info(
    current_user: User = Depends(get_current_user_from_db)
):
    """Get authenticated user information"""
    return {
        "id": current_user.id,
        "auth0_sub": current_user.auth0_sub,
        "email": current_user.email,
        "email_verified": current_user.email_verified,
        "name": current_user.name,
        "given_name": current_user.given_name,
        "family_name": current_user.family_name,
        "nickname": current_user.nickname,
        "picture": current_user.picture,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "login_count": current_user.login_count,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

@router.post("/refresh-user")
async def refresh_user_from_auth0(
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """Refresh user data from Auth0"""
    try:
        # This would typically fetch fresh data from Auth0
        # For now, we'll just update the last_login timestamp
        current_user.last_login = datetime.now()
        db.commit()
        db.refresh(current_user)
        
        return {
            "message": "User data refreshed successfully",
            "user": current_user.to_session_dict()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to refresh user data: {str(e)}"
        )

@router.get("/check-auth")
async def check_authentication(
    current_user: User = Depends(get_current_user_from_db)
):
    """Simple endpoint to check if user is authenticated"""
    return {
        "authenticated": True,
        "user_id": current_user.id,
        "email": current_user.email,
        "is_premium": current_user.is_premium
    }
