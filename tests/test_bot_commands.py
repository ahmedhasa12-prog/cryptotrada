"""
Tests for bot/commands.py and bot/formatters.py.
All Telegram Update/context objects are mocked.
No real bot token is used.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import config as cfg
import data.database as db
from bot.commands import (
    cmd_start,
    cmd_help,
    cmd_status,
    cmd_mode,
    cmd_online,
    cmd_slow,
    cmd_pause,
    cmd_trades,
    cmd_risk,
    get_state,
    reset_state,
)
from bot.formatters import (
    format_status,
    format_p2p_snapshot,
    format_daily_summary,
    format_help,
    format_trade_alert,
)
from config import OperatingMode, Availability
from data.models import P2PTrade
from p2p.market_monitor import MarketData, Offer
from p2p.trader_scorer import ScoreResult, RiskColor


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_update(user_id: int = 123456789, text: str = "/status", args: list = None):
    update = MagicMock()
    update.effective_user.id = user_id
    update.message.reply_text = AsyncMock()
    update.message.text = text
    return update


def _make_context(args: list = None):
    ctx = MagicMock()
    ctx.args = args or []
    return ctx


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test_token")
    monkeypatch.setenv("TELEGRAM_USER_ID", "123456789")
    cfg.reset_config()
    db.init_db(":memory:")
    reset_state()
    yield
    db.reset_db()
    cfg.reset_config()
    reset_state()


# ── formatter tests ───────────────────────────────────────────────────────────

def test_format_status_manual_online():
    text = format_status(OperatingMode.MANUAL, Availability.ONLINE)
    assert "MANUAL" in text
    assert "ONLINE" in text


def test_format_status_full_offline():
    text = format_status(OperatingMode.FULL, Availability.OFFLINE)
    assert "FULL" in text
    assert "OFFLINE" in text


def test_format_p2p_snapshot_with_data():
    data = MarketData(
        timestamp=datetime.utcnow(),
        buy_offers=[Offer("m1", 610.0, 100, 5000, 200, 100, 99.0)],
        sell_offers=[Offer("m2", 590.0, 100, 5000, 200, 100, 99.0)],
        buy_best_rate=610.0,
        sell_best_rate=590.0,
        spread=20.0,
    )
    text = format_p2p_snapshot(data, avg_spread_1h=18.5)
    assert "610.00" in text
    assert "590.00" in text
    assert "20.00" in text
    assert "18.50" in text


def test_format_p2p_snapshot_no_data():
    data = MarketData(datetime.utcnow(), [], [], None, None, None)
    text = format_p2p_snapshot(data)
    assert "—" in text


def test_format_daily_summary():
    text = format_daily_summary(
        date="2026-05-23",
        p2p_trades=5,
        p2p_volume_usdt=250.0,
        p2p_profit_sdg=3000.0,
        avg_release_min=2.5,
        mode=OperatingMode.MANUAL,
    )
    assert "2026-05-23" in text
    assert "5 completed" in text
    assert "250.0 USDT" in text
    assert "3000.0 SDG" in text
    assert "2.5 min" in text


def test_format_help_contains_commands():
    text = format_help()
    for cmd in ["/status", "/p2p", "/mode", "/trades", "/help"]:
        assert cmd in text


def test_format_trade_alert():
    data = MarketData(
        timestamp=datetime.utcnow(),
        buy_offers=[Offer("m1", 610.0, 100, 5000, 200, 100, 99.0)],
        sell_offers=[Offer("m2", 590.0, 100, 5000, 200, 100, 99.0)],
        buy_best_rate=610.0,
        sell_best_rate=590.0,
        spread=20.0,
    )
    score = ScoreResult(85, RiskColor.GREEN, "ACCEPT", ["High trade count."], None)
    text = format_trade_alert(
        order_id="ORD123",
        profile_data={
            "username": "trader_x",
            "amount_usdt": 100,
            "total_sdg": 61000,
            "total_trades": 600,
            "completion_rate": 99.0,
            "account_age_days": 365,
            "payment_method": "Bank of Khartoum",
        },
        score_result=score,
        market=data,
        our_rate=600.0,
        avg_spread_24h=18.0,
    )
    assert "trader_x" in text
    assert "85/100" in text
    assert "ACCEPT" in text
    assert "ORD123" in text


# ── command handler tests (mocked Update) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_cmd_start_authorised():
    update = _make_update()
    ctx = _make_context()
    await cmd_start(update, ctx)
    update.message.reply_text.assert_called_once()
    call_text = update.message.reply_text.call_args[0][0]
    assert "online" in call_text.lower()


@pytest.mark.asyncio
async def test_cmd_start_unauthorised_ignored():
    update = _make_update(user_id=999999)
    ctx = _make_context()
    await cmd_start(update, ctx)
    update.message.reply_text.assert_not_called()


@pytest.mark.asyncio
async def test_cmd_help_returns_commands():
    update = _make_update()
    await cmd_help(update, _make_context())
    text = update.message.reply_text.call_args[0][0]
    assert "/status" in text


@pytest.mark.asyncio
async def test_cmd_status_shows_mode_and_availability():
    update = _make_update()
    await cmd_status(update, _make_context())
    text = update.message.reply_text.call_args[0][0]
    assert "MANUAL" in text
    assert "ONLINE" in text


@pytest.mark.asyncio
async def test_cmd_mode_switches_to_semi():
    update = _make_update()
    ctx = _make_context(args=["semi"])
    await cmd_mode(update, ctx)
    assert get_state()["mode"] == OperatingMode.SEMI
    text = update.message.reply_text.call_args[0][0]
    assert "SEMI" in text


@pytest.mark.asyncio
async def test_cmd_mode_invalid_value():
    update = _make_update()
    ctx = _make_context(args=["turbo"])
    await cmd_mode(update, ctx)
    text = update.message.reply_text.call_args[0][0]
    assert "Unknown mode" in text
    assert get_state()["mode"] == OperatingMode.MANUAL  # unchanged


@pytest.mark.asyncio
async def test_cmd_mode_no_args():
    update = _make_update()
    ctx = _make_context(args=[])
    await cmd_mode(update, ctx)
    text = update.message.reply_text.call_args[0][0]
    assert "Usage" in text


@pytest.mark.asyncio
async def test_cmd_online():
    update = _make_update()
    await cmd_online(update, _make_context())
    assert get_state()["availability"] == Availability.ONLINE


@pytest.mark.asyncio
async def test_cmd_slow():
    update = _make_update()
    await cmd_slow(update, _make_context())
    assert get_state()["availability"] == Availability.SLOW


@pytest.mark.asyncio
async def test_cmd_pause():
    update = _make_update()
    await cmd_pause(update, _make_context())
    assert get_state()["availability"] == Availability.OFFLINE


@pytest.mark.asyncio
async def test_cmd_trades_empty_db():
    update = _make_update()
    ctx = _make_context(args=["today"])
    await cmd_trades(update, ctx)
    text = update.message.reply_text.call_args[0][0]
    assert "Count:  0" in text


@pytest.mark.asyncio
async def test_cmd_trades_with_data():
    with db.get_session() as s:
        s.add(P2PTrade(
            timestamp=datetime.utcnow(),
            trade_type="sell",
            amount_usdt=100.0,
            rate_sdg=600.0,
            total_sdg=60000.0,
            trader_username="x",
            profit_sdg=1000.0,
            mode="manual",
        ))

    update = _make_update()
    ctx = _make_context(args=["today"])
    await cmd_trades(update, ctx)
    text = update.message.reply_text.call_args[0][0]
    assert "Count:  1" in text
    assert "100.0 USDT" in text


@pytest.mark.asyncio
async def test_cmd_risk():
    update = _make_update()
    await cmd_risk(update, _make_context())
    text = update.message.reply_text.call_args[0][0]
    assert "manual only" in text.lower() or "Manual" in text


@pytest.mark.asyncio
async def test_unauthorised_user_ignored_for_all_commands():
    bad_update = _make_update(user_id=42)
    ctx = _make_context()
    for cmd in [cmd_help, cmd_status, cmd_online, cmd_slow, cmd_pause, cmd_risk]:
        bad_update.message.reply_text.reset_mock()
        await cmd(bad_update, ctx)
        bad_update.message.reply_text.assert_not_called()
