from fastapi import APIRouter
from core.schemas import ChatRequest
from core.schemas import ChatResponse

router = APIRouter(prefix="/chat", tags=["chat"])

@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    return ChatResponse(
        answer="Isso é um teste",
        hallucination_score=0.18
    )

