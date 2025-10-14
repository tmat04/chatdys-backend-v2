from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn
import os
from contextlib import asynccontextmanager

# Import route modules
from api.auth_routes import router as auth_router
from api.user_routes import router as user_router
from api.chat_routes import router as chat_router
from api.payment_routes import router as payment_router

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

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://chatdys.com",
        "https://www.chatdys.com",
        "https://chatdys-frontend-q8fgjagpx-tmat04s-projects.vercel.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "chatdys-backend",
        "timestamp": "2025-10-13T14:30:00Z"
    }

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(user_router, prefix="/api/user", tags=["User Management"])
app.include_router(chat_router, prefix="/api", tags=["Chat"])
app.include_router(payment_router, prefix="/api/payments", tags=["Payments"])

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return {
        "error": True,
        "detail": exc.detail,
        "status_code": exc.status_code
    }

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return {
        "error": True,
        "detail": "Internal server error",
        "status_code": 500
    }

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )
