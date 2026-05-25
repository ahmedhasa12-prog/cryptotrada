from datetime import datetime, timezone

import pytest

import data.database as db
from data.models import P2PTrade, SpotTrade, MarketSnapshot, TraderHistory, SystemEvent


@pytest.fixture(autouse=True)
def in_memory_db():
    """Each test gets a fresh in-memory SQLite database."""
    db.init_db(":memory:")
    yield
    db.reset_db()


def test_init_creates_all_tables():
    engine = db.get_engine()
    from sqlalchemy import inspect
    tables = inspect(engine).get_table_names()
    assert set(tables) == {
        "p2p_trades", "spot_trades", "market_snapshots",
        "trader_history", "system_events",
    }


def test_p2p_trade_insert_and_query():
    with db.get_session() as s:
        trade = P2PTrade(
            timestamp=datetime.utcnow(),
            trade_type="sell",
            amount_usdt=100.0,
            rate_sdg=600.0,
            total_sdg=60000.0,
            trader_username="trader_x",
            mode="manual",
        )
        s.add(trade)

    with db.get_session() as s:
        result = s.query(P2PTrade).filter_by(trader_username="trader_x").first()
        assert result is not None
        assert result.amount_usdt == 100.0
        assert result.total_sdg == 60000.0


def test_spot_trade_insert_and_query():
    with db.get_session() as s:
        trade = SpotTrade(
            asset="XRP",
            mode="paper",
            direction="long",
            entry_price=0.55,
            size=100.0,
        )
        s.add(trade)

    with db.get_session() as s:
        result = s.query(SpotTrade).filter_by(asset="XRP").first()
        assert result is not None
        assert result.entry_price == 0.55
        assert result.mode == "paper"


def test_market_snapshot_insert():
    with db.get_session() as s:
        snap = MarketSnapshot(
            buy_best_rate=605.0,
            sell_best_rate=595.0,
            spread=10.0,
            our_rate=600.0,
        )
        s.add(snap)

    with db.get_session() as s:
        result = s.query(MarketSnapshot).first()
        assert result.spread == 10.0


def test_trader_history_insert_and_flag():
    with db.get_session() as s:
        trader = TraderHistory(
            username="bad_actor",
            total_trades=5,
            successful=3,
            disputed=2,
            flagged=True,
        )
        s.add(trader)

    with db.get_session() as s:
        result = s.query(TraderHistory).filter_by(username="bad_actor").first()
        assert result.flagged is True
        assert result.disputed == 2


def test_system_event_insert():
    with db.get_session() as s:
        event = SystemEvent(
            event_type="mode_change",
            description="Switched to semi-auto mode",
            mode="semi",
        )
        s.add(event)

    with db.get_session() as s:
        result = s.query(SystemEvent).filter_by(event_type="mode_change").first()
        assert result.description == "Switched to semi-auto mode"


def test_session_rolls_back_on_error():
    with pytest.raises(Exception):
        with db.get_session() as s:
            s.add(P2PTrade(
                trade_type="sell",
                amount_usdt=None,  # violates NOT NULL
                rate_sdg=600.0,
                total_sdg=60000.0,
                trader_username="x",
                mode="manual",
            ))
            s.flush()

    with db.get_session() as s:
        count = s.query(P2PTrade).count()
        assert count == 0


def test_get_engine_raises_if_not_initialised():
    db.reset_db()
    with pytest.raises(RuntimeError, match="not initialised"):
        db.get_engine()
