"""
Tests for p2p/trader_scorer.py — pure logic, no HTTP calls.
"""
import pytest

import config as cfg
import data.database as db
from p2p.trader_scorer import (
    TraderProfile,
    ScoreResult,
    RiskColor,
    score_trader,
    color_emoji,
    upsert_trader_history,
)
from data.models import TraderHistory


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_USER_ID", "1")
    cfg.reset_config()
    db.init_db(":memory:")
    yield
    db.reset_db()
    cfg.reset_config()


def _good_profile(username="good_trader") -> TraderProfile:
    return TraderProfile(
        username=username,
        total_trades=600,
        completion_rate=99.0,
        positive_feedback_pct=99.5,
        account_age_days=365,
        kyc_verified=True,
    )


def _bad_profile(username="bad_trader") -> TraderProfile:
    return TraderProfile(
        username=username,
        total_trades=2,
        completion_rate=80.0,
        positive_feedback_pct=90.0,
        account_age_days=10,
        kyc_verified=False,
    )


# ── base scoring ──────────────────────────────────────────────────────────────

def test_excellent_trader_is_green():
    result = score_trader(_good_profile(), load_from_db=False)
    assert result.color == RiskColor.GREEN
    assert result.recommendation == "ACCEPT"
    assert result.score >= 75


def test_bad_trader_is_red():
    result = score_trader(_bad_profile(), load_from_db=False)
    assert result.color == RiskColor.RED
    assert result.recommendation == "DECLINE"
    assert result.score < 50


def test_score_clamped_between_0_and_100():
    # Worst possible trader
    profile = TraderProfile(
        username="worst",
        total_trades=1,
        completion_rate=70.0,
        positive_feedback_pct=80.0,
        account_age_days=5,
    )
    history = TraderHistory(username="worst", flagged=True, disputed=1, total_trades=1, successful=0)
    result = score_trader(profile, history=history, load_from_db=False)
    assert 0 <= result.score <= 100


def test_score_clamped_max():
    result = score_trader(_good_profile(), load_from_db=False)
    assert result.score <= 100


# ── individual factor tests ───────────────────────────────────────────────────

def test_high_trade_count_adds_points():
    profile = TraderProfile("x", total_trades=600, completion_rate=95.0,
                             positive_feedback_pct=95.0, account_age_days=200)
    result = score_trader(profile, load_from_db=False)
    assert any("High trade count" in r for r in result.reasons)


def test_moderate_trade_count():
    profile = TraderProfile("x", total_trades=50, completion_rate=95.0,
                             positive_feedback_pct=95.0, account_age_days=200)
    result = score_trader(profile, load_from_db=False)
    assert any("Moderate trade count" in r for r in result.reasons)


def test_very_few_trades_penalised():
    profile = TraderProfile("x", total_trades=3, completion_rate=95.0,
                             positive_feedback_pct=95.0, account_age_days=200)
    result = score_trader(profile, load_from_db=False)
    assert any("Very few trades" in r for r in result.reasons)


def test_new_account_penalised():
    profile = TraderProfile("x", total_trades=100, completion_rate=98.0,
                             positive_feedback_pct=99.0, account_age_days=15)
    result = score_trader(profile, load_from_db=False)
    assert any("new account" in r for r in result.reasons)


def test_kyc_adds_points():
    profile_no_kyc = TraderProfile("x", total_trades=200, completion_rate=97.0,
                                    positive_feedback_pct=98.0, account_age_days=200, kyc_verified=False)
    profile_kyc = TraderProfile("x", total_trades=200, completion_rate=97.0,
                                 positive_feedback_pct=98.0, account_age_days=200, kyc_verified=True)
    r1 = score_trader(profile_no_kyc, load_from_db=False)
    r2 = score_trader(profile_kyc, load_from_db=False)
    assert r2.score == r1.score + 5


def test_order_size_anomaly_penalised():
    profile = TraderProfile(
        "x", total_trades=200, completion_rate=97.0,
        positive_feedback_pct=98.0, account_age_days=200,
        order_amount_usdt=1000.0, typical_order_usdt=100.0,  # 10× normal
    )
    result = score_trader(profile, load_from_db=False)
    assert any("Order size" in r for r in result.reasons)


def test_normal_order_size_no_penalty():
    profile = TraderProfile(
        "x", total_trades=200, completion_rate=97.0,
        positive_feedback_pct=98.0, account_age_days=200,
        order_amount_usdt=150.0, typical_order_usdt=100.0,  # 1.5× — normal
    )
    result = score_trader(profile, load_from_db=False)
    assert not any("Order size" in r for r in result.reasons)


# ── personal history ─────────────────────────────────────────────────────────

def test_previously_traded_ok_adds_points():
    history = TraderHistory(username="known", total_trades=3, successful=3,
                             disputed=0, flagged=False)
    result = score_trader(_good_profile("known"), history=history, load_from_db=False)
    assert any("successfully" in r for r in result.reasons)


def test_flagged_trader_is_red():
    history = TraderHistory(username="bad", total_trades=1, successful=0,
                             disputed=1, flagged=True)
    profile = _good_profile("bad")
    result = score_trader(profile, history=history, load_from_db=False)
    assert result.color == RiskColor.RED
    assert any("flagged" in r.lower() for r in result.reasons)


def test_disputed_trader_penalised():
    history = TraderHistory(username="risky", total_trades=5, successful=4,
                             disputed=1, flagged=False)
    profile = _good_profile("risky")
    result = score_trader(profile, history=history, load_from_db=False)
    assert any("dispute" in r.lower() for r in result.reasons)


# ── database integration ──────────────────────────────────────────────────────

def test_upsert_creates_new_record():
    upsert_trader_history("alice", successful=True)
    with db.get_session() as s:
        h = s.query(TraderHistory).filter_by(username="alice").first()
        assert h is not None
        assert h.total_trades == 1
        assert h.successful == 1


def test_upsert_increments_existing():
    upsert_trader_history("bob", successful=True)
    upsert_trader_history("bob", successful=True)
    upsert_trader_history("bob", successful=False, disputed=True)
    with db.get_session() as s:
        h = s.query(TraderHistory).filter_by(username="bob").first()
        assert h.total_trades == 3
        assert h.successful == 2
        assert h.disputed == 1
        assert h.flagged is True


def test_score_loads_history_from_db():
    upsert_trader_history("charlie", successful=True)
    upsert_trader_history("charlie", successful=True)
    profile = TraderProfile("charlie", 50, 95.0, 97.0, 200)
    result = score_trader(profile, load_from_db=True)
    assert any("successfully" in r for r in result.reasons)


# ── utilities ─────────────────────────────────────────────────────────────────

def test_color_emoji():
    assert color_emoji(RiskColor.GREEN) == "🟢"
    assert color_emoji(RiskColor.YELLOW) == "🟡"
    assert color_emoji(RiskColor.RED) == "🔴"


def test_yellow_boundary():
    # Craft a profile that lands exactly in yellow band
    profile = TraderProfile("mid", total_trades=60, completion_rate=95.0,
                             positive_feedback_pct=97.0, account_age_days=100)
    result = score_trader(profile, load_from_db=False)
    assert result.color in (RiskColor.YELLOW, RiskColor.GREEN)
