"""
Stage 1 + Stage 2 — dynamic watchlist selection pipeline.

Stage 1: quality filter across all Binance USDT pairs (no auth needed).
Stage 2: composite scoring on 7 criteria → ranked list → top TARGET_SIZE coins.

PINNED coins (BTC, ETH, XRP, SOL) are always included regardless of score.
Run standalone for inspection: python -m spot.stage2
"""
from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone

import httpx
from loguru import logger

from data.database import get_session
from data.models import WatchlistScreenHistory
from spot.narratives import get_coin_narrative_heat, get_narrative_for_coin, NARRATIVES

# ── Config ────────────────────────────────────────────────────────────────────
BINANCE_TICKER   = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_EXCHANGE = "https://api.binance.com/api/v3/exchangeInfo"
BINANCE_KLINES   = "https://api.binance.com/api/v3/klines"

PINNED           = {"BTC", "ETH", "XRP", "SOL"}  # always on the list, immune to scoring
TARGET_SIZE      = 12               # total watchlist size including pinned (4 pinned + 8 dynamic)
CANDLE_LIMIT     = 200              # daily candles per coin (needed for EMA200 + listing-age check)
STAGE2_MIN_VOL   = 10_000_000       # minimum $10M/day to enter composite scoring
MIN_LISTING_DAYS = 180              # require at least 180 daily candles (≈ 6 months listed)

# ── Stage 1 quality filter constants ─────────────────────────────────────────
MIN_TRADES_24H  = 25_000    # minimum trades/day (~17/min) — ensures 5-min cycle liquidity
MAX_ABS_CHANGE  = 40.0      # reject extreme daily movers (manipulation / new listings)
MIN_PRICE       = 0.000001

# Valid symbol: 2–10 uppercase ASCII letters/digits only — blocks unicode, single chars, etc.
_SYMBOL_RE = re.compile(r'^[A-Z0-9]{2,10}$')

STABLECOINS = {
    "USDC", "BUSD", "DAI", "TUSD", "FDUSD", "USDP", "USDD",
    "FRAX", "LUSD", "SUSD", "GUSD", "UST", "USDS", "PYUSD",
}
FIAT_CODES = {"EUR", "GBP", "AUD", "BRL", "TRY", "RUB", "NGN", "ARS"}
LEVERAGED  = ["UP", "DOWN", "BULL", "BEAR", "3L", "3S", "2L", "2S", "5L", "5S", "BVOL", "HEDGE"]
WRAPPED    = {"WBTC", "WETH", "WBNB", "WMATIC", "WAVAX"}
MEME_FRAGS = [
    "INU", "MOON", "ELON", "BABY", "SAFE", "PEPE", "FLOKI", "BONK",
    "DOGE2", "SHIB2", "TURBO", "WIF", "MEME", "CHAD", "WOJAK",
    "TRUMP", "BODEN", "CAT", "COQ",
]
DERIV_FRAGS = ["BETH", "LDBNB", "LDETH"]
NFT_FAN = {
    "ACM", "AFC", "ALPINE", "ARG", "ASR", "ATM", "BAR", "CITY",
    "INTER", "JUV", "LAZIO", "NAP", "OG", "PORTO", "PSG",
    "SANTOS", "TRA", "PFL", "SPBL",
}

# ── Score weights (must sum to 1.0) ───────────────────────────────────────────
# Redesigned per Opus advisory 2026-06-01:
# — Reduced lagging indicators (volume rank, EMA trend)
# — Boosted relative strength (best predictor in Bitcoin Season)
# — Added intraday consistency and BTC beta (new signals)
# — Narrative dropped to tiebreaker (monthly curation too stale for crypto)
W_VOLUME     = 0.15   # 24h USDT volume rank (was 0.25)
W_TREND      = 0.20   # EMA structure + momentum (was 0.30)
W_REL_STR    = 0.25   # 30d return vs BTC (was 0.20)
W_NARRATIVE  = 0.05   # narrative heat — tiebreaker only (was 0.15)
W_VOLATILITY = 0.10   # ATR14 quality, sweet spot 2–5% (recalibrated)
W_INTRADAY   = 0.15   # % of past 14 days that closed positive (new)
W_BTC_BETA   = 0.10   # rolling 30d beta vs BTC, target 0.5–0.9 (new)

# ── Known coin names (cosmetic — falls back to symbol if missing) ─────────────
_COIN_NAMES: dict[str, str] = {
    "BTC": "Bitcoin",      "ETH": "Ethereum",    "SOL": "Solana",
    "XRP": "XRP",          "BNB": "BNB",         "ADA": "Cardano",
    "DOGE": "Dogecoin",    "LINK": "Chainlink",   "AVAX": "Avalanche",
    "TRX": "Tron",         "NEAR": "NEAR Protocol","SUI": "Sui",
    "UNI": "Uniswap",      "TON": "Toncoin",      "TAO": "Bittensor",
    "ONDO": "Ondo Finance","LTC": "Litecoin",     "RENDER": "Render",
    "HBAR": "Hedera",      "ALGO": "Algorand",    "VET": "VeChain",
    "ZEC": "Zcash",        "DASH": "Dash",        "FIDA": "Bonfida",
    "XLM": "Stellar",      "INJ": "Injective",    "FET": "Fetch.ai",
    "AAVE": "Aave",        "ARB": "Arbitrum",     "OP": "Optimism",
    "ATOM": "Cosmos",      "DOT": "Polkadot",     "MATIC": "Polygon",
    "AVAX": "Avalanche",   "FIL": "Filecoin",     "ICP": "Internet Computer",
}

# Build narrative-leader lookup from the narratives module
_NARRATIVE_LEADERS: set[str] = set()
for _n in NARRATIVES:
    for _sym in _n.get("coins", []):
        if _n.get("heat") == "hot":
            _NARRATIVE_LEADERS.add(_sym)


def _coin_name(symbol: str) -> str:
    return _COIN_NAMES.get(symbol, symbol)


def _is_leader(symbol: str) -> bool:
    return symbol in _NARRATIVE_LEADERS


# ── Stage 1 ───────────────────────────────────────────────────────────────────

def _quality_ok(base: str, price: float, trades: int, change: float) -> bool:
    # ASCII-only symbols: blocks unicode tokens (e.g. Chinese-char tokens on Binance)
    if not _SYMBOL_RE.match(base):                  return False
    if base in FIAT_CODES:                          return False
    if base in STABLECOINS:                         return False
    if base.startswith("USD") or base.endswith("USD"): return False
    if any(s in base for s in LEVERAGED):           return False
    if base in WRAPPED:                             return False
    if any(f in base for f in MEME_FRAGS):          return False
    if any(f in base for f in DERIV_FRAGS):         return False
    if base in NFT_FAN:                             return False
    if price < MIN_PRICE:                           return False
    if trades < MIN_TRADES_24H:                     return False
    if change > MAX_ABS_CHANGE:                     return False
    return True


def _run_stage1(tickers: list[dict], trading_syms: set[str]) -> list[dict]:
    """Return quality-filtered coins sorted by daily USDT volume descending."""
    pool = []
    for t in tickers:
        sym = t["symbol"]
        if not sym.endswith("USDT") or sym not in trading_syms:
            continue
        base   = sym[:-4]
        price  = float(t["lastPrice"])
        volume = float(t["quoteVolume"])
        trades = int(t["count"])
        change = abs(float(t["priceChangePercent"]))
        if _quality_ok(base, price, trades, change):
            pool.append({
                "symbol":     base,
                "volume":     volume,
                "price":      price,
                "change_pct": float(t["priceChangePercent"]),
            })
    pool.sort(key=lambda x: x["volume"], reverse=True)
    return pool


# ── Stage 2 helpers ───────────────────────────────────────────────────────────

async def _fetch_candles(client: httpx.AsyncClient, symbol: str) -> list:
    try:
        r = await client.get(BINANCE_KLINES, params={
            "symbol": f"{symbol}USDT", "interval": "1d", "limit": CANDLE_LIMIT,
        })
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logger.debug(f"Stage2 candle fetch failed {symbol}: {e}")
    return []


def _ema(closes: list[float], period: int) -> float | None:
    if len(closes) < period:
        return None
    k = 2.0 / (period + 1)
    ema = closes[0]
    for c in closes[1:]:
        ema = c * k + ema * (1 - k)
    return ema


def _trend_score(candles: list) -> float:
    """0–100: EMA structure + price momentum."""
    if len(candles) < 50:
        return 0.0
    closes = [float(c[4]) for c in candles]
    price  = closes[-1]
    ema50  = _ema(closes, 50)
    ema200 = _ema(closes, 200) if len(closes) >= 200 else None

    pts = 0
    max_pts = 60   # base: 3 binary EMA signals × 20

    if ema50  and price  > ema50:  pts += 20
    if ema200 and price  > ema200: pts += 20
    if ema50  and ema200 and ema50 > ema200: pts += 20
    if ema200 is None:             max_pts -= 40  # can't compute both EMA200 signals

    # Momentum: 30d and 7d returns
    if len(closes) >= 31:
        max_pts += 20
        if closes[-31] > 0 and (closes[-1] - closes[-31]) / closes[-31] > 0:
            pts += 20
    if len(closes) >= 8:
        max_pts += 20
        if closes[-8] > 0 and (closes[-1] - closes[-8]) / closes[-8] > 0:
            pts += 20

    return (pts / max_pts * 100) if max_pts > 0 else 0.0


def _atr_pct(candles: list) -> float | None:
    """ATR(14) as % of current price."""
    if len(candles) < 15:
        return None
    trs = []
    for i in range(1, 15):
        h  = float(candles[-i][2])
        lo = float(candles[-i][3])
        pc = float(candles[-i - 1][4])
        trs.append(max(h - lo, abs(h - pc), abs(lo - pc)))
    price = float(candles[-1][4])
    return (sum(trs) / len(trs) / price * 100) if price > 0 else None


def _volatility_score(atr: float | None) -> float:
    """0–100: sweet spot 2–5% (aligned with TP1 at 3.5% and trailing at 2.5%)."""
    if atr is None: return 50.0
    if atr < 1:     return 10.0
    if atr < 1.5:   return 25.0
    if atr < 2:     return 50.0
    if atr <= 5:    return 100.0   # sweet spot
    if atr <= 8:    return 75.0
    if atr <= 12:   return 45.0
    if atr <= 18:   return 25.0
    return 10.0


def _intraday_score(candles: list) -> float:
    """0–100: % of past 14 daily candles that closed above open (consistent buying pressure)."""
    if len(candles) < 7:
        return 50.0
    recent = candles[-14:] if len(candles) >= 14 else candles
    positive = sum(1 for c in recent if float(c[4]) > float(c[1]))  # close > open
    return round(positive / len(recent) * 100, 1)


def _btc_beta_score(coin_closes: list[float], btc_closes: list[float]) -> float:
    """0–100: rolling 30d beta vs BTC. Target 0.5–0.9 scores highest.
    Low-beta coins hold better in dumps and lead altcoin recoveries."""
    if len(coin_closes) < 32 or len(btc_closes) < 32:
        return 50.0
    c_ret = [(coin_closes[-i] - coin_closes[-i-1]) / coin_closes[-i-1]
             for i in range(1, 31) if coin_closes[-i-1] > 0]
    b_ret = [(btc_closes[-i] - btc_closes[-i-1]) / btc_closes[-i-1]
             for i in range(1, 31) if btc_closes[-i-1] > 0]
    n = min(len(c_ret), len(b_ret))
    if n < 20:
        return 50.0
    c_ret, b_ret = c_ret[:n], b_ret[:n]
    mean_c = sum(c_ret) / n
    mean_b = sum(b_ret) / n
    cov   = sum((c_ret[i] - mean_c) * (b_ret[i] - mean_b) for i in range(n)) / n
    var_b = sum((b_ret[i] - mean_b) ** 2 for i in range(n)) / n
    if var_b == 0:
        return 50.0
    beta = cov / var_b
    if 0.5 <= beta <= 0.9:  return 100.0
    if 0.9 < beta <= 1.1:   return 80.0
    if 0.3 <= beta < 0.5:   return 70.0
    if 1.1 < beta <= 1.3:   return 60.0
    if beta < 0.3:          return 40.0
    return 25.0  # beta > 1.3 — high-beta coins dump harder


def _narrative_score(symbol: str) -> float:
    """0–100 based on narrative heat + leader bonus."""
    heat = get_coin_narrative_heat(symbol)
    base = {"hot": 80, "warming": 55, "cooling": 25, "none": 10}.get(heat, 10)
    if _is_leader(symbol):
        base = min(100, base + 20)
    return float(base)


async def _fetch_with_sem(client: httpx.AsyncClient, sym: str, sem: asyncio.Semaphore):
    async with sem:
        return sym, await _fetch_candles(client, sym)


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def run_stage2() -> list[dict]:
    """
    Full Stage 1 + 2 pipeline. Returns ordered list of TARGET_SIZE coins.
    Each entry has: symbol, name, composite_score, trade_type, narrative, is_narrative_leader,
                    pinned, volume, trend_score, rs_score, narr_score, vol_q_score, atr_pct,
                    intraday_score, btc_beta_score
    """
    logger.info("Stage 2 watchlist refresh started")

    async with httpx.AsyncClient(timeout=30) as client:
        ticker_r   = await client.get(BINANCE_TICKER)
        exchange_r = await client.get(BINANCE_EXCHANGE)

    ticker_r.raise_for_status()
    exchange_r.raise_for_status()

    trading_syms = {
        s["symbol"] for s in exchange_r.json()["symbols"]
        if s["status"] == "TRADING" and s["quoteAsset"] == "USDT"
    }

    pool_all = _run_stage1(ticker_r.json(), trading_syms)
    pool = [c for c in pool_all if c["volume"] >= STAGE2_MIN_VOL or c["symbol"] in PINNED]
    logger.info(f"Stage 1: {len(pool_all)} coins passed quality filter, "
                f"{len(pool)} above ${STAGE2_MIN_VOL/1e6:.0f}M volume floor")

    fetch_syms = list({c["symbol"] for c in pool} | PINNED)

    sem = asyncio.Semaphore(20)
    async with httpx.AsyncClient(timeout=30) as client:
        tasks = [_fetch_with_sem(client, sym, sem) for sym in fetch_syms]
        results = await asyncio.gather(*tasks)

    candles_map: dict[str, list] = {sym: data for sym, data in results}
    btc_candles = candles_map.get("BTC", [])
    btc_closes  = [float(c[4]) for c in btc_candles]
    logger.info(f"Fetched candles for {sum(1 for v in candles_map.values() if v)} / {len(fetch_syms)} coins")

    # ── Compute raw scores ────────────────────────────────────────────────────
    n = len(pool)
    scored = []
    skipped_new = []
    for rank, coin in enumerate(pool):
        sym   = coin["symbol"]
        cdata = candles_map.get(sym, [])

        # Skip recently-listed coins (< MIN_LISTING_DAYS daily candles) unless pinned
        if len(cdata) < MIN_LISTING_DAYS and sym not in PINNED:
            skipped_new.append(sym)
            continue

        closes = [float(c[4]) for c in cdata]

        # 30d relative strength vs BTC (raw diff — normalized below)
        rs_raw = None
        if len(closes) >= 31 and len(btc_closes) >= 31 and closes[-31] > 0 and btc_closes[-31] > 0:
            r_coin = (closes[-1] - closes[-31]) / closes[-31]
            r_btc  = (btc_closes[-1] - btc_closes[-31]) / btc_closes[-31]
            rs_raw = r_coin - r_btc

        scored.append({
            "symbol":        sym,
            "volume":        coin["volume"],
            "change_pct":    coin["change_pct"],
            "vol_score":     (1 - rank / n) * 100 if n > 1 else 100.0,
            "trend_score":   _trend_score(cdata),
            "rs_raw":        rs_raw,
            "narr_score":    _narrative_score(sym),
            "vol_q_score":   _volatility_score(_atr_pct(cdata)),
            "intraday_score": _intraday_score(cdata),
            "btc_beta_score": _btc_beta_score(closes, btc_closes),
            "atr_pct":       _atr_pct(cdata),
        })

    if skipped_new:
        logger.info(f"Stage 2: skipped {len(skipped_new)} newly-listed coins (<{MIN_LISTING_DAYS}d): {skipped_new[:10]}")

    # ── Normalize relative strength across all coins ───────────────────────────
    rs_vals = [c["rs_raw"] for c in scored if c["rs_raw"] is not None]
    if rs_vals:
        rs_min, rs_max = min(rs_vals), max(rs_vals)
        rs_range = rs_max - rs_min if rs_max != rs_min else 1.0
        for c in scored:
            c["rs_score"] = ((c["rs_raw"] - rs_min) / rs_range * 100
                             if c["rs_raw"] is not None else 50.0)
    else:
        for c in scored:
            c["rs_score"] = 50.0

    # BTC's relative strength vs itself is always neutral
    for c in scored:
        if c["symbol"] == "BTC":
            c["rs_score"] = 50.0

    # ── Compute composite score ───────────────────────────────────────────────
    for c in scored:
        c["composite"] = round(
            c["vol_score"]       * W_VOLUME +
            c["trend_score"]     * W_TREND +
            c["rs_score"]        * W_REL_STR +
            c["narr_score"]      * W_NARRATIVE +
            c["vol_q_score"]     * W_VOLATILITY +
            c["intraday_score"]  * W_INTRADAY +
            c["btc_beta_score"]  * W_BTC_BETA,
            1,
        )

    scored.sort(key=lambda x: x["composite"], reverse=True)

    # ── Select final list ─────────────────────────────────────────────────────
    pinned_entries = [c for c in scored if c["symbol"] in PINNED]
    other_entries  = [c for c in scored if c["symbol"] not in PINNED]

    found_pinned = {c["symbol"] for c in pinned_entries}
    for sym in PINNED:
        if sym not in found_pinned:
            pinned_entries.append({
                "symbol": sym, "volume": 0, "change_pct": 0,
                "vol_score": 100, "trend_score": 50, "rs_raw": None,
                "rs_score": 50, "narr_score": 10, "vol_q_score": 50,
                "intraday_score": 50, "btc_beta_score": 50,
                "atr_pct": None, "composite": 75.0,
            })

    remaining  = TARGET_SIZE - len(pinned_entries)
    final_raw  = pinned_entries + other_entries[:remaining]

    # ── Annotate with display fields ──────────────────────────────────────────
    final = []
    for c in final_raw:
        sym = c["symbol"]
        final.append({
            "symbol":              sym,
            "name":                _coin_name(sym),
            "pinned":              sym in PINNED,
            "composite_score":     c["composite"],
            "narrative":           get_narrative_for_coin(sym),
            "is_narrative_leader": _is_leader(sym),
            "trade_type":          "both",
            "volume_m":            round(c["volume"] / 1e6, 1),
            "trend_score":         round(c["trend_score"], 1),
            "rs_score":            round(c["rs_score"], 1),
            "narr_score":          round(c["narr_score"], 1),
            "vol_q_score":         round(c["vol_q_score"], 1),
            "intraday_score":      round(c["intraday_score"], 1),
            "btc_beta_score":      round(c["btc_beta_score"], 1),
            "atr_pct":             round(c["atr_pct"], 2) if c["atr_pct"] else None,
            "change_pct":          c["change_pct"],
        })

    logger.info(
        f"Stage 2 complete — {len(final)} coins selected. "
        f"Pinned: {sorted(found_pinned | PINNED)}. "
        f"Top non-pinned: {[c['symbol'] for c in other_entries[:remaining]]}"
    )

    # ── Persist history (drives consistency metric) ───────────────────────────
    run_date = datetime.now(timezone.utc)
    try:
        with get_session() as s:
            for rank, c in enumerate(final, 1):
                s.add(WatchlistScreenHistory(
                    run_date        = run_date,
                    symbol          = c["symbol"],
                    rank            = rank,
                    composite_score = c["composite_score"],
                ))
        logger.info(f"Screen history saved — {len(final)} records for {run_date.date()}")
    except Exception as e:
        logger.warning(f"Failed to save screen history: {e}")

    return final


# ── Standalone runner ─────────────────────────────────────────────────────────

async def _main():
    coins = await run_stage2()
    print(f"\n{'═'*90}")
    print(f"  Final watchlist — {len(coins)} coins")
    print(f"{'═'*90}")
    print(f"  {'#':<4} {'Symbol':<8} {'Name':<18} {'Score':>6}  "
          f"{'Vol$M':>7}  {'Trend':>6}  {'RS':>6}  {'Narr':>5}  "
          f"{'VolQ':>6}  {'Intra':>6}  {'Beta':>6}  Flags")
    print(f"  {'─'*86}")
    for i, c in enumerate(coins, 1):
        flags = []
        if c["pinned"]:              flags.append("📌 pinned")
        if c["is_narrative_leader"]: flags.append("★ leader")
        print(
            f"  {i:<4} {c['symbol']:<8} {c['name']:<18} {c['composite_score']:>6.1f}  "
            f"{c['volume_m']:>7.0f}  {c['trend_score']:>6.1f}  {c['rs_score']:>6.1f}  "
            f"{c['narr_score']:>5.1f}  {c['vol_q_score']:>6.1f}  "
            f"{c['intraday_score']:>6.1f}  {c['btc_beta_score']:>6.1f}  {' '.join(flags)}"
        )


if __name__ == "__main__":
    asyncio.run(_main())
