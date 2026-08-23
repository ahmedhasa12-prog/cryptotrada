# Refactoring Plan: Remove Capitulation Bot & Enhance Auto-Trader + XRP Swing

## Phase 1: Remove Capitulation Bot (Complete Removal)

### Files to Delete
- `spot/capitulation_bot.py` - Main capitulation bot logic
- `spot/patterns_capitulation.py` - Pattern detection
- `spot/signal_capitulation.py` - Signal monitor
- `web/routes/capitulation.py` - API routes
- `frontend/src/components/CapitulationPage.vue` - Frontend component
- `scripts/backtest_capitulation.py` - Backtest script
- `scripts/backtest_causal_regime.py` - Related backtest
- `scripts/backtest_regime.py` - Related backtest
- `scripts/backtest_4h.py` - Related backtest
- `scripts/backtest_final.py` - Related backtest
- `scripts/backtest_timeouts.py` - Related backtest
- `scripts/edge_validation.py` - Related backtest

### Files to Modify (Remove References)
- `main.py` - Remove imports and scheduler jobs for capitulation bot
- `data/models.py` - Remove `CapitulationTrade` model
- `data/database.py` - Remove migrations for capitulation tables
- `web/app.py` - Remove capitulation router import
- `frontend/src/App.vue` - Remove CapitulationPage import and usage
- `frontend/src/components/trading/SignalPanel.vue` - Check for capitulation references
- `tests/` - Remove any capitulation-related tests

### Database Migrations
- Drop `capitulation_trades` table
- Drop `cap_state.json` state file references

---

## Phase 2: Enhance Auto-Trader (`spot/auto_trader.py`)

### Entry Enhancements
1. **Volume-confirmed breakout entry** - Require `vol_ratio_closed ≥ 1.5` on entry candle
2. **Graduated BTC regime gate** - Position size ∝ distance above SMA50
3. **Catalyst awareness** - Integrate news/unlock/events into hotness scoring
4. **Multi-timeframe confirmation** - Require 1H + 4H alignment

### Exit Enhancements (Highest Impact)
1. **ATR-based trailing from entry** (not post-TP1)
   - Arm trailing when gain ≥ 1.5×ATR
   - Trail distance = ATR × 1.0 (configurable)
2. **Partial takes at 1R, 2R, 3R** with scaling trail
   - TP1: 30% at 1R → move SL to BE
   - TP2: 30% at 2R → tighten trail to 0.5×ATR
   - TP3: 40% at 3R → trail at 0.3×ATR
3. **Volatility-adjusted timeout** - Exit if |price-entry| < 0.5×ATR for 4 hours
4. **Time-based exit for stagnant positions** - Max hold time based on ATR

### Risk Management
1. **Correlation-adjusted position limits** - Cluster by narrative/sector
2. **Portfolio-level circuit breaker** - Pause all if correlated drawdown > threshold
3. **Kelly/volatility-based sizing** - Replace fixed risk budget

---

## Phase 3: Enhance XRP Swing (`spot/xrp_swing.py`)

### Entry Enhancements
1. **Dynamic resistance targets** - ATR projections instead of static levels
2. **Conviction-based sizing** - Setup A (high) > Setup B (med) > Setup C (breakout)
3. **Earlier auto-entry** - Allow scaling in at SETUP_FORMING with small size

### Exit Enhancements
1. **ATR-based trailing from entry** (not post-TP2)
2. **Dynamic TP levels** - `entry + ATR×N` capped by static resistance
3. **Regime-aware trailing** - Wider trail in chop, tighter in trend

### Auto-Mode Improvements
1. **Staged auto-entry** - 20% at SETUP_FORMING, 40% at ENTRY_READY, 40% at confirmation
2. **Cooldown based on regime** - Longer in bear, shorter in bull
3. **Position management dashboard** - Better visualization of staged entries

---

## Phase 4: Unified Trading Mode System

### Concept
Create a `TradingMode` enum and manager that allows selecting/running different strategies:

```python
class TradingMode(str, Enum):
    AUTO_TREND = "auto_trend"      # Enhanced auto-trader (multi-coin, trend-following)
    XRP_SWING = "xrp_swing"        # XRP specialist (3-layer macro/tech/trigger)
    P2P_ONLY = "p2p_only"          # P2P market making only
    MANUAL = "manual"              # Insights only, no auto-execution
```

### Implementation
1. **Mode Manager** - `spot/trading_modes.py` with:
   - `set_mode(mode: TradingMode)`
   - `get_active_strategies() -> list[Strategy]`
   - `run_cycle()` - dispatches to active strategies
2. **Strategy Interface** - Base class with `on_entry()`, `on_exit()`, `on_tick()`
3. **Configuration** - Per-mode config in `config.py` and `.env`
4. **Frontend** - Mode selector in dashboard, per-mode settings panels

### Scheduler Integration
- Single `run_trading_cycle()` job that calls active mode's cycle
- Mode-specific sub-jobs (e.g., XRP swing 15-min eval, auto-trader 5-min)

---

## Phase 5: Testing & Validation

### Backtest Framework
1. **Walk-forward with parameter sweep** for each strategy
2. **Monte Carlo simulation** for confidence intervals
3. **Out-of-sample test** on recent 3 months
4. **Paper trading shadow mode** - run enhanced logic alongside current for 2 weeks

### Metrics to Track
- Net expectancy per trade
- Win rate
- Profit factor
- Max drawdown
- Sharpe/Sortino ratio
- Average hold time
- MFE/MAE efficiency

---

## Execution Order

1. **Week 1**: Phase 1 (Removal) - Clean slate
2. **Week 2**: Phase 2 (Auto-Trader Enhancement) - Core profit engine
3. **Week 3**: Phase 3 (XRP Swing Enhancement) - Specialist engine
4. **Week 4**: Phase 4 (Mode System) - Unified interface
5. **Week 5**: Phase 5 (Testing) - Validation before live

---

## Risk Mitigation

- **Git branch per phase** - Easy rollback
- **Feature flags** - Toggle enhancements without code removal
- **Shadow mode** - Run new logic in parallel, compare signals
- **Comprehensive tests** - Unit + integration for each change