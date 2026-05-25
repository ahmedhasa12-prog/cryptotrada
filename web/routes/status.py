from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from config import OperatingMode, Availability
from data.database import get_session
from data.models import SystemEvent
from web.state import get_state

router = APIRouter(prefix="/api")


class StatusResponse(BaseModel):
    mode: str
    availability: str


class SetModeRequest(BaseModel):
    mode: str


class SetAvailabilityRequest(BaseModel):
    availability: str


@router.get("/status", response_model=StatusResponse)
def get_status():
    state = get_state()
    return StatusResponse(mode=state.mode.value, availability=state.availability.value)


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

    return StatusResponse(mode=state.mode.value, availability=state.availability.value)


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

    return StatusResponse(mode=state.mode.value, availability=state.availability.value)
