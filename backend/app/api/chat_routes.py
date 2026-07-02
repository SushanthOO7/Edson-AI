from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/ask")
async def ask_chatbot() -> dict[str, str]:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="The IT Help Chatbot route is reserved for a later phase.",
    )
