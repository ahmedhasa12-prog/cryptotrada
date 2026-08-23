"""
Closed-bar backtester with fee + slippage modeling and walk-forward splitting.

Design rules (per the guide):
- Signals are generated on CLOSED bars only — the signal_idx is the bar that
  closed and triggered, entry is at the OPEN of the NEXT bar (signal_idx + 1).
- Within a bar where both stop and target are hit, stop wins (pessimistic).
- Fees applied both entry and exit (taker fee each side).
- Slippage applied on entry only (market order assumption).
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

_DB_PATH = Path(__file__).parent.parent / "data" / "trading.db"

FEE_PCT    = 0.001   # 0.1% Binance spot taker each side
SLIP_PCT   = 0.0005  # 0.05% slippage on entry (conservative)


# ── Data loading ──────────────────────────────────────────────────────────────

def load_candles(
    symbol: str,
    interval: str = "1h",
    start: str | None = None,
    end:   str | None = None,
) -> pd.DataFrame:
    """Load OHLCV + taker from DB into a clean DataFrame, sorted by timestamp."""
    con = sqlite3.connect(_DB_PATH)
    q = "SELECT timestamp, open, high, low, close, volume, taker_buy_base FROM ohlcv_candles WHERE symbol=? AND interval=?"
    params: list = [symbol, interval]
    if start:
        q += " AND timestamp >= ?"; params.append(start)
    if end:
        q += " AND timestamp < ?";  params.append(end)
    q += " ORDER BY timestamp"
    df = pd.read_sql_query(q, con, params=params, parse_dates=["timestamp"])
    con.close()
    df = df.set_index("timestamp").sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def add_primitives(df: pd.DataFrame) -> pd.DataFrame:
    """Add candle primitives and indicators (all backward-looking, no lookahead)."""
    df = df.copy()
    hi_oc = df[["open", "close"]].max(axis=1)
    lo_oc = df[["open", "close"]].min(axis=1)

    df["body"]       = (df["close"] - df["open"]).abs()
    df["upper_wick"] = df["high"] - hi_oc
    df["lower_wick"] = lo_oc - df["low"]
    df["range"]      = df["high"] - df["low"]
    df["is_bull"]    = df["close"] > df["open"]
    df["body_pct"]   = df["body"] / df["close"]       # body as fraction of price

    # taker buy ratio — handle zero volume rows
    df["taker_buy_pct"] = np.where(
        df["volume"] > 0,
        df["taker_buy_base"] / df["volume"],
        np.nan,
    )

    # indicators (backward-looking)
    df["ema50"]     = df["close"].ewm(span=50, adjust=False).mean()
    df["ema200"]    = df["close"].ewm(span=200, adjust=False).mean()
    df["vol_sma20"] = df["volume"].rolling(20, min_periods=10).mean()

    return df


def label_regimes(df: pd.DataFrame, slope_window: int = 50, threshold: float = 0.002) -> pd.Series:
    """
    Label each bar as 'bull', 'bear', or 'chop' using the slope of EMA200.

    slope_window : bars over which to measure the EMA200's direction
                   (50 × 4H = ~8 days — medium-term trend)
    threshold    : minimum absolute slope per bar to qualify as trending
                   (0.002 = 0.2% per bar; tune if needed)

    Returns a Series aligned to df.index with values 'bull'/'bear'/'chop'.
    """
    ema200 = df["close"].ewm(span=200, adjust=False).mean()
    slope  = (ema200 - ema200.shift(slope_window)) / ema200.shift(slope_window)
    regime = np.where(slope >  threshold, "bull",
             np.where(slope < -threshold, "bear", "chop"))
    return pd.Series(regime, index=df.index, name="regime")


def resample_candles(df: pd.DataFrame, rule: str = "4h") -> pd.DataFrame:
    """
    Resample 1H (or any base) OHLCV DataFrame to a coarser interval.
    Equivalent to Binance's own 4H candles — no extra API calls needed.
    """
    resampled = df.resample(rule, label="left", closed="left").agg({
        "open":           "first",
        "high":           "max",
        "low":            "min",
        "close":          "last",
        "volume":         "sum",
        "taker_buy_base": "sum",
    }).dropna(subset=["open"])
    return resampled


def walk_forward_split(
    df: pd.DataFrame,
    test_start: str = "2024-06-01",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split into train (in-sample) and test (out-of-sample) by date."""
    ts = pd.Timestamp(test_start)
    return df[df.index < ts].copy(), df[df.index >= ts].copy()


# ── Trade simulation ──────────────────────────────────────────────────────────

def summarise_by_regime(trades: list[dict]) -> dict:
    """Break down trade results by regime label ('bull'/'bear'/'chop')."""
    from collections import defaultdict
    buckets: dict[str, list] = defaultdict(list)
    for t in trades:
        buckets[t.get("regime", "unknown")].append(t)
    return {regime: summarise(ts, label=regime) for regime, ts in sorted(buckets.items())}


def bars_since_regime_flip(
    df: pd.DataFrame,
    slope_window: int = 50,
    threshold: float = 0.002,
) -> pd.Series:
    """For each bar, return how many bars have elapsed since the regime last changed."""
    regimes = label_regimes(df, slope_window, threshold)
    changed = (regimes != regimes.shift(1)).fillna(True)
    group_id = changed.cumsum()
    streak = group_id.groupby(group_id).cumcount()
    return pd.Series(streak.values, index=df.index, name="bars_since_flip")


def simulate_trades(
    df: pd.DataFrame,
    signals: list[dict],
    position_usd: float  = 1000.0,
    rr_target:    float  = 2.0,
    max_bars_held: int   = 10,
    fee_pct:      float  = FEE_PCT,
    slip_pct:     float  = SLIP_PCT,
    regime_gate:  str | None = None,  # if set, skip entries not in this regime
) -> list[dict]:
    """
    Simulate each signal against the candle data.

    Each signal dict must contain:
        signal_idx   : integer position (iloc) of the signal candle (last red / trigger bar)
        stop_price   : hard stop price (below entry for long)
        direction    : 'long' only for now

    regime_gate: when provided, only enter trades where the regime at the signal bar
                 matches this value ('bull'/'bear'/'chop'). This is a causal filter —
                 the regime is computed from data available at signal time only.

    Returns list of trade dicts with full P&L accounting.
    Includes mfe_r / mae_r (max favourable / adverse excursion in R units).
    """
    bars = df.reset_index()   # work with integer index
    n    = len(bars)
    trades = []

    # Pre-compute regime labels if not already in df
    if "regime" in df.columns:
        regime_series = df["regime"]
    else:
        regime_series = label_regimes(df)

    for sig in signals:
        sidx = sig["signal_idx"]
        stop = sig["stop_price"]

        entry_idx = sidx + 1
        if entry_idx >= n:
            continue                      # signal at end of data — skip

        # Regime at signal bar (the trigger candle, not the entry bar)
        sig_ts  = bars.iloc[sidx]["timestamp"]
        regime  = regime_series.get(sig_ts, "unknown") if hasattr(regime_series, "get") \
                  else (regime_series.iloc[sidx] if sidx < len(regime_series) else "unknown")

        # Causal regime gate — skip entry if not in required regime
        if regime_gate and regime != regime_gate:
            continue

        direction  = sig.get("direction", "long")
        entry_bar  = bars.iloc[entry_idx]
        entry_raw  = entry_bar["open"]

        # Slippage: unfavourable direction for each side
        if direction == "long":
            entry = entry_raw * (1 + slip_pct)   # buy slightly higher
        else:
            entry = entry_raw * (1 - slip_pct)   # sell slightly lower

        if direction == "long":
            if entry <= stop:
                continue                  # gap-down past stop — skip
            risk   = entry - stop
            target = entry + risk * rr_target
        else:
            if entry >= stop:
                continue                  # gap-up past stop — skip
            risk   = stop - entry
            target = entry - risk * rr_target

        if risk <= 0:
            continue

        size_coins = position_usd / entry
        entry_fee  = position_usd * fee_pct

        outcome    = "timeout"
        exit_price = None
        exit_idx   = None

        # MAE/MFE tracking (in price terms; converted to R at end)
        mfe_price = entry   # max favourable price reached
        mae_price = entry   # max adverse price reached

        for i in range(entry_idx + 1, min(entry_idx + 1 + max_bars_held, n)):
            bar = bars.iloc[i]

            if direction == "long":
                stopped = bar["low"]  <= stop
                hit_tgt = bar["high"] >= target
                mfe_price = max(mfe_price, bar["high"])
                mae_price = min(mae_price, bar["low"])
            else:
                stopped = bar["high"] >= stop
                hit_tgt = bar["low"]  <= target
                mfe_price = min(mfe_price, bar["low"])   # lower is favourable for short
                mae_price = max(mae_price, bar["high"])  # higher is adverse for short

            if stopped and hit_tgt:
                # pessimistic: stop wins when both occur in the same bar
                outcome    = "loss"
                exit_price = stop
                exit_idx   = i
                break
            elif stopped:
                outcome    = "loss"
                exit_price = stop
                exit_idx   = i
                break
            elif hit_tgt:
                outcome    = "win"
                exit_price = target
                exit_idx   = i
                break
        else:
            last_i     = min(entry_idx + max_bars_held, n - 1)
            exit_price = bars.iloc[last_i]["close"]
            exit_idx   = last_i
            outcome    = "timeout"

        exit_value = size_coins * abs(exit_price)
        exit_fee   = exit_value * fee_pct

        if direction == "long":
            pnl_gross = (exit_price - entry) * size_coins
            mfe_r = (mfe_price - entry) / risk if risk > 0 else 0
            mae_r = (entry - mae_price) / risk if risk > 0 else 0
        else:
            pnl_gross = (entry - exit_price) * size_coins
            mfe_r = (entry - mfe_price) / risk if risk > 0 else 0
            mae_r = (mae_price - entry) / risk if risk > 0 else 0

        pnl_net   = pnl_gross - entry_fee - exit_fee
        actual_rr = pnl_gross / (risk * size_coins) if risk > 0 else 0

        trades.append({
            "symbol":       sig.get("symbol", ""),
            "signal_time":  bars.iloc[sidx]["timestamp"],
            "entry_time":   entry_bar["timestamp"],
            "exit_time":    bars.iloc[exit_idx]["timestamp"],
            "entry_price":  round(entry, 6),
            "exit_price":   round(exit_price, 6),
            "stop_price":   round(stop, 6),
            "target_price": round(target, 6),
            "outcome":      outcome,
            "pnl_gross":    round(pnl_gross, 4),
            "fees":         round(entry_fee + exit_fee, 4),
            "pnl_net":      round(pnl_net, 4),
            "actual_rr":    round(actual_rr, 3),
            "bars_held":    exit_idx - entry_idx,
            "regime":       regime,
            "mfe_r":        round(mfe_r, 3),
            "mae_r":        round(mae_r, 3),
        })

    return trades


# ── Results summary ───────────────────────────────────────────────────────────

def summarise(trades: list[dict], label: str = "") -> dict:
    """Compute aggregate statistics from a list of trade dicts."""
    if not trades:
        return {"label": label, "total_trades": 0}

    wins     = [t for t in trades if t["outcome"] == "win"]
    losses   = [t for t in trades if t["outcome"] == "loss"]
    timeouts = [t for t in trades if t["outcome"] == "timeout"]

    gross_profit = sum(t["pnl_gross"] for t in wins)
    gross_loss   = abs(sum(t["pnl_gross"] for t in losses + timeouts))
    total_fees   = sum(t["fees"] for t in trades)
    net_pnl      = sum(t["pnl_net"] for t in trades)

    # equity curve for drawdown
    equity = np.cumsum([t["pnl_net"] for t in trades])
    running_max = np.maximum.accumulate(equity)
    drawdowns   = equity - running_max
    max_dd      = float(drawdowns.min()) if len(drawdowns) else 0.0

    return {
        "label":          label,
        "total_trades":   len(trades),
        "wins":           len(wins),
        "losses":         len(losses),
        "timeouts":       len(timeouts),
        "win_rate":       round(len(wins) / len(trades) * 100, 1),
        "net_pnl_usd":    round(net_pnl, 2),
        "total_fees_usd": round(total_fees, 2),
        "profit_factor":  round(gross_profit / gross_loss, 3) if gross_loss else float("inf"),
        "expectancy_usd": round(net_pnl / len(trades), 2),
        "avg_win_usd":    round(sum(t["pnl_net"] for t in wins) / len(wins), 2) if wins else 0,
        "avg_loss_usd":   round(sum(t["pnl_net"] for t in losses) / len(losses), 2) if losses else 0,
        "max_drawdown_usd": round(max_dd, 2),
    }


def print_summary(s: dict) -> None:
    label = s.get("label", "")
    if s.get("total_trades", 0) == 0:
        print(f"  [{label}] No trades.")
        return
    print(f"\n  ── {label} ──")
    print(f"  Trades:      {s['total_trades']}  ({s['wins']}W / {s['losses']}L / {s['timeouts']}T)")
    print(f"  Win rate:    {s['win_rate']}%")
    print(f"  Net P&L:     ${s['net_pnl_usd']:+.2f}  (fees ${s['total_fees_usd']:.2f})")
    print(f"  Expectancy:  ${s['expectancy_usd']:+.2f} per trade")
    print(f"  Profit factor: {s['profit_factor']}")
    print(f"  Max drawdown:  ${s['max_drawdown_usd']:.2f}")
    aw = s['avg_win_usd']; al = s['avg_loss_usd']
    aw_str = f"${aw:+.2f}" if isinstance(aw, (int, float)) else str(aw)
    al_str = f"${al:+.2f}" if isinstance(al, (int, float)) else str(al)
    print(f"  Avg win:     {aw_str}   Avg loss: {al_str}")
