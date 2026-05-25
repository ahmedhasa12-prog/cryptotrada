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

        bus = get_bus()
        for msg in check_alerts(data):
            level = AlertLevel.WARNING if "tight" in msg.lower() else AlertLevel.CRITICAL
            await bus.publish_text(msg, level=level, source="market_monitor")

        for msg in check_premium_buyers(data.sell_offers):
            await bus.publish_text(msg, level=AlertLevel.INFO, source="market_monitor")

        for msg in check_competitor_changes(data.buy_offers, data.sell_offers, last_snap):
            await bus.publish_text(msg, level=AlertLevel.INFO, source="competitor_tracker")

        for msg in await run_adjuster(data):
            await bus.publish_text(msg, level=AlertLevel.INFO, source="rate_adjuster")

        # SDG rate movement alerts (6h window = 72 × 5-min slots)
        snaps = get_recent_snapshots(limit=72)
        for msg in check_rate_movement_alerts(snaps):
            await bus.publish_text(msg, level=AlertLevel.WARNING, source="sdg_monitor")

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


def main() -> None:
    cfg = get_config()
    _setup_logging()
    logger.info("Starting Binance Trading Intelligence Platform — Phase 1")

    init_db(cfg.db_path)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(_poll_market, "interval", minutes=5, id="market_poll")
    scheduler.add_job(_daily_summary, "cron", hour=23, minute=55, id="daily_summary")

    @asynccontextmanager
    async def lifespan(_):
        scheduler.start()
        logger.info("Scheduler started — market polling every 5 minutes")
        logger.info("Dashboard available at http://localhost:8000")
        yield
        scheduler.shutdown(wait=False)

    app = create_app(lifespan=lifespan)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")


if __name__ == "__main__":
    main()
