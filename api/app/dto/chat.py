from enum import StrEnum

from pydantic import BaseModel


class MessageRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Message(BaseModel):
    role: MessageRole
    text: str


class ChatIn(BaseModel):
    project_id: int
    messages: list[Message]


class ChatOut(BaseModel):
    text: str
