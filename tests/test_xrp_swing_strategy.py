"""
Direct tests of the XRP swing strategy math — _auto_params, _check_entry_trigger,
hit_tp, and close_trade. Zero of these had any coverage before this review,
which is exactly how a mismatched-branch bug (see below) and a wrong P&L
fraction survived undetected.

_auto_params is deliberately tested against BOTH of its branches, not just
one. That split is the actual root cause of this review's original
misdiagnosis: run_auto_cycle only ever exercises the fallback branch (its
`setup` dict comes from get_latest_setup(), which never carries atr_val), so
a fix or a test written against the ATR branch alone would silently test
code that never runs in production. Both are covered here so that gap
cannot reopen unnoticed.
"""
from __future__ import annotations

import pytest

import config as cfg
import data.database as db
from data.database import get_session
from data.models import XRPSwingTrade
from spot.xrp_swing import (
    XRP_SUPPORT,
    _auto_params,
    _check_entry_trigger,
    close_trade,
    hit_tp,
)


@pytest.fixture(autouse=True)
def setup():
    cfg.reset_config()
    db.init_db(":memory:")
    yield
    db.reset_db()
    cfg.reset_config()


# ══════════════════════════════════════════════════════════════════════════════
# _auto_params — the fallback branch (what run_auto_cycle actually executes)
# ══════════════════════════════════════════════════════════════════════════════
# setup dicts here deliberately omit atr_val, mirroring get_latest_setup()'s
# real shape — this is what makes it the fallback branch, not a fixture
# oversight.

def test_fallback_branch_reproduces_the_real_historical_signal():
    """Regression lock for this review's actual finding: the 14-15 Aug signal
    at $0.9989 computes to R:R 3.97 and passes, not the 0.667-always the
    original (wrong) diagnosis claimed."""
    setup = {"setup_type": "B", "xrp_ema200": None}
    p = _auto_params(setup, 0.9989, 300.0)
    assert p["stop"] == pytest.approx(0.9357, abs=0.001)
    assert p["tp1"] == pytest.approx(1.25)
    assert p["rr_ratio"] == pytest.approx(3.97, abs=0.01)
    assert p["rr_ok"] is True


def test_fallback_branch_can_fail_the_rr_gate_too():
    """Not every price passes — deep in a support/resistance band, R:R
    degrades well below the gate. Both outcomes are real, not a fixed
    constant. Not pinning an exact ratio here: it is sensitive to exactly
    where price sits relative to the support/resistance grid, and the
    point of this test is that it CAN fail, not a specific number — that
    precise regression lock belongs to the $0.9989 case above, where the
    grid position is exact."""
    setup = {"setup_type": "B", "xrp_ema200": None}
    p = _auto_params(setup, 1.5014, 300.0)
    assert p["rr_ratio"] < 1.5
    assert p["rr_ok"] is False


def test_fallback_branch_setup_a_stops_below_ema200():
    """Setup A's stop is EMA-anchored, not support-anchored, when EMA200 is
    available. Regression lock for a real key-mismatch bug this review
    found: the fallback branch read setup["ema200"], but
    get_latest_setup() — what run_auto_cycle actually passes in — returns
    that field as "xrp_ema200". The mismatch meant Setup A's stop silently
    always fell through to the support-based fallback in production, never
    the EMA-anchored logic this branch exists for. Both key spellings are
    tested since _auto_params has two real callers using each."""
    setup = {"setup_type": "A", "xrp_ema200": 1.10}
    p = _auto_params(setup, 1.14, 300.0)
    assert p["stop"] == pytest.approx(1.10 * 0.99, abs=0.001)

    setup_live = {"setup_type": "A", "ema200": 1.10}
    p_live = _auto_params(setup_live, 1.14, 300.0)
    assert p_live["stop"] == pytest.approx(1.10 * 0.99, abs=0.001)


def test_fallback_branch_defaults_to_setup_b_stop_logic_when_type_missing():
    setup = {"setup_type": None, "xrp_ema200": None}
    p = _auto_params(setup, 0.97, 300.0)
    nearest_sup = max(s for s in XRP_SUPPORT if s < 0.97)
    assert p["stop"] == pytest.approx(nearest_sup * 0.985, abs=0.001)


# ══════════════════════════════════════════════════════════════════════════════
# _auto_params — the ATR branch (reachable from evaluate_setup's live dict,
# NOT from run_auto_cycle today — see the module docstring)
# ══════════════════════════════════════════════════════════════════════════════

def test_atr_branch_rr_is_capped_at_two_thirds_by_construction():
    """This is real and was the one part of the original finding that held
    up: TP1 = 1x ATR graded against a 1.5x ATR stop is 0.667 for any ATR
    value. Documented here as a known property of the branch, not fixed,
    because nothing in production reaches this branch today."""
    for atr_pct in (1.0, 5.0, 10.0, 25.0):
        price = 1.50
        atr = price * atr_pct / 100
        setup = {
            "setup_type": "B",
            "atr_val": atr,
            "atr_pct": atr_pct,
            "dynamic_tp_levels": [price + atr, price + 2 * atr, price + 3 * atr],
        }
        p = _auto_params(setup, price, 300.0)
        assert p["rr_ratio"] == pytest.approx(0.667, abs=0.01)


# ══════════════════════════════════════════════════════════════════════════════
# _check_entry_trigger — one case per setup type
# ══════════════════════════════════════════════════════════════════════════════

def test_no_setup_means_no_trigger():
    result = _check_entry_trigger({"setup_type": None}, 1.50)
    assert result["fired"] is False


def test_setup_a_fires_on_volume_and_healthy_rsi():
    setup = {"setup_type": "A", "rsi_4h": 55, "vol_ratio_closed": 1.8}
    result = _check_entry_trigger(setup, 1.50)
    assert result["fired"] is True
    assert result["type"] == "ema_pullback"


def test_setup_a_does_not_fire_on_thin_volume():
    setup = {"setup_type": "A", "rsi_4h": 55, "vol_ratio_closed": 1.1}
    assert _check_entry_trigger(setup, 1.50)["fired"] is False


def test_setup_b_requires_a_green_closed_candle_not_just_oversold_volume():
    """The reversal-vs-continuation guard: heavy volume + low RSI on a RED
    candle is a flush, not a bounce."""
    red = {"setup_type": "B", "rsi_4h": 28, "vol_ratio_closed": 1.5, "last_closed_green": False}
    green = {**red, "last_closed_green": True}
    assert _check_entry_trigger(red, 1.0)["fired"] is False
    assert _check_entry_trigger(green, 1.0)["fired"] is True


def test_setup_c_requires_price_to_actually_break_the_upper_band():
    setup = {"setup_type": "C", "vol_ratio_closed": 2.0, "bb_upper": 1.20}
    below = _check_entry_trigger(setup, 1.19)
    above = _check_entry_trigger(setup, 1.21)
    assert below["fired"] is False
    assert above["fired"] is True


# ══════════════════════════════════════════════════════════════════════════════
# hit_tp — fraction accounting matches the documented 30/30/40 split
# ══════════════════════════════════════════════════════════════════════════════

def _open(**overrides) -> int:
    """Insert an open trade directly, bypassing open_trade() — that function's
    own price/macro/ATR lookups are out of scope for testing the P&L math
    below. Commits in its own session, matching store_setup()'s pattern in
    the sibling test file, so hit_tp/close_trade's own get_session() calls
    see the row."""
    defaults = dict(
        setup_type="B", avg_entry=1.00, total_size_usd=300.0,
        stop_initial=0.95, stop_current=0.95,
        tp1_price=1.10, tp2_price=1.20, tp3_price=1.30,
        status="open",
    )
    with get_session() as s:
        trade = XRPSwingTrade(**{**defaults, **overrides})
        s.add(trade)
        s.flush()
        return trade.id


def test_hit_tp1_banks_thirty_percent():
    tid = _open()
    hit_tp(tid, 1, 1.10)
    with get_session() as s:
        t = s.get(XRPSwingTrade, tid)
        # 10% move * 30% of $300 = $9.00
        assert t.tp1_pnl_usd == pytest.approx(9.00, abs=0.01)
        assert t.stop_at_be is True
        assert t.stop_current == pytest.approx(1.00)


def test_hit_tp2_banks_another_thirty_percent_and_arms_trailing():
    tid = _open()
    hit_tp(tid, 1, 1.10)
    hit_tp(tid, 2, 1.20)
    with get_session() as s:
        t = s.get(XRPSwingTrade, tid)
        # 20% move * 30% of $300 = $18.00
        assert t.tp2_pnl_usd == pytest.approx(18.00, abs=0.01)
        assert t.trailing_active is True


def test_hit_tp3_banks_the_final_forty_percent():
    tid = _open()
    hit_tp(tid, 1, 1.10)
    hit_tp(tid, 2, 1.20)
    hit_tp(tid, 3, 1.30)
    with get_session() as s:
        t = s.get(XRPSwingTrade, tid)
        # 30% move * 40% of $300 = $36.00
        assert t.tp3_pnl_usd == pytest.approx(36.00, abs=0.01)


def test_invalid_tp_number_is_rejected():
    tid = _open()
    with pytest.raises(ValueError):
        hit_tp(tid, 4, 1.10)


# ══════════════════════════════════════════════════════════════════════════════
# close_trade — remaining-fraction math across all four exit paths
# ══════════════════════════════════════════════════════════════════════════════

def test_close_with_no_tps_hit_uses_the_full_position():
    tid = _open()
    close_trade(tid, 1.05, reason="sl")
    # 5% move * 100% of $300 = $15.00, no banked P&L
    with get_session() as s:
        t = s.get(XRPSwingTrade, tid)
        assert t.final_pnl_usd == pytest.approx(15.00, abs=0.01)
        assert t.status == "closed_sl"


def test_close_after_tp1_uses_seventy_percent_not_the_old_sixty():
    """The actual bug this review found: close_trade used 0.60/0.25 against
    a real 30/30/40 split. This is the case that was silently wrong."""
    tid = _open()
    hit_tp(tid, 1, 1.10)  # banks $9.00 on 30%
    close_trade(tid, 1.05, reason="manual")
    with get_session() as s:
        t = s.get(XRPSwingTrade, tid)
        # Remaining 70% at 5% move = $10.50, plus $9.00 banked = $19.50
        assert t.final_pnl_usd == pytest.approx(19.50, abs=0.01)


def test_close_after_tp1_and_tp2_uses_forty_percent_not_the_old_twenty_five():
    tid = _open()
    hit_tp(tid, 1, 1.10)  # $9.00
    hit_tp(tid, 2, 1.20)  # $18.00
    close_trade(tid, 1.15, reason="manual")
    with get_session() as s:
        t = s.get(XRPSwingTrade, tid)
        # Remaining 40% at -4.17% move from avg_entry 1.00... compute directly:
        remaining_pct = (1.15 - 1.00) / 1.00 * 100
        expected = round(300.0 * 0.40 * remaining_pct / 100, 2) + 9.00 + 18.00
        assert t.final_pnl_usd == pytest.approx(expected, abs=0.01)


def test_close_after_all_three_tps_books_zero_additional_and_includes_tp3():
    """The other real bug: banked previously omitted tp3_pnl_usd, and
    nothing stopped a fully-closed position being charged an extra
    fraction on top of three real TP fills."""
    tid = _open()
    hit_tp(tid, 1, 1.10)  # $9.00
    hit_tp(tid, 2, 1.20)  # $18.00
    hit_tp(tid, 3, 1.30)  # $36.00
    close_trade(tid, 1.30, reason="tp")
    with get_session() as s:
        t = s.get(XRPSwingTrade, tid)
        assert t.final_pnl_usd == pytest.approx(9.00 + 18.00 + 36.00, abs=0.01)
        assert t.status == "closed_tp"


def test_close_trade_reason_maps_to_the_right_status():
    for reason, expected in [
        ("sl", "closed_sl"), ("tp", "closed_tp"),
        ("timeout", "closed_timeout"), ("manual", "closed_manual"),
        ("anything_else", "closed_manual"),
    ]:
        tid = _open()
        close_trade(tid, 1.02, reason=reason)
        with get_session() as s:
            assert s.get(XRPSwingTrade, tid).status == expected


def test_closing_an_already_closed_trade_raises():
    tid = _open()
    close_trade(tid, 1.05, reason="manual")
    with pytest.raises(ValueError):
        close_trade(tid, 1.06, reason="manual")
