from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from config import OperatingMode, Availability
from data.database import get_session
from data.models import SystemEvent
from web.state import get_state
from spot.trading_modes import TradingMode, get_trading_mode, set_trading_mode as _set_trading_mode
from solana_trader import get_solana_status

router = APIRouter(prefix="/api")


class StatusResponse(BaseModel):
    mode: str
    availability: str
    trading_mode: str
    solana_agent: str = "unknown"
    solana_price: float | None = None
    solana_max_positions: int = 3
    solana_risk_pct: float = 0.0
    solana_min_rr: float = 2.0


class SetModeRequest(BaseModel):
    mode: str


class SetAvailabilityRequest(BaseModel):
    availability: str


class SetTradingModeRequest(BaseModel):
    trading_mode: str


@router.get("/status", response_model=StatusResponse)
def get_status():
    state = get_state()
    trading_mode = get_trading_mode()
    sol = get_solana_status()
    return StatusResponse(
        mode=state.mode.value,
        availability=state.availability.value,
        trading_mode=trading_mode.value,
        solana_agent=sol["solana_agent"],
        solana_price=sol["solana_price"],
        solana_max_positions=sol["solana_max_positions"],
        solana_risk_pct=sol["solana_risk_pct"],
        solana_min_rr=sol["solana_min_rr"],
    )


@router.post("/mode", response_model=StatusResponse)
def set_mode(req: SetModeRequest):
    try:
        new_mode = OperatingMode(req.mode)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid mode: {req.mode}")

    state = get_state()
    old = state.mode
    state.set_mode(new_mode)

    with get_session() as s:
        s.add(SystemEvent(
            event_type="mode_change",
            description=f"Mode changed from {old.value} to {new_mode.value}",
            mode=new_mode.value,
        ))

    return StatusResponse(
        mode=state.mode.value,
        availability=state.availability.value,
        trading_mode=get_trading_mode().value
    )


@router.post("/availability", response_model=StatusResponse)
def set_availability(req: SetAvailabilityRequest):
    try:
        new_avail = Availability(req.availability)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid availability: {req.availability}")

    state = get_state()
    state.set_availability(new_avail)

    with get_session() as s:
        s.add(SystemEvent(
            event_type="availability_change",
            description=f"Availability set to {new_avail.value}",
            mode=state.mode.value,
        ))

    return StatusResponse(
        mode=state.mode.value,
        availability=state.availability.value,
        trading_mode=get_trading_mode().value
    )


@router.post("/trading-mode", response_model=StatusResponse)
def set_trading_mode_route(req: SetTradingModeRequest):
    try:
        new_mode = TradingMode(req.trading_mode)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=f"Invalid trading mode: {req.trading_mode}")

    _set_trading_mode(new_mode)

    state = get_state()
    with get_session() as s:
        s.add(SystemEvent(
            event_type="trading_mode_change",
            description=f"Trading mode changed to {new_mode.value}",
            mode=new_mode.value,
        ))

    return StatusResponse(
        mode=state.mode.value,
        availability=state.availability.value,
        trading_mode=get_trading_mode().value
    )
