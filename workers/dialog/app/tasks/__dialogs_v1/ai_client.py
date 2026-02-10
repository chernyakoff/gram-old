import asyncio
import io
import subprocess

from openai import AsyncOpenAI

from app.common.models import enums, orm
from app.common.utils import openrouter
from app.common.utils.functions import normalize_dashes
from app.common.utils.notify import BotNotify
from app.common.utils.prompt import (
    build_prompt_v2,
    get_calendar_addon,
    get_status_addon,
)
from app.common.utils.schedule import TOOLS, ToolContext
from app.utils.logger import Logger

from .status_resolver import build_history


class AIClient:
    """Unified AI client: prompt generation + speech-to-text."""

    def __init__(self, user: orm.User, logger: Logger):
        self.user = user
        self.logger = logger

    async def generate_response(
        self,
        project_prompt: dict,
        status: enums.DialogStatus,
        dialog: orm.Dialog,
        messages: list[orm.Message],
        name_addon: str,
        project: orm.Project,
    ) -> str | None:
        history = build_history(messages)

        system_prompt = build_prompt_v2(project_prompt, status)

        chunks = []
        if await orm.ProjectDocument.filter(project_id=project.id).count() > 0:
            for msg in reversed(history):
                if msg["role"] == "user":
                    chunks = await openrouter.retrieve_chunks(self.user, msg["content"])
                    break

        if chunks:
            system_prompt = (
                f"{system_prompt}\n\n"
                "Используй следующий контекст для ответа на вопрос:\n\n"
                f"{'\n'.join(chunks)}"
            )

        prompt_messages = [{"role": "system", "content": system_prompt}] + history

        for msg in reversed(prompt_messages):
            if msg["role"] == "user":
                msg["content"] += f"\n{name_addon}"
                status_addon = await get_status_addon()
                msg["content"] += f"\n{status_addon}"
                if project.use_calendar:
                    calendar_addon = await get_calendar_addon(self.user)
                    msg["content"] += f"\n\n{calendar_addon}"
                if status == enums.DialogStatus.CLOSING:
                    msg["content"] += (
                        "\nВАЖНО, если ты попрощался, а тебе продолжают писать, "
                        "то отвечай одним словом COMPLETE и больше ничего не пиши"
                    )
                break

        try:
            if project.use_calendar:
                ctx = ToolContext(self.user, dialog)
                tool_handlers = {
                    "get_slots": ctx.get_slots,
                    "book_slot": ctx.book_slot,
                    "cancel_meeting": ctx.cancel_meeting,
                }
                response = await openrouter.create_response_with_tools(
                    self.user, prompt_messages, TOOLS, tool_handlers
                )
            else:
                response = await openrouter.create_response(self.user, prompt_messages)

            if not response:
                return None

            if response.strip() == "COMPLETE":
                return "COMPLETE"

            return normalize_dashes(response)

        except Exception as e:
            await BotNotify.error(self.user.id, str(e))
            self.logger.error(f"Ошибка AI запроса: {e}")
            return None

    async def transcribe(self, oga_bytes: bytes) -> str:
        """
        Конвертирует OGA/OGG → MP3 через ffmpeg и отправляет в OpenAI для транскрипции.
        """

        def convert_oga_to_mp3(input_bytes: bytes) -> bytes:
            process = subprocess.Popen(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    "pipe:0",
                    "-f",
                    "mp3",
                    "pipe:1",
                ],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            out, err = process.communicate(input=input_bytes)
            if process.returncode != 0:
                raise RuntimeError(
                    f"FFmpeg conversion failed: {err.decode('utf-8', errors='ignore')}"
                )
            return out

        mp3_bytes: bytes = await asyncio.to_thread(convert_oga_to_mp3, oga_bytes)
        mp3_io = io.BytesIO(mp3_bytes)

        client = AsyncOpenAI(
            api_key="sk-zU2bFj5xpbIArlgNMlqpG36qFDw9flXE",
            base_url="https://api.proxyapi.ru/openai/v1",
            timeout=600,
        )

        transcription = await client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=("voice.mp3", mp3_io),
        )

        return transcription.text
