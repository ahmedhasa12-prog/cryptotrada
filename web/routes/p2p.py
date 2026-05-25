from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from p2p.market_monitor import get_recent_snapshots, compute_average_spread
from p2p.p2p_logger import get_daily_stats, get_period_stats

router = APIRouter(prefix="/api/p2p")


class SnapshotResponse(BaseModel):
    buy_best_rate: float | None
    sell_best_rate: float | None
    spread: float | None
    avg_spread_1h: float | None
    avg_spread_24h: float | None
    timestamp: str | None
    top_sellers: list[dict]    # top buyers  — who to sell USDT to
    active_sellers: list[dict] # top sellers — your competitors / who to buy from


class TradesStatsResponse(BaseModel):
    date: str
    count: int
    volume_usdt: float
    profit_sdg: float
    avg_release_minutes: float | None
    best_trade_profit_sdg: float


class PeriodStatsResponse(BaseModel):
    days: int
    count: int
    volume_usdt: float
    profit_sdg: float


@router.get("/snapshot", response_model=SnapshotResponse)
def get_snapshot():
    snaps_1h = get_recent_snapshots(limit=12)   # 12 × 5 min = 1h
    snaps_24h = get_recent_snapshots(limit=288)  # 288 × 5 min = 24h

    if not snaps_1h:
        return SnapshotResponse(
            buy_best_rate=None, sell_best_rate=None, spread=None,
            avg_spread_1h=None, avg_spread_24h=None, timestamp=None,
            top_sellers=[], active_sellers=[],
        )

    latest = snaps_1h[0]
    import json
    competitors = json.loads(latest.competitors_json or "{}")
    top_sellers    = competitors.get("buy_top10",  [])[:5]
    active_sellers = competitors.get("sell_top10", [])[:5]

    return SnapshotResponse(
        buy_best_rate=latest.buy_best_rate,
        sell_best_rate=latest.sell_best_rate,
        spread=latest.spread,
        avg_spread_1h=compute_average_spread(snaps_1h),
        avg_spread_24h=compute_average_spread(snaps_24h),
        timestamp=latest.timestamp.isoformat() if latest.timestamp else None,
        top_sellers=top_sellers,
        active_sellers=active_sellers,
    )


class LogTradeRequest(BaseModel):
    trade_type: str          # "buy" | "sell"
    amount_usdt: float
    rate_sdg: float
    trader_username: str
    profit_sdg: float | None = None
    release_time_minutes: float | None = None
    bank_used: str | None = None
    notes: str | None = None


@router.post("/trades", status_code=201)
def log_trade_endpoint(req: LogTradeRequest):
    from p2p.p2p_logger import log_trade
    from web.state import get_state
    state = get_state()
    trade = log_trade(
        trade_type=req.trade_type,
        amount_usdt=req.amount_usdt,
        rate_sdg=req.rate_sdg,
        trader_username=req.trader_username,
        mode=state.mode.value,
        profit_sdg=req.profit_sdg,
        release_time_minutes=req.release_time_minutes,
        bank_used=req.bank_used,
        notes=req.notes,
    )
    return {"id": trade.id, "total_sdg": trade.total_sdg}


@router.get("/stats/today", response_model=TradesStatsResponse)
def get_today_stats():
    stats = get_daily_stats()
    return TradesStatsResponse(**stats)


@router.get("/stats/{days}", response_model=PeriodStatsResponse)
def get_period(days: int):
    if days not in (7, 30):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="days must be 7 or 30")
    return PeriodStatsResponse(**get_period_stats(days))
