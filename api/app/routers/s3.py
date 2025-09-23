from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.common.utils.s3 import AsyncS3Client
from app.routers.auth import get_current_user

router = APIRouter(prefix="/s3", tags=["s3"])


class PresignedOut(BaseModel):
    s3path: str
    url: str


class PresignedIn(BaseModel):
    path: str  # формат: <bucket>/<folder1>/<folder2>
    filename: str


def build_storage_path(input: PresignedIn, user_id: int) -> str:
    filename = f"{uuid4()}{Path(input.filename).suffix.lower()}"
    segments = input.path.strip("/").split("/")
    if not segments:
        raise ValueError("Path must not be empty")
    first = segments[0]
    if first == "service":
        return "/".join(["service", str(user_id), filename])
    elif first == "media":
        if len(segments) == 1:
            return "/".join(["media", str(user_id), filename])
        else:
            return "/".join(["media", str(user_id)] + segments[1:] + [filename])
    else:
        raise ValueError("Path must start with 'service' or 'media'")


@router.post("/presigned", response_model=PresignedOut)
async def presigned(input: PresignedIn, user=Depends(get_current_user)):
    path = build_storage_path(input, user.id)
    async with AsyncS3Client() as s3:
        try:
            url = await s3.presigned_put_url(path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"S3 error: {e}")

    return PresignedOut(s3path=path, url=url)
