"""
XRP Swing Trade Strategy Engine
================================
Evaluates 3-layer entry conditions every 4H and stores the verdict.
Manages staged paper entries, stop movement, and TP tracking.

Layer 1 — Macro Gate  (4 binary conditions — all must pass)
Layer 2 — XRP Setup   (which setup type is forming: A / B / C)
Layer 3 — Entry Trigger (volume + candle confirmation)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from loguru import logger
from sqlalchemy import text

from data.database import get_session
from data.models import MacroSnapshot, OhlcvCandle, XRPSwingSetup, XRPSwingTrade
from spot.streamer import get_prices

# ── Key levels ────────────────────────────────────────────────────────────────

XRP_SUPPORT    = [0.88, 0.95, 1.00]
XRP_RESISTANCE = [1.25, 1.50, 2.00, 3.00]

# Alert when price comes within this % of a key level
LEVEL_ALERT_PCT = 0.015   # 1.5%

# ── Phase 3 Enhancement Config ────────────────────────────────────────────────
# Entry Enhancements
XRP_ATR_PERIOD          = 14           # ATR period for 4H candles
XRP_TP_ATR_MULT         = [1.0, 2.0, 3.0]  # TP multipliers: TP1=1×ATR, TP2=2×ATR, TP3=3×ATR
XRP_CONVICTION_MULT     = {"A": 1.0, "B": 0.75, "C": 0.5}  # Setup conviction sizing
XRP_EARLY_ENTRY_PCT     = 0.20         # 20% at SETUP_FORMING
XRP_AUTO_STAGE_PCTS     = [0.20, 0.40, 0.40]  # Staged entry: 20%/40%/40%

# Exit Enhancements
XRP_TRAIL_ARM_ATR       = 1.5          # Arm trailing at 1.5×ATR gain from entry
XRP_TRAIL_ATR_BASE      = 1.0          # Base trail distance = ATR × 1.0
XRP_TRAIL_CHOP_MULT     = 1.5          # Chop regime: wider trail (ATR × 1.5)
XRP_TRAIL_TREND_MULT    = 0.5          # Trend regime: tighter trail (ATR × 0.5)

# Auto-Mode
XRP_COOLDOWN_BEAR_HOURS = 24           # Bear regime cooldown
XRP_COOLDOWN_BULL_HOURS = 6            # Bull regime cooldown

# ── Technical helpers ─────────────────────────────────────────────────────────

def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) < period + 2:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0
    return round(100 - 100 / (1 + ag / al), 2)


def _ema(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    k = 2 / (period + 1)
    val = sum(closes[:period]) / period
    for p in closes[period:]:
        val = p * k + val * (1 - k)
    return round(val, 6)


def _atr(candles: list[dict], period: int = 14) -> float | None:
    """Calculate ATR from candle data (list of dicts with high, low, close)."""
    if len(candles) < period + 1:
        return None
    trs = []
    for i in range(1, len(candles)):
        h = candles[i]["high"]
        l = candles[i]["low"]
        pc = candles[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def _load_xrp_candles(interval: str, limit: int) -> list[dict]:
    with get_session() as s:
        rows = (
            s.query(OhlcvCandle)
            .filter(OhlcvCandle.symbol == "XRP", OhlcvCandle.interval == interval)
            .order_by(OhlcvCandle.timestamp.desc())
            .limit(limit)
            .all()
        )
        result = [{"open": r.open, "high": r.high, "low": r.low,
                   "close": r.close, "volume": r.volume, "ts": r.timestamp}
                  for r in rows]
    result.reverse()
    return result


def _load_btc_candles(interval: str, limit: int) -> list[dict]:
    with get_session() as s:
        rows = (
            s.query(OhlcvCandle)
            .filter(OhlcvCandle.symbol == "BTC", OhlcvCandle.interval == interval)
            .order_by(OhlcvCandle.timestamp.desc())
            .limit(limit)
            .all()
        )
        result = [{"open": r.open, "high": r.high, "low": r.low,
                   "close": r.close, "volume": r.volume, "ts": r.timestamp}
                  for r in rows]
    result.reverse()
    return result


# ── Layer 1 — Macro Gate ──────────────────────────────────────────────────────

def _check_macro_gate() -> dict:
    """Returns status of all 4 macro gate conditions."""
    with get_session() as s:
        rows = (
            s.query(MacroSnapshot)
            .order_by(MacroSnapshot.id.desc())
            .limit(210)   # ~4.4 days of 30-min snapshots — guarantees 3-day look-back
            .all()
        )
        # Extract all attributes inside session to avoid detached-instance errors
        snaps_list = list(reversed([
            {"timestamp": r.timestamp, "btc_dominance": r.btc_dominance,
             "fear_greed_value": r.fear_greed_value}
            for r in rows
        ]))

    _stale_result = {k: None for k in
                     ["btc_sma50", "dom_falling", "fg_recovering", "btc_weekly_green",
                      "btc_dom", "fg_value", "dom_3d_change", "fg_3d_change"]}

    if not snaps_list:
        return {**_stale_result, "stale": True, "stale_reason": "no_snapshots"}

    latest = snaps_list[-1]
    age_minutes = (datetime.utcnow() - latest["timestamp"]).total_seconds() / 60
    if age_minutes > 120:
        logger.warning(f"XRP Swing: MacroSnapshot is {age_minutes:.0f} min old — skipping gate evaluation")
        return {**_stale_result, "stale": True, "stale_reason": f"data_{age_minutes:.0f}m_old",
                "btc_dom": latest["btc_dominance"], "fg_value": latest["fear_greed_value"]}

    btc_dom_now  = latest["btc_dominance"] or 0.0
    fg_now       = latest["fear_greed_value"] or 0

    # BTC.D 3-day trend: compare now vs 3 days ago
    cutoff_3d = datetime.utcnow() - timedelta(days=3)
    old_snaps  = [sn for sn in snaps_list if sn["timestamp"] and sn["timestamp"] <= cutoff_3d]
    dom_3d_ago = old_snaps[-1]["btc_dominance"] if old_snaps else btc_dom_now
    dom_3d_change = round(btc_dom_now - (dom_3d_ago or btc_dom_now), 3)
    # Loosened: < -0.15pp (was -0.3) OR dominance already low (≤ 54%)
    gate_dom_falling = dom_3d_change < -0.15 or btc_dom_now <= 54.0

    # F&G: pass on a real sentiment turn OR a bounce from extreme fear
    fg_3d_ago    = old_snaps[-1]["fear_greed_value"] if old_snaps else fg_now
    fg_3d_change = fg_now - (fg_3d_ago or fg_now)
    # Three ways to pass: a genuine sentiment turn (>=40 and rising), a bounce
    # from extreme fear (<=25 and ticking up), or — the previously DEAD 26-39 band — a strong
    # recovery out of fear. Without the middle clause an F&G of 27 could never satisfy
    # this gate however fast sentiment improved, permanently pinning the engine to
    # WATCHING through exactly the leg where the best swing entries occur.
    gate_fg_recovering = (
        (fg_now >= 40 and fg_3d_change >= 3)
        or (fg_now <= 25 and fg_3d_change >= 2)
        or (25 < fg_now < 40 and fg_3d_change >= 5)
    )

    # BTC SMA50 — use existing regime data via streamer prices + candles
    btc_candles = _load_btc_candles("1d", 55)
    btc_closes  = [c["close"] for c in btc_candles]
    btc_sma50   = sum(btc_closes[-50:]) / 50 if len(btc_closes) >= 50 else None
    btc_price   = btc_closes[-1] if btc_closes else None
    gate_btc_sma50 = bool(btc_price and btc_sma50 and btc_price > btc_sma50)

    # BTC weekly candle green — use CLOSED weekly candle ([-2]) not the in-progress one
    btc_weekly  = _load_btc_candles("1w", 3)
    gate_weekly = bool(len(btc_weekly) >= 2 and btc_weekly[-2]["close"] > btc_weekly[-2]["open"])

    return {
        "btc_sma50":         gate_btc_sma50,
        "dom_falling":       gate_dom_falling,
        "fg_recovering":     gate_fg_recovering,
        "btc_weekly_green":  gate_weekly,
        "btc_price":         btc_price,
        "btc_sma50_val":     btc_sma50,
        "btc_dom":           btc_dom_now,
        "fg_value":          fg_now,
        "dom_3d_change":     dom_3d_change,
        "fg_3d_change":      fg_3d_change,
        "fg_3d_ago":         fg_3d_ago,
        "dom_3d_ago":        dom_3d_ago,
    }


# ── Layer 2 — XRP Setup ───────────────────────────────────────────────────────

def _check_xrp_setup(xrp_price: float) -> dict:
    """Analyse XRP candles to determine which setup (A/B/C) is forming."""
    candles_4h = _load_xrp_candles("4h", 300)
    candles_1d = _load_xrp_candles("1d", 250)

    if len(candles_4h) < 50:
        return {"setup_type": None, "setup_desc": "Insufficient candle data", "error": True}

    closes_4h  = [c["close"]  for c in candles_4h]
    volumes_4h = [c["volume"] for c in candles_4h]
    closes_1d  = [c["close"]  for c in candles_1d]

    rsi_4h  = _rsi(closes_4h)
    rsi_1d  = _rsi(closes_1d) if len(closes_1d) >= 16 else None
    ema200  = _ema(closes_4h, 200)

    # ATR for dynamic targets and trailing
    atr_val = _atr(candles_4h, XRP_ATR_PERIOD)
    atr_pct = round(atr_val / xrp_price * 100, 2) if atr_val and xrp_price else None

    # Volume ratio vs 42-candle (7-day) average, excluding the current partial candle
    # vol_ratio      = display (current, partial candle — for the UI)
    # vol_ratio_closed = trigger use (last CLOSED candle — reliable)
    avg_vol_7d        = sum(volumes_4h[-44:-2]) / 42 if len(volumes_4h) >= 44 else sum(volumes_4h[:-2]) / max(len(volumes_4h) - 2, 1)
    vol_ratio         = round(volumes_4h[-1]  / avg_vol_7d, 2) if avg_vol_7d > 0 else 1.0
    vol_ratio_closed  = round(volumes_4h[-2]  / avg_vol_7d, 2) if avg_vol_7d > 0 else 1.0

    ema200_pct = None
    if ema200:
        ema200_pct = round((xrp_price - ema200) / ema200 * 100, 2)

    # Nearest support and resistance
    nearest_sup = max((s for s in XRP_SUPPORT if s < xrp_price), default=XRP_SUPPORT[0])
    nearest_res = min((r for r in XRP_RESISTANCE if r > xrp_price), default=XRP_RESISTANCE[-1])

    # Dynamic resistance targets based on ATR projections (capped by static resistance)
    dynamic_tp_levels = []
    if atr_val:
        for mult in XRP_TP_ATR_MULT:
            tp = round(xrp_price + atr_val * mult, 4)
            # Cap by nearest static resistance
            capped_tp = min(tp, nearest_res) if nearest_res else tp
            dynamic_tp_levels.append(capped_tp)

    # ── Setup A: EMA Reclaim ─────────────────────────────────────────────────
    setup_type = None
    setup_desc = "No setup yet — waiting for macro gate and technical alignment."

    if ema200 and ema200_pct is not None:
        above_ema = ema200_pct > 0
        near_ema  = abs(ema200_pct) < 5.0   # within 5% of EMA200
        if above_ema and near_ema and rsi_4h and 40 < rsi_4h < 68 and vol_ratio >= 1.3:
            setup_type = "A"
            setup_desc = (
                f"Setup A — EMA 200 Reclaim. Price ${xrp_price:.4f} is {ema200_pct:+.1f}% "
                f"above EMA200 (${ema200:.4f}). Volume {vol_ratio:.1f}x average. "
                f"RSI 4H: {rsi_4h:.0f}. Enter on first pullback to EMA."
            )

    # ── Setup B: Key Level Bounce ─────────────────────────────────────────────
    if setup_type is None and rsi_4h is not None:
        for sup in XRP_SUPPORT:
            dist_pct = abs(xrp_price - sup) / sup * 100
            if dist_pct < 4.0 and rsi_4h < 42:
                setup_type = "B"
                setup_desc = (
                    f"Setup B — Key Level Bounce at ${sup:.2f}. "
                    f"Price ${xrp_price:.4f} is {dist_pct:.1f}% from support. "
                    f"RSI 4H: {rsi_4h:.0f} (oversold). "
                    f"Stop: ${sup * 0.985:.4f} (below ${sup:.2f}). "
                    f"TP1: ${nearest_res:.2f}."
                )
                break

    # ── Setup C: Bollinger Squeeze → Breakout ─────────────────────────────────
    # Phase 1 (detect): BB width contracted vs recent history — volume optional
    # Phase 2 (trigger, in _check_entry_trigger): price ABOVE bb_upper + vol_ratio_closed >= 1.8
    bb_upper_c = None
    if setup_type is None and len(closes_4h) >= 20:
        recent = closes_4h[-20:]
        sma20  = sum(recent) / 20
        std20  = (sum((x - sma20) ** 2 for x in recent) / 20) ** 0.5
        bb_upper_c = round(sma20 + 2 * std20, 6)
        bb_lower_c = sma20 - 2 * std20
        bandwidth  = (bb_upper_c - bb_lower_c) / sma20 if sma20 else 1.0
        prev_bw_vals = closes_4h[-40:-20]
        if prev_bw_vals:
            prev_sma = sum(prev_bw_vals) / 20
            prev_std = (sum((x - prev_sma)**2 for x in prev_bw_vals) / 20) ** 0.5
            prev_bw  = (prev_sma + 2*prev_std - (prev_sma - 2*prev_std)) / prev_sma if prev_sma else 1.0
        else:
            prev_bw = 1.0
        # Squeeze: bands narrowed significantly vs prior period (vol_ratio < 0.8 is a bonus signal but not required)
        squeeze = bandwidth < 0.10 or (bandwidth < prev_bw * 0.65)
        if squeeze:
            setup_type = "C"
            setup_desc = (
                f"Setup C — Compression forming. Bollinger width {bandwidth:.3f} "
                f"(prev {prev_bw:.3f}). Volume {vol_ratio:.1f}x avg. "
                f"Trigger: breakout above ${bb_upper_c:.4f} with last closed candle volume ≥ 1.8x avg."
            )

    return {
        "setup_type":        setup_type,
        "setup_desc":        setup_desc,
        "rsi_4h":            rsi_4h,
        "rsi_1d":            rsi_1d,
        "ema200":            ema200,
        "ema200_pct":        ema200_pct,
        "vol_ratio":         vol_ratio,
        "vol_ratio_closed":  vol_ratio_closed,   # last closed 4H candle — used by trigger
        # Direction of the last CLOSED 4H candle — reversal confirmation for Setup B
        "last_closed_green": bool(len(candles_4h) >= 2 and
                                  candles_4h[-2]["close"] > candles_4h[-2]["open"]),
        "bb_upper":          bb_upper_c,          # Setup C: breakout level
        "nearest_sup":       nearest_sup,
        "nearest_res":       nearest_res,
        # Phase 3: Dynamic TP levels and ATR
        "atr_val":           atr_val,
        "atr_pct":           atr_pct,
        "dynamic_tp_levels": dynamic_tp_levels,
        # Phase 3: Conviction-based sizing
        "conviction_mult":   XRP_CONVICTION_MULT.get(setup_type, 1.0) if setup_type else 1.0,
    }


# ── Layer 3 — Entry Trigger ───────────────────────────────────────────────────

def _check_entry_trigger(setup: dict, xrp_price: float) -> dict:
    """Check if an actionable entry trigger has fired for the current setup.

    Uses vol_ratio_closed (last completed 4H candle) for all volume checks so
    partial-candle volume doesn't suppress triggers."""
    st = setup.get("setup_type")
    if st is None:
        return {"fired": False, "type": None, "desc": "No setup — no trigger possible."}

    rsi = setup.get("rsi_4h")
    vol = setup.get("vol_ratio_closed", setup.get("vol_ratio", 1.0))  # closed candle first

    if st == "A":
        # EMA pullback: strong volume on last closed candle + RSI in healthy range
        if vol >= 1.5 and rsi and 45 <= rsi <= 65:
            return {"fired": True, "type": "ema_pullback",
                    "desc": f"Closed candle volume {vol:.1f}x + RSI {rsi:.0f} — EMA pullback entry."}
    elif st == "B":
        # Oversold bounce: volume confirm + RSI oversold + the last CLOSED candle must
        # actually be green. Without the candle check this trigger fires into an
        # accelerating flush (heavy volume + low RSI is continuation as often as
        # reversal in a fear regime) — i.e. it catches the knife instead of the bounce.
        green = setup.get("last_closed_green", True)
        if vol >= 1.2 and rsi and rsi < 40 and green:
            return {"fired": True, "type": "oversold_bounce",
                    "desc": f"RSI {rsi:.0f} oversold + closed candle volume {vol:.1f}x + green close — reversal at support."}
        if vol >= 1.2 and rsi and rsi < 40 and not green:
            return {"fired": False, "type": None,
                    "desc": f"RSI {rsi:.0f} oversold on {vol:.1f}x volume but last closed 4H candle is red — waiting for absorption."}
    elif st == "C":
        # Breakout: closed candle volume surge AND live price above BB upper band
        bb_upper = setup.get("bb_upper")
        price_broke_out = bb_upper is not None and xrp_price > bb_upper
        if vol >= 1.8 and price_broke_out:
            return {"fired": True, "type": "compression_breakout",
                    "desc": f"Closed candle volume {vol:.1f}x + price ${xrp_price:.4f} above BB upper ${bb_upper:.4f} — breakout firing."}
        if vol >= 1.8 and not price_broke_out:
            return {"fired": False, "type": None,
                    "desc": f"Volume surge {vol:.1f}x confirmed but price ${xrp_price:.4f} still below BB upper ${bb_upper:.4f} — wait for close above."}

    return {"fired": False, "type": None,
            "desc": "Setup forming but trigger not confirmed yet — watch for volume + candle."}


# ── Master evaluate function ──────────────────────────────────────────────────

def evaluate_setup(store: bool = True) -> dict:
    """Run the full 3-layer evaluation and optionally persist to DB."""
    prices    = get_prices()
    xrp_data  = prices.get("XRP", {})
    xrp_price = xrp_data.get("price") if isinstance(xrp_data, dict) else None

    if xrp_price is None:
        logger.warning("XRP Swing: no live price — skipping evaluation")
        return {"error": "no_price"}

    macro  = _check_macro_gate()
    if macro.get("stale"):
        logger.warning(f"XRP Swing: stale macro data ({macro.get('stale_reason')}) — skipping evaluation")
        return {"error": "stale_macro", "stale_reason": macro.get("stale_reason"),
                "btc_dom": macro.get("btc_dom"), "fg_value": macro.get("fg_value")}

    setup  = _check_xrp_setup(xrp_price)
    trigger = _check_entry_trigger(setup, xrp_price)

    # Score (0-100)
    macro_gates = [
        macro.get("btc_sma50"), macro.get("dom_falling"),
        macro.get("fg_recovering"), macro.get("btc_weekly_green"),
    ]
    macro_score = sum(1 for g in macro_gates if g) * 15   # max 60

    tech_score = 0
    if setup.get("setup_type"):
        tech_score += 25
    if (setup.get("rsi_4h") or 50) < 45:
        tech_score += 10
    if trigger.get("fired"):
        tech_score += 15

    score = min(macro_score + tech_score, 100)

    # Active trade check
    active = get_active_trade()

    # Suppress Setup C when macro is hostile (high BTC.D + fear) — wrong thesis for regime
    gates_passing = sum(1 for g in macro_gates if g)
    macro_hostile = macro.get("btc_dom", 0) > 56 and macro.get("fg_value", 50) < 35
    effective_setup = setup.get("setup_type")
    if effective_setup == "C" and macro_hostile:
        effective_setup = None

    # Verdict
    if active:
        verdict = "IN_TRADE"
    # btc_sma50 is a MANDATORY gate, not one of four interchangeable ones: dom_falling
    # can pass on a -0.15pp drift and btc_weekly_green can be up to 7 days stale, so
    # 3-of-4 previously allowed an auto-opened swing long while BTC sat below its 50d
    # SMA. Failing it now degrades to SHADOW_ENTRY (discretionary watch) instead.
    elif trigger.get("fired") and gates_passing >= 3 and macro.get("btc_sma50"):
        verdict = "ENTRY_READY"
    elif trigger.get("fired") and effective_setup is not None:
        verdict = "SHADOW_ENTRY"   # technical trigger fired; macro gate blocking — user discretion
    elif effective_setup is not None and gates_passing >= 1:
        verdict = "SETUP_FORMING"
    else:
        verdict = "WATCHING"

    notes_parts = [setup.get("setup_desc", "")]
    if trigger.get("fired"):
        notes_parts.append(f"TRIGGER: {trigger['desc']}")
    notes = " | ".join(p for p in notes_parts if p)

    result = {
        "evaluated_at": datetime.utcnow().isoformat(),
        "verdict":      verdict,
        "score":        score,
        "macro":        macro,
        "setup":        setup,
        "trigger":      trigger,
        "xrp_price":    xrp_price,
        "active_trade": active,
        "key_levels": {
            "support":    XRP_SUPPORT,
            "resistance": XRP_RESISTANCE,
        },
    }

    if store:
        try:
            with get_session() as s:
                row = XRPSwingSetup(
                    gate_btc_sma50        = macro.get("btc_sma50"),
                    gate_dom_falling      = macro.get("dom_falling"),
                    gate_fg_recovering    = macro.get("fg_recovering"),
                    gate_btc_weekly_green = macro.get("btc_weekly_green"),
                    xrp_price             = xrp_price,
                    xrp_rsi_4h            = setup.get("rsi_4h"),
                    xrp_rsi_1d            = setup.get("rsi_1d"),
                    xrp_volume_ratio      = setup.get("vol_ratio"),
                    xrp_ema200            = setup.get("ema200"),
                    xrp_ema200_pct        = setup.get("ema200_pct"),
                    setup_type            = setup.get("setup_type"),
                    setup_desc            = setup.get("setup_desc"),
                    btc_price             = macro.get("btc_price"),
                    btc_dom               = macro.get("btc_dom"),
                    fg_value              = macro.get("fg_value"),
                    verdict               = verdict,
                    score                 = score,
                    notes                 = notes,
                )
                s.add(row)
        except Exception as e:
            logger.error(f"XRP Swing: failed to store setup — {e}")

    return result


def get_latest_setup() -> dict | None:
    """Return the most recently stored setup evaluation."""
    with get_session() as s:
        row = (
            s.query(XRPSwingSetup)
            .order_by(XRPSwingSetup.id.desc())
            .first()
        )
        if row is None:
            return None
        return {
            "id":            row.id,
            "evaluated_at":  row.evaluated_at.isoformat(),
            "verdict":       row.verdict,
            "score":         row.score,
            "gate_btc_sma50":       row.gate_btc_sma50,
            "gate_dom_falling":     row.gate_dom_falling,
            "gate_fg_recovering":   row.gate_fg_recovering,
            "gate_btc_weekly_green":row.gate_btc_weekly_green,
            "xrp_price":    row.xrp_price,
            "xrp_rsi_4h":   row.xrp_rsi_4h,
            "xrp_rsi_1d":   row.xrp_rsi_1d,
            "xrp_volume_ratio": row.xrp_volume_ratio,
            "xrp_ema200":   row.xrp_ema200,
            "xrp_ema200_pct": row.xrp_ema200_pct,
            "setup_type":   row.setup_type,
            "setup_desc":   row.setup_desc,
            "btc_price":    row.btc_price,
            "btc_dom":      row.btc_dom,
            "fg_value":     row.fg_value,
            "notes":        row.notes,
            "key_levels":   {"support": XRP_SUPPORT, "resistance": XRP_RESISTANCE},
        }


def get_setup_history(limit: int = 20) -> list[dict]:
    """Return the last N setup evaluations."""
    with get_session() as s:
        rows = (
            s.query(XRPSwingSetup)
            .order_by(XRPSwingSetup.id.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id":             r.id,
                "evaluated_at":   r.evaluated_at.isoformat(),
                "verdict":        r.verdict,
                "score":          r.score,
                "setup_type":     r.setup_type,
                "xrp_price":      r.xrp_price,
                "xrp_rsi_4h":     r.xrp_rsi_4h,
                "xrp_ema200_pct": r.xrp_ema200_pct,
                "btc_dom":        r.btc_dom,
                "fg_value":       r.fg_value,
            }
            for r in rows
        ]


# ── Trade management ──────────────────────────────────────────────────────────

def get_active_trade() -> dict | None:
    """Return the currently open XRP swing trade if any."""
    with get_session() as s:
        row = (
            s.query(XRPSwingTrade)
            .filter(XRPSwingTrade.status == "open")
            .order_by(XRPSwingTrade.id.desc())
            .first()
        )
        if row is None:
            return None
        return _trade_to_dict(row)


def _trade_to_dict(row: XRPSwingTrade) -> dict:
    stages = json.loads(row.stages_json) if row.stages_json else []
    prices = get_prices()
    live   = (prices.get("XRP") or {}).get("price")

    live_pnl_pct = None
    live_pnl_usd = None
    if live and row.avg_entry and row.total_size_usd:
        live_pnl_pct = round((live - row.avg_entry) / row.avg_entry * 100, 2)
        live_pnl_usd = round(row.total_size_usd * live_pnl_pct / 100, 2)

    return {
        "id":             row.id,
        "opened_at":      row.opened_at.isoformat(),
        "setup_type":     row.setup_type,
        "stages":         stages,
        "avg_entry":      row.avg_entry,
        "total_size_usd": row.total_size_usd,
        "stop_initial":   row.stop_initial,
        "stop_current":   row.stop_current,
        "tp1_price":      row.tp1_price,
        "tp2_price":      row.tp2_price,
        "stop_at_be":     row.stop_at_be,
        "trailing_active": row.trailing_active,
        "trailing_pct":   row.trailing_pct,
        "trailing_peak":  row.trailing_peak,
        "tp1_hit_at":     row.tp1_hit_at.isoformat() if row.tp1_hit_at else None,
        "tp1_pnl_usd":    row.tp1_pnl_usd,
        "tp2_hit_at":     row.tp2_hit_at.isoformat() if row.tp2_hit_at else None,
        "tp2_pnl_usd":    row.tp2_pnl_usd,
        "status":         row.status,
        "xrp_price_at_open": row.xrp_price_at_open,
        "btc_dom_at_open": row.btc_dom_at_open,
        "fg_at_open":     row.fg_at_open,
        "notes":          row.notes,
        "live_price":     live,
        "live_pnl_pct":   live_pnl_pct,
        "live_pnl_usd":   live_pnl_usd,
    }


def open_trade(setup_type: str, stage1_price: float, stage1_size_usd: float,
               stop: float, tp1: float, tp2: float, tp3: float = None,
               notes: str = "") -> dict:
    """Open a new XRP swing trade with stage 1 entry."""
    from spot.macro import get_latest_macro
    macro = get_latest_macro() or {}
    prices = get_prices()
    xrp_price = (prices.get("XRP") or {}).get("price")

    stage = {"price": stage1_price, "size_usd": stage1_size_usd,
             "time": datetime.utcnow().isoformat()}

    with get_session() as s:
        trade = XRPSwingTrade(
            setup_type       = setup_type,
            stages_json      = json.dumps([stage]),
            avg_entry        = stage1_price,
            total_size_usd   = stage1_size_usd,
            stop_initial     = stop,
            stop_current     = stop,
            tp1_price        = tp1,
            tp2_price        = tp2,
            tp3_price        = tp3,
            xrp_price_at_open= xrp_price,
            btc_dom_at_open  = macro.get("btc_dominance"),
            fg_at_open       = macro.get("fear_greed_value"),
            notes            = notes,
        )
        s.add(trade)
        s.flush()
        tid = trade.id
    logger.info(f"XRP Swing: trade #{tid} opened — Setup {setup_type} @ ${stage1_price}")
    return get_active_trade()


def add_stage(trade_id: int, price: float, size_usd: float) -> dict:
    """Add stage 2 or 3 entry to an open trade and recompute weighted average."""
    with get_session() as s:
        trade = s.query(XRPSwingTrade).filter_by(id=trade_id, status="open").first()
        if not trade:
            raise ValueError(f"No open trade with id={trade_id}")
        stages = json.loads(trade.stages_json) if trade.stages_json else []
        if len(stages) >= 3:
            raise ValueError("Already have 3 stages — no more entries allowed")
        stages.append({"price": price, "size_usd": size_usd,
                       "time": datetime.utcnow().isoformat()})
        total = sum(st["size_usd"] for st in stages)
        wavg  = sum(st["price"] * st["size_usd"] for st in stages) / total
        trade.stages_json    = json.dumps(stages)
        trade.avg_entry      = round(wavg, 6)
        trade.total_size_usd = round(total, 2)
    logger.info(f"XRP Swing: stage {len(stages)} added to trade #{trade_id} @ ${price}")
    return get_active_trade()


def hit_tp(trade_id: int, tp_num: int, close_price: float) -> dict:
    """Mark TP1, TP2, or TP3 as hit and record partial P&L. Moves stop to BE after TP1."""
    with get_session() as s:
        trade = s.query(XRPSwingTrade).filter_by(id=trade_id, status="open").first()
        if not trade:
            raise ValueError(f"No open trade #{trade_id}")
        if not trade.avg_entry or not trade.total_size_usd:
            raise ValueError("Trade has no entry price")

        # Proportion of position closed (30% at TP1, 30% at TP2, 40% at TP3)
        if tp_num == 1:
            fraction = 0.30
        elif tp_num == 2:
            fraction = 0.30
        elif tp_num == 3:
            fraction = 0.40
        else:
            raise ValueError(f"Invalid TP number: {tp_num}")

        pnl_pct   = (close_price - trade.avg_entry) / trade.avg_entry * 100
        pnl_usd   = round(trade.total_size_usd * fraction * pnl_pct / 100, 2)

        if tp_num == 1:
            trade.tp1_hit_at  = datetime.utcnow()
            trade.tp1_pnl_usd = pnl_usd
            # Move stop to breakeven after TP1
            trade.stop_current = trade.avg_entry
            trade.stop_at_be   = True
        elif tp_num == 2:
            trade.tp2_hit_at  = datetime.utcnow()
            trade.tp2_pnl_usd = pnl_usd
            # Tighten trailing after TP2
            trade.trailing_active = True
            trade.trailing_peak   = close_price
        elif tp_num == 3:
            trade.tp3_hit_at  = datetime.utcnow()
            trade.tp3_pnl_usd = pnl_usd
            # Final TP - tighten trailing to minimum
            trade.trailing_active = True
            trade.trailing_peak   = close_price

    logger.info(f"XRP Swing: TP{tp_num} hit on trade #{trade_id} @ ${close_price} — P&L ${pnl_usd:+.2f}")
    return get_active_trade()


def update_stop(trade_id: int, new_stop: float) -> dict:
    """Manually update the stop loss on an open trade."""
    with get_session() as s:
        trade = s.query(XRPSwingTrade).filter_by(id=trade_id, status="open").first()
        if not trade:
            raise ValueError(f"No open trade #{trade_id}")
        trade.stop_current = new_stop
    return get_active_trade()


def close_trade(trade_id: int, exit_price: float, reason: str = "manual") -> dict:
    """Close the full remaining position on a trade."""
    with get_session() as s:
        trade = s.query(XRPSwingTrade).filter_by(id=trade_id, status="open").first()
        if not trade:
            raise ValueError(f"No open trade #{trade_id}")

        pnl_pct = (exit_price - (trade.avg_entry or exit_price)) / (trade.avg_entry or exit_price) * 100
        # Remaining fraction: 60% if TP1 not hit, 35% if TP1 hit, 25% if both hit
        fraction = 1.0
        if trade.tp1_hit_at:
            fraction = 0.60
        if trade.tp2_hit_at:
            fraction = 0.25
        pnl_usd = round((trade.total_size_usd or 0) * fraction * pnl_pct / 100, 2)

        # Add any banked TP P&L
        banked = (trade.tp1_pnl_usd or 0.0) + (trade.tp2_pnl_usd or 0.0)
        total_pnl = round(pnl_usd + banked, 2)
        total_pct = round(total_pnl / (trade.total_size_usd or 1) * 100, 2)

        status_map = {"sl": "closed_sl", "tp": "closed_tp", "timeout": "closed_timeout"}
        trade.status        = status_map.get(reason, "closed_manual")
        trade.closed_at     = datetime.utcnow()
        trade.exit_price    = exit_price
        trade.final_pnl_usd = total_pnl
        trade.final_pnl_pct = total_pct

    logger.info(f"XRP Swing: trade #{trade_id} closed @ ${exit_price} — {reason} — P&L ${total_pnl:+.2f}")
    return _get_closed_trade(trade_id)


def _get_closed_trade(trade_id: int) -> dict:
    with get_session() as s:
        row = s.query(XRPSwingTrade).filter_by(id=trade_id).first()
        return _trade_to_dict(row) if row else {}


def get_trade_history(limit: int = 20) -> list[dict]:
    """Return recent closed trades."""
    with get_session() as s:
        rows = (
            s.query(XRPSwingTrade)
            .filter(XRPSwingTrade.status != "open")
            .order_by(XRPSwingTrade.id.desc())
            .limit(limit)
            .all()
        )
        return [_trade_to_dict(r) for r in rows]


# ── Key level alert checker ───────────────────────────────────────────────────

def check_level_alerts(xrp_price: float) -> list[str]:
    """Return alert messages if price is near any key level."""
    alerts = []
    for sup in XRP_SUPPORT:
        pct = abs(xrp_price - sup) / sup
        if pct <= LEVEL_ALERT_PCT:
            direction = "at" if pct < 0.005 else ("approaching" if xrp_price > sup else "just below")
            alerts.append(f"⚠️ XRP {direction} key support ${sup:.2f} (current: ${xrp_price:.4f})")
    for res in XRP_RESISTANCE:
        pct = abs(xrp_price - res) / res
        if pct <= LEVEL_ALERT_PCT:
            direction = "at" if pct < 0.005 else "approaching"
            alerts.append(f"⚠️ XRP {direction} key resistance ${res:.2f} (current: ${xrp_price:.4f})")
    return alerts


# ── Weekly review ─────────────────────────────────────────────────────────────

def generate_weekly_review() -> str:
    """Generate a Sunday morning text summary of XRP swing conditions."""
    result = evaluate_setup(store=False)
    if "error" in result:
        return "XRP Swing Weekly Review: no price data available."

    macro  = result["macro"]
    setup  = result["setup"]
    xrp_p  = result["xrp_price"]

    gate_count = sum(1 for k in ["btc_sma50","dom_falling","fg_recovering","btc_weekly_green"]
                     if macro.get(k))

    lines = [
        f"📊 XRP Swing Weekly Review — {datetime.utcnow().strftime('%Y-%m-%d')}",
        f"",
        f"VERDICT: {result['verdict']} (score {result['score']}/100)",
        f"",
        f"── Macro Gate ({gate_count}/4 conditions met) ──",
        f"{'✅' if macro.get('btc_sma50') else '❌'} BTC above SMA50: ${macro.get('btc_price', 0):,.0f} vs SMA50 ${macro.get('btc_sma50_val', 0):,.0f}",
        f"{'✅' if macro.get('dom_falling') else '❌'} BTC.D falling: {macro.get('btc_dom', 0):.2f}% (3d change {macro.get('dom_3d_change', 0):+.2f}pp)",
        f"{'✅' if macro.get('fg_recovering') else '❌'} F&G recovering: {macro.get('fg_value', 0)} (3d change {macro.get('fg_3d_change', 0):+.0f}pts)",
        f"{'✅' if macro.get('btc_weekly_green') else '❌'} BTC weekly candle: {'green' if macro.get('btc_weekly_green') else 'red/flat'}",
        f"",
        f"── XRP Technical ──",
        f"Price: ${xrp_p:.4f}",
        f"RSI 4H: {setup.get('rsi_4h', 'N/A')} | RSI 1D: {setup.get('rsi_1d', 'N/A')}",
        f"EMA 200: ${setup.get('ema200', 0):.4f} ({setup.get('ema200_pct', 0):+.1f}%)",
        f"Volume ratio: {setup.get('vol_ratio', 0):.1f}x",
        f"Setup: {setup.get('setup_type') or 'None forming'}",
        f"",
        f"── Assessment ──",
        f"{setup.get('setup_desc', '')}",
        f"",
        f"Key levels to watch — Support: ${', $'.join(str(s) for s in XRP_SUPPORT)} | Resistance: ${', $'.join(str(r) for r in XRP_RESISTANCE[:3])}",
    ]
    return "\n".join(lines)


# ── Auto-bot state ────────────────────────────────────────────────────────────

_AUTO_STATE_FILE = Path(__file__).parent.parent / "data" / "xrp_swing_auto.json"
_DEFAULT_SIZE_USD = 300.0


def _load_auto_state() -> dict:
    if _AUTO_STATE_FILE.exists():
        try:
            return json.loads(_AUTO_STATE_FILE.read_text())
        except Exception:
            pass
    return {
        "enabled":      False,
        "auto_size_usd": _DEFAULT_SIZE_USD,
        "last_check":   None,
        "last_action":  "Auto-trading not yet started",
    }


def _save_auto_state(state: dict) -> None:
    _AUTO_STATE_FILE.write_text(json.dumps(state, indent=2))


def get_auto_status() -> dict:
    """Full auto-bot status for the API — includes last stored verdict."""
    state   = _load_auto_state()
    setup   = get_latest_setup()
    active  = get_active_trade()
    return {
        **state,
        "verdict":        setup.get("verdict")     if setup else "WATCHING",
        "score":          setup.get("score")        if setup else 0,
        "setup_type":     setup.get("setup_type")   if setup else None,
        "has_active_trade": active is not None,
        "last_evaluated": setup.get("evaluated_at") if setup else None,
        "xrp_price":      setup.get("xrp_price")   if setup else None,
    }


def enable_auto(size_usd: float = _DEFAULT_SIZE_USD) -> dict:
    state = _load_auto_state()
    state["enabled"]       = True
    state["auto_size_usd"] = size_usd
    state["last_action"]   = "Auto-trading enabled"
    _save_auto_state(state)
    logger.info(f"XRP Swing AUTO: enabled (size ${size_usd:.0f})")
    return get_auto_status()


def disable_auto() -> dict:
    state = _load_auto_state()
    state["enabled"]     = False
    state["last_action"] = "Auto-trading disabled"
    _save_auto_state(state)
    logger.info("XRP Swing AUTO: disabled")
    return get_auto_status()


# ── Active trade monitoring: SL / TP / trailing ───────────────────────────────

def _monitor_trade(active: dict) -> list[str]:
    """Check live price against stop and TPs for an open trade. Returns list of actions taken."""
    from spot.streamer import get_prices as _gp
    prices   = _gp()
    xrp_data = prices.get("XRP") or {}
    live     = xrp_data.get("price") if isinstance(xrp_data, dict) else None
    if not live:
        return []

    trade_id = active["id"]
    actions: list[str] = []

    # Get ATR for this trade
    atr_val = active.get("atr_val")
    atr_pct = active.get("atr_pct")
    entry_price = active.get("avg_entry") or active.get("entry_price")
    
    # Determine regime for trailing (chop vs trend)
    # Simple heuristic: if price is near EMA200, it's chop; if far above, it's trend
    ema200 = active.get("ema200")
    regime = "chop"
    if ema200 and entry_price and entry_price > ema200 * 1.05:
        regime = "trend"
    
    # Trail multiplier based on regime
    if regime == "trend":
        trail_mult = XRP_TRAIL_TREND_MULT
    else:
        trail_mult = XRP_TRAIL_CHOP_MULT

    # ── Update trailing peak ──────────────────────────────────────────────────
    if active.get("trailing_active") and active.get("trailing_peak"):
        peak = active["trailing_peak"]
        if live > peak:
            with get_session() as s:
                row = s.query(XRPSwingTrade).filter_by(id=trade_id, status="open").first()
                if row:
                    row.trailing_peak = live
            actions.append(f"trail peak ↑ ${live:.4f}")
        else:
            # ATR-based trailing distance
            if atr_val:
                trail_dist_pct = (atr_val / peak * 100) * XRP_TRAIL_ATR_BASE * trail_mult
            else:
                trail_dist_pct = active.get("trailing_pct") or 2.5
            trail_stop = peak * (1 - trail_dist_pct / 100)
            if live <= trail_stop:
                close_trade(trade_id, live, reason="sl")
                actions.append(f"TRAIL STOP HIT @ ${live:.4f} (peak ${peak:.4f})")
                return actions  # trade is closed; stop further checks

    # ── Arm trailing from entry when gain ≥ 1.5×ATR ───────────────────────────
    if not active.get("trailing_active") and atr_val and entry_price:
        gain_pct = (live - entry_price) / entry_price * 100
        arm_threshold = XRP_TRAIL_ARM_ATR * atr_pct
        if gain_pct >= arm_threshold:
            with get_session() as s:
                row = s.query(XRPSwingTrade).filter_by(id=trade_id, status="open").first()
                if row:
                    row.trailing_active = True
                    row.trailing_peak = live
            actions.append(f"Trailing ARMED @ ${live:.4f} (gain {gain_pct:.1f}% ≥ {XRP_TRAIL_ARM_ATR}×ATR)")

    # ── Hard stop ────────────────────────────────────────────────────────────
    stop = active.get("stop_current") or 0.0
    if stop and live <= stop:
        close_trade(trade_id, live, reason="sl")
        actions.append(f"STOP LOSS HIT @ ${live:.4f}")
        return actions

    # ── TP1 ───────────────────────────────────────────────────────────────────
    if not active.get("tp1_hit_at") and active.get("tp1_price") and live >= active["tp1_price"]:
        hit_tp(trade_id, 1, live)
        actions.append(f"TP1 HIT @ ${live:.4f} → stop moved to BE")

    # ── TP2 ───────────────────────────────────────────────────────────────────
    if (active.get("tp1_hit_at") and not active.get("tp2_hit_at")
            and active.get("tp2_price") and live >= active["tp2_price"]):
        hit_tp(trade_id, 2, live)
        actions.append(f"TP2 HIT @ ${live:.4f} → trailing activated")

    # ── TP3 ───────────────────────────────────────────────────────────────────
    if (active.get("tp2_hit_at") and not active.get("tp3_hit_at")
            and active.get("tp3_price") and live >= active["tp3_price"]):
        hit_tp(trade_id, 3, live)
        actions.append(f"TP3 HIT @ ${live:.4f} → final target reached")

    return actions


# ── Auto-open parameters ──────────────────────────────────────────────────────

def _auto_params(setup: dict, xrp_price: float, size_usd: float) -> dict:
    """Compute entry, stop and TPs for an automated open.

    Per-setup stop placement:
      Setup A → 1% below EMA200 (dynamic trend level)
      Setup B/C → 1.5% below nearest key support (hard structural floor)
    Dynamic TPs: entry + ATR × N (capped by static resistance)
    R:R gate: reject entries where reward:risk < 1.5."""
    st  = setup.get("setup_type") or "B"
    sup = max((s for s in XRP_SUPPORT  if s < xrp_price), default=XRP_SUPPORT[0])
    res = min((r for r in XRP_RESISTANCE if r > xrp_price), default=XRP_RESISTANCE[-1])
    res2_candidates = [r for r in XRP_RESISTANCE if r > res]
    res2 = res2_candidates[0] if res2_candidates else round(res * 1.20, 2)

    # ATR-based stop and dynamic TPs
    atr_val = setup.get("atr_val")
    atr_pct = setup.get("atr_pct")
    dynamic_tp_levels = setup.get("dynamic_tp_levels", [])

    # Per-setup stop placement (ATR-based if available, else fallback)
    if atr_val:
        # Stop = entry - ATR × 1.5 (same as auto-trader)
        stop = round(xrp_price - atr_val * 1.5, 4)
        # Ensure stop is at least 1.5% below entry
        min_stop = round(xrp_price * 0.985, 4)
        stop = min(stop, min_stop)
    else:
        # Fallback to original logic
        if st == "A":
            ema200 = setup.get("ema200") or 0.0
            stop   = round(ema200 * 0.99, 4) if ema200 else round(sup * 0.985, 4)
        else:
            stop = round(sup * 0.985, 4)  # 1.5% below nearest support

    # Dynamic TPs from ATR projections (capped by static resistance)
    tp1 = dynamic_tp_levels[0] if len(dynamic_tp_levels) > 0 else res
    tp2 = dynamic_tp_levels[1] if len(dynamic_tp_levels) > 1 else res2
    tp3 = dynamic_tp_levels[2] if len(dynamic_tp_levels) > 2 else round(res * 1.5, 2)

    # R:R ratio (using TP1 as reward target)
    risk_pct   = (xrp_price - stop) / xrp_price if xrp_price > stop else 0.05
    reward_pct = (tp1 - xrp_price) / xrp_price if tp1 > xrp_price else 0
    rr_ratio   = round(reward_pct / risk_pct, 2) if risk_pct > 0 else 0.0

    return {
        "setup_type": st,
        "entry":      xrp_price,
        "size_usd":   size_usd,
        "stop":       stop,
        "tp1":        tp1,
        "tp2":        tp2,
        "tp3":        tp3,
        "rr_ratio":   rr_ratio,
        "rr_ok":      rr_ratio >= 1.5,  # gate: reject if R:R < 1.5
    }


# ── 30-second fast SL guard (XRP-specific) ───────────────────────────────────

def fast_sl_check() -> list[str]:
    """Runs every 30 s — enforces hard SL and trailing stop on open XRP swing trades
    without waiting for the 5-min cycle. Returns list of action strings."""
    active = get_active_trade()
    if not active:
        return []
    return _monitor_trade(active)


# ── Main auto cycle (runs every 5 min) ───────────────────────────────────────

_RISK_BUDGET_USD  = 20.0   # max capital at risk per trade (H3)
_COOLDOWN_HOURS   = 4      # lock-out after SL/trail close (C4)


def run_auto_cycle() -> dict:
    """
    5-minute cycle:
    1. Monitor any active trade for SL / TP hits and trailing stop updates.
    2. If auto-trading is enabled and the latest stored verdict is ENTRY_READY,
       no active trade is open, cooldown has expired, and R:R ≥ 1.5 → auto-open.
    """
    state   = _load_auto_state()
    actions: list[str] = []
    now     = datetime.utcnow()

    # ── 1. Monitor active trade (always, even when auto is OFF) ───────────────
    active = get_active_trade()
    if active:
        monitor_actions = _monitor_trade(active)
        actions.extend(monitor_actions)
        if monitor_actions:
            logger.info(f"XRP Swing MONITOR: {' | '.join(monitor_actions)}")
            # C4: start cooldown after any SL or trail-stop close
            if any("STOP LOSS" in a or "TRAIL STOP" in a for a in monitor_actions):
                state["cooldown_until"] = (now + timedelta(hours=_COOLDOWN_HOURS)).isoformat()
                logger.info(f"XRP Swing: {_COOLDOWN_HOURS}H cooldown started after SL/trail close")

    state["last_check"] = now.isoformat()

    if not state.get("enabled"):
        if actions:
            state["last_action"] = " | ".join(actions)
            _save_auto_state(state)
        return {"enabled": False, "actions": actions}

    # ── 2. Check if conditions are ready to auto-open ─────────────────────────
    # Refresh active after monitor (it may have just been closed)
    active = get_active_trade()
    if active:
        # ── Staged Auto-Entry: Add stages 2 & 3 when price moves favorably ─────
        auto_stage = state.get("auto_stage", 0)
        auto_total_size = state.get("auto_total_size", 0)
        auto_stage_sizes = state.get("auto_stage_sizes", XRP_AUTO_STAGE_PCTS)
        
        if auto_stage == 1 and auto_total_size > 0:
            # Check if we should add stage 2 (40%) - when price moves favorably by ~0.5×ATR
            atr_val = active.get("atr_val")
            entry_price = active.get("avg_entry")
            if atr_val and entry_price:
                gain_pct = (active.get("live_price", 0) - entry_price) / entry_price * 100
                atr_pct = active.get("atr_pct", 0)
                if gain_pct >= 0.5 * active.get("atr_pct", 1.0):
                    # Add stage 2: 40% of total size
                    stage2_size = round(auto_total_size * auto_stage_sizes[1], 2)
                    try:
                        add_stage(active["id"], active.get("live_price", 0), stage2_size)
                        actions.append(f"Auto Stage 2/3 added @ ${active.get('live_price', 0):.4f} (${stage2_size:.0f}, 40%)")
                        state["auto_stage"] = 2
                        logger.info(f"XRP Swing AUTO: Stage 2 added")
                    except Exception as exc:
                        logger.error(f"XRP Swing AUTO: Stage 2 failed: {exc}")
        
        elif auto_stage == 2 and auto_total_size > 0:
            # Check if we should add stage 3 (40%) - when price moves further favorably
            atr_val = active.get("atr_val")
            entry_price = active.get("avg_entry")
            if atr_val and entry_price:
                gain_pct = (active.get("live_price", 0) - entry_price) / entry_price * 100
                atr_pct = active.get("atr_pct", 0)
                if gain_pct >= 1.0 * active.get("atr_pct", 1.0):
                    # Add stage 3: 40% of total size
                    stage3_size = round(auto_total_size * auto_stage_sizes[2], 2)
                    try:
                        add_stage(active["id"], active.get("live_price", 0), stage3_size)
                        actions.append(f"Auto Stage 3/3 added @ ${active.get('live_price', 0):.4f} (${stage3_size:.0f}, 40%)")
                        state["auto_stage"] = 3
                        logger.info(f"XRP Swing AUTO: Stage 3 added")
                    except Exception as exc:
                        logger.error(f"XRP Swing AUTO: Stage 3 failed: {exc}")

        state["last_action"] = f"In trade #{active['id']} — monitoring SL/TP" + (
            f" | {' | '.join(actions)}" if actions else "")
        _save_auto_state(state)
        return {"enabled": True, "in_trade": True, "actions": actions}

    # C4: cooldown guard
    cooldown_until_str = state.get("cooldown_until")
    if cooldown_until_str:
        cooldown_until = datetime.fromisoformat(cooldown_until_str)
        if now < cooldown_until:
            remaining_h = (cooldown_until - now).total_seconds() / 3600
            state["last_action"] = f"Cooldown active — resumes in {remaining_h:.1f}h (after SL/trail close)"
            _save_auto_state(state)
            return {"enabled": True, "cooldown": True, "actions": actions}

    setup = get_latest_setup()
    if not setup:
        state["last_action"] = "No evaluation stored — waiting for 4H candle refresh"
        _save_auto_state(state)
        return {"enabled": True, "actions": actions}

    verdict = setup.get("verdict", "WATCHING")
    score   = setup.get("score", 0)
    eval_id = setup.get("id")

    # C4: setup-consumed guard — don't re-open on the same 4H evaluation
    if eval_id and eval_id == state.get("last_opened_eval_id"):
        state["last_action"] = f"{verdict} ({score}/100) — setup already consumed this bar"
        _save_auto_state(state)
        return {"enabled": True, "verdict": verdict, "score": score, "actions": actions}

    # Staleness guard: only act on evaluations from the last 5 hours
    eval_at = setup.get("evaluated_at")
    if eval_at:
        age_h = (now - datetime.fromisoformat(eval_at)).total_seconds() / 3600
        if age_h > 5:
            state["last_action"] = f"{verdict} ({score}/100) — evaluation stale ({age_h:.0f}h ago)"
            _save_auto_state(state)
            return {"enabled": True, "verdict": verdict, "actions": actions}

    if verdict != "ENTRY_READY":
        state["last_action"] = f"{verdict} ({score}/100) — waiting for ENTRY_READY"
        _save_auto_state(state)
        return {"enabled": True, "verdict": verdict, "score": score, "actions": actions}

    # ── ENTRY_READY — compute params and gate checks ──────────────────────────
    # Prefer live streamer price over stale evaluation price (H5 fix)
    from spot.streamer import get_prices as _gp
    _live = _gp().get("XRP") or {}
    xrp_price = (_live.get("price") if isinstance(_live, dict) else None) or setup.get("xrp_price")
    if not xrp_price:
        state["last_action"] = "ENTRY_READY but XRP price unavailable — skipped"
        _save_auto_state(state)
        return {"enabled": True, "verdict": verdict, "actions": actions}

    requested_size = state.get("auto_size_usd") or _DEFAULT_SIZE_USD
    params         = _auto_params(setup, xrp_price, requested_size)

    # H4: R:R gate — skip if reward:risk < 1.5
    if not params.get("rr_ok"):
        rr = params.get("rr_ratio", 0)
        state["last_action"] = (f"ENTRY_READY but R:R {rr:.2f} < 1.5 — "
                                f"stop ${params['stop']} vs TP1 ${params['tp1']} — skipped")
        _save_auto_state(state)
        return {"enabled": True, "verdict": verdict, "score": score, "actions": actions}

    # H3: Risk-based sizing — cap position so max loss ≤ RISK_BUDGET_USD
    stop_pct = (xrp_price - params["stop"]) / xrp_price if xrp_price > params["stop"] else 0.05
    max_size_by_risk = round(_RISK_BUDGET_USD / stop_pct, 2) if stop_pct > 0 else requested_size
    final_size = round(min(requested_size, max_size_by_risk), 2)
    params["size_usd"] = final_size

    # ── Staged Auto-Entry: 20% at SETUP_FORMING, 40% at ENTRY_READY, 40% at confirmation ─────
    # For now, we open with 20% at ENTRY_READY (first stage), then add stages in subsequent cycles
    # when the trade is already open and price moves favorably
    
    # First stage: 20% of final size
    stage1_size = round(final_size * XRP_AUTO_STAGE_PCTS[0], 2)
    
    try:
        open_trade(
            setup_type      = params["setup_type"],
            stage1_price    = params["entry"],
            stage1_size_usd = stage1_size,
            stop            = params["stop"],
            tp1             = params["tp1"],
            tp2             = params["tp2"],
            tp3             = params["tp3"],
            notes           = (f"Auto-opened Stage 1/3 (20%) | score={score} | R:R={params['rr_ratio']:.2f} | "
                               f"risk_cap=${max_size_by_risk:.0f} | "
                               f"{setup.get('setup_desc','')[:80]}"),
        )
        msg = (f"AUTO-OPENED Stage 1/3 Setup {params['setup_type']} @ ${xrp_price:.4f} | "
               f"stop ${params['stop']} | TP1 ${params['tp1']} | TP2 ${params['tp2']} | TP3 ${params['tp3']} | "
               f"R:R {params['rr_ratio']:.2f} | size ${stage1_size:.0f} (20%)")
        actions.append(msg)
        state["last_action"]         = msg
        state["last_opened_eval_id"] = eval_id   # C4: mark setup consumed
        state["auto_stage"]          = 1  # Track which stage we're at
        state["auto_total_size"]     = final_size
        state["auto_stage_sizes"]    = XRP_AUTO_STAGE_PCTS
        logger.info(f"XRP Swing AUTO: {msg}")
    except Exception as exc:
        err = f"Auto-open failed: {exc}"
        state["last_action"] = err
        logger.error(f"XRP Swing AUTO: {err}")

    _save_auto_state(state)
    return {"enabled": True, "verdict": verdict, "score": score, "actions": actions}
