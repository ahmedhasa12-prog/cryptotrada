"""
Weekly parameter advisor — reads TradeReview table and generates plain-English
recommendations about whether bot parameters should be adjusted.

Three tiers of rules:
  Basic       — needs ≥10 reviews per category (SL tight/loose, trail tight, timing)
  Session     — needs ≥5 reviews per (category × session)  e.g. "SL premature in Asian session"
  Volume/flow — needs ≥8 reviews with taker data            e.g. "trail exits when buyers still active"

No parameter is ever changed automatically — only a recommendation text is generated.
The human reviews it and asks for the change explicitly.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from loguru import logger

from data.database import get_session
from data.models import SystemEvent, TradeReview

MIN_BASIC   = 10   # per category
MIN_SESSION = 5    # per (category, session)
MIN_VOLUME  = 8    # for volume-aware rules

DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# ── Data loader ───────────────────────────────────────────────────────────────

def _load() -> list[dict]:
    with get_session() as s:
        rows = s.query(TradeReview).all()
        return [
            {
                "trade_id":               r.trade_id,
                "symbol":                 r.symbol,
                "close_category":         r.close_category,
                "verdict":                r.verdict,
                "actual_pnl_pct":         r.actual_pnl_pct,
                "left_on_table_pct":      r.left_on_table_pct,
                "if_held_6h_pct":         r.if_held_6h_pct,
                "optimal_pnl_pct":        r.optimal_pnl_pct,
                "exit_session":           r.exit_session,
                "exit_hour_utc":          r.exit_hour_utc,
                "exit_day_of_week":       r.exit_day_of_week,
                "avg_taker_buy_ratio_6h": r.avg_taker_buy_ratio_6h,
                "avg_volume_6h":          r.avg_volume_6h,
                "entry_taker_ratio":      r.entry_taker_ratio,
                "btc_dom_at_exit":        r.btc_dom_at_exit,
                "fear_greed_at_exit":     r.fear_greed_at_exit,
                "candles_used":           r.candles_used,
                "atm_score_at_entry":     r.atm_score_at_entry,
                "btc_24h_pct_at_entry":   r.btc_24h_pct_at_entry,
                "btc_dom_at_entry":       r.btc_dom_at_entry,
            }
            for r in rows
        ]


# ── Stat helpers ──────────────────────────────────────────────────────────────

def _rate(rows: list[dict], verdict: str) -> float:
    return sum(1 for r in rows if r["verdict"] == verdict) / len(rows) if rows else 0.0


def _avg(rows: list[dict], field: str) -> float | None:
    vals = [r[field] for r in rows if r.get(field) is not None]
    return round(sum(vals) / len(vals), 2) if vals else None


def _by_session(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("exit_session"):
            out[r["exit_session"]].append(r)
    return out


# ── Rule engine ───────────────────────────────────────────────────────────────

def _sl_rules(sl_rows: list[dict]) -> list[dict]:
    recs = []
    n = len(sl_rows)
    if n < MIN_BASIC:
        return recs

    premature_rate = _rate(sl_rows, "premature_sl")
    correct_rate   = _rate(sl_rows, "correct_loss")
    avg_actual     = _avg(sl_rows, "actual_pnl_pct")
    avg_left       = _avg(sl_rows, "left_on_table_pct")

    if premature_rate > 0.30:
        recs.append({
            "priority": "high",
            "category": "sl",
            "finding":  (
                f"{premature_rate*100:.0f}% of SL exits are premature — price recovered "
                f"above entry after stop-out ({n} trades, avg loss {avg_actual:.2f}%)"
            ),
            "action":   "Consider widening STOP_LOSS_PCT from 3.0% → 3.5%",
            "data":     {"premature_rate": round(premature_rate, 3), "sample_count": n},
        })
    elif correct_rate > 0.70:
        recs.append({
            "priority": "info",
            "category": "sl",
            "finding":  (
                f"SL exits are working correctly — {correct_rate*100:.0f}% of stops "
                f"preceded continued declines ({n} trades, avg loss {avg_actual:.2f}%)"
            ),
            "action":   "No change needed to STOP_LOSS_PCT",
            "data":     {"correct_rate": round(correct_rate, 3), "sample_count": n},
        })

    # Session breakdown
    for sess, sess_rows in _by_session(sl_rows).items():
        if len(sess_rows) < MIN_SESSION:
            continue
        prem = _rate(sess_rows, "premature_sl")
        if prem > 0.40:
            recs.append({
                "priority": "medium",
                "category": "sl_session",
                "finding":  (
                    f"{prem*100:.0f}% of SL exits in the {sess.upper()} session are premature "
                    f"({len(sess_rows)} trades) — higher volatility absorbing the stop"
                ),
                "action":   (
                    f"Consider a session-aware SL: +0.5% wider during {sess} hours "
                    f"(e.g. 3.5% from 00–07 UTC for asian, 3.5% from 13–22 UTC for us)"
                ),
                "data":     {"session": sess, "premature_rate": round(prem, 3), "sample_count": len(sess_rows)},
            })

    return recs


def _trailing_rules(trail_rows: list[dict]) -> list[dict]:
    recs = []
    n = len(trail_rows)
    if n < MIN_BASIC:
        return recs

    early_rate   = _rate(trail_rows, "early_exit")
    correct_rate = _rate(trail_rows, "correct")
    avg_left     = _avg(trail_rows, "left_on_table_pct")
    avg_actual   = _avg(trail_rows, "actual_pnl_pct")

    if early_rate > 0.40 and avg_left and avg_left > 1.5:
        recs.append({
            "priority": "high",
            "category": "trailing",
            "finding":  (
                f"{early_rate*100:.0f}% of trailing exits leave money on the table — "
                f"avg {avg_left:.2f}% unrealised ({n} trades, avg actual P&L {avg_actual:.2f}%)"
            ),
            "action":   "Consider loosening TRAILING_STOP_PCT from 1.5% → 2.0%",
            "data":     {"early_rate": round(early_rate, 3), "avg_left_on_table": avg_left, "sample_count": n},
        })
    elif early_rate < 0.20:
        recs.append({
            "priority": "info",
            "category": "trailing",
            "finding":  (
                f"Trailing stops are locking in profits well — only {early_rate*100:.0f}% "
                f"early exits ({n} trades, avg P&L {avg_actual:.2f}%)"
            ),
            "action":   "No change needed to TRAILING_STOP_PCT",
            "data":     {"early_rate": round(early_rate, 3), "sample_count": n},
        })

    # Volume / taker flow rule
    with_taker = [r for r in trail_rows if r.get("avg_taker_buy_ratio_6h") is not None]
    if len(with_taker) >= MIN_VOLUME:
        early_with_buyers = [
            r for r in with_taker
            if r["verdict"] == "early_exit" and r["avg_taker_buy_ratio_6h"] > 0.55
        ]
        if len(early_with_buyers) >= 3:
            pct = len(early_with_buyers) / len(with_taker) * 100
            avg_ratio = _avg(early_with_buyers, "avg_taker_buy_ratio_6h")
            recs.append({
                "priority": "medium",
                "category": "trailing_flow",
                "finding":  (
                    f"{pct:.0f}% of trailing early-exits happened while taker-buy ratio was >55% "
                    f"(avg {avg_ratio:.2f}) — buyers were still pushing price up when we exited"
                ),
                "action":   (
                    "When avg_taker_buy_ratio > 0.55, consider holding 1 extra cycle before "
                    "triggering the trailing stop (add a flow-gate to fast_sl_cycle)"
                ),
                "data":     {
                    "early_with_buyers": len(early_with_buyers),
                    "total_with_taker":  len(with_taker),
                    "avg_taker_ratio":   avg_ratio,
                },
            })

    return recs


def _timing_rules(timing_rows: list[dict]) -> list[dict]:
    recs = []
    n = len(timing_rows)
    if n < MIN_BASIC:
        return recs

    early_rate   = _rate(timing_rows, "early_exit")
    avoided_rate = _rate(timing_rows, "avoided_loss")
    correct_rate = _rate(timing_rows, "correct")
    avg_left     = _avg(timing_rows, "left_on_table_pct")
    avg_actual   = _avg(timing_rows, "actual_pnl_pct")

    if early_rate > 0.40:
        recs.append({
            "priority": "high",
            "category": "timing",
            "finding":  (
                f"{early_rate*100:.0f}% of score-based exits are too early — "
                f"avg {avg_left:.2f}% left on table ({n} trades)"
            ),
            "action":   (
                "Consider raising EXIT_CYCLES from 2 → 3 (require 3 consecutive low-score "
                "checks before closing), or raising EXIT_THRESHOLD from 40 → 45"
            ),
            "data":     {"early_rate": round(early_rate, 3), "avg_left_on_table": avg_left, "sample_count": n},
        })
    elif avoided_rate > 0.50:
        recs.append({
            "priority": "info",
            "category": "timing",
            "finding":  (
                f"Timing exits are protecting capital — {avoided_rate*100:.0f}% avoided a "
                f"subsequent drop ({n} trades, avg P&L {avg_actual:.2f}%)"
            ),
            "action":   "No change needed to EXIT_CYCLES or EXIT_THRESHOLD",
            "data":     {"avoided_rate": round(avoided_rate, 3), "sample_count": n},
        })

    # Day-of-week pattern
    by_dow: dict[int, list] = defaultdict(list)
    for r in timing_rows:
        if r.get("exit_day_of_week") is not None:
            by_dow[r["exit_day_of_week"]].append(r)
    worst_dow = max(by_dow.items(), key=lambda kv: _rate(kv[1], "early_exit") * len(kv[1]), default=None)
    if worst_dow and len(worst_dow[1]) >= MIN_SESSION:
        dow_early = _rate(worst_dow[1], "early_exit")
        if dow_early > 0.50:
            recs.append({
                "priority": "medium",
                "category": "timing_dow",
                "finding":  (
                    f"{dow_early*100:.0f}% of timing exits on {DAY_NAMES[worst_dow[0]]} are too early "
                    f"({len(worst_dow[1])} trades) — scores may be systematically low on this day"
                ),
                "action":   (
                    f"Monitor whether low-volume {DAY_NAMES[worst_dow[0]]} sessions skew timing scores downward. "
                    "Consider a day-of-week multiplier in the scorer."
                ),
                "data":     {"day": DAY_NAMES[worst_dow[0]], "early_rate": round(dow_early, 3), "sample_count": len(worst_dow[1])},
            })

    return recs


def _macro_rules(all_rows: list[dict]) -> list[dict]:
    """Fear & Greed correlation: are losses clustering in fear zones?"""
    recs = []
    with_fg = [r for r in all_rows if r.get("fear_greed_at_exit") is not None]
    if len(with_fg) < MIN_BASIC:
        return recs

    fear_zone  = [r for r in with_fg if r["fear_greed_at_exit"] <= 30]
    greed_zone = [r for r in with_fg if r["fear_greed_at_exit"] >= 60]

    if len(fear_zone) >= MIN_SESSION:
        loss_in_fear = sum(1 for r in fear_zone if r["actual_pnl_pct"] < 0) / len(fear_zone)
        if loss_in_fear > 0.60:
            recs.append({
                "priority": "medium",
                "category": "macro_fear",
                "finding":  (
                    f"{loss_in_fear*100:.0f}% of trades exited during Fear & Greed ≤30 "
                    f"resulted in losses ({len(fear_zone)} trades)"
                ),
                "action":   (
                    "Consider tightening STOP_LOSS_PCT to 2.5% or reducing POSITION_USD "
                    "when Fear & Greed is below 30 (Extreme Fear)"
                ),
                "data":     {"fear_loss_rate": round(loss_in_fear, 3), "sample_count": len(fear_zone)},
            })

    if len(greed_zone) >= MIN_SESSION:
        avg_left_greed = _avg(greed_zone, "left_on_table_pct")
        early_in_greed = _rate(greed_zone, "early_exit")
        if early_in_greed > 0.40 and avg_left_greed and avg_left_greed > 2.0:
            recs.append({
                "priority": "medium",
                "category": "macro_greed",
                "finding":  (
                    f"{early_in_greed*100:.0f}% of exits during Greed (F&G ≥60) are too early "
                    f"— avg {avg_left_greed:.2f}% left on table ({len(greed_zone)} trades)"
                ),
                "action":   (
                    "During Greed / Extreme Greed, momentum favours holding. "
                    "Consider loosening trailing stop to 2.5% when Fear & Greed ≥60."
                ),
                "data":     {"greed_early_rate": round(early_in_greed, 3), "avg_left": avg_left_greed, "sample_count": len(greed_zone)},
            })

    return recs


def _macro_entry_rules(all_rows: list[dict]) -> list[dict]:
    """
    Correlate atmosphere score and BTC trend at entry time with trade outcomes.
    Activates once ≥10 reviews have atm_score_at_entry populated.
    """
    recs = []
    with_atm = [r for r in all_rows if r.get("atm_score_at_entry") is not None]
    if len(with_atm) < MIN_BASIC:
        return recs

    # ── Atmosphere condition at entry ─────────────────────────────────────────
    def _atm_label(score: int) -> str:
        if score >= 80: return "exceptional"
        if score >= 65: return "favourable"
        if score >= 40: return "neutral"
        return "hostile"

    by_condition: dict[str, list] = defaultdict(list)
    for r in with_atm:
        by_condition[_atm_label(r["atm_score_at_entry"])].append(r)

    # Win rate = correct + avoided_loss + correct_loss
    win_vs = {"correct", "avoided_loss", "correct_loss"}

    rates = {}
    for cond, rows in by_condition.items():
        if len(rows) >= 3:
            rates[cond] = (
                sum(1 for r in rows if r["verdict"] in win_vs) / len(rows),
                len(rows),
                _avg(rows, "actual_pnl_pct"),
            )

    if len(rates) >= 2:
        best_cond  = max(rates, key=lambda c: rates[c][0])
        worst_cond = min(rates, key=lambda c: rates[c][0])
        best_rate, best_n, best_pnl   = rates[best_cond]
        worst_rate, worst_n, worst_pnl = rates[worst_cond]

        if best_rate - worst_rate > 0.20:
            recs.append({
                "priority": "high",
                "category": "macro_entry_atm",
                "finding": (
                    f"Win rate differs sharply by atmosphere at entry — "
                    f"{best_cond}: {best_rate*100:.0f}% ({best_n} trades, avg {best_pnl:+.2f}%) vs "
                    f"{worst_cond}: {worst_rate*100:.0f}% ({worst_n} trades, avg {worst_pnl:+.2f}%)"
                ),
                "action": (
                    f"Enable the atmosphere gate to block entries in {worst_cond} conditions "
                    f"(score < {'40' if worst_cond == 'hostile' else '65'}). "
                    f"Gate toggle available at POST /api/spot/atmosphere/gate"
                ),
                "data": {c: {"win_rate": round(v[0], 3), "n": v[1], "avg_pnl": v[2]}
                         for c, v in rates.items()},
            })
        else:
            recs.append({
                "priority": "info",
                "category": "macro_entry_atm",
                "finding": (
                    f"Win rate is consistent across atmosphere conditions "
                    f"({', '.join(f'{c}: {v[0]*100:.0f}%' for c, v in rates.items())})"
                ),
                "action": "Atmosphere gate may not add significant alpha yet — keep monitoring",
                "data": {c: {"win_rate": round(v[0], 3), "n": v[1]} for c, v in rates.items()},
            })

    # ── BTC 24h trend at entry ────────────────────────────────────────────────
    with_btc = [r for r in with_atm if r.get("btc_24h_pct_at_entry") is not None]
    if len(with_btc) >= MIN_BASIC:
        bearish = [r for r in with_btc if r["btc_24h_pct_at_entry"] < -2]
        flat    = [r for r in with_btc if -2 <= r["btc_24h_pct_at_entry"] <= 2]
        bullish = [r for r in with_btc if r["btc_24h_pct_at_entry"] > 2]

        btc_rates = {}
        for label, subset in [("bearish_btc", bearish), ("flat_btc", flat), ("bullish_btc", bullish)]:
            if len(subset) >= 3:
                btc_rates[label] = (
                    sum(1 for r in subset if r["verdict"] in win_vs) / len(subset),
                    len(subset),
                    _avg(subset, "actual_pnl_pct"),
                )

        if len(btc_rates) >= 2:
            best_b  = max(btc_rates, key=lambda c: btc_rates[c][0])
            worst_b = min(btc_rates, key=lambda c: btc_rates[c][0])
            br, bn, bp = btc_rates[best_b]
            wr, wn, wp = btc_rates[worst_b]

            if br - wr > 0.20:
                recs.append({
                    "priority": "medium",
                    "category": "macro_entry_btc",
                    "finding": (
                        f"BTC 24h trend at entry correlates with outcome — "
                        f"{best_b.replace('_btc', '')}: {br*100:.0f}% win ({bn} trades, avg {bp:+.2f}%) vs "
                        f"{worst_b.replace('_btc', '')}: {wr*100:.0f}% win ({wn} trades, avg {wp:+.2f}%)"
                    ),
                    "action": (
                        "Avoid opening positions when BTC 24h return < −2% (bearish BTC drag). "
                        "This insight is already partially captured by btc_momentum in the atmosphere score."
                    ),
                    "data": {k: {"win_rate": round(v[0], 3), "n": v[1], "avg_pnl": v[2]}
                             for k, v in btc_rates.items()},
                })

    return recs


# ── Main advisory generator ───────────────────────────────────────────────────

def generate_advisory() -> dict:
    """Read all TradeReviews, apply rule tiers, return structured recommendations."""
    reviews = _load()

    meta = {
        "generated_at":  datetime.utcnow().isoformat(),
        "total_reviews": len(reviews),
    }

    if not reviews:
        return {
            **meta,
            "overall": {},
            "recommendations": [],
            "note": f"No review data yet — need ≥{MIN_BASIC} trades per category.",
        }

    by_cat: dict[str, list] = defaultdict(list)
    for r in reviews:
        by_cat[r["close_category"]].append(r)

    recs: list[dict] = []
    recs += _sl_rules(by_cat.get("sl", []))
    recs += _trailing_rules(by_cat.get("trailing", []))
    recs += _timing_rules(by_cat.get("timing", []))
    recs += _macro_rules(reviews)
    recs += _macro_entry_rules(reviews)

    # Data-pending notice for categories below threshold
    pending = []
    for cat in ("sl", "trailing", "timing"):
        n = len(by_cat.get(cat, []))
        if n < MIN_BASIC:
            pending.append(f"{cat}: {n}/{MIN_BASIC} trades")
    if pending:
        recs.append({
            "priority": "info",
            "category": "data_pending",
            "finding":  f"Categories still accumulating data: {', '.join(pending)}",
            "action":   f"Recommendations activate once ≥{MIN_BASIC} trades exist per category",
            "data":     {"pending": pending},
        })

    # Overall health
    win_verdicts = {"correct", "avoided_loss", "correct_loss"}
    bad_verdicts = {"early_exit", "premature_sl"}
    good_rate = sum(1 for r in reviews if r["verdict"] in win_verdicts) / len(reviews)
    bad_rate  = sum(1 for r in reviews if r["verdict"] in bad_verdicts) / len(reviews)

    verdict_counts: dict[str, int] = defaultdict(int)
    for r in reviews:
        verdict_counts[r["verdict"]] += 1

    overall = {
        "good_rate_pct":  round(good_rate * 100, 1),
        "bad_rate_pct":   round(bad_rate  * 100, 1),
        "avg_pnl":        _avg(reviews, "actual_pnl_pct"),
        "by_verdict":     dict(verdict_counts),
        "by_category":    {cat: len(rows) for cat, rows in by_cat.items()},
        "session_counts": dict(
            (sess, sum(1 for r in reviews if r.get("exit_session") == sess))
            for sess in ("asian", "london", "us", "off")
        ),
    }

    return {**meta, "overall": overall, "recommendations": recs}


def run_and_store() -> dict:
    """Generate advisory and persist as a SystemEvent for audit trail."""
    advisory = generate_advisory()
    if not advisory["total_reviews"]:
        return advisory

    lines = [f"[ADVISOR] {advisory['total_reviews']} trades | good={advisory['overall'].get('good_rate_pct')}% bad={advisory['overall'].get('bad_rate_pct')}%"]
    for r in advisory["recommendations"]:
        if r["category"] == "data_pending":
            continue
        lines.append(f"  [{r['priority'].upper()}] {r['category']}: {r['finding']}")
        lines.append(f"    → {r['action']}")

    body = "\n".join(lines)

    with get_session() as s:
        s.add(SystemEvent(
            event_type=  "param_advisory",
            description= body,
            mode=        "paper",
        ))

    logger.info(body)
    return advisory
