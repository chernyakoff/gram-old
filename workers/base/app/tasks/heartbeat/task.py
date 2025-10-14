import uuid
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
    projects = await orm.Project.filter(status=True).prefetch_related(
        "accounts", "mailings"
    )

    for project in projects:
        # Берём свободные аккаунты проекта
        free_accounts: list[orm.Account] = [
            acc
            for acc in project.accounts  # type: ignore
            if acc.active
        ][:MAX_ACCOUNTS_PER_CYCLE]

        for acc in free_accounts:
            counter = await orm.AccountActionCounter.filter(
                account=acc, action=enums.AccountAction.NEW_DIALOG, date=now.date()
            ).first()

            dialogs_left = project.out_daily_limit - (counter.count if counter else 0)

            if dialogs_left <= 0:
                continue

            active_mailings = [
                m
                for m in project.mailings
                if m.status in (enums.MailingStatus.RUNNING, enums.MailingStatus.DRAFT)
            ]

            for mailing in active_mailings:
                # Генерируем уникальный session_id для этой порции
                session_id = str(uuid.uuid4())
                lease_time = now + timedelta(minutes=RECIPIENT_LEASE_MINUTES)

                # Атомарно захватываем recipients с помощью транзакции
                async with in_transaction() as conn:
                    # Выбираем свободных recipients
                    recipients = (
                        await orm.Recipient.filter(
                            mailing=mailing,
                            status=enums.RecipientStatus.PENDING,
                        )
                        .filter(
                            Q(lease_expires_at__lt=now)
                            | Q(lease_expires_at__isnull=True)
                        )
                        .limit(min(project.out_daily_limit, dialogs_left))
                        .using_db(conn)
                    )

                    if not recipients:
                        continue

                    recipients_id = [r.id for r in recipients]

                    # Атомарно помечаем их как занятые
                    await (
                        orm.Recipient.filter(
                            id__in=recipients_id,
                            status=enums.RecipientStatus.PENDING,
                        )
                        .using_db(conn)
                        .update(worker_id=worker_id, lease_expires_at=lease_time)
                    )

                # Теперь отправляем в таск - recipients уже заняты
                await dialog_task.aio_run_no_wait(
                    DialogIn(account_id=acc.id, recipients_id=recipients_id)
                )

                planned_tasks += len(recipients_id)

    return {"planned_tasks": planned_tasks, "time": now.isoformat()}
