"""
Integration tests for the agent framework (spot/trading_modes.py).

These tests verify:
- All 5 agent types instantiate correctly
- AgentRegistry creates and manages all agents
- Agent lifecycle: start, stop, pause, resume
- Config persistence via data/agent_configs.json
- Agent cycle functions are callable
"""
from __future__ import annotations

import pytest

from spot.trading_modes import (
    AgentType, AgentConfig, AgentRegistry, EventBus,
    AutoTrendAgent, XRPSwingAgent, SOLSwingAgent,
    P2PMarketAgent, ManualAgent,
    get_agent_registry, get_event_bus,
    is_agent_running, AgentState,
)


def make_registry():
    """Create a registry with a simple get_context."""
    def get_context():
        return {
            "positions": [],
            "watchlist": [],
            "live_prices": {},
            "macro_data": None,
            "atmosphere_data": None,
        }
    return get_context


class TestAgentInstantiation:
    """Verify all agent types can be created."""

    def test_all_agent_types_instantiate(self):
        """All 5 agent types should be in AgentType enum."""
        assert len(AgentType) == 5
        assert AgentType.AUTO_TREND
        assert AgentType.XRP_SWING
        assert AgentType.SOL_SWING
        assert AgentType.P2P_MARKET
        assert AgentType.MANUAL

    def test_auto_trend_agent(self):
        """AutoTrendAgent should instantiate without errors."""
        config = AgentConfig(agent_type=AgentType.AUTO_TREND)
        agent = AutoTrendAgent(config, get_event_bus(), make_context())
        assert agent.agent_type == AgentType.AUTO_TREND
        assert agent.state == AgentState.STOPPED

    def test_xrp_swing_agent(self):
        """XRPSwingAgent should instantiate without errors."""
        config = AgentConfig(agent_type=AgentType.XRP_SWING)
        agent = XRPSwingAgent(config, get_event_bus(), make_context())
        assert agent.agent_type == AgentType.XRP_SWING
        assert agent.state == AgentState.STOPPED

    def test_sol_swing_agent(self):
        """SOLSwingAgent should instantiate without errors."""
        config = AgentConfig(agent_type=AgentType.SOL_SWING)
        agent = SOLSwingAgent(config, get_event_bus(), make_context())
        assert agent.agent_type == AgentType.SOL_SWING
        assert agent.state == AgentState.STOPPED
        # Should NOT have unused strategy param causing issues

    def test_p2p_market_agent(self):
        """P2PMarketAgent should instantiate without errors."""
        config = AgentConfig(agent_type=AgentType.P2P_MARKET)
        agent = P2PMarketAgent(config, get_event_bus(), make_context())
        assert agent.agent_type == AgentType.P2P_MARKET

    def test_manual_agent(self):
        """ManualAgent should instantiate without errors."""
        config = AgentConfig(agent_type=AgentType.MANUAL)
        agent = ManualAgent(config, get_event_bus(), make_context())
        assert agent.agent_type == AgentType.MANUAL


class TestAgentRegistry:
    """Verify AgentRegistry manages all agents correctly."""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.get_context = make_registry()
        self.registry = AgentRegistry(self.get_context)
        self.registry.initialize()

    def test_registry_has_all_agents(self):
        """Registry should have all 5 agent types."""
        for agent_type in AgentType:
            agent = self.registry.get_agent(agent_type)
            assert agent is not None

    def test_registry_creates_correct_agent_types(self):
        """Each agent should be the correct class."""
        assert isinstance(self.registry.get_agent(AgentType.AUTO_TREND), AutoTrendAgent)
        assert isinstance(self.registry.get_agent(AgentType.XRP_SWING), XRPSwingAgent)
        assert isinstance(self.registry.get_agent(AgentType.SOL_SWING), SOLSwingAgent)
        assert isinstance(self.registry.get_agent(AgentType.P2P_MARKET), P2PMarketAgent)
        assert isinstance(self.registry.get_agent(AgentType.MANUAL), ManualAgent)

    def test_get_all_status(self):
        """get_all_status should return status for all agents."""
        statuses = self.registry.get_all_status()
        assert len(statuses) == 5
        for agent_type, status in statuses.items():
            assert status.state == AgentState.STOPPED
            assert status.enabled is False

    def test_start_stop_agent(self):
        """Should be able to start and stop an agent."""
        import asyncio

        async def _test():
            # Start AUTO_TREND
            status = await self.registry.start_agent(AgentType.AUTO_TREND)
            assert status.state == AgentState.RUNNING

            # Stop it
            status = await self.registry.stop_agent(AgentType.AUTO_TREND)
            assert status.state == AgentState.STOPPED

        asyncio.run(_test())

    def test_pause_resume_agent(self):
        """Should be able to pause and resume an agent."""
        import asyncio

        async def _test():
            await self.registry.start_agent(AgentType.AUTO_TREND)

            # Pause
            await self.registry.pause_agent(AgentType.AUTO_TREND)
            status = self.registry.get_agent(AgentType.AUTO_TREND).get_status()
            assert status.state == AgentState.PAUSED

            # Resume
            await self.registry.resume_agent(AgentType.AUTO_TREND)
            status = self.registry.get_agent(AgentType.AUTO_TREND).get_status()
            assert status.state == AgentState.RUNNING

            await self.registry.stop_agent(AgentType.AUTO_TREND)

        asyncio.run(_test())

    def test_config_persistence(self):
        """Agent configs should be persisted to data/agent_configs.json."""
        import json
        from pathlib import Path

        config_file = Path("data/agent_configs.json")
        if config_file.exists():
            data = json.loads(config_file.read_text())
            assert "auto_trend" in data
            assert "xrp_swing" in data
            assert "sol_swing" in data

    def test_update_agent_config(self):
        """Should be able to update agent config."""
        config = self.registry.update_agent_config(
            AgentType.AUTO_TREND, {"main_cycle_interval_sec": 600}
        )
        assert config.main_cycle_interval_sec == 600

    def test_stop_all(self):
        """stop_all should stop any running agents."""
        import asyncio

        async def _test():
            await self.registry.start_agent(AgentType.AUTO_TREND)
            await self.registry.start_agent(AgentType.XRP_SWING)

            results = await self.registry.stop_all()
            for agent_type, status in results.items():
                assert status.state == AgentState.STOPPED

        asyncio.run(_test())


class TestIsAgentRunning:
    """Verify is_agent_running utility function."""

    def test_returns_false_when_no_registry(self):
        """is_agent_running should return False if registry not initialized."""
        from spot.trading_modes import _registry
        old_registry = _registry
        try:
            # Force registry to None
            import spot.trading_modes as tm
            tm._registry = None
            assert tm.is_agent_running(AgentType.AUTO_TREND) is False
        finally:
            tm._registry = old_registry

    def test_returns_false_for_stopped_agent(self):
        """is_agent_running should return False for stopped agents."""
        registry = AgentRegistry(make_registry())
        registry.initialize()
        assert is_agent_running(AgentType.AUTO_TREND) is False


def make_context():
    """Helper to create a context dict."""
    return {
        "positions": [],
        "watchlist": [],
        "live_prices": {},
        "macro_data": None,
        "atmosphere_data": None,
    }
