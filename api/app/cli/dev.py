import httpx
from aiopath import AsyncPath
from cyclopts import App
from rich import print

from app.common.utils.usd_rate import get_usd_rate

app = App(name="dev", help="dev tests etc")


@app.default
async def _():
    async with httpx.AsyncClient(
        proxy="socks5://sazanova-nadezda_ya_ru:6072b7fd12@85.31.51.249:30042"
    ) as c:
        r = await c.get("https://ifconfig.me")
        print(r.text)
