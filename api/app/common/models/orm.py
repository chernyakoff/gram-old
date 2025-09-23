from typing import Self

from tortoise import fields
from tortoise.models import Model

from .enums import Role


class TimestampMixin:
    created_at = fields.DatetimeField(null=True, auto_now_add=True)
    updated_at = fields.DatetimeField(
        null=True,
        auto_now=True,
    )


class User(Model, TimestampMixin):
    id = fields.BigIntField(pk=True, generated=False)
    username = fields.CharField(max_length=64, null=True, db_index=True)
    first_name = fields.CharField(null=True, max_length=64)
    last_name = fields.CharField(null=True, max_length=64)
    photo_url = fields.CharField(max_length=256, null=True)
    role = fields.IntEnumField(enum_type=Role, default=Role.USER)
    license_end_date = fields.DatetimeField(null=True)
    settings: fields.ReverseRelation["Settings"]

    @property
    def display_name(self) -> str:
        if self.username:
            return f"@{self.username}"
        else:
            return f"ID: {self.id}"

    class Meta:
        table = "users"

    def __str__(self):
        return f"{self.id} | {self.username}"


class Settings(Model):
    id = fields.IntField(pk=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        on_delete=fields.CASCADE,
        related_name="settings",
        null=False,
    )
    section = fields.CharField(max_length=255, null=False)
    name = fields.CharField(max_length=255, null=False)
    value = fields.TextField(null=True)

    @classmethod
    async def upsert(cls, user_id: int, path: str, value: str) -> Self:
        section, name = path.split(".")
        obj, created = await cls.get_or_create(
            user_id=user_id,
            section=section,
            name=name,
            defaults={"value": value},
        )
        if not created:
            obj.value = value
            await obj.save(update_fields=["value"])
        return obj

    class Meta:
        table = "settings"
        unique_together = ("user_id", "section", "name")

    def __str__(self):
        return f"{self.user_id} | {self.section}.{self.name}: {self.value}"  # type: ignore


class Proxy(Model, TimestampMixin):
    id = fields.IntField(pk=True)
    host = fields.CharField(max_length=64, null=False)
    port = fields.IntField(null=False)
    username = fields.CharField(max_length=255, null=False)
    password = fields.CharField(max_length=255, null=False)
    active = fields.BooleanField(default=True)
    accounts = fields.ReverseRelation["Account"]
    country = fields.CharField(max_length=2, null=False)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="proxies", null=False
    )
    locked_until = fields.DatetimeField(null=True)
    lock_session = fields.CharField(max_length=36, null=True)
    scheme: str = "socks5"

    @property
    def dsn(self):
        if not self.host:
            return
        return (
            f"{self.scheme}://{self.username}:{self.password}@{self.host}:{self.port}"
        )

    class Meta:
        table = "proxies"
        unique_together = ("host", "port", "username", "password")


class Account(Model, TimestampMixin):
    id = fields.BigIntField(pk=True, generated=False)
    username = fields.CharField(max_length=34, null=True)
    first_name = fields.CharField(max_length=64, null=True)
    last_name = fields.CharField(max_length=64, null=True)
    phone = fields.CharField(max_length=32, null=True)
    about = fields.CharField(max_length=70, null=True)
    channel = fields.CharField(max_length=34, null=True)
    twofa = fields.CharField(max_length=64, null=True)
    app_id = fields.IntField(null=False)
    app_hash = fields.CharField(max_length=64, null=False)
    session = fields.TextField()
    device_model = fields.CharField(max_length=64, null=True)
    system_version = fields.CharField(max_length=64, null=True)
    app_version = fields.CharField(max_length=64, null=True)
    active = fields.BooleanField(default=True)
    busy = fields.BooleanField(default=False)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="accounts", null=False
    )
    premium = fields.BooleanField(default=False)
    country = fields.CharField(max_length=2, null=False)
    timeout_expires_at = fields.DatetimeField(null=True)
    photos = fields.ReverseRelation["AccountPhoto"]

    user_id: int
    main_photos: list["AccountPhoto"]

    @property
    def display_username(self) -> str:
        return f"@{self.username}" if self.username else f"ID: {self.id}"

    @property
    def name(self) -> str:
        return " ".join(filter(None, [self.first_name, self.last_name]))

    class Meta:
        table = "accounts"
        unique_together = ("id", "user_id")

    def __str__(self):
        return f"{self.id} {self.username} {self.first_name} {self.last_name}"


class AccountPhoto(Model):
    id = fields.BigIntField(pk=True)
    tg_id = fields.BigIntField(null=False)
    path = fields.CharField(null=False, max_length=128, unique=True)
    main = fields.BooleanField(default=False)
    access_hash = fields.BigIntField(null=False)
    file_reference = fields.BinaryField(null=False)
    account: fields.ForeignKeyRelation[Account] = fields.ForeignKeyField(
        "models.Account",
        related_name="photos",
        null=True,  # type: ignore
    )

    class Meta:
        table = "account_photos"
