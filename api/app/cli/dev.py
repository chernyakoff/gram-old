from cyclopts import App
from html_to_markdown import convert
from rich import print

from app.common.models.orm import Brief, Project, Prompt, User
from app.common.utils.functions import pick, randomize_message

app = App(name="dev", help="dev tests etc")


@app.default
async def test():
    text = "Здравствуйте, замечаю, что вы эксперт - мы собраны с вами в одном чате-канале, сейчас подбираем партнеров, которым готовы отдавать от 100 заявок в месяц, стоимость лида начинается обычно у нас от 40 российских рублей. Это получается благодаря искусственному интеллекту. Вам это актуально? С почтением Давид!"

    print(randomize_message(text))
    pass
