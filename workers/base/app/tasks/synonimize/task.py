from datetime import timedelta
from typing import Optional

from hatchet_sdk import Context
from pydantic import BaseModel

from app.client import hatchet
from app.common.models.orm import AppSettings, User
from app.common.utils import openrouter

PROMPT = """
Преобразуй следующее сообщение в вариант с синонимами и альтернативными формулировками, используя конструкцию {вариант1|вариант2|...} для всех возможных замен слов и фраз. 
- Сохраняй исходную структуру предложений. 
- Подбирай естественные синонимы, чтобы текст оставался понятным. 
- При возможности предлагай 2-4 варианта для каждого ключевого слова или фразы.

COOБЩЕНИЕ:
"""


class SynonimizeIn(BaseModel):
    user_id: int
    text: str


class SynonimizeOut(BaseModel):
    text: str
    error: Optional[str] = None


@hatchet.task(
    name="synonimize",
    input_validator=SynonimizeIn,
    execution_timeout=timedelta(minutes=20),
    schedule_timeout=timedelta(minutes=20),
)
async def synonimize(data: SynonimizeIn, ctx: Context) -> SynonimizeOut:
    ctx.log("Запущена рандомизация")
    prompt = await AppSettings.fetch("prompt.randomizer")
    if not prompt:
        prompt = PROMPT

    user = await User.get(id=data.user_id)
    try:
        messages = [{"role": "user", "content": f"{prompt}\n\n{data.text}"}]
        text = await openrouter.create_response(user, messages)
        return SynonimizeOut(text=text)
    except Exception as e:
        ctx.log(str(e))
        return SynonimizeOut(text="", error=str(e))
