"""
Hotness scoring engine — implements the full algorithm from the spec.
Scores are persisted to hotness_scores table and served via API.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta

from loguru import logger

from data.database import get_session
from data.models import HotnessScore
from spot.analysis import (
    calculate_indicators,
    find_support_resistance,
    get_coin_summary,
    get_multi_timeframe,
)
from spot.data_fetcher import load_dataframe
from spot.macro import get_latest_macro
from spot.narratives import get_coin_narrative_heat, get_narrative_for_coin
from spot.watchlist import get_watchlist


# ── Rating labels ─────────────────────────────────────────────────────────────

def _get_rating(score: int) -> tuple[str, str]:
    if score >= 16: return ("🔥 Very Hot",  "very_hot")
    if score >= 11: return ("🟡 Warm",       "warm")
    if score >= 6:  return ("❄️ Cold",        "cold")
    return ("✖ Avoid", "avoid")


# ── Core scoring function ─────────────────────────────────────────────────────

def _compute_score(
    symbol: str,
    summary: dict,
    macro: dict,
    narrative_heat: str,
    is_leader: bool,
) -> dict:
    score = 0
    breakdown: dict[str, tuple[int, str]] = {}

    # ── MACRO (0–4 points) ───────────────────────────────────────────────────
    dom        = macro.get("btc_dominance") or 50
    dom_change = macro.get("btc_dominance_7d_change") or 0

    if dom_change < 0 and dom < 52:
        score += 2
        breakdown["btc_dominance"] = (2, "Altcoin season conditions")
    elif dom_change < 0:
        score += 1
        breakdown["btc_dominance"] = (1, "BTC dominance weakening")
    else:
        breakdown["btc_dominance"] = (0, "Bitcoin season")

    fg = macro.get("fear_greed_value") or 50
    if fg < 30:
        score += 2
        breakdown["fear_greed"] = (2, "Extreme fear — buy opportunity")
    elif fg < 45:
        score += 1
        breakdown["fear_greed"] = (1, "Fear zone — good entry")
    elif fg > 75:
        score -= 1
        breakdown["fear_greed"] = (-1, "Extreme greed — caution")
    else:
        breakdown["fear_greed"] = (0, "Neutral sentiment")

    # ── NARRATIVE (0–4 points) ───────────────────────────────────────────────
    if narrative_heat == "hot":
        score += 2
        breakdown["narrative"] = (2, "Hot narrative")
    elif narrative_heat == "warming":
        score += 1
        breakdown["narrative"] = (1, "Warming narrative")
    else:
        breakdown["narrative"] = (0, "Cooling or no narrative")

    if is_leader:
        score += 2
        breakdown["narrative_position"] = (2, "Leading coin in narrative")
    elif narrative_heat in ("hot", "warming"):
        score += 1
        breakdown["narrative_position"] = (1, "Part of active narrative")
    else:
        breakdown["narrative_position"] = (0, "")

    # ── TECHNICAL (0–8 points) ───────────────────────────────────────────────
    rsi = summary.get("rsi_1d")
    if rsi is not None:
        if 35 <= rsi <= 50:
            score += 2
            breakdown["rsi"] = (2, f"RSI {rsi:.0f} — oversold recovery zone")
        elif 50 < rsi <= 65:
            score += 1
            breakdown["rsi"] = (1, f"RSI {rsi:.0f} — healthy momentum")
        elif rsi > 75:
            score -= 1
            breakdown["rsi"] = (-1, f"RSI {rsi:.0f} — overbought, wait")
        elif rsi < 30:
            score += 2
            breakdown["rsi"] = (2, f"RSI {rsi:.0f} — extreme oversold")
        else:
            breakdown["rsi"] = (0, f"RSI {rsi:.0f} — neutral")
    else:
        breakdown["rsi"] = (0, "RSI unavailable")

    if summary.get("above_ema200"):
        pct = summary.get("ema_200_pct", 0) or 0
        score += 2
        breakdown["ema_200"] = (2, f"Above 200 EMA by {pct:.1f}%")
    elif summary.get("above_ema200") is False:
        pct = abs(summary.get("ema_200_pct", 0) or 0)
        breakdown["ema_200"] = (0, f"Below 200 EMA by {pct:.1f}%")
    else:
        breakdown["ema_200"] = (0, "EMA 200 unavailable")

    vol = summary.get("vol_ratio")
    price_up = summary.get("change_24h", 0) > 0
    if vol is not None:
        if vol > 1.5 and price_up:
            score += 2
            breakdown["volume"] = (2, f"Volume {vol:.1f}x avg — confirmed move")
        elif vol > 1.2:
            score += 1
            breakdown["volume"] = (1, f"Volume {vol:.1f}x avg — elevated")
        elif vol < 0.7:
            score -= 1
            breakdown["volume"] = (-1, "Low volume — weak conviction")
        else:
            breakdown["volume"] = (0, f"Volume {vol:.1f}x avg — normal")
    else:
        breakdown["volume"] = (0, "Volume data unavailable")

    if summary.get("making_higher_lows"):
        score += 2
        breakdown["structure"] = (2, "Making higher lows — bullish structure")
    else:
        breakdown["structure"] = (0, "No clear higher lows")

    # ── RELATIVE STRENGTH vs BTC (0–4 points) ────────────────────────────────
    # Replaces the permanently-zero 'catalyst' placeholder, which compressed the real
    # ceiling to 16/20 and made the 13-point BITCOIN_SEASON floor near-unreachable.
    # Relative strength is also the key missing discriminator: every other technical
    # component is absolute, so the score cannot currently tell a coin that is leading
    # BTC from one that is merely falling more slowly.
    rs = None
    try:
        _btc = load_dataframe("BTC", "1d", limit=8)
        if not _btc.empty and len(_btc) >= 8:
            _bc    = _btc["close"]
            btc_7d = (float(_bc.iloc[-1]) - float(_bc.iloc[-8])) / float(_bc.iloc[-8]) * 100
            coin_7d = summary.get("change_7d")
            if coin_7d is None:
                _cd = load_dataframe(symbol, "1d", limit=8)
                if not _cd.empty and len(_cd) >= 8:
                    _cc     = _cd["close"]
                    coin_7d = (float(_cc.iloc[-1]) - float(_cc.iloc[-8])) / float(_cc.iloc[-8]) * 100
            if coin_7d is not None:
                rs = coin_7d - btc_7d
    except Exception:
        rs = None

    if rs is None:
        breakdown["rel_strength"] = (0, "Relative strength vs BTC unavailable")
    elif rs > 5:
        score += 4
        breakdown["rel_strength"] = (4, f"Strongly outperforming BTC ({rs:+.1f}% 7d)")
    elif rs > 1:
        score += 3
        breakdown["rel_strength"] = (3, f"Outperforming BTC ({rs:+.1f}% 7d)")
    elif rs > -3:
        score += 1
        breakdown["rel_strength"] = (1, f"Tracking BTC ({rs:+.1f}% 7d)")
    else:
        breakdown["rel_strength"] = (0, f"Lagging BTC ({rs:+.1f}% 7d)")

    final = max(0, min(score, 20))
    label, key = _get_rating(final)
    return {
        "score":     final,
        "max_score": 20,
        "rating":    label,
        "rating_key": key,
        "breakdown": breakdown,
    }


# ── DB persistence ────────────────────────────────────────────────────────────

def _save_score(symbol: str, score_data: dict, macro: dict) -> None:
    with get_session() as s:
        s.add(HotnessScore(
            symbol=symbol,
            score=score_data["score"],
            rating=score_data["rating"],
            breakdown_json=json.dumps(score_data["breakdown"]),
            btc_dominance=macro.get("btc_dominance"),
            fear_greed=macro.get("fear_greed_value"),
        ))


def get_latest_scores() -> list[dict]:
    """Return the most recent score for each watchlist coin, sorted by score desc."""
    with get_session() as s:
        # Subquery: latest timestamp per symbol
        from sqlalchemy import func
        latest = (
            s.query(
                HotnessScore.symbol,
                func.max(HotnessScore.timestamp).label("max_ts"),
            )
            .group_by(HotnessScore.symbol)
            .subquery()
        )
        rows = (
            s.query(HotnessScore)
             .join(latest, (HotnessScore.symbol == latest.c.symbol) &
                           (HotnessScore.timestamp == latest.c.max_ts))
             .order_by(HotnessScore.score.desc())
             .all()
        )
        result = []
        for i, r in enumerate(rows, 1):
            bd = {}
            try:
                bd = json.loads(r.breakdown_json or "{}")
            except Exception:
                pass
            result.append({
                "rank":       i,
                "symbol":     r.symbol,
                "score":      r.score,
                "max_score":  20,
                "rating":     r.rating,
                "rating_key": _get_rating(r.score)[1],
                "breakdown":  bd,
                "timestamp":  r.timestamp.isoformat(),
            })
        return result


def scores_are_stale(max_age_hours: int = 4) -> bool:
    with get_session() as s:
        latest = (
            s.query(HotnessScore.timestamp)
             .order_by(HotnessScore.timestamp.desc())
             .first()
        )
        if not latest:
            return True
        return datetime.utcnow() - latest.timestamp > timedelta(hours=max_age_hours)


# ── Main scoring routine ──────────────────────────────────────────────────────

def score_all_coins() -> list[dict]:
    """
    Score every active watchlist coin. Saves results to DB.
    Returns ranked list enriched with price/indicator data.
    """
    macro = get_latest_macro() or {}
    coins = get_watchlist()
    results = []

    for coin in coins:
        sym = coin["symbol"]
        try:
            # Use full 3-year history for reliable EMA200 on daily
            df_1d = load_dataframe(sym, "1d", limit=1000)
            if df_1d.empty or len(df_1d) < 20:
                logger.debug(f"Scorer: {sym} skipped — only {len(df_1d)} 1d candles")
                continue

            df_1d = calculate_indicators(df_1d)
            summary = get_coin_summary(df_1d)

            narrative      = get_narrative_for_coin(sym)
            narrative_heat = get_coin_narrative_heat(sym)
            is_leader      = coin.get("is_narrative_leader", False)

            score_data = _compute_score(sym, summary, macro, narrative_heat, is_leader)
            _save_score(sym, score_data, macro)

            # Load all timeframes including weekly for the full picture
            dfs: dict = {}
            df_1w = load_dataframe(sym, "1w", limit=210)
            if not df_1w.empty and len(df_1w) >= 20:
                dfs["1w"] = calculate_indicators(df_1w)
            for intv in ("4h", "1h"):
                df = load_dataframe(sym, intv, limit=200)
                if not df.empty and len(df) >= 20:
                    dfs[intv] = calculate_indicators(df)
            tf = get_multi_timeframe({"1d": df_1d, **dfs})

            # S/R levels relative to current price
            levels     = find_support_resistance(df_1d)
            price      = summary.get("price", 0)
            supports   = sorted([l for l in levels if l["type"] == "support"   and l["price"] < price],
                                 key=lambda x: x["price"], reverse=True)[:2]
            resistances = sorted([l for l in levels if l["type"] == "resistance" and l["price"] > price],
                                  key=lambda x: x["price"])[:2]

            entry = {
                **score_data,
                **summary,
                "symbol":           sym,
                "name":             coin["name"],
                "narrative":        narrative,
                "narrative_heat":   narrative_heat,
                "trade_type":       coin["trade_type"],
                "timeframes":       tf,
                "supports":         supports,
                "resistances":      resistances,
            }
            results.append(entry)

        except Exception as e:
            logger.error(f"Scorer error for {sym}: {e}")

    results.sort(key=lambda x: x["score"], reverse=True)
    for i, r in enumerate(results, 1):
        r["rank"] = i

    logger.info(f"Hotness scores updated — {len(results)} coins scored")
    return results


# In-memory cache so the API can serve instantly without re-scoring each request
_cache: list[dict] = []
_cache_time: datetime | None = None


def get_scores(force: bool = False) -> list[dict]:
    """Return scores from cache or recalculate if stale/forced."""
    global _cache, _cache_time
    stale = _cache_time is None or (datetime.utcnow() - _cache_time) > timedelta(hours=4)
    if force or stale or not _cache:
        _cache      = score_all_coins()
        _cache_time = datetime.utcnow()
    return _cache


def get_coin_detail(symbol: str) -> dict | None:
    scores = get_scores()
    for coin in scores:
        if coin["symbol"].upper() == symbol.upper():
            return coin
    return None
