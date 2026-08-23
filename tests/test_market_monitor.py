"""
Tests for p2p/market_monitor.py.
All HTTP calls are mocked — no real Binance requests are made.
"""
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx

import config as cfg
import data.database as db
from p2p.market_monitor import (
    Offer,
    MarketData,
    _build_payload,
    _parse_offers,
    _active_offers,
    fetch_market_data,
    save_snapshot,
    check_alerts,
    check_premium_buyers,
    compute_average_spread,
)
from data.models import MarketSnapshot


# ── fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_USER_ID", "1")
    cfg.reset_config()
    db.init_db(":memory:")
    yield
    db.reset_db()
    cfg.reset_config()


def _make_p2p_response(prices: list[float], pay_time_limits: list[int] | None = None) -> dict:
    """Helper: build a fake Binance P2P API response."""
    limits = pay_time_limits or [15] * len(prices)
    return {
        "data": [
            {
                "adv": {
                    "price": str(p),
                    "minSingleTransAmount": "100",
                    "dynamicMaxSingleTransAmount": "5000",
                    "tradableQuantity": "200",
                    "payTimeLimit": limits[i],
                    "tradeMethods": [{"tradeMethodName": "Bank Transfer"}],
                },
                "advertiser": {
                    "nickName": f"merchant_{i}",
                    "monthOrderCount": 150,
                    "monthFinishRate": 0.98,
                },
            }
            for i, p in enumerate(prices)
        ]
    }


# ── unit tests ───────────────────────────────────────────────────────────────

def test_build_payload_buy():
    payload = _build_payload("USDT", "SDG", "BUY", rows=5)
    assert payload["asset"] == "USDT"
    assert payload["fiat"] == "SDG"
    assert payload["tradeType"] == "BUY"
    assert payload["rows"] == 5


def test_build_payload_sell():
    payload = _build_payload("USDT", "SDG", "SELL")
    assert payload["tradeType"] == "SELL"


def test_parse_offers_normal():
    raw = _make_p2p_response([600.0, 598.0, 596.0])
    offers = _parse_offers(raw)
    assert len(offers) == 3
    assert offers[0].price == 600.0
    assert offers[0].merchant_name == "merchant_0"
    assert offers[0].completion_rate == pytest.approx(98.0)
    assert "Bank Transfer" in offers[0].payment_methods


def test_parse_offers_empty():
    offers = _parse_offers({"data": []})
    assert offers == []


def test_parse_offers_skips_malformed():
    raw = {
        "data": [
            {"adv": {"price": "not_a_number"}, "advertiser": {"nickName": "x", "monthOrderCount": 0, "monthFinishRate": 0}}
        ]
    }
    offers = _parse_offers(raw)
    assert offers == []


def test_spread_calculation():
    buy_offers = [Offer("m1", 605.0, 100, 5000, 200, 100, 99.0)]
    sell_offers = [Offer("m2", 595.0, 100, 5000, 200, 100, 99.0)]
    data = MarketData(
        timestamp=datetime.utcnow(),
        buy_offers=buy_offers,
        sell_offers=sell_offers,
        buy_best_rate=605.0,
        sell_best_rate=595.0,
        spread=10.0,
    )
    assert data.spread == 10.0


# ── async tests ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_fetch_market_data_uses_mock_client():
    buy_response = _make_p2p_response([610.0, 608.0])
    sell_response = _make_p2p_response([590.0, 588.0])

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    buy_resp = MagicMock()
    buy_resp.json.return_value = buy_response
    buy_resp.raise_for_status = MagicMock()

    sell_resp = MagicMock()
    sell_resp.json.return_value = sell_response
    sell_resp.raise_for_status = MagicMock()

    mock_client.post = AsyncMock(side_effect=[buy_resp, sell_resp])

    data = await fetch_market_data("USDT", "SDG", client=mock_client)

    assert data.buy_best_rate == 610.0
    assert data.sell_best_rate == 590.0
    assert data.spread == 20.0  # buy_best(610) - sell_best(590) = spread
    assert len(data.buy_offers) == 2
    assert len(data.sell_offers) == 2


@pytest.mark.asyncio
async def test_fetch_market_data_empty_responses():
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    empty_resp = MagicMock()
    empty_resp.json.return_value = {"data": []}
    empty_resp.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(return_value=empty_resp)

    data = await fetch_market_data("USDT", "SDG", client=mock_client)
    assert data.buy_best_rate is None
    assert data.sell_best_rate is None
    assert data.spread is None


# ── database integration ──────────────────────────────────────────────────────

def test_save_snapshot_persists_data():
    data = MarketData(
        timestamp=datetime.utcnow(),
        buy_offers=[Offer("m1", 610.0, 100, 5000, 200, 100, 99.0)],
        sell_offers=[Offer("m2", 590.0, 100, 5000, 200, 100, 99.0)],
        buy_best_rate=610.0,
        sell_best_rate=590.0,
        spread=20.0,
    )
    save_snapshot(data, our_rate=600.0)

    with db.get_session() as s:
        snap = s.query(MarketSnapshot).first()
        assert snap is not None
        assert snap.spread == 20.0
        assert snap.our_rate == 600.0
        competitors = json.loads(snap.competitors_json)
        assert len(competitors["buy_top10"]) == 1


# ── alert logic ───────────────────────────────────────────────────────────────

def test_check_alerts_wide_spread(monkeypatch):
    monkeypatch.setenv("P2P_SPREAD_ALERT_HIGH", "25")
    cfg.reset_config()
    data = _market_data_with_spread(30.0)
    alerts = check_alerts(data)
    assert any("Wide spread" in a for a in alerts)


def test_check_alerts_tight_spread(monkeypatch):
    monkeypatch.setenv("P2P_SPREAD_ALERT_LOW", "10")
    cfg.reset_config()
    data = _market_data_with_spread(8.0)
    alerts = check_alerts(data)
    assert any("Tight spread" in a for a in alerts)


def test_check_alerts_no_alert_for_normal_spread():
    data = _market_data_with_spread(15.0)
    alerts = check_alerts(data)
    assert alerts == []


def test_check_alerts_no_spread():
    data = MarketData(datetime.utcnow(), [], [], None, None, None)
    alerts = check_alerts(data)
    assert alerts == []


def _market_data_with_spread(spread: float) -> MarketData:
    buy = 600.0 + spread / 2
    sell = 600.0 - spread / 2
    return MarketData(
        timestamp=datetime.utcnow(),
        buy_offers=[Offer("m1", buy, 100, 5000, 200, 100, 99.0)],
        sell_offers=[Offer("m2", sell, 100, 5000, 200, 100, 99.0)],
        buy_best_rate=buy,
        sell_best_rate=sell,
        spread=spread,
    )


# ── analytics ─────────────────────────────────────────────────────────────────

def test_compute_average_spread():
    snaps = [
        _snapshot_with_spread(10.0),
        _snapshot_with_spread(20.0),
        _snapshot_with_spread(None),
        _snapshot_with_spread(30.0),
    ]
    avg = compute_average_spread(snaps)
    assert avg == pytest.approx(20.0)


def test_compute_average_spread_all_none():
    snaps = [_snapshot_with_spread(None), _snapshot_with_spread(None)]
    assert compute_average_spread(snaps) is None


def _snapshot_with_spread(spread):
    s = MarketSnapshot()
    s.spread = spread
    return s


# ── pay_time_limit parsing ────────────────────────────────────────────────────

def test_parse_offers_includes_pay_time_limit():
    raw = _make_p2p_response([610.0, 608.0], pay_time_limits=[15, 180])
    offers = _parse_offers(raw)
    assert offers[0].pay_time_limit == 15
    assert offers[1].pay_time_limit == 180


# ── _active_offers filtering ──────────────────────────────────────────────────

def test_active_offers_filters_slow_merchants():
    offers = [
        Offer("slow", 4231.0, 100, 1001, 50000, 0, 0.0, [], pay_time_limit=180),
        Offer("fast1", 4071.0, 100, 5000, 200, 300, 97.0, [], pay_time_limit=15),
        Offer("fast2", 4070.0, 100, 5000, 200, 500, 98.0, [], pay_time_limit=15),
    ]
    active = _active_offers(offers)
    assert len(active) == 2
    assert all(o.pay_time_limit <= 30 for o in active)
    assert active[0].merchant_name == "fast1"


def test_active_offers_fallback_when_all_slow():
    offers = [
        Offer("slow1", 600.0, 100, 5000, 200, 10, 90.0, [], pay_time_limit=60),
        Offer("slow2", 598.0, 100, 5000, 200, 10, 90.0, [], pay_time_limit=120),
    ]
    active = _active_offers(offers)
    # Falls back to full list rather than returning empty
    assert len(active) == 2


def test_active_offers_empty_input():
    assert _active_offers([]) == []


# ── fetch_market_data uses active offers for best rates ───────────────────────

@pytest.mark.asyncio
async def test_fetch_filters_restricted_from_best_rate():
    # sell side: first offer is restricted (180 min), real best is 4071
    buy_response = _make_p2p_response([4079.0, 4080.0])
    sell_response = _make_p2p_response(
        [4231.0, 4071.0, 4070.0],
        pay_time_limits=[180, 15, 15],
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    buy_resp = MagicMock()
    buy_resp.json.return_value = buy_response
    buy_resp.raise_for_status = MagicMock()
    sell_resp = MagicMock()
    sell_resp.json.return_value = sell_response
    sell_resp.raise_for_status = MagicMock()
    mock_client.post = AsyncMock(side_effect=[buy_resp, sell_resp])

    data = await fetch_market_data("USDT", "SDG", client=mock_client)

    # sell_best should be 4071, not the restricted 4231
    assert data.sell_best_rate == 4071.0
    assert data.buy_best_rate == 4079.0
    assert data.spread == pytest.approx(8.0)  # buy(4079) - sell(4071) = tight market
    # All offers still present in the raw list
    assert len(data.sell_offers) == 3


# ── check_premium_buyers ──────────────────────────────────────────────────────

def test_premium_buyer_alert_triggers(monkeypatch):
    monkeypatch.setenv("P2P_PREMIUM_BUYER_THRESHOLD", "30")
    cfg.reset_config()
    offers = [
        Offer("HighPayer", 4180.0, 100, 5000, 200, 10, 91.0, [], pay_time_limit=15),
        Offer("Normal1",   4071.0, 100, 5000, 200, 345, 97.0, [], pay_time_limit=15),
        Offer("Normal2",   4071.0, 100, 5000, 200, 790, 96.0, [], pay_time_limit=15),
    ]
    alerts = check_premium_buyers(offers)
    assert len(alerts) == 1
    assert "HighPayer" in alerts[0]
    assert "109.0 SDG" in alerts[0]


def test_premium_buyer_no_alert_when_prices_close(monkeypatch):
    monkeypatch.setenv("P2P_PREMIUM_BUYER_THRESHOLD", "30")
    cfg.reset_config()
    offers = [
        Offer("m1", 4071.02, 100, 5000, 200, 345, 97.0, [], pay_time_limit=15),
        Offer("m2", 4071.00, 100, 5000, 200, 790, 96.0, [], pay_time_limit=15),
        Offer("m3", 4070.00, 100, 5000, 200, 57, 90.0, [], pay_time_limit=15),
    ]
    alerts = check_premium_buyers(offers)
    assert alerts == []


def test_premium_buyer_ignores_restricted_merchant(monkeypatch):
    monkeypatch.setenv("P2P_PREMIUM_BUYER_THRESHOLD", "30")
    cfg.reset_config()
    # Restricted merchant at top — should be ignored; no real premium below
    offers = [
        Offer("Restricted", 4231.0, 100, 1001, 50000, 0, 0.0, [], pay_time_limit=180),
        Offer("Normal1",    4072.0, 100, 5000, 200, 300, 97.0, [], pay_time_limit=15),
        Offer("Normal2",    4071.0, 100, 5000, 200, 500, 98.0, [], pay_time_limit=15),
    ]
    alerts = check_premium_buyers(offers)
    assert alerts == []


def test_premium_buyer_single_offer_no_alert(monkeypatch):
    monkeypatch.setenv("P2P_PREMIUM_BUYER_THRESHOLD", "30")
    cfg.reset_config()
    offers = [Offer("solo", 4071.0, 100, 5000, 200, 100, 97.0, [], pay_time_limit=15)]
    alerts = check_premium_buyers(offers)
    assert alerts == []
