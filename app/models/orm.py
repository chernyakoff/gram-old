from collections import defaultdict
from decimal import Decimal
from enum import IntEnum, StrEnum, auto
from typing import Self

from tortoise import fields
from tortoise import timezone as tz
from tortoise.models import Model

from utils.functions import pick

""" 
исходные модели для всего проекта - править тут
миграции тоже отсюда запускать
 """


# Enums used by ORM models. Previously lived in `models/enums.py`.
class LicenseType(IntEnum):
    НЕТ = 0
    МЕСЯЦ = 1
    ТРИ_МЕСЯЦА = 3
    ШЕСТЬ_МЕСЯЦЕВ = 6
    ГОД = 12
    ПРЕМИУМ = 120


class TimestampMixin:
    created_at = fields.DatetimeField(null=True, auto_now_add=True)
    updated_at = fields.DatetimeField(
        null=True,
        auto_now=True,
    )


class User(Model, TimestampMixin):
    id = fields.BigIntField(pk=True, generated=False)
    settings: fields.ReverseRelation["Settings"]
    mailings = fields.ReverseRelation["Mailing"]
    projects = fields.ReverseRelation["Project"]
    meetings = fields.ReverseRelation["Meeting"]
    schedules: fields.ReverseRelation["UserSchedule"]

    @property
    def display_name(self) -> str:
        return f"ID: {self.id}"

    class Meta:
        table = "users"

    def __str__(self):
        return f"{self.id}"


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


class AccountStatus(StrEnum):
    GOOD = "good"
    BANNED = "banned"
    MUTED = "muted"
    FROZEN = "frozen"
    EXITED = "exited"
    NOPROXY = "noproxy"


class AccountAction(StrEnum):
    RESOLVE_USERNAME = "resolve_username"
    NEW_DIALOG = "new_dialog"


class Account(Model, TimestampMixin):
    PROGREV = [1, 2, 3, 3, 4, 5, 6, 7]
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
    user_id: int  # для pylance
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
        description="Исходящих сообщений с одного аккаунта в сутки",
        null=False,
        default=1,
    )

    active_days_count = fields.IntField(
        default=0, description="количество уникальных дней активности"
    )
    daily_limit_left = fields.IntField(
        default=0, description="остаток на текущие сутки"
    )

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


class MailingStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    FINISHED = "finished"
    CANCELLED = "cancelled"


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


class RecipientStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    FAILED = "failed"
    BOUNCED = "bounced"


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


class DialogStatus(StrEnum):
    INIT = "init"  # приветствие
    ENGAGE = "engage"  # проявил интерес
    OFFER = "offer"  # сделали предложение
    CLOSING = "closing"  # завершено (отказ / интерес / договорились о звонке)
    COMPLETE = "complete"  # попрощались
    NEGATIVE = "negative"  # послали нахер
    OPERATOR = "operator"  # робот раскрыт -- требуется кожаный мешок
    MANUAL = "manual"  # диалог перезваче менеджером


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
    followed_up_at = fields.DatetimeField(null=True)

    messages: fields.ReverseRelation["Message"]
    meeting: fields.ReverseRelation["Meeting"]

    class Meta:
        table = "dialogs"


class MessageSender(StrEnum):
    ACCOUNT = "account"
    RECIPIENT = "recipient"
    SYSTEM = "system"


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
    created_at = fields.DatetimeField(
        null=False,
        default=lambda: tz.now(),
    )
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


class UserSchedule(Model, TimestampMixin):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="schedules",
        on_delete=fields.CASCADE,
    )
    name = fields.CharField(max_length=128, default="Основное")
    timezone = fields.CharField(max_length=64, default="Europe/Moscow")
    meeting_duration = fields.IntField(default=30)
    is_default = fields.BooleanField(default=False)

    work_days: fields.ReverseRelation["UserWorkDay"]
    disabled_month_days: fields.ReverseRelation["UserDisabledMonthDay"]
    meetings: fields.ReverseRelation["Meeting"]

    @classmethod
    async def get_default_for_user(cls, user: User) -> "UserSchedule":
        schedule = await cls.filter(user_id=user.id, is_default=True).first()
        if schedule:
            return schedule

        schedule = await cls.filter(user_id=user.id).order_by("id").first()
        if schedule:
            if not schedule.is_default:
                schedule.is_default = True
                await schedule.save(update_fields=["is_default"])
            return schedule

        return await cls.create(
            user=user,
            name="Основное",
            timezone="Europe/Moscow",
            meeting_duration=30,
            is_default=True,
        )

    class Meta:
        table = "user_schedules"
        unique_together = ("user", "name")
        indexes = [("user", "is_default")]


class WeekDay(IntEnum):
    MONDAY = 1
    TUESDAY = 2
    WEDNESDAY = 3
    THURSDAY = 4
    FRIDAY = 5
    SATURDAY = 6
    SUNDAY = 7


class UserWorkDay(Model):
    id = fields.IntField(pk=True)

    schedule = fields.ForeignKeyField(
        "models.UserSchedule",
        related_name="work_days",
        on_delete=fields.CASCADE,
    )

    weekday = fields.IntEnumField(WeekDay)

    is_enabled = fields.BooleanField(default=True)
    intervals: fields.ReverseRelation["UserWorkInterval"]

    class Meta:
        table = "user_work_days"
        unique_together = ("schedule", "weekday")


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
    schedule = fields.ForeignKeyField(
        "models.UserSchedule",
        related_name="disabled_month_days",
        on_delete=fields.CASCADE,
    )
    day = fields.IntField()

    class Meta:
        unique_together = ("schedule", "day")
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
    schedule_id: int

    user = fields.ForeignKeyField(
        "models.User",
        related_name="meetings",
        on_delete=fields.CASCADE,
    )
    schedule = fields.ForeignKeyField(
        "models.UserSchedule",
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
            ("schedule", "start_at"),
            ("schedule", "end_at"),
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
