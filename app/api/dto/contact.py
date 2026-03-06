from datetime import datetime

from pydantic import BaseModel
from tortoise_serializer import Serializer

from api.dto.project import ProjectBase


class ContactBase(Serializer):
    uid: int
    id: int | None
    username: str
    first_name: str | None
    last_name: str | None
    created_at: datetime


class ContactOut(ContactBase):
    project: ProjectBase


class ContactsBulkCreateIn(BaseModel):
    project_id: int
    usernames: list[str]


class ContactsBulkCreateOut(BaseModel):
    total: int
    added: int
