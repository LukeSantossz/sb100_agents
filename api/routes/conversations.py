"""Routes to manage user conversations."""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.dependencies import verify_token
from core.schemas import ConversationResponse
from database.db import get_db
from database.models import Conversation, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=list[ConversationResponse])
def list_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(verify_token),
) -> list[Conversation]:
    """Retrieve all conversations for the authenticated user, sorted by created_at desc."""
    logger.info(
        "conversations.list",
        extra={"username": current_user.username, "user_id": current_user.id},
    )
    conversations = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .all()
    )
    return conversations
