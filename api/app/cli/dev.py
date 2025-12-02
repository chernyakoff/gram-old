from cyclopts import App
from rich import print

from app.common.models.orm import Proxy
from app.dto.proxy import ProxyOut

app = App(name="dev", help="dev tests etc")


@app.default
async def test():
    user_id = 359107176
    hz = await ProxyOut.from_queryset(
        Proxy.filter(user_id=user_id).prefetch_related("accounts")
    )
    print(hz)
