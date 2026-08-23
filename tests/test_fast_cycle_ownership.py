"""
Regression test for the fast-cycle double-fire bug.

main.py schedules `_fast_sl_check` / `_xrp_fast_sl_check` directly via
APScheduler every 30 seconds. Separately, `AutoTrendAgent` / `XRPSwingAgent`
call the identical underlying functions (`auto_trader.fast_sl_cycle`,
`xrp_swing.fast_sl_check`) from their own fast cycle whenever running. Before
the `is_agent_running` guard, enabling either agent while its standalone job
stayed scheduled meant stop-loss and trailing logic applied twice per tick,
silently — nothing enforced that these two paths could not both be live for
the same symbol at once.

This proves that property now holds, both for the underlying signal
(`is_agent_running`) and for the two call sites that depend on it.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

import config as cfg
import data.database as db
import spot.trading_modes as tm
from spot.trading_modes import AgentState, AgentType, get_agent_registry, is_agent_running


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_USER_ID", "1")
    cfg.reset_config()
    db.init_db(":memory:")
    tm._registry = None  # the registry is a module-level singleton — isolate tests
    yield
    db.reset_db()
    cfg.reset_config()
    tm._registry = None


def _set_running(agent_type: AgentType, running: bool) -> None:
    """
    White-box: flips an agent's lifecycle state directly rather than calling
    `.start()`, which would spin up real asyncio tasks and hit the DB/network
    on a timer. All that matters here is the `is_running` signal itself.
    """
    registry = get_agent_registry(lambda: {})
    registry.get_agent(agent_type)._state = (
        AgentState.RUNNING if running else AgentState.STOPPED
    )


# ══════════════════════════════════════════════════════════════════════════════
# The signal itself
# ══════════════════════════════════════════════════════════════════════════════

def test_is_agent_running_is_false_before_the_registry_exists():
    """Early in startup, before agents are initialised, nothing must crash —
    and the standalone jobs must remain the correct sole owner of the cycle."""
    assert tm._registry is None
    assert is_agent_running(AgentType.AUTO_TREND) is False


def test_is_agent_running_reflects_actual_agent_state():
    _set_running(AgentType.AUTO_TREND, True)
    assert is_agent_running(AgentType.AUTO_TREND) is True

    _set_running(AgentType.AUTO_TREND, False)
    assert is_agent_running(AgentType.AUTO_TREND) is False


def test_is_agent_running_never_raises():
    """A broken lookup must fail closed (standalone job keeps running), never
    propagate into a scheduled job and take the scheduler down with it."""
    registry = get_agent_registry(lambda: {})
    with patch.object(registry, "get_agent", side_effect=RuntimeError("boom")):
        assert is_agent_running(AgentType.AUTO_TREND) is False


# ══════════════════════════════════════════════════════════════════════════════
# The property that actually matters: the standalone jobs stand down
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_auto_trend_standalone_job_skips_when_the_agent_is_running():
    import main

    _set_running(AgentType.AUTO_TREND, True)
    with patch("main.get_open_positions") as get_positions:
        await main._fast_sl_check()
        get_positions.assert_not_called()


@pytest.mark.asyncio
async def test_auto_trend_standalone_job_runs_when_the_agent_is_not_running():
    import main

    _set_running(AgentType.AUTO_TREND, False)
    with patch("main.get_open_positions", return_value=[]) as get_positions:
        await main._fast_sl_check()
        get_positions.assert_called_once()


@pytest.mark.asyncio
async def test_xrp_standalone_job_skips_when_the_agent_is_running():
    import main

    _set_running(AgentType.XRP_SWING, True)
    with patch("main._xrp_fast_sl_cycle") as cycle:
        await main._xrp_fast_sl_check()
        cycle.assert_not_called()


@pytest.mark.asyncio
async def test_xrp_standalone_job_runs_when_the_agent_is_not_running():
    import main

    _set_running(AgentType.XRP_SWING, False)
    with patch("main._xrp_fast_sl_cycle") as cycle:
        await main._xrp_fast_sl_check()
        cycle.assert_called_once()


# ══════════════════════════════════════════════════════════════════════════════
# The invariant, stated directly
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.parametrize("agent_type", [AgentType.AUTO_TREND, AgentType.XRP_SWING])
@pytest.mark.parametrize("running", [True, False])
def test_exactly_one_path_owns_the_cycle_at_any_time(agent_type, running):
    """
    Not "the standalone job happens to be careful" but "these two booleans are
    exhaustive complements by construction": the agent owns the cycle, or the
    standalone job does — never both, never neither.
    """
    _set_running(agent_type, running)
    agent_owns_it = is_agent_running(agent_type)
    standalone_should_run = not agent_owns_it
    assert agent_owns_it is running
    assert standalone_should_run is (not running)
    assert agent_owns_it != standalone_should_run
