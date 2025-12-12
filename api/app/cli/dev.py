from aiopath import AsyncPath
from cyclopts import App
from rich import print

from app.common.models import orm
from app.common.utils.functions import generate_message, randomize_message
from app.common.utils.prompt import get_status_addon

app = App(name="dev", help="dev tests etc")


TEXT = """
{Здравствуйте! 👋|Добрый день! ☀️|Приветствую! 🤝}

{Вижу|Заметил|Обратил внимание}, что {Вы глубоко в теме|Вы разбираетесь в вопросах|Вам близка тема} **{ЗОЖ|правильного питания|биохакинга|оздоровления}**. 🌱

{Есть вопрос к Вам как к практику|Интересно Ваше мнение|Можно один вопрос}, {если найдется минутка|если Вы не против}. 🧐

{Скажите,|Подскажите,} выбирая {БАДы|витамины|витаминные комплексы}, Вы {смотрите только на **состав**|цените **натуральность**} 💊 или {Вам важнее **биодоступность**|учитываете **реальное усвоение**|проверяете **доставку в клетку**}? 🧬

{Есть статистика,|Многие говорят,|Известно,} что {у обычных форм **КПД всего 10–30%**|стандартные витамины **почти не усваиваются**}, {а остальное — «на ветер»|и это пустая переплата}. 📉

{Что думаете об этом?|Как решаете этот момент?|Это критично для Вас или нет?}
"""


@app.default
async def _():
    m = generate_message(TEXT)
    m = randomize_message(m)
    print(m)


async def get_generator_prompt() -> str:
    return await AsyncPath("app/common/utils/prompts/generator.txt").read_text()


async def get_system_prompt() -> str:
    return await AsyncPath("app/common/utils/prompts/status_addon.txt").read_text()


@app.command
async def update_prompts():
    system = await get_system_prompt()
    generator = await get_generator_prompt()
    await orm.AppSettings.upsert("prompt.generator", generator)
    await orm.AppSettings.upsert("prompt.system", system)
