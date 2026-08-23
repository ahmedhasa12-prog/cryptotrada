"""
Market analytics — historical context for live trading decisions.

Three functions:
  get_spread_history(days)  — hourly-averaged spread + rates for charting
  get_market_context(days)  — "now vs history" percentile and range stats
  get_hourly_patterns()     — average spread by hour-of-day across all data
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import func

from data.database import get_session
from data.models import MarketSnapshot


def get_spread_history(days: int = 7) -> list[dict]:
    """
    Return one averaged data point per hour for the last N days.
    Suitable for charting — avoids returning thousands of raw 5-min rows.
    """
    since = datetime.utcnow() - timedelta(days=days)
    with get_session() as s:
        rows = (
            s.query(MarketSnapshot)
            .filter(
                MarketSnapshot.timestamp >= since,
                MarketSnapshot.spread.isnot(None),
            )
            .order_by(MarketSnapshot.timestamp.asc())
            .all()
        )
        for r in rows:
            s.expunge(r)

    # Group into hourly buckets and average
    buckets: dict[datetime, list] = defaultdict(list)
    for r in rows:
        hour_key = r.timestamp.replace(minute=0, second=0, microsecond=0)
        buckets[hour_key].append(r)

    result = []
    for hour_key in sorted(buckets):
        group = buckets[hour_key]
        spreads   = [r.spread         for r in group if r.spread          is not None]
        buy_rates = [r.buy_best_rate  for r in group if r.buy_best_rate   is not None]
        sell_rates= [r.sell_best_rate for r in group if r.sell_best_rate  is not None]
        result.append({
            "timestamp":  hour_key.isoformat(),
            "spread":     round(sum(spreads)    / len(spreads),    2) if spreads    else None,
            "buy_rate":   round(sum(buy_rates)  / len(buy_rates),  2) if buy_rates  else None,
            "sell_rate":  round(sum(sell_rates) / len(sell_rates), 2) if sell_rates else None,
        })
    return result


def get_market_context(days: int = 30) -> dict:
    """
    Compare current market conditions to the last N days of history.
    Returns percentile rank, distance from average, and 24h rate range.
    """
    since      = datetime.utcnow() - timedelta(days=days)
    since_24h  = datetime.utcnow() - timedelta(hours=24)

    with get_session() as s:
        latest = (
            s.query(MarketSnapshot)
            .filter(MarketSnapshot.spread.isnot(None))
            .order_by(MarketSnapshot.timestamp.desc())
            .first()
        )
        if not latest:
            return {"ok": False}

        current_spread   = latest.spread
        current_buy_rate = latest.buy_best_rate

        # Aggregate stats over history window
        hist = s.query(
            func.avg(MarketSnapshot.spread).label("avg"),
            func.min(MarketSnapshot.spread).label("min"),
            func.max(MarketSnapshot.spread).label("max"),
            func.count(MarketSnapshot.id).label("total"),
        ).filter(
            MarketSnapshot.timestamp >= since,
            MarketSnapshot.spread.isnot(None),
        ).one()

        # How many historical spreads are ≤ the current one?
        below = s.query(func.count(MarketSnapshot.id)).filter(
            MarketSnapshot.timestamp >= since,
            MarketSnapshot.spread.isnot(None),
            MarketSnapshot.spread <= current_spread,
        ).scalar() or 0

        # 24-hour buy-rate range
        rate_range = s.query(
            func.min(MarketSnapshot.buy_best_rate).label("low"),
            func.max(MarketSnapshot.buy_best_rate).label("high"),
        ).filter(
            MarketSnapshot.timestamp >= since_24h,
            MarketSnapshot.buy_best_rate.isnot(None),
        ).one()

    total = int(hist.total) if hist.total else 0
    avg   = round(float(hist.avg), 2) if hist.avg is not None else None

    return {
        "ok":                True,
        "current_spread":    current_spread,
        "current_buy_rate":  current_buy_rate,
        "spread_avg":        avg,
        "spread_min":        round(float(hist.min), 2) if hist.min is not None else None,
        "spread_max":        round(float(hist.max), 2) if hist.max is not None else None,
        "spread_vs_avg":     round(current_spread - avg, 2) if avg is not None else None,
        "spread_percentile": round(below / total * 100) if total > 0 else None,
        "rate_24h_low":      round(float(rate_range.low),  2) if rate_range.low  is not None else None,
        "rate_24h_high":     round(float(rate_range.high), 2) if rate_range.high is not None else None,
        "sample_count":      total,
        "days":              days,
    }


def get_weekday_patterns() -> list[dict]:
    """Average spread grouped by day-of-week (0=Mon … 6=Sun) across all snapshots."""
    with get_session() as s:
        rows = (
            s.query(MarketSnapshot.timestamp, MarketSnapshot.spread)
            .filter(MarketSnapshot.spread.isnot(None))
            .all()
        )

    buckets: dict[int, list[float]] = defaultdict(list)
    for ts, spread in rows:
        buckets[ts.weekday()].append(spread)

    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    return [
        {
            "day":          day,
            "day_key":      day_names[day],
            "avg_spread":   round(sum(v) / len(v), 2) if (v := buckets[day]) else None,
            "sample_count": len(buckets[day]),
            "reliable":     len(buckets[day]) >= 3,
        }
        for day in range(7)
    ]


def get_heatmap() -> list[dict]:
    """7×24 grid of avg spread for every (weekday, hour-of-day) combination."""
    with get_session() as s:
        rows = (
            s.query(MarketSnapshot.timestamp, MarketSnapshot.spread)
            .filter(MarketSnapshot.spread.isnot(None))
            .all()
        )

    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    for ts, spread in rows:
        buckets[(ts.weekday(), ts.hour)].append(spread)

    result = []
    for day in range(7):
        for hour in range(24):
            vals = buckets[(day, hour)]
            result.append({
                "day":          day,
                "hour":         hour,
                "avg_spread":   round(sum(vals) / len(vals), 2) if vals else None,
                "sample_count": len(vals),
                "reliable":     len(vals) >= 3,
            })
    return result


def get_hourly_patterns() -> list[dict]:
    """
    Average spread grouped by hour-of-day (0–23) across all stored snapshots.
    Returns 24 slots; slots with fewer than 3 samples are flagged as unreliable.
    """
    with get_session() as s:
        rows = (
            s.query(MarketSnapshot.timestamp, MarketSnapshot.spread)
            .filter(MarketSnapshot.spread.isnot(None))
            .all()
        )

    buckets: dict[int, list[float]] = defaultdict(list)
    for ts, spread in rows:
        buckets[ts.hour].append(spread)

    result = []
    for hour in range(24):
        values = buckets[hour]
        result.append({
            "hour":         hour,
            "avg_spread":   round(sum(values) / len(values), 2) if values else None,
            "sample_count": len(values),
            "reliable":     len(values) >= 3,
        })
    return result
