import datetime
from typing import Self

from tortoise import fields
from tortoise.models import Model

from .enums import (
    AccountAction,
    AccountStatus,
    DialogStatus,
    MailingStatus,
    MessageSender,
    RecipientStatus,
    Role,
)

""" 
исходные модели для всего проекта - править тут
миграции тоже отсюда запускать
 """


class TimestampMixin:
    created_at = fields.DatetimeField(null=True, auto_now_add=True)
    updated_at = fields.DatetimeField(
        null=True,
        auto_now=True,
    )


class User(Model, TimestampMixin):
    id = fields.BigIntField(pk=True, generated=False)
    username = fields.CharField(max_length=34, null=True, db_index=True)
    first_name = fields.CharField(null=True, max_length=64)
    last_name = fields.CharField(null=True, max_length=64)
    photo_url = fields.CharField(max_length=256, null=True)
    role = fields.IntEnumField(enum_type=Role, default=Role.USER)
    license_end_date = fields.DatetimeField(null=True)
    settings: fields.ReverseRelation["Settings"]
    mailings = fields.ReverseRelation["Mailing"]
    projects = fields.ReverseRelation["Project"]

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
    project: fields.ForeignKeyNullableRelation["Project"] = fields.ForeignKeyField(
        "models.Project",
        related_name="accounts",
        null=True,
    )
    status = fields.CharEnumField(
        AccountStatus, default=AccountStatus.GOOD, max_length=64
    )
    muted_until = fields.DatetimeField(null=True)
    premium = fields.BooleanField(default=False)
    country = fields.CharField(max_length=2, null=False)
    photos = fields.ReverseRelation["AccountPhoto"]
    dialogs: fields.ReverseRelation["Dialog"]

    worker_id = fields.CharField(
        max_length=64, null=True
    )  # воркер, который взял аккаунт
    lease_expires_at = fields.DatetimeField(null=True)  # время, когда lease истекает

    last_error = fields.TextField(null=True)
    last_attempt_at = fields.DatetimeField(null=True)

    out_daily_limit = fields.IntField(
        description="Исходящих сообщений с одного аккаунта в сутки",
        null=False,
        default=6,
    )

    user_id: int

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


class Project(Model, TimestampMixin):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=64, null=False)
    status = fields.BooleanField(default=True)
    accounts = fields.ReverseRelation[Account]
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="projects", null=False
    )
    dialog_limit = fields.IntField(
        description="Сообщений в одной переписке", null=False, default=10
    )

    send_time_start = fields.IntField(
        description="Начало времени рассылки", null=False, default=0
    )
    send_time_end = fields.IntField(
        description="Конец времени рассылки",
        null=False,
        default=23,
    )
    first_message = fields.TextField(null=False)
    prompt = fields.JSONField(null=False)
    mailings: fields.ReverseRelation["Mailing"]
    user_id: int

    class Meta:
        table = "projects"


class AccountActionCounter(Model):
    account = fields.ForeignKeyField("models.Account", related_name="counters")
    action = fields.CharEnumField(AccountAction, max_length=64)
    date = fields.DateField(auto_now_add=True)
    count = fields.IntField(default=0)

    class Meta:
        table = "account_action_counter"
        unique_together = ("account", "action", "date")


class Mailing(Model):
    id = fields.BigIntField(pk=True)
    name = fields.TextField(null=True)
    project = fields.ForeignKeyField(
        "models.Project",
        related_name="mailings",
        on_delete=fields.CASCADE,
    )
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="mailings", null=False
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    started_at = fields.DatetimeField(null=True)
    finished_at = fields.DatetimeField(null=True)
    status = fields.CharEnumField(MailingStatus, default=MailingStatus.DRAFT)
    recipients: fields.ReverseRelation["Recipient"]

    class Meta:
        table = "mailings"


class Recipient(Model):
    id = fields.BigIntField(pk=True)
    mailing = fields.ForeignKeyField(
        "models.Mailing",
        related_name="recipients",
        on_delete=fields.CASCADE,
    )

    username = fields.CharField(max_length=320)  # ограничение email по стандарту
    metadata = fields.JSONField(null=True)
    status = fields.CharEnumField(RecipientStatus, default=RecipientStatus.PENDING)

    worker_id = fields.CharField(max_length=64, null=True)
    lease_expires_at = fields.DatetimeField(null=True)

    attempts = fields.IntField(default=0)
    last_error = fields.TextField(null=True)
    last_attempt_at = fields.DatetimeField(null=True)

    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "recipients"
        indexes = [
            ("mailing_id", "status", "lease_expires_at"),
            ("lease_expires_at",),
        ]


class Dialog(Model):
    id = fields.BigIntField(pk=True)
    account = fields.ForeignKeyField(
        "models.Account",
        related_name="dialogs",
        on_delete=fields.CASCADE,
    )

    recipient = fields.OneToOneField(
        "models.Recipient",
        related_name="dialog",
        on_delete=fields.CASCADE,
    )
    status = fields.CharEnumField(DialogStatus, default=DialogStatus.INIT)
    started_at = fields.DatetimeField(auto_now_add=True)
    finished_at = fields.DatetimeField(null=True)

    recipient_access_hash = fields.BigIntField(null=True)
    recipient_peer_id = fields.BigIntField(null=True)

    messages: fields.ReverseRelation["Message"]

    class Meta:
        table = "dialogs"


class Message(Model):
    id = fields.BigIntField(pk=True)
    dialog = fields.ForeignKeyField(
        "models.Dialog",
        related_name="messages",
        on_delete=fields.CASCADE,
    )

    sender = fields.CharEnumField(MessageSender, null=False)
    tg_message_id = fields.BigIntField(null=True)  # ID сообщения в Telegram
    text = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "messages"


class AppSettings(Model):
    id = fields.IntField(pk=True)
    section = fields.CharField(max_length=255, null=False)
    name = fields.CharField(max_length=255, null=False)
    value = fields.TextField(null=True)

    class Meta:
        table = "app_settings"
        unique_together = ("section", "name")
        indexes = ("section", "name")
