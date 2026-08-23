"""
Real-time price feed via Binance WebSocket miniTicker combined stream.
Maintains an in-memory price cache for all watchlist coins.
No API key required — public stream.
"""
from __future__ import annotations

import asyncio
import json
from datetime import datetime

import websockets
from loguru import logger

from spot.watchlist import get_symbols

_WS_BASE         = "wss://stream.binance.com:9443/stream"
_RECONNECT_DELAY = 5    # seconds before reconnect attempt
_STALE_THRESHOLD = 90   # seconds without any price tick → force reconnect

# {symbol: {price, open, change_pct, high, low, volume_usdt, updated_at}}
_prices:    dict[str, dict] = {}
_connected: bool = False
_stream_task: asyncio.Task | None = None
_last_tick: datetime | None = None   # time of the most recent price update

# Track last disconnect time so fast_sl_cycle knows how stale prices are
_last_disconnect: datetime | None = None


def _log_stream_event(event: str, description: str) -> None:
    """Persist connect/disconnect events to SystemEvent for audit trail."""
    global _last_disconnect
    try:
        from data.database import get_session
        from data.models import SystemEvent
        with get_session() as s:
            s.add(SystemEvent(event_type=f"stream_{event}", description=description))
        if event == "disconnected":
            _last_disconnect = datetime.utcnow()
    except Exception:
        pass


def disconnected_since() -> datetime | None:
    """Returns the timestamp of the last disconnect, or None if currently connected.
    If stream never started (_stream_task is None), returns epoch so callers
    treat it as a long-standing disconnect rather than a connected state."""
    if _connected:
        return None
    if _last_disconnect is None and _stream_task is None:
        return datetime(2000, 1, 1)  # sentinel: never started = effectively disconnected since forever
    return _last_disconnect


def get_prices() -> dict:
    return dict(_prices)


def is_connected() -> bool:
    return _connected


def last_tick_age_seconds() -> float | None:
    """Seconds since the most recent price tick, or None if never received."""
    if _last_tick is None:
        return None
    return (datetime.utcnow() - _last_tick).total_seconds()


async def _stale_watchdog() -> None:
    """Force-reconnect the stream if no price tick arrives for _STALE_THRESHOLD seconds.
    Handles the Binance 'zombie connection' case: TCP alive, but no data flowing."""
    while True:
        await asyncio.sleep(30)
        if not _connected or _last_tick is None:
            continue
        age = (datetime.utcnow() - _last_tick).total_seconds()
        if age > _STALE_THRESHOLD:
            logger.warning(
                f"Price stream stale — no tick for {age:.0f}s (threshold {_STALE_THRESHOLD}s) — forcing reconnect"
            )
            _log_stream_event("disconnected", f"Stale watchdog: no tick for {age:.0f}s — forced reconnect")
            refresh_subscription()


async def _run_stream() -> None:
    global _connected, _last_tick
    while True:
        # Re-resolve symbols on every (re)connect so watchlist changes are picked up
        symbols = get_symbols()
        streams = "/".join(f"{s.lower()}usdt@miniTicker" for s in symbols)
        url     = f"{_WS_BASE}?streams={streams}"
        try:
            # ping_interval=20: send a ping every 20s so dead connections are detected
            # quickly rather than waiting for Binance to timeout our silent socket.
            async with websockets.connect(url, ping_interval=20, ping_timeout=10) as ws:
                _connected = True
                _last_tick = datetime.utcnow()
                logger.info(f"Price stream connected — {len(symbols)} coins")
                _log_stream_event("connected", f"Price stream connected — {len(symbols)} coins")
                async for raw in ws:
                    msg = json.loads(raw)
                    d   = msg.get("data", {})
                    sym = d.get("s", "").replace("USDT", "")
                    if not sym:
                        continue
                    c = float(d.get("c", 0))
                    o = float(d.get("o", 0))
                    now = datetime.utcnow()
                    _prices[sym] = {
                        "price":       c,
                        "open":        o,
                        "change_pct":  round((c - o) / o * 100, 2) if o else 0,
                        "high":        float(d.get("h", 0)),
                        "low":         float(d.get("l", 0)),
                        "volume_usdt": round(float(d.get("q", 0)) / 1_000_000, 1),
                        "updated_at":  now.isoformat(),
                    }
                    _last_tick = now
        except asyncio.CancelledError:
            _connected = False
            raise
        except Exception as e:
            _connected = False
            reason = str(e)
            logger.warning(f"Price stream disconnected: {reason} — reconnecting in {_RECONNECT_DELAY}s")
            _log_stream_event("disconnected", f"Price stream disconnected: {reason[:200]}")
            await asyncio.sleep(_RECONNECT_DELAY)


def start_price_stream() -> asyncio.Task:
    """Start the WebSocket price feed + stale watchdog as background asyncio tasks."""
    global _stream_task
    _stream_task = asyncio.create_task(_run_stream())
    asyncio.create_task(_stale_watchdog())
    return _stream_task


def refresh_subscription() -> None:
    """Cancel the current stream task so it reconnects with the latest watchlist.
    Called after refresh_watchlist() to pick up added/removed coins immediately."""
    global _stream_task, _connected
    if _stream_task and not _stream_task.done():
        _connected = False
        _stream_task.cancel()
        logger.info("Price stream subscription refresh requested — will reconnect with updated symbols")
