from pydantic import BaseModel


class WorkflowOut(BaseModel):
    id: str


class PresignedOut(BaseModel):
    s3path: str
    url: str


class PresignedIn(BaseModel):
    path: str  # формат: <bucket>/<folder1>/<folder2>
    filename: str
