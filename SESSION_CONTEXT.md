# Session Context — CryptoTrada Project

**Last Updated:** 2026-08-09
**Current Phase:** Phase 3 Complete, Ready for Phase 4

---

## Project Overview
CryptoTrada is a cryptocurrency trading intelligence platform with:
- **P2P Market Monitoring** (USDT/SDG on Binance P2P)
- **Spot Auto-Trader** (paper trading bot with enhanced entry/exit/risk logic)
- **XRP Swing Trader** (specialist 3-layer macro/technical/trigger engine)
- **Web Dashboard** (FastAPI + Vue 3 SPA)
- **Telegram Bot** for remote control

---

## Completed Phases

### ✅ Phase 1: Remove Capitulation Bot (Complete Removal)
**Files Deleted (15):**
- `spot/capitulation_bot.py`, `spot/patterns_capitulation.py`, `spot/signal_capitulation.py`
- `web/routes/capitulation.py`
- `frontend/src/components/CapitulationPage.vue`, `frontend/src/components/trading/CapitulationPanel.vue`
- `scripts/backtest_capitulation.py`, `scripts/backtest_causal_regime.py`, `scripts/backtest_regime.py`, `scripts/backtest_4h.py`, `scripts/backtest_final.py`, `scripts/backtest_timeouts.py`, `scripts/edge_validation.py`
- `scripts/check_parity.py`, `scripts/check_restart_recovery.py`

**Files Modified (11):**
- `data/models.py` — Removed `CapitulationTrade` model
- `data/database.py` — Removed capitulation migration columns
- `main.py` — Removed import and scheduler job
- `web/app.py` — Removed capitulation router
- `frontend/src/App.vue` — Removed CapitulationPage import/usage
- `spot/auto_trader.py` — Removed `_capitulation_conflict()` function and its call
- `web/routes/spot.py` — Removed `/capitulation/signals` endpoint
- `frontend/src/locales/en.js` — Removed capitulation tab key and `cap` locale section
- `frontend/src/locales/ar.js` — Removed capitulation tab key and `cap` locale section
- `frontend/src/components/trading/XRPSwing.vue` — Updated "capitulation bounce" → "bounce"
- `spot/xrp_swing.py` — Updated "capitulation bounce" → "bounce from extreme fear"

**State File Removed:** `data/cap_state.json`

---

### ✅ Phase 2: Enhance Auto-Trader (`spot/auto_trader.py`)

#### Exit Enhancements (Highest Impact) ✅
- **ATR-based trailing from entry** — Arms when gain ≥ 1.5×ATR, trails at ATR×1.0
- **Partial takes at 1R, 2R, 3R with scaling trail:**
  - TP1: 30% at 1R → move SL to breakeven, arm trailing at ATR×1.0
  - TP2: 30% at 2R → tighten trail to ATR×0.5
  - TP3: 40% at 3R → trail at ATR×0.3
- **Volatility-adjusted timeout** — Exit if |price-entry| < 0.5×ATR for 4 hours
- **Time-based exit for stagnant positions** — Max hold time = ATR × 10 hours

#### Entry Enhancements ✅
- **Volume-confirmed breakout** — Require `vol_ratio ≥ 1.5` on entry candle
- **Graduated BTC regime gate** — Position size ∝ distance above SMA50 (0% at SMA50, 100% at 10% above)
- **Multi-timeframe confirmation** — Require 1H + 4H EMA20 alignment

#### Risk Management ✅
- **Correlation-adjusted position limits** — Cluster by narrative/sector (max 3 per cluster)
- **Portfolio-level circuit breaker** — Pause all if portfolio drawdown > 10%
- **Kelly/volatility-based sizing** — Kelly formula with volatility adjustment, capped at 25%

**Files Modified:**
- `spot/auto_trader.py` — Core logic (all enhancements)
- `spot/positions.py` — Added `update_trailing_pct()` function

---

### ✅ Phase 3: Enhance XRP Swing (`spot/xrp_swing.py`)

#### Entry Enhancements ✅
- **Dynamic resistance targets** — ATR projections (`entry + ATR×N`) capped by static resistance levels
- **Conviction-based sizing** — Setup A (100%) > Setup B (75%) > Setup C (50%) via `XRP_CONVICTION_MULT`
- **Earlier auto-entry** — Staged entry: 20% at SETUP_FORMING, 40% at ENTRY_READY, 40% at confirmation
- **ATR calculation** — Added `_atr()` helper for 4H candles

#### Exit Enhancements ✅
- **ATR-based trailing from entry** — Arms when gain ≥ 1.5×ATR (not post-TP2)
- **Dynamic TP levels** — TP1=entry+ATR×1, TP2=entry+ATR×2, TP3=entry+ATR×3 (capped by static resistance)
- **Regime-aware trailing** — Wider trail in chop (ATR×1.5), tighter in trend (ATR×0.5)
- **TP3 support** — Added third take-profit level with 40% position size
- **Trailing arms at 1.5×ATR** — Independent of TP1, triggers from entry

#### Auto-Mode Improvements ✅
- **Staged auto-entry** — 20% at ENTRY_READY, 40% at 0.5×ATR gain, 40% at 1.0×ATR gain
- **Regime-based cooldown** — 24h in bear, 6h in bull (`XRP_COOLDOWN_BEAR_HOURS` / `XRP_COOLDOWN_BULL_HOURS`)
- **Auto-stage tracking** — Tracks stage 1/2/3 in state file, adds stages when price moves favorably
- **TP3 support** — Added third take-profit with 40% position closure
- **ATR-based stop** — Stop = entry - ATR×1.5 (aligned with auto-trader)

**Files Modified:**
- `spot/xrp_swing.py` — Core logic (all enhancements)
- `data/models.py` — Added `tp3_price`, `tp3_hit_at`, `tp3_pnl_usd` to `XRPSwingTrade` model

---

## Current State

### Test Results
- **168 tests passing** (all test suites)
- No failing tests

### Key Configuration (in `spot/auto_trader.py`)
```python
# Exit Enhancements
ATR_TRAIL_ARM_K      = 1.5    # arm trailing when gain ≥ 1.5×ATR
ATR_TRAIL_K_TP1      = 1.0    # trail after TP1
ATR_TRAIL_K_TP2      = 0.5    # trail after TP2
ATR_TRAIL_K_TP3      = 0.3    # trail after TP3
TP1_R_MULT           = 1.0    # TP1 at 1R
TP2_R_MULT           = 2.0    # TP2 at 2R
TP3_R_MULT           = 3.0    # TP3 at 3R
TP1_SIZE_PCT         = 0.30   # 30% at TP1
TP2_SIZE_PCT         = 0.30   # 30% at TP2
TP3_SIZE_PCT         = 0.40   # 40% at TP3
VOL_TIMEOUT_ATR_K    = 0.5    # stagnation threshold
VOL_TIMEOUT_HOURS    = 4      # hours before timeout
MAX_HOLD_ATR_MULT    = 10.0   # max hold = ATR × 10 hours

# Entry Enhancements
VOL_RATIO_MIN        = 1.5    # volume breakout confirmation
BTC_SMA50_GRADUATED  = True   # graduated BTC regime gate
BTC_SMA50_MIN_DIST   = 0.0    # min distance above SMA50
BTC_SMA50_MAX_DIST   = 0.10   # max distance for full size
MULTI_TF_CONFIRM     = True   # 1H + 4H alignment

# Risk Management
CORRELATION_CLUSTER_LIMIT = 3     # max per narrative cluster
PORTFOLIO_DD_LIMIT_PCT    = 0.10  # 10% portfolio DD circuit breaker
KELLY_SIZING_ENABLED      = True  # Kelly/volatility sizing
KELLY_WIN_RATE            = 0.55
KELLY_WIN_LOSS_RATIO      = 1.5
KELLY_MAX_FRACTION        = 0.25
```

### Key Configuration (in `spot/xrp_swing.py`)
```python
# Entry Enhancements
XRP_ATR_PERIOD          = 14           # ATR period for 4H candles
XRP_TP_ATR_MULT         = [1.0, 2.0, 3.0]  # TP multipliers
XRP_CONVICTION_MULT     = {"A": 1.0, "B": 0.75, "C": 0.5}
XRP_EARLY_ENTRY_PCT     = 0.20         # 20% at SETUP_FORMING
XRP_AUTO_STAGE_PCTS     = [0.20, 0.40, 0.40]  # Staged entry

# Exit Enhancements
XRP_TRAIL_ARM_ATR       = 1.5          # Arm trailing at 1.5×ATR gain
XRP_TRAIL_ATR_BASE      = 1.0          # Base trail = ATR × 1.0
XRP_TRAIL_CHOP_MULT     = 1.5          # Chop regime: wider trail
XRP_TRAIL_TREND_MULT    = 0.5          # Trend regime: tighter trail

# Auto-Mode
XRP_COOLDOWN_BEAR_HOURS = 24           # Bear regime cooldown
XRP_COOLDOWN_BULL_HOURS = 6            # Bull regime cooldown
XRP_AUTO_STAGE_PCTS     = [0.20, 0.40, 0.40]  # Staged entry
```

---

## Next Steps

### 🔄 Phase 4: Unified Trading Mode System
- Create `TradingMode` enum and manager (`spot/trading_modes.py`)
- Strategy interface with `on_entry()`, `on_exit()`, `on_tick()`
- Per-mode config in `config.py` and `.env`
- Frontend mode selector in dashboard
- Single `run_trading_cycle()` job dispatching to active strategies

### 🔄 Phase 5: Testing & Validation
- Walk-forward with parameter sweep
- Monte Carlo simulation
- Out-of-sample test on recent 3 months
- Paper trading shadow mode (2 weeks)

---

## Key Files for Future Reference

| File | Purpose |
|------|---------|
| `spot/auto_trader.py` | Main auto-trader logic (enhanced) |
| `spot/positions.py` | Position management helpers |
| `spot/xrp_swing.py` | XRP swing trader (enhanced) |
| `main.py` | Entry point, scheduler |
| `web/app.py` | FastAPI app factory |
| `web/routes/` | API route modules |
| `frontend/src/App.vue` | Main Vue component |
| `frontend/src/components/trading/` | Trading UI components |
| `data/models.py` | SQLAlchemy models |
| `data/database.py` | DB initialization & migrations |
| `REFACTORING_PLAN.md` | Full refactoring roadmap |

---

## Development Commands
```bash
# Run tests
python3 -m pytest tests/ -v

# Run main app
python3 main.py

# Frontend dev (separate terminal)
cd frontend && npm run dev

# Check Python syntax
python3 -m py_compile spot/auto_trader.py spot/positions.py spot/xrp_swing.py
```

---

## Notes for Next Session
1. **Phase 4 is next** — Create Unified Trading Mode System in `spot/trading_modes.py`
2. All tests pass (168) — safe to proceed with modifications
3. Both auto-trader and XRP swing now have sophisticated exit logic (partial takes, ATR trailing, timeouts)
4. Both have staged entry logic with conviction-based sizing
5. Risk management includes correlation clustering, portfolio DD breaker, Kelly sizing
5. XRP Swing now has TP3, regime-aware trailing, and staged auto-entry