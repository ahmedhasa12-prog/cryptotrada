from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class P2PTrade(Base):
    __tablename__ = "p2p_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    trade_type: Mapped[str] = mapped_column(String(10), nullable=False)  # buy | sell
    amount_usdt: Mapped[float] = mapped_column(Float, nullable=False)
    rate_sdg: Mapped[float] = mapped_column(Float, nullable=False)
    total_sdg: Mapped[float] = mapped_column(Float, nullable=False)
    trader_username: Mapped[str] = mapped_column(String(100), nullable=False)
    trader_score: Mapped[int | None] = mapped_column(Integer)
    release_time_minutes: Mapped[float | None] = mapped_column(Float)
    profit_sdg: Mapped[float | None] = mapped_column(Float)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)  # manual | semi | full
    bank_used: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    binance_order_id: Mapped[str | None] = mapped_column(String(50), unique=True)


class SpotTrade(Base):
    __tablename__ = "spot_trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)   # paper | live
    direction: Mapped[str] = mapped_column(String(10), nullable=False)  # long
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Float)
    size_usd: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[float | None] = mapped_column(Float)
    target: Mapped[float | None] = mapped_column(Float)
    pnl_usd: Mapped[float | None] = mapped_column(Float)
    pnl_pct: Mapped[float | None] = mapped_column(Float)
    hotness_at_entry: Mapped[int | None] = mapped_column(Integer)
    strategy_used: Mapped[str | None] = mapped_column(String(50))
    outcome: Mapped[str | None] = mapped_column(String(20))  # win | loss | breakeven
    entry_time: Mapped[datetime | None] = mapped_column(DateTime)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)
    trailing_stop_pct:  Mapped[float | None] = mapped_column(Float)   # e.g. 2.5 means 2.5%
    trailing_stop_peak: Mapped[float | None] = mapped_column(Float)   # highest live price seen
    macro_context:      Mapped[str | None]   = mapped_column(Text)    # JSON snapshot at entry
    tp1_pnl_usd:        Mapped[float | None] = mapped_column(Float)   # P&L banked when TP1 partial fired


class Watchlist(Base):
    __tablename__ = "watchlist"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    narrative: Mapped[str | None] = mapped_column(String(100))
    is_narrative_leader: Mapped[bool] = mapped_column(Boolean, default=False)
    trade_type: Mapped[str] = mapped_column(String(20), nullable=False)  # long_term | short_term | both
    added_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    screen_score: Mapped[float | None] = mapped_column(Float)
    last_screened: Mapped[datetime | None] = mapped_column(DateTime)


class WatchlistScreenHistory(Base):
    """One row per coin per Stage-2 run — drives the consistency metric."""
    __tablename__ = "watchlist_screen_history"

    id:              Mapped[int]   = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_date:        Mapped[datetime] = mapped_column(DateTime, nullable=False)
    symbol:          Mapped[str]   = mapped_column(String(20), nullable=False)
    rank:            Mapped[int]   = mapped_column(Integer, nullable=False)
    composite_score: Mapped[float] = mapped_column(Float, nullable=False)


class HotnessScore(Base):
    __tablename__ = "hotness_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    rating: Mapped[str] = mapped_column(String(30), nullable=False)
    breakdown_json: Mapped[str | None] = mapped_column(Text)
    btc_dominance: Mapped[float | None] = mapped_column(Float)
    fear_greed: Mapped[int | None] = mapped_column(Integer)


class PriceLevel(Base):
    __tablename__ = "price_levels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    level_type: Mapped[str] = mapped_column(String(20), nullable=False)  # support | resistance
    price: Mapped[float] = mapped_column(Float, nullable=False)
    touches: Mapped[int] = mapped_column(Integer, default=1)
    first_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_touched: Mapped[datetime | None] = mapped_column(DateTime)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class OhlcvCandle(Base):
    __tablename__ = "ohlcv_candles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    interval: Mapped[str] = mapped_column(String(5), nullable=False)   # 1d | 4h | 1h | 15m
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    taker_buy_base: Mapped[float] = mapped_column(Float, nullable=False)


class MacroSnapshot(Base):
    __tablename__ = "macro_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    btc_dominance: Mapped[float | None] = mapped_column(Float)
    btc_dominance_7d_change: Mapped[float | None] = mapped_column(Float)
    market_season: Mapped[str | None] = mapped_column(String(40))
    fear_greed_value: Mapped[int | None] = mapped_column(Integer)
    fear_greed_label: Mapped[str | None] = mapped_column(String(30))
    fear_greed_yesterday: Mapped[int | None] = mapped_column(Integer)
    fear_greed_last_week: Mapped[int | None] = mapped_column(Integer)
    total_market_cap_usd: Mapped[float | None] = mapped_column(Float)


class SpotAlertLog(Base):
    __tablename__ = "spot_alert_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    alert_type: Mapped[str] = mapped_column(String(50), nullable=False)
    symbol: Mapped[str | None] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    acted_upon: Mapped[bool] = mapped_column(Boolean, default=False)
    outcome: Mapped[str | None] = mapped_column(Text)


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    buy_best_rate: Mapped[float | None] = mapped_column(Float)
    sell_best_rate: Mapped[float | None] = mapped_column(Float)
    spread: Mapped[float | None] = mapped_column(Float)
    our_rate: Mapped[float | None] = mapped_column(Float)
    competitors_json: Mapped[str | None] = mapped_column(Text)


class TraderHistory(Base):
    __tablename__ = "trader_history"

    username: Mapped[str] = mapped_column(String(100), primary_key=True)
    first_trade: Mapped[datetime | None] = mapped_column(DateTime)
    last_trade: Mapped[datetime | None] = mapped_column(DateTime)
    total_trades: Mapped[int] = mapped_column(Integer, default=0)
    successful: Mapped[int] = mapped_column(Integer, default=0)
    disputed: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    flagged: Mapped[bool] = mapped_column(Boolean, default=False)


class SystemEvent(Base):
    __tablename__ = "system_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str | None] = mapped_column(String(20))


class TradeReview(Base):
    """
    Automated post-mortem record for each closed bot trade.
    Written ~6h after close once enough candles have accumulated.
    Grows permanently — the foundation for parameter tuning over time.
    """
    __tablename__ = "trade_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)

    # Trade facts (denormalised for easy querying without joining spot_trades)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float] = mapped_column(Float, nullable=False)
    actual_pnl_pct: Mapped[float] = mapped_column(Float, nullable=False)
    close_category: Mapped[str] = mapped_column(String(20), nullable=False)  # sl | trailing | timing
    close_reason: Mapped[str | None] = mapped_column(String(200))

    # What the market did in the 6 hours after exit
    candles_used: Mapped[int] = mapped_column(Integer, default=0)
    price_1h_after: Mapped[float | None] = mapped_column(Float)
    price_3h_after: Mapped[float | None] = mapped_column(Float)
    price_6h_after: Mapped[float | None] = mapped_column(Float)
    max_high_6h: Mapped[float | None] = mapped_column(Float)   # best price achievable if held
    min_low_6h: Mapped[float | None] = mapped_column(Float)    # worst price if held

    # Derived metrics
    optimal_pnl_pct: Mapped[float | None] = mapped_column(Float)    # (max_high − entry) / entry %
    left_on_table_pct: Mapped[float | None] = mapped_column(Float)  # optimal − actual (+ = exited early)
    if_held_6h_pct: Mapped[float | None] = mapped_column(Float)     # P&L if position held to 6h mark

    # Verdict
    verdict: Mapped[str] = mapped_column(String(30), nullable=False)
    # correct | early_exit | avoided_loss | correct_loss | premature_sl | no_data

    # ── Context at exit time ───────────────────────────────────────────────────
    exit_hour_utc:    Mapped[int | None] = mapped_column(Integer)          # 0–23
    exit_day_of_week: Mapped[int | None] = mapped_column(Integer)          # 0=Mon … 6=Sun
    exit_session:     Mapped[str | None] = mapped_column(String(10))       # asian|london|us|off

    # ── Volume context — 6h candles after exit ────────────────────────────────
    avg_volume_6h:          Mapped[float | None] = mapped_column(Float)    # avg hourly volume
    avg_taker_buy_ratio_6h: Mapped[float | None] = mapped_column(Float)    # taker_buy_base/volume (>0.5 = buyers dominant)

    # ── Entry candle context ──────────────────────────────────────────────────
    entry_volume:      Mapped[float | None] = mapped_column(Float)
    entry_taker_ratio: Mapped[float | None] = mapped_column(Float)

    # ── Macro at exit ─────────────────────────────────────────────────────────
    btc_dom_at_exit:    Mapped[float | None] = mapped_column(Float)
    fear_greed_at_exit: Mapped[int | None]   = mapped_column(Integer)

    # ── Macro at entry (parsed from SpotTrade.macro_context JSON) ─────────────
    atm_score_at_entry:   Mapped[int | None]   = mapped_column(Integer)  # 0–100
    btc_24h_pct_at_entry: Mapped[float | None] = mapped_column(Float)    # BTC 24h return %
    btc_dom_at_entry:     Mapped[float | None] = mapped_column(Float)    # BTC dominance %


class AIAdvisorySession(Base):
    """
    One row per AI advisor run (scheduled Monday or manual trigger).
    Stores the full Opus response + structured findings for display in the UI.
    """
    __tablename__ = "ai_advisory_sessions"

    id:               Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at:       Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    trigger:          Mapped[str]      = mapped_column(String(20), nullable=False)   # scheduled | manual
    model:            Mapped[str]      = mapped_column(String(50), nullable=False)
    spot_trade_count: Mapped[int]      = mapped_column(Integer, default=0)
    cap_trade_count:  Mapped[int]      = mapped_column(Integer, default=0)
    summary:          Mapped[str | None] = mapped_column(Text)
    findings_json:    Mapped[str | None] = mapped_column(Text)   # JSON array of finding dicts
    full_response:    Mapped[str | None] = mapped_column(Text)   # complete Opus JSON output
    tokens_used:      Mapped[int]      = mapped_column(Integer, default=0)


class XRPSwingSetup(Base):
    """4H evaluation of the 3-layer XRP swing trade setup. One row per eval run."""
    __tablename__ = "xrp_swing_setups"

    id:           Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Layer 1 — Macro Gate (4 conditions)
    gate_btc_sma50:       Mapped[bool | None] = mapped_column(Boolean)  # BTC above SMA50
    gate_dom_falling:     Mapped[bool | None] = mapped_column(Boolean)  # BTC.D declining over 3 days
    gate_fg_recovering:   Mapped[bool | None] = mapped_column(Boolean)  # F&G >= 35 and trending up
    gate_btc_weekly_green:Mapped[bool | None] = mapped_column(Boolean)  # BTC weekly candle green

    # Layer 2 — XRP Technicals
    xrp_price:        Mapped[float | None] = mapped_column(Float)
    xrp_rsi_4h:       Mapped[float | None] = mapped_column(Float)
    xrp_rsi_1d:       Mapped[float | None] = mapped_column(Float)
    xrp_volume_ratio: Mapped[float | None] = mapped_column(Float)   # vs 7-day average
    xrp_ema200:       Mapped[float | None] = mapped_column(Float)
    xrp_ema200_pct:   Mapped[float | None] = mapped_column(Float)   # % above(+)/below(-) EMA200
    setup_type:       Mapped[str | None]   = mapped_column(String(5))  # A | B | C | None
    setup_desc:       Mapped[str | None]   = mapped_column(Text)

    # Context snapshot
    btc_price:  Mapped[float | None] = mapped_column(Float)
    btc_dom:    Mapped[float | None] = mapped_column(Float)
    fg_value:   Mapped[int | None]   = mapped_column(Integer)

    # Verdict
    verdict:    Mapped[str]          = mapped_column(String(20), nullable=False, default="WATCHING")
    # WATCHING | SETUP_FORMING | ENTRY_READY | IN_TRADE
    score:      Mapped[int]          = mapped_column(Integer, default=0)  # 0-100
    notes:      Mapped[str | None]   = mapped_column(Text)


class XRPSwingTrade(Base):
    """A manually-confirmed XRP swing trade with staged entries and P&L tracking."""
    __tablename__ = "xrp_swing_trades"

    id:          Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    opened_at:   Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    setup_type:  Mapped[str]      = mapped_column(String(5), nullable=False)  # A | B | C

    # Staged entries stored as JSON: [{price, size_usd, time}]
    stages_json:     Mapped[str | None] = mapped_column(Text)
    avg_entry:       Mapped[float | None] = mapped_column(Float)
    total_size_usd:  Mapped[float | None] = mapped_column(Float)

    # Risk levels
    stop_initial:    Mapped[float]        = mapped_column(Float, nullable=False)
    stop_current:    Mapped[float]        = mapped_column(Float, nullable=False)
    tp1_price:       Mapped[float]        = mapped_column(Float, nullable=False)
    tp2_price:       Mapped[float]        = mapped_column(Float, nullable=False)
    tp3_price:       Mapped[float]        = mapped_column(Float, nullable=False)

    # Management flags
    stop_at_be:       Mapped[bool]         = mapped_column(Boolean, default=False)
    trailing_active:  Mapped[bool]         = mapped_column(Boolean, default=False)
    trailing_pct:     Mapped[float]        = mapped_column(Float, default=2.5)
    trailing_peak:    Mapped[float | None] = mapped_column(Float)

    # Partial closes
    tp1_hit_at:   Mapped[datetime | None] = mapped_column(DateTime)
    tp1_pnl_usd:  Mapped[float | None]   = mapped_column(Float)
    tp2_hit_at:   Mapped[datetime | None] = mapped_column(DateTime)
    tp2_pnl_usd:  Mapped[float | None]   = mapped_column(Float)
    tp3_hit_at:   Mapped[datetime | None] = mapped_column(DateTime)
    tp3_pnl_usd:  Mapped[float | None]   = mapped_column(Float)

    # Final outcome
    status:          Mapped[str]          = mapped_column(String(20), default="open")
    # open | closed_tp | closed_sl | closed_manual | closed_timeout
    closed_at:       Mapped[datetime | None] = mapped_column(DateTime)
    exit_price:      Mapped[float | None]   = mapped_column(Float)
    final_pnl_usd:   Mapped[float | None]   = mapped_column(Float)
    final_pnl_pct:   Mapped[float | None]   = mapped_column(Float)

    # Context at open
    xrp_price_at_open: Mapped[float | None] = mapped_column(Float)
    btc_dom_at_open:   Mapped[float | None] = mapped_column(Float)
    fg_at_open:        Mapped[int | None]   = mapped_column(Integer)
    notes:             Mapped[str | None]   = mapped_column(Text)

    # ATR/EMA at the moment of entry. Computed at evaluation time but never
    # persisted here before — _trade_to_dict() had nothing to return for
    # atr_val/atr_pct/ema200, so every reader of an active trade
    # (_monitor_trade's staging and trailing-arm logic, regime detection)
    # silently got None and skipped. Populated once, at open_trade(); a
    # trade's entry conditions don't change after the fact.
    atr_at_open:      Mapped[float | None] = mapped_column(Float)
    atr_pct_at_open:  Mapped[float | None] = mapped_column(Float)
    ema200_at_open:   Mapped[float | None] = mapped_column(Float)


class XRPAutoState(Base):
    """
    Auto-bot control state and cooldown/staging progress.

    Replaces data/xrp_swing_auto.json — a restart used to lose nothing here
    only because the file happened to be on disk too, but it was a second,
    inconsistent persistence mechanism alongside the DB every other piece of
    trade state already uses. Effectively a singleton: always the row with
    the lowest id, read and written through get_row()/save() in
    spot/xrp_swing.py rather than queried directly.
    """
    __tablename__ = "xrp_auto_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enabled:        Mapped[bool]  = mapped_column(Boolean, default=False, nullable=False)
    auto_size_usd:  Mapped[float] = mapped_column(Float, default=300.0, nullable=False)

    # Defaults True deliberately: this agent has never opened a real trade, and
    # the R:R/level fixes change what happens the moment it can. No code path
    # may send an order to open_trade() while this is set — see run_auto_cycle.
    shadow_mode: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    last_check:  Mapped[datetime | None] = mapped_column(DateTime)
    last_action: Mapped[str | None]      = mapped_column(Text)

    cooldown_until:       Mapped[datetime | None] = mapped_column(DateTime)
    last_opened_eval_id:  Mapped[int | None]      = mapped_column(Integer)

    # Staged auto-entry progress for the currently open trade — 0 means no
    # trade is mid-staging.
    auto_stage:            Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    auto_total_size:       Mapped[float | None]  = mapped_column(Float)
    auto_stage_sizes_json: Mapped[str | None]    = mapped_column(Text)  # e.g. "[0.2, 0.4, 0.4]"


class XRPRiskDecision(Base):
    """
    Audit trail for every auto-open the risk supervisor considered.

    Recorded whether the proposal was approved or refused — a refused one is
    the more interesting record, since it is what proves the gate did its job
    rather than an operator's memory of the rule.
    """
    __tablename__ = "xrp_risk_decisions"

    id:         Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    decided_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # What was proposed
    setup_type:          Mapped[str | None]   = mapped_column(String(5))
    eval_id:              Mapped[int | None]   = mapped_column(Integer)
    entry_price:          Mapped[float | None] = mapped_column(Float)
    requested_size_usd:   Mapped[float | None] = mapped_column(Float)
    final_size_usd:       Mapped[float | None] = mapped_column(Float)
    stop:                 Mapped[float | None] = mapped_column(Float)
    tp1:                  Mapped[float | None] = mapped_column(Float)
    tp2:                  Mapped[float | None] = mapped_column(Float)
    tp3:                  Mapped[float | None] = mapped_column(Float)
    rr_ratio:              Mapped[float | None] = mapped_column(Float)

    # The verdict
    approved:     Mapped[bool]         = mapped_column(Boolean, nullable=False)
    veto_reason:  Mapped[str | None]   = mapped_column(String(48))
    detail:       Mapped[str | None]   = mapped_column(Text)
    checks_json:  Mapped[str | None]   = mapped_column(Text)  # full per-gate audit trail

    # True when approved but not actually sent to open_trade() — the shadow-mode
    # paper record. Distinguishes "approved and taken" from "approved, would
    # have taken" in the Risk Log. Meaningless when approved=False.
    shadowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

