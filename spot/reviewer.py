"""
Automated post-mortem reviewer — runs every 30 minutes.

For each closed bot trade that is at least 6 hours old and has no review yet:
  1. Pull 6 hourly candles after exit from DB (price + volume + taker flow)
  2. Pull the entry candle (volume + taker context at time of entry)
  3. Pull closest MacroSnapshot (BTC dominance, Fear & Greed)
  4. Classify exit session (asian / london / us / off) from exit_time UTC hour
  5. Compute: optimal exit, profit left on table, what price did after we sold
  6. Assign a verdict: correct | early_exit | avoided_loss | correct_loss | premature_sl
  7. Store an enriched TradeReview row

The table grows permanently — it is the raw material for the param advisor,
which runs weekly and generates recommendations based on accumulated patterns.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from loguru import logger

from data.database import get_session
from data.models import MacroSnapshot, OhlcvCandle, SpotTrade, TradeReview


# ── Session classifier (matches intelligence/spot_timing.py SESSIONS) ─────────

def _session(hour: int) -> str:
    if 0 <= hour < 7:   return "asian"
    if 7 <= hour < 13:  return "london"
    if 13 <= hour < 22: return "us"
    return "off"


# ── DB helpers ────────────────────────────────────────────────────────────────

def _classify_reason(notes: str) -> str:
    low = notes.lower()
    if "stop-loss" in low or "fast sl" in low:
        return "sl"
    if "trailing" in low:
        return "trailing"
    if "take profit" in low or "tp1" in low or "tp2" in low:
        return "tp"
    if "score" in low:
        return "timing"
    return "unknown"


def _extract_close_reason(notes: str) -> str:
    if "| Bot closed:" in notes:
        return notes.split("| Bot closed:")[1].strip()
    return notes[:200]


def _candles_after(symbol: str, exit_time: datetime, hours: int = 6) -> list[dict]:
    """Return up to `hours` hourly candles at or after exit_time, including volume."""
    with get_session() as s:
        rows = (
            s.query(OhlcvCandle)
             .filter(
                 OhlcvCandle.symbol   == symbol,
                 OhlcvCandle.interval == "1h",
                 OhlcvCandle.timestamp >= exit_time,
             )
             .order_by(OhlcvCandle.timestamp.asc())
             .limit(hours)
             .all()
        )
        return [
            {
                "high":           r.high,
                "low":            r.low,
                "close":          r.close,
                "volume":         r.volume,
                "taker_buy_base": r.taker_buy_base,
            }
            for r in rows
        ]


def _entry_candle(symbol: str, entry_time: datetime | None) -> dict:
    """Return volume + taker_ratio for the 1h candle at or just before entry_time."""
    if not entry_time:
        return {}
    with get_session() as s:
        row = (
            s.query(OhlcvCandle)
             .filter(
                 OhlcvCandle.symbol   == symbol,
                 OhlcvCandle.interval == "1h",
                 OhlcvCandle.timestamp <= entry_time,
             )
             .order_by(OhlcvCandle.timestamp.desc())
             .first()
        )
        if not row:
            return {}
        ratio = (row.taker_buy_base / row.volume) if row.volume else None
        return {"volume": row.volume, "taker_ratio": round(ratio, 4) if ratio is not None else None}


def _macro_at(exit_time: datetime) -> dict:
    """Return BTC dominance + Fear & Greed from the MacroSnapshot closest to exit_time."""
    window = timedelta(hours=4)
    with get_session() as s:
        rows = (
            s.query(MacroSnapshot)
             .filter(
                 MacroSnapshot.timestamp >= exit_time - window,
                 MacroSnapshot.timestamp <= exit_time + window,
             )
             .all()
        )
        if not rows:
            return {}
        closest = min(rows, key=lambda r: abs((r.timestamp - exit_time).total_seconds()))
        return {
            "btc_dom":    closest.btc_dominance,
            "fear_greed": closest.fear_greed_value,
        }


# ── Verdict logic ─────────────────────────────────────────────────────────────

def _verdict(
    category: str,
    actual_pnl: float,
    if_held_6h: float,
    optimal_pnl: float,
    worst_pnl: float,
) -> str:
    if category == "sl":
        if worst_pnl < actual_pnl - 0.3:
            return "correct_loss"
        if if_held_6h > 1.0:   # price must end >1% above entry 6h later for stop to be premature
            return "premature_sl"
        return "correct_loss"

    if category == "trailing":
        if optimal_pnl > actual_pnl + 1.0:
            return "early_exit"
        if if_held_6h < actual_pnl - 0.5:
            return "correct"
        return "correct"

    if category == "timing":
        if if_held_6h > actual_pnl + 0.8:
            return "early_exit"
        if if_held_6h < actual_pnl - 0.5:
            return "avoided_loss"
        return "correct"

    if category == "tp":
        if optimal_pnl > actual_pnl + 2.0:
            return "early_exit"   # significant upside was left on table
        if if_held_6h < 0:
            return "correct"      # price reversed — locking gains was right
        return "correct"

    return "correct"


# ── Core review function ───────────────────────────────────────────────────────

def _review_trade(td: dict) -> TradeReview:
    """Build an enriched TradeReview for one trade dict (detached from any DB session)."""
    import json
    notes      = td["notes"]
    category   = _classify_reason(notes)
    reason     = _extract_close_reason(notes)
    entry      = td["entry_price"]
    exit_px    = td["exit_price"]
    exit_time  = td["exit_time"]
    actual     = (exit_px - entry) / entry * 100

    # ── Macro context at entry ────────────────────────────────────────────────
    mctx: dict = {}
    try:
        raw = td.get("macro_context")
        if raw:
            mctx = json.loads(raw)
    except Exception:
        pass

    # ── Session / timing context ──────────────────────────────────────────────
    exit_hour = exit_time.hour if exit_time else None
    exit_dow  = exit_time.weekday() if exit_time else None
    sess      = _session(exit_hour) if exit_hour is not None else None

    # ── Post-exit candle data ─────────────────────────────────────────────────
    candles = _candles_after(td["symbol"], exit_time, hours=6)

    # ── Entry candle context ──────────────────────────────────────────────────
    ec = _entry_candle(td["symbol"], td.get("entry_time"))

    # ── Macro at exit ─────────────────────────────────────────────────────────
    macro = _macro_at(exit_time) if exit_time else {}

    if not candles:
        return TradeReview(
            trade_id              = td["id"],
            symbol                = td["symbol"],
            entry_price           = entry,
            exit_price            = exit_px,
            actual_pnl_pct        = round(actual, 3),
            close_category        = category,
            close_reason          = reason[:200],
            candles_used          = 0,
            verdict               = "no_data",
            exit_hour_utc         = exit_hour,
            exit_day_of_week      = exit_dow,
            exit_session          = sess,
            entry_volume          = ec.get("volume"),
            entry_taker_ratio     = ec.get("taker_ratio"),
            btc_dom_at_exit       = macro.get("btc_dom"),
            fear_greed_at_exit    = macro.get("fear_greed"),
            atm_score_at_entry    = mctx.get("atm_score"),
            btc_24h_pct_at_entry  = mctx.get("btc_24h_pct"),
            btc_dom_at_entry      = mctx.get("btc_dom"),
        )

    def pct(px: float) -> float:
        return (px - entry) / entry * 100

    highs    = [c["high"]  for c in candles]
    lows     = [c["low"]   for c in candles]
    closes   = [c["close"] for c in candles]
    max_high = max(highs)
    min_low  = min(lows)

    price_1h = closes[0] if len(closes) >= 1 else None
    price_3h = closes[2] if len(closes) >= 3 else closes[-1]
    price_6h = closes[5] if len(closes) >= 6 else closes[-1]

    optimal       = pct(max_high)
    worst         = pct(min_low)
    if_held_6h    = pct(price_6h)
    left_on_table = optimal - actual

    # ── Volume / taker context for post-exit window ───────────────────────────
    volumes = [c["volume"] for c in candles]
    avg_vol = round(sum(volumes) / len(volumes), 2) if volumes else None

    ratios = [
        c["taker_buy_base"] / c["volume"]
        for c in candles
        if c.get("volume", 0) > 0
    ]
    avg_taker = round(sum(ratios) / len(ratios), 4) if ratios else None

    v = _verdict(category, actual, if_held_6h, optimal, worst)

    return TradeReview(
        trade_id                = td["id"],
        symbol                  = td["symbol"],
        entry_price             = entry,
        exit_price              = exit_px,
        actual_pnl_pct          = round(actual, 3),
        close_category          = category,
        close_reason            = reason[:200],
        candles_used            = len(candles),
        price_1h_after          = round(price_1h, 6) if price_1h else None,
        price_3h_after          = round(price_3h, 6),
        price_6h_after          = round(price_6h, 6),
        max_high_6h             = round(max_high, 6),
        min_low_6h              = round(min_low, 6),
        optimal_pnl_pct         = round(optimal, 3),
        left_on_table_pct       = round(left_on_table, 3),
        if_held_6h_pct          = round(if_held_6h, 3),
        verdict                 = v,
        # Context fields
        exit_hour_utc           = exit_hour,
        exit_day_of_week        = exit_dow,
        exit_session            = sess,
        avg_volume_6h           = avg_vol,
        avg_taker_buy_ratio_6h  = avg_taker,
        entry_volume            = ec.get("volume"),
        entry_taker_ratio       = ec.get("taker_ratio"),
        btc_dom_at_exit         = macro.get("btc_dom"),
        fear_greed_at_exit      = macro.get("fear_greed"),
        atm_score_at_entry      = mctx.get("atm_score"),
        btc_24h_pct_at_entry    = mctx.get("btc_24h_pct"),
        btc_dom_at_entry        = mctx.get("btc_dom"),
    )


# ── Scheduled entry point ─────────────────────────────────────────────────────

def run_reviews() -> int:
    """
    Find all closed bot trades 6+ hours old with no review yet.
    Write an enriched TradeReview row for each. Returns count written.
    """
    cutoff = datetime.utcnow() - timedelta(hours=6)

    with get_session() as s:
        reviewed_ids = {r[0] for r in s.query(TradeReview.trade_id).all()}
        candidates = (
            s.query(SpotTrade)
             .filter(
                 SpotTrade.mode == "paper",
                 SpotTrade.notes.like("[BOT]%"),
                 SpotTrade.exit_price.isnot(None),
                 SpotTrade.exit_time < cutoff,
             )
             .all()
        )
        trade_dicts = [
            {
                "id":            t.id,
                "symbol":        t.symbol,
                "entry_price":   t.entry_price,
                "exit_price":    t.exit_price,
                "entry_time":    t.entry_time,
                "exit_time":     t.exit_time,
                "notes":         t.notes or "",
                "macro_context": t.macro_context,
            }
            for t in candidates
            if t.id not in reviewed_ids
        ]

    written = 0
    for td in trade_dicts:
        try:
            review = _review_trade(td)
            # Capture log fields before session closes (NullPool disconnects immediately)
            sym       = review.symbol
            category  = review.close_category
            verdict   = review.verdict
            lott      = review.left_on_table_pct
            sess_lbl  = review.exit_session
            taker     = review.avg_taker_buy_ratio_6h
            with get_session() as s:
                s.add(review)
            info = (
                f"verdict={verdict}"
                f" | left_on_table={lott:+.2f}%"
                f" | session={sess_lbl}"
                f" | taker_ratio={taker}"
                if lott is not None
                else f"verdict={verdict} | session={sess_lbl}"
            )
            logger.info(f"[REVIEW] {sym} id={td['id']} ({category}): {info}")
            written += 1
        except Exception as e:
            logger.error(f"[REVIEW] trade {td['id']} failed: {e}")

    if written:
        logger.info(f"[REVIEW] Wrote {written} new review(s)")
    return written


# ── Read API ──────────────────────────────────────────────────────────────────

def get_reviews() -> list[dict]:
    """All reviews, newest first."""
    with get_session() as s:
        rows = (
            s.query(TradeReview)
             .order_by(TradeReview.reviewed_at.desc())
             .all()
        )
        return [
            {
                "id":                      r.id,
                "trade_id":                r.trade_id,
                "reviewed_at":             r.reviewed_at.isoformat() if r.reviewed_at else None,
                "symbol":                  r.symbol,
                "entry_price":             r.entry_price,
                "exit_price":              r.exit_price,
                "actual_pnl_pct":          r.actual_pnl_pct,
                "close_category":          r.close_category,
                "close_reason":            r.close_reason,
                "candles_used":            r.candles_used,
                "price_1h_after":          r.price_1h_after,
                "price_3h_after":          r.price_3h_after,
                "price_6h_after":          r.price_6h_after,
                "max_high_6h":             r.max_high_6h,
                "min_low_6h":              r.min_low_6h,
                "optimal_pnl_pct":         r.optimal_pnl_pct,
                "left_on_table_pct":       r.left_on_table_pct,
                "if_held_6h_pct":          r.if_held_6h_pct,
                "verdict":                 r.verdict,
                # Context fields
                "exit_hour_utc":           r.exit_hour_utc,
                "exit_day_of_week":        r.exit_day_of_week,
                "exit_session":            r.exit_session,
                "avg_volume_6h":           r.avg_volume_6h,
                "avg_taker_buy_ratio_6h":  r.avg_taker_buy_ratio_6h,
                "entry_volume":            r.entry_volume,
                "entry_taker_ratio":       r.entry_taker_ratio,
                "btc_dom_at_exit":         r.btc_dom_at_exit,
                "fear_greed_at_exit":      r.fear_greed_at_exit,
            }
            for r in rows
        ]


def get_summary() -> dict:
    """
    Aggregate statistics across all reviews — the growing intelligence base.
    Returns per-category verdict breakdown and average metrics.
    """
    with get_session() as s:
        rows = [
            {
                "close_category":         r.close_category,
                "verdict":                r.verdict,
                "actual_pnl_pct":         r.actual_pnl_pct,
                "left_on_table_pct":      r.left_on_table_pct,
                "optimal_pnl_pct":        r.optimal_pnl_pct,
                "exit_session":           r.exit_session,
                "avg_taker_buy_ratio_6h": r.avg_taker_buy_ratio_6h,
            }
            for r in s.query(TradeReview).all()
        ]

    if not rows:
        return {"total": 0, "by_category": {}, "by_verdict": {}}

    by_cat: dict[str, list[dict]]  = {}
    by_verdict: dict[str, int]     = {}

    for r in rows:
        by_cat.setdefault(r["close_category"], []).append(r)
        by_verdict[r["verdict"]] = by_verdict.get(r["verdict"], 0) + 1

    cat_stats = {}
    for cat, cat_rows in by_cat.items():
        valid  = [r for r in cat_rows if r["left_on_table_pct"] is not None]
        verdicts: dict[str, int] = {}
        for r in cat_rows:
            verdicts[r["verdict"]] = verdicts.get(r["verdict"], 0) + 1

        # Session breakdown
        by_sess: dict[str, int] = {}
        for r in cat_rows:
            if r.get("exit_session"):
                by_sess[r["exit_session"]] = by_sess.get(r["exit_session"], 0) + 1

        cat_stats[cat] = {
            "count":             len(cat_rows),
            "verdicts":          verdicts,
            "avg_actual_pnl":    round(sum(r["actual_pnl_pct"] for r in cat_rows) / len(cat_rows), 2),
            "avg_left_on_table": round(sum(r["left_on_table_pct"] for r in valid) / len(valid), 2) if valid else None,
            "avg_optimal_pnl":   round(sum(r["optimal_pnl_pct"]  for r in valid) / len(valid), 2) if valid else None,
            "by_session":        by_sess,
        }

    return {
        "total":       len(rows),
        "by_category": cat_stats,
        "by_verdict":  by_verdict,
    }
