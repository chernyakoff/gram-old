# app/dto/project.py


from pydantic import BaseModel
from tortoise_serializer import Serializer



class ProjectBase(Serializer):
    id: int
    name: str


class ProjectStatusIn(BaseModel):
    status: bool


class ProjectShortOut(ProjectBase):
    status: bool


class SynonimizeIn(BaseModel):
    text: str


class SynonimizeOut(BaseModel):
    text: str


class ProjectFilesIn(BaseModel):
    project_id: int
    files: list[str]
