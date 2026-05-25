"""
Telegram command handlers.
All handlers are restricted to the authorised user ID from config.
"""
from __future__ import annotations

import functools
from datetime import date

from loguru import logger
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from config import get_config, OperatingMode, Availability
from bot.formatters import (
    format_status,
    format_p2p_snapshot,
    format_daily_summary,
    format_help,
)
from data.database import get_session
from data.models import SystemEvent, P2PTrade
from p2p.market_monitor import fetch_market_data, get_recent_snapshots, compute_average_spread
from p2p.trader_scorer import TraderProfile, score_trader, color_emoji

# In-memory state (persisted to DB on change)
_state: dict = {
    "mode": None,
    "availability": None,
}


def _get_state() -> dict:
    if _state["mode"] is None:
        cfg = get_config()
        _state["mode"] = cfg.operating_mode
        _state["availability"] = cfg.availability
    return _state


def restricted(func):
    """Decorator — silently drop messages from unauthorised users."""
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        if user is None or user.id != get_config().telegram_user_id:
            logger.warning(f"Unauthorised access attempt from user {user.id if user else 'unknown'}")
            return
        return await func(update, context)
    return wrapper


async def _reply(update: Update, text: str) -> None:
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)


def _log_event(event_type: str, description: str) -> None:
    try:
        state = _get_state()
        with get_session() as s:
            s.add(SystemEvent(
                event_type=event_type,
                description=description,
                mode=state["mode"].value if state["mode"] else None,
            ))
    except Exception as e:
        logger.warning(f"Could not log system event: {e}")


# ── handlers ─────────────────────────────────────────────────────────────────

@restricted
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "👋 Trading platform online. Type /help for commands.")


@restricted
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, format_help())


@restricted
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = _get_state()
    text = format_status(state["mode"], state["availability"])
    await _reply(update, text)


@restricted
async def cmd_mode(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _reply(update, "Usage: /mode manual|semi|full")
        return

    requested = context.args[0].lower()
    try:
        new_mode = OperatingMode(requested)
    except ValueError:
        await _reply(update, f"❌ Unknown mode: `{requested}`. Use manual, semi, or full.")
        return

    state = _get_state()
    old_mode = state["mode"]
    state["mode"] = new_mode

    _log_event("mode_change", f"Mode changed from {old_mode.value} to {new_mode.value}")
    logger.info(f"Operating mode changed to {new_mode.value}")
    await _reply(update, f"✅ Mode switched to *{new_mode.value.upper()}*.")


@restricted
async def cmd_online(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _get_state()["availability"] = Availability.ONLINE
    _log_event("availability_change", "Set to ONLINE")
    await _reply(update, "🟢 Availability set to *ONLINE*.")


@restricted
async def cmd_slow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _get_state()["availability"] = Availability.SLOW
    _log_event("availability_change", "Set to SLOW")
    await _reply(update, "🟡 Availability set to *SLOW*.")


@restricted
async def cmd_pause(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _get_state()["availability"] = Availability.OFFLINE
    _log_event("availability_change", "Set to OFFLINE")
    await _reply(update, "🔴 Availability set to *OFFLINE*. Ads will be paused.")


@restricted
async def cmd_p2p(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(update, "⏳ Fetching P2P market data...")
    try:
        data = await fetch_market_data()
        snaps = get_recent_snapshots(limit=12)  # ~1h at 5-min intervals
        avg_1h = compute_average_spread(snaps)
        text = format_p2p_snapshot(data, avg_spread_1h=avg_1h)
        await _reply(update, text)
    except Exception as e:
        logger.error(f"P2P fetch error: {e}")
        await _reply(update, f"❌ Could not fetch P2P data: {e}")


@restricted
async def cmd_score(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await _reply(update, "Usage: /score <trader_username>")
        return

    username = context.args[0]
    # We can only score with data we have — ask user to provide stats
    await _reply(
        update,
        f"ℹ️ To score trader *{username}*, I need their Binance profile data.\n"
        "For now, check their profile on Binance and use /score manually.\n"
        "Full auto-scoring from incoming orders is coming in Phase 2."
    )


@restricted
async def cmd_trades(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    period = (context.args[0] if context.args else "today").lower()
    from datetime import datetime, timedelta

    try:
        with get_session() as s:
            query = s.query(P2PTrade)
            if period == "today":
                start = datetime.utcnow().replace(hour=0, minute=0, second=0)
                query = query.filter(P2PTrade.timestamp >= start)
            elif period == "week":
                start = datetime.utcnow() - timedelta(days=7)
                query = query.filter(P2PTrade.timestamp >= start)

            trades = query.order_by(P2PTrade.timestamp.desc()).limit(20).all()
            count = len(trades)
            volume = sum(t.amount_usdt for t in trades)
            profit = sum(t.profit_sdg or 0 for t in trades)

        text = (
            f"📋 *Trades — {period.upper()}*\n\n"
            f"Count:  {count}\n"
            f"Volume: {volume:.1f} USDT\n"
            f"Profit: {profit:.1f} SDG\n"
        )
        await _reply(update, text)
    except Exception as e:
        await _reply(update, f"❌ Error fetching trades: {e}")


@restricted
async def cmd_risk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _reply(
        update,
        "🛡️ *Risk Limits (Phase 1 — Manual Mode)*\n\n"
        "• Max single trade: configurable\n"
        "• Completion rate target: > 97%\n"
        "• Release time target: < 3 min\n"
        "• Crypto release: *manual only*\n\n"
        "_Full risk manager activates in Phase 4 (Spot module)._"
    )


def get_state() -> dict:
    """Expose state for testing."""
    return _get_state()


def reset_state() -> None:
    """Reset in-memory state — for tests only."""
    _state["mode"] = None
    _state["availability"] = None
