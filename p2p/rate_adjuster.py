"""
P2P rate auto-adjuster.

On every market poll, reads the user's active P2P ads via the Binance
private API, computes the optimal price, and updates any ad whose rate
has drifted beyond `p2p_rate_adjuster_step`.

Strategy:
  SELL ad → price = best active sell price  - offset  (undercut competitors)
  BUY  ad → price = best active buy  price  + offset  (outbid  competitors)

Safety:
  - Does nothing unless P2P_RATE_ADJUSTER_ENABLED=true.
  - In MANUAL mode: suggests the new price but does NOT update the ad.
  - In SEMI / FULL mode: sends the update to Binance.
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import httpx
from loguru import logger

from binance.client import _sign, _auth_headers
from config import get_config, OperatingMode
from p2p.market_monitor import MarketData

_P2P_BASE = "https://p2p.binance.com"


# ── Data model ────────────────────────────────────────────────────────────────

@dataclass
class AdInfo:
    ad_no: str
    trade_type: str   # "BUY" or "SELL"
    price: float
    asset: str
    fiat: str


# ── Pure business logic (no I/O — fully testable) ─────────────────────────────

def compute_target_price(
    trade_type: str,
    data: MarketData,
    offset: float,
) -> float | None:
    """
    Return the ideal price for our ad given current market conditions.

    SELL ad: undercut the cheapest active seller by `offset` SDG.
    BUY  ad: outbid  the highest active buyer   by `offset` SDG.
    """
    if trade_type == "SELL":
        if data.sell_best_rate is None:
            return None
        return round(data.sell_best_rate - offset, 2)
    else:  # BUY
        if data.buy_best_rate is None:
            return None
        return round(data.buy_best_rate + offset, 2)


# ── Binance P2P private API ───────────────────────────────────────────────────

async def _p2p_post(endpoint: str, body: dict) -> dict:
    """POST to a Binance P2P private endpoint (timestamp + signature in query string)."""
    cfg = get_config()
    ts = int(time.time() * 1000)
    qs_params = {"timestamp": ts}
    qs_params["signature"] = _sign(cfg.binance_secret_key, qs_params)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{_P2P_BASE}{endpoint}",
            params=qs_params,
            json=body,
            headers={**_auth_headers(cfg.binance_api_key), "Content-Type": "application/json"},
        )
    resp.raise_for_status()
    return resp.json()


async def get_my_ads() -> list[AdInfo]:
    """Fetch the user's own active P2P ads from Binance."""
    cfg = get_config()
    resp = await _p2p_post(
        "/bapi/c2c/v2/private/c2c/adv/page",
        {"asset": cfg.p2p_asset, "fiat": cfg.p2p_fiat, "page": 1, "rows": 20},
    )
    # Binance wraps results in data.page.records or data directly
    data = resp.get("data", {})
    records = (
        data.get("page", {}).get("records", [])
        if isinstance(data, dict)
        else data if isinstance(data, list)
        else []
    )
    ads = []
    for item in records:
        try:
            ads.append(AdInfo(
                ad_no=item["advNo"],
                trade_type=item["tradeType"],
                price=float(item["price"]),
                asset=item["asset"],
                fiat=item["fiatUnit"],
            ))
        except (KeyError, ValueError) as exc:
            logger.warning(f"Skipping malformed ad record: {exc}")
    return ads


async def _update_ad_price(ad_no: str, new_price: float) -> bool:
    """Send a price-update request for one ad. Returns True on success."""
    try:
        resp = await _p2p_post(
            "/bapi/c2c/v2/private/c2c/adv/update",
            {"advNo": ad_no, "price": f"{new_price:.2f}"},
        )
        return resp.get("code") == "000000" or resp.get("success") is True
    except Exception as exc:
        logger.error(f"Rate adjuster: update failed for {ad_no}: {exc}")
        return False


# ── Orchestrator (called from main poll loop) ─────────────────────────────────

async def run_adjuster(data: MarketData) -> list[str]:
    """
    Inspect active ads and adjust prices that have drifted beyond the step size.
    Returns human-readable status strings suitable for the alert feed.
    """
    cfg = get_config()
    if not cfg.p2p_rate_adjuster_enabled:
        return []
    if not cfg.binance_api_key or not cfg.binance_secret_key:
        return []

    step = cfg.p2p_rate_adjuster_step
    offset = cfg.p2p_rate_adjuster_offset
    dry_run = cfg.operating_mode == OperatingMode.MANUAL

    try:
        ads = await get_my_ads()
    except Exception as exc:
        logger.error(f"Rate adjuster: could not fetch ads — {exc}")
        return []

    messages: list[str] = []
    for ad in ads:
        target = compute_target_price(ad.trade_type, data, offset)
        if target is None:
            continue

        drift = round(abs(target - ad.price), 2)
        if drift < step:
            continue

        direction = "↓" if target < ad.price else "↑"
        label = ad.trade_type  # "SELL" or "BUY"

        if dry_run:
            messages.append(
                f"💡 [{label}] Suggested rate: {target:.2f} SDG "
                f"({ad.price:.2f} → {target:.2f}, drift {drift:.1f} SDG). "
                f"Switch to Semi/Full mode to auto-apply."
            )
        else:
            ok = await _update_ad_price(ad.ad_no, target)
            if ok:
                messages.append(
                    f"✅ [{label}] Rate adjusted {direction} {drift:.1f} SDG "
                    f"({ad.price:.2f} → {target:.2f})"
                )
            else:
                messages.append(f"⚠️ [{label}] Rate update failed — check logs")

    return messages
