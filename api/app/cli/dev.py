from cyclopts import App
from html_to_markdown import convert
from rich import print

from app.common.models.orm import Brief, Project, Prompt, Proxy, User
from app.common.utils.functions import pick, randomize_message
from app.dto.proxy import ProxyOut

app = App(name="dev", help="dev tests etc")


@app.default
async def test():
    user_id = 359107176
    hz = await ProxyOut.from_queryset(
        Proxy.filter(user_id=user_id).prefetch_related("accounts")
    )
    print(hz)
