import math
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from enum import StrEnum, auto
from typing import Self

from tortoise import fields
from tortoise import timezone as tz
from tortoise.models import Model

from app.common.utils.functions import pick

from .enums import (
    AccountAction,
    AccountStatus,
    DialogStatus,
    MailingStatus,
    MessageSender,
    RecipientStatus,
    Role,
    WeekDay,
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
    meetings = fields.ReverseRelation["Meeting"]
    balance = fields.BigIntField(default=0)
    or_api_key = fields.CharField(max_length=256, null=True)
    or_api_hash = fields.CharField(max_length=256, null=True)
    or_model = fields.CharField(max_length=256, null=True)
    timezone = fields.CharField(max_length=64, null=True, default="Europe/Moscow")
    meeting_duration = fields.IntField(default=30)

    work_days: fields.ReverseRelation["UserWorkDay"]
    intervals: fields.ReverseRelation["UserWorkInterval"]
    disabled_month_days: fields.ReverseRelation["UserDisabledMonthDay"]

    async def extend_license(self, days: int) -> None:
        """Продлевает лицензию на указанное число дней."""

        now = tz.now()
        if self.license_end_date is None or self.license_end_date < now:
            self.license_end_date = now + timedelta(days=days)
        else:
            self.license_end_date += timedelta(days=days)

        await self.save()

    async def add_balance(self, rubles: int) -> None:
        if rubles <= 0:
            return  # или raise ValueError

        self.balance += rubles * 100
        await self.save()

    @property
    def days_left(self) -> int:
        """Сколько дней осталось до конца лицензии."""
        if not self.license_end_date:
            return 0

        now = tz.now()
        delta = self.license_end_date - now

        # если уже просрочена → 0
        if delta.total_seconds() <= 0:
            return 0

        return math.ceil(delta.total_seconds() / 86400)

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

    @classmethod
    async def fetch_all(cls, user_id: int) -> dict[str, dict[str, str | None]]:
        rows = await Settings.filter(user_id=user_id).values("section", "name", "value")

        result: dict[str, dict[str, str | None]] = defaultdict(dict)

        for row in rows:
            result[row["section"]][row["name"]] = row["value"]

        return dict(result)

    @classmethod
    async def fetch(cls, user_id: int, path: str) -> str:
        section, name = path.split(".")
        instance = await cls.filter(user_id=user_id, section=section, name=name).first()
        if instance:
            return instance.value
        return ""

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
    account: fields.ReverseRelation["Account"]
    locked_until = fields.DatetimeField(null=True)
    lock_session = fields.CharField(max_length=36, null=True)
    failures = fields.IntField(default=0)
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
    PROGREV = [2, 2, 3, 4, 4, 5, 6, 6, 7]
    id = fields.BigIntField(pk=True, generated=False)
    username = fields.CharField(max_length=34, null=True)
    first_name = fields.CharField(max_length=64, null=True)
    last_name = fields.CharField(max_length=64, null=True)
    phone = fields.CharField(max_length=32, null=True)
    about = fields.CharField(max_length=150, null=True)
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
        on_delete=fields.SET_NULL,
    )
    status = fields.CharEnumField(
        AccountStatus, default=AccountStatus.GOOD, max_length=64
    )
    muted_until = fields.DatetimeField(null=True)
    premium = fields.BooleanField(default=False)
    premium_stopped = fields.BooleanField(default=False)
    premiumed_at = fields.DatetimeField(null=True)
    country = fields.CharField(max_length=2, null=False)
    photos = fields.ReverseRelation["AccountPhoto"]
    dialogs: fields.ReverseRelation["Dialog"]

    proxy: fields.OneToOneNullableRelation[Proxy] = fields.OneToOneField(
        "models.Proxy",
        related_name="account",
        on_delete=fields.SET_NULL,
        null=True,
    )
    proxy_id: int

    lease_expires_at = fields.DatetimeField(null=True)  # время, когда lease истекает

    last_error = fields.TextField(null=True)
    last_attempt_at = fields.DatetimeField(null=True)

    out_daily_limit = fields.IntField(
        description="Исходящих сообщений с одного аккаунта в сутки( deprecated)",
        null=False,
        default=1,
    )

    user_id: int

    async def get_active_days_count(self) -> int:
        """
        Подсчитывает количество уникальных дней активности из таблицы dialogs
        """
        from tortoise import Tortoise

        conn = Tortoise.get_connection("default")

        result = await conn.execute_query_dict(
            """
            SELECT COUNT(DISTINCT DATE(started_at)) as days_count
            FROM dialogs
            WHERE account_id = $1
            """,
            [self.id],
        )

        return result[0]["days_count"] if result else 0

    async def get_dynamic_daily_limit(self) -> int:
        """
        Лимит основан на количестве АКТИВНЫХ дней
        """
        active_days = await self.get_active_days_count()

        if active_days >= len(self.PROGREV):
            return self.out_daily_limit

        if not self.premium:
            return 1

        return self.PROGREV[active_days]

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
    status = fields.BooleanField(default=False)
    accounts = fields.ReverseRelation[Account]
    skip_options = fields.JSONField(null=True)
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User", related_name="projects", null=False
    )
    dialog_limit = fields.IntField(
        description="Сообщений в одной переписке", null=False, default=10
    )

    send_time_start = fields.IntField(
        description="Начало времени рассылки", null=False, default=10
    )
    send_time_end = fields.IntField(
        description="Конец времени рассылки",
        null=False,
        default=21,
    )
    first_message = fields.TextField(null=True)
    use_calendar = fields.BooleanField(default=False)
    morning_reminder = fields.TextField(null=True)
    meeting_reminder = fields.TextField(null=True)

    prompt: fields.ReverseRelation["Prompt"]

    mailings: fields.ReverseRelation["Mailing"]
    brief: fields.ReverseRelation["Brief"]
    files: fields.ReverseRelation["ProjectFile"]
    documents: fields.ReverseRelation["ProjectDocument"]
    premium_required = fields.BooleanField(default=True)
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
    active = fields.BooleanField(default=False)

    class Meta:
        table = "mailings"


class Recipient(Model):
    id = fields.BigIntField(pk=True)
    mailing = fields.ForeignKeyField(
        "models.Mailing",
        related_name="recipients",
        on_delete=fields.CASCADE,
    )
    access_hash = fields.BigIntField(null=True)
    peer_id = fields.BigIntField(null=True)
    username = fields.CharField(max_length=320)
    first_name = fields.CharField(max_length=64, null=True)
    last_name = fields.CharField(max_length=64, null=True)
    phone = fields.CharField(max_length=32, null=True)
    about = fields.CharField(max_length=150, null=True)
    channel = fields.CharField(max_length=34, null=True)
    premium = fields.BooleanField(default=False)

    metadata = fields.JSONField(null=True)
    status = fields.CharEnumField(RecipientStatus, default=RecipientStatus.PENDING)

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
    started_at = fields.DatetimeField(auto_now_add=True, db_index=True)
    finished_at = fields.DatetimeField(null=True)

    messages: fields.ReverseRelation["Message"]
    meeting: fields.ReverseRelation["Meeting"]

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
    ack = fields.BooleanField(default=False)
    ui_only = fields.BooleanField(default=False)

    class Meta:
        table = "messages"


class AppSettings(Model, TimestampMixin):
    id = fields.IntField(pk=True)
    section = fields.CharField(max_length=255, null=False)
    name = fields.CharField(max_length=255, null=False)
    value = fields.TextField(null=True)

    @classmethod
    async def upsert(cls, path: str, value: str) -> Self:
        section, name = path.split(".")
        instance, _ = await cls.update_or_create(
            section=section, name=name, defaults={"value": value}
        )
        return instance

    @classmethod
    async def fetch(cls, path: str) -> str:
        section, name = path.split(".")
        instance = await cls.filter(section=section, name=name).first()
        if instance:
            return instance.value
        return ""

    class Meta:
        table = "app_settings"
        unique_together = ("section", "name")
        indexes = ("section", "name")


BRIEF_FIELDS = [
    "description",
    "offer",
    "client",
    "pains",
    "advantages",
    "mission",
    "focus",
]


class Brief(Model):
    id = fields.IntField(pk=True)
    project = fields.OneToOneField(
        "models.Project", related_name="brief", on_delete=fields.CASCADE
    )
    description = fields.TextField(null=False)
    offer = fields.TextField(null=False)
    client = fields.TextField(null=False)
    pains = fields.TextField(null=False)
    advantages = fields.TextField(null=False)
    mission = fields.TextField(null=False)
    focus = fields.TextField(null=False)

    def to_dict(self) -> dict:
        return pick(
            BRIEF_FIELDS,
            self,
        )

    class Meta:
        table = "briefs"


PROMPT_FIELDS = [
    "role",
    "context",
    "init",
    "engage",
    "offer",
    "closing",
    "instruction",
    "rules",
]


class Prompt(Model):
    id = fields.IntField(pk=True)
    project = fields.OneToOneField(
        "models.Project", related_name="prompt", on_delete=fields.CASCADE
    )
    role = fields.TextField(null=False)
    context = fields.TextField(null=False)
    init = fields.TextField(null=False)
    engage = fields.TextField(null=False)
    offer = fields.TextField(null=False)
    closing = fields.TextField(null=False)
    instruction = fields.TextField(null=False)
    rules = fields.TextField(null=False)

    def to_dict(self) -> dict:
        return pick(
            PROMPT_FIELDS,
            self,
        )

    @classmethod
    async def upsert(cls, project_id: int, data: dict) -> Self:
        instance, _ = await cls.update_or_create(project_id=project_id, defaults=data)
        return instance

    class Meta:
        table = "prompts"


class AccountBackup(Model, TimestampMixin):
    id = fields.BigIntField(pk=True, generated=False)
    session = fields.TextField()

    class Meta:
        table = "account_backups"


class AiModel(Model, TimestampMixin):
    id = fields.CharField(pk=True, max_length=256)
    name = fields.CharField(max_length=256, null=False)

    description = fields.TextField(null=False)
    prompt_price = fields.DecimalField(
        max_digits=20, decimal_places=12, default=Decimal("0")
    )
    completion_price = fields.DecimalField(
        max_digits=20, decimal_places=12, default=Decimal("0")
    )
    visible = fields.BooleanField(default=True)

    class Meta:
        table = "ai_models"


class UserWorkDay(Model):
    id = fields.IntField(pk=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="work_days",
        on_delete=fields.CASCADE,
    )

    weekday = fields.IntEnumField(WeekDay)

    is_enabled = fields.BooleanField(default=True)
    intervals: fields.ReverseRelation["UserWorkInterval"]

    class Meta:
        table = "user_work_days"
        unique_together = ("user", "weekday")


class UserWorkInterval(Model):
    id = fields.IntField(pk=True)

    work_day = fields.ForeignKeyField(
        "models.UserWorkDay",
        related_name="intervals",
        on_delete=fields.CASCADE,
    )

    time_from = fields.TimeField()
    time_to = fields.TimeField()

    class Meta:
        table = "user_work_intervals"


class UserDisabledMonthDay(Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="disabled_month_days",
        on_delete=fields.CASCADE,
    )
    day = fields.IntField()

    class Meta:
        unique_together = ("user", "day")
        table = "user_disabled_month_day"


class MutedAccount(Model, TimestampMixin):
    id = fields.BigIntField(pk=True, generated=False)
    username = fields.CharField(max_length=34, null=True)
    first_name = fields.CharField(max_length=64, null=True)
    last_name = fields.CharField(max_length=64, null=True)
    phone = fields.CharField(max_length=32, null=True)
    twofa = fields.CharField(max_length=64, null=True)
    app_id = fields.IntField(null=False)
    app_hash = fields.CharField(max_length=64, null=False)
    session = fields.TextField()
    device_model = fields.CharField(max_length=64, null=True)
    system_version = fields.CharField(max_length=64, null=True)
    app_version = fields.CharField(max_length=64, null=True)

    @classmethod
    def from_account(cls, account: Account) -> Self:
        return cls(
            id=account.id,
            username=account.username,
            first_name=account.first_name,
            last_name=account.last_name,
            phone=account.phone,
            twofa=account.twofa,
            app_id=account.app_id,
            app_hash=account.app_hash,
            session=account.session,
            device_model=account.device_model,
            system_version=account.system_version,
            app_version=account.app_version,
        )

    class Meta:
        table = "muted_accounts"


class ProjectDocumentSourceType(StrEnum):
    FILE = auto()
    URL = auto()
    TEXT = auto()


class ProjectDocument(Model, TimestampMixin):
    id = fields.BigIntField(pk=True)

    project = fields.ForeignKeyField(
        "models.Project",
        related_name="documents",
        on_delete=fields.CASCADE,
        index=True,
    )

    # Метаданные

    filename = fields.CharField(max_length=255, null=True)
    content_type = fields.CharField(
        max_length=100, null=True
    )  # application/pdf, text/plain

    source_type = fields.CharEnumField(
        ProjectDocumentSourceType,
        default=ProjectDocumentSourceType.FILE,
        index=True,
    )

    # Статус ingestion

    error_message = fields.TextField(null=True)

    # Размеры / статистика (удобно для лимитов и UI)
    file_size = fields.BigIntField(null=True)
    text_length = fields.IntField(null=True)  # длина извлечённого текста
    chunks_count = fields.IntField(null=True)

    # Источник
    source_url = fields.CharField(max_length=2048, null=True)
    storage_path = fields.CharField(
        max_length=1024, null=True
    )  # путь к файлу (S3, local, etc.)

    # Аудит

    class Meta:
        table = "project_documents"

    def __str__(self) -> str:
        return f"<Document {self.id} ({self.filename})>"


class ProjectFileStatus(StrEnum):
    ENGAGE = auto()  # проявил интерес
    OFFER = auto()  # сделали предложение
    CLOSING = auto()  # завершено (отказ / интерес / договорились о звонке)
    COMPLETE = auto()  # попрощались


class ProjectFile(Model, TimestampMixin):
    id = fields.BigIntField(pk=True)

    project = fields.ForeignKeyField(
        "models.Project",
        related_name="files",
        on_delete=fields.CASCADE,
        index=True,
    )
    project_id: int
    # Метаданные
    title = fields.CharField(max_length=255, null=True)
    status = fields.CharEnumField(ProjectFileStatus, null=True)

    filename = fields.CharField(max_length=255, null=True)
    content_type = fields.CharField(
        max_length=100, null=True
    )  # application/pdf, text/plain

    file_size = fields.BigIntField(null=True)
    storage_path = fields.CharField(
        max_length=1024, null=True
    )  # путь к файлу (S3, local, etc.)

    class Meta:
        table = "project_files"

    def __str__(self) -> str:
        return f"<Files {self.id} ({self.filename})>"


class MeetingStatus(StrEnum):
    SCHEDULED = auto()
    CANCELLED = auto()
    COMPLETED = auto()


class MeetingSource(StrEnum):
    MANUAL = auto()
    API = auto()
    AUTO = auto()


class Meeting(Model, TimestampMixin):
    id = fields.IntField(pk=True)

    user = fields.ForeignKeyField(
        "models.User",
        related_name="meetings",
        on_delete=fields.CASCADE,
    )

    start_at = fields.DatetimeField()
    end_at = fields.DatetimeField()

    status = fields.CharEnumField(
        enum_type=MeetingStatus,
        default=MeetingStatus.SCHEDULED,
        max_length=16,
        index=True,
    )

    source = fields.CharEnumField(
        enum_type=MeetingSource,
        default=MeetingSource.AUTO,
        max_length=16,
    )

    dialog = fields.OneToOneField(
        "models.Dialog",
        related_name="meeting",
        on_delete=fields.CASCADE,
    )

    class Meta:
        table = "meetings"
        indexes = [
            ("user", "start_at"),
            ("user", "end_at"),
        ]


class MorningReminderSent(Model, TimestampMixin):
    id = fields.IntField(pk=True)
    meeting = fields.ForeignKeyField("models.Meeting", related_name="morning_reminders")

    class Meta:
        table = "morning_reminders_sent"
        unique_together = ("meeting",)


class MeetingReminderSent(Model, TimestampMixin):
    id = fields.IntField(pk=True)
    meeting = fields.ForeignKeyField(
        "models.Meeting", related_name="hour_before_reminders"
    )

    class Meta:
        table = "meeting_reminders_sent"
        unique_together = ("meeting",)
