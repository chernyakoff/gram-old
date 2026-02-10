from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta

from hatchet_sdk import ConcurrencyExpression, ConcurrencyLimitStrategy, Context
from pydantic import BaseModel
from tortoise import timezone as tz

from app.client import hatchet
from app.common.models import orm
from app.utils.logger import Logger

from .account_session import AccountSession
from .flow import DialogFlow
from .telegram_service import TelegramService

MAX_SESSION_HOURS = 6


class DialogIn(BaseModel):
    account_id: int
    recipients_id: list[int]
    key: str


@dataclass
class DialogTaskDeps:
    logger: Logger
    account: orm.Account
    session: AccountSession
    telegram: TelegramService
    flow: DialogFlow
    stop_event: asyncio.Event
    end_time: datetime


@hatchet.task(
    name="dialog_v1",
    input_validator=DialogIn,
    execution_timeout=timedelta(hours=MAX_SESSION_HOURS),
    schedule_timeout=timedelta(hours=MAX_SESSION_HOURS),
    concurrency=ConcurrencyExpression(
        expression="input.key",
        max_runs=1,
        limit_strategy=ConcurrencyLimitStrategy.CANCEL_NEWEST,
    ),
)
async def dialog_task(input: DialogIn, ctx: Context):
    """
    Skeleton entrypoint.
    TODO: Move orchestration from dialogs_v1/task.py into DialogTaskRunner.
    """
    runner = DialogTaskRunner()
    await runner.run(input, ctx)


class DialogTaskRunner:
    """
    Orchestrates lifecycle of dialog task.
    """

    async def run(self, input: DialogIn, ctx: Context):
        deps = await self._bootstrap(input, ctx)
        if not deps:
            return

        try:
            await self._process_initial_dialogs(input, deps)
            await self._wait_loop(deps)
        finally:
            await self._cleanup(deps)

    async def _bootstrap(self, input: DialogIn, ctx: Context) -> DialogTaskDeps | None:
        """
        - load account
        - build session + gateway + flow
        - connect / authorize
        """
        logger = Logger(ctx)

        account = await orm.Account.get(id=input.account_id).prefetch_related(
            "user", "proxy"
        )
        if not account:
            return None

        stop_event = asyncio.Event()
        start_time = tz.now()
        end_time = start_time + timedelta(hours=MAX_SESSION_HOURS)

        session = AccountSession(account, logger)
        ok = await session.connect_and_authorize()
        if not ok:
            return None

        telegram = TelegramService(session.client, logger)  # type:ignore
        flow = DialogFlow(account, telegram, logger, stop_event)

        return DialogTaskDeps(
            logger=logger,
            account=account,
            session=session,
            telegram=telegram,
            flow=flow,
            stop_event=stop_event,
            end_time=end_time,
        )

    async def _process_initial_dialogs(self, input: DialogIn, deps: DialogTaskDeps):
        """
        - process existing dialogs
        - start new dialogs for input recipients
        """
        await deps.flow.process_existing_dialogs()
        await deps.flow.start_new_dialogs(input.recipients_id, end_time=deps.end_time)

    async def _wait_loop(self, deps: DialogTaskDeps):
        """
        - wait until stop_event or timeout
        - periodic checks
        """
        await deps.flow.wait_for_replies(end_time=deps.end_time)

    async def _cleanup(self, deps: DialogTaskDeps):
        """
        - cancel timers/tasks
        - disconnect client
        - release account
        """
        await deps.flow.shutdown()
        await deps.session.disconnect()
