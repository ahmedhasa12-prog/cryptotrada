"""
Coin universe: static seed + dynamic weekly refresh via Stage 1+2 scorer.
The watchlist is seeded into the DB on first run; every Monday Stage 2 runs
and replaces non-pinned coins with the current top scorers.
"""
from __future__ import annotations

from datetime import datetime, timezone

from loguru import logger

from data.database import get_session
from data.models import SpotTrade, Watchlist, WatchlistScreenHistory
from spot.narratives import get_narrative_for_coin

# ── Golden filter (hard rules — no exceptions) ────────────────────────────────

GOLDEN_FILTERS = {
    "min_listing_age_days":    365,
    "min_daily_volume_usd":    10_000_000,
    "must_have_usdt_pair":     True,
    "market_cap_rank_max":     100,
    "exclude_name_keywords":   ["inu", "moon", "elon", "baby", "safe", "doge2", "shib2"],
    "must_have_real_project":  True,
}

# ── Pre-loaded watchlist ──────────────────────────────────────────────────────

_SEED_WATCHLIST: list[dict] = [
    # Long-term holds
    {
        "symbol": "HBAR", "name": "Hedera",
        "trade_type": "long_term", "is_narrative_leader": False,
        "notes": "Enterprise blockchain, very low unit price, govt partnerships",
    },
    {
        "symbol": "ALGO", "name": "Algorand",
        "trade_type": "long_term", "is_narrative_leader": False,
        "notes": "Carbon neutral, government partnerships, strong tech",
    },
    {
        "symbol": "VET", "name": "VeChain",
        "trade_type": "long_term", "is_narrative_leader": False,
        "notes": "Supply chain, real enterprise clients",
    },
    {
        "symbol": "LINK", "name": "Chainlink",
        "trade_type": "long_term", "is_narrative_leader": True,
        "notes": "DeFi infrastructure leader, fundamental to RWA narrative",
    },
    {
        "symbol": "XRP", "name": "XRP",
        "trade_type": "long_term", "is_narrative_leader": True,
        "notes": "Already held — monitor only. RWA + payments narrative leader",
    },
    {
        "symbol": "ADA", "name": "Cardano",
        "trade_type": "long_term", "is_narrative_leader": False,
        "notes": "Already held — monitor only",
    },
    # Short-term trading
    {
        "symbol": "SOL", "name": "Solana",
        "trade_type": "both", "is_narrative_leader": False,
        "notes": "High volatility, high liquidity, already held some",
    },
    {
        "symbol": "BNB", "name": "BNB",
        "trade_type": "short_term", "is_narrative_leader": False,
        "notes": "Binance native, liquid, moderate volatility",
    },
    {
        "symbol": "DOGE", "name": "Dogecoin",
        "trade_type": "short_term", "is_narrative_leader": False,
        "notes": "Pure trading coin, high liquidity, news-driven",
    },
]


# ── DB helpers ────────────────────────────────────────────────────────────────

def init_watchlist() -> None:
    """Seed watchlist into DB if it's empty. Safe to call on every startup."""
    from spot.stage2 import PINNED
    with get_session() as s:
        if s.query(Watchlist).count() == 0:
            for coin in _SEED_WATCHLIST:
                narrative = get_narrative_for_coin(coin["symbol"])
                s.add(Watchlist(
                    symbol=coin["symbol"],
                    name=coin["name"],
                    narrative=narrative,
                    is_narrative_leader=coin["is_narrative_leader"],
                    trade_type=coin["trade_type"],
                    added_date=datetime.utcnow(),
                    notes=coin.get("notes"),
                    active=True,
                    pinned=coin["symbol"] in PINNED,
                ))
            logger.info(f"Watchlist seeded with {len(_SEED_WATCHLIST)} coins")

        # Always enforce pinned+active for PINNED symbols (survives Monday refresh)
        patched = 0
        for sym in PINNED:
            row = s.query(Watchlist).filter(Watchlist.symbol == sym).first()
            if row and (not row.pinned or not row.active):
                row.pinned = True
                row.active = True
                patched += 1
        if patched:
            logger.info(f"Enforced pinned+active on {patched} protected symbol(s): {PINNED}")


def get_consistency_map() -> dict[str, dict]:
    """
    Returns {symbol: {appearances, total_runs, pct, mature}} for every coin
    that has ever appeared in a Stage-2 run. mature=True once ≥4 runs exist.
    """
    with get_session() as s:
        total_runs = s.query(WatchlistScreenHistory.run_date).distinct().count()
        if total_runs == 0:
            return {}
        from sqlalchemy import func
        rows = (
            s.query(WatchlistScreenHistory.symbol,
                    func.count(WatchlistScreenHistory.id).label("appearances"))
            .group_by(WatchlistScreenHistory.symbol)
            .all()
        )
        return {
            row.symbol: {
                "appearances": row.appearances,
                "total_runs":  total_runs,
                "pct":         round(row.appearances / total_runs * 100),
                "mature":      total_runs >= 4,
            }
            for row in rows
        }


def pin_coin(symbol: str) -> bool:
    """Pin a coin so it stays on the watchlist regardless of score. Returns True if found."""
    with get_session() as s:
        coin = s.query(Watchlist).filter(Watchlist.symbol == symbol.upper()).first()
        if not coin:
            return False
        coin.pinned = True
        coin.active = True
    return True


def unpin_coin(symbol: str) -> bool:
    """Remove user pin from a coin (BTC/ETH stay pinned regardless)."""
    from spot.stage2 import PINNED
    sym = symbol.upper()
    if sym in PINNED:
        return False  # anchors cannot be unpinned
    with get_session() as s:
        coin = s.query(Watchlist).filter(Watchlist.symbol == sym).first()
        if not coin:
            return False
        coin.pinned = False
    return True


def get_watchlist(active_only: bool = True) -> list[dict]:
    consistency = get_consistency_map()
    with get_session() as s:
        q = s.query(Watchlist)
        if active_only:
            q = q.filter(Watchlist.active == True)
        coins = q.all()

        # Coins with an open journal trade
        held_symbols = {
            row.symbol for row in
            s.query(SpotTrade.symbol).filter(SpotTrade.exit_price == None).all()
        }

        result = []
        for c in coins:
            cons = consistency.get(c.symbol, {})
            result.append({
                "symbol":               c.symbol,
                "name":                 c.name,
                "narrative":            c.narrative,
                "is_narrative_leader":  c.is_narrative_leader,
                "trade_type":           c.trade_type,
                "notes":                c.notes,
                "active":               c.active,
                "pinned":               bool(c.pinned),
                "held":                 c.symbol in held_symbols,
                "screen_score":         c.screen_score,
                "last_screened":        c.last_screened.isoformat() if c.last_screened else None,
                "consistency":          cons,
            })

        # Sort: pinned first, then by screen_score desc
        result.sort(key=lambda x: (not x["pinned"], -(x["screen_score"] or 0)))
        return result


def get_symbols() -> list[str]:
    """Return just the ticker symbols for active coins."""
    with get_session() as s:
        rows = s.query(Watchlist.symbol).filter(Watchlist.active == True).all()
        return [r.symbol for r in rows]


async def eject_unhealthy_coins() -> list[str]:
    """
    Daily health scan — immediately deactivates non-pinned coins that fail
    basic liquidity checks. Never adds mid-cycle, only removes.
    Criteria: < 15k trades/24h OR abs_change > 40% OR symbol no longer TRADING on Binance.
    """
    from spot.stage2 import PINNED, BINANCE_TICKER, MIN_TRADES_24H, MAX_ABS_CHANGE
    import httpx

    ejected: list[str] = []
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(BINANCE_TICKER)
        tickers = {t["symbol"]: t for t in r.json() if isinstance(t, dict)}
    except Exception as e:
        logger.warning(f"Ejection scan: failed to fetch tickers — {e}")
        return ejected

    with get_session() as s:
        active_non_pinned = (
            s.query(Watchlist)
             .filter(Watchlist.active == True, Watchlist.pinned == False)
             .all()
        )
        for coin in active_non_pinned:
            ticker = tickers.get(f"{coin.symbol}USDT")
            reason = None
            if not ticker:
                reason = "no longer trading as USDT pair"
            else:
                trades = int(ticker["count"])
                change = abs(float(ticker["priceChangePercent"]))
                if trades < 15_000:
                    reason = f"trades/day dropped to {trades:,} (floor: 15,000)"
                elif change > MAX_ABS_CHANGE:
                    reason = f"extreme move {change:.1f}% (ceiling: {MAX_ABS_CHANGE}%)"
            if reason:
                coin.active = False
                ejected.append(coin.symbol)
                logger.warning(f"[EJECTION] {coin.symbol} removed from watchlist — {reason}")

    return ejected


async def refresh_watchlist() -> list[str]:
    """
    Run Stage 1+2 pipeline and update the DB watchlist.
    Pinned coins (BTC, ETH) always remain active regardless of score.
    Returns the list of newly active symbols.
    """
    from spot.stage2 import run_stage2, PINNED

    ranked = await run_stage2()
    now    = datetime.now(timezone.utc)

    with get_session() as s:
        # Deactivate all non-pinned active coins
        (s.query(Watchlist)
           .filter(Watchlist.active == True, Watchlist.pinned == False)
           .update({"active": False}))

        for coin in ranked:
            sym    = coin["symbol"]
            pinned = coin["pinned"]
            existing = s.query(Watchlist).filter(Watchlist.symbol == sym).first()

            if existing:
                existing.active              = True
                existing.pinned              = pinned
                existing.screen_score        = coin["composite_score"]
                existing.last_screened       = now
                existing.narrative           = coin["narrative"]
                existing.is_narrative_leader = coin["is_narrative_leader"]
            else:
                s.add(Watchlist(
                    symbol               = sym,
                    name                 = coin["name"],
                    narrative            = coin["narrative"],
                    is_narrative_leader  = coin["is_narrative_leader"],
                    trade_type           = coin["trade_type"],
                    pinned               = pinned,
                    screen_score         = coin["composite_score"],
                    last_screened        = now,
                    added_date           = now,
                    active               = True,
                ))

    new_syms = [c["symbol"] for c in ranked]
    logger.info(f"Watchlist refreshed — {len(new_syms)} active coins: {new_syms}")
    return new_syms
