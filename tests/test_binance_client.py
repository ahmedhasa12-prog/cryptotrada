"""Tests for binance/client.py — all HTTP calls are mocked."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import config as cfg
from binance.client import verify_connection, _sign


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("BINANCE_API_KEY", "test_api_key")
    monkeypatch.setenv("BINANCE_SECRET_KEY", "test_secret_key")
    cfg.reset_config()
    yield
    cfg.reset_config()


def _mock_response(status_code: int, body: dict):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = body
    return resp


def _patch_httpx(response):
    """Patch httpx.AsyncClient so client.get() returns `response`."""
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return patch("binance.client.httpx.AsyncClient", return_value=mock_cm)


# ── _sign ─────────────────────────────────────────────────────────────────────

def test_sign_is_deterministic():
    params = {"timestamp": 1234567890, "recvWindow": 5000}
    assert _sign("mysecret", params) == _sign("mysecret", params)


def test_sign_differs_for_different_secrets():
    params = {"timestamp": 1234567890}
    assert _sign("secret_a", params) != _sign("secret_b", params)


def test_sign_returns_hex_string():
    sig = _sign("key", {"timestamp": 1})
    assert all(c in "0123456789abcdef" for c in sig)
    assert len(sig) == 64  # SHA-256 hex digest


# ── verify_connection ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_verify_connection_success():
    resp = _mock_response(200, {"permissions": ["SPOT"], "canTrade": True})
    with _patch_httpx(resp):
        result = await verify_connection()
    assert result["ok"] is True
    assert "SPOT" in result["permissions"]
    assert result["can_trade"] is True


@pytest.mark.asyncio
async def test_verify_connection_spot_not_in_permissions():
    resp = _mock_response(200, {"permissions": [], "canTrade": False})
    with _patch_httpx(resp):
        result = await verify_connection()
    assert result["ok"] is True
    assert result["can_trade"] is False


@pytest.mark.asyncio
async def test_verify_connection_invalid_key():
    resp = _mock_response(401, {"code": -2014, "msg": "API-key format invalid."})
    with _patch_httpx(resp):
        result = await verify_connection()
    assert result["ok"] is False
    assert "invalid" in result["error"].lower()


@pytest.mark.asyncio
async def test_verify_connection_no_key_configured(monkeypatch):
    monkeypatch.setenv("BINANCE_API_KEY", "")
    cfg.reset_config()
    result = await verify_connection()
    assert result["ok"] is False
    assert "not configured" in result["error"]


@pytest.mark.asyncio
async def test_verify_connection_no_secret_configured(monkeypatch):
    monkeypatch.setenv("BINANCE_SECRET_KEY", "")
    cfg.reset_config()
    result = await verify_connection()
    assert result["ok"] is False


@pytest.mark.asyncio
async def test_verify_connection_sends_api_key_header():
    resp = _mock_response(200, {"permissions": ["SPOT"]})
    with _patch_httpx(resp) as mock_cls:
        await verify_connection()
    mock_client = mock_cls.return_value.__aenter__.return_value
    _, kwargs = mock_client.get.call_args
    assert kwargs["headers"]["X-MBX-APIKEY"] == "test_api_key"


@pytest.mark.asyncio
async def test_verify_connection_sends_signature_param():
    resp = _mock_response(200, {"permissions": ["SPOT"]})
    with _patch_httpx(resp) as mock_cls:
        await verify_connection()
    mock_client = mock_cls.return_value.__aenter__.return_value
    _, kwargs = mock_client.get.call_args
    assert "signature" in kwargs["params"]
    assert "timestamp" in kwargs["params"]
