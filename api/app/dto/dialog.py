from datetime import datetime

from pydantic import BaseModel
from tortoise_serializer import ContextType, Serializer

from app.common.models import enums, orm


class DialogOut(BaseModel):
    id: int
    status: enums.DialogStatus
    recipient: str
    account: str
    project: str
    started_at: datetime


class DialogMessageOut(BaseModel):
    sender: enums.MessageSender
    text: str
    ack: bool
    created_at: datetime


class DialogSystemMessageIn(BaseModel):
    dialog_id: int
    message: str
