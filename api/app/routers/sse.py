import asyncio
import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.hatchet.client import hatchet

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sse", tags=["sse"])

# Максимальный размер очереди (чтобы не разрасталась бесконечно)
QUEUE_SIZE = 100
PING_INTERVAL = 15 # каждые 15 секунд шлем ping

subscribers: list[asyncio.Queue] = []
# pipa dripa supa pupa watchfiles testing suka


async def watch_job(run_id: str):
    try:
        async for chunk in hatchet.runs.subscribe_to_stream(run_id):
            event = {"jobId": run_id, "log": json.loads(chunk)}
            await broadcast_event(event)

        # если стрим закончился сам по себе — задача завершена
        await broadcast_event({"jobId": run_id, "status": "finished"})

    except Exception as e:
        await broadcast_event({"jobId": run_id, "status": "failed", "error": str(e)})


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
