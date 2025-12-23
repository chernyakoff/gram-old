from cyclopts import App
from rich import print
from tortoise import timezone as tz
from tortoise.expressions import Q

from app.common.models import enums, orm

app = App(name="heartbeat", help="dev tests etc")


MAX_ACCOUNTS_PER_CYCLE = 50


async def debug_heartbeat_for_user(user_id: int):
    now = tz.now()
    print("=" * 80)
    print(f"[DEBUG] Heartbeat DRY-RUN for user_id={user_id}")
    print(f"[DEBUG] Now: {now}")
    print("=" * 80)

    projects = await orm.Project.filter(
        status=True,
        user_id=user_id,
        user__balance__gt=1000,
    ).prefetch_related("mailings", "user")

    if not projects:
        print("❌ Нет активных проектов или недостаточно баланса")
        return

    for project in projects:
        print("\n" + "-" * 60)
        print(f"📦 Project #{project.id} «{project.name}»")

        in_window = is_project_in_send_window(project, now)
        print(f"⏱ Send window: {project.send_time_start}-{project.send_time_end}")
        print(f"➡ In send window: {in_window}")

        mailings = [
            m
            for m in project.mailings
            if m.status in (enums.MailingStatus.RUNNING, enums.MailingStatus.DRAFT)
        ]

        if not mailings:
            print("❌ Нет активных рассылок")
            continue

        print(f"📨 Активных рассылок: {len(mailings)}")
        for m in mailings:
            print(f"   - Mailing #{m.id} [{m.status}] {m.name}")

        accounts = await orm.Account.filter(
            project=project,
            active=True,
            premium=True,
            status=enums.AccountStatus.GOOD,
            busy=False,
        ).limit(MAX_ACCOUNTS_PER_CYCLE)

        if not accounts:
            print("❌ Нет свободных аккаунтов")
            continue

        print(f"👤 Свободных аккаунтов: {len(accounts)}")

        for acc in accounts:
            print("\n" + "." * 40)
            print(f"👤 Account #{acc.id}")

            dialogs_left = await get_dialogs_left(acc, now)
            print(f"📊 Остаток дневного лимита: {dialogs_left}")

            if dialogs_left <= 0:
                print("❌ Лимит исчерпан")
                continue

            recipients = []
            if in_window:
                recipients = await get_recipients(mailings, dialogs_left, now)
                print(f"🎯 Найдено recipients: {len(recipients)}")
            else:
                print("⏳ Не в окне отправки — новых recipients не берём")

            print("🔒 ПРОВЕРКА ЛОГИКИ ЗАПУСКА TASK")
            print("   → dialog_task ДОЛЖЕН быть запущен ВСЕГДА")
            print("   → recipients_id:", [r.id for r in recipients])

            print("🚫 DRY-RUN: task НЕ запускается")
            print("🚫 DRY-RUN: база НЕ меняется")
            print("🚫 DRY-RUN: уведомления НЕ отправляются")

    print("\n✅ DEBUG RUN COMPLETED")


def is_project_in_send_window(project, now):
    h = now.hour
    if project.send_time_start <= project.send_time_end:
        return project.send_time_start <= h <= project.send_time_end
    return h >= project.send_time_start or h <= project.send_time_end


async def get_dialogs_left(account, now):
    counter = await orm.AccountActionCounter.filter(
        account=account,
        action=enums.AccountAction.NEW_DIALOG,
        date=now.date(),
    ).first()

    used = counter.count if counter else 0
    return max(0, account.out_daily_limit - used)


async def get_recipients(mailings, limit, now):
    result = []
    for mailing in mailings:
        if len(result) >= limit:
            break

        found = (
            await orm.Recipient.filter(
                mailing=mailing,
                status=enums.RecipientStatus.PENDING,
            )
            .filter(Q(lease_expires_at__lt=now) | Q(lease_expires_at__isnull=True))
            .limit(limit - len(result))
        )

        result.extend(found)

    return result


@app.default
async def _(id: str):
    if id.isdigit():
        user = await orm.User.get_or_none(id=id)
    else:
        user = await orm.User.get_or_none(username=id.removeprefix("@"))
    if not user:
        print("Пользователь не найден")
        return

    await debug_heartbeat_for_user(user.id)
