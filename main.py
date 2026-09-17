"""
Entry point — initialises the database, starts the scheduler, and serves
the FastAPI web dashboard.

Usage:
    python main.py          # production (serves built Vue SPA + API)

Development (two terminals):
    python main.py          # terminal 1 — FastAPI on :8000
    cd frontend && npm run dev   # terminal 2 — Vite on :5173 (hot reload)
"""
from __future__ import annotations

import sys
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from loguru import logger

from config import get_config
from data.database import init_db
from p2p.market_monitor import fetch_market_data, save_snapshot, check_alerts, check_premium_buyers, get_recent_snapshots
from p2p.p2p_logger import get_daily_stats
from intelligence.sdg_monitor import check_rate_movement_alerts
from intelligence.competitor_tracker import check_competitor_changes
from p2p.rate_adjuster import run_adjuster
from spot.data_fetcher import refresh_interval, startup_fetch, retry_failed_fetches
from spot.macro import refresh_macro
from spot.positions import get_open_positions
from spot.scorer import get_scores
from spot.spot_alerts import check_position_alerts, check_rating_transitions
from spot.streamer import get_prices, start_price_stream, refresh_subscription
from spot.watchlist import init_watchlist, refresh_watchlist, eject_unhealthy_coins
from spot.auto_trader import fast_sl_cycle
from spot.reviewer import run_reviews as run_trade_reviews
from spot.param_advisor import run_and_store as run_param_advisory
from spot.xrp_swing import (evaluate_setup as xrp_swing_evaluate, generate_weekly_review as xrp_weekly_review,
                            fast_sl_check as _xrp_fast_sl_cycle)
from spot.trading_modes import (get_trading_mode, TradingMode,
                                get_agent_registry, start_all_agents, stop_all_agents)
from web.alerts import get_bus, AlertLevel
from web.state import get_state
from web.app import create_app


def _setup_logging() -> None:
    cfg = get_config()
    Path("logs").mkdir(exist_ok=True)
    logger.remove()
    logger.add(sys.stderr, level=cfg.log_level, colorize=True,
               format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}")
    logger.add("logs/platform.log", rotation="1 day", retention="30 days",
               level="DEBUG", encoding="utf-8")


async def _poll_market() -> None:
    """Fetch P2P market data every 5 min, store snapshot, push alerts via SSE."""
    try:
        data = await fetch_market_data()

        # Fetch last snapshot BEFORE saving so competitor tracker has a true previous poll
        last_snaps = get_recent_snapshots(limit=1)
        last_snap = last_snaps[0] if last_snaps else None

        save_snapshot(data, our_rate=None)  # Phase 2: pull from active ad

        # Spread and SDG-trend conditions are now shown as inline badges in
        # the P2P card — call the checks so their logic runs but don't push
        # them to the global bus (they fired every 5 min and were too noisy).
        check_alerts(data)
        check_premium_buyers(data.sell_offers)

        bus = get_bus()
        # Competitor price changes: meaningful and infrequent → keep in bus
        for msg in check_competitor_changes(data.buy_offers, data.sell_offers, last_snap):
            await bus.publish_text(msg, level=AlertLevel.INFO, source="competitor_tracker")

        for msg in await run_adjuster(data):
            await bus.publish_text(msg, level=AlertLevel.INFO, source="rate_adjuster")

        # SDG rate movement: shown as inline badge — skip global bus
        snaps = get_recent_snapshots(limit=72)
        check_rate_movement_alerts(snaps)

        logger.debug(f"Market poll done — spread: {data.spread}")
    except Exception as e:
        logger.error(f"Market poll error: {e}")


async def _daily_summary() -> None:
    """Push daily summary as an info alert at 23:55 UTC."""
    try:
        stats = get_daily_stats()
        state = get_state()
        msg = (
            f"Daily summary — {stats['date']} | "
            f"{stats['count']} trades | "
            f"{stats['volume_usdt']:.1f} USDT | "
            f"{stats['profit_sdg']:.1f} SDG profit | "
            f"Mode: {state.mode.value}"
        )
        await get_bus().publish_text(msg, level=AlertLevel.INFO, source="daily_summary")
    except Exception as e:
        logger.error(f"Daily summary error: {e}")


async def _hotness_and_alerts() -> None:
    """Recalculate hotness scores then emit rating-transition alerts."""
    import asyncio
    try:
        scores = await asyncio.get_event_loop().run_in_executor(None, lambda: get_scores(force=True))
        alerts = check_rating_transitions(scores)
        if alerts:
            bus = get_bus()
            for level_str, msg in alerts:
                lv = AlertLevel.WARNING if level_str == "warning" else AlertLevel.INFO
                await bus.publish_text(msg, level=lv, source="spot_alerts")
    except Exception as e:
        logger.error(f"Hotness/alert job error: {e}")


async def _fast_sl_check() -> None:
    """
    Runs every 30 seconds — enforces hard SL and trailing stop immediately.
    Keeps losses tight without waiting for the 5-minute bot cycle.
    Also updates trailing peaks as prices rise between 5-min ticks.

    Stands down once AutoTrendAgent is running: its own fast cycle calls this
    same underlying function, and running both would apply stop-loss/trailing
    logic twice per tick. This is the standalone, pre-agent-framework path —
    it owns the cycle only while the agent is not.
    """
    import asyncio
    from spot.trading_modes import AgentType, is_agent_running
    if is_agent_running(AgentType.AUTO_TREND):
        return
    try:
        positions = get_open_positions()
        if not positions:
            return
        prices = get_prices()
        # Run in thread — fast_sl_cycle does DB writes that must not stall the event loop
        closed = await asyncio.get_event_loop().run_in_executor(
            None, lambda: fast_sl_cycle(positions, prices)
        )
        if closed:
            bus = get_bus()
            for sym, reason, pnl in closed:
                emoji = "🟢" if pnl > 0 else "🔴"
                msg   = f"{emoji} [FAST] {sym} closed — {reason} · P&L {pnl:+.2f}%"
                await bus.publish_text(msg, level=AlertLevel.CRITICAL, source="fast_guard")
    except Exception as e:
        logger.error(f"Fast SL check error: {e}")


async def _check_position_alerts() -> None:
    """Check open positions against live prices for SL / target breaches, then run unified trading cycle."""
    import asyncio
    try:
        positions = get_open_positions()
        prices    = get_prices()
        if positions:
            alerts = check_position_alerts(positions, prices)
            if alerts:
                bus = get_bus()
                for level_str, msg in alerts:
                    lv = AlertLevel.CRITICAL if level_str == "critical" else AlertLevel.INFO
                    await bus.publish_text(msg, level=lv, source="position_monitor")
        
    except Exception as e:
        logger.error(f"Position/trading cycle error: {e}")


async def _xrp_fast_sl_check() -> None:
    """
    Runs every 30 seconds — the standalone path for XRP swing's stop-loss and
    trailing enforcement, scheduled independently of the agent framework.

    Stands down once XRPSwingAgent is running, for the same reason as
    _fast_sl_check above: the agent's own fast cycle calls this identical
    underlying function, and running both would apply stop-loss/trailing
    logic twice per tick.
    """
    from spot.trading_modes import AgentType, is_agent_running
    if is_agent_running(AgentType.XRP_SWING):
        return
    try:
        _xrp_fast_sl_cycle()
    except Exception as e:
        logger.error(f"XRP fast SL check error: {e}")


def _run_trade_reviews_job() -> None:
    """Runs every 30 min — reviews closed bot trades older than 6h."""
    try:
        run_trade_reviews()
    except Exception as e:
        logger.error(f"Trade review job error: {e}")


async def _refresh_watchlist_and_resubscribe() -> None:
    """Bi-weekly watchlist refresh (odd ISO weeks, Monday 03:00 UTC) — then immediately
    reconnect the price stream so newly added coins are streamed without waiting."""
    await refresh_watchlist()
    refresh_subscription()


async def _daily_ejection_job() -> None:
    """
    Daily at 06:00 UTC — ejects non-pinned coins that fail liquidity health checks
    (< 15k trades/day, extreme move > 40%, or delisted). Never adds, only removes.
    Reconnects price stream if any coins were ejected.
    """
    try:
        ejected = await eject_unhealthy_coins()
        if ejected:
            refresh_subscription()
            bus = get_bus()
            await bus.publish_text(
                f"[WATCHLIST] Daily ejection scan removed {len(ejected)} coin(s): {', '.join(ejected)}",
                level=AlertLevel.WARNING,
                source="watchlist_ejection",
            )
            logger.info(f"Daily ejection: removed {ejected}")
        else:
            logger.debug("Daily ejection scan: all coins healthy")
    except Exception as e:
        logger.error(f"Daily ejection job error: {e}")


async def _param_advisory_job() -> None:
    """
    Runs every Monday at 08:00 UTC — applies rule engine to all accumulated
    TradeReviews and pushes recommendations to the alert bus + SystemEvent log.
    Requires ≥10 reviews per category before generating actionable advice.
    """
    try:
        advisory = run_param_advisory()
        recs = [r for r in advisory.get("recommendations", []) if r["priority"] in ("high", "medium")]
        if recs:
            bus = get_bus()
            total = advisory["total_reviews"]
            await bus.publish_text(
                f"[ADVISOR] Weekly review complete — {total} trades analysed, "
                f"{len(recs)} recommendation(s). Check /api/spot/bot/advisor for details.",
                level=AlertLevel.INFO,
                source="param_advisor",
            )
    except Exception as e:
        logger.error(f"Param advisory job error: {e}")


def main() -> None:
    cfg = get_config()
    _setup_logging()
    logger.info("Starting Binance Trading Intelligence Platform — Phase 4b: Agent Architecture")

    init_db(cfg.db_path)
    init_watchlist()

    # misfire_grace_time=None on data-critical interval jobs means: run immediately on wake
    # regardless of how long the system was offline (sleep/restart). Without this, APScheduler
    # silently drops any job whose scheduled time is > 1s in the past (the default grace period),
    # causing feeds like macro + candles to go stale after every system sleep cycle.
    _WAKE_GRACE = None   # run the missed fire immediately, no matter how late

    scheduler = AsyncIOScheduler()
    scheduler.add_job(_poll_market,    "interval", minutes=5,  id="market_poll",   misfire_grace_time=_WAKE_GRACE, coalesce=True)
    scheduler.add_job(_daily_summary,  "cron",     hour=23, minute=55, id="daily_summary")
    scheduler.add_job(refresh_macro,   "interval", minutes=30, id="macro_refresh", misfire_grace_time=_WAKE_GRACE, coalesce=True)
    # Candle refresh jobs (async functions run natively in AsyncIOScheduler)
    scheduler.add_job(refresh_interval, "interval", minutes=15, args=["15m"], id="candles_15m", misfire_grace_time=_WAKE_GRACE, coalesce=True)
    scheduler.add_job(refresh_interval, "interval", hours=1,    args=["1h"],  id="candles_1h",  misfire_grace_time=_WAKE_GRACE, coalesce=True)
    scheduler.add_job(refresh_interval, "interval", hours=4,    args=["4h"],  id="candles_4h",  misfire_grace_time=_WAKE_GRACE, coalesce=True)
    scheduler.add_job(refresh_interval, "cron", hour=0, minute=10, args=["1d"], id="candles_1d")
    scheduler.add_job(refresh_interval, "cron", day_of_week="mon", hour=1, minute=0, args=["1w"], id="candles_1w")
    # Recalculate hotness scores every 4 hours + emit rating-transition alerts
    scheduler.add_job(_hotness_and_alerts, "interval", hours=4, id="hotness_score", misfire_grace_time=_WAKE_GRACE, coalesce=True)
    # Fast SL guard — enforces hard stop and trailing stop every 30 seconds (unified)
    scheduler.add_job(_fast_sl_check, "interval", seconds=30, id="fast_sl_guard")
    # Unified trading cycle — check positions, entries, exits every 5 minutes
    scheduler.add_job(_check_position_alerts, "interval", minutes=5, id="position_check", misfire_grace_time=_WAKE_GRACE, coalesce=True)
    # Automated post-mortem: review closed trades 6h+ after close, every 30 min
    scheduler.add_job(_run_trade_reviews_job, "interval", minutes=30, id="trade_review")
    # Bi-weekly watchlist refresh — odd ISO weeks, Monday 03:00 UTC (after weekly candles at 01:00)
    scheduler.add_job(_refresh_watchlist_and_resubscribe, "cron", week="1-53/2", day_of_week="mon", hour=3, minute=0, id="watchlist_refresh")
    # Daily ejection scan — 06:00 UTC, removes coins that fail liquidity health checks
    scheduler.add_job(_daily_ejection_job, "cron", hour=6, minute=0, id="watchlist_ejection")
    # Weekly parameter advisor — every Monday at 08:00 UTC (after watchlist + candle refresh)
    scheduler.add_job(_param_advisory_job, "cron", day_of_week="mon", hour=8, minute=0, id="param_advisor")
    # AI advisor (Opus/OpenRouter) — disabled from auto-schedule; trigger manually via API when needed
    # XRP Swing — evaluate 3-layer conditions every 15 min (cheap: cached candle data + live price)
    scheduler.add_job(xrp_swing_evaluate, "interval", minutes=15, kwargs={"store": True}, id="xrp_swing_eval", misfire_grace_time=_WAKE_GRACE, coalesce=True)
    # XRP Swing — Sunday 07:00 UTC weekly review stored as system event
    scheduler.add_job(xrp_weekly_review, "cron", day_of_week="sun", hour=7, minute=0, id="xrp_swing_weekly")
    # Auto-retry for failed fetches (rate limit / overload resilience) - runs every 30s
    async def _auto_retry_fetches():
        retries = await retry_failed_fetches()
        if retries > 0:
            logger.info(f"Auto-retry completed: {retries} fetches recovered")
    scheduler.add_job(_auto_retry_fetches, "interval", seconds=30, id="auto_retry_fetches", coalesce=True)
    # XRP Swing — 30s fast SL guard: enforces hard stop and trailing stop immediately
    scheduler.add_job(_xrp_fast_sl_check, "interval", seconds=30, id="xrp_fast_sl")

    @asynccontextmanager
    async def lifespan(_):
        scheduler.start()
        logger.info("Scheduler started — market polling every 5 minutes")
        logger.info("Dashboard available at http://localhost:8000")
        # Kick off background tasks: macro data + historical candle fetch + price stream
        import asyncio as _asyncio
        _asyncio.create_task(refresh_macro())
        _asyncio.create_task(startup_fetch())
        start_price_stream()
        
        # Initialize and start enabled agents
        def get_context():
            from spot.positions import get_open_positions
            from spot.watchlist import get_watchlist
            from spot.streamer import get_prices
            from spot.macro import get_latest_macro
            from spot.atmosphere import get_atmosphere
            return {
                "positions": get_open_positions(),
                "watchlist": get_watchlist(active_only=True),
                "live_prices": get_prices(),
                "macro_data": get_latest_macro(),
                "atmosphere_data": get_atmosphere(),
            }
        
        try:
            await start_all_agents(get_context)
            logger.info("Agent system initialized and enabled agents started")
        except Exception as e:
            logger.error(f"Failed to start agents: {e}")
        
        yield
        
        # Stop all agents on shutdown
        try:
            await stop_all_agents()
            logger.info("All agents stopped")
        except Exception as e:
            logger.error(f"Error stopping agents: {e}")
        
        scheduler.shutdown(wait=False)

    # Export the FastAPI app for ASGI servers (Railway, uvicorn)
    app = create_app(lifespan=lifespan)
    port = int(os.environ.get("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="warning")


if __name__ == "__main__":
    main()
