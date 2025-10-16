from cyclopts import App
from rich import print

from app.tasks.proxies.model import Proxy

app = App(name="dev", help="dev tests etc")

proxy_line = "109.236.82.42:9999:hmzqaove2v-mobile-country-RU-state-536203-city-498817-hold-query:nSBjWvFSer8uwjOU"


@app.command
async def test():
    p = Proxy.from_line(proxy_line)
    ip = await p.check()

    print(ip)
    if ip:
        country = await p.get_country(ip)
        print(country)
