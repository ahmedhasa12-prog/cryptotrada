"""
XRP swing risk supervisor tests — one per veto reason, plus the invariants.

These seven gates used to be sequential early-returns inside run_auto_cycle,
correct but only reachable by driving the whole function through a specific
sequence of state. Each one gets its own test here, isolated from the 4H
evaluation, the streamer, and the database entirely.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from spot.xrp_risk.context import RiskContext
from spot.xrp_risk.proposal import OpenProposal
from spot.xrp_risk.reasons import VetoReason
from spot.xrp_risk.supervisor import GATES, review

NOW = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)


def make_proposal(**overrides) -> OpenProposal:
    """A setup that passes every gate. Break one field per test."""
    defaults = dict(
        eval_id=42,
        evaluated_at=NOW - timedelta(hours=1),
        verdict="ENTRY_READY",
        score=85,
        setup_type="B",
        entry_price=0.9200,
        requested_size_usd=300.0,
        stop=0.9061,
        tp1=1.0000,
        tp2=1.2500,
        tp3=1.3800,
        rr_ratio=1.8,
    )
    return OpenProposal(**{**defaults, **overrides})


def make_context(**overrides) -> RiskContext:
    """A clean context: no active trade, no cooldown, fresh eval, live price."""
    defaults = dict(
        now=NOW,
        has_active_trade=False,
        cooldown_until=None,
        last_opened_eval_id=None,
        live_price=0.9200,
    )
    return RiskContext(**{**defaults, **overrides})


def assert_vetoed_for(proposal, ctx, reason: VetoReason):
    verdict = review(proposal, ctx)
    assert not verdict.approved, f"expected a veto for {reason.value}"
    assert reason in {c.reason for c in verdict.failures}, (
        f"expected {reason.value}, got {[c.reason.value for c in verdict.failures]}"
    )
    return verdict


# ══════════════════════════════════════════════════════════════════════════════
# The baseline must pass, or every test below is meaningless
# ══════════════════════════════════════════════════════════════════════════════

def test_a_good_proposal_is_approved():
    verdict = review(make_proposal(), make_context())
    assert verdict.approved
    assert verdict.reason is None


def test_approval_runs_every_gate():
    """No short-circuiting: the audit trail must be complete."""
    verdict = review(make_proposal(), make_context())
    assert len(verdict.checks) == len(GATES)


# ══════════════════════════════════════════════════════════════════════════════
# One per veto reason
# ══════════════════════════════════════════════════════════════════════════════

def test_duplicate_position():
    assert_vetoed_for(
        make_proposal(), make_context(has_active_trade=True), VetoReason.DUPLICATE_POSITION
    )


def test_cooldown_active():
    ctx = make_context(cooldown_until=NOW + timedelta(hours=2))
    assert_vetoed_for(make_proposal(), ctx, VetoReason.COOLDOWN_ACTIVE)


def test_cooldown_expired_is_not_a_veto():
    """A cooldown that has already elapsed must not block re-entry."""
    ctx = make_context(cooldown_until=NOW - timedelta(minutes=1))
    assert review(make_proposal(), ctx).approved


def test_setup_already_consumed():
    ctx = make_context(last_opened_eval_id=42)
    assert_vetoed_for(make_proposal(eval_id=42), ctx, VetoReason.SETUP_ALREADY_CONSUMED)


def test_different_eval_id_is_not_a_veto():
    ctx = make_context(last_opened_eval_id=41)
    assert review(make_proposal(eval_id=42), ctx).approved


def test_evaluation_stale():
    assert_vetoed_for(
        make_proposal(evaluated_at=NOW - timedelta(hours=6)),
        make_context(),
        VetoReason.EVALUATION_STALE,
    )


def test_evaluation_with_no_timestamp_is_stale():
    """Unmeasurable must never mean acceptable."""
    assert_vetoed_for(
        make_proposal(evaluated_at=None), make_context(), VetoReason.EVALUATION_STALE
    )


def test_verdict_not_ready():
    assert_vetoed_for(
        make_proposal(verdict="SETUP_FORMING", score=40),
        make_context(),
        VetoReason.VERDICT_NOT_READY,
    )


def test_no_live_price():
    assert_vetoed_for(
        make_proposal(), make_context(live_price=None), VetoReason.NO_LIVE_PRICE
    )


def test_risk_reward_too_low():
    assert_vetoed_for(
        make_proposal(rr_ratio=1.2), make_context(), VetoReason.RISK_REWARD_TOO_LOW
    )


def test_risk_reward_exactly_at_the_floor_passes():
    """The floor itself is inclusive — 1.5 is acceptable, not just >1.5."""
    ctx = make_context()
    assert review(make_proposal(rr_ratio=1.5), ctx).approved


# ══════════════════════════════════════════════════════════════════════════════
# Invariants
# ══════════════════════════════════════════════════════════════════════════════

def test_every_veto_reason_has_a_test():
    """Fails the moment a reason is added without a test provoking it."""
    import inspect
    import tests.test_xrp_risk as self_module

    source = inspect.getsource(self_module)
    untested = [r.value for r in VetoReason if f"VetoReason.{r.name}" not in source]
    assert not untested, f"veto reasons with no test: {untested}"


def test_a_crashing_gate_fails_closed():
    def exploding_gate(proposal, ctx):
        raise RuntimeError("boom")

    exploding_gate.__name__ = "exploding_gate"
    verdict = review(make_proposal(), make_context(), gates=(exploding_gate,))
    assert not verdict.approved
    assert "boom" in verdict.detail


def test_multiple_failures_are_all_reported():
    """The point of running every gate is seeing every objection, not just
    whichever one happened to run first."""
    verdict = review(
        make_proposal(verdict="WATCHING", rr_ratio=1.0, evaluated_at=NOW - timedelta(hours=9)),
        make_context(),
    )
    reasons = {c.reason for c in verdict.failures}
    assert {
        VetoReason.EVALUATION_STALE,
        VetoReason.VERDICT_NOT_READY,
        VetoReason.RISK_REWARD_TOO_LOW,
    } <= reasons


def test_every_gate_appears_exactly_once():
    names = [g.__name__ for g in GATES]
    assert len(names) == len(set(names))


def test_every_failure_names_a_reason():
    verdict = review(make_proposal(verdict="WATCHING", rr_ratio=0.5), make_context())
    assert verdict.failures
    assert all(c.reason is not None for c in verdict.failures)


def test_describe_handles_a_missing_entry_price():
    """entry_price is None exactly when no price was available anywhere — the
    scenario no_live_price exists for. describe() must render that proposal
    for the log line and audit trail, not crash formatting None as a float."""
    proposal = make_proposal(entry_price=None, stop=0.0, tp1=0.0, rr_ratio=0.0)
    assert "no price" in proposal.describe()

    verdict = review(proposal, make_context(live_price=None))
    assert not verdict.approved
    assert VetoReason.NO_LIVE_PRICE in {c.reason for c in verdict.failures}
