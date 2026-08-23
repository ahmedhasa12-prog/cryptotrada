"""
Paper account — tracks the virtual capital the user has allocated to the bots.
Stored as a JSON file; no DB dependency. Locked capital is computed live from
open trades in both SpotTrade and CapitulationTrade tables.
"""
from __future__ import annotations

import json
from pathlib import Path

from loguru import logger

_ACCOUNT_FILE = Path(__file__).parent.parent / "data" / "paper_account.json"


def _load() -> dict:
    try:
        return json.loads(_ACCOUNT_FILE.read_text())
    except Exception:
        return {"balance_usd": 0.0, "total_funded_usd": 0.0}


def _save(data: dict) -> None:
    _ACCOUNT_FILE.write_text(json.dumps(data, indent=2))


def get_account() -> dict:
    """
    Returns account snapshot:
    {balance_usd, total_funded_usd, locked_usd, available_usd, realized_pnl_usd, net_value_usd}
    """
    data = _load()
    balance = data.get("balance_usd", 0.0)

    locked_usd      = 0.0
    realized_pnl    = 0.0

    try:
        from data.database import get_session
        from data.models import SpotTrade, CapitulationTrade

        with get_session() as s:
            # Open spot trades — lock the full position size
            open_spot = s.query(SpotTrade).filter(SpotTrade.exit_price == None).all()
            for t in open_spot:
                locked_usd += (t.size_usd or 0.0)

            # Closed spot trades — realized P&L
            closed_spot = s.query(SpotTrade).filter(SpotTrade.exit_price != None).all()
            for t in closed_spot:
                realized_pnl += (t.pnl_usd or 0.0)

            # Open cap trades — lock position_usd
            open_cap = s.query(CapitulationTrade).filter(
                CapitulationTrade.outcome == "open"
            ).all()
            for t in open_cap:
                locked_usd += (t.position_usd or 0.0)

            # Closed cap trades — realized P&L
            closed_cap = s.query(CapitulationTrade).filter(
                CapitulationTrade.outcome != "open",
                CapitulationTrade.pnl_net != None,
            ).all()
            for t in closed_cap:
                realized_pnl += (t.pnl_net or 0.0)

    except Exception as e:
        logger.warning(f"[PAPER] Could not compute locked/pnl: {e}")

    available   = max(0.0, balance - locked_usd)
    net_value   = balance + realized_pnl

    return {
        "balance_usd":       round(balance, 2),
        "total_funded_usd":  round(data.get("total_funded_usd", 0.0), 2),
        "locked_usd":        round(locked_usd, 2),
        "available_usd":     round(available, 2),
        "realized_pnl_usd":  round(realized_pnl, 2),
        "net_value_usd":     round(net_value, 2),
    }


def fund_account(amount: float) -> dict:
    """Add amount to the paper account balance. Returns updated account snapshot."""
    if amount <= 0:
        raise ValueError("Amount must be positive")
    data = _load()
    data["balance_usd"]       = round(data.get("balance_usd", 0.0) + amount, 2)
    data["total_funded_usd"]  = round(data.get("total_funded_usd", 0.0) + amount, 2)
    _save(data)
    logger.info(f"[PAPER] Funded ${amount:,.2f} → balance ${data['balance_usd']:,.2f}")
    return get_account()


def set_balance(amount: float) -> dict:
    """Overwrite the paper account balance directly (useful for reset)."""
    if amount < 0:
        raise ValueError("Balance cannot be negative")
    data = _load()
    data["balance_usd"]      = round(amount, 2)
    data["total_funded_usd"] = round(data.get("total_funded_usd", 0.0), 2)
    _save(data)
    logger.info(f"[PAPER] Balance set to ${amount:,.2f}")
    return get_account()
