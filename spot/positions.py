"""
Open spot position helpers — reads live journal trades for P&L display and alert checks.
"""
from __future__ import annotations

from data.database import get_session
from data.models import SpotTrade


def get_open_positions() -> list[dict]:
    """Return all open SpotTrade records (no exit price yet), newest first."""
    with get_session() as s:
        trades = (
            s.query(SpotTrade)
             .filter(SpotTrade.exit_price == None)
             .order_by(SpotTrade.entry_time.desc())
             .all()
        )
        return [
            {
                "id":                 t.id,
                "symbol":             t.symbol,
                "mode":               t.mode,
                "direction":          t.direction,
                "entry_price":        t.entry_price,
                "size_usd":           t.size_usd,
                "stop_loss":          t.stop_loss,
                "target":             t.target,
                "hotness_at_entry":   t.hotness_at_entry,
                "strategy_used":      t.strategy_used,
                "entry_time":         t.entry_time.isoformat() if t.entry_time else None,
                "notes":              t.notes,
                "trailing_stop_pct":  t.trailing_stop_pct,
                "trailing_stop_peak": t.trailing_stop_peak,
                "tp1_pnl_usd":        t.tp1_pnl_usd,
            }
            for t in trades
        ]


def update_trailing_peak(trade_id: int, peak: float) -> None:
    """Persist the new highest price seen for a position's trailing stop."""
    with get_session() as s:
        trade = s.get(SpotTrade, trade_id)
        if trade and trade.exit_price is None:
            trade.trailing_stop_peak = peak


def update_stop_loss(trade_id: int, new_sl: float) -> None:
    """Move the stop-loss on an open position (used for breakeven stop)."""
    with get_session() as s:
        trade = s.get(SpotTrade, trade_id)
        if trade and trade.exit_price is None:
            trade.stop_loss = round(new_sl, 6)


def apply_tp1(trade_id: int, new_size_usd: float, entry_price: float, tp1_price: float) -> None:
    """Partial TP1: halve size, raise SL to entry, clear fixed target so runner trails freely.
    Records the banked 50% gain in tp1_pnl_usd so the final close includes the full position P&L."""
    with get_session() as s:
        trade = s.get(SpotTrade, trade_id)
        if trade and trade.exit_price is None:
            locked_size   = (trade.size_usd or 0) - new_size_usd  # the half being banked
            banked_pnl    = round(locked_size * (tp1_price - entry_price) / entry_price, 4)
            trade.size_usd    = round(new_size_usd, 2)
            trade.stop_loss   = round(entry_price, 6)
            trade.target      = None
            trade.tp1_pnl_usd = banked_pnl
            trade.notes = (trade.notes or "") + (
                f" | TP1 hit — runner active (50% banked ${banked_pnl:+.2f}, SL → entry)"
            )


def update_trailing_pct(trade_id: int, new_trail_pct: float) -> None:
    """Update the trailing stop percentage on an open position."""
    with get_session() as s:
        trade = s.get(SpotTrade, trade_id)
        if trade and trade.exit_price is None:
            trade.trailing_stop_pct = round(new_trail_pct, 2)
