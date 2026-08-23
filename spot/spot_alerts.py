"""
Spot trading alert checks:
  1. Open position SL / target breach detection (runs every 5 min)
  2. Open position trailing stop — tracks peak price, fires on reversal
  3. Hotness rating transition detection (runs after each 4h recalculation)

Both return a list of (level_str, message) tuples for the alert bus.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from loguru import logger

from spot.positions import update_trailing_peak
from spot.streamer import is_connected as _stream_is_connected

# ── Position breach cooldown (avoid re-alerting every 5 min) ─────────────────

_position_alert_cooldown: dict[str, datetime] = {}
_COOLDOWN = timedelta(minutes=30)

# ── Rating history for transition detection ───────────────────────────────────

_prev_ratings: dict[str, str] = {}


# ── Position SL / target / trailing-stop breach ───────────────────────────────

def check_position_alerts(
    positions: list[dict],
    prices: dict,
) -> list[tuple[str, str]]:
    """
    Compare each open position's live price against its stop-loss, target,
    and trailing stop. Returns (level, message) pairs.
    """
    now = datetime.utcnow()
    alerts: list[tuple[str, str]] = []

    for pos in positions:
        sym        = pos["symbol"]
        live_data  = prices.get(sym) or prices.get(f"{sym}USDT")
        live_price = (live_data or {}).get("price")
        if not live_price:
            continue

        entry  = pos["entry_price"]
        sl     = pos["stop_loss"]
        target = pos["target"]
        pnl_pct = (live_price - entry) / entry * 100

        key_sl = f"{sym}_sl"
        key_tp = f"{sym}_tp"

        # ── Fixed stop-loss ───────────────────────────────────────────────────
        if sl and live_price <= sl:
            last = _position_alert_cooldown.get(key_sl, datetime.min)
            if now - last > _COOLDOWN:
                _position_alert_cooldown[key_sl] = now
                alerts.append((
                    "critical",
                    f"⚠️ {sym} hit stop-loss! "
                    f"Price ${live_price:.4f} ≤ SL ${sl:.4f} ({pnl_pct:+.1f}%) — consider closing."
                ))

        # ── Fixed take-profit target ──────────────────────────────────────────
        if target and live_price >= target:
            last = _position_alert_cooldown.get(key_tp, datetime.min)
            if now - last > _COOLDOWN:
                _position_alert_cooldown[key_tp] = now
                alerts.append((
                    "info",
                    f"🎯 {sym} reached take-profit target! "
                    f"Price ${live_price:.4f} ≥ TP ${target:.4f} ({pnl_pct:+.1f}%) — consider taking gains."
                ))

        # ── Trailing stop ─────────────────────────────────────────────────────
        ts_pct = pos.get("trailing_stop_pct")
        if ts_pct:
            peak = pos.get("trailing_stop_peak") or entry

            # Only update peak when stream is live — stale prices must not distort peak
            if live_price > peak and _stream_is_connected():
                update_trailing_peak(pos["id"], live_price)
                peak = live_price

            ts_level = peak * (1 - ts_pct / 100)

            # Natural floor: only fire once the trailing level is above entry
            # (prevents triggering on early dips before any real gain)
            if ts_level > entry and live_price <= ts_level:
                key_ts = f"{sym}_trailing"
                last = _position_alert_cooldown.get(key_ts, datetime.min)
                if now - last > _COOLDOWN:
                    _position_alert_cooldown[key_ts] = now
                    drop_pct = (live_price - peak) / peak * 100
                    alerts.append((
                        "critical",
                        f"🔄 {sym} trailing stop hit! "
                        f"Peak ${peak:.4f} → now ${live_price:.4f} ({drop_pct:.1f}%) — "
                        f"overall {pnl_pct:+.1f}%. Secure your profits!"
                    ))

    if alerts:
        logger.info(f"Position alerts: {len(alerts)} triggered")
    return alerts


# ── Rating transition detection ───────────────────────────────────────────────

def check_rating_transitions(new_scores: list[dict]) -> list[tuple[str, str]]:
    """
    Compare new hotness ratings against the previous run.
    Emits alerts for meaningful upgrades (cold/avoid → warm/very_hot)
    and downgrades (warm/very_hot → cold/avoid) on held watchlist coins.
    """
    global _prev_ratings
    alerts: list[tuple[str, str]] = []

    for coin in new_scores:
        sym     = coin["symbol"]
        new_key = coin.get("rating_key", "")
        old_key = _prev_ratings.get(sym)

        if old_key is not None and old_key != new_key:
            score = coin.get("score", 0)

            if new_key == "very_hot":
                alerts.append((
                    "warning",
                    f"🔥 {sym} just became a BUY SIGNAL — hotness {score}/20. "
                    f"Check the scanner now."
                ))
            elif new_key == "warm" and old_key in ("cold", "avoid"):
                alerts.append((
                    "info",
                    f"👀 {sym} is warming up — hotness {score}/20. "
                    f"Worth watching for an entry."
                ))
            elif old_key in ("warm", "very_hot") and new_key in ("cold", "avoid"):
                alerts.append((
                    "info",
                    f"📉 {sym} cooled down — now {coin.get('rating', new_key)} ({score}/20). "
                    f"Hold off on new entries."
                ))

        _prev_ratings[sym] = new_key

    if alerts:
        logger.info(f"Rating transition alerts: {len(alerts)}")
    return alerts
