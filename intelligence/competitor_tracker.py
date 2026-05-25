"""
Competitor rate-change tracker.

After every market poll, compares prices for watched merchants against
the previous snapshot. Alerts when a key competitor moves their rate.
"""
from __future__ import annotations

import json

from config import get_config
from data.models import MarketSnapshot
from p2p.market_monitor import Offer


def _prices_from_snapshot(snap: MarketSnapshot) -> dict[str, float]:
    """merchant_name → price extracted from a stored snapshot's competitors_json."""
    if not snap or not snap.competitors_json:
        return {}
    data = json.loads(snap.competitors_json)
    prices: dict[str, float] = {}
    for offer in data.get("buy_top10", []) + data.get("sell_top10", []):
        name = offer.get("name", "")
        price = offer.get("price")
        if name and price is not None:
            prices[name] = float(price)
    return prices


def _prices_from_offers(offers: list[Offer]) -> dict[str, float]:
    """merchant_name → price from live Offer objects."""
    return {o.merchant_name: o.price for o in offers}


def check_competitor_changes(
    current_buy: list[Offer],
    current_sell: list[Offer],
    last_snapshot: MarketSnapshot | None,
) -> list[str]:
    """
    Compare current offer prices to the previous snapshot for watched merchants.
    Returns alert strings for any merchant whose rate changed beyond the threshold.
    Called before saving the new snapshot so last_snapshot is truly the previous poll.
    """
    cfg = get_config()
    watched = {m.strip() for m in cfg.p2p_watched_merchants if m.strip()}
    if not watched or last_snapshot is None:
        return []

    threshold = cfg.p2p_competitor_alert_threshold
    prev = _prices_from_snapshot(last_snapshot)

    current: dict[str, float] = {}
    current.update(_prices_from_offers(current_buy))
    current.update(_prices_from_offers(current_sell))

    alerts = []
    for name in sorted(watched):
        prev_price = prev.get(name)
        curr_price = current.get(name)
        if prev_price is None or curr_price is None:
            continue
        change = round(curr_price - prev_price, 2)
        if abs(change) >= threshold:
            arrow = "↑" if change > 0 else "↓"
            alerts.append(
                f"🔔 {name} {arrow} {abs(change):.1f} SDG "
                f"({prev_price:.2f} → {curr_price:.2f}). "
                f"Market may be shifting."
            )
    return alerts
