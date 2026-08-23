"""
Technical analysis: indicators, higher-lows detection, support/resistance.
All functions are pure (no DB access) — they work on pandas DataFrames.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import ta


# ── Indicators ────────────────────────────────────────────────────────────────

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Add RSI, MACD, EMAs, Bollinger Bands, volume metrics to a candle DataFrame."""
    if len(df) < 20:
        return df

    close = df["close"]
    vol   = df["volume"]

    # RSI (14)
    df["rsi"] = ta.momentum.RSIIndicator(close, window=14).rsi()

    # MACD
    _macd = ta.trend.MACD(close)
    df["macd"]         = _macd.macd()
    df["macd_signal"]  = _macd.macd_signal()
    df["macd_hist"]    = _macd.macd_diff()
    df["macd_bullish"] = df["macd"] > df["macd_signal"]

    # EMAs
    df["ema_20"]  = ta.trend.EMAIndicator(close, window=20).ema_indicator()
    df["ema_50"]  = ta.trend.EMAIndicator(close, window=50).ema_indicator()
    df["ema_200"] = ta.trend.EMAIndicator(close, window=200).ema_indicator()

    # Bollinger Bands
    _bb = ta.volatility.BollingerBands(close)
    df["bb_upper"] = _bb.bollinger_hband()
    df["bb_lower"] = _bb.bollinger_lband()
    df["bb_mid"]   = _bb.bollinger_mavg()
    bb_range = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    df["bb_position"] = (close - df["bb_lower"]) / bb_range

    # Volume
    df["vol_sma_20"] = vol.rolling(20).mean()
    df["vol_ratio"]  = vol / df["vol_sma_20"].replace(0, np.nan)

    # Taker buy ratio (aggressive buyers vs total)
    df["taker_buy_ratio"] = df["taker_buy_base"] / vol.replace(0, np.nan)

    # Daily volatility
    df["daily_ret"]      = close.pct_change()
    df["volatility_20d"] = df["daily_ret"].rolling(20).std() * 100

    return df


def _safe(row: pd.Series, col: str) -> float | None:
    v = row.get(col)
    if v is None:
        return None
    try:
        f = float(v)
        return None if np.isnan(f) else f
    except (TypeError, ValueError):
        return None


def get_coin_summary(df_1d: pd.DataFrame) -> dict:
    """Extract the most recent candle's key metrics as a clean dict."""
    if df_1d.empty or len(df_1d) < 2:
        return {}

    row  = df_1d.iloc[-1]
    prev = df_1d.iloc[-2]
    price     = float(row["close"])
    prev_close = float(prev["close"])
    change_24h = ((price - prev_close) / prev_close) * 100 if prev_close else 0

    ema200     = _safe(row, "ema_200")
    ema200_pct = ((price - ema200) / ema200 * 100) if ema200 else None
    ema20      = _safe(row, "ema_20")
    ema20_pct  = ((price - ema20)  / ema20  * 100) if ema20  else None

    return {
        "price":              price,
        "change_24h":         round(change_24h, 2),
        "rsi_1d":             round(r, 1) if (r := _safe(row, "rsi"))          else None,
        "macd_bullish":       bool(row.get("macd_bullish")),
        "ema_200":            ema200,
        "ema_200_pct":        round(ema200_pct, 1) if ema200_pct is not None   else None,
        "above_ema200":       ema200_pct > 0        if ema200_pct is not None   else None,
        "ema_20_pct":         round(ema20_pct, 1)  if ema20_pct  is not None   else None,
        "vol_ratio":          round(v, 2)  if (v := _safe(row, "vol_ratio"))   else None,
        "volatility_20d":     round(v, 1)  if (v := _safe(row, "volatility_20d")) else None,
        "bb_position":        round(v, 2)  if (v := _safe(row, "bb_position")) else None,
        "making_higher_lows": is_making_higher_lows(df_1d),
    }


def get_multi_timeframe(dfs: dict[str, pd.DataFrame]) -> dict:
    """Build a {interval: {rsi, macd_bullish, vs_ema20, vs_ema200}} dict."""
    result = {}
    for intv, df in dfs.items():
        if df.empty or len(df) < 2:
            continue
        row   = df.iloc[-1]
        price = float(row["close"])
        ema20  = _safe(row, "ema_20")
        ema200 = _safe(row, "ema_200")
        result[intv] = {
            "rsi":          round(r, 1) if (r := _safe(row, "rsi"))   else None,
            "macd_bullish": bool(row.get("macd_bullish")),
            "vs_ema20":     round(((price - ema20)  / ema20  * 100), 1) if ema20  else None,
            "vs_ema200":    round(((price - ema200) / ema200 * 100), 1) if ema200 else None,
        }
    return result


# ── Higher lows ───────────────────────────────────────────────────────────────

def is_making_higher_lows(df: pd.DataFrame, lookback: int = 30) -> bool:
    if len(df) < lookback:
        return False
    recent = df.tail(lookback).reset_index(drop=True)
    n = len(recent)
    lows: list[float] = []
    for i in range(1, n - 1):
        if (recent["low"].iloc[i] < recent["low"].iloc[i - 1] and
                recent["low"].iloc[i] < recent["low"].iloc[i + 1]):
            lows.append(float(recent["low"].iloc[i]))
    if len(lows) < 2:
        return False
    tail = lows[-3:] if len(lows) >= 3 else lows[-2:]
    return all(tail[j] > tail[j - 1] for j in range(1, len(tail)))


# ── Support / Resistance ──────────────────────────────────────────────────────

def find_support_resistance(
    df: pd.DataFrame,
    window: int = 10,
    min_touches: int = 2,
    tolerance: float = 0.01,
) -> list[dict]:
    """Find price levels touched multiple times (pivots)."""
    if len(df) < window * 2 + 1:
        return []

    raw: list[tuple[str, float]] = []
    for i in range(window, len(df) - window):
        lo = float(df["low"].iloc[i])
        hi = float(df["high"].iloc[i])
        if lo == df["low"].iloc[i - window: i + window + 1].min():
            raw.append(("support", lo))
        if hi == df["high"].iloc[i - window: i + window + 1].max():
            raw.append(("resistance", hi))

    if not raw:
        return []

    # Cluster nearby levels
    clustered: list[dict] = []
    for lvl_type, price in raw:
        merged = False
        for c in clustered:
            if c["type"] == lvl_type and abs(c["price"] - price) / c["price"] <= tolerance:
                c["price"]   = (c["price"] * c["touches"] + price) / (c["touches"] + 1)
                c["touches"] += 1
                merged = True
                break
        if not merged:
            clustered.append({"type": lvl_type, "price": price, "touches": 1})

    strong = [c for c in clustered if c["touches"] >= min_touches]
    return sorted(strong, key=lambda x: x["price"])
