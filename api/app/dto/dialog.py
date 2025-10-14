from datetime import datetime

from pydantic import BaseModel
from tortoise_serializer import ContextType, Serializer

from app.common.models import enums, orm


class DialogOut(Serializer):
    id: int
    status: enums.DialogStatus
    recipient: str
    started_at: datetime

    @classmethod
    async def resolve_recipient(cls, instance: orm.Dialog, context: ContextType) -> str:
        return instance.recipient.username


class DialogMessageOut(BaseModel):
    sender: enums.MessageSender
    text: str
