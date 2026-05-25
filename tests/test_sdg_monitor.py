"""
Tests for intelligence/sdg_monitor.py
No real DB calls except get_sdg_summary (which uses the in-memory DB fixture).
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

import pytest

import config as cfg
import data.database as db
from data.models import MarketSnapshot
from intelligence.sdg_monitor import (
    RateTrend,
    compute_rate_trend,
    check_rate_movement_alerts,
    get_sdg_summary,
)


# ── helpers ──────────────────────────────────────────────────────────────────

def _snap(buy: float, sell: float, minutes_ago: int = 0) -> MarketSnapshot:
    """Build an unsaved MarketSnapshot (no DB write needed for pure unit tests)."""
    return MarketSnapshot(
        buy_best_rate=buy,
        sell_best_rate=sell,
        spread=round(buy - sell, 2),
        our_rate=None,
        competitors_json=json.dumps({}),
        timestamp=datetime.utcnow() - timedelta(minutes=minutes_ago),
    )


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_USER_ID", "1")
    cfg.reset_config()
    db.init_db(":memory:")
    yield
    db.reset_db()
    cfg.reset_config()


# ── compute_rate_trend ────────────────────────────────────────────────────────

def test_trend_empty_snapshots():
    t = compute_rate_trend([], window_slots=12)
    assert t.direction == "stable"
    assert t.change_abs == 0.0
    assert t.from_rate is None
    assert t.to_rate is None


def test_trend_single_snapshot():
    t = compute_rate_trend([_snap(600.0, 580.0)], window_slots=12)
    assert t.direction == "stable"
    assert t.change_abs == 0.0
    assert t.to_rate == 600.0


def test_trend_up():
    # newest first: current=610, 1h-ago=600 → +10 SDG
    snaps = [_snap(610.0, 590.0)] + [_snap(600.0, 580.0)] * 11
    t = compute_rate_trend(snaps, window_slots=12)
    assert t.direction == "up"
    assert t.change_abs == pytest.approx(10.0)
    assert t.change_pct == pytest.approx(10 / 600 * 100, rel=1e-3)


def test_trend_down():
    snaps = [_snap(590.0, 570.0)] + [_snap(600.0, 580.0)] * 11
    t = compute_rate_trend(snaps, window_slots=12)
    assert t.direction == "down"
    assert t.change_abs == pytest.approx(-10.0)


def test_trend_stable_within_threshold():
    # change = 0.3 SDG — below the 0.5 threshold
    snaps = [_snap(600.3, 580.0)] + [_snap(600.0, 580.0)] * 11
    t = compute_rate_trend(snaps, window_slots=12)
    assert t.direction == "stable"


def test_trend_fewer_slots_than_window():
    # only 3 snapshots but window=12 — should use the oldest available
    snaps = [_snap(605.0, 585.0), _snap(602.0, 582.0), _snap(600.0, 580.0)]
    t = compute_rate_trend(snaps, window_slots=12)
    assert t.from_rate == 600.0
    assert t.to_rate == 605.0
    assert t.direction == "up"


# ── check_rate_movement_alerts ────────────────────────────────────────────────

def test_no_alerts_stable_market():
    snaps = [_snap(600.0, 580.0)] * 72
    alerts = check_rate_movement_alerts(snaps)
    assert alerts == []


def test_no_alerts_single_snapshot():
    alerts = check_rate_movement_alerts([_snap(600.0, 580.0)])
    assert alerts == []


def test_alert_large_1h_move_up():
    # 1h move: 600 → 608 (+8 SDG, above threshold of 5)
    snaps = [_snap(608.0, 588.0)] + [_snap(600.0, 580.0)] * 71
    alerts = check_rate_movement_alerts(snaps)
    assert len(alerts) == 1
    assert "risen" in alerts[0]
    assert "8.0 SDG" in alerts[0]


def test_alert_large_1h_move_down():
    snaps = [_snap(592.0, 572.0)] + [_snap(600.0, 580.0)] * 71
    alerts = check_rate_movement_alerts(snaps)
    assert len(alerts) == 1
    assert "fallen" in alerts[0]


def test_no_alert_small_1h_move():
    # 4 SDG change — below the 5 SDG threshold
    snaps = [_snap(604.0, 584.0)] + [_snap(600.0, 580.0)] * 71
    alerts = check_rate_movement_alerts(snaps)
    assert alerts == []


def test_alert_sustained_6h_up():
    # 6h: baseline=600, current=612 (+12 SDG), 1h: stable
    # First 12 snapshots (1h): current → just above stable threshold
    snaps = (
        [_snap(612.0, 592.0)] * 12   # last 1h (change vs 1h-ago = 0 → stable)
        + [_snap(600.0, 580.0)] * 60  # 6h baseline
    )
    alerts = check_rate_movement_alerts(snaps)
    assert any("strengthening" in a for a in alerts)


def test_alert_sustained_6h_down():
    snaps = (
        [_snap(588.0, 568.0)] * 12
        + [_snap(600.0, 580.0)] * 60
    )
    alerts = check_rate_movement_alerts(snaps)
    assert any("weakening" in a for a in alerts)


# ── get_sdg_summary ───────────────────────────────────────────────────────────

def test_sdg_summary_empty_db():
    summary = get_sdg_summary()
    assert summary["current_buy_rate"] is None
    assert summary["snapshots_available"] == 0
    assert summary["trend_1h"] is None


def test_sdg_summary_with_data():
    with db.get_session() as s:
        for i in range(15):
            s.add(MarketSnapshot(
                timestamp=datetime.utcnow() - timedelta(minutes=i * 5),
                buy_best_rate=600.0 + i * 0.5,
                sell_best_rate=580.0 + i * 0.5,
                spread=20.0,
                our_rate=None,
                competitors_json="{}",
            ))

    summary = get_sdg_summary()
    assert summary["current_buy_rate"] is not None
    assert summary["snapshots_available"] == 15
    assert summary["trend_1h"] is not None
    assert summary["trend_1h"]["direction"] in ("up", "down", "stable")
