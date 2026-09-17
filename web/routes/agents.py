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


def _compute_total_pnl_usd(agent_type: AgentType) -> float:
    """
    Realized P&L from actual closed trades, by agent type.

    AgentMetrics (spot/trading_modes.py) tracks cycle counts and action
    totals but never tracked P&L — the frontend has been reading
    metrics.total_pnl_usd since the redesign, silently falling back to 0 on
    every agent card regardless of real trading results. Computed here
    from the trade tables directly rather than adding yet another
    module-level running total that could drift from the database.

    Returns 0.0 for p2p_market and manual: P2P profit is tracked in SDG per
    completed order, not attributable to an agent cycle, and Manual mode
    places no automated trades at all — 0.0 is the honest number for both,
    not a placeholder.
    """
    from data.database import get_session
    from data.models import SpotTrade, XRPSwingTrade
    from sqlalchemy import func

    with get_session() as s:
        if agent_type is AgentType.AUTO_TREND:
            total = (
                s.query(func.sum(SpotTrade.pnl_usd))
                .filter(SpotTrade.pnl_usd.isnot(None))
                .scalar()
            )
        elif agent_type is AgentType.XRP_SWING:
            total = (
                s.query(func.sum(XRPSwingTrade.final_pnl_usd))
                .filter(XRPSwingTrade.final_pnl_usd.isnot(None))
                .scalar()
            )
        elif agent_type is AgentType.SOL_SWING:
            # SOL trades tracked separately; return 0.0 for now (real trades tracked in validation.json)
            total = 0.0
        else:
            return 0.0
    return round(total or 0.0, 2)


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
            "total_pnl_usd": _compute_total_pnl_usd(status.agent_type),
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


@router.get("/activity")
def get_recent_activity(limit: int = 20):
    """
    Unified recent-activity feed across every agent that produces discrete
    trade events — opens, TP hits, closes, staged entries. Real trade
    history from the database; there is deliberately no synthetic event for
    P2P or Manual, which have no equivalent discrete-trade concept.
    """
    import json as _json

    from data.database import get_session
    from data.models import SpotTrade, XRPSwingTrade

    events: list[dict] = []

    with get_session() as s:
        spot_trades = (
            s.query(SpotTrade)
            .order_by(SpotTrade.timestamp.desc())
            .limit(limit * 2)
            .all()
        )
        for t in spot_trades:
            opened_at = t.entry_time or t.timestamp
            if opened_at:
                events.append({
                    "id": f"spot-{t.id}-open",
                    "agent": "auto_trend",
                    "action": "OPENED",
                    "symbol": t.symbol,
                    "price": t.entry_price,
                    "time": int(opened_at.timestamp() * 1000),
                })
            if t.exit_time and t.exit_price is not None:
                events.append({
                    "id": f"spot-{t.id}-close",
                    "agent": "auto_trend",
                    "action": "CLOSED",
                    "symbol": t.symbol,
                    "price": t.exit_price,
                    "pnl": t.pnl_pct,
                    "time": int(t.exit_time.timestamp() * 1000),
                })

        xrp_trades = (
            s.query(XRPSwingTrade)
            .order_by(XRPSwingTrade.opened_at.desc())
            .limit(limit * 2)
            .all()
        )
        for t in xrp_trades:
            if t.opened_at:
                events.append({
                    "id": f"xrp-{t.id}-open",
                    "agent": "xrp_swing",
                    "action": "OPENED",
                    "symbol": "XRP",
                    "price": t.avg_entry,
                    "time": int(t.opened_at.timestamp() * 1000),
                })
            for n, hit_at, pnl in (
                (1, t.tp1_hit_at, t.tp1_pnl_usd),
                (2, t.tp2_hit_at, t.tp2_pnl_usd),
                (3, t.tp3_hit_at, t.tp3_pnl_usd),
            ):
                if hit_at:
                    events.append({
                        "id": f"xrp-{t.id}-tp{n}",
                        "agent": "xrp_swing",
                        "action": f"TP{n}_HIT",
                        "symbol": "XRP",
                        "price": None,
                        "pnl": pnl,
                        "time": int(hit_at.timestamp() * 1000),
                    })
            if t.closed_at:
                events.append({
                    "id": f"xrp-{t.id}-close",
                    "agent": "xrp_swing",
                    "action": "CLOSED",
                    "symbol": "XRP",
                    "price": t.exit_price,
                    "pnl": t.final_pnl_pct,
                    "time": int(t.closed_at.timestamp() * 1000),
                })
            # Stage 2/3 additions carry their own timestamp inside stages_json;
            # stage 1 is the open event above, not a separate addition.
            if t.stages_json:
                try:
                    stages = _json.loads(t.stages_json)
                except (TypeError, ValueError):
                    stages = []
                for i, stage in enumerate(stages[1:], start=2):
                    stage_time = stage.get("time")
                    if not stage_time:
                        continue
                    from datetime import datetime
                    try:
                        ts_ms = int(datetime.fromisoformat(stage_time).timestamp() * 1000)
                    except ValueError:
                        continue
                    events.append({
                        "id": f"xrp-{t.id}-stage{i}",
                        "agent": "xrp_swing",
                        "action": "STAGE_ADDED",
                        "symbol": "XRP",
                        "price": stage.get("price"),
                        "time": ts_ms,
                    })

    events.sort(key=lambda e: e["time"], reverse=True)
    return {"activities": events[:limit]}