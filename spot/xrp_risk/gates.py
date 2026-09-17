"""
The seven gates governing whether XRP swing may auto-open a position.

Each one used to be a sequential `if: return early` inside `run_auto_cycle` —
correct, but only testable by driving the whole function through a specific
sequence of state. Broken out here, each gate is testable against a
one-line fabricated context, and — the property that matters most — every
gate runs on every proposal, not just the first one to fail. A rejected
proposal shows every reason it was rejected, not just whichever check
happened to run first.
"""
from __future__ import annotations

from spot.xrp_risk.checks import Check, passed, vetoed
from spot.xrp_risk.context import RiskContext
from spot.xrp_risk.proposal import OpenProposal
from spot.xrp_risk.reasons import VetoReason


def no_duplicate_position(proposal: OpenProposal, ctx: RiskContext) -> Check:
    """
    One XRP swing position at a time.

    Structurally, `run_auto_cycle` never reaches the open-decision while a
    trade is active — this asserts the invariant explicitly rather than
    trusting that control flow, so a future call site can't accidentally
    open a second position by skipping the caller's own check.
    """
    if not ctx.has_active_trade:
        return passed("no_duplicate_position")
    return vetoed(
        "no_duplicate_position",
        VetoReason.DUPLICATE_POSITION,
        "a trade is already open",
    )


def not_in_cooldown(proposal: OpenProposal, ctx: RiskContext) -> Check:
    """No new entry immediately after a stop-loss or trailing-stop close."""
    if not ctx.in_cooldown:
        return passed("not_in_cooldown")
    remaining_h = (ctx.cooldown_until - ctx.now).total_seconds() / 3600
    return vetoed(
        "not_in_cooldown",
        VetoReason.COOLDOWN_ACTIVE,
        f"cooldown active — {remaining_h:.1f}h remaining",
    )


def setup_not_already_consumed(proposal: OpenProposal, ctx: RiskContext) -> Check:
    """Refuse to open twice off the same 4H evaluation."""
    if proposal.eval_id is None or proposal.eval_id != ctx.last_opened_eval_id:
        return passed("setup_not_already_consumed")
    return vetoed(
        "setup_not_already_consumed",
        VetoReason.SETUP_ALREADY_CONSUMED,
        f"evaluation #{proposal.eval_id} already produced an entry",
    )


def evaluation_is_fresh(proposal: OpenProposal, ctx: RiskContext) -> Check:
    """The stored evaluation must be recent enough that conditions haven't
    plausibly moved since it was computed."""
    if proposal.evaluated_at is None:
        return vetoed(
            "evaluation_is_fresh", VetoReason.EVALUATION_STALE, "no evaluation timestamp"
        )
    # Normalise naive/aware mismatch: stored durations from the DB come back naive
    # (datetime.utcnow() default in the model) while ctx.now is timezone-aware.
    # Subtracting them directly raised a TypeError on every auto-cycle, which the
    # fail-closed supervisor translated into a spurious veto. Treat any naive
    # timestamp as UTC before computing the age.
    evaluated_at = proposal.evaluated_at
    now = ctx.now
    if evaluated_at.tzinfo is None:
        from datetime import timezone as _tz
        evaluated_at = evaluated_at.replace(tzinfo=_tz.utc)
    if now.tzinfo is None:
        from datetime import timezone as _tz
        now = now.replace(tzinfo=_tz.utc)
    age_h = (now - evaluated_at).total_seconds() / 3600
    if age_h <= ctx.max_evaluation_age_hours:
        return passed("evaluation_is_fresh", f"{age_h:.1f}h old")
    return vetoed(
        "evaluation_is_fresh",
        VetoReason.EVALUATION_STALE,
        f"evaluation is {age_h:.0f}h old, limit is {ctx.max_evaluation_age_hours:.0f}h",
    )


def verdict_is_entry_ready(proposal: OpenProposal, ctx: RiskContext) -> Check:
    """The 3-layer evaluation must actually have reached ENTRY_READY."""
    if proposal.verdict == "ENTRY_READY":
        return passed("verdict_is_entry_ready")
    return vetoed(
        "verdict_is_entry_ready",
        VetoReason.VERDICT_NOT_READY,
        f"verdict is {proposal.verdict} ({proposal.score}/100), not ENTRY_READY",
    )


def live_price_available(proposal: OpenProposal, ctx: RiskContext) -> Check:
    """Never price an entry off a stale evaluation price when the live
    streamer has nothing to offer."""
    if ctx.live_price is not None:
        return passed("live_price_available", f"${ctx.live_price:.4f}")
    return vetoed(
        "live_price_available", VetoReason.NO_LIVE_PRICE, "no live XRP price from the streamer"
    )


def reward_risk_sufficient(proposal: OpenProposal, ctx: RiskContext) -> Check:
    """Reject setups where the stop sits too close to TP1 to justify the risk."""
    if proposal.rr_ratio >= ctx.min_rr_ratio:
        return passed("reward_risk_sufficient", f"R:R {proposal.rr_ratio:.2f}")
    return vetoed(
        "reward_risk_sufficient",
        VetoReason.RISK_REWARD_TOO_LOW,
        f"R:R {proposal.rr_ratio:.2f} below the {ctx.min_rr_ratio:.2f} floor — "
        f"stop ${proposal.stop:.4f} vs TP1 ${proposal.tp1:.4f}",
    )


GATES: tuple = (
    no_duplicate_position,
    not_in_cooldown,
    setup_not_already_consumed,
    evaluation_is_fresh,
    verdict_is_entry_ready,
    live_price_available,
    reward_risk_sufficient,
)
