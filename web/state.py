"""
In-memory platform state shared across all web routes.
In Phase 2 this will be persisted to the database on every change.
"""
from __future__ import annotations

from config import OperatingMode, Availability, get_config


class PlatformState:
    def __init__(self):
        cfg = get_config()
        self.mode: OperatingMode = cfg.operating_mode
        self.availability: Availability = cfg.availability

    def set_mode(self, mode: OperatingMode) -> None:
        self.mode = mode

    def set_availability(self, availability: Availability) -> None:
        self.availability = availability


_state: PlatformState | None = None


def get_state() -> PlatformState:
    global _state
    if _state is None:
        _state = PlatformState()
    return _state


def reset_state() -> None:
    global _state
    _state = None
