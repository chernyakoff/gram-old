import logging
import tomllib
from typing import Self

import yaml
from pydantic import BaseModel, Field, PostgresDsn
from tortoise import BaseDBAsyncClient, Tortoise

logger = logging.getLogger(__name__)


class Hatchet(BaseModel):
    token: str
    host_port: str


class S3(BaseModel):
    access_key: str
    secret_key: str
    endpoint_url: str


class DatabaseOptions(BaseModel):
    host: str
    port: int
    user: str = Field(alias="username")
    password: str
    database: str


class Postgres(BaseModel):
    dsn: PostgresDsn = Field()

    @property
    def options(self) -> DatabaseOptions:
        return DatabaseOptions(**self.dsn.hosts()[0], database=self.dsn.path.strip("/"))  # type: ignore


class IpInfo(BaseModel):
    token: str


class Openai(BaseModel):
    api_key: str
    model: str
    base_url: str | None
    timeout: int | None = 180


class Settings(BaseModel):
    hatchet: Hatchet
    postgres: Postgres
    ipinfo: IpInfo
    s3: S3
    openai: Openai

    @classmethod
    def create(cls, path="config.yml") -> Self:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)


class WorkerConfig(BaseModel):
    name: str
    slots: int


def get_worker_config() -> WorkerConfig:
    with open("pyproject.toml", "rb") as f:
        data = tomllib.load(f)
    return WorkerConfig(**data["tool"]["worker"])


config = Settings.create()
worker_config = get_worker_config()


tortoise_config = {
    "connections": {
        "default": config.postgres.dsn.unicode_string(),
    },
    "apps": {
        "models": {
            "models": ["app.common.models.orm"],
            "default_connection": "default",
        },
    },
}


async def init_db() -> BaseDBAsyncClient:
    await Tortoise.init(config=tortoise_config, timezone="Europe/Moscow", use_tz=False)
    return Tortoise.get_connection("default")


async def shutdown_db() -> None:
    await Tortoise.close_connections()
