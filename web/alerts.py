"""
Alert bus — collects alerts from background jobs and fans them out
to all connected SSE clients.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import AsyncGenerator

from loguru import logger


class AlertLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    message: str
    level: AlertLevel = AlertLevel.INFO
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = "system"


class AlertBus:
    """Fan-out queue: one publisher, many SSE subscriber queues."""

    def __init__(self):
        self._subscribers: list[asyncio.Queue[Alert]] = []

    def subscribe(self) -> asyncio.Queue[Alert]:
        q: asyncio.Queue[Alert] = asyncio.Queue(maxsize=50)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[Alert]) -> None:
        self._subscribers.remove(q)

    async def publish(self, alert: Alert) -> None:
        for q in list(self._subscribers):
            try:
                q.put_nowait(alert)
            except asyncio.QueueFull:
                pass  # slow client — drop rather than block

    async def publish_text(
        self,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        source: str = "system",
    ) -> None:
        await self.publish(Alert(message=message, level=level, source=source))
        # Persist to DB so alert history survives page reloads and disconnections
        try:
            from data.database import get_session
            from data.models import SpotAlertLog
            with get_session() as s:
                s.add(SpotAlertLog(
                    alert_type=source,
                    message=message,
                ))
        except Exception as e:
            logger.warning(f"Alert DB persist failed (alert still delivered): {e}")


_bus: AlertBus | None = None


def get_bus() -> AlertBus:
    global _bus
    if _bus is None:
        _bus = AlertBus()
    return _bus


def reset_bus() -> None:
    global _bus
    _bus = None
