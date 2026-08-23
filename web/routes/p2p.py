from __future__ import annotations

import json

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func

from config import get_config
from data.database import get_session
from data.models import MarketSnapshot
from intelligence.sdg_monitor import compute_rate_trend
from p2p.market_monitor import get_recent_snapshots, compute_average_spread
from p2p.p2p_logger import get_daily_stats, get_period_stats

router = APIRouter(prefix="/api/p2p")


def _compute_conditions(snaps: list, latest) -> list[dict]:
    """Derive inline market-condition badges. Returns structured params so the
    frontend can build localised text via i18n rather than using pre-built strings."""
    cfg = get_config()
    conditions: list[dict] = []

    # 1. Spread status
    spread = latest.spread
    if spread is not None:
        if spread >= cfg.p2p_spread_alert_high:
            conditions.append({
                "type": "spread_wide", "level": "wide", "icon": "📈",
                "params": {"spread": f"{spread:.1f}"},
            })
        elif spread < cfg.p2p_spread_alert_low:
            conditions.append({
                "type": "spread_tight", "level": "tight", "icon": "⚠️",
                "params": {"spread": f"{spread:.1f}"},
            })
        else:
            conditions.append({
                "type": "spread_normal", "level": "normal", "icon": "✅",
                "params": {"spread": f"{spread:.1f}"},
            })

    # 2. Premium buyer check from stored competitors_json
    if latest.competitors_json:
        comps = json.loads(latest.competitors_json)
        buyers = comps.get("buy_top10", [])
        if len(buyers) >= 2:
            premium = round(buyers[0]["price"] - buyers[1]["price"], 2)
            if premium >= cfg.p2p_premium_buyer_threshold:
                conditions.append({
                    "type": "premium_buyer", "level": "info", "icon": "💰",
                    "params": {
                        "name":    buyers[0]["name"],
                        "price":   f"{buyers[0]['price']:.2f}",
                        "premium": f"{premium:.1f}",
                    },
                })

    # 3. SDG rate trend (1h and 6h)
    if len(snaps) >= 2:
        trend_1h = compute_rate_trend(snaps, window_slots=12)
        trend_6h = compute_rate_trend(snaps, window_slots=72)

        if abs(trend_1h.change_abs) >= 5.0:
            direction = "up" if trend_1h.direction == "up" else "down"
            conditions.append({
                "type": f"trend_1h_{direction}", "level": "warning", "icon": "📊",
                "params": {
                    "change":     f"{abs(trend_1h.change_abs):.1f}",
                    "from_rate":  f"{trend_1h.from_rate:.1f}",
                    "to_rate":    f"{trend_1h.to_rate:.1f}",
                },
            })
        elif trend_6h.direction != "stable" and abs(trend_6h.change_abs) >= 10.0:
            direction = "up" if trend_6h.direction == "up" else "down"
            conditions.append({
                "type": f"trend_6h_{direction}", "level": "info",
                "icon": "📈" if trend_6h.direction == "up" else "📉",
                "params": {"change": f"{trend_6h.change_abs:+.1f}"},
            })

    return conditions


class SnapshotResponse(BaseModel):
    buy_best_rate: float | None
    sell_best_rate: float | None
    spread: float | None
    avg_spread_1h: float | None
    avg_spread_24h: float | None
    timestamp: str | None
    top_sellers: list[dict]    # top buyers  — who to sell USDT to
    active_sellers: list[dict] # top sellers — your competitors / who to buy from
    conditions: list[dict]     # inline market-condition badges


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
    snaps_24h = get_recent_snapshots(limit=288)   # single query; slice for shorter windows
    snaps_6h  = snaps_24h[:72]
    snaps_1h  = snaps_24h[:12]

    if not snaps_1h:
        return SnapshotResponse(
            buy_best_rate=None, sell_best_rate=None, spread=None,
            avg_spread_1h=None, avg_spread_24h=None, timestamp=None,
            top_sellers=[], active_sellers=[], conditions=[],
        )

    latest = snaps_1h[0]
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
        conditions=_compute_conditions(snaps_6h, latest),
    )


@router.get("/history")
def get_history(limit: int = 500):
    """Return time-series of buy/sell rates (oldest first) for charting."""
    snaps = get_recent_snapshots(limit=limit)
    return [
        {
            "t":      s.timestamp.isoformat(),
            "buy":    s.buy_best_rate,
            "sell":   s.sell_best_rate,
            "spread": s.spread,
        }
        for s in reversed(snaps)  # oldest first
    ]


@router.get("/history/daily")
def get_daily_history():
    """Daily-averaged buy/sell rates for the historical 60-day chart."""
    with get_session() as session:
        rows = (
            session.query(
                func.date(MarketSnapshot.timestamp).label("d"),
                func.avg(MarketSnapshot.buy_best_rate).label("buy"),
                func.avg(MarketSnapshot.sell_best_rate).label("sell"),
                func.avg(MarketSnapshot.spread).label("spread"),
            )
            .group_by(func.date(MarketSnapshot.timestamp))
            .order_by(func.date(MarketSnapshot.timestamp))
            .all()
        )
        return [
            {
                "date":   str(r.d),
                "buy":    round(r.buy, 1)    if r.buy    is not None else None,
                "sell":   round(r.sell, 1)   if r.sell   is not None else None,
                "spread": round(r.spread, 1) if r.spread is not None else None,
            }
            for r in rows
        ]


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


@router.post("/trades/sync")
async def sync_trades_from_binance():
    """Pull completed P2P trades from Binance and import any not already stored."""
    from p2p.p2p_logger import sync_from_binance
    return await sync_from_binance()


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
