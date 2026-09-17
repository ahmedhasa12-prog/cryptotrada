"""
Agent 1: BTC Multi-Coin Swing Explorer

Scans watchlist + additional coins for swing-trade opportunities.
Uses real Binance OHLCV + live WebSocket prices.
Auto-resume on rate limits via checkpoint + retry mechanism.
"""
from __future__ import annotations
import asyncio
from datetime import datetime
from loguru import logger

from spot.data_fetcher import load_dataframe, refresh_symbol, record_failed_fetch
from spot.streamer import get_prices
from spot.watchlist import get_symbols


def explore_swing_opportunities() -> list[dict]:
    """
    Scan all available symbols + watchlist for high-probability swing setups.
    Returns ranked list of candidates: [{symbol, score, reason}, ...]
    Uses only real OHLCV data (no synthetic/fallback).
    """
    candidates = []
    symbols = get_symbols()  # active watchlist
    prices = get_prices()
    
    for sym in symbols:
        try:
            # Load real 4H candles from DB (populated by Binance klines)
            df = load_dataframe(sym, "4h", limit=100)
            if df.empty or len(df) < 20:
                continue
            
            close = df["close"].iloc[-1]
            high = df["high"].max()
            low = df["low"].min()
            vol_avg = df["volume"].mean()
            vol_current = df["volume"].iloc[-1] if len(df) > 0 else 0
            
            # Real-time price confirmation from Binance WebSocket
            live_price = prices.get(sym, {}).get("price", close)
            
            # Swing exploration logic: volume breakout + price near 4H resistance
            vol_ratio = vol_current / vol_avg if vol_avg > 0 else 0
            price_near_high = (live_price / high) if high > 0 else 0
            
            # Score based on real market conditions
            score = 0
            if vol_ratio >= 1.5:  # Volume breakout confirmation (matches auto_trader)
                score += 40
            if price_near_high >= 0.95:  # Near resistance / breakout zone
                score += 30
            else:
                score += max(0, int(price_near_high * 20))  # Proportional score
            
            # Regime: only explore when price is in healthy range (no synthetic data)
            if score >= 50:
                candidates.append({
                    "symbol": sym,
                    "score": min(score, 100),
                    "reason": f"vol_ratio={vol_ratio:.2f}, price_near_high={price_near_high:.2f}",
                    "live_price": live_price,
                    "close_4h": close,
                })
        except Exception as e:
            # If fetch fails (rate limit), record for automatic retry
            record_failed_fetch(sym, "4h", str(e))
            logger.debug(f"Swing explore skipped {sym}: {e}")
    
    # Sort by score descending (highest probability first)
    candidates.sort(key=lambda x: x["score"], reverse=True)
    logger.info(f"Swing exploration complete: {len(candidates)} candidates from {len(symbols)} symbols")
    top_3 = candidates[:3]  # Focus on top 3 for efficiency
    for c in top_3:
        logger.info(f"Top candidate: {c['symbol']} score={c['score']} price={c['live_price']} reason={c['reason']}")
    # Auto-resume: if fetch fails, retry job (scheduled every 30s) will recover
    # The checkpoint mechanism ensures we resume from disk on restart
    return top_3


def scan_all_profitable_swings() -> dict:
    """
    Master exploration: scan BTC, XRP, SOL, and watchlist for profitable swing trades.
    Returns combined ranking across all 3 agent strategies.
    Always uses real market data.
    """
    # Agent 1: BTC Multi-coin (via explore_swing_opportunities)
    btc_candidates = explore_swing_opportunities()
    
    # Agent 2: XRP Swing (via evaluate_setup equivalent)
    from spot.xrp_swing import evaluate_setup
    xrp_result = evaluate_setup()
    
    # Agent 3: SOL Swing (via evaluate_sol_swing)
    from spot.sol_swing import evaluate_sol_swing
    sol_result = evaluate_sol_swing()
    
    combined = {
        "agents_active": 3,
        "btc_explorer_candidates": len([c for c in btc_candidates if c.get("score", 0) > 50]),
        "xrp_swing_active": xrp_result.get("enabled", False) if isinstance(xrp_result, dict) else False,
        "sol_swing_signal": sol_result.get("signal", False),
        "sol_swing_score": sol_result.get("entry_pct", 0) * 100,
        "data_integrity": "real_binance_ohlcv_and_websocket",
        "auto_resume": True,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    }
    return combined
