from cyclopts import App

app = App(name="dev", help="dev tests etc")


@app.default
async def _():
    print("hello, dev")
