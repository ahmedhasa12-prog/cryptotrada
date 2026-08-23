"""
Macro dashboard data: BTC dominance (CoinGecko) + Fear & Greed (alternative.me).
Cached in macro_snapshots table so the dashboard is instant even if APIs are slow.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import httpx
from loguru import logger

from data.database import get_session
from data.models import MacroSnapshot

_COINGECKO_GLOBAL = "https://api.coingecko.com/api/v3/global"
_FEAR_GREED_URL   = "https://api.alternative.me/fng/?limit=8"
_HTTP_TIMEOUT     = 10.0


# ── Season logic ─────────────────────────────────────────────────────────────

def _get_market_season(dominance: float, change_7d: float) -> str:
    if dominance > 55:
        if change_7d < -1.5:
            return "ALTCOIN_SEASON_STARTING"
        return "BITCOIN_SEASON"
    if dominance < 45:
        return "ALTCOIN_SEASON"
    return "TRANSITIONING"


SEASON_META: dict[str, dict] = {
    "BITCOIN_SEASON": {
        "label":      "Bitcoin Season",
        "icon":       "⚠️",
        "color":      "orange",
        "long_term":  "Good accumulation prices for alts",
        "short_term": "Stick to BNB and SOL only",
    },
    "ALTCOIN_SEASON_STARTING": {
        "label":      "Altcoin Season Starting!",
        "icon":       "🚨",
        "color":      "green",
        "long_term":  "Hold your positions — surge incoming",
        "short_term": "Get aggressive on quality alts",
    },
    "ALTCOIN_SEASON": {
        "label":      "Altcoin Season Active",
        "icon":       "🟢",
        "color":      "green",
        "long_term":  "Consider taking profits on long holds",
        "short_term": "Best time for alt trading",
    },
    "TRANSITIONING": {
        "label":      "Market Transitioning",
        "icon":       "🟡",
        "color":      "yellow",
        "long_term":  "Watch closely",
        "short_term": "Be selective",
    },
}


def _get_fg_label(value: int) -> str:
    if value <= 25:  return "Extreme Fear"
    if value <= 45:  return "Fear"
    if value <= 55:  return "Neutral"
    if value <= 75:  return "Greed"
    return "Extreme Greed"


def _get_fg_advice(value: int) -> str:
    if value <= 25:  return "Strong buy opportunity — market is panicking"
    if value <= 45:  return "Good entry zone — fear creates discounts"
    if value <= 55:  return "Neutral — be selective on entries"
    if value <= 75:  return "Caution on new buys — greed is elevated"
    return "Consider taking profits — extreme greed rarely lasts"


# ── External API fetchers ─────────────────────────────────────────────────────

async def _fetch_btc_dominance() -> tuple[float, float]:
    """Returns (btc_dominance_pct, total_market_cap_usd)."""
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        r = await client.get(_COINGECKO_GLOBAL)
        r.raise_for_status()
        data = r.json()["data"]
        dominance = data["market_cap_percentage"]["btc"]
        market_cap = data["total_market_cap"].get("usd", 0)
        return round(dominance, 2), market_cap


async def _fetch_fear_greed() -> dict:
    """Returns {value, label, yesterday, last_week}."""
    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        r = await client.get(_FEAR_GREED_URL)
        r.raise_for_status()
        entries = r.json()["data"]  # index 0 = today, 1 = yesterday, 7 = ~last week
        current   = int(entries[0]["value"])
        yesterday = int(entries[1]["value"]) if len(entries) > 1 else None
        last_week = int(entries[7]["value"]) if len(entries) > 7 else None
        return {
            "value":     current,
            "label":     _get_fg_label(current),
            "yesterday": yesterday,
            "last_week": last_week,
        }


# ── Snapshot save / load ──────────────────────────────────────────────────────

def _compute_7d_change(current: float) -> float | None:
    """Compare current dominance against snapshot from ~7 days ago."""
    cutoff = datetime.utcnow() - timedelta(days=6)
    with get_session() as s:
        old = (
            s.query(MacroSnapshot)
            .filter(MacroSnapshot.timestamp <= cutoff)
            .order_by(MacroSnapshot.timestamp.desc())
            .first()
        )
        if old and old.btc_dominance:
            return round(current - old.btc_dominance, 2)
    return None


def _save_snapshot(
    dominance: float,
    dominance_7d_change: float | None,
    market_cap: float,
    fg: dict,
    season: str,
) -> MacroSnapshot:
    snap = MacroSnapshot(
        btc_dominance=dominance,
        btc_dominance_7d_change=dominance_7d_change,
        market_season=season,
        fear_greed_value=fg["value"],
        fear_greed_label=fg["label"],
        fear_greed_yesterday=fg.get("yesterday"),
        fear_greed_last_week=fg.get("last_week"),
        total_market_cap_usd=market_cap,
    )
    with get_session() as s:
        s.add(snap)
    return snap


def get_latest_macro() -> dict | None:
    """Return the most recent macro snapshot as a plain dict, or None."""
    with get_session() as s:
        row = (
            s.query(MacroSnapshot)
            .order_by(MacroSnapshot.timestamp.desc())
            .first()
        )
        if not row:
            return None
        season = row.market_season or "TRANSITIONING"
        meta   = SEASON_META.get(season, SEASON_META["TRANSITIONING"])
        return {
            "btc_dominance":         row.btc_dominance,
            "btc_dominance_7d_change": row.btc_dominance_7d_change,
            "market_season":         season,
            "season_label":          meta["label"],
            "season_icon":           meta["icon"],
            "season_color":          meta["color"],
            "season_long_term":      meta["long_term"],
            "season_short_term":     meta["short_term"],
            "fear_greed_value":      row.fear_greed_value,
            "fear_greed_label":      row.fear_greed_label,
            "fear_greed_yesterday":  row.fear_greed_yesterday,
            "fear_greed_last_week":  row.fear_greed_last_week,
            "fear_greed_advice":     _get_fg_advice(row.fear_greed_value) if row.fear_greed_value else None,
            "total_market_cap_usd":  row.total_market_cap_usd,
            "timestamp":             row.timestamp.isoformat(),
        }


# ── Scheduled jobs ────────────────────────────────────────────────────────────

async def refresh_macro() -> None:
    """Fetch BTC dominance + Fear & Greed and save snapshot. Called by scheduler."""
    try:
        dominance, market_cap = await _fetch_btc_dominance()
        change_7d = _compute_7d_change(dominance)
        season    = _get_market_season(dominance, change_7d or 0)
        fg        = await _fetch_fear_greed()
        _save_snapshot(dominance, change_7d, market_cap, fg, season)
        logger.info(f"Macro refreshed — BTC dom: {dominance}%, F&G: {fg['value']} ({fg['label']})")
    except Exception as e:
        logger.error(f"Macro refresh error: {e}")
