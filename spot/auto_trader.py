"""
Paper Auto-Trader — Phase 2 autonomous trading bot.

Every 5 minutes:
  1. Score all bot-held paper positions → close any that fall below EXIT_THRESHOLD
  2. If slots remain → open paper trades for top ENTER signals (score ≥ ENTER_THRESHOLD)
  3. Apply per-coin cooldown after close so the bot doesn't immediately re-enter

Rules:
  - Paper mode only — never touches live trades or real money
  - Only manages trades it opened (notes start with "[BOT]")
  - Respects MAX_POSITIONS cap, cooldown, and the kill switch
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from loguru import logger

# ── Config ────────────────────────────────────────────────────────────────────

# Entry gates — hotness is now primary; timing is a soft ranking tiebreaker
HOTNESS_MIN          = 11    # primary entry gate: technical/structural health (0–20 scale)
TIMING_SOFT_MIN      = 40    # soft timing floor: block only strongly bearish calendar periods
ATM_MIN_ENTRY        = 45    # atmosphere floor (enforced only when atmosphere_gate toggle is ON)
ATM_HOSTILE_FLOOR    = 40    # HARD floor — ALWAYS enforced: <40 = "hostile" regime, no new entries
MAX_GROSS_FRAC       = 0.60  # max total deployed capital as a fraction of equity (gross exposure cap)
EXIT_CYCLES          = 6     # consecutive 5-min cycles (~30 min) below 4H EMA20 before exiting.
                             # 2 cycles = 10 min, i.e. intraday noise resolving a 4H signal;
                             # hard SL / trailing still run every 30s so tail risk is unchanged.
MAX_POSITIONS        = 6     # max concurrent bot positions. 10 slots on a 10-coin watchlist
                             # is index exposure, not selection, and put ~10% of equity at
                             # simultaneous risk in one correlated altcoin factor.
MAX_PER_NARRATIVE    = 2     # max positions in the same narrative at once (concentration cap)

# Equity-based risk model (A8)
EQUITY_USD           = 5000.0  # paper portfolio size
RISK_PCT_PER_TRADE   = 0.01    # risk 1% of equity per trade → $50 max risk
MAX_POSITION_FRAC    = 0.20    # cap single position at 20% of equity → $1000
FEE_RT_PCT           = 0.20    # round-trip fee deducted from paper P&L (0.10% each side)

# ATR-based stops / trail / TP — adapts to each coin's actual volatility (A4)
ATR_STOP_K           = 1.5    # stop = entry − ATR14(4H)% × ATR_STOP_K
ATR_TRAIL_K          = 1.0    # trailing stop pct = ATR14(4H)% × ATR_TRAIL_K
ATR_TP_HARD_K        = 3.5    # hard TP = entry + ATR14(4H)% × ATR_TP_HARD_K
MIN_STOP_PCT         = 2.0    # floor: stop always ≥ 2% below entry
MAX_STOP_PCT         = 8.0    # cap: stop never > 8% below entry

# Exit Enhancements (Phase 2)
ATR_TRAIL_ARM_K      = 1.5    # arm trailing when gain ≥ 1.5×ATR (from entry)
ATR_TRAIL_K_TP1      = 1.0    # trail distance after TP1 (1R) = ATR × 1.0
ATR_TRAIL_K_TP2      = 0.5    # trail distance after TP2 (2R) = ATR × 0.5
ATR_TRAIL_K_TP3      = 0.3    # trail distance after TP3 (3R) = ATR × 0.3
TP1_R_MULT           = 1.0    # TP1 at 1R (1× stop distance)
TP2_R_MULT           = 2.0    # TP2 at 2R
TP3_R_MULT           = 3.0    # TP3 at 3R
TP1_SIZE_PCT         = 0.30   # 30% at TP1
TP2_SIZE_PCT         = 0.30   # 30% at TP2
TP3_SIZE_PCT         = 0.40   # 40% at TP3
VOL_TIMEOUT_ATR_K    = 0.5    # exit if |price-entry| < 0.5×ATR for VOL_TIMEOUT_HOURS
VOL_TIMEOUT_HOURS    = 4      # hours of stagnation before volatility timeout
MAX_HOLD_ATR_MULT    = 10.0   # max hold time = ATR × this multiplier (in hours)

# Entry Enhancements (Phase 2)
VOL_RATIO_MIN        = 1.5    # minimum volume ratio on entry candle for breakout confirmation
BTC_SMA50_GRADUATED  = True   # enable graduated BTC regime gate (size ∝ distance above SMA50)
BTC_SMA50_MIN_DIST   = 0.0    # minimum distance above SMA50 to allow any entry (0 = at SMA50)
BTC_SMA50_MAX_DIST   = 0.10   # distance above SMA50 for full position size (10%)
MULTI_TF_CONFIRM     = True   # require 1H + 4H alignment for entry

# Fallbacks (used in status display and when ATR is unavailable)
POSITION_USD         = 1000.0
STOP_LOSS_PCT        = 3.0
TRAILING_STOP_PCT    = 2.5
TAKE_PROFIT_PCT      = 6.0
TP1_PCT              = 3.5    # TP1 ≈ 1× stop-distance (dynamic); this is the legacy reference
RUNNER_SIZE_RATIO    = 0.5    # fraction kept as runner after TP1

# Risk circuit breakers
UNREALIZED_DD_LIMIT  = 200.0  # pause new entries if open book total P&L ≤ −$200
DAILY_LOSS_LIMIT_USD = 60.0
WEEKLY_LOSS_LIMIT_USD= 150.0

# Risk Management Enhancements (Phase 2)
CORRELATION_CLUSTER_LIMIT = 3     # max positions per correlation cluster (narrative/sector)
PORTFOLIO_DD_LIMIT_PCT    = 0.10  # pause all if portfolio drawdown > 10%
KELLY_SIZING_ENABLED      = True  # use Kelly/volatility-based sizing
KELLY_WIN_RATE            = 0.55  # estimated win rate for Kelly formula
KELLY_WIN_LOSS_RATIO      = 1.5   # estimated avg win / avg loss for Kelly formula
KELLY_MAX_FRACTION        = 0.25  # cap Kelly fraction at 25% (quarter Kelly for safety)

COOLDOWN_MINUTES     = 60
BTC_TREND_GATE       = True
CB_IN_PAPER_MODE     = False

_STATE_FILE = Path("data/bot_state.json")
_activity: list[dict] = []           # in-memory log of recent actions
_exit_streak: dict[int, int] = {}    # trade_id → consecutive structure-break cycle count (A6)
_btc_regime_cache: dict = {}         # {ok, price, sma50, at} — refreshed every 4h

# Exit Enhancement state tracking
_trailing_armed: dict[int, bool] = {}      # trade_id → trailing armed (gain ≥ 1.5×ATR)
_tp_stage: dict[int, int] = {}             # trade_id → 0=none, 1=TP1 hit, 2=TP2 hit, 3=TP3 hit
_stagnation_start: dict[int, datetime] = {} # trade_id → when price entered ±0.5×ATR band
_entry_price_map: dict[int, float] = {}     # trade_id → entry price (for stagnation check)
_atr_pct_map: dict[int, float] = {}         # trade_id → ATR% at entry (for timeout calc)


# ── Persistent state (enabled flag + cooldowns) ────────────────────────────────
def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"enabled": False, "cooldowns": {}}


def _save_state(state: dict) -> None:
    try:
        _STATE_FILE.write_text(json.dumps(state, default=str))
    except Exception as e:
        logger.warning(f"[BOT] Could not save state: {e}")


_state = _load_state()


def is_enabled() -> bool:
    return bool(_state.get("enabled", False))


def get_atmosphere_settings() -> dict:
    return {
        "gate_enabled":  bool(_state.get("atmosphere_gate",  False)),
        "boost_enabled": bool(_state.get("atmosphere_boost", True)),
    }


def toggle_atmosphere_gate() -> bool:
    new_val = not bool(_state.get("atmosphere_gate", False))
    _state["atmosphere_gate"] = new_val
    _save_state(_state)
    logger.info(f"[BOT] Atmosphere gate {'ON' if new_val else 'OFF'}")
    return new_val


def toggle_atmosphere_boost() -> bool:
    new_val = not bool(_state.get("atmosphere_boost", True))
    _state["atmosphere_boost"] = new_val
    _save_state(_state)
    logger.info(f"[BOT] Atmosphere boost {'ON' if new_val else 'OFF'}")
    return new_val


def set_enabled(val: bool) -> None:
    _state["enabled"] = val
    _save_state(_state)
    logger.info(f"[BOT] {'ENABLED — will trade on next 5-min tick' if val else 'PAUSED'}")


def _cooldown_ok(symbol: str) -> bool:
    cd = _state.get("cooldowns", {}).get(symbol)
    if not cd:
        return True
    return datetime.utcnow() >= datetime.fromisoformat(cd)


def _set_cooldown(symbol: str) -> None:
    _state.setdefault("cooldowns", {})[symbol] = (
        datetime.utcnow() + timedelta(minutes=COOLDOWN_MINUTES)
    ).isoformat()
    _save_state(_state)


def _trend_ok(symbol: str, live_price: float) -> bool:
    """
    Return False if the coin is in a clear downtrend (price below 24h SMA).
    Prevents re-entering coins that keep getting stopped out while falling.
    Returns True on any data error so we don't incorrectly block entries.
    """
    try:
        from data.database import get_session
        from data.models import OhlcvCandle
        with get_session() as s:
            rows = (
                s.query(OhlcvCandle.close)
                 .filter(OhlcvCandle.symbol == symbol, OhlcvCandle.interval == "1h")
                 .order_by(OhlcvCandle.timestamp.desc())
                 .limit(24)
                 .all()
            )
        if len(rows) < 12:
            return True  # not enough history — don't block
        sma24 = sum(r[0] for r in rows) / len(rows)
        ok = live_price >= sma24 * 0.99  # allow 1% tolerance below SMA
        if not ok:
            logger.info(f"[BOT] TREND FILTER {symbol}: live={live_price:.5g} < SMA24={sma24:.5g} — skipping entry")
        return ok
    except Exception:
        return True


def _get_btc_sma50() -> float | None:
    """
    Compute BTC 50-day SMA from our own DB candles. Cached for 24h — the daily
    SMA barely shifts between candle closes, so recomputing every cycle is wasted work.
    Returns None if we don't have enough candles yet.
    """
    global _btc_regime_cache
    now    = datetime.utcnow()
    cached = _btc_regime_cache.get("sma50_at")
    if cached and (now - cached).total_seconds() < 24 * 3600 and "sma50" in _btc_regime_cache:
        return _btc_regime_cache["sma50"]

    try:
        from spot.data_fetcher import load_dataframe
        df = load_dataframe("BTC", "1d", limit=51)
        if df.empty or len(df) < 50:
            return None
        sma50 = round(float(df["close"].iloc[-50:].mean()), 2)
        _btc_regime_cache["sma50"]    = sma50
        _btc_regime_cache["sma50_at"] = now
        return sma50
    except Exception:
        return _btc_regime_cache.get("sma50")   # serve stale value on error


def _get_btc_regime() -> bool:
    """
    True = BTC is above its 50-day SMA → altcoin longs allowed.
    False = BTC is in a downtrend → block new entries.

    Uses live BTC price from the in-memory stream (updated every few seconds)
    and SMA50 computed from our own DB daily candles (cached 24h — barely changes
    between daily candle closes). No external HTTP call needed.
    """
    global _btc_regime_cache
    from spot.streamer import get_prices

    sma50 = _get_btc_sma50()
    if sma50 is None:
        return True  # not enough history yet — don't block

    prices = get_prices()
    btc    = prices.get("BTC")
    if not btc:
        return True  # stream not ready — don't block

    price = btc["price"]
    ok    = price >= sma50 * 0.99   # 1% tolerance
    prev  = _btc_regime_cache.get("ok")
    _btc_regime_cache.update({"ok": ok, "price": round(price, 2)})

    if not ok and prev is not False:
        logger.info(f"[BOT] BTC regime BEARISH: ${price:,.0f} < SMA50 ${sma50:,.0f} — blocking new entries")
    elif ok and prev is False:
        logger.info(f"[BOT] BTC regime BULLISH: ${price:,.0f} ≥ SMA50 ${sma50:,.0f} — gate open")
    return ok


def _daily_pnl() -> float:
    """Realized P&L (USD) for all bot paper trades closed today (UTC)."""
    try:
        from data.database import get_session
        from data.models import SpotTrade
        day_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        with get_session() as s:
            trades = (
                s.query(SpotTrade)
                 .filter(
                     SpotTrade.mode == "paper",
                     SpotTrade.notes.like("[BOT]%"),
                     SpotTrade.exit_price.isnot(None),
                     SpotTrade.exit_time >= day_start,
                 )
                 .all()
            )
            return sum(t.pnl_usd or 0 for t in trades)
    except Exception:
        return 0.0


def _weekly_pnl() -> float:
    """Realized P&L (USD) for all bot paper trades closed in the last 7 days."""
    try:
        from data.database import get_session
        from data.models import SpotTrade
        week_ago = datetime.utcnow() - timedelta(days=7)
        with get_session() as s:
            trades = (
                s.query(SpotTrade)
                 .filter(
                     SpotTrade.mode == "paper",
                     SpotTrade.notes.like("[BOT]%"),
                     SpotTrade.exit_price.isnot(None),
                     SpotTrade.exit_time >= week_ago,
                 )
                 .all()
            )
            return sum(t.pnl_usd or 0 for t in trades)
    except Exception:
        return 0.0


def _drawdown_ok() -> bool:
    """Return False if daily or weekly loss limits have been breached — pause new entries.
    Skipped in paper mode (CB_IN_PAPER_MODE=False) since no real capital is at risk."""
    if not CB_IN_PAPER_MODE:
        return True
    daily  = _daily_pnl()
    weekly = _weekly_pnl()
    if daily <= -DAILY_LOSS_LIMIT_USD:
        logger.warning(f"[BOT] Daily loss limit hit: ${daily:.2f} ≤ -${DAILY_LOSS_LIMIT_USD:.0f} — pausing new entries")
        return False
    if weekly <= -WEEKLY_LOSS_LIMIT_USD:
        logger.warning(f"[BOT] Weekly loss limit hit: ${weekly:.2f} ≤ -${WEEKLY_LOSS_LIMIT_USD:.0f} — pausing new entries")
        return False
    return True


# ── Volatility / structure helpers ───────────────────────────────────────────

def _atr14(symbol: str, price: float) -> float:
    """ATR14 (4H candles) as % of current price. Falls back to STOP_LOSS_PCT/ATR_STOP_K."""
    try:
        from data.database import get_session
        from data.models import OhlcvCandle
        with get_session() as s:
            rows = (
                s.query(OhlcvCandle)
                 .filter(OhlcvCandle.symbol == symbol, OhlcvCandle.interval == "4h")
                 .order_by(OhlcvCandle.timestamp.desc())
                 .limit(30)
                 .all()
            )
        if len(rows) < 15:
            return STOP_LOSS_PCT / ATR_STOP_K
        candles = list(reversed(rows))
        trs = []
        for i in range(1, len(candles)):
            h  = candles[i].high
            l  = candles[i].low
            pc = candles[i - 1].close
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        atr = sum(trs[-14:]) / 14
        return atr / price * 100
    except Exception:
        return STOP_LOSS_PCT / ATR_STOP_K


def _get_ema20_4h(symbol: str) -> float | None:
    """EMA20 on 4H candles — used for both structure entry confirmation and exit."""
    try:
        from data.database import get_session
        from data.models import OhlcvCandle
        with get_session() as s:
            rows = (
                s.query(OhlcvCandle.close)
                 .filter(OhlcvCandle.symbol == symbol, OhlcvCandle.interval == "4h")
                 .order_by(OhlcvCandle.timestamp.desc())
                 .limit(30)
                 .all()
            )
        if len(rows) < 20:
            return None
        closes = [float(r[0]) for r in reversed(rows)]
        k, ema = 2 / 21, sum(closes[:20]) / 20
        for c in closes[20:]:
            ema = c * k + ema * (1 - k)
        return ema
    except Exception:
        return None


def _structure_ok(symbol: str, price: float) -> bool:
    """Price is above EMA20 on 4H — confirms coin is in a short-term uptrend at entry."""
    ema20 = _get_ema20_4h(symbol)
    if ema20 is None:
        return True  # missing data: don't block
    ok = price > ema20
    if not ok:
        logger.debug(f"[BOT] {symbol} structure weak: ${price:.4g} < EMA20 ${ema20:.4g}")
    return ok


def _get_ema20_1h(symbol: str) -> float | None:
    """EMA20 on 1H candles — used for multi-timeframe confirmation."""
    try:
        from data.database import get_session
        from data.models import OhlcvCandle
        with get_session() as s:
            rows = (
                s.query(OhlcvCandle.close)
                 .filter(OhlcvCandle.symbol == symbol, OhlcvCandle.interval == "1h")
                 .order_by(OhlcvCandle.timestamp.desc())
                 .limit(30)
                 .all()
            )
        if len(rows) < 20:
            return None
        closes = [float(r[0]) for r in reversed(rows)]
        k, ema = 2 / 21, sum(closes[:20]) / 20
        for c in closes[20:]:
            ema = c * k + ema * (1 - k)
        return ema
    except Exception:
        return None


def _multi_tf_ok(symbol: str, price: float) -> bool:
    """Multi-timeframe confirmation: price above EMA20 on both 1H and 4H."""
    if not MULTI_TF_CONFIRM:
        return True
    ema20_1h = _get_ema20_1h(symbol)
    ema20_4h = _get_ema20_4h(symbol)
    if ema20_1h is None or ema20_4h is None:
        return True  # missing data: don't block
    ok = price > ema20_1h and price > ema20_4h
    if not ok:
        logger.debug(f"[BOT] {symbol} multi-TF fail: 1H EMA20={ema20_1h:.4g}, 4H EMA20={ema20_4h:.4g}, price={price:.4g}")
    return ok


def _get_btc_sma50_distance() -> float | None:
    """Get BTC price distance above SMA50 as a fraction (e.g., 0.05 = 5% above).
    Returns None if data unavailable."""
    try:
        from spot.streamer import get_prices
        sma50 = _get_btc_sma50()
        if sma50 is None:
            return None
        prices = get_prices()
        btc = prices.get("BTC")
        if not btc:
            return None
        price = btc["price"]
        return (price - sma50) / sma50
    except Exception:
        return None


def _btc_regime_size_multiplier() -> float:
    """Graduated BTC regime gate: position size ∝ distance above SMA50.
    Returns multiplier between 0.0 and 1.0 (capped at 1.0).
    At SMA50 = 0.0, at BTC_SMA50_MAX_DIST = 1.0."""
    if not BTC_SMA50_GRADUATED:
        return 1.0
    dist = _get_btc_sma50_distance()
    if dist is None:
        return 1.0  # no data: don't penalize
    if dist <= BTC_SMA50_MIN_DIST:
        return 0.0  # at or below SMA50: no entry
    # Linear interpolation between min and max distance
    multiplier = min(1.0, max(0.0, (dist - BTC_SMA50_MIN_DIST) / (BTC_SMA50_MAX_DIST - BTC_SMA50_MIN_DIST)))
    return multiplier


def _volume_breakout_ok(symbol: str) -> bool:
    """Volume-confirmed breakout: require vol_ratio_closed ≥ 1.5 on entry candle."""
    try:
        from spot.scorer import get_coin_detail
        hd = get_coin_detail(symbol)
        if hd is None:
            return True  # no data: don't block
        vol_ratio = hd.get("vol_ratio", 1.0)
        ok = vol_ratio >= VOL_RATIO_MIN
        if not ok:
            logger.debug(f"[BOT] {symbol} volume breakout fail: vol_ratio={vol_ratio:.2f} < {VOL_RATIO_MIN}")
        return ok
    except Exception:
        return True  # error: don't block


def _unrealized_pnl(bot_trades: list[dict], live_prices: dict) -> float:
    """Sum of unrealized P&L (USD) across all open bot positions."""
    total = 0.0
    for pos in bot_trades:
        px   = (live_prices.get(pos["symbol"]) or {}).get("price") or pos["entry_price"]
        size = pos.get("size_usd") or POSITION_USD
        total += (px - pos["entry_price"]) / pos["entry_price"] * size
    return round(total, 2)


def _portfolio_drawdown_pct(bot_trades: list[dict], live_prices: dict) -> float:
    """Calculate portfolio drawdown as percentage of equity."""
    if not bot_trades:
        return 0.0
    unreal = _unrealized_pnl(bot_trades, live_prices)
    return abs(unreal) / EQUITY_USD if unreal < 0 else 0.0


def _correlation_cluster_ok(symbol: str, held_syms: set[str], watchlist: list[dict]) -> bool:
    """Correlation-adjusted position limits: cluster by narrative/sector.
    Returns False if adding this symbol would exceed CORRELATION_CLUSTER_LIMIT."""
    try:
        from spot.narratives import get_narrative_for_coin
    except Exception:
        def get_narrative_for_coin(_s):  # noqa: D103
            return None

    wl_map = {c["symbol"]: c for c in watchlist}
    base = symbol.replace("USDT", "")
    target_narrative = get_narrative_for_coin(base)
    if not target_narrative:
        target_narrative = wl_map.get(symbol, {}).get("narrative")
    if not target_narrative:
        return True  # no narrative info: don't block

    def _norm(v) -> str:
        return "".join(ch for ch in str(v or "").lower() if ch.isalnum())

    target = _norm(target_narrative)
    if not target:
        return True

    count = 0
    for s in held_syms:
        b = s.replace("USDT", "")
        cands = {_norm(wl_map.get(s, {}).get("narrative")), _norm(get_narrative_for_coin(b))}
        if any(c and (c == target or c.startswith(target) or target.startswith(c)) for c in cands):
            count += 1
    return count < CORRELATION_CLUSTER_LIMIT


def _portfolio_dd_ok(bot_trades: list[dict], live_prices: dict) -> bool:
    """Portfolio-level circuit breaker: pause all if correlated drawdown > threshold."""
    dd_pct = _portfolio_drawdown_pct(bot_trades, live_prices)
    if dd_pct > PORTFOLIO_DD_LIMIT_PCT:
        logger.warning(f"[BOT] Portfolio drawdown {dd_pct:.1%} > {PORTFOLIO_DD_LIMIT_PCT:.0%} — pausing all new entries")
        return False
    return True


def _kelly_position_fraction(atr_pct: float) -> float:
    """Kelly/volatility-based sizing: replace fixed risk budget.
    Kelly fraction = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
    Then scale by volatility (lower vol = larger position) and cap at KELLY_MAX_FRACTION."""
    if not KELLY_SIZING_ENABLED:
        return 1.0  # use default sizing

    # Basic Kelly formula
    win_rate = KELLY_WIN_RATE
    win_loss_ratio = KELLY_WIN_LOSS_RATIO
    kelly_f = (win_rate * win_loss_ratio - (1 - win_rate)) / win_loss_ratio
    kelly_f = max(0.0, min(kelly_f, KELLY_MAX_FRACTION))

    # Volatility adjustment: lower ATR% → larger position (inverse relationship)
    # Normalize around 3% ATR as baseline
    vol_adj = min(2.0, max(0.5, 3.0 / max(atr_pct, 0.5)))

    return kelly_f * vol_adj


def _narrative_ok(narrative: str | None, held_syms: set[str], watchlist: list[dict]) -> bool:
    """Enforce MAX_PER_NARRATIVE concentration cap per narrative category.

    Robust matching: the watchlist row's free-text 'narrative' field and
    spot.narratives can disagree (e.g. "Real World Assets" vs
    "Real World Assets (RWA)"), and any mismatch or None silently disabled the cap —
    letting the bot stack 3+ correlated RWA or AI alts into a single factor bet.
    We normalise and check both sources."""
    if not narrative:
        return True

    def _norm(v) -> str:
        return "".join(ch for ch in str(v or "").lower() if ch.isalnum())

    target = _norm(narrative)
    if not target:
        return True

    wl_map = {c["symbol"]: c for c in watchlist}
    try:
        from spot.narratives import get_narrative_for_coin
    except Exception:
        def get_narrative_for_coin(_s):  # noqa: D103
            return None

    count = 0
    for s in held_syms:
        base  = s.replace("USDT", "")
        cands = {_norm(wl_map.get(s, {}).get("narrative")), _norm(get_narrative_for_coin(base))}
        if any(c and (c == target or c.startswith(target) or target.startswith(c)) for c in cands):
            count += 1
    return count < MAX_PER_NARRATIVE


def _xrp_swing_ok(symbol: str) -> bool:
    """Cross-bot gate: defer XRP entries to the specialist XRP Swing engine.
    Blocks generic XRP longs when the swing engine's latest verdict is WATCHING
    (conditions NOT right for XRP) or IN_TRADE (it already holds XRP exposure).
    Fail-safe: any error, missing, or stale (>5h) evaluation returns True."""
    base = symbol.replace("USDT", "")
    if base != "XRP":
        return True
    try:
        from spot.xrp_swing import get_latest_setup
        setup = get_latest_setup()
        if not setup:
            return True
        # Staleness guard — never block on an old evaluation
        ev = setup.get("evaluated_at")
        if ev:
            age_h = (datetime.utcnow() - datetime.fromisoformat(ev)).total_seconds() / 3600
            if age_h > 5:
                return True
        verdict = setup.get("verdict")
        # Defer to the specialist on EVERY non-null verdict. The previous list omitted
        # SETUP_FORMING and ENTRY_READY — precisely the states where the swing engine
        # is about to open or stage into its own XRP position, so the generic bot could
        # double XRP exposure with a different stop and a conflicting exit rule.
        if verdict in ("WATCHING", "SETUP_FORMING", "IN_TRADE", "SHADOW_ENTRY", "ENTRY_READY"):
            logger.info(
                f"[BOT] {symbol} entry BLOCKED — XRP Swing verdict {verdict} "
                f"(btc_dom={setup.get('btc_dom')}, fg={setup.get('fg_value')})"
            )
            return False
        return True
    except Exception:
        return True


# ── DB helpers — paper trade open / close ─────────────────────────────────────
def _is_bot_trade(pos: dict) -> bool:
    return pos.get("mode") == "paper" and str(pos.get("notes") or "").startswith("[BOT]")


def _open_paper_trade(
    symbol: str, entry_price: float, score: int, reasons: list[str],
    size_multiplier: float = 1.0,
) -> int:
    from data.database import get_session
    from data.models import SpotTrade

    # ATR-based stops — adapt to each coin's actual volatility (A4)
    atr_pct     = _atr14(symbol, entry_price)
    stop_pct    = max(min(atr_pct * ATR_STOP_K, MAX_STOP_PCT), MIN_STOP_PCT)
    trail_pct   = max(atr_pct * ATR_TRAIL_K, 1.5)
    tp_hard_pct = atr_pct * ATR_TP_HARD_K

    stop_loss   = round(entry_price * (1 - stop_pct    / 100), 6)
    take_profit = round(entry_price * (1 + tp_hard_pct / 100), 6)

    # Equity-based risk sizing: risk $EQUITY×RISK_PCT per trade, capped at MAX_POSITION_FRAC (A8)
    risk_usd     = EQUITY_USD * RISK_PCT_PER_TRADE
    position_usd = min(risk_usd / (stop_pct / 100), EQUITY_USD * MAX_POSITION_FRAC)

    # RISK MANAGEMENT: Kelly/volatility-based sizing
    kelly_mult = _kelly_position_fraction(atr_pct)
    position_usd = round(position_usd * min(size_multiplier * kelly_mult, 1.10), 2)

    boost_tag = f" · atm×{size_multiplier:.2f}" if size_multiplier != 1.0 else ""
    if kelly_mult != 1.0:
        boost_tag += f" · kelly×{kelly_mult:.2f}"
    notes = f"[BOT] Score {score}/20 · ATR={atr_pct:.2f}% · stop={stop_pct:.2f}% · {' · '.join(reasons)}{boost_tag}"

    with get_session() as s:
        trade = SpotTrade(
            symbol            = symbol,
            mode              = "paper",
            direction         = "long",
            entry_price       = entry_price,
            size_usd          = position_usd,
            stop_loss         = stop_loss,
            target            = take_profit,
            trailing_stop_pct = round(trail_pct, 2),   # ATR-derived (was static 2.5% — trail_pct was computed then thrown away)
            entry_time        = datetime.utcnow(),
            notes             = notes,
        )
        s.add(trade)
        s.flush()
        tid = trade.id
        try:
            import json
            from spot.atmosphere import snapshot_entry_context
            ctx = snapshot_entry_context()
            # Persist entry scores so the feedback loop can learn entry edge, not just exit quality
            ctx["timing_score_at_entry"] = score
            try:
                from spot.scorer import get_coin_detail
                hd = get_coin_detail(symbol)
                if hd:
                    trade.hotness_at_entry          = hd.get("score")
                    ctx["hotness_score_at_entry"]   = hd.get("score")
                    ctx["rsi_at_entry"]             = hd.get("rsi_1d")
                    ctx["above_ema200_at_entry"]    = hd.get("above_ema200")
                    ctx["vol_ratio_at_entry"]       = hd.get("vol_ratio")
            except Exception:
                logger.warning(f"[BOT] Could not fetch hotness detail for {symbol} at entry")
            trade.macro_context = json.dumps(ctx)
        except Exception:
            logger.warning(f"[BOT] Could not snapshot macro context for {symbol}")

    # Initialize exit enhancement state tracking
    _trailing_armed[tid] = False
    _tp_stage[tid] = 0
    _stagnation_start[tid] = None
    _entry_price_map[tid] = entry_price
    _atr_pct_map[tid] = atr_pct

    logger.info(f"[BOT] OPEN  {symbol} paper @ ${entry_price:.5g}  score={score}/100  id={tid}")
    return tid


def _close_paper_trade(trade_id: int, exit_price: float, reason: str) -> float:
    """Close the trade, return net P&L % after round-trip fees (A4)."""
    from data.database import get_session
    from data.models import SpotTrade

    pnl = 0.0
    with get_session() as s:
        trade = s.query(SpotTrade).filter(SpotTrade.id == trade_id).first()
        if trade and trade.exit_price is None:
            gross_pct   = (exit_price - trade.entry_price) / trade.entry_price * 100
            pnl         = gross_pct - FEE_RT_PCT          # net of round-trip fees
            runner_usd  = (trade.size_usd or POSITION_USD) * pnl / 100
            tp1_banked  = trade.tp1_pnl_usd or 0.0
            pnl_usd     = runner_usd + tp1_banked
            trade.exit_price = exit_price
            trade.exit_time  = datetime.utcnow()
            trade.pnl_pct    = round(pnl, 2)
            trade.pnl_usd    = round(pnl_usd, 2)
            trade.outcome    = "win" if pnl_usd > 0.01 else "loss" if pnl_usd < -0.01 else "breakeven"
            trade.notes      = (trade.notes or "") + f" | Bot closed: {reason} · P&L {pnl:+.2f}% (net fees)"

    # Clean up exit enhancement state tracking
    _trailing_armed.pop(trade_id, None)
    _tp_stage.pop(trade_id, None)
    _stagnation_start.pop(trade_id, None)
    _entry_price_map.pop(trade_id, None)
    _atr_pct_map.pop(trade_id, None)
    _exit_streak.pop(trade_id, None)

    logger.info(f"[BOT] CLOSE trade {trade_id} @ ${exit_price:.5g} — {reason} — P&L {pnl:+.2f}% (net)")
    return pnl


# ── Main cycle ─────────────────────────────────────────────────────────────────
def run_cycle(positions: list[dict], watchlist: list[dict], live_prices: dict) -> None:
    """
    Called every 5 minutes by the scheduler.
    positions    — all open spot trades (from get_open_positions)
    watchlist    — active watchlist coins
    live_prices  — {symbol: {price, change_pct, …}} from get_prices()
    """
    if not is_enabled():
        return

    from spot.signal_bot import timing_score   # used for ranking in entry section
    from spot.positions import get_open_positions

    now        = datetime.utcnow()
    bot_trades = [p for p in positions if _is_bot_trade(p)]

    # ── 0. Regime-flip: tighten stops immediately when BTC turns bearish (A3) ──
    prev_btc_ok = _btc_regime_cache.get("ok")
    btc_ok_now  = _get_btc_regime()   # updates cache as a side-effect
    if BTC_TREND_GATE and not btc_ok_now and prev_btc_ok is True:
        from spot.positions import update_stop_loss as _usl
        tightened = 0
        for pos in bot_trades:
            px     = (live_prices.get(pos["symbol"]) or {}).get("price") or pos["entry_price"]
            new_sl = round(px * 0.985, 6)   # 1.5% below current price
            if new_sl > (pos.get("stop_loss") or 0):
                _usl(pos["id"], new_sl)
                tightened += 1
        if tightened:
            logger.warning(f"[BOT] REGIME FLIP bearish — {tightened} position stops tightened to 1.5% below current")

    # ── 1. Close any bot position that breached hard stops or structure exit ────
    closed_syms: set[str] = set()
    for pos in bot_trades:
        sym      = pos["symbol"]
        px       = (live_prices.get(sym) or {}).get("price") or pos["entry_price"]
        entry    = pos["entry_price"]
        gain_pct = (px - entry) / entry * 100
        tp1_fired = pos.get("tp1_pnl_usd") is not None
        tid      = pos["id"]

        # Get ATR% for this trade (from entry or recalculate)
        atr_pct = _atr_pct_map.get(tid) or _atr14(sym, entry)
        stop_dist_pct = atr_pct * ATR_STOP_K  # 1R = stop distance

        # Take profit — full close when spike hits target price
        target = pos.get("target")
        if target and px >= target:
            pnl = _close_paper_trade(pos["id"], px, f"take profit hit @ {px:.5g}")
            _set_cooldown(sym)
            closed_syms.add(sym)
            _log_activity("CLOSED", sym, 0, px, pnl=pnl)
            continue

        # ── Enhanced Exit Logic: Partial takes at 1R, 2R, 3R with scaling trail ──

        # TP1 at 1R (30% size) → move SL to breakeven, arm trailing at ATR×1.0
        tp1_level = entry * (1 + TP1_R_MULT * stop_dist_pct / 100)
        if not tp1_fired and gain_pct >= TP1_R_MULT * stop_dist_pct:
            from spot.positions import apply_tp1
            apply_tp1(pos["id"], (pos.get("size_usd") or POSITION_USD) * TP1_SIZE_PCT,
                      entry, tp1_price=px)
            _tp_stage[tid] = 1
            # Arm trailing from entry now that TP1 hit
            _trailing_armed[tid] = True
            _log_activity("TP1", sym, 0, px)
            logger.info(f"[BOT] {sym} TP1 (1R) @ ${px:.5g} +{gain_pct:.2f}% — 30% locked, SL→BE, trailing armed at ATR×{ATR_TRAIL_K_TP1}")
            continue

        # Breakeven stop — after TP1
        sl = pos.get("stop_loss") or round(entry * (1 - STOP_LOSS_PCT / 100), 6)
        if _tp_stage.get(tid, 0) >= 1 and sl is not None and sl < entry:
            from spot.positions import update_stop_loss as _update_sl
            _update_sl(pos["id"], entry)
            sl = entry
            logger.info(f"[BOT] {sym} breakeven stop engaged (post-TP1) — gain {gain_pct:.2f}%")

        # TP2 at 2R (30% size) → tighten trail to ATR×0.5
        tp2_level = entry * (1 + TP2_R_MULT * stop_dist_pct / 100)
        if _tp_stage.get(tid, 0) == 1 and gain_pct >= TP2_R_MULT * stop_dist_pct:
            from spot.positions import apply_tp1
            apply_tp1(pos["id"], (pos.get("size_usd") or POSITION_USD) * TP2_SIZE_PCT,
                      entry, tp1_price=px)
            _tp_stage[tid] = 2
            # Update trailing stop pct to tighter level
            new_trail_pct = max(atr_pct * ATR_TRAIL_K_TP2, 1.0)
            from spot.positions import update_trailing_pct
            update_trailing_pct(pos["id"], new_trail_pct)
            _log_activity("TP2", sym, 0, px)
            logger.info(f"[BOT] {sym} TP2 (2R) @ ${px:.5g} +{gain_pct:.2f}% — 30% more locked, trail tightened to ATR×{ATR_TRAIL_K_TP2}")
            continue

        # TP3 at 3R (40% size) → trail at ATR×0.3
        tp3_level = entry * (1 + TP3_R_MULT * stop_dist_pct / 100)
        if _tp_stage.get(tid, 0) == 2 and gain_pct >= TP3_R_MULT * stop_dist_pct:
            from spot.positions import apply_tp1
            apply_tp1(pos["id"], (pos.get("size_usd") or POSITION_USD) * TP3_SIZE_PCT,
                      entry, tp1_price=px)
            _tp_stage[tid] = 3
            # Update trailing stop pct to tightest level
            new_trail_pct = max(atr_pct * ATR_TRAIL_K_TP3, 0.8)
            from spot.positions import update_trailing_pct
            update_trailing_pct(pos["id"], new_trail_pct)
            _log_activity("TP3", sym, 0, px)
            logger.info(f"[BOT] {sym} TP3 (3R) @ ${px:.5g} +{gain_pct:.2f}% — final 40% locked, trail tightened to ATR×{ATR_TRAIL_K_TP3}")
            continue

        # Trailing peak update — keep peak current so 5-min cycle is self-sufficient (A9)
        ts_pct  = pos.get("trailing_stop_pct")
        ts_peak = pos.get("trailing_stop_peak") or entry
        if px > ts_peak:
            from spot.positions import update_trailing_peak
            update_trailing_peak(pos["id"], px)
            ts_peak = px

        # Hard stop-loss
        if sl and px <= sl:
            pnl = _close_paper_trade(pos["id"], px, f"stop-loss hit @ {px:.5g}")
            _set_cooldown(sym)
            closed_syms.add(sym)
            _log_activity("CLOSED", sym, 0, px, pnl=pnl)
            logger.info(f"[BOT] SL triggered {sym} @ ${px:.5g} (SL was ${sl:.5g})")
            continue

        # ── ATR-based trailing from entry (armed when gain ≥ 1.5×ATR) ──
        # Arm trailing if not already armed and gain ≥ 1.5×ATR
        if not _trailing_armed.get(tid, False) and gain_pct >= ATR_TRAIL_ARM_K * stop_dist_pct:
            _trailing_armed[tid] = True
            logger.info(f"[BOT] {sym} trailing ARMED — gain {gain_pct:.2f}% ≥ {ATR_TRAIL_ARM_K}×ATR ({ATR_TRAIL_ARM_K * stop_dist_pct:.2f}%)")

        # Trailing stop — fires once armed (after TP1 or at 1.5×ATR from entry)
        if ts_pct and _trailing_armed.get(tid, False):
            ts_level = ts_peak * (1 - ts_pct / 100)
            if ts_level > entry and px <= ts_level:
                pnl = _close_paper_trade(pos["id"], px, f"trailing stop hit @ {px:.5g} (peak {ts_peak:.5g})")
                _set_cooldown(sym)
                closed_syms.add(sym)
                _log_activity("CLOSED", sym, 0, px, pnl=pnl)
                logger.info(f"[BOT] Trailing stop {sym} @ ${px:.5g} (peak ${ts_peak:.5g})")
                continue

        # ── Volatility-adjusted timeout: exit if |price-entry| < 0.5×ATR for 4 hours ──
        stagnation_threshold = VOL_TIMEOUT_ATR_K * atr_pct  # 0.5×ATR%
        price_diff_pct = abs(px - entry) / entry * 100
        if price_diff_pct < stagnation_threshold:
            if _stagnation_start.get(tid) is None:
                _stagnation_start[tid] = now
            else:
                stagnation_hours = (now - _stagnation_start[tid]).total_seconds() / 3600
                if stagnation_hours >= VOL_TIMEOUT_HOURS:
                    reason = f"volatility timeout: price stuck within ±{stagnation_threshold:.2f}% of entry for {stagnation_hours:.1f}h"
                    pnl = _close_paper_trade(pos["id"], px, reason)
                    _set_cooldown(sym)
                    closed_syms.add(sym)
                    _log_activity("CLOSED", sym, 0, px, pnl=pnl)
                    logger.info(f"[BOT] {sym} {reason} — closed")
                    continue
        else:
            _stagnation_start[tid] = None  # reset if price moves out of band

        # ── Time-based exit for stagnant positions: max hold time based on ATR ──
        max_hold_hours = MAX_HOLD_ATR_MULT * atr_pct  # e.g., 10 × ATR% hours
        if _entry_price_map.get(tid):
            _et = pos.get("entry_time")
            entry_time = datetime.fromisoformat(_et) if isinstance(_et, str) else (_et or now)
            hold_hours = (now - entry_time).total_seconds() / 3600
            if hold_hours >= max_hold_hours:
                reason = f"max hold time reached: {hold_hours:.1f}h ≥ {max_hold_hours:.1f}h (ATR×{MAX_HOLD_ATR_MULT})"
                pnl = _close_paper_trade(pos["id"], px, reason)
                _set_cooldown(sym)
                closed_syms.add(sym)
                _log_activity("CLOSED", sym, 0, px, pnl=pnl)
                logger.info(f"[BOT] {sym} {reason} — closed")
                continue

        # Structure-based exit — price broke below 4H EMA20 for EXIT_CYCLES consecutive checks (A6)
        # Replaces the calendar-based timing exit which fired on clock ticks, not price breaks.
        ema20 = _get_ema20_4h(sym)
        if ema20 is not None and px < ema20 * 0.99:   # 1% tolerance to avoid hair-trigger
            streak = _exit_streak.get(pos["id"], 0) + 1
            _exit_streak[pos["id"]] = streak
            if streak < EXIT_CYCLES:
                logger.debug(f"[BOT] {sym} below EMA20 ${ema20:.4g} — exit streak {streak}/{EXIT_CYCLES}")
                continue
            reason = f"trend break: ${px:.5g} < EMA20 ${ema20:.4g} ({EXIT_CYCLES} cycles)"
            pnl    = _close_paper_trade(pos["id"], px, reason)
            _set_cooldown(sym)
            closed_syms.add(sym)
            _exit_streak.pop(pos["id"], None)
            _log_activity("CLOSED", sym, 0, px, pnl=pnl)
        else:
            _exit_streak.pop(pos["id"], None)   # reset on price recovery

    # ── 2. Open new positions if slots are available ──────────────────────────
    fresh_positions = get_open_positions()
    bot_open_count  = sum(1 for p in fresh_positions if _is_bot_trade(p))
    slots_free      = MAX_POSITIONS - bot_open_count

    if slots_free <= 0:
        return

    # Gross exposure cap — per-trade risk sizing says nothing about portfolio size.
    # 10 slots × 20%-of-equity positions = up to 200% of equity deployed into a
    # correlated altcoin basket, with ~10% of equity at simultaneous risk. Cap the
    # total deployed notional so one market-wide flush cannot exceed the DD breakers.
    deployed = sum((p.get("size_usd") or POSITION_USD)
                   for p in fresh_positions if _is_bot_trade(p))
    if deployed >= EQUITY_USD * MAX_GROSS_FRAC:
        logger.info(f"[BOT] Gross exposure ${deployed:.0f} ≥ cap "
                    f"{MAX_GROSS_FRAC:.0%} of ${EQUITY_USD:.0f} — no new entries")
        return

    # BTC macro gate — already evaluated above; reuse result
    if BTC_TREND_GATE and not btc_ok_now:
        return

    # Altcoin-hostile macro gate: high BTC dominance + fear = alt longs bleed
    # even when BTC itself is above SMA50 (capital rotating out of alts).
    # Also extracts market_season for downstream Bitcoin Season tightening.
    # Fail-safe: any error skips this gate rather than blocking entries.
    effective_hotness_min = HOTNESS_MIN
    try:
        from spot.macro import get_latest_macro
        _m      = get_latest_macro() or {}
        _dom    = _m.get("btc_dominance")
        _fg     = _m.get("fear_greed_value")
        _season = _m.get("market_season", "")
        if _dom is not None and _fg is not None:
            if _dom > 56 and _fg < 35:
                logger.info(f"[BOT] Macro hostile (btc_dom={_dom:.1f} > 56, F&G={_fg} < 35) — blocking new entries")
                return
            # Knife-edge softener: the hard AND gate flips fully open the instant one
            # leg crosses back (dom 55.9 / F&G 34 => full-size entries at floor 11).
            # Keep a graduated middle band so the risk response is continuous.
            if _dom > 54 and _fg < 40:
                effective_hotness_min = HOTNESS_MIN + 1
                logger.info(f"[BOT] Macro semi-hostile (dom={_dom:.1f}, F&G={_fg}) — "
                            f"hotness floor raised to {effective_hotness_min}/20")
        # Bitcoin Season: capital rotating into BTC — only enter high-conviction alts
        if _season == "BITCOIN_SEASON":
            effective_hotness_min = 13
            logger.debug(f"[BOT] Bitcoin Season active — hotness floor raised to {effective_hotness_min}/20")
    except Exception:
        pass

    # Realized drawdown circuit breaker
    if not _drawdown_ok():
        return

    # Unrealized drawdown breaker — pause new entries if open book is too far underwater (A3)
    unreal = _unrealized_pnl(bot_trades, live_prices)
    if unreal <= -UNREALIZED_DD_LIMIT:
        logger.warning(f"[BOT] Unrealized drawdown ${unreal:.2f} ≤ -${UNREALIZED_DD_LIMIT:.0f} — pausing new entries")
        return

    # Atmosphere score — hoist computation BEFORE the loop; gate once, not per-coin (A7)
    atm_score = 50
    atm_boost = 1.0
    try:
        from spot.atmosphere import get_atmosphere
        atm       = get_atmosphere()
        atm_score = atm["score"]
        if _state.get("atmosphere_boost", True):
            atm_boost = min(atm["boost"], 1.10)  # cap boost at 1.10× (A7: avoid pro-cyclical over-sizing)
    except Exception:
        pass

    # HARD hostile floor — always enforced, independent of the operator toggle.
    # Below 40 the ecosystem is "hostile" (breadth, taker flow and ETH/BTC negative);
    # long-only alt entries there bleed even when the macro gate happens to pass.
    # Previously this was only a 0.50x size multiplier, which is not a risk control.
    if atm_score < ATM_HOSTILE_FLOOR:
        logger.info(f"[BOT] Atmosphere HOSTILE — {atm_score}/100 < {ATM_HOSTILE_FLOOR} — no new entries")
        return

    # Optional stricter operator gate (toggle) — neutral floor
    if _state.get("atmosphere_gate") and atm_score < ATM_MIN_ENTRY:
        logger.info(f"[BOT] Atmosphere gate BLOCKED — score {atm_score}/100 < {ATM_MIN_ENTRY}")
        return

    # Bitcoin Season release valve: if market breadth is locally favourable (≥65/100),
    # drop the tighter 13-point floor back to the standard 11. This handles pockets of
    # genuine strength (taker buy, volume, price breadth all recovering) within a broader
    # Bitcoin Season. Atmosphere < 65 keeps the stricter floor in place.
    if effective_hotness_min > HOTNESS_MIN and atm_score >= 65:
        # Release only on genuine BREADTH strength, not on a sentiment-driven score.
        # atm_score can hit 65 off F&G level/momentum + dominance accel while price and
        # taker breadth are still 3-4/10 — sentiment improving but alts not being bought.
        try:
            _comp = atm.get("components", {}) or {}
            _pb   = (_comp.get("price_breadth") or {}).get("score", 0)
            _tb   = (_comp.get("taker_breadth") or {}).get("score", 0)
        except Exception:
            _pb = _tb = 0
        if _pb >= 6 and _tb >= 6:
            effective_hotness_min = HOTNESS_MIN
            logger.debug(f"[BOT] Bitcoin Season floor RELEASED — atm {atm_score}/100, "
                         f"breadth price={_pb}/10 taker={_tb}/10")
        else:
            logger.debug(f"[BOT] Bitcoin Season floor HELD at {effective_hotness_min} — "
                         f"atm {atm_score}/100 but breadth price={_pb}/10 taker={_tb}/10")

    held_syms = {p["symbol"] for p in fresh_positions}

    # ── Candidate scoring — hotness is primary gate, timing is ranking tiebreaker (A1) ──
    candidates: list[tuple[int, int, str, dict, dict]] = []
    for coin in watchlist:
        sym = coin["symbol"]
        if sym in held_syms or sym in closed_syms or not _cooldown_ok(sym):
            continue

        px_now = (live_prices.get(sym) or {}).get("price")
        if not px_now:
            continue

        # 24h SMA trend filter — unchanged
        if not _trend_ok(sym, px_now):
            continue

        # CROSS-BOT GATE: defer XRP entries to the XRP Swing engine's verdict
        if not _xrp_swing_ok(sym):
            continue

        # PRIMARY GATE: hotness — technical/structural health (RSI, EMA200, volume, narrative)
        try:
            from spot.scorer import get_coin_detail
            hd = get_coin_detail(sym)
        except Exception:
            continue
        if hd is None or hd.get("score", 0) < effective_hotness_min:
            logger.debug(f"[BOT] {sym} hotness {(hd or {}).get('score', 0)}/20 < {effective_hotness_min} — skipped")
            continue
        hotness = hd["score"]

        # STRUCTURE CONFIRMATION: price above EMA20 on 4H (A1)
        if not _structure_ok(sym, px_now):
            continue

        # ENTRY ENHANCEMENT: Volume-confirmed breakout (vol_ratio ≥ 1.5)
        if not _volume_breakout_ok(sym):
            continue

        # ENTRY ENHANCEMENT: Multi-timeframe confirmation (1H + 4H alignment)
        if not _multi_tf_ok(sym, px_now):
            continue

        # NARRATIVE CONCENTRATION CAP (A8)
        if not _narrative_ok(coin.get("narrative"), held_syms, watchlist):
            logger.debug(f"[BOT] {sym} narrative cap hit ({coin.get('narrative')}: {MAX_PER_NARRATIVE} max)")
            continue

        # RISK MANAGEMENT: Correlation-adjusted position limits (cluster by narrative/sector)
        if not _correlation_cluster_ok(sym, held_syms, watchlist):
            logger.debug(f"[BOT] {sym} correlation cluster cap hit ({CORRELATION_CLUSTER_LIMIT} max per cluster)")
            continue

        # TIMING: soft floor only — block strongly bearish periods, otherwise just rank by it
        ts     = timing_score(sym)
        timing = ts.get("score") or 50
        if timing < TIMING_SOFT_MIN:
            logger.debug(f"[BOT] {sym} timing {timing}/100 < {TIMING_SOFT_MIN} (strongly bearish period) — skipped")
            continue

        # Rank by hotness first (primary), timing second (tiebreaker)
        candidates.append((hotness, timing, sym, ts, hd))

    candidates.sort(reverse=True)

    # ENTRY ENHANCEMENT: Graduated BTC regime gate — size multiplier based on distance above SMA50
    btc_size_mult = _btc_regime_size_multiplier()
    if btc_size_mult == 0.0:
        logger.info(f"[BOT] BTC regime at/below SMA50 — blocking all new entries")
        return

    # RISK MANAGEMENT: Portfolio-level circuit breaker
    if not _portfolio_dd_ok(bot_trades, live_prices):
        return

    for hotness, timing, sym, ts, hd in candidates[:slots_free]:
        px = (live_prices.get(sym) or {}).get("price")
        if not px:
            continue
        # Combine atmosphere boost with BTC regime size multiplier
        combined_boost = min(atm_boost * btc_size_mult, 1.10)
        _open_paper_trade(sym, px, hotness, ts.get("reasons", []), size_multiplier=combined_boost)
        _log_activity("OPENED", sym, hotness, px)


def fast_sl_cycle(positions: list[dict], live_prices: dict) -> list[tuple[str, str, float]]:
    """
    Called every 30 seconds — enforces hard SL and trailing stop only.
    No timing score logic (that stays in the 5-min run_cycle).
    Also updates trailing peaks as prices move up.

    Returns list of (symbol, human_reason, pnl_pct) for alert publishing by the caller.
    Idempotent: _close_paper_trade silently skips already-closed trades.
    """
    if not is_enabled():
        return []

    from spot.positions import update_trailing_peak, update_stop_loss
    from spot.streamer import is_connected, disconnected_since
    from datetime import datetime

    stream_ok = is_connected()
    if not stream_ok:
        since = disconnected_since()
        secs  = int((datetime.utcnow() - since).total_seconds()) if since else "?"
        logger.warning(f"[FAST-SL] Stream disconnected for ~{secs}s — checking hard SL on stale prices only")

    closed: list[tuple[str, str, float]] = []
    now = datetime.utcnow()

    for pos in positions:
        if not _is_bot_trade(pos):
            continue

        sym   = pos["symbol"]
        px    = (live_prices.get(sym) or {}).get("price")
        if not px:
            logger.debug(f"[FAST-SL] {sym} — no price in cache, skipping")
            continue

        entry    = pos["entry_price"]
        ts_pct   = pos.get("trailing_stop_pct")
        ts_peak  = pos.get("trailing_stop_peak") or entry
        gain_pct = (px - entry) / entry * 100
        tid      = pos["id"]

        # Get ATR% for this trade
        atr_pct = _atr_pct_map.get(tid) or _atr14(sym, entry)
        stop_dist_pct = atr_pct * ATR_STOP_K  # 1R = stop distance

        # ── Take profit — full close when spike hits target price ───────────
        target = pos.get("target")
        if target and px >= target:
            pnl = _close_paper_trade(pos["id"], px, f"take profit hit @ {px:.5g}")
            _set_cooldown(sym)
            _log_activity("CLOSED", sym, 0, px, pnl=pnl)
            closed.append((sym, f"take profit @ ${px:.4g}", pnl))
            logger.info(f"[FAST-SL] {sym} TP hit @ ${px:.5g}  P&L {pnl:+.2f}%")
            continue

        # ── TP1 partial close — dynamic 1R level (matches run_cycle), fire once ──
        sl0 = pos.get("stop_loss") or round(entry * (1 - STOP_LOSS_PCT / 100), 6)
        stop_dist_pct  = (entry - sl0) / entry * 100 if sl0 < entry else STOP_LOSS_PCT
        tp1_fired_pre  = pos.get("tp1_pnl_usd") is not None
        if target and not tp1_fired_pre and gain_pct >= stop_dist_pct:
            from spot.positions import apply_tp1
            apply_tp1(pos["id"], (pos.get("size_usd") or POSITION_USD) * TP1_SIZE_PCT, entry, tp1_price=px)
            _tp_stage[tid] = 1
            _trailing_armed[tid] = True
            _log_activity("TP1", sym, 0, px)
            logger.info(f"[FAST-SL] {sym} TP1 (1R) @ ${px:.5g} +{gain_pct:.2f}% — 30% locked, SL→BE, trailing armed at ATR×{ATR_TRAIL_K_TP1}")
            continue

        # ── Breakeven stop — only after TP1 has fired (A2: prevents scratching winners pre-TP1)
        sl        = pos.get("stop_loss")
        tp1_fired = pos.get("tp1_pnl_usd") is not None
        if stream_ok and _tp_stage.get(tid, 0) >= 1 and sl is not None and sl < entry:
            update_stop_loss(pos["id"], entry)
            sl = entry
            logger.info(f"[FAST-SL] {sym} breakeven stop engaged (post-TP1) — gain {gain_pct:.2f}%  SL → ${entry:.5g}")

        # ── TP2 at 2R (30% size) → tighten trail to ATR×0.5 ──
        if _tp_stage.get(tid, 0) == 1 and gain_pct >= TP2_R_MULT * stop_dist_pct:
            from spot.positions import apply_tp1, update_trailing_pct
            apply_tp1(pos["id"], (pos.get("size_usd") or POSITION_USD) * TP2_SIZE_PCT, entry, tp1_price=px)
            _tp_stage[tid] = 2
            new_trail_pct = max(atr_pct * ATR_TRAIL_K_TP2, 1.0)
            update_trailing_pct(pos["id"], new_trail_pct)
            ts_pct = new_trail_pct  # update local for trailing check below
            _log_activity("TP2", sym, 0, px)
            logger.info(f"[FAST-SL] {sym} TP2 (2R) @ ${px:.5g} +{gain_pct:.2f}% — 30% more locked, trail tightened to ATR×{ATR_TRAIL_K_TP2}")
            continue

        # ── TP3 at 3R (40% size) → trail at ATR×0.3 ──
        if _tp_stage.get(tid, 0) == 2 and gain_pct >= TP3_R_MULT * stop_dist_pct:
            from spot.positions import apply_tp1, update_trailing_pct
            apply_tp1(pos["id"], (pos.get("size_usd") or POSITION_USD) * TP3_SIZE_PCT, entry, tp1_price=px)
            _tp_stage[tid] = 3
            new_trail_pct = max(atr_pct * ATR_TRAIL_K_TP3, 0.8)
            update_trailing_pct(pos["id"], new_trail_pct)
            ts_pct = new_trail_pct  # update local for trailing check below
            _log_activity("TP3", sym, 0, px)
            logger.info(f"[FAST-SL] {sym} TP3 (3R) @ ${px:.5g} +{gain_pct:.2f}% — final 40% locked, trail tightened to ATR×{ATR_TRAIL_K_TP3}")
            continue

        # Only update trailing peak when stream is live — stale prices must not move the peak
        if stream_ok and ts_pct and px > ts_peak:
            update_trailing_peak(pos["id"], px)
            ts_peak = px

        # ── Hard stop-loss ────────────────────────────────────────────────────
        sl = pos.get("stop_loss")
        if sl and px <= sl:
            pnl = _close_paper_trade(pos["id"], px, f"fast SL hit @ {px:.5g}")
            _set_cooldown(sym)
            _log_activity("CLOSED", sym, 0, px, pnl=pnl)
            closed.append((sym, f"hard SL @ ${px:.4g}", pnl))
            logger.info(f"[FAST-SL] {sym} hard SL @ ${px:.5g}  P&L {pnl:+.2f}%")
            continue

        # ── ATR-based trailing from entry (armed when gain ≥ 1.5×ATR) ──
        # Arm trailing if not already armed and gain ≥ 1.5×ATR
        if not _trailing_armed.get(tid, False) and gain_pct >= ATR_TRAIL_ARM_K * stop_dist_pct:
            _trailing_armed[tid] = True
            logger.info(f"[FAST-SL] {sym} trailing ARMED — gain {gain_pct:.2f}% ≥ {ATR_TRAIL_ARM_K}×ATR ({ATR_TRAIL_ARM_K * stop_dist_pct:.2f}%)")

        # Trailing stop — fires once armed (after TP1 or at 1.5×ATR from entry)
        if ts_pct and stream_ok and _trailing_armed.get(tid, False):
            ts_level = ts_peak * (1 - ts_pct / 100)
            if ts_level > entry and px <= ts_level:
                pnl = _close_paper_trade(
                    pos["id"], px, f"fast trailing @ {px:.5g} (peak {ts_peak:.5g})"
                )
                _set_cooldown(sym)
                _log_activity("CLOSED", sym, 0, px, pnl=pnl)
                closed.append((sym, f"trailing stop @ ${px:.4g} (peak ${ts_peak:.4g})", pnl))
                logger.info(f"[FAST-SL] {sym} trailing @ ${px:.5g}  P&L {pnl:+.2f}%")

    return closed


def _log_activity(action: str, symbol: str, score: int, price: float, pnl: float | None = None) -> None:
    entry = {
        "ts":     datetime.utcnow().isoformat(),
        "action": action,
        "symbol": symbol,
        "score":  score,
        "price":  price,
    }
    if pnl is not None:
        entry["pnl"] = round(pnl, 2)
    _activity.insert(0, entry)
    if len(_activity) > 30:
        _activity.pop()


def seed_all_coins(watchlist: list[dict], live_prices: dict) -> dict:
    """
    Open a $POSITION_USD paper position on every active watchlist coin right now,
    skipping any that already have an open bot position.
    Returns {seeded: [syms], skipped: [syms], no_price: [syms]}.
    """
    from spot.positions import get_open_positions

    existing_bot_syms = {p["symbol"] for p in get_open_positions() if _is_bot_trade(p)}
    seeded, skipped, no_price = [], [], []

    for coin in watchlist:
        sym = coin["symbol"]
        if sym in existing_bot_syms:
            skipped.append(sym)
            continue
        px = (live_prices.get(sym) or {}).get("price")
        if not px:
            no_price.append(sym)
            continue
        _open_paper_trade(sym, px, score=0, reasons=["Test seed — all coins"])
        _log_activity("OPENED", sym, 0, px)
        seeded.append(sym)

    logger.info(f"[BOT] Seed complete — {len(seeded)} opened, {len(skipped)} already held, {len(no_price)} no price")
    return {"seeded": seeded, "skipped": skipped, "no_price": no_price}


def get_leaderboard(live_prices: dict | None = None) -> list[dict]:
    """
    Aggregate all bot paper trades by symbol.
    Returns list sorted by net P&L (realised + unrealised), best first.
    """
    from data.database import get_session
    from data.models import SpotTrade

    with get_session() as s:
        raw = (
            s.query(SpotTrade)
            .filter(SpotTrade.mode == "paper", SpotTrade.notes.like("[BOT]%"))
            .all()
        )
        # Extract all needed fields inside the session
        trades = [
            {
                "symbol":      t.symbol,
                "entry_price": t.entry_price,
                "exit_price":  t.exit_price,
                "size_usd":    t.size_usd,
            }
            for t in raw
        ]

    by_sym: dict[str, dict] = {}
    for t in trades:
        sym = t["symbol"]
        if sym not in by_sym:
            by_sym[sym] = {"closed": [], "open": []}
        if t["exit_price"] is not None:
            pnl_usd = (t["exit_price"] - t["entry_price"]) / t["entry_price"] * (t["size_usd"] or POSITION_USD)
            by_sym[sym]["closed"].append({
                "pnl_usd": pnl_usd,
                "win":     t["exit_price"] > t["entry_price"],
            })
        else:
            by_sym[sym]["open"].append(t)

    rows = []
    for sym, data in by_sym.items():
        closed   = data["closed"]
        open_pos = data["open"]

        realised = sum(c["pnl_usd"] for c in closed)
        wins     = sum(1 for c in closed if c["win"])

        unrealised = 0.0
        for t in open_pos:
            px  = (live_prices or {}).get(sym, {})
            cur = px.get("price", t["entry_price"]) if isinstance(px, dict) else t["entry_price"]
            unrealised += (cur - t["entry_price"]) / t["entry_price"] * (t["size_usd"] or POSITION_USD)

        rows.append({
            "symbol":        sym,
            "closed_trades": len(closed),
            "open_trades":   len(open_pos),
            "wins":          wins,
            "win_rate":      round(wins / len(closed) * 100) if closed else None,
            "realised_usd":  round(realised, 2),
            "unrealised_usd":round(unrealised, 2),
            "net_usd":       round(realised + unrealised, 2),
        })

    rows.sort(key=lambda r: r["net_usd"], reverse=True)
    return rows


def get_trade_history() -> list[dict]:
    """
    All completed bot paper trade cycles, newest first.
    Each dict includes parsed open/close scores, reasons, duration, and P&L.
    """
    import re

    from data.database import get_session
    from data.models import SpotTrade

    with get_session() as s:
        raw = (
            s.query(SpotTrade)
            .filter(
                SpotTrade.mode == "paper",
                SpotTrade.notes.like("[BOT]%"),
                SpotTrade.exit_price.isnot(None),
            )
            .order_by(SpotTrade.exit_time.desc())
            .all()
        )
        trades = [
            {
                "id":          t.id,
                "symbol":      t.symbol,
                "entry_price": t.entry_price,
                "exit_price":  t.exit_price,
                "size_usd":    t.size_usd,
                "entry_time":  t.entry_time.isoformat() if t.entry_time else None,
                "exit_time":   t.exit_time.isoformat() if t.exit_time else None,
                "notes":       t.notes or "",
            }
            for t in raw
        ]

    for t in trades:
        notes = t.pop("notes")
        ep, xp = t["entry_price"], t["exit_price"]
        # Net of round-trip fees so the review/feedback loop sees the same number the
        # P&L accounting recorded. Gross figures overstate edge by FEE_RT_PCT on every
        # trade — material when the average target move is only 1-3%.
        t["pnl_pct"] = round((xp - ep) / ep * 100 - FEE_RT_PCT, 2)
        t["pnl_usd"] = round(t["pnl_pct"] / 100 * (t["size_usd"] or POSITION_USD), 2)

        # Duration in minutes
        if t["entry_time"] and t["exit_time"]:
            from datetime import datetime as _dt
            dur = _dt.fromisoformat(t["exit_time"]) - _dt.fromisoformat(t["entry_time"])
            t["duration_min"] = int(dur.total_seconds() / 60)
        else:
            t["duration_min"] = None

        # Open score — matches both legacy '/100' and current '/20' note formats
        m = re.search(r'\[BOT\] Score (\d+)/\d+', notes)
        t["open_score"] = int(m.group(1)) if m else None

        # Open reasons — text between first "· " after score and the "|" separator
        m = re.search(r'\[BOT\] Score \d+/\d+ · (.+?)(?:\s*\||$)', notes)
        t["open_reasons"] = m.group(1).strip() if m else None

        # Close score + reason
        mc = re.search(r'Bot closed: (.+?)(?:\s*·\s*P&L|$)', notes)
        t["close_reason"] = mc.group(1).strip() if mc else None
        ms = re.search(r'Bot closed: score (\d+)/100', notes)
        t["close_score"] = int(ms.group(1)) if ms else None

    return trades


def get_status() -> dict:
    active_cooldowns = {
        sym: cd
        for sym, cd in _state.get("cooldowns", {}).items()
        if datetime.utcnow() < datetime.fromisoformat(cd)
    }
    btc = _btc_regime_cache
    return {
        "enabled":       is_enabled(),
        "config": {
            "hotness_min":           HOTNESS_MIN,
            "timing_soft_min":       TIMING_SOFT_MIN,
            "exit_cycles":           EXIT_CYCLES,
            # display-compat keys used by the frontend status strip
            "enter_at":              TIMING_SOFT_MIN,
            "exit_at":               TIMING_SOFT_MIN,
            "position_usd":          round(EQUITY_USD * MAX_POSITION_FRAC),
            "atr_stop_k":            ATR_STOP_K,
            "atr_trail_k":           ATR_TRAIL_K,
            "atr_tp_hard_k":         ATR_TP_HARD_K,
            "min_stop_pct":          MIN_STOP_PCT,
            "max_stop_pct":          MAX_STOP_PCT,
            "runner_size_ratio":     RUNNER_SIZE_RATIO,
            "equity_usd":            EQUITY_USD,
            "risk_pct_per_trade":    RISK_PCT_PER_TRADE,
            "fee_rt_pct":            FEE_RT_PCT,
            "max_positions":         MAX_POSITIONS,
            "max_per_narrative":     MAX_PER_NARRATIVE,
            "unrealized_dd_limit":   UNREALIZED_DD_LIMIT,
            "cooldown_min":          COOLDOWN_MINUTES,
            "btc_trend_gate":        BTC_TREND_GATE,
            "cb_in_paper_mode":      CB_IN_PAPER_MODE,
            "daily_loss_limit_usd":  DAILY_LOSS_LIMIT_USD,
            "weekly_loss_limit_usd": WEEKLY_LOSS_LIMIT_USD,
        },
        "btc_regime": {
            "bullish":       btc.get("ok"),
            "btc_price":     btc.get("price"),
            "sma50":         btc.get("sma50"),
            "sma50_updated": btc.get("sma50_at").isoformat() if btc.get("sma50_at") else None,
        } if btc else None,
        "drawdown": {
            "daily_pnl_usd":  round(_daily_pnl(), 2),
            "weekly_pnl_usd": round(_weekly_pnl(), 2),
            "daily_limit":    DAILY_LOSS_LIMIT_USD,
            "weekly_limit":   WEEKLY_LOSS_LIMIT_USD,
        },
        "atmosphere": get_atmosphere_settings(),
        "last_activity": _activity[:15],
        "cooldowns":     active_cooldowns,
    }
