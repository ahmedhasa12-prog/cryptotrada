"""
The typed proposal to open a new XRP swing position.

Everything the gates need to judge an auto-open, gathered in one place rather
than read piecemeal from the `setup`/`params` dicts scattered through
`run_auto_cycle`. This is the contract between the evaluation layer
(`evaluate_setup`, `_auto_params` — which decide *what* to propose) and the
risk supervisor (which decides whether it is *wise* to act on it).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OpenProposal:
    """A candidate auto-open, as computed by `_auto_params` for the latest
    stored evaluation."""

    eval_id: int | None
    evaluated_at: datetime | None
    verdict: str
    score: int

    setup_type: str
    entry_price: float | None
    requested_size_usd: float

    stop: float
    tp1: float
    tp2: float
    tp3: float
    rr_ratio: float

    def describe(self) -> str:
        # entry_price is None exactly when no price was available anywhere —
        # the case the no_live_price gate exists for. describe() still needs
        # to render that proposal for the log line and the audit trail.
        price = f"${self.entry_price:.4f}" if self.entry_price is not None else "no price"
        return (
            f"Setup {self.setup_type} @ {price} | "
            f"stop ${self.stop:.4f} | TP1 ${self.tp1:.4f} | R:R {self.rr_ratio:.2f} | "
            f"${self.requested_size_usd:.0f} requested"
        )
