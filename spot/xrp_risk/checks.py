"""
The gate protocol — domain-agnostic, XRP swing is just the first user.

A gate is a pure function of (proposal, context) returning a Check: no
network, no clock, no database. That constraint is what makes every veto
reason testable against a fabricated context rather than against whatever
the market happens to be doing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from spot.xrp_risk.context import RiskContext
from spot.xrp_risk.proposal import OpenProposal
from spot.xrp_risk.reasons import VetoReason


@dataclass(frozen=True)
class Check:
    """One gate's verdict on one proposal."""

    gate: str
    passed: bool
    reason: VetoReason | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.passed and self.reason is None:
            raise ValueError(f"gate {self.gate!r} vetoed without naming a reason")

    def to_dict(self) -> dict:
        return {
            "gate": self.gate,
            "passed": self.passed,
            "reason": self.reason.value if self.reason else None,
            "detail": self.detail,
        }


def passed(gate: str, detail: str = "") -> Check:
    return Check(gate=gate, passed=True, detail=detail)


def vetoed(gate: str, reason: VetoReason, detail: str) -> Check:
    return Check(gate=gate, passed=False, reason=reason, detail=detail)


class Gate(Protocol):
    __name__: str

    def __call__(self, proposal: OpenProposal, ctx: RiskContext) -> Check: ...
