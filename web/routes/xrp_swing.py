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


@router.post("/auto/run-now")
def run_auto_now():
    """Trigger an immediate auto-cycle (evaluate + monitor + auto-open if ready)."""
    from spot.xrp_swing import run_auto_cycle, evaluate_setup
    evaluate_setup(store=True)   # refresh stored verdict first
    return run_auto_cycle()
