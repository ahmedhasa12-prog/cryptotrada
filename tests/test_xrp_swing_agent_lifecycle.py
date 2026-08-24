"""
Regression test for a real production incident: starting the XRP swing agent
silently disabled auto-trading.

_on_stop() used to unconditionally call disable_auto(), and _on_start() would
conditionally call enable_auto() based on an agent config key
("auto_enabled") that nothing in this codebase ever actually sets. In
production, a routine restart — the run.sh watchdog recovering from an
unrelated hiccup, not a deliberate decision by anyone — silently flipped a
live, user-set auto-trading flag back off. The whole point of moving this
state into the database (see the XRPAutoState work earlier this project) was
for it to survive exactly this kind of restart; the agent's own lifecycle
hooks were quietly undoing that guarantee.

Fixed by decoupling entirely: the agent's start/stop no longer touches
auto-trading state at all. These tests exercise the hooks directly rather
than the full asyncio start()/stop() lifecycle (spinning up real cycle tasks
is out of scope for what this regression is about).
"""
from __future__ import annotations

import pytest

import config as cfg
import data.database as db
from spot.trading_modes import AgentConfig, AgentType, EventBus, XRPSwingAgent
from spot.xrp_swing import disable_auto, enable_auto, get_auto_status


@pytest.fixture(autouse=True)
def setup(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_USER_ID", "1")
    cfg.reset_config()
    db.init_db(":memory:")
    yield
    db.reset_db()
    cfg.reset_config()


def make_agent(config_overrides: dict | None = None) -> XRPSwingAgent:
    agent_config = AgentConfig(
        agent_type=AgentType.XRP_SWING,
        config=config_overrides or {},
    )
    return XRPSwingAgent(agent_config, EventBus(), get_context=lambda: {})


@pytest.mark.asyncio
async def test_stopping_the_agent_does_not_disable_auto_trading():
    """The actual incident: enable auto-trading, then stop the agent for an
    unrelated reason (a restart, a redeploy) — the flag must survive."""
    enable_auto(300.0)
    assert get_auto_status()["enabled"] is True

    agent = make_agent()
    await agent._on_stop()

    assert get_auto_status()["enabled"] is True


@pytest.mark.asyncio
async def test_starting_the_agent_does_not_change_auto_trading_state():
    """Starting must be equally hands-off, in both directions."""
    disable_auto()
    agent = make_agent()
    await agent._on_start()
    assert get_auto_status()["enabled"] is False

    enable_auto(300.0)
    agent2 = make_agent()
    await agent2._on_start()
    assert get_auto_status()["enabled"] is True


@pytest.mark.asyncio
async def test_a_legacy_auto_enabled_config_key_is_inert():
    """auto_enabled was never wired to anything real — confirm setting it
    does not resurrect the old behavior if this code is ever touched again."""
    disable_auto()
    agent = make_agent({"auto_enabled": True, "auto_size_usd": 500.0})
    await agent._on_start()
    assert get_auto_status()["enabled"] is False
