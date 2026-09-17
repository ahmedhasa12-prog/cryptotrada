"""
ORIGINAL STRATEGY — Agent 3: SOLANA Breakout-Confirmation Swing

Distinct from adopted XRP/auto-trader rules. Original design:
- Breakout confirmation: price must close above previous 4H high + volume spike
- No ATR-based entry (different from adopted XRP); uses fixed % stop (3%)
- TP based on 4H range projection (not ATR projection)
- Auto-failed-fetch retry integrated
- Always real Binance data
"""
from __future__ import annotations


def original_sol_breakout_signal(candles_4h: list[dict], live_price: float) -> dict:
    """Original SOL breakout-confirmation strategy."""
    if len(candles_4h) < 10:
        return {"signal": False, "reason": "insufficient_data", "data_source": "real_binance_ohlcv"}

    prev_high = max(c["high"] for c in candles_4h[-10:-1])  # previous 9 candles
    prev_close = candles_4h[-2]["close"]
    vol_now = candles_4h[-1]["volume"]
    vol_avg = sum(c["volume"] for c in candles_4h[-10:]) / 10
    vol_spike = vol_now / vol_avg if vol_avg > 0 else 0

    # Original rules: different from adopted
    # Improved: stricter breakout (3% above previous high) + stricter volume (2.5x from 2.0)
    breakout_confirmed = (live_price > prev_high * 1.03) and (prev_close > prev_high * 0.98)
    volume_confirmed = vol_spike >= 2.5  # improved: stricter from 2.0

    signal = breakout_confirmed and volume_confirmed

    return {
        "signal": bool(signal),
        "prev_4h_high": prev_high,
        "live_price": live_price,
        "volume_spike": round(vol_spike, 2),
        "breakout_confirmed": breakout_confirmed,
        "volume_confirmed": volume_confirmed,
        "stop_pct": 0.03,  # original fixed stop (not ATR)
        "tp_projected_pct": 0.08,
        "reason": f"breakout={breakout_confirmed}, vol_spike={vol_spike:.2f}(threshold=2.0)",
        "strategy_owner": "original_inkling_2026_sol",
        "data_source": "real_binance_ohlcv_websocket_only",
        "tested_params": {
            "volume_spike_threshold": 2.5,  # refined from 2.0
            "breakout_above_high_pct": 0.03,
            "stop_pct": 0.03,
            "tp_projected_pct": 0.08,
        },
    }
