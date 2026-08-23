"""
Agent API Routes
================
REST API endpoints for agent lifecycle management.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from spot.trading_modes import (
    get_agent_registry,
    AgentType,
    AgentConfig,
    AgentStatus,
    AgentState,
)

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ── Request/Response Models ────────────────────────────────────────────────

class AgentConfigUpdate(BaseModel):
    """Request model for updating agent config."""
    enabled: Optional[bool] = None
    main_cycle_interval_sec: Optional[int] = None
    fast_cycle_interval_sec: Optional[int] = None
    config: Optional[dict] = None


class AgentActionResponse(BaseModel):
    """Response model for agent actions."""
    agent_type: str
    state: str
    enabled: bool
    config: dict
    metrics: dict
    error_message: Optional[str] = None


class AllAgentsStatusResponse(BaseModel):
    """Response model for all agents status."""
    agents: dict[str, AgentActionResponse]


# ── Helper Functions ──────────────────────────────────────────────────────

def _get_registry():
    """Get agent registry with context provider."""
    from spot.positions import get_open_positions
    from spot.watchlist import get_watchlist
    from spot.streamer import get_prices
    from spot.macro import get_latest_macro
    from spot.atmosphere import get_atmosphere
    
    def get_context():
        return {
            "positions": get_open_positions(),
            "watchlist": get_watchlist(active_only=True),
            "live_prices": get_prices(),
            "macro_data": get_latest_macro(),
            "atmosphere_data": get_atmosphere(),
        }
    
    return get_agent_registry(get_context)


def _status_to_response(status: AgentStatus) -> AgentActionResponse:
    """Convert AgentStatus to API response."""
    return AgentActionResponse(
        agent_type=status.agent_type.value,
        state=status.state.value,
        enabled=status.enabled,
        config={
            "main_cycle_interval_sec": status.config.main_cycle_interval_sec,
            "fast_cycle_interval_sec": status.config.fast_cycle_interval_sec,
            "config": status.config.config,
        },
        metrics={
            "cycles_completed": status.metrics.cycles_completed,
            "fast_cycles_completed": status.metrics.fast_cycles_completed,
            "last_cycle_at": status.metrics.last_cycle_at,
            "last_fast_cycle_at": status.metrics.last_fast_cycle_at,
            "last_error": status.metrics.last_error,
            "last_error_at": status.metrics.last_error_at,
            "total_actions": status.metrics.total_actions,
            "total_entries": status.metrics.total_entries,
            "total_exits": status.metrics.total_exits,
            "uptime_started_at": status.metrics.uptime_started_at,
        },
        error_message=status.error_message,
    )


# ── API Endpoints ─────────────────────────────────────────────────────────

@router.get("/status", response_model=AllAgentsStatusResponse)
async def get_all_agents_status():
    """Get status of all agents."""
    registry = _get_registry()
    statuses = registry.get_all_status()
    return AllAgentsStatusResponse(
        agents={at.value: _status_to_response(s) for at, s in statuses.items()}
    )


@router.get("/{agent_type}/status", response_model=AgentActionResponse)
async def get_agent_status(agent_type: str):
    """Get status of a specific agent."""
    try:
        at = AgentType(agent_type)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown agent type: {agent_type}")
    
    registry = _get_registry()
    status = registry.get_agent(at).get_status()
    return _status_to_response(status)


@router.post("/{agent_type}/start", response_model=AgentActionResponse)
async def start_agent(agent_type: str):
    """Start a specific agent."""
    try:
        at = AgentType(agent_type)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown agent type: {agent_type}")
    
    registry = _get_registry()
    status = await registry.start_agent(at)
    return _status_to_response(status)


@router.post("/{agent_type}/stop", response_model=AgentActionResponse)
async def stop_agent(agent_type: str):
    """Stop a specific agent."""
    try:
        at = AgentType(agent_type)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown agent type: {agent_type}")
    
    registry = _get_registry()
    status = await registry.stop_agent(at)
    return _status_to_response(status)


@router.post("/{agent_type}/pause", response_model=AgentActionResponse)
async def pause_agent(agent_type: str):
    """Pause a specific agent."""
    try:
        at = AgentType(agent_type)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown agent type: {agent_type}")
    
    registry = _get_registry()
    status = await registry.pause_agent(at)
    return _status_to_response(status)


@router.post("/{agent_type}/resume", response_model=AgentActionResponse)
async def resume_agent(agent_type: str):
    """Resume a paused agent."""
    try:
        at = AgentType(agent_type)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown agent type: {agent_type}")
    
    registry = _get_registry()
    status = await registry.resume_agent(at)
    return _status_to_response(status)


@router.post("/start-all", response_model=AllAgentsStatusResponse)
async def start_all_enabled():
    """Start all enabled agents."""
    registry = _get_registry()
    results = await registry.start_all_enabled()
    return AllAgentsStatusResponse(
        agents={at.value: _status_to_response(s) for at, s in results.items()}
    )


@router.post("/stop-all", response_model=AllAgentsStatusResponse)
async def stop_all_agents():
    """Stop all running agents."""
    registry = _get_registry()
    results = await registry.stop_all()
    return AllAgentsStatusResponse(
        agents={at.value: _status_to_response(s) for at, s in results.items()}
    )


@router.patch("/{agent_type}/config", response_model=AgentActionResponse)
async def update_agent_config(agent_type: str, config_update: AgentConfigUpdate):
    """Update agent configuration."""
    try:
        at = AgentType(agent_type)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown agent type: {agent_type}")
    
    registry = _get_registry()
    
    # Build config dict from non-None fields
    config_dict = {}
    if config_update.enabled is not None:
        config_dict["enabled"] = config_update.enabled
    if config_update.main_cycle_interval_sec is not None:
        config_dict["main_cycle_interval_sec"] = config_update.main_cycle_interval_sec
    if config_update.fast_cycle_interval_sec is not None:
        config_dict["fast_cycle_interval_sec"] = config_update.fast_cycle_interval_sec
    if config_update.config is not None:
        config_dict["config"] = config_update.config
    
    updated_config = registry.update_agent_config(at, config_dict)
    status = registry.get_agent(at).get_status()
    return _status_to_response(status)