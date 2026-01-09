# app/dto/project.py


from pydantic import BaseModel
from tortoise_serializer import ContextType, Serializer

from app.common.models import orm
from app.common.utils.prompt import DEFAULT_SKIP_OPTIONS, ProjectSkipOptions


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


class PromptOut(Serializer):
    role: str
    context: str
    init: str
    engage: str
    offer: str
    closing: str
    instruction: str
    rules: str


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
    premium_required: bool
    brief: BriefIn
    prompt: PromptIn
    advanced_mode: bool
    skip_options: ProjectSkipOptions


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
    premium_required: bool
    brief: BriefOut
    prompt: PromptOut
    skip_options: ProjectSkipOptions

    @classmethod
    async def resolve_skip_options(
        cls, instance: orm.Project, context: ContextType
    ) -> ProjectSkipOptions:
        if not instance.skip_options:
            return DEFAULT_SKIP_OPTIONS
        return ProjectSkipOptions(**instance.skip_options)


def create_default_project() -> ProjectIn:
    return ProjectIn(
        name="Мой проект",
        dialog_limit=50,
        send_time_start=10,
        send_time_end=21,
        first_message="",
        advanced_mode=False,
        premium_required=True,
        skip_options=DEFAULT_SKIP_OPTIONS,
        prompt=PromptIn(
            role="",
            context="",
            init="",
            engage="",
            offer="",
            closing="",
            instruction="",
            rules="",
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
