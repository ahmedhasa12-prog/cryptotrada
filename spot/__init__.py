"""
CryptoTrada package exports.
"""
from spot.auto_trader import run_cycle, fast_sl_cycle
from spot.xrp_swing import run_auto_cycle, fast_sl_check, evaluate_setup
from spot.sol_swing import evaluate_sol_swing
from spot.trading_modes import (
    AgentType, AgentConfig, AgentStatus, AgentMetrics, AgentState,
    BaseAgent, AutoTrendAgent, XRPSwingAgent, SOLSwingAgent,
    P2PMarketAgent, ManualAgent, AgentRegistry, EventBus,
    get_agent_registry, get_event_bus, start_all_agents, stop_all_agents,
    is_agent_running, StrategyContext, TradingMode,
)
from spot.positions import get_open_positions
from spot.watchlist import get_watchlist
from spot.streamer import get_prices, start_price_stream
from spot.data_fetcher import load_dataframe, refresh_interval, startup_fetch
from spot.macro import refresh_macro, get_latest_macro
from spot.atmosphere import get_atmosphere

__all__ = [
    "AgentType", "AgentConfig", "AgentStatus", "AgentMetrics", "AgentState",
    "BaseAgent", "AutoTrendAgent", "XRPSwingAgent", "SOLSwingAgent",
    "P2PMarketAgent", "ManualAgent", "AgentRegistry", "EventBus",
    "get_agent_registry", "get_event_bus", "start_all_agents", "stop_all_agents",
    "is_agent_running", "StrategyContext", "TradingMode",
    "run_cycle", "fast_sl_cycle", "run_auto_cycle", "fast_sl_check",
    "evaluate_setup", "evaluate_sol_swing",
    "get_open_positions", "get_watchlist", "get_prices",
    "load_dataframe", "refresh_interval", "startup_fetch",
    "refresh_macro", "get_latest_macro", "get_atmosphere",
    "start_price_stream",
]
