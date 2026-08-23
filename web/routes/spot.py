from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException

from spot.data_fetcher import candle_counts, load_dataframe, refresh_interval, backfill_status, ensure_hourly_backfill
from spot.macro import get_latest_macro, refresh_macro
from spot.narratives import get_narratives
from spot.scorer import get_coin_detail, get_scores, score_all_coins, scores_are_stale
from spot.positions import get_open_positions
from spot.watchlist import get_watchlist, refresh_watchlist, pin_coin, unpin_coin

router = APIRouter(prefix="/api/spot")


# ── Macro ─────────────────────────────────────────────────────────────────────

@router.get("/macro")
async def macro_endpoint():
    data = get_latest_macro()
    if data is None:
        await refresh_macro()
        data = get_latest_macro()
    return data or {"error": "no_data"}


@router.post("/macro/refresh")
async def macro_refresh():
    await refresh_macro()
    return get_latest_macro() or {"error": "no_data"}


# ── Watchlist & narratives ────────────────────────────────────────────────────

@router.get("/narratives")
def narratives_endpoint():
    return get_narratives()


@router.get("/watchlist")
def watchlist_endpoint():
    return get_watchlist()


@router.post("/watchlist/refresh")
async def watchlist_refresh():
    """Trigger an immediate Stage 1+2 watchlist refresh (normally runs weekly)."""
    new_symbols = await refresh_watchlist()
    return {"status": "ok", "coins": new_symbols, "count": len(new_symbols)}


@router.post("/watchlist/{symbol}/pin")
def watchlist_pin(symbol: str):
    if not pin_coin(symbol):
        raise HTTPException(status_code=404, detail=f"{symbol} not in watchlist")
    return {"status": "pinned", "symbol": symbol.upper()}


@router.post("/watchlist/{symbol}/unpin")
def watchlist_unpin(symbol: str):
    if not unpin_coin(symbol):
        raise HTTPException(status_code=400, detail=f"{symbol} cannot be unpinned (anchor or not found)")
    return {"status": "unpinned", "symbol": symbol.upper()}


# ── Hotness scanner ───────────────────────────────────────────────────────────

@router.get("/hotness")
def hotness_endpoint():
    """Ranked hotness scores for all watchlist coins."""
    scores = get_scores()
    macro  = get_latest_macro() or {}
    return {
        "coins": scores,
        "macro_summary": {
            "btc_dominance":  macro.get("btc_dominance"),
            "fear_greed":     macro.get("fear_greed_value"),
            "market_season":  macro.get("market_season"),
            "season_label":   macro.get("season_label"),
        },
        "candle_counts": candle_counts(),
    }


@router.post("/hotness/recalculate")
def hotness_recalculate():
    """Force a fresh score calculation (uses existing DB candles)."""
    scores = get_scores(force=True)
    return {"recalculated": len(scores), "coins": scores}


# ── Coin detail ───────────────────────────────────────────────────────────────

@router.get("/coin/{symbol}")
def coin_detail(symbol: str):
    detail = get_coin_detail(symbol.upper())
    if not detail:
        raise HTTPException(status_code=404, detail=f"{symbol} not found or not scored yet")
    return detail


# ── Data status ───────────────────────────────────────────────────────────────

@router.get("/data/status")
def data_status():
    """How many candles we have per coin/interval."""
    return candle_counts()


@router.post("/data/refresh/{interval}")
async def data_refresh(interval: str):
    if interval not in ("1d", "4h", "1h", "15m"):
        raise HTTPException(status_code=400, detail="interval must be 1d|4h|1h|15m")
    count = await refresh_interval(interval)
    return {"interval": interval, "new_candles": count}


# ── Coin candles ─────────────────────────────────────────────────────────────

@router.get("/coin/{symbol}/candles")
def coin_candles(symbol: str, interval: str = "1h", limit: int = 200):
    """OHLCV candles for lightweight-charts (Unix timestamps in seconds)."""
    if interval not in ("15m", "1h", "4h", "1d", "1w"):
        raise HTTPException(status_code=400, detail="interval must be 15m|1h|4h|1d|1w")
    df = load_dataframe(symbol.upper(), interval, limit)
    if df.empty:
        return {"candles": []}
    candles = []
    for _, row in df.iterrows():
        ts = row["timestamp"]
        t = int(ts.timestamp()) if hasattr(ts, "timestamp") else int(ts)
        candles.append({
            "time":  t,
            "open":  float(row["open"]),
            "high":  float(row["high"]),
            "low":   float(row["low"]),
            "close": float(row["close"]),
        })
    return {"candles": candles, "interval": interval, "symbol": symbol.upper()}


# ── Open positions (for live P&L display) ────────────────────────────────────

@router.get("/positions")
def positions_endpoint():
    """Open journal trades — used by the frontend for live P&L calculation."""
    return get_open_positions()


# ── Live prices ───────────────────────────────────────────────────────────────

@router.get("/prices")
def prices_endpoint():
    """Real-time prices from WebSocket miniTicker stream."""
    from spot.streamer import get_prices, is_connected, last_tick_age_seconds
    return {"prices": get_prices(), "connected": is_connected(),
            "last_tick_age_seconds": last_tick_age_seconds()}


# ── Spot timing analysis ──────────────────────────────────────────────────────

@router.get("/timing/{symbol}/status")
def timing_status(symbol: str):
    """How many 1h candles are stored for this coin and whether backfill is running."""
    return backfill_status(symbol.upper())


@router.post("/timing/{symbol}/backfill")
async def timing_backfill(symbol: str):
    """Trigger a background 180-day 1h candle backfill for this coin."""
    sym = symbol.upper()
    status = backfill_status(sym)
    if status["backfilling"]:
        return {"status": "already_running", **status}
    asyncio.create_task(ensure_hourly_backfill(sym, target_days=1460))
    return {"status": "started", **status}


@router.get("/timing/{symbol}/patterns")
def timing_patterns(symbol: str):
    """Hourly + weekday + session timing patterns for a coin."""
    from intelligence.spot_timing import timing_summary
    sym = symbol.upper()
    status = backfill_status(sym)
    if not status["ready"]:
        return {"symbol": sym, "ready": False, "status": status}
    return {"ready": True, "status": status, **timing_summary(sym)}


@router.get("/bot/status")
def bot_status():
    from spot.auto_trader import get_status
    return get_status()

@router.post("/bot/toggle")
def bot_toggle():
    from spot.auto_trader import is_enabled, set_enabled
    set_enabled(not is_enabled())
    from spot.auto_trader import get_status
    return get_status()

@router.post("/bot/seed-test")
def bot_seed_test():
    """Open $1000 paper position on every watchlist coin at current price."""
    from spot.auto_trader import seed_all_coins
    from spot.streamer import get_prices
    coins = get_watchlist(active_only=True)
    result = seed_all_coins(coins, get_prices())
    return result

@router.get("/bot/leaderboard")
def bot_leaderboard():
    """Per-coin P&L summary across all bot paper trades."""
    from spot.auto_trader import get_leaderboard
    from spot.streamer import get_prices
    return {"rows": get_leaderboard(get_prices())}

@router.get("/bot/history")
def bot_history():
    """All completed bot paper trade cycles, newest first."""
    from spot.auto_trader import get_trade_history
    return {"trades": get_trade_history()}

@router.get("/bot/reviews")
def bot_reviews():
    """All automated post-mortem reviews, newest first."""
    from spot.reviewer import get_reviews, get_summary
    return {"reviews": get_reviews(), "summary": get_summary()}


@router.post("/bot/reviews/run")
def bot_reviews_run():
    """Manually trigger the post-mortem reviewer (normally runs every 30 min)."""
    from spot.reviewer import run_reviews
    written = run_reviews()
    return {"written": written}


@router.get("/bot/advisor")
def bot_advisor():
    """
    Weekly parameter advisory — rules-based recommendations derived from all
    accumulated TradeReview data. Activates once ≥10 trades per category exist.
    """
    from spot.param_advisor import generate_advisory
    return generate_advisory()


@router.post("/bot/advisor/run")
def bot_advisor_run():
    """Manually trigger the advisor and persist result as a SystemEvent."""
    from spot.param_advisor import run_and_store
    return run_and_store()


@router.get("/atmosphere")
def atmosphere_endpoint():
    """Ecosystem-level atmosphere score (0–100) across 10 indicators."""
    from spot.atmosphere import get_atmosphere
    from spot.auto_trader import get_atmosphere_settings
    atm = get_atmosphere()
    atm["settings"] = get_atmosphere_settings()
    return atm


@router.post("/atmosphere/refresh")
def atmosphere_refresh():
    """Force-recompute the atmosphere score (bypasses 15-min cache)."""
    from spot.atmosphere import compute_atmosphere, _cache as atm_cache
    import spot.atmosphere as _atm_mod
    result = compute_atmosphere()
    _atm_mod._cache = result
    from spot.auto_trader import get_atmosphere_settings
    result["settings"] = get_atmosphere_settings()
    return result


@router.post("/atmosphere/gate")
def atmosphere_gate_toggle():
    """Toggle atmosphere gate on/off (blocks entries when score < 40)."""
    from spot.auto_trader import toggle_atmosphere_gate, get_atmosphere_settings
    enabled = toggle_atmosphere_gate()
    return {"gate_enabled": enabled, "settings": get_atmosphere_settings()}


@router.post("/atmosphere/boost")
def atmosphere_boost_toggle():
    """Toggle atmosphere boost on/off (scales position size by score)."""
    from spot.auto_trader import toggle_atmosphere_boost, get_atmosphere_settings
    enabled = toggle_atmosphere_boost()
    return {"boost_enabled": enabled, "settings": get_atmosphere_settings()}


@router.get("/signals")
def get_signals():
    """Timing-based trade signals for all held positions and watchlist coins."""
    from datetime import datetime
    from spot.signal_bot import generate_signals, timing_score
    from spot.streamer import get_prices

    positions = get_open_positions()
    watchlist = get_watchlist(active_only=True)

    try:
        live_prices = get_prices()
    except Exception:
        live_prices = {}

    signals = generate_signals(positions, watchlist, live_prices)

    all_syms = list({p['symbol'] for p in positions} | {w['symbol'] for w in watchlist})
    scores   = {sym: timing_score(sym) for sym in all_syms}

    return {
        'signals':      signals,
        'scores':       scores,
        'generated_at': datetime.utcnow().isoformat(),
    }

