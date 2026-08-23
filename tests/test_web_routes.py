"""
Tests for web routes — status, p2p, stream.
Uses FastAPI TestClient (synchronous) — no real HTTP calls, no scheduler.
"""
from __future__ import annotations

import json
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

import config as cfg
import data.database as db
from data.models import MarketSnapshot, P2PTrade
from web.app import create_app
from web.state import reset_state
from web.alerts import reset_bus


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_USER_ID", "1")
    cfg.reset_config()
    db.init_db(":memory:")
    reset_state()
    reset_bus()
    yield
    db.reset_db()
    cfg.reset_config()
    reset_state()
    reset_bus()


@pytest.fixture()
def client():
    app = create_app()
    return TestClient(app)


# ── /api/status ───────────────────────────────────────────────────────────────

def test_get_status_defaults(client):
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert data["mode"] == "manual"
    assert data["availability"] == "online"


def test_set_mode_valid(client):
    r = client.post("/api/mode", json={"mode": "semi"})
    assert r.status_code == 200
    assert r.json()["mode"] == "semi"


def test_set_mode_invalid(client):
    r = client.post("/api/mode", json={"mode": "turbo"})
    assert r.status_code == 400


def test_set_mode_persists(client):
    client.post("/api/mode", json={"mode": "full"})
    r = client.get("/api/status")
    assert r.json()["mode"] == "full"


def test_set_availability_online(client):
    r = client.post("/api/availability", json={"availability": "offline"})
    assert r.status_code == 200
    assert r.json()["availability"] == "offline"


def test_set_availability_invalid(client):
    r = client.post("/api/availability", json={"availability": "turbo"})
    assert r.status_code == 400


def test_mode_change_logged_to_db(client):
    client.post("/api/mode", json={"mode": "semi"})
    from data.models import SystemEvent
    with db.get_session() as s:
        event = s.query(SystemEvent).filter_by(event_type="mode_change").first()
        assert event is not None
        assert "semi" in event.description


# ── /api/p2p/snapshot ─────────────────────────────────────────────────────────

def test_p2p_snapshot_empty(client):
    r = client.get("/api/p2p/snapshot")
    assert r.status_code == 200
    data = r.json()
    assert data["spread"] is None
    assert data["top_sellers"] == []
    assert data["active_sellers"] == []


def test_p2p_snapshot_with_data(client):
    competitors = json.dumps({
        "buy_top10":  [{"name": "m1", "price": 610.0, "min": 100, "max": 5000}],
        "sell_top10": [{"name": "s1", "price": 590.0, "min": 100, "max": 5000}],
    })
    with db.get_session() as s:
        s.add(MarketSnapshot(
            timestamp=datetime.utcnow(),
            buy_best_rate=610.0,
            sell_best_rate=590.0,
            spread=20.0,
            our_rate=600.0,
            competitors_json=competitors,
        ))

    r = client.get("/api/p2p/snapshot")
    assert r.status_code == 200
    data = r.json()
    assert data["spread"] == 20.0
    assert data["buy_best_rate"] == 610.0
    assert len(data["top_sellers"]) == 1
    assert data["top_sellers"][0]["name"] == "m1"
    assert len(data["active_sellers"]) == 1
    assert data["active_sellers"][0]["name"] == "s1"


# ── POST /api/p2p/trades ─────────────────────────────────────────────────────

def test_log_trade_returns_201(client):
    r = client.post("/api/p2p/trades", json={
        "trade_type": "sell",
        "amount_usdt": 50.0,
        "rate_sdg": 4085.0,
        "trader_username": "TestBuyer",
    })
    assert r.status_code == 201
    data = r.json()
    assert data["id"] is not None
    assert data["total_sdg"] == pytest.approx(50.0 * 4085.0)


def test_log_trade_appears_in_today_stats(client):
    client.post("/api/p2p/trades", json={
        "trade_type": "buy",
        "amount_usdt": 100.0,
        "rate_sdg": 4071.0,
        "trader_username": "TestSeller",
        "profit_sdg": 320.0,
    })
    r = client.get("/api/p2p/stats/today")
    data = r.json()
    assert data["count"] == 1
    assert data["volume_usdt"] == pytest.approx(100.0)
    assert data["profit_sdg"] == pytest.approx(320.0)


def test_log_trade_missing_required_field(client):
    r = client.post("/api/p2p/trades", json={
        "trade_type": "sell",
        "amount_usdt": 50.0,
        # missing rate_sdg and trader_username
    })
    assert r.status_code == 422


# ── /api/p2p/stats/today ─────────────────────────────────────────────────────

def test_today_stats_empty(client):
    r = client.get("/api/p2p/stats/today")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 0
    assert data["volume_usdt"] == 0.0


def test_today_stats_with_trades(client):
    with db.get_session() as s:
        s.add(P2PTrade(
            timestamp=datetime.utcnow(),
            trade_type="sell",
            amount_usdt=100.0,
            rate_sdg=600.0,
            total_sdg=60000.0,
            trader_username="x",
            profit_sdg=500.0,
            mode="manual",
        ))

    r = client.get("/api/p2p/stats/today")
    data = r.json()
    assert data["count"] == 1
    assert data["volume_usdt"] == pytest.approx(100.0)
    assert data["profit_sdg"] == pytest.approx(500.0)


# ── /api/p2p/stats/{days} ────────────────────────────────────────────────────

def test_period_stats_7_days(client):
    r = client.get("/api/p2p/stats/7")
    assert r.status_code == 200
    assert r.json()["days"] == 7


def test_period_stats_30_days(client):
    r = client.get("/api/p2p/stats/30")
    assert r.status_code == 200
    assert r.json()["days"] == 30


def test_period_stats_invalid_days(client):
    r = client.get("/api/p2p/stats/99")
    assert r.status_code == 400


# ── /api/stream ───────────────────────────────────────────────────────────────

def test_stream_route_registered(client):
    # Verify the SSE route exists without consuming the infinite stream.
    routes = set()
    # Check both app.routes and app.router.routes (TestClient sometimes puts routes in different places)
    for route_list in [client.app.routes, client.app.router.routes]:
        for r in route_list:
            if hasattr(r, 'path'):
                routes.add(r.path)
            elif hasattr(r, 'routes'):  # IncludedRouter
                for sub_r in r.routes:
                    if hasattr(sub_r, 'path'):
                        routes.add(sub_r.path)
                    elif hasattr(sub_r, 'original_router'):  # _IncludedRouter
                        for inner_r in sub_r.original_router.routes:
                            if hasattr(inner_r, 'path'):
                                routes.add(inner_r.path)
            elif hasattr(r, 'original_router'):  # _IncludedRouter directly in route_list
                for inner_r in r.original_router.routes:
                    if hasattr(inner_r, 'path'):
                        routes.add(inner_r.path)
    assert "/api/stream" in routes
