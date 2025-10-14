from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from config.settings import settings
import asyncio
from typing import AsyncGenerator

# Create database engine
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite configuration
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 20
        },
        poolclass=StaticPool,
        echo=settings.DEBUG
    )
else:
    # PostgreSQL configuration
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        echo=settings.DEBUG
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()

# Metadata for table creation
metadata = MetaData()

class DatabaseManager:
    """Database connection manager"""
    
    def __init__(self):
        self.engine = engine
        self.SessionLocal = SessionLocal
        self.Base = Base

    async def init_db(self):
        """Initialize database and create tables"""
        try:
            # Import all models to ensure they're registered
            from models.user import User
            from models.conversation import Conversation, Message
            
            # Create all tables
            Base.metadata.create_all(bind=engine)
            print("✅ Database tables created successfully")
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            raise

    async def close_db(self):
        """Close database connections"""
        try:
            engine.dispose()
            print("✅ Database connections closed")
        except Exception as e:
            print(f"❌ Error closing database: {e}")

    def get_session(self) -> Session:
        """Get database session"""
        return SessionLocal()

    async def get_async_session(self) -> AsyncGenerator[Session, None]:
        """Get async database session"""
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

# Create global database manager
db_manager = DatabaseManager()

# Dependency for FastAPI
def get_db() -> Session:
    """FastAPI dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Async version
async def get_async_db() -> AsyncGenerator[Session, None]:
    """Async FastAPI dependency to get database session"""
    async for session in db_manager.get_async_session():
        yield session

# Initialize and close functions
async def init_db():
    """Initialize database"""
    await db_manager.init_db()

async def close_db():
    """Close database"""
    await db_manager.close_db()

# Export commonly used items
__all__ = [
    "engine",
    "SessionLocal", 
    "Base",
    "get_db",
    "get_async_db",
    "init_db",
    "close_db",
    "db_manager"
]
