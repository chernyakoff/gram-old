from pydantic import BaseModel
from tortoise_serializer import Serializer


class ProjectBase(Serializer):
    id: int
    name: str


class ProjectStatusIn(BaseModel):
    status: bool


class ProjectIn(Serializer):
    name: str
    dialog_limit: int
    out_daily_limit: int
    send_time_start: int
    send_time_end: int
    first_message: str
    prompt: str


class ProjectShortOut(ProjectBase):
    status: bool


class ProjectOut(ProjectIn):
    id: int
