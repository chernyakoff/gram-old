from datetime import datetime

from tortoise_serializer import Serializer

from models import orm
from utils.validators import is_valid_telegram_username
from api.dto.project import ProjectBase


class MailingOut(Serializer):
    id: int
    project: ProjectBase
    name: str
    status: orm.MailingStatus
    started_at: datetime | None
    sent_count: int  # сколько RecipientStatus.SEND
    total_count: int  # всего Recipient
    failed_count: int  # сколько RecipientStatus.FAILED
    active: bool


class MailingListOut(Serializer):
    id: int
    name: str


class MailingIn(Serializer):
    name: str
    project_id: int
    recipients: list[str]

    async def create_tortoise_instance(self, model, **kwargs):
        usernames = []
        for u in self.recipients:
            username = u.removeprefix("https://t.me/").removeprefix("@")
            if is_valid_telegram_username(username):
                usernames.append(username)

        if usernames:
            mailing = await model.create(
                **self.model_dump(exclude={"recipients"}), **kwargs
            )
            objs = [
                orm.Recipient(
                    mailing=mailing,
                    username=username,
                    status=orm.RecipientStatus.PENDING,
                )
                for username in usernames
            ]

        await orm.Recipient.bulk_create(objs, ignore_conflicts=True, batch_size=1000)

        return mailing
