import asyncio
import json
import logging
import os
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from hatchet_sdk import TriggerWorkflowOptions
from hatchet_sdk.clients.listeners.run_event_listener import StepRunEventType

from app.hatchet.client import hatchet
from app.redis import get_redis

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sse", tags=["sse"])

# Максимальный размер очереди (чтобы не разрасталась бесконечно)
QUEUE_SIZE = 100
PING_INTERVAL = 15 # каждые 15 секунд шлем ping
STREAM_READY_PREFIX = os.getenv("STREAM_READY_PREFIX", "stream-ready")
STREAM_READY_TTL_SECONDS = int(os.getenv("STREAM_READY_TTL_SECONDS", "120"))

subscribers: list[asyncio.Queue] = []
# pipa dripa supa pupa watchfiles testing suka


def _parse_stream_payload(payload: Any) -> dict:
    if payload is None:
        return {}
    if isinstance(payload, dict):
        return payload
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="replace")
    if isinstance(payload, str):
        try:
            loaded = json.loads(payload)
            if isinstance(loaded, dict):
                return loaded
            return {"message": payload}
        except json.JSONDecodeError:
            return {"message": payload}
    return {"message": str(payload)}


def _ready_key(stream_key: str) -> str:
    return f"{STREAM_READY_PREFIX}:{stream_key}"


async def _mark_stream_ready(stream_key: str):
    redis = get_redis()
    await redis.set(_ready_key(stream_key), "1", ex=STREAM_READY_TTL_SECONDS)


def build_stream_options() -> tuple[str, TriggerWorkflowOptions]:
    stream_key = str(uuid4())
    options = TriggerWorkflowOptions(additional_metadata={"stream_key": stream_key})
    return stream_key, options


async def watch_job(stream_key: str):
    ready_sent = False
    try:
        listener = hatchet.runs.workflow_run_event_listener.stream_by_additional_metadata(
            "stream_key", stream_key
        )
        async for chunk in listener:
            if not ready_sent:
                await _mark_stream_ready(stream_key)
                ready_sent = True
            if chunk.type == StepRunEventType.STEP_RUN_EVENT_TYPE_STREAM:
                event = {"jobId": stream_key, "log": _parse_stream_payload(chunk.payload)}
                await broadcast_event(event)
            elif chunk.type == StepRunEventType.STEP_RUN_EVENT_TYPE_COMPLETED:
                await broadcast_event({"jobId": stream_key, "status": "finished"})
                break
            elif chunk.type in (
                StepRunEventType.STEP_RUN_EVENT_TYPE_FAILED,
                StepRunEventType.STEP_RUN_EVENT_TYPE_CANCELLED,
                StepRunEventType.STEP_RUN_EVENT_TYPE_TIMED_OUT,
            ):
                await broadcast_event({"jobId": stream_key, "status": "failed"})
                break
    except Exception as e:
        logger.exception("watch_job failed for stream_key=%s", stream_key)
        await broadcast_event({"jobId": stream_key, "status": "failed", "error": str(e)})
    finally:
        if not ready_sent:
            try:
                await _mark_stream_ready(stream_key)
            except Exception:
                logger.exception("failed to mark stream ready for stream_key=%s", stream_key)


async def broadcast_event(event: dict):
    """
    Рассылаем событие всем подключённым клиентам.
    Если очередь переполнена — старое событие выбрасывается.
    """
    for queue in subscribers:
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            # если очередь переполнена — вытесняем старое событие
            _ = queue.get_nowait()
            await queue.put(event)


@router.get("/")
async def jobs_stream(request: Request):
    """
    SSE эндпоинт для фронта. Все события транслируются через него.
    """
    queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
    subscribers.append(queue)

    async def event_generator():
        try:
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    logger.info("Client disconnected")
                    break
                try:
                    # ждём событие или таймаут для ping
                    data = await asyncio.wait_for(queue.get(), timeout=PING_INTERVAL)
                    yield f"data: {json.dumps(data)}\n\n"
                except asyncio.TimeoutError:
                    # отправляем ping, если новых событий не было
                    yield "data: {}\n\n"

        except asyncio.CancelledError:
            # сюда придёт при reload/shutdown
            print("SSE connection cancelled")
            raise

        finally:
            if queue in subscribers:
                subscribers.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
