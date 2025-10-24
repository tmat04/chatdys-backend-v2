from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import os
from datetime import datetime
from contextlib import asynccontextmanager

# Import route modules
from api.auth_routes import router as auth_router
from api.user_routes import router as user_router
from api.chat_routes import router as chat_router
from api.payment_routes import router as payment_router
from api.hubspot_routes import router as hubspot_router

# Import database and auth
from database.connection import init_db, close_db
from auth.auth0_manager import Auth0Manager

# Initialize Auth0 manager
auth0_manager = Auth0Manager()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    print("✅ Database initialized")
    print("✅ ChatDys Backend started successfully")
    print(f"🔧 Environment: {os.getenv('ENVIRONMENT', 'development')}")
    print(f"🔧 Auth0 Domain: {os.getenv('AUTH0_DOMAIN')}")
    print(f"🔧 HubSpot Integration: {'Enabled' if os.getenv('HUBSPOT_ACCESS_TOKEN') else 'Disabled'}")
    yield
    # Shutdown
    await close_db()
    print("🔄 Database connections closed")

# Create FastAPI app
app = FastAPI(
    title="ChatDys Backend API",
    description="Backend API for ChatDys - AI Assistant for Dysautonomia and Long Covid",
    version="1.0.0",
    lifespan=lifespan
)

# Get allowed origins from environment variable
allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
if allowed_origins_env:
    # Split by comma and strip whitespace
    allowed_origins = [origin.strip() for origin in allowed_origins_env.split(",") if origin.strip()]
else:
    # Default origins if environment variable is not set
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://chatdys.com",
        "https://www.chatdys.com"
    ]

print(f"🌐 CORS allowed origins: {allowed_origins}")

# CORS middleware with environment-based configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Accept",
        "Accept-Language",
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Access-Control-Request-Method",
        "Access-Control-Request-Headers"
    ],
    expose_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Validate Auth0 token and return user info"""
    try:
        token = credentials.credentials
        user_info = await auth0_manager.validate_token(token)
        return user_info
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication: {str(e)}")

# Health check endpoint
@app.get("/")
async def root():
    return {
        "message": "ChatDys Backend API",
        "status": "healthy",
        "version": "1.0.0",
        "cors_origins": allowed_origins,
        "features": {
            "auth0": True,
            "hubspot": bool(os.getenv("HUBSPOT_ACCESS_TOKEN")),
            "stripe": bool(os.getenv("STRIPE_SECRET_KEY")),
            "openai": bool(os.getenv("OPENAI_API_KEY"))
        }
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "message": "ChatDys Backend is running",
        "version": "1.0.0",
        "cors_configured": True,
        "allowed_origins": allowed_origins,
        "timestamp": datetime.now().isoformat()
    }

# CORS test endpoint
@app.options("/{path:path}")
async def options_handler(request: Request):
    """Handle preflight OPTIONS requests"""
    return {
        "message": "CORS preflight handled",
        "method": "OPTIONS",
        "path": request.url.path
    }

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/api/user", tags=["User Management"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(payment_router, prefix="/api/payments", tags=["Payments"])
app.include_router(hubspot_router, prefix="/api/hubspot", tags=["HubSpot CRM"])

# Make auth0_manager available to routes
app.state.auth0_manager = auth0_manager

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )