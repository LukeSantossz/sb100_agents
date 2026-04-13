from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])

@router.get("/")
async def chat(question: str):
    return {"answer": "Isso é um teste"}