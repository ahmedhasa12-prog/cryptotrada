"""
Tests for p2p/p2p_logger.py
"""
from datetime import datetime, timedelta

import pytest

import config as cfg
import data.database as db
from p2p.p2p_logger import log_trade, get_daily_stats, get_period_stats
from data.models import P2PTrade


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_USER_ID", "1")
    cfg.reset_config()
    db.init_db(":memory:")
    yield
    db.reset_db()
    cfg.reset_config()


def test_log_trade_persists():
    log_trade("sell", 100.0, 600.0, "alice", "manual",
               profit_sdg=1000.0, release_time_minutes=2.5)

    with db.get_session() as s:
        trade = s.query(P2PTrade).filter_by(trader_username="alice").first()
        assert trade is not None
        assert trade.total_sdg == 60000.0
        assert trade.profit_sdg == 1000.0
        assert trade.release_time_minutes == 2.5


def test_log_trade_computes_total_sdg():
    log_trade("buy", 50.0, 590.0, "bob", "manual")

    with db.get_session() as s:
        trade = s.query(P2PTrade).filter_by(trader_username="bob").first()
        assert trade.total_sdg == pytest.approx(29500.0)


def test_get_daily_stats_empty():
    stats = get_daily_stats()
    assert stats["count"] == 0
    assert stats["volume_usdt"] == 0.0
    assert stats["profit_sdg"] == 0.0
    assert stats["avg_release_minutes"] is None


def test_get_daily_stats_with_trades():
    log_trade("sell", 100.0, 600.0, "x1", "manual", profit_sdg=500.0, release_time_minutes=2.0)
    log_trade("sell", 200.0, 602.0, "x2", "manual", profit_sdg=800.0, release_time_minutes=4.0)

    stats = get_daily_stats()
    assert stats["count"] == 2
    assert stats["volume_usdt"] == pytest.approx(300.0)
    assert stats["profit_sdg"] == pytest.approx(1300.0)
    assert stats["avg_release_minutes"] == pytest.approx(3.0)
    assert stats["best_trade_profit_sdg"] == 800.0


def test_get_daily_stats_excludes_other_days():
    log_trade("sell", 100.0, 600.0, "today", "manual", profit_sdg=500.0)

    yesterday = datetime.utcnow() - timedelta(days=2)
    with db.get_session() as s:
        old = P2PTrade(
            timestamp=yesterday,
            trade_type="sell",
            amount_usdt=50.0,
            rate_sdg=595.0,
            total_sdg=29750.0,
            trader_username="yesterday",
            profit_sdg=200.0,
            mode="manual",
        )
        s.add(old)

    stats = get_daily_stats()
    assert stats["count"] == 1
    assert stats["volume_usdt"] == 100.0


def test_get_period_stats_7_days():
    log_trade("sell", 100.0, 600.0, "a", "manual", profit_sdg=500.0)
    log_trade("sell", 200.0, 605.0, "b", "manual", profit_sdg=700.0)

    stats = get_period_stats(7)
    assert stats["count"] == 2
    assert stats["volume_usdt"] == pytest.approx(300.0)
    assert stats["profit_sdg"] == pytest.approx(1200.0)


def test_get_period_stats_no_trades():
    stats = get_period_stats(30)
    assert stats["count"] == 0
