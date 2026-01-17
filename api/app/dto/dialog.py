from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from tortoise.expressions import Q
from tortoise_serializer import Serializer

from app.common.models import enums


class DialogIn(BaseModel):
    project_id: Optional[int] = Field(None, description="ID проекта")
    account_id: Optional[int] = Field(None, description="ID аккаунта")
    mailing_id: Optional[int] = Field(None, description="ID рассылки")

    def to_filter_q(self, user_id: int) -> Q:
        q = Q(
            mailing__user_id=user_id,
        )
        if self.project_id:
            q &= Q(mailing__project_id=self.project_id)

        if self.account_id:
            q &= Q(account_id=self.account_id)

        if self.mailing_id:
            q &= Q(mailing_id=self.mailing_id)

        return q


class DialogOut(Serializer):
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
