import json
from dataclasses import asdict, dataclass
from enum import StrEnum, auto

from hatchet_sdk import Context


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
        return json.dumps(asdict(entry), ensure_ascii=False)

    async def _log(self, entry: LogEntry):
        data = self._dump(entry)
        # if entry.status in [Status.ERROR, Status.WARNING]:
        self.ctx.log(data)
        await self.ctx.aio_put_stream(data)

    async def error(self, msg: str | Exception, payload: dict | None = None):
        if isinstance(msg, Exception):
            msg = f"{type(msg).__name__}: {msg}"
        await self._log(LogEntry(Status.ERROR, msg, payload))

    async def success(self, msg: str, payload: dict | None = None):
        await self._log(LogEntry(Status.SUCCESS, msg, payload))

    async def info(self, msg: str, payload: dict | None = None):
        await self._log(LogEntry(Status.INFO, msg, payload))

    async def warning(self, msg: str, payload: dict | None = None):
        await self._log(LogEntry(Status.WARNING, msg, payload))
