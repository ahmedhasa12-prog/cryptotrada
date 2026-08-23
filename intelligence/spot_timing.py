"""
Spot-coin timing analysis — built from stored 1h OHLCV candles.

Three views per coin:
  hourly_patterns(symbol)  — avg volatility / volume / bull-rate by hour-of-day (UTC)
  weekday_patterns(symbol) — same aggregated by day-of-week (0=Mon)
  session_stats(symbol)    — Asian / London / US session performance
"""
from __future__ import annotations

from collections import defaultdict

from data.database import get_session
from data.models import OhlcvCandle

# Session windows in UTC hours (inclusive start, exclusive end)
SESSIONS = {
    "asian":  (0,  8),
    "london": (7,  16),
    "us":     (13, 22),
}


_CANDLE_LIMIT = 2160  # 90 days of 1H candles — enough for session/hour/dow stats


def _load_candles(symbol: str) -> list[OhlcvCandle]:
    with get_session() as s:
        rows = (
            s.query(OhlcvCandle)
            .filter(OhlcvCandle.symbol == symbol, OhlcvCandle.interval == "1h")
            .order_by(OhlcvCandle.timestamp.desc())
            .limit(_CANDLE_LIMIT)
            .all()
        )
        rows = list(reversed(rows))  # restore chronological order
        return [
            {
                "ts":     r.timestamp,
                "open":   r.open,
                "high":   r.high,
                "low":    r.low,
                "close":  r.close,
                "volume": r.volume,
            }
            for r in rows
        ]


def _metrics(candles: list[dict]) -> dict:
    if not candles:
        return None
    ranges   = [(c["high"] - c["low"]) / c["open"] * 100 for c in candles if c["open"]]
    returns  = [(c["close"] - c["open"]) / c["open"] * 100 for c in candles if c["open"]]
    volumes  = [c["volume"] for c in candles]
    bull_pct = sum(1 for r in returns if r > 0) / len(returns) * 100 if returns else None
    return {
        "avg_range_pct":  round(sum(ranges)  / len(ranges),  3) if ranges  else None,
        "avg_return_pct": round(sum(returns) / len(returns), 3) if returns else None,
        "avg_volume":     round(sum(volumes) / len(volumes), 2) if volumes else None,
        "bull_pct":       round(bull_pct, 1) if bull_pct is not None else None,
        "sample_count":   len(candles),
        "reliable":       len(candles) >= 5,
    }


def hourly_patterns(symbol: str) -> list[dict]:
    """24 slots (UTC hours). Each slot has volatility, volume, direction stats."""
    candles = _load_candles(symbol)
    buckets: dict[int, list] = defaultdict(list)
    for c in candles:
        buckets[c["ts"].hour].append(c)

    result = []
    for hour in range(24):
        m = _metrics(buckets[hour])
        result.append({"hour": hour, **(m or {
            "avg_range_pct": None, "avg_return_pct": None,
            "avg_volume": None, "bull_pct": None,
            "sample_count": 0, "reliable": False,
        })})
    return result


def weekday_patterns(symbol: str) -> list[dict]:
    """7 slots (0=Mon … 6=Sun). Each slot has volatility, volume, direction stats."""
    candles = _load_candles(symbol)
    buckets: dict[int, list] = defaultdict(list)
    for c in candles:
        buckets[c["ts"].weekday()].append(c)

    day_keys = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    result = []
    for day in range(7):
        m = _metrics(buckets[day])
        result.append({"day": day, "day_key": day_keys[day], **(m or {
            "avg_range_pct": None, "avg_return_pct": None,
            "avg_volume": None, "bull_pct": None,
            "sample_count": 0, "reliable": False,
        })})
    return result


def session_stats(symbol: str) -> list[dict]:
    """Asian / London / US session performance summary."""
    candles = _load_candles(symbol)
    buckets: dict[str, list] = defaultdict(list)
    for c in candles:
        h = c["ts"].hour
        for name, (start, end) in SESSIONS.items():
            if start <= h < end:
                buckets[name].append(c)

    result = []
    for name, (start, end) in SESSIONS.items():
        m = _metrics(buckets[name])
        result.append({
            "session":   name,
            "utc_hours": f"{start:02d}:00–{end:02d}:00",
            **(m or {
                "avg_range_pct": None, "avg_return_pct": None,
                "avg_volume": None, "bull_pct": None,
                "sample_count": 0, "reliable": False,
            }),
        })
    return result


def month_of_year_patterns(symbol: str) -> list[dict]:
    """12 slots (1=Jan … 12=Dec). Each slot has volatility, volume, direction stats."""
    candles = _load_candles(symbol)
    buckets: dict[int, list] = defaultdict(list)
    for c in candles:
        buckets[c["ts"].month].append(c)
    result = []
    for month in range(1, 13):
        m = _metrics(buckets[month])
        result.append({"month": month, **(m or {
            "avg_range_pct": None, "avg_return_pct": None,
            "avg_volume": None, "bull_pct": None,
            "sample_count": 0, "reliable": False,
        })})
    return result


def week_of_month_patterns(symbol: str) -> list[dict]:
    """4 slots: week 1 (days 1-7), week 2 (8-14), week 3 (15-21), week 4 (22+)."""
    candles = _load_candles(symbol)
    buckets: dict[int, list] = defaultdict(list)
    for c in candles:
        week = min(4, (c["ts"].day - 1) // 7 + 1)
        buckets[week].append(c)
    result = []
    for week in range(1, 5):
        m = _metrics(buckets[week])
        result.append({"week": week, **(m or {
            "avg_range_pct": None, "avg_return_pct": None,
            "avg_volume": None, "bull_pct": None,
            "sample_count": 0, "reliable": False,
        })})
    return result


def timing_summary(symbol: str) -> dict:
    """Full timing payload — hourly, weekday, session, week-of-month, month-of-year — in one call."""
    return {
        "symbol":          symbol,
        "hourly":          hourly_patterns(symbol),
        "weekday":         weekday_patterns(symbol),
        "sessions":        session_stats(symbol),
        "week_of_month":   week_of_month_patterns(symbol),
        "month_of_year":   month_of_year_patterns(symbol),
    }
