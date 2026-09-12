from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.agent.agent import ask_ai
from app.core.security import UserContext, get_current_user

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    response: str


@router.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    context: UserContext = Depends(get_current_user),
):
    ai_response = ask_ai(request.message, context.hotel_id)

    return ChatResponse(response=ai_response)
