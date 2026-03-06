from utils.cyclopts import create_app

from utils.functions import generate_message

app = create_app("dev", "dev tests etc")

MSG = """

{Привет|Здравствуйте}, {друг|товарищ|{уважаемый|дорогой} коллега}!
Сегодня у нас {важное|интересное|особое} сообщение.
{Будьте готовы|Приготовьтесь} к {новому вызову|открытию|{сюрпризу|интригующему событию}}!

"""


@app.default
async def _():
    for _ in range(9):
        print(generate_message(MSG.strip()))
        print("-" * 10)
