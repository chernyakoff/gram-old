import asyncio
import io
import subprocess
from datetime import date

from openai import AsyncOpenAI

from app.common.models import enums, orm
from app.common.utils import openrouter
from app.common.utils.functions import normalize_dashes
from app.common.utils.notify import BotNotify
from app.common.utils.prompt import (
    DEFAULT_SKIP_OPTIONS,
    ProjectSkipOptions,
    analyze_dialog_status,
    build_prompt_v2,
    get_active_status,
    get_calendar_addon,
    get_status_addon,
)
from app.common.utils.schedule import TOOLS, ToolContext
from app.tasks.dialog.telegram_service import TelegramService
from app.utils.logger import Logger


class AIService:
    """Сервис для работы с AI"""

    def __init__(self, user: orm.User):
        self.user = user

    async def get_response_with_status(
        self,
        project_prompt: dict,
        dialog: orm.Dialog,
        dialog_messages: list[orm.Message],
        name_addon: str,
        project: orm.Project,
        telegram_service: TelegramService,
        recipient: orm.Recipient,
        logger: Logger,
    ) -> tuple[str | None, enums.DialogStatus | None]:
        """Получает ответ от AI и определяет статус диалога"""

        status = dialog.status

        history = self._build_history(dialog_messages)

        skip_options = (
            ProjectSkipOptions(**project.skip_options)
            if project.skip_options
            else DEFAULT_SKIP_OPTIONS
        )
        # TODO сделать событием смену статуса

        files = []
        new_status = await analyze_dialog_status(self.user, history.copy(), status)
        if new_status:
            logger.info(f"AI установил статус: {new_status.value}")
            new_status = get_active_status(new_status, skip_options)
            if new_status != status:
                files = await orm.ProjectFile.filter(
                    project_id=project.id, status=new_status
                ).all()
                if files:
                    for f in files:
                        msg = await telegram_service.send_file(recipient, f)
                        if msg:
                            await orm.Message.create(
                                dialog=dialog,
                                tg_message_id=msg.id,  # type: ignore
                                sender=enums.MessageSender.ACCOUNT,
                                text=f"{f.filename}\n{f.title}",
                                ui_only=True,
                            )

            status = new_status
        else:
            logger.warning("AI не вернул статус")

        if status in [
            enums.DialogStatus.COMPLETE,
            enums.DialogStatus.NEGATIVE,
            enums.DialogStatus.OPERATOR,
        ]:
            return "", status

        system_prompt = build_prompt_v2(project_prompt, status)

        chunks = []
        if await orm.ProjectDocument.filter(project_id=project.id).count() > 0:
            for msg in reversed(history):
                if msg["role"] == "user":
                    chunks = await openrouter.retrieve_chunks(self.user, msg["content"])

        if chunks:
            system_prompt = f"""
                {system_prompt}

                Используй следующий контекст для ответа на вопрос:

                {"\n".join(chunks)}
            """

        messages = [{"role": "system", "content": system_prompt}] + history

        for msg in reversed(messages):
            if msg["role"] == "user":
                msg["content"] += f"\n{name_addon}"
                status_addon = await get_status_addon()
                msg["content"] += f"\n{status_addon}"
                if project.use_calendar:
                    calendar_addon = await get_calendar_addon(self.user)
                    msg["content"] += f"\n\n{calendar_addon}"
                if status == enums.DialogStatus.CLOSING:
                    msg["content"] += (
                        "\nВАЖНО, если ты попрощался, а тебе продолжают писать, то отвечай одним словом COMPLETE и больше ничего не пиши"
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
                    self.user, messages, TOOLS, tool_handlers
                )
            else:
                response = await openrouter.create_response(self.user, messages)

            if not response:
                return None, None

            if response.strip() == "COMPLETE":
                return "COMPLETE", enums.DialogStatus.COMPLETE

            return normalize_dashes(response), status

        except Exception as e:
            await BotNotify.error(self.user.id, str(e))
            logger.error(f"Ошибка AI запроса: {e}")
            return None, None

    def _build_history(self, messages: list[orm.Message]) -> list[dict]:
        """Формирует историю сообщений для AI"""
        history = []
        for msg in messages:
            if msg.sender == enums.MessageSender.SYSTEM:
                # Добавляем маркер что это важное указание
                role = "assistant"
                content = f"[ВАЖНОЕ УТОЧНЕНИЕ] {msg.text}"
            elif msg.sender == enums.MessageSender.ACCOUNT:
                role = "assistant"
                content = msg.text
            else:
                role = "user"
                content = msg.text

            history.append({"role": role, "content": content})
        return history

    async def transcribe(self, oga_bytes: bytes) -> str:
        """
        Конвертирует OGA/OGG → MP3 через ffmpeg и отправляет в OpenAI для транскрипции.
        Работает с asyncio и последним OpenAI SDK.
        """

        # конвертация через ffmpeg в отдельном потоке, чтобы не блокировать event loop
        def convert_oga_to_mp3(input_bytes: bytes) -> bytes:
            process = subprocess.Popen(
                [
                    "ffmpeg",
                    "-y",  # overwrite
                    "-i",
                    "pipe:0",  # input из stdin
                    "-f",
                    "mp3",
                    "pipe:1",  # output в stdout
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

        # вызываем конвертацию в отдельном потоке
        mp3_bytes: bytes = await asyncio.to_thread(convert_oga_to_mp3, oga_bytes)

        # создаём BytesIO, чтобы OpenAI SDK точно понял формат
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
