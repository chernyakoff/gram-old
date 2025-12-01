from datetime import timedelta

from hatchet_sdk import Context
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.client import hatchet
from app.config import config

PROMPT = """
Преобразуй следующее сообщение в вариант с синонимами и альтернативными формулировками, используя конструкцию {вариант1|вариант2|...} для всех возможных замен слов и фраз. 
- Сохраняй исходную структуру предложений. 
- Подбирай естественные синонимы, чтобы текст оставался понятным. 
- При возможности предлагай 2-4 варианта для каждого ключевого слова или фразы.

COOБЩЕНИЕ:
"""


class SynonimizeIn(BaseModel):
    text: str


class SynonimizeOut(BaseModel):
    text: str


def get_openai() -> AsyncOpenAI:
    params = {
        "api_key": config.openai.api_key,
        "timeout": config.openai.timeout,
    }
    if config.openai.base_url:
        params["base_url"] = config.openai.base_url
    return AsyncOpenAI(**params)


async def get_completion(text: str) -> str:
    completion = await get_openai().responses.create(
        model="gpt-4.1-mini", input=f"{PROMPT}\n\n{text}"
    )
    return completion.output_text


@hatchet.task(
    name="synonimize",
    input_validator=SynonimizeIn,
    execution_timeout=timedelta(minutes=20),
    schedule_timeout=timedelta(minutes=20),
)
async def synonimize(data: SynonimizeIn, ctx: Context) -> SynonimizeOut:
    ctx.log("Запущена рандомизация")
    try:
        text = await get_completion(data.text)
        return SynonimizeOut(text=text)
    except Exception as e:
        ctx.log(str(e))
        return SynonimizeOut(text="")
