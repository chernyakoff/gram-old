import asyncio
from datetime import timedelta

from hatchet_sdk import Context, EmptyModel, TriggerWorkflowOptions
from pydantic import BaseModel
from tortoise import Tortoise
from tortoise import timezone as tz
from tortoise.expressions import F, Q
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import enums, orm
from app.common.utils.notify import notify_mailing_end
from app.tasks.accounts.stop_premium import StopPremiumIn


class DialogIn(BaseModel):
    account_id: int
    recipients_id: list[int]
    key: str


dialog_task = hatchet.stubs.task(
    name="dialog",
    input_validator=DialogIn,
)

stop_premium_task = hatchet.stubs.task(
    name="stop_premium", input_validator=StopPremiumIn
)

LEASE_HOURS = 2
MAX_ACCOUNTS_PER_CYCLE = 50
RECIPIENT_LEASE_MINUTES = 30

heartbeat = hatchet.workflow(name="heartbeat", on_crons=["5,35 * * * *"])


async def execute_query(query: str):
    await Tortoise.get_connection("default").execute_query(query)


async def cleanup_stale_locks():
    """Очистить устаревшие блокировки"""
    now = tz.now()
    await orm.Proxy.filter(locked_until__lt=now, lock_session__not_isnull=True).update(
        locked_until=None, lock_session=None
    )
    await execute_query("""
UPDATE accounts
SET lease_expires_at = NULL,
    busy = FALSE
WHERE lease_expires_at <= NOW()
  AND busy = TRUE;
""")


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
  AND m.last_msg_time < NOW() - INTERVAL '7 days';
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


async def get_active_projects(min_balance: int = 1000) -> list[orm.Project]:
    """Получить активные проекты, где у пользователя хватает баланса"""
    return await orm.Project.filter(
        status=True,
        user__balance__gt=min_balance,
    ).prefetch_related("mailings", "user")


def is_project_in_send_window(project: orm.Project, now) -> bool:
    """Проверить, находится ли проект в окне отправки (для новых recipients)"""
    current_hour = now.hour
    start = project.send_time_start
    end = project.send_time_end

    if start <= end:
        # Обычный случай: например, 9-18
        return start <= current_hour <= end
    else:
        # Переход через полночь: например, 22-6
        return current_hour >= start or current_hour <= end


async def get_available_accounts(project: orm.Project, now, conn) -> list[orm.Account]:
    params = dict(
        project=project,
        status=enums.AccountStatus.GOOD,
        busy=False,
    )
    if project.premium_required:
        params["premium"] = True

    return (
        await orm.Account.filter(**params).limit(MAX_ACCOUNTS_PER_CYCLE).using_db(conn)
    )


async def check_daily_limit(account: orm.Account, now, conn) -> int:
    # Получаем динамический лимит (с запросом к dialogs)
    daily_limit = await account.get_dynamic_daily_limit()

    counter = (
        await orm.AccountActionCounter.filter(
            account=account,
            action=enums.AccountAction.NEW_DIALOG,
            date=now.date(),
        )
        .using_db(conn)
        .first()
    )

    return max(0, daily_limit - (counter.count if counter else 0))


async def reserve_daily_limit(
    account: orm.Account,
    reserve: int,
    now,
    conn,
) -> int:
    """
    Резервирует диалоги, НО НЕ увеличивает active_days_count
    """
    if reserve <= 0:
        return 0

    # Получаем лимит на основе текущего active_days_count
    daily_limit = await account.get_dynamic_daily_limit()

    await orm.AccountActionCounter.get_or_create(
        account=account,
        action=enums.AccountAction.NEW_DIALOG,
        date=now.date(),
        defaults={"count": 0},
        using_db=conn,
    )

    # Атомарно резервируем
    rows = await conn.execute_query_dict(
        """
        UPDATE account_action_counter
        SET count = count + $1
        WHERE account_id = $2
          AND action = $3
          AND date = $4
          AND count + $1 <= $5
        RETURNING count;
        """,
        [
            reserve,
            account.id,
            enums.AccountAction.NEW_DIALOG,
            now.date(),
            daily_limit,
        ],
    )

    # НЕ увеличиваем active_days_count здесь!
    return reserve if rows else 0


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


""" 
 if acc.premium is True and acc.premium_stopped is False:
                    
                    continue
 """


@heartbeat.task()
async def task(input: EmptyModel, ctx: Context):
    await complete_old_dialogs()
    await unmute_accounts()
    await release_recipients()
    await cleanup_stale_locks()

    # убрать после всех изменений
    premium_accounts_with_auto_renew = await orm.Account.filter(
        status=enums.AccountStatus.GOOD, busy=False, premium=True, premium_stopped=False
    ).all()
    if premium_accounts_with_auto_renew:
        for a in premium_accounts_with_auto_renew:
            await stop_premium_task.aio_run_no_wait(
                input=StopPremiumIn(account_id=a.id)
            )
            ctx.log(f"отменяем премиум для {a.id}")

        return

    now = tz.now()
    planned_tasks = 0
    notify_queue = []

    projects = await get_active_projects()

    for project in projects:
        # Проверяем, находится ли проект в окне отправки
        in_send_window = is_project_in_send_window(project, now)

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
                # Получаем доступное количество новых диалогов
                dialogs_left = await check_daily_limit(acc, now, conn)

                # Получаем recipients для новых диалогов ТОЛЬКО если в окне отправки
                recipients = []
                if in_send_window:
                    recipients = await get_recipients_for_mailings(
                        active_mailings, dialogs_left, now, conn
                    )

                # Резервируем лимит новых диалогов атомарно
                reserved = 0
                if recipients:
                    reserved = await reserve_daily_limit(
                        acc, len(recipients), now, conn
                    )
                    if reserved < len(recipients):
                        recipients = recipients[:reserved]

                # Статус DRAFT → RUNNING, если есть recipients (только в окне отправки)
                if in_send_window:
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

                # Лочим аккаунт и recipients
                if not await lock_account_and_recipients(acc, recipients, now, conn):
                    continue

                recipients_id = [r.id for r in recipients]  # может быть пусто

                # Всегда запускаем диалог-таск (даже без новых recipients - для продолжения старых диалогов)
                await dialog_task.aio_run_no_wait(
                    input=DialogIn(
                        account_id=acc.id, recipients_id=recipients_id, key=str(acc.id)
                    ),
                    options=TriggerWorkflowOptions(
                        additional_metadata={
                            "account_id": acc.id,
                            "user_id": acc.user_id,
                        }
                    ),
                )

                planned_tasks += len(recipients_id)

    # Отправка уведомлений о завершении рассылок
    for info in notify_queue:
        asyncio.create_task(
            notify_mailing_end(info["user_id"], info["name"], info["project_name"])
        )

    return {"planned_tasks": planned_tasks, "time": now.isoformat()}
