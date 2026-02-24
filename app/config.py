import logging
import tomllib
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, Field, PostgresDsn, SecretStr
from tortoise import BaseDBAsyncClient, Tortoise

logger = logging.getLogger(__name__)


class Jwt(BaseModel):
    expire_seconds: int
    refresh_expire_days: int
    secret: str
    algorithm: str


class Bot(BaseModel):
    token: SecretStr

    @property
    def id(self) -> int:
        return int(self.token.get_secret_value().split(":")[0])


class Api(BaseModel):
    port: int = Field(default=8833)
    host: str = Field(default="localhost")
    url: str | None = None
    jwt: Jwt
    bot: Bot


class Web(BaseModel):
    url: str


class Hatchet(BaseModel):
    token: str
    host_port: str


class DatabaseOptions(BaseModel):
    host: str
    port: int
    user: str = Field(alias="username")
    password: str
    database: str


class S3Config(BaseModel):
    access_key: str
    secret_key: str
    endpoint_url: str
    public_endpoint_url: str


class OpenRouter(BaseModel):
    manager_api_key: str
    proxy: str


class TgSessions(BaseModel):
    url: str


class Postgres(BaseModel):
    dsn: PostgresDsn = Field()

    @property
    def options(self) -> DatabaseOptions:
        return DatabaseOptions(**self.dsn.hosts()[0], database=self.dsn.path.strip("/"))  # type: ignore


class IpInfo(BaseModel):
    token: str


class Settings(BaseModel):
    api: Api
    s3: S3Config
    web: Web
    postgres: Postgres
    hatchet: Hatchet
    ipinfo: IpInfo
    openrouter: OpenRouter
    tg_sessions: TgSessions

    @classmethod
    def create(cls, path: str | Path = "config.yml") -> Self:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)


class WorkerConfig(BaseModel):
    name: str
    slots: int


def get_worker_config(worker: str | None = None) -> WorkerConfig:
    """
    Worker config lives in app/pyproject.toml.

    Preferred format:
      [tool.workers.base]
      name = "base"
      slots = 20

    Backward-compatible fallback:
      [tool.worker]
      name = "dialog"
      slots = 20
    """

    pyproject_path = Path(__file__).with_name("pyproject.toml")
    with pyproject_path.open("rb") as f:
        data = tomllib.load(f)

    tool = data.get("tool") or {}

    if worker:
        # Allow passing "workers.base" / "workers.dialog" too.
        if worker.startswith("workers."):
            worker = worker.split(".", 1)[1]

        # Direct mapping: [tool.<worker>] (optional escape hatch).
        cfg = tool.get(worker)
        if cfg:
            return WorkerConfig(**cfg)

        # Preferred mapping: [tool.workers.base] / [tool.workers.dialog]
        workers = tool.get("workers") or {}
        cfg = workers.get(worker)
        if cfg:
            return WorkerConfig(**cfg)

    cfg = tool.get("worker")
    if cfg:
        return WorkerConfig(**cfg)

    raise KeyError(
        "Missing worker config: expected [tool.<worker>] (e.g. [tool.workers.base]) or [tool.worker]"
    )


config = Settings.create()


tortoise_config = {
    "connections": {
        "default": config.postgres.dsn.unicode_string(),
    },
    "apps": {
        "models": {
            "models": ["models.orm", "aerich.models"],
            "default_connection": "default",
        },
    },
}


async def init_db() -> BaseDBAsyncClient:
    await Tortoise.init(config=tortoise_config, timezone="Europe/Moscow", use_tz=False)
    return Tortoise.get_connection("default")


async def shutdown_db() -> None:
    await Tortoise.close_connections()
