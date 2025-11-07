import asyncio
import logging
from typing import cast

from cyclopts import App
from rich import print
from telethon import types
from tortoise import timezone as tz
from tortoise.transactions import in_transaction

from app.common.models import enums, orm
from app.tasks.accounts.model import Account
from app.tasks.heartbeat.task import get_active_projects, get_available_accounts
from app.tasks.proxies.model import Proxy
from app.tasks.proxies.pool import ProxyPool
from app.tasks.proxies.utils import get_user_proxies

logging.basicConfig(
    level=logging.WARNING,  # или DEBUG для больше боли
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)


app = App(name="heartbeat", help="dev tests etc")


@app.command
async def test():
    now = tz.now()
    projects = await get_active_projects()
    print(f"Надено {len(projects)} проектов")

    for project in projects:
        active_mailings = [
            m
            for m in project.mailings
            if m.status in (enums.MailingStatus.RUNNING, enums.MailingStatus.DRAFT)
        ]
        print(f"В проекте {project.id} найдено {len(active_mailings)} рассылок")
        async with in_transaction() as conn:
            # Получаем свободные аккаунты
            free_accounts = await get_available_accounts(project, now, conn)

            print(f"Нашлось {len(free_accounts)} свободных аккаунтов")
