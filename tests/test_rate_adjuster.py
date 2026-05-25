"""Tests for p2p/rate_adjuster.py — all HTTP calls are mocked."""
from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import config as cfg
from p2p.market_monitor import MarketData, Offer
from p2p.rate_adjuster import (
    AdInfo,
    compute_target_price,
    run_adjuster,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("BINANCE_API_KEY", "test_key")
    monkeypatch.setenv("BINANCE_SECRET_KEY", "test_secret")
    monkeypatch.setenv("P2P_RATE_ADJUSTER_ENABLED", "true")
    monkeypatch.setenv("P2P_RATE_ADJUSTER_STEP", "1.0")
    monkeypatch.setenv("P2P_RATE_ADJUSTER_OFFSET", "0.5")
    cfg.reset_config()
    yield
    cfg.reset_config()


def _market(sell_best: float | None = 4085.0, buy_best: float | None = 4071.0) -> MarketData:
    return MarketData(
        timestamp=datetime.utcnow(),
        buy_offers=[],
        sell_offers=[],
        buy_best_rate=buy_best,
        sell_best_rate=sell_best,
        spread=(sell_best - buy_best) if (sell_best and buy_best) else None,
    )


def _ad(trade_type: str, price: float) -> AdInfo:
    return AdInfo(ad_no="ADV001", trade_type=trade_type, price=price, asset="USDT", fiat="SDG")


# ── compute_target_price ──────────────────────────────────────────────────────

def test_sell_ad_undercuts_best_seller():
    # Best sell = 4085, offset = 0.5  → target = 4084.5
    result = compute_target_price("SELL", _market(sell_best=4085.0), offset=0.5)
    assert result == pytest.approx(4084.5)


def test_buy_ad_outbids_best_buyer():
    # Best buy = 4071, offset = 0.5  → target = 4071.5
    result = compute_target_price("BUY", _market(buy_best=4071.0), offset=0.5)
    assert result == pytest.approx(4071.5)


def test_sell_ad_no_market_data_returns_none():
    result = compute_target_price("SELL", _market(sell_best=None), offset=0.5)
    assert result is None


def test_buy_ad_no_market_data_returns_none():
    result = compute_target_price("BUY", _market(buy_best=None), offset=0.5)
    assert result is None


def test_target_rounded_to_2dp():
    result = compute_target_price("SELL", _market(sell_best=4085.001), offset=0.3)
    assert result == round(4085.001 - 0.3, 2)


# ── run_adjuster — disabled / no key ─────────────────────────────────────────

@pytest.mark.asyncio
async def test_adjuster_disabled_returns_empty(monkeypatch):
    monkeypatch.setenv("P2P_RATE_ADJUSTER_ENABLED", "false")
    cfg.reset_config()
    msgs = await run_adjuster(_market())
    assert msgs == []


@pytest.mark.asyncio
async def test_adjuster_no_api_key_returns_empty(monkeypatch):
    monkeypatch.setenv("BINANCE_API_KEY", "")
    cfg.reset_config()
    msgs = await run_adjuster(_market())
    assert msgs == []


# ── run_adjuster — manual mode (dry-run) ─────────────────────────────────────

@pytest.mark.asyncio
async def test_manual_mode_suggests_but_does_not_update(monkeypatch):
    monkeypatch.setenv("OPERATING_MODE", "manual")
    cfg.reset_config()

    ad = _ad("SELL", 4090.0)  # current = 4090, target = 4084.5, drift = 5.5 ≥ step 1
    with patch("p2p.rate_adjuster.get_my_ads", new=AsyncMock(return_value=[ad])):
        with patch("p2p.rate_adjuster._update_ad_price") as mock_update:
            msgs = await run_adjuster(_market(sell_best=4085.0))

    assert len(msgs) == 1
    assert "💡" in msgs[0]
    assert "4084.50" in msgs[0]
    assert "Semi/Full" in msgs[0]
    mock_update.assert_not_called()


# ── run_adjuster — semi mode (live updates) ───────────────────────────────────

@pytest.mark.asyncio
async def test_semi_mode_updates_ad_when_drift_exceeds_step(monkeypatch):
    monkeypatch.setenv("OPERATING_MODE", "semi")
    cfg.reset_config()

    ad = _ad("SELL", 4090.0)  # drift = 4090 - 4084.5 = 5.5 ≥ step 1
    with patch("p2p.rate_adjuster.get_my_ads", new=AsyncMock(return_value=[ad])):
        with patch("p2p.rate_adjuster._update_ad_price", new=AsyncMock(return_value=True)) as mock_upd:
            msgs = await run_adjuster(_market(sell_best=4085.0))

    assert len(msgs) == 1
    assert "✅" in msgs[0]
    assert "4084.50" in msgs[0]
    mock_upd.assert_called_once_with("ADV001", pytest.approx(4084.5))


@pytest.mark.asyncio
async def test_drift_below_step_no_update(monkeypatch):
    monkeypatch.setenv("OPERATING_MODE", "semi")
    monkeypatch.setenv("P2P_RATE_ADJUSTER_STEP", "5.0")
    cfg.reset_config()

    ad = _ad("SELL", 4085.3)  # drift = 4085.3 - 4084.5 = 0.8, below step 5.0
    with patch("p2p.rate_adjuster.get_my_ads", new=AsyncMock(return_value=[ad])):
        with patch("p2p.rate_adjuster._update_ad_price") as mock_upd:
            msgs = await run_adjuster(_market(sell_best=4085.0))

    assert msgs == []
    mock_upd.assert_not_called()


@pytest.mark.asyncio
async def test_update_failure_returns_warning(monkeypatch):
    monkeypatch.setenv("OPERATING_MODE", "semi")
    cfg.reset_config()

    ad = _ad("SELL", 4090.0)
    with patch("p2p.rate_adjuster.get_my_ads", new=AsyncMock(return_value=[ad])):
        with patch("p2p.rate_adjuster._update_ad_price", new=AsyncMock(return_value=False)):
            msgs = await run_adjuster(_market(sell_best=4085.0))

    assert len(msgs) == 1
    assert "⚠️" in msgs[0]


@pytest.mark.asyncio
async def test_buy_ad_outbid_strategy(monkeypatch):
    monkeypatch.setenv("OPERATING_MODE", "semi")
    cfg.reset_config()

    ad = _ad("BUY", 4060.0)  # target = 4071 + 0.5 = 4071.5, drift = 11.5 ≥ step 1
    with patch("p2p.rate_adjuster.get_my_ads", new=AsyncMock(return_value=[ad])):
        with patch("p2p.rate_adjuster._update_ad_price", new=AsyncMock(return_value=True)) as mock_upd:
            msgs = await run_adjuster(_market(buy_best=4071.0))

    assert "✅" in msgs[0]
    assert "↑" in msgs[0]
    mock_upd.assert_called_once_with("ADV001", pytest.approx(4071.5))


@pytest.mark.asyncio
async def test_get_my_ads_exception_returns_empty(monkeypatch):
    monkeypatch.setenv("OPERATING_MODE", "semi")
    cfg.reset_config()

    with patch("p2p.rate_adjuster.get_my_ads", new=AsyncMock(side_effect=Exception("timeout"))):
        msgs = await run_adjuster(_market())

    assert msgs == []


@pytest.mark.asyncio
async def test_no_ads_returns_empty(monkeypatch):
    monkeypatch.setenv("OPERATING_MODE", "semi")
    cfg.reset_config()

    with patch("p2p.rate_adjuster.get_my_ads", new=AsyncMock(return_value=[])):
        msgs = await run_adjuster(_market())

    assert msgs == []
