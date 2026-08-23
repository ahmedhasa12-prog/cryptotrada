"""
Narrative tracker — manually curated monthly by the operator.
Each narrative has a heat level: hot | warming | cooling.
Coins in the watchlist are tagged to a narrative; hot narrative = score boost.
"""
from __future__ import annotations

# ── Current narratives (update monthly) ──────────────────────────────────────

NARRATIVES: list[dict] = [
    # HOT
    {
        "name":   "Real World Assets (RWA)",
        "heat":   "hot",
        "coins":  ["LINK", "XRP", "XLM"],
        "reason": "Tokenisation of real-world assets is the dominant institutional narrative; Stellar adjacent via cross-border payments",
    },
    {
        "name":   "AI + Crypto",
        "heat":   "hot",
        "coins":  ["FET", "NEAR", "INJ"],
        "reason": "AI infrastructure and compute tokens attracting major capital flows; FET/NEAR/INJ all have live AI product layers",
    },
    # WARMING
    {
        "name":   "Smart Contract Platforms",
        "heat":   "warming",
        "coins":  ["ETH", "SOL", "BNB", "TON"],
        "reason": "Core L1 foundation assets with ongoing ecosystem growth; underperforming BTC near-term but structurally sound",
    },
    {
        "name":   "DeFi Resurgence",
        "heat":   "warming",
        "coins":  [],
        "reason": "On-chain activity picking up across major DeFi protocols",
    },
    {
        "name":   "Enterprise Blockchain",
        "heat":   "warming",
        "coins":  ["HBAR", "VET", "ALGO"],
        "reason": "Governments and corporations integrating blockchain solutions",
    },
    # COOLING
    {
        "name":   "Layer 2 Scaling",
        "heat":   "cooling",
        "coins":  [],
        "reason": "L2 narrative peaked; market rotation away from scaling tokens",
    },
    {
        "name":   "Meme Coins",
        "heat":   "cooling",
        "coins":  ["DOGE"],
        "reason": "Speculative cycle fading without fresh catalyst",
    },
]

_HEAT_ORDER = {"hot": 3, "warming": 2, "cooling": 1}

# Build quick lookup: symbol → narrative name
_SYMBOL_TO_NARRATIVE: dict[str, str] = {}
for _n in NARRATIVES:
    for _sym in _n["coins"]:
        _SYMBOL_TO_NARRATIVE[_sym] = _n["name"]


def get_narratives() -> list[dict]:
    return NARRATIVES


def get_narrative_for_coin(symbol: str) -> str | None:
    return _SYMBOL_TO_NARRATIVE.get(symbol.upper())


def get_narrative_heat(narrative_name: str) -> str:
    """Return 'hot' | 'warming' | 'cooling' | 'unknown'."""
    for n in NARRATIVES:
        if n["name"] == narrative_name:
            return n["heat"]
    return "unknown"


def get_coin_narrative_heat(symbol: str) -> str:
    """Convenience: get heat level directly for a coin symbol."""
    name = get_narrative_for_coin(symbol)
    if not name:
        return "unknown"
    return get_narrative_heat(name)
