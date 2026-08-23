"""
Full Agent Architecture for Trading System
==========================================
Independent agents with lifecycle management running concurrently.

Agent Lifecycle: STOPPED → STARTING → RUNNING → PAUSED → STOPPING → ERROR

Agent Types:
- AutoTrendAgent: Enhanced auto-trader (multi-coin, trend-following)
- XRPSwingAgent: XRP specialist (3-layer macro/tech/trigger)
- P2PMarketAgent: P2P market making (placeholder)
- ManualAgent: Insights only, no auto-execution

Each agent runs independently with:
- Main cycle (configurable interval, default 5min)
- Fast cycle for SL/trailing/TP (30s)
- Independent start/stop/pause/resume
- Individual state tracking and metrics

AgentRegistry manages all agents:
- start_agent/stop_agent/pause_agent/resume_agent per agent
- start_all_enabled/stop_all
- get_all_status for UI
- EventBus for inter-agent communication
"""
from __future__ import annotations

import asyncio
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA CLASSES
# ══════════════════════════════════════════════════════════════════════════════

class AgentState(str, Enum):
    """Agent lifecycle states."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class AgentType(str, Enum):
    """Available agent types."""
    AUTO_TREND = "auto_trend"
    XRP_SWING = "xrp_swing"
    P2P_MARKET = "p2p_market"
    MANUAL = "manual"


@dataclass
class AgentConfig:
    """Configuration for an agent."""
    agent_type: AgentType
    enabled: bool = False
    main_cycle_interval_sec: int = 300      # 5 minutes default
    fast_cycle_interval_sec: int = 30       # 30 seconds default
    config: dict = field(default_factory=dict)  # Agent-specific config


@dataclass
class AgentMetrics:
    """Runtime metrics for an agent."""
    cycles_completed: int = 0
    fast_cycles_completed: int = 0
    last_cycle_at: Optional[str] = None
    last_fast_cycle_at: Optional[str] = None
    last_error: Optional[str] = None
    last_error_at: Optional[str] = None
    total_actions: int = 0
    total_entries: int = 0
    total_exits: int = 0
    uptime_started_at: Optional[str] = None


@dataclass
class AgentStatus:
    """Complete agent status for UI/API."""
    agent_type: AgentType
    state: AgentState
    enabled: bool
    config: AgentConfig
    metrics: AgentMetrics
    error_message: Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════════
# EVENT BUS
# ══════════════════════════════════════════════════════════════════════════════

class EventBus:
    """Simple pub/sub event bus for inter-agent communication."""
    
    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
    
    def subscribe(self, event_type: str, callback: Callable) -> None:
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
    
    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        """Unsubscribe from an event type."""
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                cb for cb in self._subscribers[event_type] if cb != callback
            ]
    
    async def publish(self, event_type: str, data: Any = None) -> None:
        """Publish an event to all subscribers."""
        if event_type not in self._subscribers:
            return
        for callback in self._subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"EventBus: Error in callback for {event_type}: {e}")


# Global event bus instance
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus instance."""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


# ══════════════════════════════════════════════════════════════════════════════
# BASE AGENT
# ══════════════════════════════════════════════════════════════════════════════

class BaseAgent(ABC):
    """Base class for all trading agents with lifecycle management."""
    
    def __init__(
        self,
        agent_type: AgentType,
        config: AgentConfig,
        event_bus: EventBus,
        get_context: Callable[[], dict],
    ):
        self.agent_type = agent_type
        self.config = config
        self.event_bus = event_bus
        self.get_context = get_context  # Callable that returns StrategyContext
        
        self._state = AgentState.STOPPED
        self._error_message: Optional[str] = None
        self._main_task: Optional[asyncio.Task] = None
        self._fast_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused by default
        
        self.metrics = AgentMetrics()
    
    @property
    def state(self) -> AgentState:
        return self._state
    
    @property
    def error_message(self) -> Optional[str]:
        return self._error_message
    
    @property
    def is_running(self) -> bool:
        return self._state == AgentState.RUNNING
    
    @property
    def is_paused(self) -> bool:
        return self._state == AgentState.PAUSED
    
    # ── Lifecycle Methods ──────────────────────────────────────────────────
    
    async def start(self) -> None:
        """Start the agent (main + fast cycles)."""
        if self._state in (AgentState.RUNNING, AgentState.STARTING):
            logger.warning(f"Agent {self.agent_type.value} already running/starting")
            return
        
        self._state = AgentState.STARTING
        self._error_message = None
        self._stop_event.clear()
        self._pause_event.set()
        self.metrics.uptime_started_at = datetime.utcnow().isoformat()
        
        try:
            await self._on_start()
            
            self._main_task = asyncio.create_task(self._main_loop())
            self._fast_task = asyncio.create_task(self._fast_loop())
            
            self._state = AgentState.RUNNING
            logger.info(f"Agent {self.agent_type.value} STARTED")
            await self.event_bus.publish(f"agent.{self.agent_type.value}.started", {"agent": self.agent_type.value})
            
        except Exception as e:
            self._state = AgentState.ERROR
            self._error_message = str(e)
            logger.error(f"Agent {self.agent_type.value} failed to start: {e}")
            await self.event_bus.publish(f"agent.{self.agent_type.value}.error", {"error": str(e)})
            raise
    
    async def stop(self) -> None:
        """Stop the agent gracefully."""
        if self._state == AgentState.STOPPED:
            return
        
        self._state = AgentState.STOPPING
        self._stop_event.set()
        self._pause_event.set()  # Unpause if paused so loops can exit
        
        # Cancel tasks
        for task in (self._main_task, self._fast_task):
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        try:
            await self._on_stop()
        except Exception as e:
            logger.error(f"Agent {self.agent_type.value} error during stop: {e}")
        
        self._state = AgentState.STOPPED
        self._main_task = None
        self._fast_task = None
        logger.info(f"Agent {self.agent_type.value} STOPPED")
        await self.event_bus.publish(f"agent.{self.agent_type.value}.stopped", {"agent": self.agent_type.value})
    
    async def pause(self) -> None:
        """Pause the agent (stops cycles but keeps state)."""
        if self._state != AgentState.RUNNING:
            logger.warning(f"Agent {self.agent_type.value} cannot pause from state {self._state}")
            return
        
        self._state = AgentState.PAUSED
        self._pause_event.clear()
        logger.info(f"Agent {self.agent_type.value} PAUSED")
        await self.event_bus.publish(f"agent.{self.agent_type.value}.paused", {"agent": self.agent_type.value})
    
    async def resume(self) -> None:
        """Resume a paused agent."""
        if self._state != AgentState.PAUSED:
            logger.warning(f"Agent {self.agent_type.value} cannot resume from state {self._state}")
            return
        
        self._state = AgentState.RUNNING
        self._pause_event.set()
        logger.info(f"Agent {self.agent_type.value} RESUMED")
        await self.event_bus.publish(f"agent.{self.agent_type.value}.resumed", {"agent": self.agent_type.value})
    
    # ── Abstract Methods (to be implemented by subclasses) ─────────────────
    
    @abstractmethod
    async def _on_start(self) -> None:
        """Called when agent starts - initialize resources."""
        pass
    
    @abstractmethod
    async def _on_stop(self) -> None:
        """Called when agent stops - cleanup resources."""
        pass
    
    @abstractmethod
    async def _run_main_cycle(self, ctx: dict) -> dict:
        """Main trading cycle (every 5 min by default). Returns actions taken."""
        pass
    
    @abstractmethod
    async def _run_fast_cycle(self, ctx: dict) -> list[dict]:
        """Fast cycle for SL/trailing/TP (every 30s). Returns actions taken."""
        pass
    
    # ── Internal Loop Methods ──────────────────────────────────────────────
    
    async def _main_loop(self) -> None:
        """Main cycle loop."""
        interval = self.config.main_cycle_interval_sec
        
        while not self._stop_event.is_set():
            try:
                # Wait for pause to clear
                await self._pause_event.wait()
                
                if self._stop_event.is_set():
                    break
                
                start_time = time.time()
                ctx = self.get_context()
                result = await self._run_main_cycle(ctx)
                
                self.metrics.cycles_completed += 1
                self.metrics.last_cycle_at = datetime.utcnow().isoformat()
                self.metrics.total_actions += len(result.get("actions", []))
                self.metrics.total_entries += len(result.get("entries", []))
                self.metrics.total_exits += len(result.get("exits", []))
                
                # Publish cycle completion event
                await self.event_bus.publish(
                    f"agent.{self.agent_type.value}.cycle_complete",
                    {"agent": self.agent_type.value, "result": result, "duration": time.time() - start_time}
                )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._error_message = str(e)
                self.metrics.last_error = str(e)
                self.metrics.last_error_at = datetime.utcnow().isoformat()
                logger.error(f"Agent {self.agent_type.value} main cycle error: {e}")
                await self.event_bus.publish(
                    f"agent.{self.agent_type.value}.cycle_error",
                    {"agent": self.agent_type.value, "error": str(e)}
                )
            
            # Sleep until next cycle (with stop event check)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                break  # Stop event was set
            except asyncio.TimeoutError:
                continue  # Normal cycle interval elapsed
    
    async def _fast_loop(self) -> None:
        """Fast cycle loop (SL, trailing, TP)."""
        interval = self.config.fast_cycle_interval_sec
        
        while not self._stop_event.is_set():
            try:
                await self._pause_event.wait()
                
                if self._stop_event.is_set():
                    break
                
                ctx = self.get_context()
                actions = await self._run_fast_cycle(ctx)
                
                self.metrics.fast_cycles_completed += 1
                self.metrics.last_fast_cycle_at = datetime.utcnow().isoformat()
                self.metrics.total_actions += len(actions)
                
                if actions:
                    await self.event_bus.publish(
                        f"agent.{self.agent_type.value}.fast_actions",
                        {"agent": self.agent_type.value, "actions": actions}
                    )
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._error_message = str(e)
                self.metrics.last_error = str(e)
                self.metrics.last_error_at = datetime.utcnow().isoformat()
                logger.error(f"Agent {self.agent_type.value} fast cycle error: {e}")
            
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval)
                break
            except asyncio.TimeoutError:
                continue
    
    # ── Status & Config ────────────────────────────────────────────────────
    
    def get_status(self) -> AgentStatus:
        """Get complete agent status."""
        return AgentStatus(
            agent_type=self.agent_type,
            state=self._state,
            enabled=self.config.enabled,
            config=self.config,
            metrics=self.metrics,
            error_message=self._error_message,
        )
    
    def update_config(self, config: dict) -> None:
        """Update agent configuration."""
        self.config.config.update(config)
        logger.info(f"Agent {self.agent_type.value} config updated: {config}")


# ══════════════════════════════════════════════════════════════════════════════
# CONCRETE AGENTS
# ══════════════════════════════════════════════════════════════════════════════

class AutoTrendAgent(BaseAgent):
    """Enhanced auto-trader agent (multi-coin, trend-following)."""
    
    def __init__(self, config: AgentConfig, event_bus: EventBus, get_context: Callable[[], dict]):
        super().__init__(AgentType.AUTO_TREND, config, event_bus, get_context)
    
    async def _on_start(self) -> None:
        logger.info("AutoTrendAgent: Initializing...")
        # Auto-trader uses global state, no special init needed
    
    async def _on_stop(self) -> None:
        logger.info("AutoTrendAgent: Cleaning up...")
    
    async def _run_main_cycle(self, ctx: dict) -> dict:
        from spot.auto_trader import run_cycle
        from spot.watchlist import get_watchlist
        watchlist = get_watchlist(active_only=True)
        run_cycle(ctx.get("positions", []), watchlist, ctx.get("live_prices", {}))
        return {"entries": [], "exits": [], "actions": []}
    
    async def _run_fast_cycle(self, ctx: dict) -> list[dict]:
        from spot.auto_trader import fast_sl_cycle
        return fast_sl_cycle(ctx.get("positions", []), ctx.get("live_prices", {}))


class XRPSwingAgent(BaseAgent):
    """XRP Swing specialist agent (3-layer macro/tech/trigger)."""
    
    def __init__(self, config: AgentConfig, event_bus: EventBus, get_context: Callable[[], dict]):
        super().__init__(AgentType.XRP_SWING, config, event_bus, get_context)
    
    async def _on_start(self) -> None:
        logger.info("XRPSwingAgent: Initializing...")
        # Enable auto mode if configured
        if self.config.config.get("auto_enabled", False):
            from spot.xrp_swing import enable_auto
            size = self.config.config.get("auto_size_usd", 300.0)
            enable_auto(size)
    
    async def _on_stop(self) -> None:
        logger.info("XRPSwingAgent: Cleaning up...")
        from spot.xrp_swing import disable_auto
        disable_auto()
    
    async def _run_main_cycle(self, ctx: dict) -> dict:
        from spot.xrp_swing import run_auto_cycle
        result = run_auto_cycle()
        actions = result.get("actions", [])
        entries = [a for a in actions if "AUTO-OPENED" in a]
        return {"entries": entries, "exits": [], "actions": actions}
    
    async def _run_fast_cycle(self, ctx: dict) -> list[dict]:
        from spot.xrp_swing import fast_sl_check
        return fast_sl_check()


class P2PMarketAgent(BaseAgent):
    """P2P market making agent (placeholder for future implementation)."""
    
    def __init__(self, config: AgentConfig, event_bus: EventBus, get_context: Callable[[], dict]):
        super().__init__(AgentType.P2P_MARKET, config, event_bus, get_context)
    
    async def _on_start(self) -> None:
        logger.info("P2PMarketAgent: Initializing (placeholder)...")
    
    async def _on_stop(self) -> None:
        logger.info("P2PMarketAgent: Cleaning up...")
    
    async def _run_main_cycle(self, ctx: dict) -> dict:
        # TODO: Implement P2P market making logic
        return {"entries": [], "exits": [], "actions": []}
    
    async def _run_fast_cycle(self, ctx: dict) -> list[dict]:
        return []


class ManualAgent(BaseAgent):
    """Manual mode agent - insights only, no auto-execution."""
    
    def __init__(self, config: AgentConfig, event_bus: EventBus, get_context: Callable[[], dict]):
        super().__init__(AgentType.MANUAL, config, event_bus, get_context)
    
    async def _on_start(self) -> None:
        logger.info("ManualAgent: Started (insights only)")
    
    async def _on_stop(self) -> None:
        logger.info("ManualAgent: Stopped")
    
    async def _run_main_cycle(self, ctx: dict) -> dict:
        # No auto-execution in manual mode
        return {"entries": [], "exits": [], "actions": []}
    
    async def _run_fast_cycle(self, ctx: dict) -> list[dict]:
        return []


# ══════════════════════════════════════════════════════════════════════════════
# AGENT REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

CONFIG_FILE = Path("data/agent_configs.json")


class AgentRegistry:
    """Manages all trading agents with lifecycle and config persistence."""
    
    def __init__(self, get_context: Callable[[], dict]):
        self.get_context = get_context
        self.event_bus = get_event_bus()
        self._agents: dict[AgentType, BaseAgent] = {}
        self._configs: dict[AgentType, AgentConfig] = {}
        self._initialized = False
    
    def initialize(self) -> None:
        """Create all agents and load configs."""
        if self._initialized:
            return
        
        # Load persisted configs
        self._load_configs()
        
        # Create agents
        self._agents[AgentType.AUTO_TREND] = AutoTrendAgent(
            self._configs.get(AgentType.AUTO_TREND, AgentConfig(agent_type=AgentType.AUTO_TREND)),
            self.event_bus,
            self.get_context,
        )
        self._agents[AgentType.XRP_SWING] = XRPSwingAgent(
            self._configs.get(AgentType.XRP_SWING, AgentConfig(agent_type=AgentType.XRP_SWING)),
            self.event_bus,
            self.get_context,
        )
        self._agents[AgentType.P2P_MARKET] = P2PMarketAgent(
            self._configs.get(AgentType.P2P_MARKET, AgentConfig(agent_type=AgentType.P2P_MARKET)),
            self.event_bus,
            self.get_context,
        )
        self._agents[AgentType.MANUAL] = ManualAgent(
            self._configs.get(AgentType.MANUAL, AgentConfig(agent_type=AgentType.MANUAL)),
            self.event_bus,
            self.get_context,
        )
        
        self._initialized = True
        logger.info("AgentRegistry initialized with all agents")
    
    def _load_configs(self) -> None:
        """Load agent configs from JSON file."""
        if CONFIG_FILE.exists():
            try:
                data = json.loads(CONFIG_FILE.read_text())
                for agent_type_str, cfg in data.items():
                    agent_type = AgentType(agent_type_str)
                    self._configs[agent_type] = AgentConfig(
                        agent_type=agent_type,
                        enabled=cfg.get("enabled", False),
                        main_cycle_interval_sec=cfg.get("main_cycle_interval_sec", 300),
                        fast_cycle_interval_sec=cfg.get("fast_cycle_interval_sec", 30),
                        config=cfg.get("config", {}),
                    )
                logger.info(f"Loaded agent configs from {CONFIG_FILE}")
            except Exception as e:
                logger.warning(f"Failed to load agent configs: {e}")
        
        # Ensure all agent types have configs
        for agent_type in AgentType:
            if agent_type not in self._configs:
                self._configs[agent_type] = AgentConfig(agent_type=agent_type)
    
    def _save_configs(self) -> None:
        """Persist agent configs to JSON file."""
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for agent_type, config in self._configs.items():
                data[agent_type.value] = {
                    "enabled": config.enabled,
                    "main_cycle_interval_sec": config.main_cycle_interval_sec,
                    "fast_cycle_interval_sec": config.fast_cycle_interval_sec,
                    "config": config.config,
                }
            CONFIG_FILE.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save agent configs: {e}")
    
    # ── Agent Control ──────────────────────────────────────────────────────
    
    async def start_agent(self, agent_type: AgentType) -> AgentStatus:
        """Start a specific agent."""
        self.initialize()
        agent = self._agents[agent_type]
        self._configs[agent_type].enabled = True
        self._save_configs()
        await agent.start()
        return agent.get_status()
    
    async def stop_agent(self, agent_type: AgentType) -> AgentStatus:
        """Stop a specific agent."""
        self.initialize()
        agent = self._agents[agent_type]
        self._configs[agent_type].enabled = False
        self._save_configs()
        await agent.stop()
        return agent.get_status()
    
    async def pause_agent(self, agent_type: AgentType) -> AgentStatus:
        """Pause a specific agent."""
        self.initialize()
        agent = self._agents[agent_type]
        await agent.pause()
        return agent.get_status()
    
    async def resume_agent(self, agent_type: AgentType) -> AgentStatus:
        """Resume a paused agent."""
        self.initialize()
        agent = self._agents[agent_type]
        await agent.resume()
        return agent.get_status()
    
    async def start_all_enabled(self) -> dict[AgentType, AgentStatus]:
        """Start all agents that are enabled in config."""
        self.initialize()
        results = {}
        for agent_type, config in self._configs.items():
            if config.enabled:
                results[agent_type] = await self.start_agent(agent_type)
        return results
    
    async def stop_all(self) -> dict[AgentType, AgentStatus]:
        """Stop all running agents."""
        self.initialize()
        results = {}
        for agent_type, agent in self._agents.items():
            if agent.state != AgentState.STOPPED:
                results[agent_type] = await self.stop_agent(agent_type)
        return results
    
    def get_agent(self, agent_type: AgentType) -> BaseAgent:
        """Get agent instance."""
        self.initialize()
        return self._agents[agent_type]
    
    def get_all_status(self) -> dict[AgentType, AgentStatus]:
        """Get status of all agents for UI."""
        self.initialize()
        return {at: agent.get_status() for at, agent in self._agents.items()}
    
    def update_agent_config(self, agent_type: AgentType, config: dict) -> AgentConfig:
        """Update agent configuration and persist."""
        self.initialize()
        agent_config = self._configs[agent_type]
        agent_config.config.update(config)
        self._save_configs()
        
        # Apply config to running agent if needed
        agent = self._agents[agent_type]
        agent.update_config(config)
        
        return agent_config


# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL REGISTRY & HELPERS
# ══════════════════════════════════════════════════════════════════════════════

_registry: AgentRegistry | None = None


def get_agent_registry(get_context: Callable[[], dict] | None = None) -> AgentRegistry:
    """Get the global agent registry instance."""
    global _registry
    if _registry is None:
        if get_context is None:
            raise ValueError("get_context must be provided on first call")
        _registry = AgentRegistry(get_context)
    return _registry


async def start_all_agents(get_context: Callable[[], dict]) -> dict[AgentType, AgentStatus]:
    """Initialize registry and start all enabled agents."""
    registry = get_agent_registry(get_context)
    return await registry.start_all_enabled()


async def stop_all_agents() -> dict[AgentType, AgentStatus]:
    """Stop all agents."""
    if _registry:
        return await _registry.stop_all()
    return {}


def is_agent_running(agent_type: AgentType) -> bool:
    """
    Safe check for whether an agent currently owns its own cycle.

    Used by any standalone scheduled job whose logic duplicates what an
    agent's fast cycle already does (fast_sl_cycle, fast_sl_check) — those
    jobs predate the agent framework and must stand down once the
    corresponding agent is running, or stop-loss/trailing logic executes
    twice per tick. Never raises: before the registry exists (early in
    startup, or if agents were never initialised) this returns False, which
    correctly leaves the standalone job as the sole owner of the cycle.
    """
    if _registry is None:
        return False
    try:
        return _registry.get_agent(agent_type).is_running
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY CONTEXT (for backward compatibility with existing code)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class StrategyContext:
    """Context passed to strategy methods each cycle."""
    positions: list[dict]
    watchlist: list[dict]
    live_prices: dict
    macro_data: dict | None = None
    atmosphere_data: dict | None = None


class TradingMode(str, Enum):
    """Available trading modes (legacy - kept for compatibility)."""
    AUTO_TREND = "auto_trend"
    XRP_SWING = "xrp_swing"
    P2P_ONLY = "p2p_only"
    MANUAL = "manual"


# Legacy mode manager for backward compatibility
class ModeManager:
    """Legacy mode manager - delegates to AgentRegistry."""
    
    def __init__(self):
        self._mode = TradingMode.MANUAL
    
    @property
    def mode(self) -> TradingMode:
        return self._mode
    
    def set_mode(self, mode: TradingMode) -> None:
        self._mode = mode
        logger.info(f"Legacy mode changed to: {mode.value}")
    
    def run_cycle(self, ctx: StrategyContext) -> dict:
        """Run cycle for backward compatibility."""
        # This is now handled by individual agents
        return {"mode": self._mode.value, "entries": [], "exits": [], "actions": []}
    
    def run_fast_cycle(self, ctx: StrategyContext) -> list[dict]:
        return []


_mode_manager: ModeManager | None = None


def get_mode_manager() -> ModeManager:
    global _mode_manager
    if _mode_manager is None:
        _mode_manager = ModeManager()
    return _mode_manager


def set_trading_mode(mode: TradingMode) -> None:
    get_mode_manager().set_mode(mode)


def get_trading_mode() -> TradingMode:
    return get_mode_manager().mode


def run_trading_cycle(ctx: StrategyContext) -> dict:
    return get_mode_manager().run_cycle(ctx)


def run_fast_cycle(ctx: StrategyContext) -> list[dict]:
    return get_mode_manager().run_fast_cycle(ctx)