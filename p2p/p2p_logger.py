"""
P2P trade logger and analytics.
Records every completed trade and generates daily statistics.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from loguru import logger
from sqlalchemy import func

from data.database import get_session
from data.models import P2PTrade


def log_trade(
    trade_type: str,
    amount_usdt: float,
    rate_sdg: float,
    trader_username: str,
    mode: str,
    *,
    trader_score: int | None = None,
    release_time_minutes: float | None = None,
    profit_sdg: float | None = None,
    bank_used: str | None = None,
    notes: str | None = None,
) -> P2PTrade:
    """Record a completed P2P trade to the database."""
    total_sdg = round(amount_usdt * rate_sdg, 2)
    trade = P2PTrade(
        timestamp=datetime.utcnow(),
        trade_type=trade_type,
        amount_usdt=amount_usdt,
        rate_sdg=rate_sdg,
        total_sdg=total_sdg,
        trader_username=trader_username,
        trader_score=trader_score,
        release_time_minutes=release_time_minutes,
        profit_sdg=profit_sdg,
        mode=mode,
        bank_used=bank_used,
        notes=notes,
    )
    with get_session() as s:
        s.add(trade)
        s.flush()
        trade_id = trade.id
        s.expunge(trade)
    logger.info(f"P2P trade logged: #{trade_id} {trade_type} {amount_usdt} USDT @ {rate_sdg} SDG")
    return trade


def get_daily_stats(date: datetime | None = None) -> dict:
    """Return aggregated stats for a given UTC date (defaults to today)."""
    if date is None:
        date = datetime.utcnow()

    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    with get_session() as s:
        row = s.query(
            func.count(P2PTrade.id).label("count"),
            func.coalesce(func.sum(P2PTrade.amount_usdt), 0.0).label("volume"),
            func.coalesce(func.sum(P2PTrade.profit_sdg), 0.0).label("profit"),
            func.avg(P2PTrade.release_time_minutes).label("avg_release"),
            func.max(P2PTrade.profit_sdg).label("best"),
        ).filter(
            P2PTrade.timestamp >= day_start,
            P2PTrade.timestamp < day_end,
        ).one()

    avg_release = round(float(row.avg_release), 2) if row.avg_release is not None else None

    return {
        "date": day_start.date().isoformat(),
        "count": int(row.count),
        "volume_usdt": round(float(row.volume), 2),
        "profit_sdg": round(float(row.profit), 2),
        "avg_release_minutes": avg_release,
        "best_trade_profit_sdg": float(row.best) if row.best is not None else 0.0,
    }


def get_period_stats(days: int) -> dict:
    """Return aggregated stats over the last N days."""
    since = datetime.utcnow() - timedelta(days=days)
    with get_session() as s:
        row = s.query(
            func.count(P2PTrade.id).label("count"),
            func.coalesce(func.sum(P2PTrade.amount_usdt), 0.0).label("volume"),
            func.coalesce(func.sum(P2PTrade.profit_sdg), 0.0).label("profit"),
        ).filter(P2PTrade.timestamp >= since).one()

    return {
        "days": days,
        "count": int(row.count),
        "volume_usdt": round(float(row.volume), 2),
        "profit_sdg": round(float(row.profit), 2),
    }
