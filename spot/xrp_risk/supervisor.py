"""
The XRP swing risk supervisor.

`run_auto_cycle` proposes; this disposes. Every gate runs on every proposal —
no short-circuiting on the first failure — so a refused proposal's audit
trail shows every reason it was refused, not just whichever check happened to
run first. A gate that raises is treated as a veto, not a pass: a broken rule
must never become an open door.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from loguru import logger

from data.database import get_session
from data.models import XRPRiskDecision
from spot.xrp_risk.checks import Check, Gate
from spot.xrp_risk.context import RiskContext
from spot.xrp_risk.gates import GATES
from spot.xrp_risk.proposal import OpenProposal
from spot.xrp_risk.reasons import VetoReason


@dataclass(frozen=True)
class Verdict:
    approved: bool
    checks: tuple[Check, ...]

    @property
    def failures(self) -> tuple[Check, ...]:
        return tuple(c for c in self.checks if not c.passed)

    @property
    def reason(self) -> VetoReason | None:
        """The primary veto reason — the first gate to object, in GATES order."""
        return self.failures[0].reason if self.failures else None

    @property
    def detail(self) -> str:
        if self.approved:
            return "approved"
        return "; ".join(c.detail for c in self.failures)

    @property
    def checks_json(self) -> str:
        return json.dumps([c.to_dict() for c in self.checks])


def review(proposal: OpenProposal, ctx: RiskContext, gates: tuple[Gate, ...] = GATES) -> Verdict:
    """Run every gate against a proposal and return the combined verdict."""
    checks: list[Check] = []
    for gate in gates:
        try:
            checks.append(gate(proposal, ctx))
        except Exception as e:  # a crashing gate must fail closed, not open
            logger.exception(f"XRP risk gate {gate.__name__} raised")
            checks.append(
                Check(
                    gate=gate.__name__,
                    passed=False,
                    reason=VetoReason.NO_LIVE_PRICE,  # least-wrong generic reason
                    detail=f"gate raised {type(e).__name__}: {e}",
                )
            )

    verdict = Verdict(approved=all(c.passed for c in checks), checks=tuple(checks))
    if verdict.approved:
        logger.info(f"XRP risk: APPROVED {proposal.describe()}")
    else:
        logger.info(
            f"XRP risk: VETOED {proposal.describe()} — {verdict.reason.value}: "
            f"{verdict.failures[0].detail}"
        )
    return verdict


def persist(
    proposal: OpenProposal,
    verdict: Verdict,
    *,
    final_size_usd: float | None = None,
    shadowed: bool = False,
) -> None:
    """
    Record the decision, approved or not.

    `final_size_usd` is filled in only when the trade actually opens, after
    the risk-budget sizing step downstream — the gates themselves don't
    reject on size, they only gate whether opening is wise at all.

    `shadowed=True` marks an approved decision that was logged but never sent
    to open_trade() — meaningless when the verdict was a veto.
    """
    with get_session() as s:
        s.add(
            XRPRiskDecision(
                setup_type=proposal.setup_type,
                eval_id=proposal.eval_id,
                entry_price=proposal.entry_price,
                requested_size_usd=proposal.requested_size_usd,
                final_size_usd=final_size_usd,
                stop=proposal.stop,
                tp1=proposal.tp1,
                tp2=proposal.tp2,
                tp3=proposal.tp3,
                rr_ratio=proposal.rr_ratio,
                approved=verdict.approved,
                veto_reason=verdict.reason.value if verdict.reason else None,
                detail=verdict.detail,
                checks_json=verdict.checks_json,
                shadowed=shadowed,
            )
        )
