import json
import sys
import traceback
from dataclasses import asdict, dataclass
from enum import StrEnum, auto

from hatchet_sdk import Context

from app.common.utils.proxy_pool import ProxyPool


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


class StreamLogger:
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

    async def _log(self, entry: LogEntry):
        data = self._dump(entry)
        # This stream is user-facing (frontend progress). Keep it short, readable, no stack traces.
        # Streaming/logging must never crash the task.
        self._ctx_log(data)
        try:
            await self.ctx.aio_put_stream(data)
        except Exception:
            # Stream can fail if the run/stream is gone; orchestration log still has the entry.
            pass

    async def error(self, msg: str | Exception, payload: dict | None = None):
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
    ):
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

    async def success(self, msg: str, payload: dict | None = None):
        await self._log(LogEntry(Status.SUCCESS, msg, payload))

    async def info(self, msg: str, payload: dict | None = None):
        await self._log(LogEntry(Status.INFO, msg, payload))

    async def warning(self, msg: str, payload: dict | None = None):
        await self._log(LogEntry(Status.WARNING, msg, payload))

    async def from_proxy_pool(self, pool: ProxyPool):
        for log in pool.get_logs(clear=True):
            if log.status == Status.INFO:
                await self.info(log.message, log.payload)
            elif log.status == Status.WARNING:
                await self.warning(log.message, log.payload)
            elif log.status == Status.ERROR:
                await self.error(log.message, log.payload)
            elif log.status == Status.SUCCESS:
                await self.success(log.message, log.payload)
