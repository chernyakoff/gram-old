from pydantic import BaseModel
from tortoise_serializer import Serializer

from app.common.models.orm import Project
from app.common.utils.prompt import TRANSITIONS, get_default_prompt


class ProjectBase(Serializer):
    id: int
    name: str


class ProjectStatusIn(BaseModel):
    status: bool


class ProjectIn(BaseModel):
    name: str
    dialog_limit: int
    out_daily_limit: int
    send_time_start: int
    send_time_end: int
    first_message: str
    role: str
    context: str
    init: str
    engage: str
    offer: str
    closing: str
    instruction: str
    rules: str

    async def to_model_dict(self) -> dict:
        data = self.model_dump()  # берём все поля сериализатора
        prompt_fields = [
            "role",
            "context",
            "init",
            "engage",
            "offer",
            "closing",
            "instruction",
            "rules",
        ]
        prompt_data = {key: data.pop(key) for key in prompt_fields}
        prompt_data["transitions"] = TRANSITIONS
        data["prompt"] = prompt_data
        return data

    @classmethod
    def from_orm(cls, project: Project):
        prompt = project.prompt or {}
        kwargs = dict(
            name=project.name,
            dialog_limit=project.dialog_limit,
            out_daily_limit=project.out_daily_limit,
            send_time_start=project.send_time_start,
            send_time_end=project.send_time_end,
            first_message=project.first_message,
            role=prompt.get("role", ""),
            context=prompt.get("context", ""),
            init=prompt.get("init", ""),
            engage=prompt.get("engage", ""),
            offer=prompt.get("offer", ""),
            closing=prompt.get("closing", ""),
            instruction=prompt.get("instruction", ""),
            rules=prompt.get("rules", ""),
        )
        if "id" in cls.__annotations__:
            kwargs["id"] = project.id
        return cls(**kwargs)  # type: ignore


class ProjectShortOut(ProjectBase):
    status: bool


class ProjectOut(ProjectIn):
    id: int


async def create_default_project() -> ProjectIn:
    project = {
        "name": "Мой проект",
        "dialog_limit": 50,
        "out_daily_limit": 5,
        "send_time_start": 0,
        "send_time_end": 23,
    }
    prompt = await get_default_prompt()
    return ProjectIn(**(project | prompt))
