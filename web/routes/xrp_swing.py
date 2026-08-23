"""XRP Swing Strategy — API routes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/xrp-swing")


@router.get("/status")
def get_status():
    """Current evaluation + active trade (if any)."""
    from datetime import datetime, timedelta
    from spot.xrp_swing import get_latest_setup, get_active_trade
    from data.database import get_session
    from data.models import MacroSnapshot
    from sqlalchemy import desc

    setup = get_latest_setup()
    trade = get_active_trade()

    # Macro freshness + 3-day trajectory for F&G and BTC.D
    macro_age_minutes = None
    fg_3d_change = None
    dom_3d_change = None
    with get_session() as s:
        latest_snap = s.query(MacroSnapshot).order_by(desc(MacroSnapshot.id)).first()
        if latest_snap and latest_snap.timestamp:
            macro_age_minutes = round((datetime.utcnow() - latest_snap.timestamp).total_seconds() / 60, 1)
            cutoff = latest_snap.timestamp - timedelta(days=3)
            old_snap = (
                s.query(MacroSnapshot)
                .filter(MacroSnapshot.timestamp <= cutoff)
                .order_by(desc(MacroSnapshot.id))
                .first()
            )
            if old_snap:
                if latest_snap.fear_greed_value is not None and old_snap.fear_greed_value is not None:
                    fg_3d_change = latest_snap.fear_greed_value - old_snap.fear_greed_value
                if latest_snap.btc_dominance is not None and old_snap.btc_dominance is not None:
                    dom_3d_change = round(latest_snap.btc_dominance - old_snap.btc_dominance, 3)

    return {
        "setup": setup,
        "active_trade": trade,
        "has_active_trade": trade is not None,
        "macro_age_minutes": macro_age_minutes,
        "macro_stale": macro_age_minutes is not None and macro_age_minutes > 120,
        "fg_3d_change":  fg_3d_change,
        "dom_3d_change": dom_3d_change,
    }


@router.post("/evaluate")
def trigger_evaluate():
    """Force an immediate 3-layer evaluation and store the result."""
    from spot.xrp_swing import evaluate_setup
    try:
        result = evaluate_setup(store=True)
        return {"ok": True, "result": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/setups")
def get_setup_history(limit: int = 30):
    """Recent stored setup evaluations."""
    from spot.xrp_swing import get_setup_history
    return get_setup_history(limit=min(limit, 200))


@router.get("/trades")
def get_trade_history(limit: int = 30):
    """Closed XRP swing trades."""
    from spot.xrp_swing import get_trade_history
    return get_trade_history(limit=min(limit, 200))


@router.get("/active-trade")
def get_active_trade_route():
    """Active open trade detail."""
    from spot.xrp_swing import get_active_trade
    trade = get_active_trade()
    return {"active_trade": trade}


class OpenTradeBody(BaseModel):
    setup_type: str       # A | B | C
    stage1_price: float
    stage1_size_usd: float
    stop: float
    tp1: float
    tp2: float
    notes: str = ""


@router.post("/open-trade")
def open_trade_route(body: OpenTradeBody):
    """Open a new XRP swing trade (stage 1 entry)."""
    from spot.xrp_swing import get_active_trade, open_trade
    if get_active_trade():
        raise HTTPException(status_code=409, detail="Already have an open XRP swing trade")
    try:
        trade = open_trade(
            setup_type=body.setup_type,
            stage1_price=body.stage1_price,
            stage1_size_usd=body.stage1_size_usd,
            stop=body.stop,
            tp1=body.tp1,
            tp2=body.tp2,
            notes=body.notes,
        )
        return {"ok": True, "trade": trade}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class AddStageBody(BaseModel):
    trade_id: int
    price: float
    size_usd: float


@router.post("/add-stage")
def add_stage_route(body: AddStageBody):
    """Add stage 2 or 3 entry to an open trade."""
    from spot.xrp_swing import add_stage
    try:
        trade = add_stage(body.trade_id, body.price, body.size_usd)
        return {"ok": True, "trade": trade}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class HitTPBody(BaseModel):
    trade_id: int
    tp_num: int       # 1 or 2
    close_price: float


@router.post("/hit-tp")
def hit_tp_route(body: HitTPBody):
    """Mark TP1 or TP2 as hit. Moves stop to BE after TP1, enables trailing after TP2."""
    from spot.xrp_swing import hit_tp
    if body.tp_num not in (1, 2):
        raise HTTPException(status_code=400, detail="tp_num must be 1 or 2")
    try:
        trade = hit_tp(body.trade_id, body.tp_num, body.close_price)
        return {"ok": True, "trade": trade}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class UpdateStopBody(BaseModel):
    trade_id: int
    new_stop: float


@router.post("/update-stop")
def update_stop_route(body: UpdateStopBody):
    """Manually adjust the stop loss on an open trade."""
    from spot.xrp_swing import update_stop
    try:
        trade = update_stop(body.trade_id, body.new_stop)
        return {"ok": True, "trade": trade}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


class CloseTradeBody(BaseModel):
    trade_id: int
    exit_price: float
    reason: str = "manual"   # manual | sl | tp | timeout


@router.post("/close-trade")
def close_trade_route(body: CloseTradeBody):
    """Close the open trade and record final P&L."""
    from spot.xrp_swing import close_trade
    try:
        trade = close_trade(body.trade_id, body.exit_price, body.reason)
        return {"ok": True, "trade": trade}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/weekly-review")
def get_weekly_review():
    """Generate the weekly XRP swing condition review text."""
    from spot.xrp_swing import generate_weekly_review
    try:
        text = generate_weekly_review()
        return {"review": text}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/level-alerts")
def get_level_alerts():
    """Check if XRP price is near any key support/resistance level."""
    from spot.xrp_swing import check_level_alerts
    from spot.streamer import get_prices
    prices = get_prices()
    xrp = prices.get("XRP") or {}
    price = xrp.get("price") if isinstance(xrp, dict) else None
    if price is None:
        return {"alerts": [], "xrp_price": None}
    alerts = check_level_alerts(price)
    return {"alerts": alerts, "xrp_price": price}


# ── Auto-bot ──────────────────────────────────────────────────────────────────

@router.get("/auto-status")
def get_auto_status_route():
    """Auto-bot enabled state, last action, and current verdict."""
    from spot.xrp_swing import get_auto_status
    return get_auto_status()


class AutoEnableBody(BaseModel):
    size_usd: float = 300.0


@router.post("/auto/enable")
def enable_auto_route(body: AutoEnableBody):
    """Enable auto-trading. size_usd sets the Stage 1 position size."""
    from spot.xrp_swing import enable_auto
    if body.size_usd < 10 or body.size_usd > 10000:
        raise HTTPException(status_code=400, detail="size_usd must be between 10 and 10000")
    return enable_auto(body.size_usd)


@router.post("/auto/disable")
def disable_auto_route():
    """Disable auto-trading (monitoring of open trades continues)."""
    from spot.xrp_swing import disable_auto
    return disable_auto()


@router.post("/auto/shadow/enable")
def enable_shadow_mode_route():
    """
    Turn shadow mode on: approved entries are logged to the risk decision
    audit trail but never actually opened. This is the default state — this
    route exists to go back to it after shadow mode has been turned off.
    """
    from spot.xrp_swing import enable_shadow_mode
    return enable_shadow_mode()


@router.post("/auto/shadow/disable")
def disable_shadow_mode_route():
    """
    Turn shadow mode off: approved entries will actually call open_trade()
    and place real positions. A deliberate, separate step from enabling
    auto-trading itself — read the risk decision log before flipping this.
    """
    from spot.xrp_swing import disable_shadow_mode
    return disable_shadow_mode()


@router.post("/auto/run-now")
def run_auto_now():
    """Trigger an immediate auto-cycle (evaluate + monitor + auto-open if ready)."""
    from spot.xrp_swing import run_auto_cycle, evaluate_setup
    evaluate_setup(store=True)   # refresh stored verdict first
    return run_auto_cycle()


@router.get("/risk-decisions")
def get_risk_decisions(limit: int = 30):
    """
    Audit trail of every auto-open the risk supervisor has considered,
    approved or vetoed, most recent first — with the full per-gate
    pass/fail breakdown so the UI can show exactly why.
    """
    import json
    from data.database import get_session
    from data.models import XRPRiskDecision
    from spot.xrp_risk.reasons import VetoReason
    from sqlalchemy import desc

    with get_session() as s:
        rows = (
            s.query(XRPRiskDecision)
            .order_by(desc(XRPRiskDecision.id))
            .limit(min(limit, 200))
            .all()
        )
        decisions = []
        for row in rows:
            try:
                checks = json.loads(row.checks_json) if row.checks_json else []
            except (TypeError, ValueError):
                checks = []
            for check in checks:
                if check.get("reason"):
                    try:
                        check["reason_explain"] = VetoReason(check["reason"]).explain
                    except ValueError:
                        check["reason_explain"] = None
            decisions.append({
                "id": row.id,
                "decided_at": row.decided_at.isoformat() if row.decided_at else None,
                "setup_type": row.setup_type,
                "eval_id": row.eval_id,
                "entry_price": row.entry_price,
                "requested_size_usd": row.requested_size_usd,
                "final_size_usd": row.final_size_usd,
                "stop": row.stop,
                "tp1": row.tp1,
                "tp2": row.tp2,
                "tp3": row.tp3,
                "rr_ratio": row.rr_ratio,
                "approved": row.approved,
                "veto_reason": row.veto_reason,
                "veto_reason_explain": (
                    VetoReason(row.veto_reason).explain
                    if row.veto_reason and row.veto_reason in VetoReason._value2member_map_
                    else None
                ),
                "detail": row.detail,
                "checks": checks,
                "shadowed": row.shadowed,
            })
        return {"decisions": decisions}
