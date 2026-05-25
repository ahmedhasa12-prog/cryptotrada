"""
Server-Sent Events endpoint.
The Vue frontend opens EventSource('/api/stream') and receives
live alerts without polling.
"""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from web.alerts import get_bus, Alert

router = APIRouter(prefix="/api")


def _format_sse(alert: Alert) -> str:
    data = json.dumps({
        "message": alert.message,
        "level": alert.level.value,
        "timestamp": alert.timestamp,
        "source": alert.source,
    })
    return f"data: {data}\n\n"


async def _event_generator():
    bus = get_bus()
    queue = bus.subscribe()
    try:
        # Send a heartbeat every 30s so the connection stays alive through proxies
        while True:
            try:
                alert = await asyncio.wait_for(queue.get(), timeout=30.0)
                yield _format_sse(alert)
            except asyncio.TimeoutError:
                yield ": heartbeat\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        bus.unsubscribe(queue)


@router.get("/stream")
async def stream():
    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx buffering on VPS
        },
    )
