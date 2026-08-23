from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from data.database import get_session
from data.models import SpotTrade

router = APIRouter(prefix="/api/journal")


# ── Schemas ───────────────────────────────────────────────────────────────────

class OpenTradeIn(BaseModel):
    symbol: str
    mode: str = "paper"
    direction: str = "long"
    entry_price: float
    size_usd: float
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    hotness_at_entry: Optional[int] = None
    strategy_used: Optional[str] = None
    notes: Optional[str] = None
    trailing_stop_pct: Optional[float] = None


class CloseTradeIn(BaseModel):
    exit_price: float
    notes: Optional[str] = None


def _to_dict(t: SpotTrade) -> dict:
    entry_ts = t.entry_time or t.timestamp
    return {
        "id":                 t.id,
        "symbol":             t.symbol,
        "mode":               t.mode,
        "direction":          t.direction,
        "entry_price":        t.entry_price,
        "exit_price":         t.exit_price,
        "size_usd":           t.size_usd,
        "stop_loss":          t.stop_loss,
        "target":             t.target,
        "pnl_usd":            t.pnl_usd,
        "pnl_pct":            t.pnl_pct,
        "hotness_at_entry":   t.hotness_at_entry,
        "strategy_used":      t.strategy_used,
        "outcome":            t.outcome,
        "entry_time":         entry_ts.isoformat() if entry_ts else None,
        "exit_time":          t.exit_time.isoformat() if t.exit_time else None,
        "notes":              t.notes,
        "status":             "open" if t.exit_price is None else "closed",
        "trailing_stop_pct":  t.trailing_stop_pct,
        "trailing_stop_peak": t.trailing_stop_peak,
    }


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/summary")
def journal_summary():
    with get_session() as s:
        all_trades    = s.query(SpotTrade).all()
        open_trades   = [t for t in all_trades if t.exit_price is None]
        closed_trades = [t for t in all_trades if t.exit_price is not None]
        total_pnl = sum(t.pnl_usd or 0 for t in closed_trades)
        wins      = sum(1 for t in closed_trades if t.outcome == "win")
        losses    = sum(1 for t in closed_trades if t.outcome == "loss")
        win_rate  = round(wins / len(closed_trades) * 100) if closed_trades else None
        best  = round(max((t.pnl_usd or 0 for t in closed_trades), default=0), 2)
        worst = round(min((t.pnl_usd or 0 for t in closed_trades), default=0), 2)
    return {
        "open_count":    len(open_trades),
        "closed_count":  len(closed_trades),
        "total_pnl_usd": round(total_pnl, 2),
        "wins":          wins,
        "losses":        losses,
        "win_rate":      win_rate,
        "best_trade":    best,
        "worst_trade":   worst,
    }


@router.get("/trades")
def list_trades(status: str = "all", symbol: str = ""):
    with get_session() as s:
        q = s.query(SpotTrade).order_by(SpotTrade.timestamp.desc())
        if status == "open":
            q = q.filter(SpotTrade.exit_price.is_(None))
        elif status == "closed":
            q = q.filter(SpotTrade.exit_price.isnot(None))
        if symbol:
            q = q.filter(SpotTrade.symbol == symbol.upper())
        result = [_to_dict(t) for t in q.all()]
    return {"trades": result}


@router.post("/trades")
def open_trade(body: OpenTradeIn):
    with get_session() as s:
        trade = SpotTrade(
            symbol=body.symbol.upper(),
            mode=body.mode,
            direction=body.direction,
            entry_price=body.entry_price,
            size_usd=body.size_usd,
            stop_loss=body.stop_loss,
            target=body.target,
            hotness_at_entry=body.hotness_at_entry,
            strategy_used=body.strategy_used,
            notes=body.notes,
            entry_time=datetime.utcnow(),
            trailing_stop_pct=body.trailing_stop_pct,
        )
        s.add(trade)
        s.flush()
        result = _to_dict(trade)
    return result


@router.patch("/trades/{trade_id}/close")
def close_trade(trade_id: int, body: CloseTradeIn):
    with get_session() as s:
        trade = s.get(SpotTrade, trade_id)
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        if trade.exit_price is not None:
            raise HTTPException(status_code=400, detail="Trade already closed")
        trade.exit_price = body.exit_price
        trade.exit_time  = datetime.utcnow()
        if body.notes:
            trade.notes = body.notes
        pnl_pct       = (body.exit_price - trade.entry_price) / trade.entry_price * 100
        pnl_usd       = trade.size_usd * pnl_pct / 100
        trade.pnl_usd = round(pnl_usd, 2)
        trade.pnl_pct = round(pnl_pct, 2)
        trade.outcome = "win" if pnl_usd > 0.01 else "loss" if pnl_usd < -0.01 else "breakeven"
        result = _to_dict(trade)
    return result


@router.delete("/trades/{trade_id}")
def delete_trade(trade_id: int):
    with get_session() as s:
        trade = s.get(SpotTrade, trade_id)
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        s.delete(trade)
    return {"deleted": trade_id}


class TrailingStopIn(BaseModel):
    pct: float   # e.g. 2.5 for 2.5%


@router.patch("/trades/{trade_id}/trailing-stop")
def set_trailing_stop(trade_id: int, body: TrailingStopIn):
    """Enable or update trailing stop on an already-open trade."""
    if body.pct <= 0:
        raise HTTPException(status_code=400, detail="pct must be positive")
    with get_session() as s:
        trade = s.get(SpotTrade, trade_id)
        if not trade:
            raise HTTPException(status_code=404, detail="Trade not found")
        if trade.exit_price is not None:
            raise HTTPException(status_code=400, detail="Trade already closed")
        trade.trailing_stop_pct  = body.pct
        trade.trailing_stop_peak = None   # reset so next check picks up fresh peak
        result = _to_dict(trade)
    return result
