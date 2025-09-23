from typing import Self

import yaml
from pydantic import BaseModel, Field, PostgresDsn, SecretStr
from tortoise import Tortoise


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
    jwt: Jwt
    bot: Bot


class Web(BaseModel):
    url: str


class Hatchet(BaseModel):
    token: str


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


class Postgres(BaseModel):
    dsn: PostgresDsn = Field()

    @property
    def options(self) -> DatabaseOptions:
        return DatabaseOptions(**self.dsn.hosts()[0], database=self.dsn.path.strip("/"))  # type: ignore


class Settings(BaseModel):
    api: Api
    s3: S3Config
    web: Web
    postgres: Postgres
    hatchet: Hatchet

    @classmethod
    def create(cls, path="config.yml") -> Self:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)


config = Settings.create()


tortoise_config = {
    "connections": {
        "default": config.postgres.dsn.unicode_string(),
    },
    "apps": {
        "models": {
            "models": ["app.common.models.orm", "aerich.models"],
            "default_connection": "default",
        },
    },
}


async def init_db() -> None:
    await Tortoise.init(config=tortoise_config, timezone="Europe/Moscow", use_tz=False)


async def shutdown_db() -> None:
    await Tortoise.close_connections()
