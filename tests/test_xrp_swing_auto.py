"""
Integration tests for XRP swing's auto-cycle, now that it's wired through the
risk supervisor instead of a chain of inline early-returns.

These don't exercise the 3-layer evaluation itself (_check_macro_gate /
_check_xrp_setup need a full OHLCV history and are unchanged by this rebuild)
— they insert an XRPSwingSetup row directly, the same shape evaluate_setup()
would have written, and drive run_auto_cycle() from there. The two things
this rebuild was actually for: every auto-open decision lands in the
database, and state survives a restart.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

import config as cfg
import data.database as db
from data.database import get_session
from data.models import XRPRiskDecision, XRPSwingSetup


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_USER_ID", "1")
    cfg.reset_config()
    db.init_db(":memory:")
    yield
    db.reset_db()
    cfg.reset_config()


def store_setup(**overrides) -> int:
    """Insert an XRPSwingSetup row directly — bypassing the macro/technical
    evaluation, which is untouched by this rebuild and out of scope here."""
    defaults = dict(
        evaluated_at=datetime.utcnow(),
        verdict="ENTRY_READY",
        score=85,
        setup_type="B",
        xrp_price=0.9200,
        gate_btc_sma50=True,
        gate_dom_falling=True,
        gate_fg_recovering=True,
        gate_btc_weekly_green=True,
    )
    with get_session() as s:
        row = XRPSwingSetup(**{**defaults, **overrides})
        s.add(row)
        s.flush()
        return row.id


def with_live_price(price: float | None):
    """Patch the streamer as run_auto_cycle sees it (a local re-import inside
    the function body, so patching the source module is enough)."""
    return patch(
        "spot.streamer.get_prices",
        return_value={"XRP": {"price": price}} if price else {},
    )


# ══════════════════════════════════════════════════════════════════════════════
# Auto-open — approved and vetoed paths both land in the audit trail
# ══════════════════════════════════════════════════════════════════════════════

def test_a_good_setup_opens_a_trade_and_is_recorded_approved():
    import spot.xrp_swing as xs

    store_setup()
    xs.enable_auto(300.0)

    with with_live_price(0.9200):
        result = xs.run_auto_cycle()

    assert result["actions"], "expected an AUTO-OPENED action"
    assert xs.get_active_trade() is not None

    with get_session() as s:
        decisions = s.query(XRPRiskDecision).all()
        assert len(decisions) == 1
        assert decisions[0].approved is True
        assert decisions[0].final_size_usd is not None


def test_a_watching_verdict_is_vetoed_and_recorded():
    import spot.xrp_swing as xs

    store_setup(verdict="WATCHING", score=20)
    xs.enable_auto(300.0)

    with with_live_price(0.9200):
        result = xs.run_auto_cycle()

    assert xs.get_active_trade() is None
    assert "WATCHING" in result["verdict"]

    with get_session() as s:
        decisions = s.query(XRPRiskDecision).all()
        assert len(decisions) == 1
        assert decisions[0].approved is False
        assert decisions[0].veto_reason == "verdict_not_ready"
        assert decisions[0].final_size_usd is None


def test_disabled_auto_never_opens_or_records_a_decision():
    """Monitoring runs regardless of the enabled flag; opening does not."""
    import spot.xrp_swing as xs

    store_setup()
    xs.disable_auto()

    with with_live_price(0.9200):
        result = xs.run_auto_cycle()

    assert result["enabled"] is False
    assert xs.get_active_trade() is None
    with get_session() as s:
        assert s.query(XRPRiskDecision).count() == 0


def test_no_live_price_falls_back_to_the_evaluation_price():
    """The original behaviour this rebuild had to preserve: live price wins,
    but the stored evaluation price is a valid fallback, not a veto trigger."""
    import spot.xrp_swing as xs

    store_setup(xrp_price=0.9100)
    xs.enable_auto(300.0)

    with with_live_price(None):
        result = xs.run_auto_cycle()

    assert result["actions"], "should still open using the evaluation's price"
    trade = xs.get_active_trade()
    assert trade is not None
    assert trade["avg_entry"] == pytest.approx(0.9100)


def test_no_price_anywhere_is_vetoed_as_no_live_price():
    import spot.xrp_swing as xs

    store_setup(xrp_price=None)
    xs.enable_auto(300.0)

    with with_live_price(None):
        result = xs.run_auto_cycle()

    assert xs.get_active_trade() is None
    with get_session() as s:
        decision = s.query(XRPRiskDecision).one()
        assert decision.veto_reason == "no_live_price"


# ══════════════════════════════════════════════════════════════════════════════
# State that must survive a restart
# ══════════════════════════════════════════════════════════════════════════════

def test_cooldown_blocks_reopening_after_a_process_restart():
    """The whole point of moving off the JSON file: state set in one process
    lifetime must still be honoured after a fresh session opens it."""
    import spot.xrp_swing as xs

    xs.enable_auto(300.0)
    state = xs._load_auto_state()
    state["cooldown_until"] = (datetime.utcnow() + timedelta(hours=2)).isoformat()
    xs._save_auto_state(state)

    # Simulate a restart: nothing held in memory, re-read from the DB.
    reloaded = xs._load_auto_state()
    assert reloaded["cooldown_until"] is not None

    store_setup()
    with with_live_price(0.9200):
        result = xs.run_auto_cycle()

    assert xs.get_active_trade() is None
    with get_session() as s:
        decision = s.query(XRPRiskDecision).one()
        assert decision.veto_reason == "cooldown_active"


def test_setup_already_consumed_persists_across_a_restart():
    import spot.xrp_swing as xs

    eval_id = store_setup()
    xs.enable_auto(300.0)
    with with_live_price(0.9200):
        xs.run_auto_cycle()
    assert xs.get_active_trade() is not None

    # A second cycle against the SAME evaluation must not open a second trade
    # — even though the first trade's own `active` branch would already
    # short-circuit this, the consumed-eval_id guard is the real backstop.
    reloaded = xs._load_auto_state()
    assert reloaded["last_opened_eval_id"] == eval_id


def test_default_state_is_created_on_first_use_without_crashing():
    """A brand-new database — never having run auto mode before — must not
    error the first time auto status is checked."""
    import spot.xrp_swing as xs

    status = xs.get_auto_status()
    assert status["enabled"] is False
    assert status["auto_size_usd"] == pytest.approx(300.0)
