"""
Atmosphere Score — ecosystem-level market conditions (0–100).

Ten indicators at 10 points each, all computed from existing DB candles,
MacroSnapshot history, and the live price stream. No external API calls.

Score → bot behaviour:
  0–39   hostile     → gate blocks new entries (if gate toggle is on)
  40–64  neutral     → normal sizing / normal exits
  65–79  favourable  → position ×1.10, trailing loosened slightly
  80–100 exceptional → position ×1.25, trailing loosened more
"""
from __future__ import annotations

from datetime import datetime, timedelta

from loguru import logger

_cache: dict = {}
_CACHE_TTL   = 15 * 60          # recompute at most every 15 minutes


# ── DB / stream helpers ────────────────────────────────────────────────────────

def _macro_history(hours: int = 72) -> list[dict]:
    from data.database import get_session
    from data.models import MacroSnapshot
    since = datetime.utcnow() - timedelta(hours=hours)
    with get_session() as s:
        rows = (
            s.query(MacroSnapshot)
             .filter(MacroSnapshot.timestamp >= since)
             .order_by(MacroSnapshot.timestamp.asc())
             .all()
        )
        return [
            {"ts": r.timestamp, "btc_dom": r.btc_dominance, "fear_greed": r.fear_greed_value}
            for r in rows
        ]


def _watchlist_candles(limit: int = 170) -> dict[str, list[dict]]:
    """Last `limit` hourly candles per active watchlist coin — single session for all symbols."""
    from data.database import get_session
    from data.models import OhlcvCandle
    from spot.watchlist import get_watchlist
    symbols = [c["symbol"] for c in get_watchlist(active_only=True)]
    result: dict[str, list[dict]] = {sym: [] for sym in symbols}
    with get_session() as s:
        for sym in symbols:
            rows = (
                s.query(OhlcvCandle)
                 .filter(OhlcvCandle.symbol == sym, OhlcvCandle.interval == "1h")
                 .order_by(OhlcvCandle.timestamp.desc())
                 .limit(limit)
                 .all()
            )
            result[sym] = [
                {"close": r.close, "volume": r.volume, "taker_buy_base": r.taker_buy_base}
                for r in reversed(rows)
            ]
    return result


def _daily_candles(symbol: str, limit: int = 3) -> list[float]:
    """Last `limit` 1d closing prices for a symbol."""
    from data.database import get_session
    from data.models import OhlcvCandle
    with get_session() as s:
        rows = (
            s.query(OhlcvCandle.close)
             .filter(OhlcvCandle.symbol == symbol, OhlcvCandle.interval == "1d")
             .order_by(OhlcvCandle.timestamp.desc())
             .limit(limit)
             .all()
        )
        return [float(r[0]) for r in reversed(rows)]


# ── The 10 indicator functions — each returns (points: int, detail: str) ─────

def _i_btc_dom_trend(macro: list[dict]) -> tuple[int, str]:
    """BTC.D falling 24h → capital rotating to alts."""
    if len(macro) < 2:
        return 5, "insufficient macro data"
    latest = macro[-1]
    day_ago = next(
        (r for r in reversed(macro) if (latest["ts"] - r["ts"]).total_seconds() >= 20 * 3600),
        macro[0],
    )
    if latest["btc_dom"] is None or day_ago["btc_dom"] is None:
        return 5, "no BTC dominance data"
    change = latest["btc_dom"] - day_ago["btc_dom"]
    if change < -0.5:  return 10, f"BTC.D −{abs(change):.2f}% — strong alt rotation"
    if change < -0.2:  return 7,  f"BTC.D −{abs(change):.2f}% — mild rotation"
    if change <  0.1:  return 5,  f"BTC.D flat ({change:+.2f}%)"
    return 0, f"BTC.D +{change:.2f}% — capital flowing to BTC"


def _i_btc_dom_accel(macro: list[dict]) -> tuple[int, str]:
    """BTC.D declining faster than the prior day — acceleration."""
    if len(macro) < 3:
        return 5, "insufficient macro data"
    latest  = macro[-1]
    day1    = next((r for r in reversed(macro) if (latest["ts"] - r["ts"]).total_seconds() >= 20 * 3600), None)
    day2    = next((r for r in reversed(macro) if (latest["ts"] - r["ts"]).total_seconds() >= 44 * 3600), None)
    if not day1 or not day2:
        return 5, "insufficient history"
    if any(x["btc_dom"] is None for x in [latest, day1, day2]):
        return 5, "no dominance data"
    recent = latest["btc_dom"] - day1["btc_dom"]
    prior  = day1["btc_dom"]   - day2["btc_dom"]
    if recent < prior - 0.1 and recent < 0:
        return 10, f"BTC.D decline accelerating ({recent:+.2f}% vs {prior:+.2f}%)"
    if recent < 0 and prior < 0:
        return 6, "BTC.D steadily declining"
    if recent < 0:
        return 4, "BTC.D starting to fall"
    return 0, "BTC.D not declining"


def _i_fg_level(macro: list[dict]) -> tuple[int, str]:
    """Fear & Greed level — for a long-only spot bot, fear zones are buying opportunities."""
    if not macro or macro[-1]["fear_greed"] is None:
        return 5, "no F&G data"
    fg = macro[-1]["fear_greed"]
    if 45 <= fg <= 68:  return 10, f"F&G {fg} — optimal zone"
    if 35 <= fg <  45:  return 8,  f"F&G {fg} — mild fear, good entry zone"
    if fg < 35:         return 7,  f"F&G {fg} — extreme fear, historically strong buy zone"
    if 68 <  fg <= 80:  return 6,  f"F&G {fg} — greedy but ok"
    return 2, f"F&G {fg} — extreme greed, risk elevated"


def _i_fg_momentum(macro: list[dict]) -> tuple[int, str]:
    """F&G rising over 3 days — crowd optimism building."""
    if len(macro) < 2:
        return 5, "insufficient data"
    latest = macro[-1]
    old    = next(
        (r for r in reversed(macro) if (latest["ts"] - r["ts"]).total_seconds() >= 68 * 3600),
        macro[0],
    )
    if latest["fear_greed"] is None or old["fear_greed"] is None:
        return 5, "no F&G data"
    delta = latest["fear_greed"] - old["fear_greed"]
    if delta >  8:  return 10, f"F&G +{delta:.0f}pts in 3d — optimism building"
    if delta >  3:  return 7,  f"F&G +{delta:.0f}pts — rising"
    if delta > -3:  return 4,  f"F&G flat ({delta:+.0f}pts)"
    return 0, f"F&G −{abs(delta):.0f}pts — sentiment falling"


def _i_btc_momentum(macro: list[dict]) -> tuple[int, str]:
    """BTC in healthy uptrend: 2–8% above its 50-day SMA."""
    try:
        from spot.data_fetcher import load_dataframe
        from spot.streamer import get_prices
        df = load_dataframe("BTC", "1d", limit=51)
        if df.empty or len(df) < 50:
            return 5, "insufficient BTC candles"
        sma50  = float(df["close"].iloc[-50:].mean())
        prices = get_prices()
        btc_px = (prices.get("BTC") or {}).get("price")
        if not btc_px:
            return 5, "BTC price unavailable"
        ratio = (btc_px - sma50) / sma50 * 100
        if ratio < -1:   return 0,  f"BTC {ratio:+.1f}% below SMA50 — bearish"
        if ratio <  2:   return 5,  f"BTC {ratio:+.1f}% — at SMA50"
        if ratio <  8:   return 10, f"BTC {ratio:+.1f}% above SMA50 — healthy uptrend"
        return 4, f"BTC {ratio:+.1f}% above SMA50 — extended, overbought risk"
    except Exception as e:
        return 5, f"btc_momentum error: {e}"


def _i_eth_btc(macro: list[dict]) -> tuple[int, str]:
    """ETH outperforming BTC — classic alt season leading indicator."""
    try:
        eth_closes = _daily_candles("ETH", 3)
        btc_closes = _daily_candles("BTC", 3)
        if len(eth_closes) < 2 or len(btc_closes) < 2:
            return 5, "insufficient ETH/BTC candles"
        ratio_now  = eth_closes[-1] / btc_closes[-1]
        ratio_prev = eth_closes[-2] / btc_closes[-2]
        change = (ratio_now - ratio_prev) / ratio_prev * 100
        if change >  1.5:  return 10, f"ETH/BTC +{change:.2f}% — alt season signal"
        if change >  0.4:  return 7,  f"ETH/BTC +{change:.2f}% — mild ETH outperformance"
        if change > -0.4:  return 4,  f"ETH/BTC flat ({change:+.2f}%)"
        return 0, f"ETH/BTC {change:+.2f}% — ETH lagging BTC"
    except Exception as e:
        return 5, f"eth_btc error: {e}"


def _i_price_breadth(candles: dict[str, list[dict]]) -> tuple[int, str]:
    """% of watchlist coins with last close > 20-candle SMA."""
    above, total = 0, 0
    for cs in candles.values():
        if len(cs) < 20:
            continue
        total += 1
        closes = [c["close"] for c in cs]
        sma20  = sum(closes[-20:]) / 20
        if closes[-1] > sma20:
            above += 1
    if not total:
        return 5, "no candle data"
    pct = above / total * 100
    if pct > 65:  return 10, f"{pct:.0f}% above SMA20 — broad market lift"
    if pct > 50:  return 7,  f"{pct:.0f}% above SMA20"
    if pct > 35:  return 4,  f"{pct:.0f}% above SMA20 — mixed"
    return 0, f"{pct:.0f}% above SMA20 — weak breadth"


def _i_taker_breadth(candles: dict[str, list[dict]]) -> tuple[int, str]:
    """% of coins where last 1h taker_buy_base/volume > 0.55 (aggressive buyers dominant)."""
    above, total = 0, 0
    for cs in candles.values():
        if not cs:
            continue
        last = cs[-1]
        vol  = last.get("volume", 0) or 0
        if not vol:
            continue
        total += 1
        ratio = (last.get("taker_buy_base") or 0) / vol
        if ratio > 0.55:
            above += 1
    if not total:
        return 5, "no taker data"
    pct = above / total * 100
    if pct > 60:  return 10, f"{pct:.0f}% coins — aggressive buyers dominant"
    if pct > 45:  return 6,  f"{pct:.0f}% coins with dominant buying"
    if pct > 30:  return 3,  f"{pct:.0f}% — buying pressure thin"
    return 0, f"{pct:.0f}% — sellers in control"


def _i_volume_breadth(candles: dict[str, list[dict]]) -> tuple[int, str]:
    """% of coins with last 24h volume > 110% of their 7-day average."""
    above, total = 0, 0
    for cs in candles.values():
        if len(cs) < 168:
            continue
        total += 1
        recent_24h = sum(c["volume"] for c in cs[-24:])
        avg_7d_24h = sum(c["volume"] for c in cs[-168:]) / 7
        if avg_7d_24h > 0 and recent_24h > avg_7d_24h * 1.10:
            above += 1
    if not total:
        return 5, "need 7d+ candle history"
    pct = above / total * 100
    if pct > 55:  return 10, f"{pct:.0f}% coins with volume expansion"
    if pct > 35:  return 6,  f"{pct:.0f}% with above-average volume"
    if pct > 20:  return 3,  f"{pct:.0f}% volume expansion (thin)"
    return 0, f"{pct:.0f}% volume expansion — market is quiet"


def _i_market_momentum() -> tuple[int, str]:
    """% of watchlist coins with positive 24h return — forward-looking regime breadth."""
    try:
        from spot.streamer import get_prices
        prices = get_prices()
        if not prices:
            return 5, "no price data"
        positive = sum(1 for p in prices.values()
                       if isinstance(p, dict) and (p.get("change_pct") or 0) > 0)
        total = sum(1 for p in prices.values() if isinstance(p, dict))
        if not total:
            return 5, "no price data"
        pct = positive / total * 100
        if pct > 65:  return 10, f"{pct:.0f}% coins positive 24h — broad momentum"
        if pct > 50:  return 7,  f"{pct:.0f}% coins positive 24h"
        if pct > 35:  return 4,  f"{pct:.0f}% coins positive 24h — mixed"
        return 0, f"{pct:.0f}% coins positive 24h — broad weakness"
    except Exception as e:
        return 5, f"market_momentum error: {e}"


# ── Core computation ──────────────────────────────────────────────────────────

def compute_atmosphere() -> dict:
    macro   = _macro_history(hours=72)
    candles = _watchlist_candles(limit=170)

    indicators: list[tuple[str, str, tuple[int, str]]] = [
        ("btc_dom_trend",   "BTC.D 24h Trend",        _i_btc_dom_trend(macro)),
        ("btc_dom_accel",   "BTC.D Acceleration",      _i_btc_dom_accel(macro)),
        ("fg_level",        "Fear & Greed Level",       _i_fg_level(macro)),
        ("fg_momentum",     "F&G Momentum (3d)",        _i_fg_momentum(macro)),
        ("btc_momentum",    "BTC vs SMA50",             _i_btc_momentum(macro)),
        ("eth_btc_ratio",   "ETH/BTC Ratio",            _i_eth_btc(macro)),
        ("price_breadth",   "Price Breadth",            _i_price_breadth(candles)),
        ("taker_breadth",   "Taker Buy Breadth",        _i_taker_breadth(candles)),
        ("volume_breadth",  "Volume Expansion",         _i_volume_breadth(candles)),
        ("market_momentum", "Market Momentum (24h)",    _i_market_momentum()),
    ]

    total = sum(pts for _, _, (pts, _) in indicators)
    components = {
        key: {"label": label, "score": pts, "detail": detail}
        for key, label, (pts, detail) in indicators
    }

    # Boost capped at 1.10 — bigger sizes at froth tops increases correlated risk (A7)
    if   total >= 80: label, boost = "exceptional", 1.10
    elif total >= 65: label, boost = "favourable",  1.05
    elif total >= 50: label, boost = "neutral",     1.00
    elif total >= 40: label, boost = "low_neutral", 0.75
    else:             label, boost = "hostile",     0.50

    return {
        "score":       total,
        "label":       label,
        "boost":       boost,
        "components":  components,
        "computed_at": datetime.utcnow().isoformat(),
    }


def get_atmosphere() -> dict:
    """Return cached atmosphere score, recomputing if older than 15 min."""
    global _cache
    cached_at = _cache.get("computed_at")
    if cached_at:
        age = (datetime.utcnow() - datetime.fromisoformat(cached_at)).total_seconds()
        if age < _CACHE_TTL:
            return _cache
    try:
        result  = compute_atmosphere()
        _cache  = result
        logger.info(f"[ATM] Score {result['score']}/100 ({result['label']}) boost×{result['boost']}")
        return result
    except Exception as e:
        logger.error(f"[ATM] Compute failed: {e}")
        fallback = {"score": 50, "label": "neutral", "boost": 1.0,
                    "components": {}, "computed_at": datetime.utcnow().isoformat()}
        return _cache or fallback


def boost_for_score(score: int) -> float:
    if score >= 80: return 1.10
    if score >= 65: return 1.05
    if score >= 50: return 1.00
    if score >= 40: return 0.75
    return 0.50


def snapshot_entry_context() -> dict:
    """
    Compact macro snapshot recorded at the moment a bot trade opens.
    Reuses the 15-min atmosphere cache (free if warm). Never raises.
    Keys: atm_score, atm_label, btc_24h_pct, btc_taker_pct, btc_dom, fear_greed, captured_at
    """
    from data.database import get_session
    from data.models import OhlcvCandle, MacroSnapshot

    ctx: dict = {"captured_at": datetime.utcnow().isoformat()}

    try:
        atm = get_atmosphere()
        ctx["atm_score"] = atm["score"]
        ctx["atm_label"] = atm["label"]
    except Exception:
        pass

    try:
        with get_session() as s:
            rows = (
                s.query(OhlcvCandle)
                 .filter(OhlcvCandle.symbol == "BTC", OhlcvCandle.interval == "1h")
                 .order_by(OhlcvCandle.timestamp.desc())
                 .limit(25).all()
            )
            if len(rows) >= 24:
                ctx["btc_24h_pct"] = round(
                    (rows[0].close - rows[23].close) / rows[23].close * 100, 2
                )
            if rows and rows[0].volume:
                ctx["btc_taker_pct"] = round(
                    rows[0].taker_buy_base / rows[0].volume * 100, 1
                )
    except Exception:
        pass

    try:
        with get_session() as s:
            snap = s.query(MacroSnapshot).order_by(MacroSnapshot.timestamp.desc()).first()
            if snap:
                ctx["btc_dom"]    = snap.btc_dominance
                ctx["fear_greed"] = snap.fear_greed_value
    except Exception:
        pass

    return ctx
