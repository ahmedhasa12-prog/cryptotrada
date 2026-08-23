"""
Stage 1 — Hard screening of the full Binance USDT universe.

Two approaches run simultaneously:
  A) Fixed floor  — all coins with volume > $15M that pass quality filters
  B) Dynamic top  — quality-filtered coins ranked by volume, top 30 taken

Run: python3 screen_coins.py
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone

import httpx

TICKER_URL   = "https://api.binance.com/api/v3/ticker/24hr"
EXCHANGE_URL = "https://api.binance.com/api/v3/exchangeInfo"

# ── Thresholds ────────────────────────────────────────────────────────────────
FIXED_FLOOR_USD  = 15_000_000   # Approach A
DYNAMIC_TOP_N    = 30           # Approach B
MIN_TRADES_24H   = 5_000        # real activity (not wash-traded ghost volume)
MAX_ABS_CHANGE   = 40.0         # reject extreme 24h moves (listing day / manipulation)
MIN_PRICE        = 0.000001     # reject essentially dead-priced coins

# ── Quality-filter exclusion lists ────────────────────────────────────────────
STABLECOINS = {
    "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "USDD",
    "FRAX", "LUSD", "SUSD", "GUSD", "UST", "USDS", "PYUSD",
}

FIAT_CODES = {          # e.g. EURUSDT, GBPUSDT — forex pairs, not crypto
    "EUR", "GBP", "AUD", "BRL", "TRY", "RUB", "NGN", "ARS",
}

LEVERAGED = [           # substring match against base symbol
    "UP", "DOWN", "BULL", "BEAR",
    "3L", "3S", "2L", "2S", "BVOL", "HEDGE",
]

WRAPPED = {             # exact base-symbol match
    "WBTC", "WETH", "WBNB", "WMATIC", "WAVAX",
}

MEME_FRAGMENTS = [
    "INU", "MOON", "ELON", "BABY", "SAFE",
    "PEPE", "FLOKI", "BONK", "DOGE2", "SHIB2",
    "TURBO", "WIF", "MEME", "CHAD", "WOJAK",
]

DERIVATIVE_FRAGMENTS = ["BETH", "LDBNB", "LDETH"]

NFT_FAN_TOKENS = {
    "ACM", "AFC", "ALPINE", "ARG", "ASR", "ATM", "BAR",
    "CITY", "INTER", "JUV", "LAZIO", "NAP", "OG",
    "PORTO", "PSG", "SANTOS", "TRA", "PFL", "SPBL",
}


# ── Filter logic ──────────────────────────────────────────────────────────────
def quality_reject_reason(base: str, price: float, volume: float,
                           trades: int, change: float) -> str | None:
    """Return rejection reason string, or None if coin passes quality filters."""
    if base in FIAT_CODES:
        return "fiat forex pair"
    if base in STABLECOINS or base.startswith("USD") or base.endswith("USD"):
        return "stablecoin"
    if any(s in base for s in LEVERAGED):
        return "leveraged/inverse token"
    if base in WRAPPED:
        return "wrapped token"
    if any(f in base for f in MEME_FRAGMENTS):
        return "meme/low-quality token"
    if any(f in base for f in DERIVATIVE_FRAGMENTS):
        return "staking derivative"
    if base in NFT_FAN_TOKENS:
        return "NFT/fan token"
    if price < MIN_PRICE:
        return f"price too low (${price:.8f})"
    if trades < MIN_TRADES_24H:
        return f"too few trades ({trades:,})"
    if change > MAX_ABS_CHANGE:
        return f"extreme 24h move ({change:.1f}%)"
    return None


def build_candidate(sym: str, t: dict) -> dict:
    base = sym[:-4]
    return {
        "symbol":     base,
        "price":      float(t["lastPrice"]),
        "volume_m":   round(float(t["quoteVolume"]) / 1e6, 1),
        "trades_k":   round(int(t["count"]) / 1000, 1),
        "change_pct": round(float(t["priceChangePercent"]), 2),
    }


def screen(tickers: list[dict], trading_symbols: set[str]):
    quality_passed = []
    rejected       = []

    for t in tickers:
        sym = t["symbol"]
        if not sym.endswith("USDT") or sym not in trading_symbols:
            continue

        base   = sym[:-4]
        price  = float(t["lastPrice"])
        volume = float(t["quoteVolume"])
        trades = int(t["count"])
        change = abs(float(t["priceChangePercent"]))

        reason = quality_reject_reason(base, price, volume, trades, change)
        if reason:
            rejected.append({"symbol": base, "reason": reason,
                             "volume_m": round(volume / 1e6, 1)})
        else:
            quality_passed.append(build_candidate(sym, t))

    quality_passed.sort(key=lambda x: x["volume_m"], reverse=True)

    approach_a = [c for c in quality_passed if c["volume_m"] >= FIXED_FLOOR_USD / 1e6]
    approach_b = quality_passed[:DYNAMIC_TOP_N]

    return quality_passed, approach_a, approach_b, rejected


# ── Display helpers ───────────────────────────────────────────────────────────
CURRENT_WATCHLIST = {"SOL", "ADA", "ALGO", "HBAR", "LINK", "VET", "XRP", "BNB", "DOGE"}

def row(i: int, c: dict, flag: str = "") -> str:
    arrow = "▲" if c["change_pct"] >= 0 else "▼"
    wl    = " ★" if c["symbol"] in CURRENT_WATCHLIST else ""
    return (f"  {i:<4} {c['symbol']:<8} ${c['price']:<15,.4f} "
            f"{c['volume_m']:>8,.0f}M   {c['trades_k']:>7,.0f}K   "
            f"{arrow}{abs(c['change_pct']):.2f}%  {wl}{flag}")

HDR = (f"\n  {'#':<4} {'Symbol':<8} {'Price':<17} {'Vol/day':>8}    "
       f"{'Trades':>7}    {'24h%'}   ★=on watchlist")
DIV = "  " + "─" * 68


def main():
    print("Fetching Binance data …")
    with httpx.Client(timeout=20) as client:
        tickers  = client.get(TICKER_URL).json()
        exchange = client.get(EXCHANGE_URL).json()

    trading_symbols = {
        s["symbol"]
        for s in exchange["symbols"]
        if s["status"] == "TRADING" and s["quoteAsset"] == "USDT"
    }

    total = len(trading_symbols)
    quality_all, approach_a, approach_b, rejected = screen(tickers, trading_symbols)

    # ── Overview ──────────────────────────────────────────────────────────────
    print(f"\n{'═'*70}")
    print(f"  Binance USDT pairs (actively trading) : {total}")
    print(f"  Pass quality filters                  : {len(quality_all)}")
    print(f"  Rejected                              : {len(rejected)}")
    print(f"{'═'*70}")

    reasons = Counter(r["reason"].split(" (")[0] for r in rejected)
    print("\nRejection breakdown:")
    for reason, count in reasons.most_common():
        print(f"  {count:>4}  {reason}")

    # ── Approach A: Fixed $15M floor ──────────────────────────────────────────
    print(f"\n{'═'*70}")
    print(f"  APPROACH A — Fixed floor ≥ ${FIXED_FLOOR_USD/1e6:.0f}M/day   ({len(approach_a)} coins)")
    print(f"{'═'*70}")
    print(HDR); print(DIV)
    for i, c in enumerate(approach_a, 1):
        print(row(i, c))

    # ── Approach B: Dynamic top 30 ────────────────────────────────────────────
    print(f"\n{'═'*70}")
    print(f"  APPROACH B — Dynamic top {DYNAMIC_TOP_N} by volume (no volume floor)")
    cutoff = approach_b[-1]["volume_m"] if approach_b else 0
    print(f"  (cutoff falls naturally at ${cutoff:.0f}M/day today)")
    print(f"{'═'*70}")
    print(HDR); print(DIV)
    for i, c in enumerate(approach_b, 1):
        only_b = " ← only in B" if c not in approach_a else ""
        print(row(i, c, only_b))

    # ── Divergence check ─────────────────────────────────────────────────────
    syms_a = {c["symbol"] for c in approach_a}
    syms_b = {c["symbol"] for c in approach_b}
    only_a = syms_a - syms_b
    only_b = syms_b - syms_a

    print(f"\n{'═'*70}")
    print("  DIVERGENCE between A and B")
    print(f"{'═'*70}")
    if only_a:
        print(f"  In A only (above $15M but outside top {DYNAMIC_TOP_N}): {', '.join(sorted(only_a))}")
    if only_b:
        print(f"  In B only (in top {DYNAMIC_TOP_N} but below $15M cutoff): {', '.join(sorted(only_b))}")
    if not only_a and not only_b:
        print("  → Lists are identical today.")

    # ── Current watchlist check ───────────────────────────────────────────────
    all_syms = {c["symbol"] for c in quality_all}
    print(f"\n{'═'*70}")
    print("  CURRENT WATCHLIST STATUS")
    print(f"{'═'*70}")
    for coin in sorted(CURRENT_WATCHLIST):
        if coin in syms_b:
            vol = next(c["volume_m"] for c in approach_b if c["symbol"] == coin)
            rank = next(i for i, c in enumerate(approach_b, 1) if c["symbol"] == coin)
            print(f"  {coin:<8} ✓ in top {DYNAMIC_TOP_N}  (rank #{rank}, ${vol:.0f}M/day)")
        elif coin in all_syms:
            vol = next(c["volume_m"] for c in quality_all if c["symbol"] == coin)
            rank = next(i for i, c in enumerate(quality_all, 1) if c["symbol"] == coin)
            print(f"  {coin:<8} ✗ below top {DYNAMIC_TOP_N}  (rank #{rank} overall, ${vol:.0f}M/day)")
        else:
            print(f"  {coin:<8} ✗ failed quality filters")

    # ── Save ──────────────────────────────────────────────────────────────────
    out = {
        "run_at": datetime.now(timezone.utc).isoformat(),
        "total_usdt_pairs": total,
        "quality_pool_size": len(quality_all),
        "approach_a_fixed_15m": approach_a,
        "approach_b_dynamic_top30": approach_b,
        "rejection_summary": dict(reasons.most_common()),
    }
    with open("screen_results.json", "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n  Full results saved → screen_results.json\n")


if __name__ == "__main__":
    main()
