import asyncio
import json
import os
import time
from dataclasses import asdict, dataclass
from enum import StrEnum, auto

from hatchet_sdk import Context

from app.common.utils.proxy_pool import ProxyPool
from app.redis import get_redis


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
        self._stream_ready = False
        self._warmup_seconds = float(os.getenv("HATCHET_STREAM_WARMUP_SECONDS", "1"))
        self._ready_prefix = os.getenv("STREAM_READY_PREFIX", "stream-ready")
        self._ready_timeout_seconds = float(
            os.getenv("STREAM_READY_TIMEOUT_SECONDS", "10")
        )
        self._ready_poll_seconds = float(os.getenv("STREAM_READY_POLL_SECONDS", "0.2"))

    def _stream_key(self) -> str:
        meta = getattr(self.ctx.action, "additional_metadata", {}) or {}
        if isinstance(meta, dict):
            value = meta.get("stream_key")
            if isinstance(value, str) and value:
                return value
        return self.ctx.workflow_run_id

    def _ready_key(self) -> str:
        return f"{self._ready_prefix}:{self._stream_key()}"

    async def _wait_until_stream_ready(self):
        if self._stream_ready:
            return
        try:
            redis = get_redis()
            deadline = time.monotonic() + self._ready_timeout_seconds
            ready_key = self._ready_key()
            while time.monotonic() < deadline:
                if await redis.exists(ready_key):
                    self._stream_ready = True
                    break
                await asyncio.sleep(self._ready_poll_seconds)
        except Exception as e:
            self.ctx.log(f"Stream readiness check failed: {type(e).__name__}: {e}")

        if not self._stream_ready:
            self.ctx.log("Stream readiness timeout, continue publishing")

        if self._warmup_seconds > 0:
            await asyncio.sleep(self._warmup_seconds)

    def _dump(self, entry: LogEntry) -> str:
        return json.dumps(asdict(entry), ensure_ascii=False)

    async def _log(self, entry: LogEntry):
        data = self._dump(entry)
        self.ctx.log(data)
        if not self._stream_ready:
            await self._wait_until_stream_ready()
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
