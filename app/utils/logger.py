from __future__ import annotations

import json
import logging
import sys
import traceback
from dataclasses import asdict, dataclass
from enum import StrEnum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hatchet_sdk import Context
    from utils.proxy_pool import ProxyPool


class InterceptHandler(logging.Handler):
    def emit(self, record):
        # Просто пробрасываем рекорд в корневой логгер
        logging.getLogger(record.name).handle(record)


def setup_logger(filename: str = "app.log"):
    # Формат логов
    formatter = logging.Formatter(
        fmt="[{asctime}] {levelname} | {name} | {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )

    # Хендлер для stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Хендлер для файла (если нужно)
    # file_handler = logging.FileHandler(f"logs/{filename}")
    # file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Уровень логирования
    root_logger.handlers.clear()  # Убираем старые хендлеры
    root_logger.addHandler(console_handler)
    # root_logger.addHandler(file_handler)

    # Настройки сторонних библиотек
    logging.getLogger("tortoise.db_client").setLevel(logging.ERROR)
    logging.getLogger("tortoise").setLevel(logging.ERROR)
    logging.getLogger("telethon").setLevel(logging.ERROR)
    logging.getLogger("httpx").setLevel(logging.WARNING)


logger = logging.getLogger("bot")


class Status(StrEnum):
    INFO = auto()
    ERROR = auto()
    SUCCESS = auto()
    WARNING = auto()


@dataclass
class LogEntry:
    status: Status
    message: str
    payload: dict | None = None


class Logger:
    """
    Synchronous logger: writes to orchestration logs (ctx.log).
    """

    def __init__(self, ctx: Context):
        self.ctx = ctx

    def _dump(self, entry: LogEntry) -> str:
        data = asdict(entry)
        try:
            return json.dumps(data, ensure_ascii=False)
        except TypeError:
            # Best-effort serialization: payload may contain non-JSON types (datetime, enums, etc.).
            return json.dumps(data, ensure_ascii=False, default=str)

    def _log(self, entry: LogEntry) -> None:
        data = self._dump(entry)
        # Logging must never crash the task.
        try:
            self.ctx.log(data)
        except Exception:
            print(data, file=sys.stderr, flush=True)

    def error(self, msg: str | Exception, payload: dict | None = None) -> None:
        if isinstance(msg, Exception):
            msg = f"{type(msg).__name__}: {msg}"
        self._log(LogEntry(Status.ERROR, msg, payload))

    def success(self, msg: str, payload: dict | None = None) -> None:
        self._log(LogEntry(Status.SUCCESS, msg, payload))

    def info(self, msg: str, payload: dict | None = None) -> None:
        self._log(LogEntry(Status.INFO, msg, payload))

    def warning(self, msg: str, payload: dict | None = None) -> None:
        self._log(LogEntry(Status.WARNING, msg, payload))

    def from_proxy_pool(self, pool: ProxyPool) -> None:
        for log in pool.get_logs(clear=True):
            if log.status == Status.INFO:
                self.info(log.message, log.payload)
            elif log.status == Status.WARNING:
                self.warning(log.message, log.payload)
            elif log.status == Status.ERROR:
                self.error(log.message, log.payload)
            elif log.status == Status.SUCCESS:
                self.success(log.message, log.payload)


class StreamLogger:
    """
    Async logger: writes to orchestration logs (ctx.log) and streams user-facing progress (ctx.aio_put_stream).
    """

    def __init__(self, ctx: Context):
        self.ctx = ctx

    def _dump(self, entry: LogEntry) -> str:
        # Best-effort serialization: payload may contain non-JSON types (datetime, enums, etc.).
        return json.dumps(asdict(entry), ensure_ascii=False, default=str)

    def _ctx_log(self, text: str) -> None:
        # ctx.log is orchestration log, must never crash the task.
        try:
            self.ctx.log(text)
        except Exception:
            print(text, file=sys.stderr, flush=True)

    async def _log(self, entry: LogEntry) -> None:
        data = self._dump(entry)
        # This stream is user-facing (frontend progress). Keep it short, readable, no stack traces.
        # Streaming/logging must never crash the task.
        self._ctx_log(data)
        try:
            await self.ctx.aio_put_stream(data)
        except Exception:
            # Stream can fail if the run/stream is gone; orchestration log still has the entry.
            pass

    async def error(self, msg: str | Exception, payload: dict | None = None) -> None:
        if isinstance(msg, Exception):
            msg = f"{type(msg).__name__}: {msg}"
        await self._log(LogEntry(Status.ERROR, msg, payload))

    async def tech(
        self, msg: str, payload: dict | None = None, exc: BaseException | None = None
    ) -> None:
        """
        Technical logging: only to orchestration logs (ctx.log), never to the user stream.
        Use for stack traces and low-level diagnostics.
        """

        data: dict = {"kind": "tech", "message": msg}
        if payload is not None:
            data["payload"] = payload
        if exc is not None:
            tb = "".join(
                traceback.format_exception(type(exc), exc, exc.__traceback__)
            ).strip()
            data["exception"] = type(exc).__name__
            data["exception_message"] = str(exc)
            data["traceback"] = tb

        self._ctx_log(json.dumps(data, ensure_ascii=False, default=str))

    async def exception(
        self,
        msg: str,
        exc: BaseException,
        payload: dict | None = None,
        *,
        max_traceback_chars: int = 4000,
    ) -> None:
        # Backward-compatible helper: user gets a short error, technical details go to ctx.log.
        tb = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        ).strip()
        if len(tb) > max_traceback_chars:
            tb = tb[-max_traceback_chars:]

        await self.error(msg, payload=payload)
        await self.tech(
            msg,
            payload=dict(payload or {}),
            exc=exc,
        )

    async def success(self, msg: str, payload: dict | None = None) -> None:
        await self._log(LogEntry(Status.SUCCESS, msg, payload))

    async def info(self, msg: str, payload: dict | None = None) -> None:
        await self._log(LogEntry(Status.INFO, msg, payload))

    async def warning(self, msg: str, payload: dict | None = None) -> None:
        await self._log(LogEntry(Status.WARNING, msg, payload))

    async def from_proxy_pool(self, pool: ProxyPool) -> None:
        for log in pool.get_logs(clear=True):
            if log.status == Status.INFO:
                await self.info(log.message, log.payload)
            elif log.status == Status.WARNING:
                # Proxy pool warnings are often transient/retry noise.
                # Keep them out of user-facing stream, but preserve in technical logs.
                await self.tech(log.message, payload=log.payload)
            elif log.status == Status.ERROR:
                await self.error(log.message, log.payload)
            elif log.status == Status.SUCCESS:
                await self.success(log.message, log.payload)


__all__ = [
    "InterceptHandler",
    "LogEntry",
    "Logger",
    "Status",
    "StreamLogger",
    "logger",
    "setup_logger",
]
