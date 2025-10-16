"""
HubSpot CRM Integration Service
Syncs ChatDys users to HubSpot for customer relationship management
"""

import requests
from typing import Dict, Any, Optional
from datetime import datetime
from config.settings import settings


class HubSpotService:
    """Service for integrating with HubSpot CRM"""
    
    def __init__(self):
        self.access_token = settings.HUBSPOT_ACCESS_TOKEN
        self.portal_id = settings.HUBSPOT_PORTAL_ID
        self.base_url = "https://api.hubapi.com"
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for HubSpot API requests"""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def create_or_update_contact(
        self,
        email: str,
        properties: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create or update a contact in HubSpot
        
        Args:
            email: Contact's email address (unique identifier)
            properties: Dictionary of contact properties
            
        Returns:
            Contact data from HubSpot or None if failed
        """
        try:
            if not self.access_token:
                print("⚠️ HubSpot access token not configured")
                return None
            
            # Prepare contact data
            contact_data = {
                "properties": {
                    "email": email,
                    **properties
                }
            }
            
            # Try to create contact first
            url = f"{self.base_url}/crm/v3/objects/contacts"
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=contact_data,
                timeout=10
            )
            
            if response.status_code == 201:
                print(f"✅ Created HubSpot contact: {email}")
                return response.json()
            
            elif response.status_code == 409:
                # Contact already exists, update instead
                print(f"📝 Contact exists, updating: {email}")
                return await self._update_contact_by_email(email, properties)
            
            else:
                print(f"❌ HubSpot API error: {response.status_code} - {response.text}")
                return None
                
        except requests.RequestException as e:
            print(f"❌ HubSpot request failed: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ HubSpot sync error: {str(e)}")
            return None
    
    async def _update_contact_by_email(
        self,
        email: str,
        properties: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update existing contact by email"""
        try:
            # First, get contact ID by email
            search_url = f"{self.base_url}/crm/v3/objects/contacts/search"
            search_data = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "email",
                        "operator": "EQ",
                        "value": email
                    }]
                }]
            }
            
            search_response = requests.post(
                search_url,
                headers=self._get_headers(),
                json=search_data,
                timeout=10
            )
            
            if search_response.status_code != 200:
                print(f"❌ Failed to search for contact: {search_response.text}")
                return None
            
            search_results = search_response.json()
            if not search_results.get("results"):
                print(f"⚠️ Contact not found: {email}")
                return None
            
            contact_id = search_results["results"][0]["id"]
            
            # Update the contact
            update_url = f"{self.base_url}/crm/v3/objects/contacts/{contact_id}"
            update_data = {"properties": properties}
            
            update_response = requests.patch(
                update_url,
                headers=self._get_headers(),
                json=update_data,
                timeout=10
            )
            
            if update_response.status_code == 200:
                print(f"✅ Updated HubSpot contact: {email}")
                return update_response.json()
            else:
                print(f"❌ Failed to update contact: {update_response.text}")
                return None
                
        except Exception as e:
            print(f"❌ Error updating contact: {str(e)}")
            return None
    
    async def sync_user(self, user: Any) -> bool:
        """
        Sync a ChatDys user to HubSpot
        
        Args:
            user: User model instance
            
        Returns:
            True if sync successful, False otherwise
        """
        try:
            # Prepare HubSpot properties
            properties = {
                "firstname": user.given_name or "",
                "lastname": user.family_name or "",
                "phone": user.preferences.get("phone_number", "") if user.preferences else "",
                "city": user.preferences.get("location", "") if user.preferences else "",
                
                # Lifecycle and lead status
                "lifecyclestage": "customer" if user.is_premium else "lead",
                "hs_lead_status": "OPEN" if user.profile_completed else "NEW",
                
                # Custom ChatDys properties (you need to create these in HubSpot first)
                "chatdys_user_id": user.id,
                "chatdys_auth0_sub": user.auth0_sub,
                "chatdys_signup_date": user.created_at.isoformat() if user.created_at else "",
                "chatdys_last_login": user.last_login.isoformat() if user.last_login else "",
                "chatdys_login_count": str(user.login_count),
                "chatdys_question_count": str(user.question_count),
                "chatdys_daily_question_count": str(user.daily_question_count),
                "chatdys_is_premium": "true" if user.is_premium else "false",
                "chatdys_subscription_status": user.subscription_status,
                "chatdys_profile_completed": "true" if user.profile_completed else "false",
                "chatdys_onboarding_completed": "true" if user.onboarding_completed else "false",
            }
            
            # Add health conditions if available
            if user.conditions:
                properties["chatdys_health_conditions"] = ", ".join(user.conditions)
            
            # Add how they heard about us
            if user.preferences and user.preferences.get("how_heard_about_us"):
                properties["how_did_you_hear_about_us"] = user.preferences["how_heard_about_us"]
            
            # Sync to HubSpot
            result = await self.create_or_update_contact(user.email, properties)
            
            if result:
                # Update user record with HubSpot contact ID
                if "id" in result:
                    user.hubspot_contact_id = result["id"]
                    user.hubspot_synced = True
                    user.hubspot_last_sync = datetime.now()
                return True
            
            return False
            
        except Exception as e:
            print(f"❌ Error syncing user to HubSpot: {str(e)}")
            return False
    
    async def track_event(
        self,
        email: str,
        event_name: str,
        properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track a custom event in HubSpot
        
        Args:
            email: Contact's email
            event_name: Name of the event
            properties: Optional event properties
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.access_token:
                return False
            
            # HubSpot timeline events API
            url = f"{self.base_url}/crm/v3/timeline/events"
            
            event_data = {
                "eventTemplateId": event_name,
                "email": email,
                "tokens": properties or {},
                "timestamp": datetime.now().isoformat()
            }
            
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=event_data,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                print(f"✅ Tracked event '{event_name}' for {email}")
                return True
            else:
                print(f"⚠️ Failed to track event: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error tracking event: {str(e)}")
            return False
    
    async def add_to_list(self, contact_id: str, list_id: str) -> bool:
        """
        Add a contact to a HubSpot list
        
        Args:
            contact_id: HubSpot contact ID
            list_id: HubSpot list ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not self.access_token:
                return False
            
            url = f"{self.base_url}/contacts/v1/lists/{list_id}/add"
            data = {"vids": [int(contact_id)]}
            
            response = requests.post(
                url,
                headers=self._get_headers(),
                json=data,
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"✅ Added contact {contact_id} to list {list_id}")
                return True
            else:
                print(f"⚠️ Failed to add to list: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error adding to list: {str(e)}")
            return False


# Create global instance
hubspot_service = HubSpotService()

