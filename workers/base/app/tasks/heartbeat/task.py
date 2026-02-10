import asyncio
import math
from datetime import datetime, time, timedelta

from hatchet_sdk import Context, EmptyModel, TriggerWorkflowOptions
from pydantic import BaseModel
from tortoise import Tortoise
from tortoise import timezone as tz
from tortoise.expressions import Q
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
    name="stop-premium", input_validator=StopPremiumIn
)

ACCOUNT_LEASE_MINUTES = 45
MAX_ACCOUNTS_PER_CYCLE = 100
RECIPIENT_LEASE_MINUTES = 30
MAX_ACCOUNTS_PER_USER_PER_CYCLE = 20
HEARTBEAT_MINUTES = 30

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


async def ensure_reminder_tables():
    """
    Гарантирует существование таблиц логов отправленных напоминаний.
    Нужна для совместимости окружений, где схема еще не была обновлена.
    """
    await execute_query("""
CREATE TABLE IF NOT EXISTS morning_reminders_sent (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    meeting_id INT NOT NULL UNIQUE REFERENCES meetings(id) ON DELETE CASCADE
);
""")
    await execute_query("""
CREATE TABLE IF NOT EXISTS meeting_reminders_sent (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL,
    meeting_id INT NOT NULL UNIQUE REFERENCES meetings(id) ON DELETE CASCADE
);
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


def is_project_morning_time(project: orm.Project, now) -> bool:
    """
    Проверяет, что сейчас подходящее время для утреннего напоминания:
    близко к project.send_time_start (±30 минут).
    """
    current_minutes = now.hour * 60 + now.minute
    target_minutes = project.send_time_start * 60
    return abs(current_minutes - target_minutes) <= 30


async def get_available_accounts(project: orm.Project, now, conn) -> list[orm.Account]:
    """
    Получить доступные аккаунты с приоритетом у тех, у кого есть дневной лимит,
    и с равномерным распределением между пользователями (round-robin).
    Если проект требует премиум, берём только премиум-аккаунты.
    """
    premium_filter = "AND a.premium = TRUE" if project.premium_required else ""

    query = f"""
    WITH ranked AS (
        SELECT
            a.id,
            a.user_id,
            a.daily_limit_left,
            a.busy,
            a.status,
            a.lease_expires_at,
            a.last_attempt_at,
            ROW_NUMBER() OVER (
                PARTITION BY a.user_id
                ORDER BY 
                    (a.daily_limit_left > 0) DESC,
                    COALESCE(a.last_attempt_at, '1970-01-01') ASC,
                    a.id ASC
            ) AS user_rank
        FROM accounts a
        WHERE 
            a.project_id = $1
            AND a.status = 'good'
            AND a.busy = FALSE
            AND (a.lease_expires_at IS NULL OR a.lease_expires_at < $2)
            {premium_filter}
    )
    SELECT *
    FROM ranked
    WHERE user_rank <= {MAX_ACCOUNTS_PER_USER_PER_CYCLE}
    ORDER BY (daily_limit_left > 0) DESC, last_attempt_at ASC
    LIMIT {MAX_ACCOUNTS_PER_CYCLE};
    """

    rows = await conn.execute_query_dict(query, [project.id, now])
    accounts = [orm.Account(**row) for row in rows]
    return accounts


async def get_accounts_with_due_reminders(project: orm.Project, now, conn) -> list[int]:
    """
    Возвращает свободные аккаунты проекта, которым нужно срочно отправить напоминания.
    Приоритет:
      1) напоминание о встрече (за час)
      2) утреннее напоминание
    """
    if not project.use_calendar:
        return []

    meeting_enabled = bool(project.meeting_reminder)
    morning_enabled = bool(project.morning_reminder) and is_project_morning_time(
        project, now
    )

    if not meeting_enabled and not morning_enabled:
        return []

    params = [project.id, now]

    meeting_due_sql = "FALSE"
    if meeting_enabled:
        hour_from_now_min = now + timedelta(minutes=45)
        hour_from_now_max = now + timedelta(minutes=75)
        params.extend([hour_from_now_min, hour_from_now_max])
        meeting_due_sql = """
        EXISTS (
            SELECT 1
            FROM meetings m
            JOIN dialogs d ON d.id = m.dialog_id
            JOIN recipients r ON r.id = d.recipient_id
            JOIN mailings ml ON ml.id = r.mailing_id
            LEFT JOIN meeting_reminders_sent mrs ON mrs.meeting_id = m.id
            WHERE d.account_id = a.id
              AND m.status = 'scheduled'
              AND m.start_at >= $3
              AND m.start_at <= $4
              AND mrs.id IS NULL
        )
        """

    morning_due_sql = "FALSE"
    if morning_enabled:
        params.append(now.date())
        date_param = "$5" if meeting_enabled else "$3"
        morning_due_sql = f"""
        EXISTS (
            SELECT 1
            FROM meetings m
            JOIN dialogs d ON d.id = m.dialog_id
            JOIN recipients r ON r.id = d.recipient_id
            JOIN mailings ml ON ml.id = r.mailing_id
            LEFT JOIN morning_reminders_sent mrs ON mrs.meeting_id = m.id
            WHERE d.account_id = a.id
              AND m.status = 'scheduled'
              AND m.start_at::date = {date_param}
              AND mrs.id IS NULL
        )
        """

    query = f"""
    WITH due AS (
        SELECT
            a.id,
            {meeting_due_sql} AS meeting_due,
            {morning_due_sql} AS morning_due,
            (
                SELECT MIN(m2.start_at)
                FROM meetings m2
                JOIN dialogs d2 ON d2.id = m2.dialog_id
                LEFT JOIN meeting_reminders_sent m2rs ON m2rs.meeting_id = m2.id
                WHERE d2.account_id = a.id
                  AND m2.status = 'scheduled'
                  AND m2.start_at >= $2
                  AND m2rs.id IS NULL
            ) AS next_meeting_at
        FROM accounts a
        WHERE a.project_id = $1
          AND a.status = 'good'
          AND a.busy = FALSE
          AND (a.lease_expires_at IS NULL OR a.lease_expires_at < $2)
    )
    SELECT id
    FROM due
    WHERE meeting_due OR morning_due
    ORDER BY meeting_due DESC, next_meeting_at ASC NULLS LAST, id ASC
    LIMIT {MAX_ACCOUNTS_PER_CYCLE};
    """

    rows = await conn.execute_query_dict(query, params)
    return [row["id"] for row in rows]


async def reserve_daily_limit(account_id: int, reserve: int, conn) -> int:
    if reserve <= 0:
        return 0

    rows = await conn.execute_query_dict(
        """
        UPDATE accounts
        SET daily_limit_left = daily_limit_left - $1
        WHERE id = $2
          AND daily_limit_left >= $1
        RETURNING daily_limit_left;
        """,
        [reserve, account_id],
    )

    if not rows:
        return 0

    # для аналитики / аудита
    await conn.execute_query(
        """
        INSERT INTO account_action_counter (account_id, action, date, count)
        VALUES ($1, $2, CURRENT_DATE, $3)
        ON CONFLICT (account_id, action, date)
        DO UPDATE SET count = account_action_counter.count + EXCLUDED.count;
        """,
        [account_id, enums.AccountAction.NEW_DIALOG, reserve],
    )

    return reserve


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


async def lock_account_and_recipients(
    account_id: int, recipients: list[orm.Recipient], now, conn
):
    account_lease = now + timedelta(minutes=ACCOUNT_LEASE_MINUTES)
    recipient_lease = now + timedelta(minutes=RECIPIENT_LEASE_MINUTES)
    ids = [r.id for r in recipients]

    updated = await (
        orm.Account.filter(id=account_id)
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


def minutes_left_in_send_window(project: orm.Project, now) -> int:
    start_h = project.send_time_start
    end_h = project.send_time_end

    today = now.date()
    tzinfo = now.tzinfo

    if start_h <= end_h:
        # окно внутри суток
        end_dt = datetime.combine(today, time(end_h), tzinfo=tzinfo)
    else:
        # окно через полночь
        if now.hour >= start_h:
            end_dt = datetime.combine(
                today + timedelta(days=1), time(end_h), tzinfo=tzinfo
            )
        else:
            end_dt = datetime.combine(today, time(end_h), tzinfo=tzinfo)

    if now >= end_dt:
        return 0

    return int((end_dt - now).total_seconds() // 60)


def ticks_left_in_send_window(project: orm.Project, now) -> int:
    minutes_left = minutes_left_in_send_window(project, now)
    return max(1, math.ceil(minutes_left / HEARTBEAT_MINUTES))


@heartbeat.task()
async def task(input: EmptyModel, ctx: Context):
    await ensure_reminder_tables()
    await complete_old_dialogs()
    await unmute_accounts()
    await release_recipients()
    await cleanup_stale_locks()

    # убрать после всех изменений
    """premium_accounts_with_auto_renew = await orm.Account.filter(
        busy=False, premium=True, premium_stopped=False
    ).all()
    if premium_accounts_with_auto_renew:
        for a in premium_accounts_with_auto_renew:
            await stop_premium_task.aio_run_no_wait(
                input=StopPremiumIn(account_id=a.id)
            )
            ctx.log(f"отменяем премиум для {a.id}")

        return"""

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
            and m.active is True
        ]

        async with in_transaction() as conn:
            reminder_account_ids = await get_accounts_with_due_reminders(project, now, conn)

            if not active_mailings and not reminder_account_ids:
                continue

            free_accounts = await get_available_accounts(project, now, conn)
            if not free_accounts:
                continue

            accounts_by_id = {acc.id: acc for acc in free_accounts}
            prioritized_accounts = [
                accounts_by_id[acc_id]
                for acc_id in reminder_account_ids
                if acc_id in accounts_by_id
            ]
            prioritized_ids = {acc.id for acc in prioritized_accounts}
            regular_accounts = [acc for acc in free_accounts if acc.id not in prioritized_ids]
            accounts_queue = prioritized_accounts + regular_accounts

            # Проверяем закрытие рассылок только если они есть
            if active_mailings:
                for mailing in active_mailings:
                    info = await check_and_close_mailing(mailing, now, conn)
                    if info:
                        notify_queue.append(info)

                # Аккаунты могли закрыть mailings → фильтруем
                active_mailings = [
                    m
                    for m in active_mailings
                    if m.status
                    in (enums.MailingStatus.RUNNING, enums.MailingStatus.DRAFT)
                ]

            has_active_mailings = bool(active_mailings)

            for acc in accounts_queue:
                if in_send_window and has_active_mailings and acc.daily_limit_left > 0:
                    ticks_left = ticks_left_in_send_window(project, now)

                    dialogs_left = acc.daily_limit_left // ticks_left
                    if dialogs_left <= 0:
                        dialogs_left = 1

                    dialogs_left = min(dialogs_left, acc.daily_limit_left)
                else:
                    dialogs_left = 0

                # Получаем recipients для новых диалогов ТОЛЬКО если в окне отправки
                recipients = []
                if in_send_window and has_active_mailings:
                    recipients = await get_recipients_for_mailings(
                        active_mailings, dialogs_left, now, conn
                    )

                # Резервируем лимит новых диалогов атомарно
                reserved = 0
                if recipients:
                    reserved = await reserve_daily_limit(acc.id, len(recipients), conn)
                    if reserved < len(recipients):
                        recipients = recipients[:reserved]

                # Статус DRAFT → RUNNING, если есть recipients (только в окне отправки)
                if in_send_window and has_active_mailings:
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
                if not await lock_account_and_recipients(acc.id, recipients, now, conn):
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
