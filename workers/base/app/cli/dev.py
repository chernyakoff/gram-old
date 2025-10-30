from datetime import timedelta

from cyclopts import App
from hatchet_sdk import Context, EmptyModel
from pydantic import BaseModel
from rich import print
from tortoise import timezone as tz
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.client import hatchet
from app.common.models import enums, orm

LEASE_HOURS = 6  # сколько "занятый" аккаунт считается занятым
MAX_ACCOUNTS_PER_CYCLE = 50  # сколько аккаунтов проверяем за 1 тик
RECIPIENT_LEASE_MINUTES = 30  # время аренды recipient перед отправкой в таск


app = App(name="dev", help="dev tests etc")


@app.command
async def test():
    now = tz.now()

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
            print("НЕТ АКТИВНЫХ РАССЫЛОК")
            continue

        print("ЕСТЬ АКТИВЫЕ РАССЫЛКИ")

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
                print("НЕТ СВОБОДНЫХ АККАУНТОВ")
                continue

            print("ЕСТЬ СВОБОДНЫЕ АККАУНТЫ")
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

                print(f"{acc.id} - {dialogs_left}  диалогов осталось сегодня")

                if dialogs_left <= 0:
                    continue

                print(f"{acc.id} не осталось диалогов пропускаем")

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

                print(recipients_to_assign)
