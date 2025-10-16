"""
HubSpot Integration API Routes
Handles syncing users and events to HubSpot CRM
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel, EmailStr
from datetime import datetime

from database.connection import get_db
from models.user import User
from api.user_routes import get_current_user_from_db
from utils.hubspot_service import hubspot_service

router = APIRouter()


class HubSpotSyncRequest(BaseModel):
    """Request model for HubSpot contact sync"""
    email: EmailStr
    firstname: str = ""
    lastname: str = ""
    phone: str = ""
    lifecyclestage: str = "lead"
    hs_lead_status: str = "NEW"
    chatdys_user_id: str = ""
    chatdys_signup_date: str = ""
    chatdys_is_premium: str = "false"
    chatdys_question_count: int = 0


class HubSpotEventRequest(BaseModel):
    """Request model for tracking HubSpot events"""
    event_name: str
    properties: Dict[str, Any] = {}


@router.post("/sync-contact")
async def sync_contact_to_hubspot(
    sync_data: HubSpotSyncRequest,
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """
    Sync current user to HubSpot CRM
    This endpoint is called from the frontend after user completes onboarding
    """
    try:
        # Prepare properties for HubSpot
        properties = {
            "firstname": sync_data.firstname,
            "lastname": sync_data.lastname,
            "phone": sync_data.phone,
            "lifecyclestage": sync_data.lifecyclestage,
            "hs_lead_status": sync_data.hs_lead_status,
            "chatdys_user_id": sync_data.chatdys_user_id or current_user.id,
            "chatdys_auth0_sub": current_user.auth0_sub,
            "chatdys_signup_date": sync_data.chatdys_signup_date or (
                current_user.created_at.isoformat() if current_user.created_at else ""
            ),
            "chatdys_last_login": current_user.last_login.isoformat() if current_user.last_login else "",
            "chatdys_login_count": str(current_user.login_count),
            "chatdys_question_count": str(sync_data.chatdys_question_count or current_user.question_count),
            "chatdys_is_premium": sync_data.chatdys_is_premium,
            "chatdys_subscription_status": current_user.subscription_status,
            "chatdys_profile_completed": "true" if current_user.profile_completed else "false",
        }
        
        # Add health conditions if available
        if current_user.conditions:
            properties["chatdys_health_conditions"] = ", ".join(current_user.conditions)
        
        # Add how they heard about us
        if current_user.preferences and current_user.preferences.get("how_heard_about_us"):
            properties["how_did_you_hear_about_us"] = current_user.preferences["how_heard_about_us"]
        
        # Sync to HubSpot
        result = await hubspot_service.create_or_update_contact(
            email=sync_data.email,
            properties=properties
        )
        
        if result:
            # Update user record
            if "id" in result:
                current_user.hubspot_contact_id = result["id"]
                current_user.hubspot_synced = True
                current_user.hubspot_last_sync = datetime.now()
                db.commit()
            
            return {
                "success": True,
                "message": "User synced to HubSpot successfully",
                "hubspot_contact_id": result.get("id")
            }
        else:
            return {
                "success": False,
                "message": "Failed to sync to HubSpot",
                "hubspot_contact_id": None
            }
            
    except Exception as e:
        print(f"❌ HubSpot sync error: {str(e)}")
        # Don't fail the request if HubSpot sync fails
        return {
            "success": False,
            "message": f"HubSpot sync error: {str(e)}",
            "hubspot_contact_id": None
        }


@router.post("/sync-current-user")
async def sync_current_user_to_hubspot(
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """
    Sync current authenticated user to HubSpot
    Uses user data from database
    """
    try:
        success = await hubspot_service.sync_user(current_user)
        
        if success:
            db.commit()
            return {
                "success": True,
                "message": "User synced to HubSpot successfully",
                "hubspot_contact_id": current_user.hubspot_contact_id
            }
        else:
            return {
                "success": False,
                "message": "Failed to sync to HubSpot"
            }
            
    except Exception as e:
        print(f"❌ HubSpot sync error: {str(e)}")
        return {
            "success": False,
            "message": f"HubSpot sync error: {str(e)}"
        }


@router.post("/track-event")
async def track_hubspot_event(
    event_data: HubSpotEventRequest,
    current_user: User = Depends(get_current_user_from_db)
):
    """
    Track a custom event in HubSpot for the current user
    
    Example events:
    - "question_asked"
    - "premium_upgrade"
    - "profile_completed"
    - "conversation_started"
    """
    try:
        success = await hubspot_service.track_event(
            email=current_user.email,
            event_name=event_data.event_name,
            properties=event_data.properties
        )
        
        return {
            "success": success,
            "message": "Event tracked successfully" if success else "Failed to track event"
        }
        
    except Exception as e:
        print(f"❌ HubSpot event tracking error: {str(e)}")
        return {
            "success": False,
            "message": f"Event tracking error: {str(e)}"
        }


@router.get("/sync-status")
async def get_hubspot_sync_status(
    current_user: User = Depends(get_current_user_from_db)
):
    """
    Get HubSpot sync status for current user
    """
    return {
        "hubspot_synced": current_user.hubspot_synced,
        "hubspot_contact_id": current_user.hubspot_contact_id,
        "hubspot_last_sync": current_user.hubspot_last_sync.isoformat() if current_user.hubspot_last_sync else None
    }


@router.post("/force-sync-all-users")
async def force_sync_all_users(
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """
    Force sync all users to HubSpot
    (Admin only - you should add admin check here)
    """
    try:
        # TODO: Add admin permission check
        # if not current_user.is_admin:
        #     raise HTTPException(status_code=403, detail="Admin access required")
        
        users = db.query(User).filter(User.is_active == True).all()
        
        synced_count = 0
        failed_count = 0
        
        for user in users:
            try:
                success = await hubspot_service.sync_user(user)
                if success:
                    synced_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                print(f"❌ Failed to sync user {user.email}: {str(e)}")
                failed_count += 1
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Sync completed: {synced_count} successful, {failed_count} failed",
            "synced_count": synced_count,
            "failed_count": failed_count,
            "total_users": len(users)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Bulk sync failed: {str(e)}"
        )

