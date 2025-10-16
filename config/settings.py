import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # Auth0 Configuration
    AUTH0_DOMAIN: str = "dev-5040302010.us.auth0.com"
    AUTH0_CLIENT_ID: str = "fqzwP9fpJrY0c7FINxADguJhxjrOqnwV"
    AUTH0_CLIENT_SECRET: Optional[str] = None
    AUTH0_AUDIENCE: str = "https://api.chatdys.com/"
    
    # Database Configuration
    DATABASE_URL: str = "sqlite:///./chatdys.db"  # Default to SQLite for development
    
    # Supabase Configuration (if using)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_KEY: Optional[str] = None
    
    # HubSpot Configuration
    HUBSPOT_ACCESS_TOKEN: Optional[str] = None
    HUBSPOT_PORTAL_ID: Optional[str] = None
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = None
    
    # Stripe Configuration
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    
    # Application Settings
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Rate Limiting
    FREE_USER_DAILY_LIMIT: int = 5
    PREMIUM_USER_DAILY_LIMIT: int = 1000
    
    # CORS Settings - Can be a comma-separated string or list
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173,https://chatdys.com,https://www.chatdys.com"
    
    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    @field_validator('ALLOWED_ORIGINS', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v):
        """Parse ALLOWED_ORIGINS from string or list"""
        if isinstance(v, str):
            # If it's a string, split by comma and strip whitespace
            return v
        elif isinstance(v, list):
            # If it's already a list, join it into a string
            return ','.join(v)
        return v
    
    def get_allowed_origins_list(self) -> List[str]:
        """Get ALLOWED_ORIGINS as a list"""
        if isinstance(self.ALLOWED_ORIGINS, str):
            return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(',') if origin.strip()]
        return self.ALLOWED_ORIGINS
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()

# Validation
def validate_settings():
    """Validate required settings"""
    required_settings = [
        "AUTH0_DOMAIN",
        "AUTH0_CLIENT_ID",
        "AUTH0_AUDIENCE"
    ]
    
    missing = []
    for setting in required_settings:
        if not getattr(settings, setting):
            missing.append(setting)
    
    if missing:
        raise ValueError(f"Missing required settings: {', '.join(missing)}")
    
    return True

# Export settings
__all__ = ["settings", "validate_settings"]
