from datetime import timedelta

from hatchet_sdk import Context, EmptyModel
from pydantic import BaseModel
from tortoise import timezone as tz
from tortoise.expressions import F, Q
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import enums, orm


class DialogIn(BaseModel):
    account_id: int
    recipients_id: list[int]


dialog_task = hatchet.stubs.task(
    name="dialog",
    input_validator=DialogIn,
)


LEASE_HOURS = 6  # сколько "занятый" аккаунт считается занятым
MAX_ACCOUNTS_PER_CYCLE = 50  # сколько аккаунтов проверяем за 1 тик
RECIPIENT_LEASE_MINUTES = 30  # время аренды recipient перед отправкой в таск

heartbeat = hatchet.workflow(name="heartbeat", on_crons=["* * * * *"])


async def get_active_projects() -> list[orm.Project]:
    now = tz.now()
    projects = (
        await orm.Project.filter(status=True)
        .filter(
            # 1) Обычный промежуток (например 10 → 18)
            (
                Q(send_time_start__lte=F("send_time_end"))
                & Q(send_time_start__lte=now.hour)
                & Q(send_time_end__gte=now.hour)
            )
            |
            # 2) Промежуток через полночь (например 21 → 1)
            (
                Q(send_time_start__gt=F("send_time_end"))
                & (Q(send_time_start__lte=now.hour) | Q(send_time_end__gte=now.hour))
            )
        )
        .prefetch_related("mailings")
    )
    return projects


async def get_available_accounts(project: orm.Project, now, conn) -> list[orm.Account]:
    """Получает список свободных аккаунтов для проекта."""
    return (
        await orm.Account.filter(
            project=project,
            active=True,
        )
        .filter(Q(busy=False) | Q(lease_expires_at__lt=now))
        .limit(MAX_ACCOUNTS_PER_CYCLE)
        .using_db(conn)
    )


async def check_daily_limit(
    account: orm.Account, project: orm.Project, now, conn
) -> int:
    """Проверяет дневной лимит аккаунта и возвращает количество оставшихся диалогов."""
    counter = (
        await orm.AccountActionCounter.filter(
            account=account,
            action=enums.AccountAction.NEW_DIALOG,
            date=now.date(),
        )
        .using_db(conn)
        .first()
    )

    dialogs_left = project.out_daily_limit - (counter.count if counter else 0)
    return max(0, dialogs_left)


async def get_recipients_for_mailings(
    mailings: list[orm.Mailing], max_count: int, now, conn
) -> list[orm.Recipient]:
    """Собирает свободных recipients из списка mailings до достижения лимита."""
    recipients_to_assign = []

    for mailing in mailings:
        need_count = max_count - len(recipients_to_assign)
        if need_count <= 0:
            break

        available_recipients = (
            await orm.Recipient.filter(
                mailing=mailing,
                status=enums.RecipientStatus.PENDING,
            )
            .filter(Q(lease_expires_at__lt=now) | Q(lease_expires_at__isnull=True))
            .limit(need_count)
            .using_db(conn)
        )

        recipients_to_assign.extend(available_recipients)

    return recipients_to_assign


async def lock_account_and_recipients(
    account: orm.Account, recipients: list[orm.Recipient], now, conn
) -> bool:
    """
    Атомарно блокирует аккаунт и recipients.
    Возвращает True если блокировка успешна, False если аккаунт уже занят.
    """
    account_lease_time = now + timedelta(hours=LEASE_HOURS)
    recipient_lease_time = now + timedelta(minutes=RECIPIENT_LEASE_MINUTES)
    recipients_id = [r.id for r in recipients]

    # Блокируем аккаунт
    updated_accounts = await (
        orm.Account.filter(id=account.id)
        .filter(Q(busy=False) | Q(lease_expires_at__lt=now))
        .using_db(conn)
        .update(
            busy=True,
            lease_expires_at=account_lease_time,
            last_attempt_at=now,
            last_error=None,
        )
    )

    # Если аккаунт не удалось захватить (другой worker успел раньше)
    if updated_accounts == 0:
        return False

    # Блокируем recipients
    await (
        orm.Recipient.filter(
            id__in=recipients_id,
            status=enums.RecipientStatus.PENDING,
        )
        .filter(Q(lease_expires_at__lt=now) | Q(lease_expires_at__isnull=True))
        .using_db(conn)
        .update(lease_expires_at=recipient_lease_time)
    )

    return True


@heartbeat.task()
async def task(input: EmptyModel, ctx: Context):
    now = tz.now()
    planned_tasks = 0

    projects = await get_active_projects()

    for project in projects:
        # Находим активные mailings для проекта
        active_mailings = [
            m
            for m in project.mailings
            if m.status in (enums.MailingStatus.RUNNING, enums.MailingStatus.DRAFT)
        ]

        if not active_mailings:
            continue

        # Атомарно захватываем аккаунты и recipients в одной транзакции
        async with in_transaction() as conn:
            # Получаем свободные аккаунты
            free_accounts = await get_available_accounts(project, now, conn)

            if not free_accounts:
                continue

            # Обрабатываем каждый аккаунт
            for acc in free_accounts:
                # Проверяем дневной лимит
                dialogs_left = await check_daily_limit(acc, project, now, conn)

                if dialogs_left <= 0:
                    continue

                # Собираем recipients из активных mailings
                recipients_to_assign = await get_recipients_for_mailings(
                    active_mailings, dialogs_left, now, conn
                )

                if not recipients_to_assign:
                    continue

                # Атомарно блокируем аккаунт и recipients
                locked = await lock_account_and_recipients(
                    acc, recipients_to_assign, now, conn
                )

                if not locked:
                    continue

                # Отправляем в таск
                recipients_id = [r.id for r in recipients_to_assign]
                await dialog_task.aio_run_no_wait(
                    DialogIn(account_id=acc.id, recipients_id=recipients_id)
                )

                planned_tasks += len(recipients_id)

    return {"planned_tasks": planned_tasks, "time": now.isoformat()}
