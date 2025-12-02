import asyncio
from datetime import timedelta

from hatchet_sdk import Context, EmptyModel
from pydantic import BaseModel
from tortoise import Tortoise
from tortoise import timezone as tz
from tortoise.expressions import F, Q
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import enums, orm
from app.utils.notify import notify_mailing_end


class DialogIn(BaseModel):
    account_id: int
    recipients_id: list[int]
    key: str


dialog_task = hatchet.stubs.task(
    name="dialog",
    input_validator=DialogIn,
)

LEASE_HOURS = 2
MAX_ACCOUNTS_PER_CYCLE = 50
RECIPIENT_LEASE_MINUTES = 30

heartbeat = hatchet.workflow(name="heartbeat", on_crons=["15 * * * *"])


async def execute_query(query: str):
    await Tortoise.get_connection("default").execute_query(query)


async def complete_old_dialogs():
    await execute_query("""
UPDATE dialogs d
SET finished_at = NOW()
FROM (
    SELECT dialog_id, MAX(created_at) AS last_msg_time
    FROM messages
    GROUP BY dialog_id
) m
WHERE d.id = m.dialog_id
  AND d.status <> 'complete'
  AND d.finished_at IS NULL
  AND m.last_msg_time < NOW() - INTERVAL '2 days';
""")


async def unmute_accounts():
    await execute_query("""
UPDATE accounts
SET 
    status = 'good',
    muted_until = NULL,
    active = True
WHERE 
    status = 'muted'
    AND muted_until IS NOT NULL
    AND muted_until <= NOW();
""")


async def release_recipients():
    await execute_query(
        "UPDATE recipients SET lease_expires_at = NULL WHERE lease_expires_at < NOW()"
    )


async def get_active_projects() -> list[orm.Project]:
    now = tz.now()
    return await (
        orm.Project.filter(status=True)
        .filter(
            (
                Q(send_time_start__lte=F("send_time_end"))
                & Q(send_time_start__lte=now.hour)
                & Q(send_time_end__gte=now.hour)
            )
            | (
                Q(send_time_start__gt=F("send_time_end"))
                & (Q(send_time_start__lte=now.hour) | Q(send_time_end__gte=now.hour))
            )
        )
        .prefetch_related("mailings")
    )


async def get_available_accounts(project: orm.Project, now, conn):
    return (
        await orm.Account.filter(
            project=project, active=True, status=enums.AccountStatus.GOOD, busy=False
        )
        .limit(MAX_ACCOUNTS_PER_CYCLE)
        .using_db(conn)
    )


async def check_daily_limit(account: orm.Account, now, conn) -> int:
    counter = (
        await orm.AccountActionCounter.filter(
            account=account,
            action=enums.AccountAction.NEW_DIALOG,
            date=now.date(),
        )
        .using_db(conn)
        .first()
    )
    return max(0, account.out_daily_limit - (counter.count if counter else 0))


async def get_recipients_for_mailings(mailings, max_count, now, conn):
    recipients = []

    for mailing in mailings:
        need = max_count - len(recipients)
        if need <= 0:
            break

        available = (
            await orm.Recipient.filter(
                mailing=mailing,
                status=enums.RecipientStatus.PENDING,
            )
            .filter(Q(lease_expires_at__lt=now) | Q(lease_expires_at__isnull=True))
            .limit(need)
            .using_db(conn)
        )
        recipients.extend(available)

    return recipients


async def lock_account_and_recipients(account, recipients, now, conn):
    account_lease = now + timedelta(hours=LEASE_HOURS)
    recipient_lease = now + timedelta(minutes=RECIPIENT_LEASE_MINUTES)
    ids = [r.id for r in recipients]

    updated = await (
        orm.Account.filter(id=account.id)
        .filter(Q(busy=False) | Q(lease_expires_at__lt=now))
        .using_db(conn)
        .update(
            busy=True,
            lease_expires_at=account_lease,
            last_attempt_at=now,
            last_error=None,
        )
    )

    if updated == 0:
        return False

    await (
        orm.Recipient.filter(id__in=ids, status=enums.RecipientStatus.PENDING)
        .filter(Q(lease_expires_at__lt=now) | Q(lease_expires_at__isnull=True))
        .using_db(conn)
        .update(lease_expires_at=recipient_lease)
    )

    return True


async def check_and_close_mailing(mailing: orm.Mailing, now, conn) -> dict | None:
    """
    Закрывает рассылку, если:
        1) нет PENDING recipients
        2) нет открытых диалогов

    Возвращает словарь info, если нужно отправить notify.
    """
    pending_exists = (
        await orm.Recipient.filter(
            mailing=mailing,
            status=enums.RecipientStatus.PENDING,
        )
        .using_db(conn)
        .exists()
    )

    if pending_exists:
        return None

    open_dialogs_exist = (
        await orm.Dialog.filter(
            finished_at__isnull=True, recipient__mailing_id=mailing.id
        )
        .using_db(conn)
        .exists()
    )

    if open_dialogs_exist:
        return None

    await (
        orm.Mailing.filter(id=mailing.id)
        .using_db(conn)
        .update(status=enums.MailingStatus.FINISHED, finished_at=now)
    )

    info = await (
        orm.Mailing.filter(id=mailing.id)
        .using_db(conn)
        .values("user_id", "name", project_name="project__name")
    )

    return info[0] if info else None


@heartbeat.task()
async def task(input: EmptyModel, ctx: Context):
    await complete_old_dialogs()
    await unmute_accounts()
    await release_recipients()

    now = tz.now()
    planned_tasks = 0
    notify_queue = []

    projects = await get_active_projects()

    for project in projects:
        active_mailings = [
            m
            for m in project.mailings
            if m.status in (enums.MailingStatus.RUNNING, enums.MailingStatus.DRAFT)
        ]

        if not active_mailings:
            continue

        async with in_transaction() as conn:
            free_accounts = await get_available_accounts(project, now, conn)
            if not free_accounts:
                continue

            # Проверяем закрытие рассылок прямо здесь
            for mailing in active_mailings:
                info = await check_and_close_mailing(mailing, now, conn)
                if info:
                    notify_queue.append(info)

            # Аккаунты могли закрыть mailings → фильтруем
            active_mailings = [
                m
                for m in active_mailings
                if m.status in (enums.MailingStatus.RUNNING, enums.MailingStatus.DRAFT)
            ]

            if not active_mailings:
                continue

            for acc in free_accounts:
                dialogs_left = await check_daily_limit(acc, now, conn)

                recipients = await get_recipients_for_mailings(
                    active_mailings, dialogs_left, now, conn
                )

                for mailing in active_mailings:
                    if mailing.status == enums.MailingStatus.DRAFT:
                        if any(r.mailing_id == mailing.id for r in recipients):
                            await (
                                orm.Mailing.filter(id=mailing.id)
                                .using_db(conn)
                                .update(
                                    status=enums.MailingStatus.RUNNING,
                                    started_at=now,
                                )
                            )

                if not await lock_account_and_recipients(acc, recipients, now, conn):
                    continue

                recipients_id = [r.id for r in recipients]

                await dialog_task.aio_run_no_wait(
                    input=DialogIn(
                        account_id=acc.id, recipients_id=recipients_id, key=str(acc.id)
                    ),
                )

                planned_tasks += len(recipients_id)

    for info in notify_queue:
        asyncio.create_task(
            notify_mailing_end(info["user_id"], info["name"], info["project_name"])
        )

    return {"planned_tasks": planned_tasks, "time": now.isoformat()}
