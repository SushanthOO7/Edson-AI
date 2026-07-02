from pydantic import BaseModel


class ChatAskRequest(BaseModel):
    question: str


class ChatAskResponse(BaseModel):
    answer: str
    sources: list[dict] = []
