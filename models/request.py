from pydantic import BaseModel


class ChatBotRequest(BaseModel):
    session_id: str
    prompt: str
