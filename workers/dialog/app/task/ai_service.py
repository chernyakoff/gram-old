import re

from openai import AsyncOpenAI

from app.common.models import enums, orm
from app.common.utils.prompt import (
    build_prompt,
    get_ooc_status,
    get_status_addon,
    strip_ooc_status,
)
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
        self,
        project_prompt: dict,
        status: enums.DialogStatus,
        dialog_messages: list[orm.Message],
        logger: Logger,
    ) -> tuple[str | None, enums.DialogStatus | None]:
        """Получает ответ от AI и определяет статус диалога"""

        history = self._build_history(dialog_messages)
        system_prompt = await self._build_system_prompt(project_prompt, status)
        messages = [{"role": "system", "content": system_prompt}] + history

        for msg in reversed(messages):
            if msg["role"] == "user":
                msg["content"] += f"\n{get_status_addon(status)}"
                break

        try:
            completion = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,  # type: ignore
            )
            response = completion.choices[0].message.content

            if not response:
                return None, None

            text, new_status = self._parse_response(response, logger)
            return text, new_status

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

    async def _build_system_prompt(
        self, project_prompt: dict, status: enums.DialogStatus
    ) -> str:
        """Формирует системный промпт с инструкциями по статусам"""
        return await build_prompt(project_prompt, status)

    def _parse_response(
        self, response: str, logger: Logger
    ) -> tuple[str, enums.DialogStatus | None]:
        """Парсит ответ AI и извлекает статус"""

        status = None
        text = response

        status = get_ooc_status(response)
        if status:
            text = strip_ooc_status(text)
            if status:
                logger.info(f"AI установил статус: {status.value}")
            else:
                logger.warning(f"Неизвестный статус от AI: {status.value}")
        else:
            logger.warning(f"AI не вернул статус. Ответ: {response[:100]}...")

        return text, status
