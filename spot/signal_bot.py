"""
Phase 1 Signal Bot — timing-based trade recommendations (read-only, no orders placed).

For each held position: HOLD / MONITOR / EXIT / STRONG EXIT
For each unwatched watchlist coin: ENTER when timing is strong

Score 0–100: 50 = neutral, >65 = bullish, <35 = bearish
Weights:  hourly 40% · weekday 25% · week-of-month 20% · month-of-year 15%
"""
from __future__ import annotations

from datetime import datetime

_pattern_cache: dict[str, tuple[dict, int]] = {}   # {symbol: (patterns, utc_hour)}

_DAY_NAMES   = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
_MONTH_NAMES = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def _get_patterns(symbol: str) -> dict | None:
    hour = datetime.utcnow().hour
    cached = _pattern_cache.get(symbol)
    if cached and cached[1] == hour:
        return cached[0]
    try:
        from intelligence.spot_timing import timing_summary
        patterns = timing_summary(symbol)
        _pattern_cache[symbol] = (patterns, hour)
        return patterns
    except Exception:
        return None


def _norm(avg_return_pct: float, ref: float = 0.1) -> float:
    """Map avg_return_pct (%) to 0–100. ref = the ±% that maps to ±30 pts."""
    return min(100.0, max(0.0, 50.0 + (avg_return_pct / ref) * 30.0))


def timing_score(symbol: str) -> dict:
    """
    Composite timing score for the current UTC moment.
    Returns dict: score (int|None), reasons (list[str]), breakdown (dict), layers_used (int)
    """
    now      = datetime.utcnow()
    patterns = _get_patterns(symbol)
    if not patterns:
        return {'score': None, 'reasons': ['No pattern data'], 'layers_used': 0, 'breakdown': {}}

    layers: list[tuple[str, float, float]] = []   # (name, score_0_100, weight)
    reasons: list[str] = []

    # ── Hourly (40%) ──────────────────────────────────────────────────────────
    h = patterns['hourly'][now.hour]
    if h['sample_count'] >= 5:
        r  = h['avg_return_pct'] or 0.0
        s  = _norm(r, ref=0.10)
        layers.append(('hourly', s, 0.40))
        conf  = '' if h['reliable'] else '~'
        arrow = '↑' if r >= 0 else '↓'
        reasons.append(f"{conf}{now.hour:02d}:00 UTC {arrow} avg {r:+.3f}%")

    # ── Weekday (25%) ─────────────────────────────────────────────────────────
    wd = patterns['weekday'][now.weekday()]
    if wd['sample_count'] >= 5:
        r  = wd['avg_return_pct'] or 0.0
        s  = _norm(r, ref=0.10)
        layers.append(('weekday', s, 0.25))
        arrow = '↑' if r >= 0 else '↓'
        reasons.append(f"{_DAY_NAMES[now.weekday()]} {arrow} avg {r:+.3f}%")

    # ── Week of month (20%) ───────────────────────────────────────────────────
    # Require 80+ candles (~3–4 real calendar occurrences) before trusting this layer (A5)
    week = min(4, (now.day - 1) // 7 + 1)
    wom  = next((w for w in patterns['week_of_month'] if w['week'] == week), None)
    if wom and wom['sample_count'] >= 80:
        r  = wom['avg_return_pct'] or 0.0
        s  = _norm(r, ref=0.05)
        layers.append(('week_of_month', s, 0.20))
        arrow = '↑' if r >= 0 else '↓'
        reasons.append(f"Wk{week} {arrow} avg {r:+.3f}%")

    # ── Month of year (15%) ───────────────────────────────────────────────────
    # Require 200+ candles (~8 full occurrences) — 3-month window has only 3 instances (A5)
    moy = next((m for m in patterns['month_of_year'] if m['month'] == now.month), None)
    if moy and moy['sample_count'] >= 200:
        r  = moy['avg_return_pct'] or 0.0
        s  = _norm(r, ref=0.03)
        layers.append(('month_of_year', s, 0.15))
        arrow = '↑' if r >= 0 else '↓'
        reasons.append(f"{_MONTH_NAMES[now.month]} {arrow} avg {r:+.3f}%")

    if not layers:
        return {'score': None, 'reasons': ['Not enough data yet'], 'layers_used': 0, 'breakdown': {}}

    total_w   = sum(w for _, _, w in layers)
    composite = sum(s * w for _, s, w in layers) / total_w

    return {
        'score':       round(composite),
        'reasons':     reasons,
        'breakdown':   {name: round(s) for name, s, _ in layers},
        'layers_used': len(layers),
    }


def _classify(score: int, held: bool) -> tuple[str, str, str]:
    """Return (action, level, emoji) given score and whether coin is held."""
    if held:
        if score >= 65: return ('HOLD',        'info',     '🟢')
        if score >= 45: return ('MONITOR',     'warning',  '🟡')
        if score >= 30: return ('EXIT',        'warning',  '🔴')
        return                 ('STRONG EXIT', 'critical', '🚨')
    else:
        if score >= 60: return ('ENTER', 'info', '🟢')
        return (None, None, None)


def generate_signals(
    positions:       list[dict],
    watchlist_coins: list[dict],
    live_prices:     dict[str, float] | None = None,
) -> list[dict]:
    """
    Produce actionable signals for the current moment.
      positions       — from spot.positions.get_open_positions()
      watchlist_coins — active watchlist rows (symbol, pinned, held, …)
      live_prices     — optional {symbol: price} for display context
    """
    signals: list[dict] = []
    now          = datetime.utcnow().isoformat()
    held_symbols = {p['symbol'] for p in positions}

    # ── Held positions ────────────────────────────────────────────────────────
    for pos in positions:
        sym = pos['symbol']
        ts  = timing_score(sym)
        if ts['score'] is None:
            continue
        score              = ts['score']
        action, level, emo = _classify(score, held=True)
        px        = live_prices[sym]['price'] if live_prices and sym in live_prices else None
        price_str = f" @ ${px:,.4g}" if px else ''
        signals.append({
            'symbol':      sym,
            'action':      action,
            'score':       score,
            'level':       level,
            'held':        True,
            'message':     f"{emo} {sym}{price_str} — {action} · {score}/100 · {' · '.join(ts['reasons'])}",
            'reasons':     ts['reasons'],
            'breakdown':   ts.get('breakdown', {}),
            'layers_used': ts['layers_used'],
            'timestamp':   now,
            'source':      'signal_bot',
        })

    # ── Unwatched coins — entry opportunities ─────────────────────────────────
    for coin in watchlist_coins:
        sym = coin['symbol']
        if sym in held_symbols:
            continue
        ts  = timing_score(sym)
        if ts['score'] is None:
            continue
        score              = ts['score']
        action, level, emo = _classify(score, held=False)
        if not action:
            continue
        signals.append({
            'symbol':      sym,
            'action':      action,
            'score':       score,
            'level':       level,
            'held':        False,
            'message':     f"{emo} {sym} — {action} · {score}/100 · {' · '.join(ts['reasons'])}",
            'reasons':     ts['reasons'],
            'breakdown':   ts.get('breakdown', {}),
            'layers_used': ts['layers_used'],
            'timestamp':   now,
            'source':      'signal_bot',
        })

    # Urgency order: STRONG EXIT → EXIT → MONITOR → ENTER → HOLD
    _order = {'STRONG EXIT': 0, 'EXIT': 1, 'MONITOR': 2, 'ENTER': 3, 'HOLD': 4}
    signals.sort(key=lambda s: (
        _order.get(s['action'], 5),
        s['score'] if s['held'] else -s['score'],   # worst-first for held, best-first for entry
    ))
    return signals
