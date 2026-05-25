from __future__ import annotations

from fastapi import APIRouter

from intelligence.sdg_monitor import get_sdg_summary

router = APIRouter(prefix="/api/p2p")


@router.get("/rate-trend")
def get_rate_trend() -> dict:
    return get_sdg_summary()
