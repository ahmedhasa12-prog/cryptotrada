"""Analytics endpoints — historical context for live trading decisions."""
from __future__ import annotations

from fastapi import APIRouter, Query

from intelligence.analytics import get_spread_history, get_market_context, get_hourly_patterns

router = APIRouter(prefix="/api/p2p/analytics")


@router.get("/history")
def spread_history(days: int = Query(default=7, ge=1, le=90)):
    return get_spread_history(days)


@router.get("/context")
def market_context(days: int = Query(default=30, ge=1, le=90)):
    return get_market_context(days)


@router.get("/patterns")
def hourly_patterns():
    return get_hourly_patterns()
