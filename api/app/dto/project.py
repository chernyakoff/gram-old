# app/dto/project.py

from pydantic import BaseModel
from tortoise_serializer import ContextType, Serializer

from app.common.models.orm import Brief, Project


class BriefIn(BaseModel):
    description: str
    offer: str
    client: str
    pains: str
    advantages: str
    mission: str
    focus: str


class BriefOut(Serializer):
    description: str
    offer: str
    client: str
    pains: str
    advantages: str
    mission: str
    focus: str


class ProjectBase(Serializer):
    id: int
    name: str
    prompt_exists: bool

    @classmethod
    async def resolve_prompt_exists(
        cls, instance: Project, context: ContextType
    ) -> bool:
        prompt = instance.prompt
        return bool(prompt)


class ProjectStatusIn(BaseModel):
    status: bool


class ProjectIn(BaseModel):
    name: str
    dialog_limit: int
    send_time_start: int
    send_time_end: int
    first_message: str
    brief: BriefIn


class ProjectShortOut(ProjectBase):
    status: bool


class ProjectOut(Serializer):
    id: int
    name: str
    dialog_limit: int
    send_time_start: int
    send_time_end: int
    first_message: str
    status: bool
    brief: BriefOut


async def create_default_project() -> ProjectIn:
    return ProjectIn(
        name="Мой проект",
        dialog_limit=50,
        send_time_start=0,
        send_time_end=23,
        first_message="",
        brief=BriefIn(
            description="",
            offer="",
            client="",
            pains="",
            advantages="",
            mission="",
            focus="",
        ),
    )
