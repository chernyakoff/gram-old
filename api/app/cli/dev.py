import hashlib
import hmac

from app.common.models.orm import Project, User
from app.common.utils.prompt import build_prompt
from app.config import config
from cyclopts import App
from rich import print

app = App(name="dev", help="dev tests etc")


raw_users = """
@happy_best
@asn341
@VadimSanychRu
@trafic_garant
@otvety_slav_bogov
"""


@app.command
async def license():
    usernames = [u.strip().removeprefix("@") for u in raw_users.strip().splitlines()]
    orm_users = await User.filter(username__in=usernames).all()
    for orm_user in orm_users:
        await orm_user.extend_license(3650)
        print(orm_user.username)
