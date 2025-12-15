from datetime import datetime

from pydantic import BaseModel
from tortoise_serializer import ContextType, Serializer

from app.common.models import enums, orm


class DialogOut(Serializer):
    id: int
    status: enums.DialogStatus
    recipient: str
    account: str
    project: str
    started_at: datetime

    @classmethod
    async def resolve_project(cls, instance: orm.Dialog, context: ContextType) -> str:
        return instance.recipient.mailing.project.name

    @classmethod
    async def resolve_account(cls, instance: orm.Dialog, context: ContextType) -> str:
        return instance.account.username

    @classmethod
    async def resolve_recipient(cls, instance: orm.Dialog, context: ContextType) -> str:
        return instance.recipient.username


class DialogMessageOut(BaseModel):
    sender: enums.MessageSender
    text: str
    ack: bool
    created_at: datetime


class DialogSystemMessageIn(BaseModel):
    dialog_id: int
    message: str
