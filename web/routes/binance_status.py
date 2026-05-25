"""GET /api/binance/status — verify Binance API key is reachable and valid."""
from __future__ import annotations

from fastapi import APIRouter

from binance.client import verify_connection

router = APIRouter()


@router.get("/api/binance/status")
async def binance_status() -> dict:
    return await verify_connection()
