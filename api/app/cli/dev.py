from enum import StrEnum
from itertools import product

import httpx
from aiopath import AsyncPath
from cyclopts import App
from rich import print

from app.common.models import orm
from app.common.utils.prompt import (
    ProjectSkipOptions,
    build_prompt_v2,
    get_active_status,
    get_status_info,
)

app = App(name="dev", help="dev tests etc")


class DialogStatus(StrEnum):
    INIT = "init"  # приветствие
    ENGAGE = "engage"  # проявил интерес
    OFFER = "offer"  # сделали предложение
    CLOSING = "closing"  # завершено (отказ / интерес / договорились о звонке)


@app.default
async def _():
    orm_prompt = await orm.Prompt.get(id=17)
    prompt_dict = orm_prompt.to_dict()

    statuses = list(DialogStatus)

    # все комбинации True/False для engage / offer / closing
    skip_variants = list(product([False, True], repeat=3))

    for status in statuses:
        for engage, offer, closing in skip_variants:
            skip_options = ProjectSkipOptions(
                engage=engage,
                offer=offer,
                closing=closing,
            )
            print(
                f"\nSTATUS={status.value} SKIP(engage={engage}, offer={offer}, closing={closing})"
            )
            active_status = get_active_status(status, skip_options)

            prompt = build_prompt_v2(
                prompt_dict,
                active_status,
            )

            print(prompt)

            status_info = get_status_info(active_status, skip_options)

            print(status_info)

            print("-" * 10)


@app.command
async def ppp():
    orm_prompt = await orm.Prompt.get(id=17)
    prompt_dict = orm_prompt.to_dict()
    status = DialogStatus.OFFER
    skip_options = ProjectSkipOptions(
        engage=True,
        offer=True,
        closing=False,
    )
    active_status = get_active_status(status, skip_options)
    prompt = build_prompt_v2(
        prompt_dict,
        active_status,
    )
    print(prompt)

    status_info = get_status_info(active_status, skip_options)

    print(status_info)

    print("-" * 10)
