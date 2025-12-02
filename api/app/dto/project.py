# app/dto/project.py


from pydantic import BaseModel
from tortoise_serializer import Serializer



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


class PromptIn(BaseModel):
    role: str
    context: str
    init: str
    engage: str
    offer: str
    closing: str
    instruction: str
    rules: str
    transitions: str


class PromptOut(Serializer):
    role: str
    context: str
    init: str
    engage: str
    offer: str
    closing: str
    instruction: str
    rules: str
    transitions: str


class ProjectBase(Serializer):
    id: int
    name: str


class ProjectStatusIn(BaseModel):
    status: bool


class ProjectIn(BaseModel):
    name: str
    dialog_limit: int
    send_time_start: int
    send_time_end: int
    first_message: str
    brief: BriefIn
    prompt: PromptIn
    advanced_mode: bool


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
    prompt: PromptOut


def create_default_project() -> ProjectIn:
    return ProjectIn(
        name="Мой проект",
        dialog_limit=50,
        send_time_start=0,
        send_time_end=23,
        first_message="",
        advanced_mode=False,
        prompt=PromptIn(
            role="",
            context="",
            init="",
            engage="",
            offer="",
            closing="",
            instruction="",
            rules="",
            transitions="",
        ),
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


class SynonimizeIn(BaseModel):
    text: str


class SynonimizeOut(BaseModel):
    text: str
