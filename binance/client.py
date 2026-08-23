"""
Thin async wrapper around the Binance REST API.

Only signed endpoints (account data, order management) are here.
Public market-data endpoints (P2P search, ticker) are called directly
in their respective modules without needing a key.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from urllib.parse import urlencode

import httpx

from config import get_config

_BASE = "https://api.binance.com"


def _sign(secret: str, params: dict) -> str:
    query = urlencode(params)
    return hmac.new(secret.encode(), query.encode(), hashlib.sha256).hexdigest()


def _auth_headers(api_key: str) -> dict[str, str]:
    return {"X-MBX-APIKEY": api_key}


async def verify_connection() -> dict:
    """
    Call GET /api/v3/account to confirm the key is valid and has read access.
    Returns a dict with 'ok' (bool) and either 'permissions' or 'error'.
    """
    cfg = get_config()
    if not cfg.binance_api_key or not cfg.binance_secret_key:
        return {"ok": False, "error": "API key not configured — add to .env"}

    params: dict = {
        "timestamp": int(time.time() * 1000),
        "recvWindow": 5000,
    }
    params["signature"] = _sign(cfg.binance_secret_key, params)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            f"{_BASE}/api/v3/account",
            params=params,
            headers=_auth_headers(cfg.binance_api_key),
        )

    if resp.status_code == 200:
        data = resp.json()
        permissions: list[str] = data.get("permissions", [])
        # Binance uses "SPOT" (old accounts) or "TRD_GRP_XXX" (new accounts) for trading
        can_trade = "SPOT" in permissions or any(p.startswith("TRD_GRP_") for p in permissions)
        return {
            "ok": True,
            "permissions": permissions,
            "can_trade": can_trade,
        }

    error = resp.json().get("msg", f"HTTP {resp.status_code}")
    return {"ok": False, "error": error}


async def fetch_p2p_order_history(
    trade_type: str = "SELL",
    page: int = 1,
    rows: int = 100,
) -> dict:
    """
    GET /sapi/v1/c2c/orderMatch/listUserOrderHistory
    Returns your completed P2P trades. trade_type: "BUY" | "SELL".
    """
    cfg = get_config()
    if not cfg.binance_api_key or not cfg.binance_secret_key:
        return {"ok": False, "error": "API key not configured — add to .env"}

    params: dict = {
        "tradeType": trade_type,
        "page": page,
        "rows": rows,
        "timestamp": int(time.time() * 1000),
        "recvWindow": 5000,
    }
    params["signature"] = _sign(cfg.binance_secret_key, params)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            f"{_BASE}/sapi/v1/c2c/orderMatch/listUserOrderHistory",
            params=params,
            headers=_auth_headers(cfg.binance_api_key),
        )

    if resp.status_code != 200:
        return {"ok": False, "error": f"HTTP {resp.status_code}: {resp.text[:200]}"}

    data = resp.json()
    if data.get("code") != "000000":
        return {"ok": False, "error": data.get("message", "Unknown Binance error")}

    return {
        "ok": True,
        "data": data.get("data", []),
        "total": data.get("total", 0),
    }
