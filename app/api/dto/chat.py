from enum import StrEnum

from pydantic import BaseModel

from models.orm import DialogStatus


class MessageRole(StrEnum):
    user = "user"
    assistant = "assistant"
    system = "system"


class Message(BaseModel):
    role: MessageRole
    text: str


class ChatIn(BaseModel):
    status: DialogStatus = DialogStatus.INIT
    project_id: int
    messages: list[Message]


class ToolEvent(BaseModel):
    tool: str
    arguments: dict
    result: object


class ChatOut(BaseModel):
    text: str
    status: DialogStatus
    tool_events: list[ToolEvent] | None = None
    warnings: list[str] | None = None
