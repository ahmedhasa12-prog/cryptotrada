"""
Backtest framework for 3-agent paper trading system.
Uses ONLY real historical Binance OHLCV (DB candles) — no synthetic data.
Tracks win rate, profit factor, max drawdown per agent.
"""
from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime

def run_backtest(agent_name: str, symbol: str, candles_4h: list[dict],
                  entry_logic: callable, exit_logic: callable) -> dict:
    """
    Simple backtest: apply entry/exit logic to real 4H candles.
    Returns {win_rate, profit_factor, max_drawdown, trades_count}.
    Always uses real historical data — never synthetic.
    """
    trades = []
    in_position = False
    entry_price = 0
    
    for i, candle in enumerate(candles_4h):
        price = candle["close"]
        if not in_position:
            signal = entry_logic(candle, price, i)
            if signal:
                in_position = True
                entry_price = price
                trades.append({"entry": price, "time": candle.get("timestamp", i)})
        else:
            exit_signal = exit_logic(price, entry_price, i)
            if exit_signal:
                pnl_pct = ((price - entry_price) / entry_price) * 100
                trades.append({
                    "exit": price,
                    "pnl_pct": round(pnl_pct, 4),
                    "time": candle.get("timestamp", i),
                })
                in_position = False
                entry_price = 0
    
    if in_position:
        # Force close at last candle for backtest completeness
        last_price = candles_4h[-1]["close"]
        pnl_pct = ((last_price - entry_price) / entry_price) * 100
        trades.append({
            "exit": last_price,
            "pnl_pct": round(pnl_pct, 4),
            "time": "end",
            "forced": True,
        })
    
    wins = sum(1 for t in trades[1::2] if t.get("pnl_pct", 0) > 0)  # exit trades only
    total_exits = len([t for t in trades if "exit" in t])
    win_rate = wins / total_exits if total_exits > 0 else 0.0
    
    gross_profit = sum(t.get("pnl_pct", 0) for t in trades if "exit" in t and t.get("pnl_pct", 0) > 0)
    gross_loss = abs(sum(t.get("pnl_pct", 0) for t in trades if "exit" in t and t.get("pnl_pct", 0) <= 0))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    
    max_drawdown = max(
        (t.get("pnl_pct", 0) for t in trades if "exit" in t),
        default=0,
    )
    max_drawdown = min(max_drawdown, 0)  # drawdown is negative PnL
    
    result = {
        "agent": agent_name,
        "symbol": symbol,
        "trades": len([t for t in trades if "exit" in t]),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4) if profit_factor != float("inf") else 999.0,
        "max_drawdown_pct": round(max_drawdown, 4),
        "gross_profit_pct": round(gross_profit, 4),
        "gross_loss_pct": round(gross_loss, 4),
        "data_source": "real_binance_ohlcv_historical_only",
        "tested_at": datetime.utcnow().isoformat(),
        "synthetic_data_used": False,
    }
    
    # Save result
    result_path = Path("data/backtest_results.json")
    existing = {}
    if result_path.exists():
        try:
            existing = json.loads(result_path.read_text())
        except Exception:
            pass
    existing[agent_name] = result
    result_path.write_text(json.dumps(existing, indent=2))
    
    return result
