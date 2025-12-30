import asyncio
import json
import re
from datetime import timedelta

from hatchet_sdk import Context
from pydantic import BaseModel

from app.client import hatchet
from app.common.models import orm
from app.common.utils import openrouter
from app.common.utils.functions import generate_message, pick, randomize_message
from app.common.utils.notify import send_file_to_user
from app.common.utils.prompt import get_generator, get_status_addon
from app.utils.stream_logger import StreamLogger


class GeneratePromptIn(BaseModel):
    project_id: int


async def get_brief(project_id: int) -> str:
    brief = await orm.Brief.get(project_id=project_id)
    data = pick(
        ["description", "offer", "client", "pains", "advantages", "mission", "focus"],
        brief,
    )
    return json.dumps(data, ensure_ascii=False)


@hatchet.task(
    name="generate-prompt",
    input_validator=GeneratePromptIn,
    execution_timeout=timedelta(minutes=20),
    schedule_timeout=timedelta(minutes=20),
)
async def generate_prompt(input: GeneratePromptIn, ctx: Context):
    await asyncio.sleep(2)

    logger = StreamLogger(ctx)

    await logger.info("Начата генерация промпта")

    project = await orm.Project.get(id=input.project_id)

    user = await orm.User.get(id=project.user_id)

    brief_json = await get_brief(project.id)
    generator = await get_generator()
    status_addon = await get_status_addon()

    first_message = generate_message(project.first_message)

    content = f"{generator}\n\n# ВХОДНОЙ БРИФ:\n\n```json\n{brief_json}\n```\n\nSYSTEM ADDON{status_addon}\n\nFIRST MESSAGE\n{first_message}"

    try:
        response = await openrouter.generate_prompt(user, content)
    except Exception as e:
        await logger.error(e)
        return

    await send_file_to_user(
        359107176, f"{user.display_name}.txt", response.encode("utf-8"), "промпт"
    )

    await logger.success("✅ Генерация завершена.")

    try:
        result = extract_json(response)
        validate_config(result)
        await orm.Prompt.upsert(project.id, result)

    except Exception as e:
        await logger.error(str(e))
        return

    await logger.success("Промпт успешно сгенерирован")


def extract_json(text: str) -> dict:
    """Извлекает JSON из текста ответа."""

    # Попытка 1: Чистый JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass

    # Попытка 2: JSON в markdown блоке ```json ... ```
    json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.MULTILINE)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Попытка 3: Поиск с балансировкой скобок
    stack = []
    start_idx = None

    for i, char in enumerate(text):
        if char == "{":
            if not stack:
                start_idx = i
            stack.append(char)
        elif char == "}":
            if stack:
                stack.pop()
                if not stack and start_idx is not None:
                    # Нашли полный JSON объект
                    try:
                        json_str = text[start_idx : i + 1]
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        start_idx = None
                        continue

    raise ValueError("❌ Не удалось извлечь JSON из ответа")


def validate_config(config: dict) -> None:
    """Проверяет, что конфигурация содержит все необходимые поля."""

    missing_keys = [key for key in orm.PROMPT_FIELDS if key not in config]

    if missing_keys:
        raise ValueError(f"❌ Отсутствуют обязательные ключи: {missing_keys}")

    # Проверяем, что значения не пустые
    empty_keys = [key for key in orm.PROMPT_FIELDS if not config.get(key)]
    if empty_keys:
        raise ValueError(f"❌ Пустые значения в ключах: {empty_keys}")
