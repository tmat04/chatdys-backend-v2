from sqlalchemy import Column, String, Integer, DateTime, Text, JSON, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database.connection import Base
from typing import Dict, Any, List
import uuid

class Conversation(Base):
    __tablename__ = "conversations"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # User relationship
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Conversation metadata
    title = Column(String, nullable=True)  # Auto-generated or user-set title
    summary = Column(Text, nullable=True)  # AI-generated summary
    
    # Conversation state
    is_active = Column(Boolean, default=True)
    message_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_message_at = Column(DateTime, nullable=True)
    
    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Relationship to messages
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id}, messages={self.message_count})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert conversation to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "summary": self.summary,
            "is_active": self.is_active,
            "message_count": self.message_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None
        }

    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert conversation to summary dictionary (for lists)"""
        return {
            "id": self.id,
            "title": self.title or "Untitled Conversation",
            "message_count": self.message_count,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Message(Base):
    __tablename__ = "messages"

    # Primary key
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Relationships
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Message content
    role = Column(String, nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    
    # Message metadata
    token_count = Column(Integer, nullable=True)
    model_used = Column(String, nullable=True)  # e.g., 'gpt-4', 'gpt-3.5-turbo'
    
    # Sources and references (for AI responses)
    sources = Column(JSON, nullable=True)  # List of source documents/URLs
    confidence_score = Column(Integer, nullable=True)  # 1-100 confidence rating
    
    # Processing metadata
    processing_time = Column(Integer, nullable=True)  # milliseconds
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    
    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, conversation_id={self.conversation_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary"""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "role": self.role,
            "content": self.content,
            "token_count": self.token_count,
            "model_used": self.model_used,
            "sources": self.sources,
            "confidence_score": self.confidence_score,
            "processing_time": self.processing_time,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def to_chat_dict(self) -> Dict[str, Any]:
        """Convert message to chat format (simplified)"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "sources": self.sources,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
