from pydantic import BaseModel


class ChatBotRequest(BaseModel):
    session_id: str
    prompt: str


class HistoryRequest(BaseModel):
    session_id: str
