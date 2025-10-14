from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel

from database.connection import get_db
from models.user import User
from models.conversation import Conversation, Message
from api.user_routes import get_current_user_from_db
from chat.chat_service import ChatService
from config.settings import settings

router = APIRouter()

# Initialize chat service
chat_service = ChatService()

# Pydantic models
class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    conversation_id: str
    message_id: str
    sources: Optional[List[Dict[str, Any]]] = None
    confidence_score: Optional[int] = None
    processing_time: Optional[int] = None

class ConversationListResponse(BaseModel):
    conversations: List[Dict[str, Any]]
    total: int

@router.post("/query", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """Send a chat message and get AI response"""
    
    # Check if user can ask questions
    if not current_user.can_ask_questions(settings.FREE_USER_DAILY_LIMIT):
        raise HTTPException(
            status_code=429,
            detail="Daily question limit reached. Upgrade to Premium for unlimited questions."
        )
    
    # Validate question length
    if len(request.question.strip()) == 0:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty"
        )
    
    if len(request.question) > 2000:
        raise HTTPException(
            status_code=400,
            detail="Question too long. Maximum 2000 characters allowed."
        )
    
    try:
        start_time = datetime.now()
        
        # Get or create conversation
        conversation = None
        if request.conversation_id:
            conversation = db.query(Conversation).filter(
                Conversation.id == request.conversation_id,
                Conversation.user_id == current_user.id,
                Conversation.is_active == True
            ).first()
        
        if not conversation:
            # Create new conversation
            conversation = Conversation(
                user_id=current_user.id,
                title=request.question[:50] + "..." if len(request.question) > 50 else request.question
            )
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
        
        # Save user message
        user_message = Message(
            conversation_id=conversation.id,
            user_id=current_user.id,
            role="user",
            content=request.question
        )
        db.add(user_message)
        
        # Get AI response
        ai_response = await chat_service.get_response(
            question=request.question,
            user_id=current_user.id,
            conversation_history=get_conversation_history(conversation.id, db)
        )
        
        # Calculate processing time
        processing_time = int((datetime.now() - start_time).total_seconds() * 1000)
        
        # Save AI message
        ai_message = Message(
            conversation_id=conversation.id,
            user_id=current_user.id,
            role="assistant",
            content=ai_response.get("answer", "I apologize, but I couldn't generate a response."),
            sources=ai_response.get("sources"),
            confidence_score=ai_response.get("confidence_score"),
            processing_time=processing_time,
            model_used=ai_response.get("model_used", "gpt-4")
        )
        db.add(ai_message)
        
        # Update conversation
        conversation.message_count += 2  # User + AI message
        conversation.last_message_at = datetime.now()
        conversation.updated_at = datetime.now()
        
        # Update user stats (this will be handled by the increment endpoint)
        # But we need to increment total conversations if it's a new conversation
        if conversation.message_count == 2:  # First messages in conversation
            current_user.total_conversations += 1
        
        db.commit()
        db.refresh(ai_message)
        
        return ChatResponse(
            answer=ai_message.content,
            conversation_id=conversation.id,
            message_id=ai_message.id,
            sources=ai_message.sources,
            confidence_score=ai_message.confidence_score,
            processing_time=ai_message.processing_time
        )
        
    except Exception as e:
        db.rollback()
        print(f"❌ Chat error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process message: {str(e)}"
        )

@router.get("/conversations", response_model=ConversationListResponse)
async def get_conversations(
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """Get user's conversation history"""
    
    # Only premium users can access conversation history
    if not current_user.is_premium:
        raise HTTPException(
            status_code=403,
            detail="Conversation history is a premium feature. Please upgrade to access your chat history."
        )
    
    # Get conversations
    conversations = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_active == True
    ).order_by(Conversation.updated_at.desc()).offset(offset).limit(limit).all()
    
    # Get total count
    total = db.query(Conversation).filter(
        Conversation.user_id == current_user.id,
        Conversation.is_active == True
    ).count()
    
    return ConversationListResponse(
        conversations=[conv.to_summary_dict() for conv in conversations],
        total=total
    )

@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """Get specific conversation with messages"""
    
    # Only premium users can access conversation history
    if not current_user.is_premium:
        raise HTTPException(
            status_code=403,
            detail="Conversation history is a premium feature. Please upgrade to access your chat history."
        )
    
    # Get conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_active == True
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )
    
    # Get messages
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).all()
    
    return {
        "conversation": conversation.to_dict(),
        "messages": [msg.to_chat_dict() for msg in messages]
    }

@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """Delete a conversation"""
    
    # Get conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )
    
    # Soft delete
    conversation.is_active = False
    conversation.deleted_at = datetime.now()
    
    db.commit()
    
    return {"message": "Conversation deleted successfully"}

@router.put("/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str,
    title: str,
    current_user: User = Depends(get_current_user_from_db),
    db: Session = Depends(get_db)
):
    """Update conversation title"""
    
    # Get conversation
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.user_id == current_user.id,
        Conversation.is_active == True
    ).first()
    
    if not conversation:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found"
        )
    
    # Update title
    conversation.title = title[:100]  # Limit title length
    conversation.updated_at = datetime.now()
    
    db.commit()
    db.refresh(conversation)
    
    return {
        "message": "Title updated successfully",
        "conversation": conversation.to_dict()
    }

def get_conversation_history(conversation_id: str, db: Session) -> List[Dict[str, str]]:
    """Get conversation history for context"""
    messages = db.query(Message).filter(
        Message.conversation_id == conversation_id
    ).order_by(Message.created_at.asc()).limit(10).all()  # Last 10 messages for context
    
    return [
        {
            "role": msg.role,
            "content": msg.content
        }
        for msg in messages
    ]
