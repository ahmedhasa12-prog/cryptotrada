"""
Solana Trading Agent — Mean Reversion Strategy with R:R Filtering
====================================================================

Strategy: 4H Mean Reversion with Volume Confirmation
- Entry: Price deviates ≥ 2σ from EMA20 on 4H + RSI oversold + volume surge
- Exit: Take profit at 2:1 R:R or stop loss at 1% below entry
- Timeframe: 4H candles
- Assets: SOL/USD, major SOL-based tokens

Risk Controls:
- Maximum 1% equity risk per trade
- R:R minimum 2.0 (reject entries with poor reward-to-risk)
- Maximum 3 concurrent positions
- 60-minute cooldown per symbol after close
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger

# Database integration
from config import get_config
from data.database import init_db, get_session
from data.models import SpotTrade

# ── Configuration ──────────────────────────────────────────────────────
SOLANA_RPC = "https://api.mainnet-beta.solana.com"
SOL_USD_PAIR = "SOL/USD"
MAX_POSITIONS = 3
RISK_PCT_PER_TRADE = 0.01  # 1% of equity per trade
MIN_RR_RATIO = 2.0  # Minimum reward-to-risk ratio
EQUITY_USD = 5000.0  # Paper portfolio size
MAX_PER_NARRATIVE = 2

# Technical analysis parameters
EMA_PERIOD = 20
RSI_PERIOD = 14
RSI_OVER_SOLD = 30
RSI_OVER_BOUGHT = 70
BB_PERIOD = 20
BB_STDEV = 2.0

# Timeframes
TIMEFRAME_4H = "4H"
TIMEFRAME_1H = "1H"


# Initialize database on module load
_cfg = get_config()
init_db(_cfg.db_path)


# ── Helpers ────────────────────────────────────────────────────────────

def _round_to_precision(value: float, prec: int = 4) -> float:
    """Round value to specified decimal places."""
    return round(value, prec)


def _fetch_sol_price() -> Optional[float]:
    """Fetch current SOL/USD price from public APIs."""
    prices = []

    # Try CoinGecko
    try:
        resp = httpx.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": "solana", "vs_currencies": "usd"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            price = data.get("solana", {}).get("usd")
            if price:
                prices.append(float(price))
    except Exception as e:
        logger.debug(f"CoinGecko price fetch error: {e}")

    # Try Binance
    try:
        resp = httpx.get(
            "https://api.binance.com/api/v3/ticker/price",
            params={"symbol": "SOLUSDT"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            price = float(data.get("price", 0))
            if price > 0:
                prices.append(price)
    except Exception as e:
        logger.debug(f"Binance price fetch error: {e}")

    # Average prices from multiple sources
    if prices:
        return sum(prices) / len(prices)

    return None


def _calculate_ema(
    closes: List[float], period: int = EMA_PERIOD
) -> Optional[float]:
    """Calculate Exponential Moving Average."""
    if len(closes) < period:
        return None

    k = 2 / (period + 1)
    ema = sum(closes[:period]) / period
    for c in closes[period:]:
        ema = c * k + ema * (1 - k)
    return round(ema, 4)


def _calculate_rsi(
    closes: List[float], period: int = RSI_PERIOD
) -> Optional[int]:
    """Calculate Relative Strength Index."""
    if len(closes) < period + 1:
        return None

    gains, losses = [], []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    # Average gains/losses over period
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period

    # Smoothed RSI
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period

    if al == 0:
        return 100

    rsi = round(100 - (100 / (1 + ag / al)))
    return max(0, min(100, rsi))


def _calculate_bollinger_bands(
    closes: List[float], period: int = BB_PERIOD, stdev: float = BB_STDEV
) -> Optional[Tuple[float, float, float]]:
    """
    Calculate Bollinger Bands.
    Returns (middle_band, upper_band, lower_band)
    """
    if len(closes) < period:
        return None

    sma = sum(closes[-period:]) / period
    variance = sum((c - sma) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5

    middle = round(sma, 4)
    upper = round(sma + (stdev * std), 4)
    lower = round(sma - (stdev * std), 4)

    return middle, upper, lower


def _fetch_ohlcv(
    symbol: str = SOL_USD_PAIR,
    timeframe: str = TIMEFRAME_4H,
    limit: int = 200,
) -> Optional[List[Dict[str, float]]]:
    """
    Fetch OHLCV candles from Binance via CCXT.
    Falls back to synthetic data if API unavailable.
    """
    try:
        import ccxt
        import asyncio

        # Map timeframe to CCXT format
        ccxt_timeframe = {
            "1m": "1m",
            "5m": "5m",
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d",
            "1w": "1w",
        }.get(timeframe.lower(), "4h")

        # Use Binance for SOLUSDT
        exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
        })

        # Fetch OHLCV data synchronously
        # ccxt is sync by default
        ohlcv_data = exchange.fetch_ohlcv(
            symbol="SOL/USDT",
            timeframe=ccxt_timeframe,
            limit=limit,
        )

        if not ohlcv_data or len(ohlcv_data) < 50:
            logger.warning(f"[SOL-AGENT] Insufficient CCXT data ({len(ohlcv_data) if ohlcv_data else 0} candles)")
            return _generate_synthetic_ohlcv(limit, base_price=100.0, volatility=0.02)

        # Convert to our format: list of dicts with timestamp, open, high, low, close, volume
        result = []
        for candle in ohlcv_data:
            ts, o, h, l, c, v = candle
            result.append({
                "timestamp": datetime.fromtimestamp(ts / 1000).isoformat(),
                "open": round(float(o), 4),
                "high": round(float(h), 4),
                "low": round(float(l), 4),
                "close": round(float(c), 4),
                "volume": round(float(v), 2),
            })

        logger.info(f"[SOL-AGENT] Fetched {len(result)} real 4H candles from Binance via CCXT")
        return result

    except Exception as e:
        logger.warning(f"[SOL-AGENT] CCXT fetch failed ({e}), using synthetic data")
        return _generate_synthetic_ohlcv(limit, base_price=100.0, volatility=0.02)

    sma = sum(closes[-period:]) / period
    variance = sum((c - sma) ** 2 for c in closes[-period:]) / period
    std = variance ** 0.5

    middle = round(sma, 4)
    upper = round(sma + (stdev * std), 4)
    lower = round(sma - (stdev * std), 4)

    return middle, upper, lower


# ── Strategy Logic ─────────────────────────────────────────────────────

def _check_mean_reversal_setup(
    closes_4h: List[float],
    volumes_4h: List[float],
    current_price: float,
) -> Dict[str, Any]:
    """
    Check for mean reversion setup on 4H timeframe.

    Setup conditions:
    1. Price below lower Bollinger Band (oversold)
    2. RSI(14) < 30 (oversold momentum)
    3. Volume surge (current 4H vol > 1.5x 20-period avg vol)
    4. Price showing signs of reversal (current candle green after red)
    """
    results = {
        "entry_signal": False,
        "signal_type": None,
        "reason": "",
        "bb_lower": 0.0,
        "bb_middle": 0.0,
        "rsi": 50,
        "volume_ratio": 1.0,
        "stop_price": 0.0,
        "tp_price": 0.0,
    }

    # Calculate technical indicators
    bb = _calculate_bollinger_bands(closes_4h)
    if bb is None:
        return results

    bb_middle, bb_upper, bb_lower = bb
    results["bb_lower"] = bb_lower
    results["bb_middle"] = bb_middle

    # RSI
    rsi = _calculate_rsi(closes_4h)
    if rsi is None:
        return results
    results["rsi"] = rsi

    # Volume analysis
    if len(volumes_4h) >= 20:
        recent_vol = volumes_4h[-1]
        avg_vol = sum(volumes_4h[-21:-1]) / 20  # avg of previous 20
        volume_ratio = round(recent_vol / avg_vol, 2) if avg_vol > 0 else 1.0
    else:
        volume_ratio = 1.0
    results["volume_ratio"] = volume_ratio

    # Get the last close and current price context
    last_close = closes_4h[-1]
    prev_close = closes_4h[-2] if len(closes_4h) >= 2 else last_close

    # ── Mean Reversal Conditions ─────────────────────────────────────

    # Condition 1: Price below lower BB (oversold)
    below_bb = current_price < bb_lower

    # Condition 2: RSI oversold
    rsi_oversold = rsi < RSI_OVER_SOLD

    # Condition 3: Volume surge
    vol_surge = volume_ratio >= 1.5

    # Condition 4: Reversal candle pattern
    # Green candle after red, or current candle closing above previous open
    is_reversal = False
    if len(closes_4h) >= 3:
        # Check if last 2 candles show reversal
        c1_close = closes_4h[-1]
        c1_open = None  # Would need open prices
        c2_close = closes_4h[-2]
        # Simplified: price moving back toward middle BB
        moving_toward_mid = current_price > bb_lower + (bb_middle - bb_lower) * 0.5

        if moving_toward_mid:
            is_reversal = True

    # ── Entry Signal ─────────────────────────────────────────────────

    if below_bb and rsi_oversold and vol_surge and is_reversal:
        results["entry_signal"] = True
        results["signal_type"] = "mean_reversion_long"

        # Set stop loss at 1% below entry (conservative)
        results["stop_price"] = round(current_price * 0.99, 4)

        # Take profit at 2:1 R:R
        risk = current_price - results["stop_price"]
        if risk > 0:
            results["tp_price"] = round(current_price + risk * 2.0, 4)

        results["reason"] = (
            f"Mean reversion: price ${current_price:.2f} below BB lower ${bb_lower:.2f}, "
            f"RSI {rsi}, volume {volume_ratio:.1f}x surge, reversal pattern detected"
        )

    return results


def _check_breakout_setup(
    closes_4h: List[float],
    volumes_4h: List[float],
    current_price: float,
) -> Dict[str, Any]:
    """
    Check for breakout setup on 4H timeframe.

    Setup conditions:
    1. Price breaks above resistance (BB upper or previous high)
    2. Volume confirmation (surge on breakout candle)
    3. RSI in healthy range (not overbought)
    4. Higher high formation
    """
    results = {
        "entry_signal": False,
        "signal_type": None,
        "reason": "",
        "resistance": 0.0,
        "support": 0.0,
        "rsi": 50,
        "volume_ratio": 1.0,
        "stop_price": 0.0,
        "tp_price": 0.0,
    }

    # Calculate resistance/support from recent highs/lows
    if len(closes_4h) >= 20:
        recent_high = max(closes_4h[-20:])
        recent_low = min(closes_4h[-20:])
    else:
        recent_high = current_price
        recent_low = current_price

    results["resistance"] = round(recent_high, 4)
    results["support"] = round(recent_low, 4)

    # RSI
    rsi = _calculate_rsi(closes_4h)
    if rsi is None:
        return results
    results["rsi"] = rsi

    # Volume
    if len(volumes_4h) >= 20:
        recent_vol = volumes_4h[-1]
        avg_vol = sum(volumes_4h[-21:-1]) / 20
        volume_ratio = round(recent_vol / avg_vol, 2) if avg_vol > 0 else 1.0
    else:
        volume_ratio = 1.0
    results["volume_ratio"] = volume_ratio

    # Last close
    last_close = closes_4h[-1] if closes_4h else current_price
    prev_close = closes_4h[-2] if len(closes_4h) >= 2 else last_close

    # ── Breakout Conditions ────────────────────────────────────────────

    # Price above resistance
    above_resistance = current_price > results["resistance"]

    # RSI not overbought (good for breakout sustainability)
    rsi_healthy = rsi < RSI_OVER_BOUGHT  # Allow some flexibility

    # Volume confirmation
    vol_confirmed = results["volume_ratio"] >= 1.5

    # Higher high formation (last close > previous close)
    higher_high = last_close > prev_close

    # ── Entry Signal ───────────────────────────────────────────────────

    if above_resistance and rsi_healthy and vol_confirmed and higher_high:
        results["entry_signal"] = True
        results["signal_type"] = "breakout_long"

        # Stop loss just below resistance/previous swing low
        results["stop_price"] = round(results["support"] * 0.995, 4)

        # Take profit at 2:1 R:R from entry
        risk = current_price - results["stop_price"]
        if risk > 0:
            results["tp_price"] = round(current_price + risk * 2.0, 4)

        results["reason"] = (
            f"Breakout: price ${current_price:.2f} above resistance ${results['resistance']:.2f}, "
            f"RSI {rsi}, volume {volume_ratio:.1f}x confirmed, higher high formation"
        )

    return results


# ── Position Sizing ────────────────────────────────────────────────────

def _calculate_position_size(
    entry_price: float,
    stop_price: float,
    equity_usd: float = EQUITY_USD,
    risk_pct: float = RISK_PCT_PER_TRADE,
) -> float:
    """
    Calculate position size based on 1% risk per trade.
    Risk amount = equity * risk_pct
    Position size = risk_amount / (entry_price - stop_price)
    """
    risk_amount = equity_usd * risk_pct
    price_diff = abs(entry_price - stop_price)

    if price_diff <= 0 or price_diff is None:
        return 0.0

    # Size in USD (not SOL amount)
    position_usd = risk_amount / (price_diff / entry_price * 100) if price_diff else 0

    # Cap at reasonable maximum
    max_position_usd = equity_usd * 0.20  # Max 20% of equity per position
    position_usd = min(position_usd, max_position_usd)

    return round(position_usd, 2)


# ── Helpers for Database Integration ──────────────────────────────────

def _get_open_paper_trades() -> List[Dict]:
    """Fetch all open paper trades from database."""
    try:
        with get_session() as s:
            trades = s.query(SpotTrade).filter(
                SpotTrade.symbol == "SOL/USD",
                SpotTrade.mode == "paper",
                SpotTrade.exit_price == None,
                SpotTrade.notes.like("[BOT]%"),
            ).all()
            
            result = []
            for t in trades:
                result.append({
                    "trade_id": t.id,
                    "symbol": t.symbol,
                    "mode": t.mode,
                    "direction": t.direction,
                    "entry_price": t.entry_price,
                    "size_usd": t.size_usd,
                    "stop_loss": t.stop_loss,
                    "take_profit": t.target,
                    "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                    "notes": t.notes,
                    "trailing_active": False,  # simplified
                })
            return result
    except Exception as e:
        logger.warning(f"[SOL-AGENT] Could not fetch open trades: {e}")
        return []


# ── Main Trading Cycle ────────────────────────────────────────────────

async def run_solana_cycle(
    positions: Optional[List[Dict]] = None,
    watchlist: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Main trading cycle for Solana agent.
    Runs every 5 minutes (300 seconds).

    Returns:
        dict with actions taken, new entries, closures, etc.
    """
    if positions is None:
        # Fetch open paper trades from database
        positions = _get_open_paper_trades()

    if watchlist is None:
        watchlist = ["SOL/USD"]

    logger.info("[SOL-AGENT] Starting trading cycle...")

    actions = {"entries": [], "exits": [], "closures": []}

    # Get current SOL price
    current_price = _fetch_sol_price()
    if current_price is None:
        logger.error("[SOL-AGENT] Could not fetch SOL price - skipping cycle")
        actions["error"] = "Could not fetch SOL price"
        return actions

    logger.info(f"[SOL-AGENT] Current SOL price: ${current_price:.2f}")

    # Fetch 4H candles for analysis
    ohlcv_4h = _fetch_ohlcv(timeframe=TIMEFRAME_4H, limit=200)
    if ohlcv_4h is None or len(ohlcv_4h) < 50:
        logger.warning("[SOL-AGENT] Insufficient 4H candle data - using fallback")
        ohlcv_4h = _generate_synthetic_ohlcv(200, current_price)

    closes_4h = [c["close"] for c in ohlcv_4h]
    volumes_4h = [c["volume"] for c in ohlcv_4h]

    # ── Check for new entries ─────────────────────────────────────────

    # Count current bot positions
    bot_positions = [p for p in positions if p.get("mode") == "paper" and str(p.get("notes") or "").startswith("[BOT]")]
    current_pos_count = len(bot_positions)

    if current_pos_count >= MAX_POSITIONS:
        logger.info(f"[SOL-AGENT] Max positions ({MAX_POSITIONS}) reached - no new entries")
    else:
        # Check mean reversion setup
        mr_setup = _check_mean_reversal_setup(closes_4h, volumes_4h, current_price)

        if mr_setup["entry_signal"] and current_pos_count < MAX_POSITIONS:
            # Calculate position size
            size_usd = _calculate_position_size(
                entry_price=current_price,
                stop_price=mr_setup["stop_price"],
                equity_usd=EQUITY_USD,
                risk_pct=RISK_PCT_PER_TRADE,
            )

            if size_usd > 0:
                # Check R:R ratio
                risk = current_price - mr_setup["stop_price"]
                reward = mr_setup["tp_price"] - current_price
                rr_ratio = round(reward / risk, 2) if risk > 0 else 0

                if rr_ratio >= MIN_RR_RATIO:
                    # Execute entry - persist to database
                    from data.database import get_session
                    from data.models import SpotTrade
                    
                    with get_session() as s:
                        trade = SpotTrade(
                            symbol="SOL/USD",
                            mode="paper",
                            direction="long",
                            entry_price=current_price,
                            size_usd=size_usd,
                            stop_loss=mr_setup["stop_price"],
                            target=mr_setup["tp_price"],
                            entry_time=datetime.now(timezone.utc),
                            notes=f"[BOT] Solana {mr_setup['signal_type']} R:R {rr_ratio}:1 - {mr_setup['reason'][:100]}",
                        )
                        s.add(trade)
                        s.flush()
                        trade_id = trade.id

                    action = {
                        "symbol": "SOL/USD",
                        "action": "entry",
                        "trade_id": trade_id,
                        "signal_type": mr_setup["signal_type"],
                        "entry_price": current_price,
                        "size_usd": size_usd,
                        "stop_loss": mr_setup["stop_price"],
                        "take_profit": mr_setup["tp_price"],
                        "risk": round(risk, 2),
                        "reward": round(reward, 2),
                        "rr_ratio": rr_ratio,
                        "reason": mr_setup["reason"],
                        "entry_time": datetime.now(timezone.utc).isoformat(),
                        "cooldown_until": (datetime.now(timezone.utc) + timedelta(minutes=60)).isoformat(),
                    }

                    actions["entries"].append(action)
                    logger.info(
                        f"[SOL-AGENT] ENTRY: {action['signal_type']} SOL/USD @ ${current_price:.2f} "
                        f"size=${size_usd:.2f} R:R {rr_ratio}:1 @ ${mr_setup['tp_price']:.2f} (ID: {trade_id})"
                    )
                else:
                    logger.info(
                        f"[SOL-AGENT] Rejected mean reversion entry: R:R {rr_ratio:.1f} < {MIN_RR_RATIO}"
                    )

        # Check breakout setup if no mean reversion signal
        if not mr_setup["entry_signal"]:
            bo_setup = _check_breakout_setup(closes_4h, volumes_4h, current_price)

            if bo_setup["entry_signal"] and current_pos_count < MAX_POSITIONS:
                size_usd = _calculate_position_size(
                    entry_price=current_price,
                    stop_price=bo_setup["stop_price"],
                    equity_usd=EQUITY_USD,
                    risk_pct=RISK_PCT_PER_TRADE,
                )

                if size_usd > 0:
                    risk = current_price - bo_setup["stop_price"]
                    reward = bo_setup["tp_price"] - current_price
                    rr_ratio = round(reward / risk, 2) if risk > 0 else 0

                    if rr_ratio >= MIN_RR_RATIO:
                        # Execute entry - persist to database
                        from data.database import get_session
                        from data.models import SpotTrade
                        
                        with get_session() as s:
                            trade = SpotTrade(
                                symbol="SOL/USD",
                                mode="paper",
                                direction="long",
                                entry_price=current_price,
                                size_usd=size_usd,
                                stop_loss=bo_setup["stop_price"],
                                target=bo_setup["tp_price"],
                                entry_time=datetime.now(timezone.utc),
                                notes=f"[BOT] Solana {bo_setup['signal_type']} R:R {rr_ratio}:1 - {bo_setup['reason'][:100]}",
                            )
                            s.add(trade)
                            s.flush()
                            trade_id = trade.id

                        action = {
                            "symbol": "SOL/USD",
                            "action": "entry",
                            "trade_id": trade_id,
                            "signal_type": bo_setup["signal_type"],
                            "entry_price": current_price,
                            "size_usd": size_usd,
                            "stop_loss": bo_setup["stop_price"],
                            "take_profit": bo_setup["tp_price"],
                            "risk": round(risk, 2),
                            "reward": round(reward, 2),
                            "rr_ratio": rr_ratio,
                            "reason": bo_setup["reason"],
                            "entry_time": datetime.now(timezone.utc).isoformat(),
                            "cooldown_until": (datetime.now(timezone.utc) + timedelta(minutes=60)).isoformat(),
                        }

                        actions["entries"].append(action)
                        logger.info(
                            f"[SOL-AGENT] ENTRY: {action['signal_type']} SOL/USD @ ${current_price:.2f} "
                            f"size=${size_usd:.2f} R:R {rr_ratio}:1 @ ${bo_setup['tp_price']:.2f} (ID: {trade_id})"
                        )
                    else:
                        logger.info(
                            f"[SOL-AGENT] Rejected breakout entry: R:R {rr_ratio:.1f} < {MIN_RR_RATIO}"
                        )

    # ── Check for exits/closures ──────────────────────────────────────

    for pos in positions:
        if pos.get("mode") != "paper":
            continue

        sym = pos.get("symbol")
        if sym != "SOL/USD":
            continue

        entry_price = pos.get("entry_price", 0)
        current_pos_price = current_price
        stop_loss = pos.get("stop_loss", 0)
        take_profit = pos.get("take_profit", 0)
        size_usd = pos.get("size_usd", 0)

        # Calculate P&L
        pnl_pct = (current_pos_price - entry_price) / entry_price * 100
        pnl_usd = (current_pos_price - entry_price) / entry_price * size_usd

        # Check take profit hit
        if current_pos_price >= take_profit:
            trade_id = pos.get("trade_id")
            if trade_id:
                # Close trade in database
                from data.database import get_session
                from data.models import SpotTrade
                with get_session() as s:
                    trade = s.query(SpotTrade).filter(SpotTrade.id == trade_id).first()
                    if trade and trade.exit_price is None:
                        trade.exit_price = take_profit
                        trade.exit_time = datetime.now(timezone.utc)
                        trade.pnl_pct = round(pnl_pct, 2)
                        trade.pnl_usd = round(pnl_usd, 2)
                        trade.outcome = "win" if pnl_usd > 0 else "loss" if pnl_usd < 0 else "breakeven"
                        trade.notes = (trade.notes or "") + f" | Bot closed: take profit hit @ ${take_profit:.2f} P&L {pnl_pct:+.2f}%"

            actions["exits"].append({
                "symbol": "SOL/USD",
                "action": "take_profit",
                "trade_id": trade_id,
                "entry_price": entry_price,
                "exit_price": take_profit,
                "pnl_pct": round(pnl_pct, 2),
                "pnl_usd": round(pnl_usd, 2),
                "reason": "Take profit hit",
                "exit_time": datetime.now(timezone.utc).isoformat(),
                "size_usd": size_usd,
            })
            logger.info(
                f"[SOL-AGENT] TP HIT SOL/USD @ ${take_profit:.2f} "
                f"P&L {pnl_pct:+.2f}% (${pnl_usd:+.2f})"
            )
            continue

        # Check stop loss hit
        if current_pos_price <= stop_loss:
            trade_id = pos.get("trade_id")
            if trade_id:
                # Close trade in database
                from data.database import get_session
                from data.models import SpotTrade
                with get_session() as s:
                    trade = s.query(SpotTrade).filter(SpotTrade.id == trade_id).first()
                    if trade and trade.exit_price is None:
                        trade.exit_price = stop_loss
                        trade.exit_time = datetime.now(timezone.utc)
                        trade.pnl_pct = round(pnl_pct, 2)
                        trade.pnl_usd = round(pnl_usd, 2)
                        trade.outcome = "win" if pnl_usd > 0 else "loss" if pnl_usd < 0 else "breakeven"
                        trade.notes = (trade.notes or "") + f" | Bot closed: stop loss hit @ ${stop_loss:.2f} P&L {pnl_pct:+.2f}%"

            actions["exits"].append({
                "symbol": "SOL/USD",
                "action": "stop_loss",
                "trade_id": trade_id,
                "entry_price": entry_price,
                "exit_price": stop_loss,
                "pnl_pct": round(pnl_pct, 2),
                "pnl_usd": round(pnl_usd, 2),
                "reason": "Stop loss hit",
                "exit_time": datetime.now(timezone.utc).isoformat(),
                "size_usd": size_usd,
            })
            logger.warning(
                f"[SOL-AGENT] SL HIT SOL/USD @ ${stop_loss:.2f} "
                f"P&L {pnl_pct:+.2f}% (${pnl_usd:+.2f})"
            )
            continue

        # Trailing stop logic (simplified)
        if pnl_pct > 0 and not pos.get("trailing_active", False):
            # Trail at 2% below current price
            trailing_stop = round(current_pos_price * 0.98, 4)
            if trailing_stop > stop_loss:
                # Update stop loss
                actions["exits"].append({
                    "symbol": "SOL/USD",
                    "action": "trailing_stop_update",
                    "entry_price": entry_price,
                    "current_price": current_pos_price,
                    "new_stop": trailing_stop,
                    "pnl_pct": round(pnl_pct, 2),
                    "reason": "Trailing stop adjustment",
                    "exit_time": datetime.utcnow().isoformat(),
                    "size_usd": size_usd,
                })
                logger.debug(
                    f"[SOL-AGENT] Trailing stop adjusted to ${trailing_stop:.2f} "
                    f"for {pnl_pct:+.2f}% gain"
                )

    # ── Portfolio health check ────────────────────────────────────────

    total_unrealized = sum(
        (current_price - p.get("entry_price", 0)) / p.get("entry_price", 1) * p.get("size_usd", 0)
        for p in positions if p.get("mode") == "paper"
    )

    actions["portfolio_health"] = {
        "total_unrealized_pnl_pct": round(total_unrealized / EQUITY_USD * 100, 2),
        "positions_count": current_pos_count,
        "max_positions": MAX_POSITIONS,
        "equity_usd": EQUITY_USD,
        "drawdown_pct": abs(total_unrealized) / EQUITY_USD if total_unrealized < 0 else 0.0,
    }

    logger.info(f"[SOL-AGENT] Cycle complete: {len(actions['entries'])} entries, "
                f"{len(actions['exits'])} exits, {current_pos_count} open positions")

    return actions


def _generate_synthetic_ohlcv(
    count: int, base_price: float = 100.0, volatility: float = 0.02
) -> List[Dict[str, float]]:
    """Generate synthetic OHLCV data for demonstration purposes."""
    import random

    price = base_price
    data = []
    for i in range(count):
        # Random walk with mean reversion
        change = random.gauss(0, volatility)
        price = price * (1 + change)

        # Generate realistic OHLC
        high = price * (1 + abs(random.gauss(0, volatility * 0.5)))
        low = price * (1 - abs(random.gauss(0, volatility * 0.5)))
        volume = random.uniform(1000, 10000)

        data.append({
            "timestamp": (datetime.utcnow() - timedelta(hours=i * 4)).isoformat(),
            "open": round(price * (1 + random.uniform(-0.01, 0.01)), 4),
            "high": round(high, 4),
            "low": round(low, 4),
            "close": round(price, 4),
            "volume": round(volume, 2),
        })

    return data


# ── Agent Integration ──────────────────────────────────────────────────

def get_solana_status() -> Dict[str, Any]:
    """Get current Solana agent status - keys match web.StatusResponse expectations."""
    current_price = _fetch_sol_price()
    return {
        "solana_agent": "solana_trend",
        "solana_price": current_price,
        "solana_max_positions": MAX_POSITIONS,
        "solana_risk_pct": RISK_PCT_PER_TRADE * 100,
        "solana_min_rr": MIN_RR_RATIO,
        "equity_usd": EQUITY_USD,
    }


if __name__ == "__main__":
    """Test the agent when run directly."""
    import asyncio

    async def test():
        print("=== Solana Trading Agent Test ===\n")

        # Test price fetch
        price = _fetch_sol_price()
        print(f"SOL/USD price: ${price or 'N/A'}")

        # Test data generation
        ohlcv = _generate_synthetic_ohlcv(200, price or 150.0 if price else 150.0, 0.03)
        closes = [c["close"] for c in ohlcv]
        vols = [c["volume"] for c in ohlcv]

        # Mean reversion
        mr = _check_mean_reversal_setup(closes, vols, price or 150.0)
        print(f"\nMean reversion setup: {'SIGNAL' if mr['entry_signal'] else 'NO SIGNAL'}")
        if mr["entry_signal"]:
            print(f"  R:R: {mr.get('rr_ratio')}")
            print(f"  Stop: ${mr['stop_price']:.2f}")
            print(f"  TP: ${mr['tp_price']:.2f}")
            print(f"  Reason: {mr['reason'][:80]}...")

        # Breakout
        bo = _check_breakout_setup(closes, vols, price or 150.0)
        print(f"\nBreakout setup: {'SIGNAL' if bo['entry_signal'] else 'NO SIGNAL'}")
        if bo["entry_signal"]:
            print(f"  R:R: {bo.get('rr_ratio')}")
            print(f"  Stop: ${bo['stop_price']:.2f}")
            print(f"  TP: ${bo['tp_price']:.2f}")
            print(f"  Reason: {bo['reason'][:80]}...")

        # Run trading cycle
        print("\n--- Running trading cycle ---")
        actions = await run_solana_cycle(positions=[], watchlist=["SOL/USD"])
        print(f"Entries: {len(actions['entries'])}")
        print(f"Exits: {len(actions['exits'])}")
        if "portfolio_health" in actions:
            ph = actions["portfolio_health"]
            print(f"Portfolio: {ph['positions_count']} positions, "
                  f"drawdown {ph['drawdown_pct']:.1f}%, "
                  f"unrealized P&L {ph['total_unrealized_pnl_pct']:.1f}%")

    asyncio.run(test())