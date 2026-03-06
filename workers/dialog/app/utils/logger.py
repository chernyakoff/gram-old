import json
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


class Logger:
    def __init__(self, ctx: Context):
        self.ctx = ctx

    def _dump(self, entry: LogEntry) -> str:
        return json.dumps(asdict(entry), ensure_ascii=False)

    def _log(self, entry: LogEntry):
        data = self._dump(entry)
        # if entry.status in [Status.ERROR, Status.WARNING]:
        self.ctx.log(data)

    def error(self, msg: str | Exception, payload: dict | None = None):
        if isinstance(msg, Exception):
            msg = f"{type(msg).__name__}: {msg}"
        self._log(LogEntry(Status.ERROR, msg, payload))

    def success(self, msg: str, payload: dict | None = None):
        self._log(LogEntry(Status.SUCCESS, msg, payload))

    def info(self, msg: str, payload: dict | None = None):
        self._log(LogEntry(Status.INFO, msg, payload))

    def warning(self, msg: str, payload: dict | None = None):
        self._log(LogEntry(Status.WARNING, msg, payload))

    def from_proxy_pool(self, pool: ProxyPool):
        for log in pool.get_logs(clear=True):
            if log.status == Status.INFO:
                self.info(log.message, log.payload)
            elif log.status == Status.WARNING:
                self.warning(log.message, log.payload)
            elif log.status == Status.ERROR:
                self.error(log.message, log.payload)
            elif log.status == Status.SUCCESS:
                self.success(log.message, log.payload)
