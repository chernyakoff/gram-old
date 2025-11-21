import hashlib
import hmac

from cyclopts import App
from rich import print

from app.common.models.orm import Project, User
from app.common.utils.prompt import build_prompt
from app.config import config

app = App(name="dev", help="dev tests etc")


raw_users = """
@sanatpr
@web5050
@maestro9119
@Fox_23
@egor2358
@Sergei_irk38
@lizenzia_777
@DmitrijShamro
@Ann_Labanceva
@simakova_ya
@Nata_lya_tg
@andylipatov
@topdog_everyday
@PotashevMaxim
@ArinaKuriyanova
@BPNM8
@dhanividjaya
@evgeniya_atp
@OVS8888
@droshnev
@asn341
@ignatevaolgavl
@davydov86
@love_1008sv
@Dmitrich4
@Nata_lya_tg
@fedor_tep
@Kat_kat99
@irbe88
@kwingroup
@prostatuss
@natalia_kartashova
@mnadirbegov
@Tatyana_Pushkina5
@traker_happines
"""


@app.command
async def license():
    usernames = [u.strip().removeprefix("@") for u in raw_users.strip().splitlines()]
    orm_users = await User.filter(username__in=usernames).all()
    for orm_user in orm_users:
        await orm_user.extend_license(3650)
        print(orm_user.username)
