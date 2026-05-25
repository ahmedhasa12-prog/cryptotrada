"""
Trader Risk Scorer — scores incoming P2P traders 0-100.

Scoring is pure Python logic with no external calls.
Personal history is loaded from the database.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from loguru import logger

from data.database import get_session
from data.models import TraderHistory


class RiskColor(str, Enum):
    GREEN = "green"    # 75-100  — auto-recommend accept
    YELLOW = "yellow"  # 50-74   — manual review
    RED = "red"        # 0-49    — recommend decline


@dataclass
class TraderProfile:
    username: str
    total_trades: int
    completion_rate: float    # 0.0 – 100.0
    positive_feedback_pct: float  # 0.0 – 100.0
    account_age_days: int
    kyc_verified: bool = False
    order_amount_usdt: float = 0.0
    typical_order_usdt: float = 0.0   # their usual order size; 0 = unknown


@dataclass
class ScoreResult:
    score: int
    color: RiskColor
    recommendation: str
    reasons: list[str]
    personal_history: TraderHistory | None


def _load_history(username: str) -> TraderHistory | None:
    try:
        with get_session() as s:
            record = s.query(TraderHistory).filter_by(username=username).first()
            if record is not None:
                s.expunge(record)
            return record
    except RuntimeError:
        # DB not initialised (e.g. early tests)
        return None


def score_trader(
    profile: TraderProfile,
    *,
    history: TraderHistory | None = None,
    load_from_db: bool = True,
) -> ScoreResult:
    """
    Score a trader based on their Binance profile and personal history.

    Pass `history` directly in tests; set `load_from_db=False` to skip DB lookup.
    """
    if load_from_db and history is None:
        history = _load_history(profile.username)

    score = 50
    reasons: list[str] = []
    hard_cap: int | None = None  # enforced at final clamp

    # ── personal history (applied first — can be decisive) ───────────────────
    if history is not None:
        if history.flagged:
            score -= 40
            reasons.append("Previously flagged — strong decline recommendation.")
            hard_cap = 49  # flagged traders are always RED regardless of profile stats
        elif history.disputed > 0:
            score -= 30
            reasons.append(f"Has {history.disputed} dispute(s) in personal history.")
        elif history.total_trades > 0:
            score += 15
            reasons.append("Previously traded with us successfully.")

    # ── dispute history from Binance profile ─────────────────────────────────
    # (Binance doesn't expose this directly; we treat completion_rate < 85 as proxy)

    # ── trade volume ─────────────────────────────────────────────────────────
    if profile.total_trades > 500:
        score += 15
        reasons.append(f"High trade count: {profile.total_trades}.")
    elif profile.total_trades >= 100:
        score += 10
        reasons.append(f"Good trade count: {profile.total_trades}.")
    elif profile.total_trades >= 20:
        score += 5
        reasons.append(f"Moderate trade count: {profile.total_trades}.")
    elif profile.total_trades < 5:
        score -= 20
        reasons.append(f"Very few trades: {profile.total_trades}.")

    # ── completion rate ───────────────────────────────────────────────────────
    if profile.completion_rate >= 98:
        score += 15
        reasons.append(f"Excellent completion rate: {profile.completion_rate:.1f}%.")
    elif profile.completion_rate >= 95:
        score += 10
        reasons.append(f"Good completion rate: {profile.completion_rate:.1f}%.")
    elif profile.completion_rate >= 90:
        score += 5
        reasons.append(f"Acceptable completion rate: {profile.completion_rate:.1f}%.")
    elif profile.completion_rate < 85:
        score -= 20
        reasons.append(f"Poor completion rate: {profile.completion_rate:.1f}%.")

    # ── positive feedback ─────────────────────────────────────────────────────
    if profile.positive_feedback_pct > 99:
        score += 10
        reasons.append(f"Excellent feedback: {profile.positive_feedback_pct:.1f}%.")

    # ── account age ───────────────────────────────────────────────────────────
    if profile.account_age_days > 180:
        score += 10
        reasons.append(f"Established account: {profile.account_age_days} days old.")
    elif profile.account_age_days >= 90:
        score += 5
        reasons.append(f"Moderately established: {profile.account_age_days} days old.")
    elif profile.account_age_days < 30:
        score -= 25
        reasons.append(f"Very new account: {profile.account_age_days} days old.")

    # ── KYC ──────────────────────────────────────────────────────────────────
    if profile.kyc_verified:
        score += 5
        reasons.append("KYC verified.")

    # ── order size anomaly ────────────────────────────────────────────────────
    if profile.typical_order_usdt > 0 and profile.order_amount_usdt > 0:
        ratio = profile.order_amount_usdt / profile.typical_order_usdt
        if ratio > 3.0:
            score -= 10
            reasons.append(
                f"Order size ({profile.order_amount_usdt:.0f} USDT) is "
                f"{ratio:.1f}× their usual ({profile.typical_order_usdt:.0f} USDT)."
            )

    # ── clamp ────────────────────────────────────────────────────────────────
    score = max(0, min(100, score))
    if hard_cap is not None:
        score = min(score, hard_cap)

    # ── color + recommendation ────────────────────────────────────────────────
    if score >= 75:
        color = RiskColor.GREEN
        recommendation = "ACCEPT"
    elif score >= 50:
        color = RiskColor.YELLOW
        recommendation = "REVIEW"
    else:
        color = RiskColor.RED
        recommendation = "DECLINE"

    logger.debug(f"Scored trader {profile.username}: {score}/100 ({color.value})")

    return ScoreResult(
        score=score,
        color=color,
        recommendation=recommendation,
        reasons=reasons,
        personal_history=history,
    )


def color_emoji(color: RiskColor) -> str:
    return {"green": "🟢", "yellow": "🟡", "red": "🔴"}[color.value]


def upsert_trader_history(
    username: str,
    successful: bool = True,
    disputed: bool = False,
    notes: str = "",
) -> None:
    """Update or create a trader history record after a completed trade."""
    from datetime import datetime

    with get_session() as s:
        record = s.query(TraderHistory).filter_by(username=username).first()
        now = datetime.utcnow()
        if record is None:
            record = TraderHistory(
                username=username,
                first_trade=now,
                last_trade=now,
                total_trades=1,
                successful=1 if successful else 0,
                disputed=1 if disputed else 0,
                flagged=disputed,
                notes=notes,
            )
            s.add(record)
        else:
            record.last_trade = now
            record.total_trades += 1
            if successful:
                record.successful += 1
            if disputed:
                record.disputed += 1
                record.flagged = True
            if notes:
                record.notes = (record.notes or "") + f"\n{now.date()}: {notes}"
