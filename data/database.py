from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from loguru import logger
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool, NullPool

from data.models import Base

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None

# Indexes — CREATE INDEX IF NOT EXISTS is idempotent, safe to re-run
_INDEX_MIGRATIONS = [
    "CREATE INDEX IF NOT EXISTS idx_ohlcv_sit   ON ohlcv_candles (symbol, interval, timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_macro_snap_ts ON market_snapshots (timestamp)",
]

# Columns added to pre-existing tables — ALTER TABLE ADD COLUMN is idempotent via try/except
_MIGRATIONS = [
    ("spot_trades", "symbol",           "TEXT"),
    ("spot_trades", "size_usd",         "REAL"),
    ("spot_trades", "hotness_at_entry", "INTEGER"),
    ("spot_trades", "strategy_used",    "TEXT"),
    ("spot_trades", "entry_time",       "DATETIME"),
    ("spot_trades", "exit_time",        "DATETIME"),
    ("watchlist",   "pinned",              "INTEGER DEFAULT 0"),
    ("watchlist",   "screen_score",        "REAL"),
    ("watchlist",   "last_screened",       "DATETIME"),
    ("spot_trades",   "trailing_stop_pct",        "REAL"),
    ("spot_trades",   "trailing_stop_peak",       "REAL"),
    ("p2p_trades",    "binance_order_id",         "TEXT UNIQUE"),
    # trade_reviews context columns (added with enriched post-mortem)
    ("trade_reviews", "exit_hour_utc",            "INTEGER"),
    ("trade_reviews", "exit_day_of_week",         "INTEGER"),
    ("trade_reviews", "exit_session",             "TEXT"),
    ("trade_reviews", "avg_volume_6h",            "REAL"),
    ("trade_reviews", "avg_taker_buy_ratio_6h",   "REAL"),
    ("trade_reviews", "entry_volume",             "REAL"),
    ("trade_reviews", "entry_taker_ratio",        "REAL"),
    ("trade_reviews", "btc_dom_at_exit",          "REAL"),
    ("trade_reviews", "fear_greed_at_exit",       "INTEGER"),
    # macro context at entry — for feedback-loop correlation analysis
    ("spot_trades",   "macro_context",            "TEXT"),
    ("trade_reviews", "atm_score_at_entry",       "INTEGER"),
    ("trade_reviews", "btc_24h_pct_at_entry",     "REAL"),
    ("trade_reviews", "btc_dom_at_entry",         "REAL"),
    # TP1 partial-close banked P&L — added to runner close for full position P&L
    ("spot_trades",         "tp1_pnl_usd",        "REAL"),
    # XRP swing shadow mode — xrp_auto_state/xrp_risk_decisions already exist in
    # the live DB from Phase 2, so these columns need the ALTER path too, not
    # just create_all (which only creates missing tables, never alters existing
    # ones). Both default true/false so an old row reads as "safe" the moment
    # this runs — no positions can slip open on the same deploy that adds it.
    ("xrp_auto_state",      "shadow_mode",        "INTEGER DEFAULT 1"),
    ("xrp_risk_decisions",  "shadowed",           "INTEGER DEFAULT 0"),
    # ATR/EMA at entry — see the XRPSwingTrade docstring in models.py. NULL on
    # every trade opened before this migration; that's correct, not a gap to
    # backfill, since those trades' entry conditions were never recorded.
    ("xrp_swing_trades",    "atr_at_open",        "REAL"),
    ("xrp_swing_trades",    "atr_pct_at_open",    "REAL"),
    ("xrp_swing_trades",    "ema200_at_open",     "REAL"),
]


def _migrate(engine: Engine) -> None:
    with engine.connect() as conn:
        for table, column, col_type in _MIGRATIONS:
            try:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                conn.commit()
            except Exception as e:
                if "duplicate column" not in str(e).lower() and "already exists" not in str(e).lower() and "cannot add a unique column" not in str(e).lower():
                    logger.warning(f"Migration warning — {table}.{column}: {e}")
        for stmt in _INDEX_MIGRATIONS:
            conn.execute(text(stmt))
        conn.commit()


def init_db(db_path: str = "data/trading.db") -> Engine:
    """Create tables and return the engine. Safe to call multiple times."""
    global _engine, _SessionLocal

    is_memory = db_path == ":memory:"
    if not is_memory:
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    url = f"sqlite:///{db_path}"
    if is_memory:
        # StaticPool: all threads share one connection so in-memory DB is visible everywhere
        kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": StaticPool}
    else:
        # NullPool: each call gets a fresh SQLite connection and closes it immediately.
        # No pool limit → no exhaustion errors when FastAPI threads + executor threads
        # + scheduler jobs all hit the DB concurrently. Safe with WAL journal mode.
        kwargs = {"connect_args": {"check_same_thread": False}, "poolclass": NullPool}
    _engine = create_engine(url, **kwargs)
    # WAL mode: safe concurrent reads + crash recovery without corruption
    if not is_memory:
        with _engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA synchronous=NORMAL"))  # safe + faster than FULL
            conn.commit()
    Base.metadata.create_all(_engine)
    _migrate(_engine)
    _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    logger.info(f"Database initialised at {db_path}")
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    if _SessionLocal is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    session: Session = _SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_db() -> None:
    """Drop all tables and reset engine — for tests only."""
    global _engine, _SessionLocal
    if _engine is not None:
        Base.metadata.drop_all(_engine)
        _engine.dispose()
    _engine = None
    _SessionLocal = None
