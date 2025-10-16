from datetime import timedelta

from hatchet_sdk import Context, EmptyModel
from pydantic import BaseModel
from tortoise import timezone as tz
from tortoise.expressions import Q
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


@heartbeat.task()
async def task(input: EmptyModel, ctx: Context):
    now = tz.now()
    planned_tasks = 0
    worker_id = str(ctx.worker.id())

    # Берём активные проекты
    projects = await orm.Project.filter(status=True).prefetch_related("mailings")

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
            # 1. Находим свободные аккаунты проекта
            free_accounts = (
                await orm.Account.filter(
                    project=project,
                    active=True,
                )
                .filter(Q(busy=False) | Q(lease_expires_at__lt=now))
                .limit(MAX_ACCOUNTS_PER_CYCLE)
                .using_db(conn)
            )

            if not free_accounts:
                continue

            # 2. Для каждого аккаунта проверяем лимиты и захватываем recipients
            for acc in free_accounts:
                # Проверяем дневной лимит
                counter = (
                    await orm.AccountActionCounter.filter(
                        account=acc,
                        action=enums.AccountAction.NEW_DIALOG,
                        date=now.date(),
                    )
                    .using_db(conn)
                    .first()
                )

                dialogs_left = project.out_daily_limit - (
                    counter.count if counter else 0
                )

                if dialogs_left <= 0:
                    continue

                # Ищем свободных recipients из активных mailings
                recipients_to_assign = []

                for mailing in active_mailings:
                    # Сколько ещё можем взять для этого аккаунта
                    need_count = dialogs_left - len(recipients_to_assign)
                    if need_count <= 0:
                        break

                    # Выбираем свободных recipients
                    available_recipients = (
                        await orm.Recipient.filter(
                            mailing=mailing,
                            status=enums.RecipientStatus.PENDING,
                        )
                        .filter(
                            Q(lease_expires_at__lt=now)
                            | Q(lease_expires_at__isnull=True)
                        )
                        .limit(need_count)
                        .using_db(conn)
                    )

                    recipients_to_assign.extend(available_recipients)

                if not recipients_to_assign:
                    continue

                # 3. Атомарно блокируем и аккаунт, и recipients
                recipients_id = [r.id for r in recipients_to_assign]

                account_lease_time = now + timedelta(hours=LEASE_HOURS)
                recipient_lease_time = now + timedelta(minutes=RECIPIENT_LEASE_MINUTES)

                # Блокируем аккаунт
                updated_accounts = await (
                    orm.Account.filter(
                        id=acc.id,
                    )
                    .filter(Q(busy=False) | Q(lease_expires_at__lt=now))
                    .using_db(conn)
                    .update(
                        busy=True,
                        worker_id=worker_id,
                        lease_expires_at=account_lease_time,
                        last_attempt_at=now,
                        last_error=None,
                    )
                )

                # Если аккаунт не удалось захватить (другой worker успел раньше)
                if updated_accounts == 0:
                    continue

                # Блокируем recipients
                await (
                    orm.Recipient.filter(
                        id__in=recipients_id,
                        status=enums.RecipientStatus.PENDING,
                    )
                    .filter(
                        Q(lease_expires_at__lt=now) | Q(lease_expires_at__isnull=True)
                    )
                    .using_db(conn)
                    .update(worker_id=worker_id, lease_expires_at=recipient_lease_time)
                )

                # 4. Отправляем в таск - всё уже заблокировано
                await dialog_task.aio_run_no_wait(
                    DialogIn(account_id=acc.id, recipients_id=recipients_id)
                )

                planned_tasks += len(recipients_id)

    return {"planned_tasks": planned_tasks, "time": now.isoformat()}
