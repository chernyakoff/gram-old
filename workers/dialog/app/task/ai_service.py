import re

from openai import AsyncOpenAI

from app.common.models import enums, orm
from app.config import config
from app.utils.logger import Logger


class AIService:
    """Сервис для работы с AI"""

    def __init__(self):
        params = {
            "api_key": config.openai.api_key,
            "timeout": config.openai.timeout,
        }
        if config.openai.base_url:
            params["base_url"] = config.openai.base_url

        self.client = AsyncOpenAI(**params)
        self.model = config.openai.model

    async def get_response_with_status(
        self, project_prompt: str, dialog_messages: list[orm.Message], logger: Logger
    ) -> tuple[str | None, enums.DialogStatus | None]:
        """Получает ответ от AI и определяет статус диалога"""

        history = self._build_history(dialog_messages)
        system_prompt = self._build_system_prompt(project_prompt)
        messages = [{"role": "system", "content": system_prompt}] + history

        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
            )
            response = completion.choices[0].message.content

            if not response:
                return None, None

            text, status = self._parse_response(response, logger)
            return text, status

        except Exception as e:
            logger.error(f"Ошибка AI запроса: {e}")
            return None, None

    def _build_history(self, messages: list[orm.Message]) -> list[dict]:
        """Формирует историю сообщений для AI"""
        history = []
        for msg in messages:
            role = "assistant" if msg.sender == enums.MessageSender.ACCOUNT else "user"
            history.append({"role": role, "content": msg.text})
        return history

    def _build_system_prompt(self, project_prompt: str) -> str:
        """Формирует системный промпт с инструкциями по статусам"""
        return f"""{project_prompt}

ВАЖНО: После каждого ответа укажи статус диалога на отдельной строке в формате:
STATUS: [один из: init, engage, offer, close]

Критерии:
- init: первое взаимодействие, приветствие
- engage: получатель проявляет интерес, задаёт вопросы, ведёт диалог
- offer: сделано конкретное предложение (цена, условия, призыв к действию)
- close: диалог завершён (отказ, договорённость достигнута, потеря интереса, или собеседник игнорирует)

ОБЯЗАТЕЛЬНО добавляй строку STATUS после каждого своего ответа!
"""

    def _parse_response(
        self, response: str, logger: Logger
    ) -> tuple[str, enums.DialogStatus | None]:
        """Парсит ответ AI и извлекает статус"""

        status = None
        text = response

        # Ищем паттерн "STATUS: xxx" (регистронезависимо)
        match = re.search(
            r"STATUS:\s*(init|engage|offer|close)", response, re.IGNORECASE
        )

        if match:
            status_str = match.group(1).lower()
            # Убираем строку со статусом из текста
            text = re.sub(
                r"\n?\s*STATUS:\s*(init|engage|offer|close)\s*\n?",
                "",
                response,
                flags=re.IGNORECASE,
            ).strip()

            # Маппинг строки на enum
            status_map = {
                "init": enums.DialogStatus.INIT,
                "engage": enums.DialogStatus.ENGAGE,
                "offer": enums.DialogStatus.OFFER,
                "close": enums.DialogStatus.CLOSE,
            }

            status = status_map.get(status_str)

            if status:
                logger.info(f"AI установил статус: {status_str}")
            else:
                logger.warning(f"Неизвестный статус от AI: {status_str}")
        else:
            logger.warning(f"AI не вернул статус. Ответ: {response[:100]}...")

        return text, status
