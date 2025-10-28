import asyncio
import json
import re

from aiopath import AsyncPath
from html_to_markdown import convert

from app.common.models.enums import DialogStatus
from app.common.models.orm import AppSettings

PROMPT_TITLES = {
    "role": "РОЛЬ",
    "instruction": "ИНСТРУКЦИЯ",
    "context": "КОНТЕКСТ",
    "init": "STAGE 1: INIT",
    "engage": "STAGE 2: ENGAGE",
    "offer": "STAGE 3: OFFER",
    "closing": "STAGE 4: CLOSING",
    "transitions": "СИСТЕМА ПЕРЕХОДОВ МЕЖДУ STAGE",
    "rules": "ГЛОБАЛЬНЫЕ ПРАВИЛА",
}


TRANSITIONS = """
<table>\n <thead>\n <tr>\n <th>От</th>\n <th>К</th>\n <th>Условие</th>\n <th>Промежуточный текст</th>\n </tr>\n </thead>\n <tbody>\n <tr>\n <td><strong>INIT</strong></td>\n <td><strong>ENGAGE</strong></td>\n <td>goalMet: true (конкретное направление получено)</td>\n <td>&quot;Звучит интересно! Расскажи подробнее...&quot;</td>\n </tr>\n <tr>\n <td><strong>ENGAGE</strong></td>\n <td><strong>OFFER</strong></td>\n <td>goalMet: true (детали и боли услышаны)</td>\n <td>&quot;Спасибо за честность. Вижу, что [боль]...&quot;</td>\n </tr>\n <tr>\n <td><strong>OFFER</strong></td>\n <td><strong>CLOSING</strong></td>\n <td>goalMet: true (четкое согласие получено)</td>\n <td>&quot;Отлично! Давай запишемся...&quot;</td>\n </tr>\n <tr>\n <td><strong>CLOSING</strong></td>\n <td><strong>COMPLETE</strong></td>\n <td>goalMet: true (все данные собраны)</td>\n <td>&quot;Спасибо, [имя]! До встречи!&quot;</td>\n </tr>\n </tbody>\n</table>
"""


async def get_default_prompt():
    first_message = await AppSettings.get(section="prompt", name="first_message")
    json_prompt = await AppSettings.get(section="prompt", name="json")
    result = json.loads(json_prompt.value)
    result["first_message"] = first_message.value

    return result


def get_ooc_status(message: str) -> DialogStatus | None:
    match = re.search(r"OOC_STATUS:\s*(init|engage|offer|closing)", message)
    if match:
        status = match.group(1)
        return DialogStatus(status)


def strip_ooc_status(message: str) -> str:
    return re.sub(r"OOC_STATUS:.*", "", message).strip()


STATUS_ADDON = """
# Текущий статус диалога: {current_status}

После ответа выполни OOC-анализ (вне контекста):

- Проверь, достигнута ли цель текущего статуса {current_status} на основе всего диалога.
- Если цель достигнута — верни новый статус (следующий по порядку: init -> engage -> offer -> closing).
- Если нет — верни текущий статус.
- Добавь в конец ответа строку: OOC_STATUS: [статус]

Пример: Если в init ты поприветствовал и задал вопрос, а пользователь ответил — цель достигнута, верни engage.
"""


def get_status_addon(status: DialogStatus) -> str:
    return STATUS_ADDON.replace("{current_status}", status.value)


async def build_prompt(prompt: dict, status: DialogStatus = DialogStatus.INIT):
    html = []
    statuses = {s.value for s in DialogStatus}
    for key, title in PROMPT_TITLES.items():
        if key not in statuses:
            title = f"<h1>{title}</h1>"
            block = f"{title}{prompt[key]}"
            html.append(block)
        elif key == status:
            block = f"<h1>{title}</h1><p>=== СТАТУС СИСТЕМЫ ===</p>{prompt[key]}"
            html.append(block)

    markdown = await asyncio.to_thread(convert, "<hr>".join(html))
    markdown = markdown.replace("{current_status}", status.value)
    return markdown
