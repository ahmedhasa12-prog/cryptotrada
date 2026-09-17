"""
The world as the XRP swing risk supervisor sees it.

A plain snapshot, no live clients attached — assembling one from the database
and the clock is `spot.xrp_swing`'s job, not the gates'. That split is what
lets every gate be tested against a fabricated context with no DB and no
patched clock.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class RiskContext:
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    has_active_trade: bool = False
    cooldown_until: datetime | None = None
    last_opened_eval_id: int | None = None

    live_price: float | None = None

    # How old a stored evaluation may be before it's refused as stale, and the
    # reward:risk floor below which a setup isn't worth the capital. Module
    # constants rather than a settings object — matching this codebase's
    # existing style (spot/xrp_swing.py's _COOLDOWN_HOURS, _RISK_BUDGET_USD)
    # rather than importing a new configuration pattern for one strategy.
    max_evaluation_age_hours: float = 24.0
    min_rr_ratio: float = 2.0

    @property
    def in_cooldown(self) -> bool:
        return self.cooldown_until is not None and self.now < self.cooldown_until
