from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any

from .brain import personal_brain

# API routes for Personal AI interactions
router = APIRouter(prefix="/api/personal", tags=["personal_ai"])

class ChatRequest(BaseModel):
    message: str
    requires_online: bool = False

class ChatResponse(BaseModel):
    response: str
    source: str

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Entry point for the Personal AI chat interface."""
    try:
        reply = personal_brain.route(request.message, requires_online=request.requires_online)
        return ChatResponse(
            response=reply,
            source="LocalBrain" if hasattr(personal_brain, "local") and personal_brain.local.ready else "GeminiFallback"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

