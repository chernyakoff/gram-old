from datetime import datetime

from cyclopts import App
from rich import print
from tortoise import timezone as tz
from tortoise.expressions import Q

from app.common.models import enums, orm

app = App(name="heartbeat", help="dev tests etc")

MAX_ACCOUNTS_PER_USER_PER_CYCLE = 5  # можно взять из конфига
MAX_ACCOUNTS_PER_CYCLE = 50


def is_project_in_send_window(project, now):
    h = now.hour
    if project.send_time_start <= project.send_time_end:
        return project.send_time_start <= h <= project.send_time_end
    return h >= project.send_time_start or h <= project.send_time_end


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

        # Берём все доступные аккаунты
        all_accounts = await orm.Account.filter(
            project=project,
            active=True,
            status=enums.AccountStatus.GOOD,
            busy=False,
        ).all()

        if not all_accounts:
            print("❌ Нет свободных аккаунтов")
            continue

        # Round-robin по пользователям с учётом per-user лимита
        accounts_by_user = {}
        for acc in all_accounts:
            accounts_by_user.setdefault(acc.user_id, []).append(acc)

        selected_accounts = []
        for uid, acc_list in accounts_by_user.items():
            # сортировка: сначала с лимитом, потом по last_attempt_at, потом по id
            acc_list.sort(
                key=lambda a: (
                    -(a.daily_limit_left > 0),  # True > False
                    a.last_attempt_at
                    or datetime(
                        1970, 1, 1
                    ),  # "datetime" is not exported from module "tortoise.timezone"
                    a.id,
                )
            )
            selected_accounts.extend(acc_list[:MAX_ACCOUNTS_PER_USER_PER_CYCLE])

        # Ограничиваем по глобальному максимуму
        selected_accounts = selected_accounts[:MAX_ACCOUNTS_PER_CYCLE]

        print(f"👤 Всего выбранных аккаунтов для task: {len(selected_accounts)}")

        for acc in selected_accounts:
            print("\n" + "." * 40)
            print(f"👤 Account #{acc.id} ({acc.display_username})")
            print(f"🗓 Активных дней: {acc.active_days_count}")
            is_dynamic = acc.active_days_count < len(acc.PROGREV)
            print(f"⚡ Лимит динамический: {is_dynamic}")
            print(f"📊 Остаток дневного лимита: {acc.daily_limit_left}")

            if acc.daily_limit_left <= 0:
                print("❌ Лимит исчерпан")
                continue

            recipients = []
            if in_window:
                recipients = await get_recipients(mailings, acc.daily_limit_left, now)
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
