"""
Binance public klines fetcher — no API key required.
Endpoint: GET https://api.binance.com/api/v3/klines
Stores OHLCV candles in the ohlcv_candles table.
"""
from __future__ import annotations

import asyncio
from datetime import datetime

import httpx
import json
from loguru import logger
from pathlib import Path
from sqlalchemy import func

from data.database import get_session
from data.models import OhlcvCandle
from spot.watchlist import get_symbols

_KLINES_URL = "https://api.binance.com/api/v3/klines"
_TIMEOUT    = 15.0
_REQ_DELAY  = 0.12   # seconds between requests — stays well under rate limits

# Rate-limit exponential backoff settings
_MAX_RETRIES    = 5
_BACKOFF_BASE   = 1.5    # seconds; doubled each retry: 1.5, 2.25, 3.375, …
_RETRY_429_MAX  = 60     # cap backoff at 60s for 429s

# How many candles to fetch per interval on a regular (scheduler) refresh
INTERVAL_LIMITS: dict[str, int] = {
    "1w":  210,   # ~4 years weekly  — weekly job
    "1d":  365,   # rolling 1-year   — daily job (3-year history loaded at startup)
    "4h":  300,   # ~50 days
    "1h":  200,   # ~8 days
    "15m": 200,   # ~2 days
}


# ── Low-level fetch ───────────────────────────────────────────────────────────

async def _fetch_raw(symbol: str, interval: str, limit: int,
                     start_ms: int | None = None) -> list:
    """Fetch klines from Binance with exponential backoff on 429 rate limits."""
    url = (
        f"{_KLINES_URL}?symbol={symbol}USDT"
        f"&interval={interval}&limit={limit}"
    )
    if start_ms is not None:
        url += f"&startTime={start_ms}"

    for attempt in range(1, _MAX_RETRIES + 1):
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url)
        if r.status_code == 429:
            # Rate limited — respect Retry-After if provided, else exponential backoff
            retry_after = r.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                wait = max(int(retry_after), 1)
            else:
                wait = min(_BACKOFF_BASE ** attempt, _RETRY_429_MAX)
            logger.warning(
                f"429 rate limited for {symbol} {interval} "
                f"(attempt {attempt}/{_MAX_RETRIES}), waiting {wait}s"
            )
            await asyncio.sleep(wait)
            continue
        r.raise_for_status()
        return r.json()

    raise RuntimeError(
        f"Max retries ({_MAX_RETRIES}) exceeded for {symbol} {interval}"
    )


# ── DB helpers ────────────────────────────────────────────────────────────────

def _existing_timestamps(symbol: str, interval: str) -> set[datetime]:
    with get_session() as s:
        rows = (
            s.query(OhlcvCandle.timestamp)
             .filter(OhlcvCandle.symbol == symbol,
                     OhlcvCandle.interval == interval)
             .all()
        )
        return {r.timestamp for r in rows}


def _save_candles(symbol: str, interval: str, klines: list,
                  existing: set[datetime]) -> int:
    if not klines:
        return 0
    rows_to_add = []
    # Skip the last candle — it's the current (still open) candle
    for k in klines[:-1]:
        ts = datetime.utcfromtimestamp(k[0] / 1000)
        if ts in existing:
            continue
        rows_to_add.append(OhlcvCandle(
            symbol=symbol, interval=interval, timestamp=ts,
            open=float(k[1]), high=float(k[2]),
            low=float(k[3]),  close=float(k[4]),
            volume=float(k[5]), taker_buy_base=float(k[9]),
        ))
    if rows_to_add:
        with get_session() as s:
            s.add_all(rows_to_add)
    return len(rows_to_add)


def load_dataframe(symbol: str, interval: str, limit: int = 300):
    """Load candles from DB as a pandas DataFrame (chronological order)."""
    import pandas as pd
    with get_session() as s:
        rows = (
            s.query(OhlcvCandle)
             .filter(OhlcvCandle.symbol == symbol,
                     OhlcvCandle.interval == interval)
             .order_by(OhlcvCandle.timestamp.desc())
             .limit(limit)
             .all()
        )
        if not rows:
            return pd.DataFrame()
        # Build DataFrame inside session so attributes are accessible before expiry
        data = [{
            "timestamp":      r.timestamp,
            "open":           r.open,
            "high":           r.high,
            "low":            r.low,
            "close":          r.close,
            "volume":         r.volume,
            "taker_buy_base": r.taker_buy_base,
        } for r in reversed(rows)]
    return pd.DataFrame(data)


def candle_counts() -> dict[str, dict[str, int]]:
    """Return {symbol: {interval: count}} — useful for status reporting."""
    with get_session() as s:
        rows = (
            s.query(
                OhlcvCandle.symbol,
                OhlcvCandle.interval,
                func.count(OhlcvCandle.id).label("cnt"),
            )
            .group_by(OhlcvCandle.symbol, OhlcvCandle.interval)
            .all()
        )
    result: dict[str, dict[str, int]] = {}
    for sym, intv, cnt in rows:
        result.setdefault(sym, {})[intv] = cnt
    return result


# ── Symbol refresh ────────────────────────────────────────────────────────────

async def refresh_interval_batch(interval: str) -> int:
    """Batch refresh: fetch all watchlist coins concurrently for efficiency."""
    import concurrent.futures
    symbols = get_symbols()
    total = 0
    # Use concurrent requests to reduce total time (efficiency improvement)
    # Still respect rate limits with delay between batches
    batch_size = 5  # small batch to stay under Binance limits
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        results = await asyncio.gather(
            *[refresh_symbol(sym, interval) for sym in batch],
            return_exceptions=True
        )
        total += sum(r if isinstance(r, int) else 0 for r in results)
        await asyncio.sleep(_REQ_DELAY)
    # Save checkpoint
    _save_checkpoint(symbols, interval, candle_counts())
    logger.info(f"Batch refresh [{interval}] — {total} new candles, {len(symbols)} coins")
    return total


async def refresh_symbol(symbol: str, interval: str) -> int:
    try:
        limit    = INTERVAL_LIMITS[interval]
        existing = _existing_timestamps(symbol, interval)
        klines   = await _fetch_raw(symbol, interval, limit)
        count    = _save_candles(symbol, interval, klines, existing)
        if count:
            logger.debug(f"{symbol} {interval}: +{count} candles")
        return count
    except Exception as e:
        logger.error(f"Kline fetch failed — {symbol} {interval}: {e}")
        return 0


async def refresh_interval(interval: str) -> int:
    """Refresh all watchlist coins for one interval. Called by scheduler."""
    symbols = get_symbols()
    total   = 0
    for sym in symbols:
        total += await refresh_symbol(sym, interval)
        await asyncio.sleep(_REQ_DELAY)
    # ── checkpoint: persist progress for auto-resume ──────────────────
    _save_checkpoint(symbols, interval, candle_counts())
    logger.info(f"Candle refresh [{interval}] — {total} new candles, {len(symbols)} coins")
    return total


def _checkpoint_path() -> Path:
    return Path("data/checkpoint.json")


def _save_checkpoint(symbols: list[str], interval: str, counts: dict[str, dict[str, int]]) -> None:
    """Save per-symbol candle progress to disk for auto-resume on restart."""
    payload = {
        "interval": interval,
        "symbols": {sym: counts.get(sym, {}).get(interval, 0) for sym in symbols},
        "saved_at": datetime.utcnow().isoformat() + "Z",
    }
    _checkpoint_path().write_text(json.dumps(payload, indent=2))


def _load_checkpoint() -> dict | None:
    """Load the last checkpoint; returns None if absent or invalid."""
    p = _checkpoint_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (json.JSONDecodeError, KeyError):
        return None


async def _fetch_daily_extended(symbol: str) -> int:
    """Fetch ~3 years of daily candles using two Binance requests (max 1000 each)."""
    from datetime import timedelta
    existing = _existing_timestamps(symbol, "1d")
    saved = 0

    # Request 1: most recent 1000 candles (~2.74 years)
    klines = await _fetch_raw(symbol, "1d", limit=1000)
    saved += _save_candles(symbol, "1d", klines, existing)
    await asyncio.sleep(_REQ_DELAY)

    # Request 2: oldest ~95-day gap (from 3 years ago, fills what request 1 missed)
    existing = _existing_timestamps(symbol, "1d")
    start_ms = int((datetime.utcnow() - timedelta(days=1095)).timestamp() * 1000)
    klines = await _fetch_raw(symbol, "1d", limit=200, start_ms=start_ms)
    saved += _save_candles(symbol, "1d", klines, existing)

    if saved:
        logger.debug(f"{symbol} 1d extended: +{saved} candles")
    return saved


async def fetch_hourly_extended(symbol: str, target_days: int = 1460) -> int:
    """
    Backfill 1h candles for a coin going back target_days.
    Paginates backwards in 1000-candle batches until the target is reached
    or Binance returns no older data. Safe to call multiple times — dedupes by timestamp.
    Returns total new candles saved.
    """
    from datetime import timedelta

    target_candles = target_days * 24
    saved_total = 0

    existing = _existing_timestamps(symbol, "1h")
    current_count = len(existing)

    if current_count >= target_candles:
        return 0  # already have enough

    # Walk backwards: start from oldest stored candle, or now
    if existing:
        oldest_ts = min(existing)
        end_ms = int(oldest_ts.timestamp() * 1000)
    else:
        end_ms = int(datetime.utcnow().timestamp() * 1000)

    cutoff = datetime.utcnow() - timedelta(days=target_days)

    while True:
        start_ms = end_ms - (1000 * 3600 * 1000)  # 1000 hours earlier
        if datetime.utcfromtimestamp(start_ms / 1000) < cutoff:
            start_ms = int(cutoff.timestamp() * 1000)

        url = (
            f"{_KLINES_URL}?symbol={symbol}USDT"
            f"&interval=1h&limit=1000"
            f"&startTime={start_ms}&endTime={end_ms}"
        )
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url)
            r.raise_for_status()
            klines = r.json()

        if not klines:
            break

        saved = _save_candles(symbol, "1h", klines, existing)
        saved_total += saved
        for k in klines:
            existing.add(datetime.utcfromtimestamp(k[0] / 1000))

        oldest_in_batch = datetime.utcfromtimestamp(klines[0][0] / 1000)
        end_ms = int(klines[0][0])  # step back to just before this batch

        if oldest_in_batch <= cutoff or len(existing) >= target_candles:
            break

        await asyncio.sleep(_REQ_DELAY)

    if saved_total:
        logger.info(f"{symbol} 1h backfill: +{saved_total} candles ({len(existing)} total)")
    return saved_total


async def fetch_4h_extended(symbol: str, target_days: int = 1460) -> int:
    """
    Backfill 4h candles going back target_days (default 4 years = 8760 candles).
    Paginates backwards in 1000-candle batches (~167 days each). ~9 calls per symbol.
    Safe to call multiple times — dedupes by timestamp.
    """
    from datetime import timedelta

    CANDLE_MS    = 4 * 3600 * 1000          # 4h in milliseconds
    target_candles = target_days * 6        # 6 four-hour bars per day
    saved_total  = 0

    existing = _existing_timestamps(symbol, "4h")
    if len(existing) >= target_candles:
        return 0

    end_ms  = int(min(existing).timestamp() * 1000) if existing else int(datetime.utcnow().timestamp() * 1000)
    cutoff  = datetime.utcnow() - timedelta(days=target_days)

    while True:
        start_ms = end_ms - (1000 * CANDLE_MS)
        if datetime.utcfromtimestamp(start_ms / 1000) < cutoff:
            start_ms = int(cutoff.timestamp() * 1000)

        url = (
            f"{_KLINES_URL}?symbol={symbol}USDT"
            f"&interval=4h&limit=1000"
            f"&startTime={start_ms}&endTime={end_ms}"
        )
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(url)
            r.raise_for_status()
            klines = r.json()

        if not klines:
            break

        saved = _save_candles(symbol, "4h", klines, existing)
        saved_total += saved
        for k in klines:
            existing.add(datetime.utcfromtimestamp(k[0] / 1000))

        oldest_in_batch = datetime.utcfromtimestamp(klines[0][0] / 1000)
        end_ms = int(klines[0][0])

        if oldest_in_batch <= cutoff or len(existing) >= target_candles:
            break

        await asyncio.sleep(_REQ_DELAY)

    if saved_total:
        logger.info(f"{symbol} 4h backfill: +{saved_total} candles ({len(existing)} total)")
    return saved_total


# Track in-progress backfills so we can report status
_backfill_running: set[str] = set()


async def ensure_hourly_backfill(symbol: str, target_days: int = 1460) -> None:
    """Launch backfill in the background if not already running."""
    if symbol in _backfill_running:
        return
    _backfill_running.add(symbol)
    try:
        await fetch_hourly_extended(symbol, target_days)
    except Exception as e:
        logger.debug(f"Hourly backfill {symbol} skipped: {e}")
    finally:
        _backfill_running.discard(symbol)


def backfill_status(symbol: str) -> dict:
    """Return current 1h candle count and whether a backfill is running."""
    with get_session() as s:
        count = (
            s.query(func.count(OhlcvCandle.id))
            .filter(OhlcvCandle.symbol == symbol, OhlcvCandle.interval == "1h")
            .scalar() or 0
        )
    target = 1460 * 24
    return {
        "symbol":       symbol,
        "candles_1h":   count,
        "target":       target,
        "days_covered": round(count / 24, 1),
        "pct_complete": min(100, round(count / target * 100)),
        "backfilling":  symbol in _backfill_running,
        "ready":        count >= 7 * 24,  # at least 1 week to show anything
    }


async def startup_fetch() -> None:
    """Full historical fetch on first run. Extends 1d to 3 years and seeds 1w (4 years).
    On restart, loads the last checkpoint and skips intervals already have enough data,
    enabling auto-resume after rate limits or system restarts."""
    checkpoint = _load_checkpoint()
    skip_symbols = set()
    skip_intervals = set()
    if checkpoint:
        # If the checkpoint interval matches one we're about to seed, skip it
        if checkpoint.get("interval") in ("1w", "1d", "4h", "1h", "15m"):
            skip_intervals.add(checkpoint["interval"])
        # Per-symbol: if already have enough candles per interval, skip
        for sym, saved in checkpoint.get("symbols", {}).items():
            if saved >= INTERVAL_LIMITS.get(checkpoint["interval"], 0):
                skip_symbols.add(sym)
    logger.info(f"Checkpoint loaded: skip_symbols={len(skip_symbols)}, skip_intervals={skip_intervals}")
    counts  = candle_counts()
    symbols = get_symbols()

    # Weekly — 4 years (210 candles, single request per coin)
    for sym in symbols:
        if sym in skip_symbols or counts.get(sym, {}).get("1w", 0) >= 180:
            logger.debug(f"Skipping 1w fetch for {sym} (checkpoint up to date)")
            continue
        await refresh_symbol(sym, "1w")
        await asyncio.sleep(_REQ_DELAY)

    # Daily — 3 years (two requests per coin; scheduler keeps it topped up with 365)
    for sym in symbols:
        if sym in skip_symbols or counts.get(sym, {}).get("1d", 0) >= 900:
            logger.debug(f"Skipping 1d fetch for {sym} (checkpoint up to date)")
            continue
        if checkpoint and checkpoint.get("interval") == "1d":
            # If checkpoint is from a 1d run and this sym is in skip_symbols, we already handled it
            pass
        if counts.get(sym, {}).get("1d", 0) < 900:
            await _fetch_daily_extended(sym)
        else:
            await refresh_symbol(sym, "1d")
        await asyncio.sleep(_REQ_DELAY)

    # Sub-daily intervals (single request each)
    for interval in ("4h", "1h", "15m"):
        if interval in skip_intervals:
            logger.debug(f"Skipping {interval} fetch (checkpoint up to date)")
            continue
        for sym in symbols:
            if sym in skip_symbols:
                continue
            await refresh_symbol(sym, interval)
            await asyncio.sleep(_REQ_DELAY)

    # Track failed fetches for automatic retry
_failed_fetches: list[dict] = []


def record_failed_fetch(symbol: str, interval: str, reason: str) -> None:
    """Record a failed fetch for later automatic retry."""
    _failed_fetches.append({
        "symbol": symbol, "interval": interval,
        "reason": str(reason),
        "failed_at": datetime.utcnow().isoformat(),
        "retried": False,
    })


def get_failed_fetches() -> list[dict]:
    """Get list of failed fetches that haven't been retried."""
    return [f for f in _failed_fetches if not f.get("retried", False)]


async def retry_failed_fetches() -> int:
    """Automatically retry all previously failed fetches.
    Called periodically (e.g., every 30 seconds) to overcome rate limits.
    Returns number of successful retries."""
    retries_done = 0
    for fail in get_failed_fetches():
        try:
            await refresh_symbol(fail["symbol"], fail["interval"])
            fail["retried"] = True
            fail["retried_at"] = datetime.utcnow().isoformat()
            retries_done += 1
            logger.info(f"Auto-retry success: {fail['symbol']} {fail['interval']} (was: {fail['reason']})")
            await asyncio.sleep(_REQ_DELAY)
        except Exception as e:
            fail["last_retry_error"] = str(e)
            logger.warning(f"Auto-retry failed: {fail['symbol']} {fail['interval']}: {e}")
    return retries_done


logger.info("Historical data fetch complete — 1w:210, 1d:~1095, 4h:300, 1h:200, 15m:200 candles/coin")
