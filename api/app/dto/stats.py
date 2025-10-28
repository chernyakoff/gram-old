from datetime import date, datetime, time
from typing import Optional

from pydantic import BaseModel, Field
from tortoise.expressions import Q


class StatsIn(BaseModel):
    date_from: date = Field(..., description="Дата начала периода (YYYY-MM-DD)")
    date_to: date = Field(..., description="Дата конца периода (YYYY-MM-DD)")
    project_id: Optional[int] = Field(None, description="ID проекта")
    account_id: Optional[int] = Field(None, description="ID аккаунта")
    mailing_id: Optional[int] = Field(None, description="ID рассылки")

    def to_filter_q(self, user_id: int) -> Q:
        """Преобразуем в Q-фильтр для Tortoise"""
        start_dt = datetime.combine(self.date_from, time.min)
        end_dt = datetime.combine(self.date_to, time.max)
        q = Q(user_id=user_id, started_at__gte=start_dt, started_at__lte=end_dt)
        if self.project_id:
            q &= Q(account__project_id=self.project_id)
        if self.account_id:
            q &= Q(account_id=self.account_id)
        if self.mailing_id:
            q &= Q(recipient__mailing_id=self.mailing_id)
        return q


class StatsOut(BaseModel):
    init: list[int]
    engage: list[int]
    offer: list[int]
    closing: list[int]
