"""Tests for intelligence/analytics.py"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import config as cfg
import data.database as db
from data.models import MarketSnapshot
from intelligence.analytics import get_spread_history, get_market_context, get_hourly_patterns


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_USER_ID", "1")
    cfg.reset_config()
    db.init_db(":memory:")
    yield
    db.reset_db()
    cfg.reset_config()


def _snap(hours_ago: float, spread: float, buy: float = 4071.0, sell: float = 4085.0):
    with db.get_session() as s:
        s.add(MarketSnapshot(
            timestamp=datetime.utcnow() - timedelta(hours=hours_ago),
            buy_best_rate=buy,
            sell_best_rate=sell,
            spread=spread,
        ))


# ── get_spread_history ────────────────────────────────────────────────────────

def test_history_empty_db():
    assert get_spread_history(7) == []


def test_history_returns_hourly_points():
    # 3 snaps within the same clock-hour → should collapse to 1 averaged point
    base = datetime.utcnow().replace(minute=30, second=0, microsecond=0)
    with db.get_session() as s:
        for offset_min in [5, 10, 15]:
            s.add(MarketSnapshot(
                timestamp=base - timedelta(minutes=offset_min),
                spread=10.0 * offset_min / 5,  # 10, 20, 30
                buy_best_rate=4071.0,
                sell_best_rate=4085.0,
            ))
    result = get_spread_history(7)
    assert len(result) == 1
    assert result[0]["spread"] == pytest.approx(20.0)


def test_history_two_separate_hours():
    _snap(1.0, 10.0)
    _snap(3.0, 20.0)
    result = get_spread_history(7)
    assert len(result) == 2


def test_history_excludes_beyond_window():
    _snap(1.0, 10.0)   # inside window
    _snap(200.0, 99.0) # 8+ days ago — outside 7-day window
    result = get_spread_history(7)
    assert len(result) == 1
    assert result[0]["spread"] == pytest.approx(10.0)


def test_history_point_has_required_keys():
    _snap(1.0, 14.0)
    point = get_spread_history(7)[0]
    assert "timestamp" in point
    assert "spread" in point
    assert "buy_rate" in point
    assert "sell_rate" in point


# ── get_market_context ────────────────────────────────────────────────────────

def test_context_empty_db():
    result = get_market_context()
    assert result == {"ok": False}


def test_context_has_required_fields():
    for h in range(10):
        _snap(h * 2, spread=10.0 + h)
    ctx = get_market_context(days=30)
    assert ctx["ok"] is True
    for key in ("current_spread", "spread_avg", "spread_min", "spread_max",
                "spread_percentile", "spread_vs_avg", "sample_count"):
        assert key in ctx


def test_context_percentile_current_is_max():
    # Current spread (last inserted) is the highest → should be 100th percentile
    for h in range(5, 0, -1):
        _snap(h, spread=float(h * 10))   # 50, 40, 30, 20, 10
    _snap(0.1, spread=60.0)              # current = highest
    ctx = get_market_context(days=30)
    assert ctx["spread_percentile"] == 100


def test_context_percentile_current_is_min():
    for h in range(5, 0, -1):
        _snap(h, spread=float(h * 10))   # 50, 40, 30, 20, 10
    _snap(0.1, spread=5.0)               # current = lowest
    ctx = get_market_context(days=30)
    assert ctx["spread_percentile"] <= 20  # bottom of the range


def test_context_vs_avg_positive_when_above():
    _snap(2.0, 10.0)
    _snap(1.0, 10.0)
    _snap(0.1, 20.0)  # current is 10 above avg of 10
    ctx = get_market_context(days=30)
    assert ctx["spread_vs_avg"] > 0


# ── get_hourly_patterns ───────────────────────────────────────────────────────

def test_patterns_always_returns_24_slots():
    result = get_hourly_patterns()
    assert len(result) == 24


def test_patterns_empty_slots_have_none_avg():
    result = get_hourly_patterns()
    for slot in result:
        assert slot["avg_spread"] is None
        assert slot["sample_count"] == 0
        assert slot["reliable"] is False


def test_patterns_populated_slot():
    # Insert 5 snaps that all fall on the same hour
    base = datetime.utcnow().replace(minute=5, second=0, microsecond=0)
    target_hour = base.hour
    with db.get_session() as s:
        for i in range(5):
            s.add(MarketSnapshot(
                timestamp=base - timedelta(days=i),
                spread=10.0 + i,
                buy_best_rate=4071.0,
                sell_best_rate=4085.0,
            ))

    result = get_hourly_patterns()
    slot = next(r for r in result if r["hour"] == target_hour)
    assert slot["sample_count"] == 5
    assert slot["reliable"] is True
    assert slot["avg_spread"] == pytest.approx(12.0)  # avg of 10,11,12,13,14
