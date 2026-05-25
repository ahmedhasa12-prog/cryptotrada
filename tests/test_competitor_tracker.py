"""Tests for intelligence/competitor_tracker.py"""
from __future__ import annotations

import json

import pytest

import config as cfg
import data.database as db
from data.models import MarketSnapshot
from intelligence.competitor_tracker import (
    check_competitor_changes,
    _prices_from_snapshot,
    _prices_from_offers,
)
from p2p.market_monitor import Offer


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_USER_ID", "1")
    cfg.reset_config()
    db.init_db(":memory:")
    yield
    db.reset_db()
    cfg.reset_config()


def _snap(buy_prices: dict[str, float], sell_prices: dict[str, float]) -> MarketSnapshot:
    competitors = {
        "buy_top10":  [{"name": n, "price": p, "min": 100, "max": 5000} for n, p in buy_prices.items()],
        "sell_top10": [{"name": n, "price": p, "min": 100, "max": 5000} for n, p in sell_prices.items()],
    }
    return MarketSnapshot(
        buy_best_rate=min(buy_prices.values()) if buy_prices else None,
        sell_best_rate=max(sell_prices.values()) if sell_prices else None,
        spread=None,
        our_rate=None,
        competitors_json=json.dumps(competitors),
    )


def _offer(name: str, price: float) -> Offer:
    return Offer(name, price, 100, 5000, 200, 300, 97.0)


# ── _prices_from_snapshot ────────────────────────────────────────────────────

def test_prices_from_snapshot_extracts_both_sides():
    snap = _snap({"Flyrate1": 4100.0}, {"MOATZ-CRYPTO": 4071.0})
    prices = _prices_from_snapshot(snap)
    assert prices["Flyrate1"] == 4100.0
    assert prices["MOATZ-CRYPTO"] == 4071.0


def test_prices_from_snapshot_none():
    assert _prices_from_snapshot(None) == {}


def test_prices_from_snapshot_empty_json():
    snap = MarketSnapshot(competitors_json="{}", spread=None, our_rate=None)
    assert _prices_from_snapshot(snap) == {}


# ── _prices_from_offers ───────────────────────────────────────────────────────

def test_prices_from_offers():
    offers = [_offer("Flyrate1", 4099.99), _offer("MOATZ-CRYPTO", 4071.02)]
    prices = _prices_from_offers(offers)
    assert prices["Flyrate1"] == pytest.approx(4099.99)
    assert prices["MOATZ-CRYPTO"] == pytest.approx(4071.02)


# ── check_competitor_changes ──────────────────────────────────────────────────

def test_no_watched_merchants_no_alerts(monkeypatch):
    monkeypatch.setenv("P2P_WATCHED_MERCHANTS", "")
    cfg.reset_config()
    snap = _snap({"Flyrate1": 4100.0}, {})
    alerts = check_competitor_changes([_offer("Flyrate1", 4080.0)], [], snap)
    assert alerts == []


def test_no_last_snapshot_no_alerts(monkeypatch):
    monkeypatch.setenv("P2P_WATCHED_MERCHANTS", "Flyrate1")
    cfg.reset_config()
    alerts = check_competitor_changes([_offer("Flyrate1", 4080.0)], [], None)
    assert alerts == []


def test_price_unchanged_no_alert(monkeypatch):
    monkeypatch.setenv("P2P_WATCHED_MERCHANTS", "Flyrate1")
    monkeypatch.setenv("P2P_COMPETITOR_ALERT_THRESHOLD", "5")
    cfg.reset_config()
    snap = _snap({"Flyrate1": 4100.0}, {})
    alerts = check_competitor_changes([_offer("Flyrate1", 4100.0)], [], snap)
    assert alerts == []


def test_small_change_below_threshold_no_alert(monkeypatch):
    monkeypatch.setenv("P2P_WATCHED_MERCHANTS", "Flyrate1")
    monkeypatch.setenv("P2P_COMPETITOR_ALERT_THRESHOLD", "5")
    cfg.reset_config()
    snap = _snap({"Flyrate1": 4100.0}, {})
    # change = 3 SDG, below 5 threshold
    alerts = check_competitor_changes([_offer("Flyrate1", 4103.0)], [], snap)
    assert alerts == []


def test_price_drop_triggers_alert(monkeypatch):
    monkeypatch.setenv("P2P_WATCHED_MERCHANTS", "Flyrate1")
    monkeypatch.setenv("P2P_COMPETITOR_ALERT_THRESHOLD", "5")
    cfg.reset_config()
    snap = _snap({"Flyrate1": 4100.0}, {})
    # Flyrate1 dropped 29 SDG
    alerts = check_competitor_changes([_offer("Flyrate1", 4071.0)], [], snap)
    assert len(alerts) == 1
    assert "Flyrate1" in alerts[0]
    assert "↓" in alerts[0]
    assert "29.0 SDG" in alerts[0]
    assert "4100.00" in alerts[0]
    assert "4071.00" in alerts[0]


def test_price_rise_triggers_alert(monkeypatch):
    monkeypatch.setenv("P2P_WATCHED_MERCHANTS", "MOATZ-CRYPTO")
    monkeypatch.setenv("P2P_COMPETITOR_ALERT_THRESHOLD", "5")
    cfg.reset_config()
    snap = _snap({}, {"MOATZ-CRYPTO": 4071.0})
    alerts = check_competitor_changes([], [_offer("MOATZ-CRYPTO", 4090.0)], snap)
    assert len(alerts) == 1
    assert "↑" in alerts[0]
    assert "19.0 SDG" in alerts[0]


def test_multiple_watched_merchants(monkeypatch):
    monkeypatch.setenv("P2P_WATCHED_MERCHANTS", "Flyrate1,MOATZ-CRYPTO")
    monkeypatch.setenv("P2P_COMPETITOR_ALERT_THRESHOLD", "5")
    cfg.reset_config()
    snap = _snap({"Flyrate1": 4100.0}, {"MOATZ-CRYPTO": 4071.0})
    current_buy = [_offer("Flyrate1", 4071.0)]   # dropped 29
    current_sell = [_offer("MOATZ-CRYPTO", 4071.0)]  # unchanged
    alerts = check_competitor_changes(current_buy, current_sell, snap)
    assert len(alerts) == 1
    assert "Flyrate1" in alerts[0]


def test_unwatched_merchant_ignored(monkeypatch):
    monkeypatch.setenv("P2P_WATCHED_MERCHANTS", "Flyrate1")
    monkeypatch.setenv("P2P_COMPETITOR_ALERT_THRESHOLD", "5")
    cfg.reset_config()
    snap = _snap({"SomeOtherMerchant": 4100.0}, {})
    alerts = check_competitor_changes([_offer("SomeOtherMerchant", 4060.0)], [], snap)
    assert alerts == []


def test_merchant_missing_from_current_no_crash(monkeypatch):
    monkeypatch.setenv("P2P_WATCHED_MERCHANTS", "Flyrate1")
    monkeypatch.setenv("P2P_COMPETITOR_ALERT_THRESHOLD", "5")
    cfg.reset_config()
    snap = _snap({"Flyrate1": 4100.0}, {})
    # Flyrate1 not in current offers (went offline)
    alerts = check_competitor_changes([], [], snap)
    assert alerts == []
