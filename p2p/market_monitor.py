"""
P2P market monitor — polls the Binance P2P public endpoint every 5 minutes
and stores snapshots. No Binance API key required.

LIVE CALLS: Only made when start_polling() is called from the scheduler.
            All logic is fully testable via mocked HTTP responses.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Awaitable

import httpx
from loguru import logger

from config import get_config
from data.database import get_session
from data.models import MarketSnapshot

P2P_SEARCH_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

# Respectful rate: max 1 request per 30 seconds per the PRD
_MIN_INTERVAL_SECONDS = 30

# Merchants with payTimeLimit > this are slow/restricted and excluded from best-rate calc
_MAX_PAY_TIME_LIMIT = 30


@dataclass
class Offer:
    merchant_name: str
    price: float
    min_amount: float
    max_amount: float
    available_amount: float
    trade_count: int
    completion_rate: float  # 0.0 – 100.0
    payment_methods: list[str] = field(default_factory=list)
    pay_time_limit: int = 15  # minutes the buyer has to pay


@dataclass
class MarketData:
    timestamp: datetime
    buy_offers: list[Offer]   # merchants BUYING USDT from you (they pay SDG, tradeType="BUY")
    sell_offers: list[Offer]  # merchants SELLING USDT to you (they want SDG, tradeType="SELL")
    buy_best_rate: float | None  # highest price buyers offer (what you receive when selling USDT)
    sell_best_rate: float | None  # lowest price sellers charge (what you pay when buying USDT)
    spread: float | None  # buy_best - sell_best: positive = opportunity to buy low & sell high


def _build_payload(asset: str, fiat: str, trade_type: str, rows: int = 10) -> dict:
    """Build the POST payload for Binance P2P search."""
    return {
        "asset": asset,
        "fiat": fiat,
        "merchantCheck": False,
        "page": 1,
        "payTypes": [],
        "rows": rows,
        "tradeType": trade_type,  # "BUY" = they buy USDT, "SELL" = they sell USDT
    }


def _active_offers(offers: list[Offer]) -> list[Offer]:
    """Return offers from merchants with a normal pay time limit (<= 30 min).
    Merchants with 60+ min limits are typically restricted or inactive.
    Falls back to the full list only if every offer is slow (edge case)."""
    active = [o for o in offers if o.pay_time_limit <= _MAX_PAY_TIME_LIMIT]
    return active if active else offers


def _parse_offers(data: dict) -> list[Offer]:
    offers = []
    for item in data.get("data", []):
        adv = item.get("adv", {})
        advertiser = item.get("advertiser", {})
        try:
            offer = Offer(
                merchant_name=advertiser.get("nickName", "unknown"),
                price=float(adv.get("price", 0)),
                min_amount=float(adv.get("minSingleTransAmount", 0)),
                max_amount=float(adv.get("dynamicMaxSingleTransAmount", 0)),
                available_amount=float(adv.get("tradableQuantity", 0)),
                trade_count=int(advertiser.get("monthOrderCount", 0)),
                completion_rate=float(advertiser.get("monthFinishRate", 0)) * 100,
                payment_methods=[
                    t.get("tradeMethodName", "") for t in adv.get("tradeMethods", [])
                ],
                pay_time_limit=int(adv.get("payTimeLimit", 15)),
            )
            offers.append(offer)
        except (ValueError, TypeError) as e:
            logger.warning(f"Skipping malformed offer: {e}")
    return offers


async def fetch_market_data(
    asset: str | None = None,
    fiat: str | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> MarketData:
    """
    Fetch top 10 buy + sell offers from Binance P2P.
    Pass a pre-built client for testing (avoids real HTTP calls).
    """
    cfg = get_config()
    asset = asset or cfg.p2p_asset
    fiat = fiat or cfg.p2p_fiat

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=15.0)

    try:
        buy_resp = await client.post(
            P2P_SEARCH_URL,
            json=_build_payload(asset, fiat, "BUY"),
            headers=headers,
        )
        buy_resp.raise_for_status()

        sell_resp = await client.post(
            P2P_SEARCH_URL,
            json=_build_payload(asset, fiat, "SELL"),
            headers=headers,
        )
        sell_resp.raise_for_status()
    finally:
        if own_client:
            await client.aclose()

    buy_offers = _parse_offers(buy_resp.json())
    sell_offers = _parse_offers(sell_resp.json())

    # Use only active (non-restricted) offers for best-rate calculation
    active_buy = _active_offers(buy_offers)
    active_sell = _active_offers(sell_offers)

    buy_best = active_buy[0].price if active_buy else None
    sell_best = active_sell[0].price if active_sell else None
    spread = round(buy_best - sell_best, 2) if (buy_best and sell_best) else None

    return MarketData(
        timestamp=datetime.utcnow(),
        buy_offers=buy_offers,
        sell_offers=sell_offers,
        buy_best_rate=buy_best,
        sell_best_rate=sell_best,
        spread=spread,
    )


def save_snapshot(data: MarketData, our_rate: float | None = None) -> None:
    """Persist a MarketData snapshot to the database."""
    competitors = {
        "buy_top10": [
            {"name": o.merchant_name, "price": o.price, "min": o.min_amount, "max": o.max_amount}
            for o in _active_offers(data.buy_offers)
        ],
        "sell_top10": [
            {"name": o.merchant_name, "price": o.price, "min": o.min_amount, "max": o.max_amount}
            for o in _active_offers(data.sell_offers)
        ],
    }
    with get_session() as session:
        session.add(MarketSnapshot(
            timestamp=data.timestamp,
            buy_best_rate=data.buy_best_rate,
            sell_best_rate=data.sell_best_rate,
            spread=data.spread,
            our_rate=our_rate,
            competitors_json=json.dumps(competitors),
        ))
    logger.debug(f"Snapshot saved: spread={data.spread} {get_config().p2p_fiat}")


def check_alerts(data: MarketData) -> list[str]:
    """
    Return a list of alert strings based on current market conditions.
    Empty list = no alerts.
    """
    cfg = get_config()
    alerts = []

    if data.spread is None:
        return alerts

    if data.spread > cfg.p2p_spread_alert_high:
        alerts.append(
            f"📈 Wide spread detected: {data.spread:.1f} {cfg.p2p_fiat} "
            f"(threshold: {cfg.p2p_spread_alert_high}). Great opportunity!"
        )
    elif data.spread < cfg.p2p_spread_alert_low:
        alerts.append(
            f"⚠️ Tight spread: {data.spread:.1f} {cfg.p2p_fiat} "
            f"(threshold: {cfg.p2p_spread_alert_low}). Consider pausing."
        )

    return alerts


def check_premium_buyers(sell_offers: list[Offer]) -> list[str]:
    """
    Alert when an active buyer is paying significantly more than the next-best buyer.
    Compares best vs second-best among non-restricted offers.
    """
    cfg = get_config()
    active = _active_offers(sell_offers)
    if len(active) < 2:
        return []

    best = active[0]
    second = active[1]
    premium = round(best.price - second.price, 2)

    if premium >= cfg.p2p_premium_buyer_threshold:
        return [
            f"💰 Premium buyer: {best.merchant_name} paying {best.price:.2f} SDG "
            f"({premium:.1f} SDG above next buyer at {second.price:.2f}). "
            f"Consider selling to them now."
        ]
    return []


def get_recent_snapshots(limit: int = 12) -> list[MarketSnapshot]:
    """Return the most recent N snapshots (newest first)."""
    with get_session() as session:
        rows = (
            session.query(MarketSnapshot)
            .order_by(MarketSnapshot.timestamp.desc())
            .limit(limit)
            .all()
        )
        for row in rows:
            session.expunge(row)
        return rows


def compute_average_spread(snapshots: list[MarketSnapshot]) -> float | None:
    """Average spread across a list of snapshots, ignoring None values."""
    values = [s.spread for s in snapshots if s.spread is not None]
    return round(sum(values) / len(values), 2) if values else None
