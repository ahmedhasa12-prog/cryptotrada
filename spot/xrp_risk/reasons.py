"""
Every reason the XRP swing risk supervisor may refuse to open a trade.

Before this existed, these seven checks were sequential `if: return early`
statements buried in `run_auto_cycle` — correct, but untestable in isolation
and invisible to anything outside a log line. Each one becomes a named gate
here with its own test, so refusing a trade is an auditable decision rather
than a side effect of control flow.

`explain` is written for the dashboard and the alert feed, not a log grep —
this is meant to be read by a human deciding whether to trust the bot.
"""
from __future__ import annotations

from enum import Enum


class VetoReason(str, Enum):
    DUPLICATE_POSITION = "duplicate_position"
    COOLDOWN_ACTIVE = "cooldown_active"
    SETUP_ALREADY_CONSUMED = "setup_already_consumed"
    EVALUATION_STALE = "evaluation_stale"
    VERDICT_NOT_READY = "verdict_not_ready"
    NO_LIVE_PRICE = "no_live_price"
    RISK_REWARD_TOO_LOW = "risk_reward_too_low"

    @property
    def explain(self) -> str:
        return _EXPLANATIONS[self]


_EXPLANATIONS: dict[VetoReason, str] = {
    VetoReason.DUPLICATE_POSITION:
        "A trade is already open. One XRP swing position at a time — a second "
        "would be doubling down, not diversifying.",
    VetoReason.COOLDOWN_ACTIVE:
        "In cooldown after a stop-loss or trailing-stop close. Re-entering "
        "immediately after a loss is how a strategy compounds one bad read "
        "into several.",
    VetoReason.SETUP_ALREADY_CONSUMED:
        "This 4H evaluation already produced an entry. Waiting for a fresh "
        "candle rather than opening twice off the same read.",
    VetoReason.EVALUATION_STALE:
        "The stored evaluation is too old to act on — conditions may have "
        "moved since it was computed.",
    VetoReason.VERDICT_NOT_READY:
        "The 3-layer evaluation has not reached ENTRY_READY yet.",
    VetoReason.NO_LIVE_PRICE:
        "No live XRP price available to price the entry against.",
    VetoReason.RISK_REWARD_TOO_LOW:
        "Reward-to-risk on this setup is below the 1.5 floor — the stop is "
        "too close to TP1 to justify the trade.",
}

_missing = set(VetoReason) - set(_EXPLANATIONS)
if _missing:  # pragma: no cover - guards against an incomplete edit
    raise RuntimeError(f"VetoReason missing explain text: {sorted(r.value for r in _missing)}")
