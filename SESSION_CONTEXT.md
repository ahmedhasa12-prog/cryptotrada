# Session Context — CryptoTrada Project

**Last Updated:** 2026-09-16
**Current Phase:** Phase 4 (Agent Framework) — Core built, needs completion
**See `HANDOFF.md` for the canonical handoff document**

---

## Project Overview
CryptoTrada is a cryptocurrency trading intelligence platform:
- **P2P Market Monitoring** (USDT/SDG on Binance P2P)
- **Spot Auto-Trader** (paper trading bot with enhanced entry/exit/risk logic)
- **XRP Swing Trader** (specialist 3-layer macro/technical/trigger engine)
- **Web Dashboard** (FastAPI + Vue 3 SPA)
- **Telegram Bot** for remote control

---

## Test Results
- **234 tests passing** (all test suites)
- 13635 deprecation warnings (`datetime.utcnow()` → `datetime.now(datetime.UTC)` migration needed)
- No test failures

## Live Platform
- Running at `http://localhost:8000`
- All 5 agents STOPPED, enabled: false
- Platform mode: manual
- AUTO_TREND total_pnl_usd: -17.16
- Activity feed: 3 trades (SOL open at $103.5, XRP close at -1.72%, XRP open at $1.1085)

---

## Completed Phases

### ✅ Phase 1: Remove Capitulation Bot
- 15 files deleted, 11 files modified
- See `HANDOFF.md` for full detail

### ✅ Phase 2: Enhance Auto-Trader
- ATR trailing, partial takes (1R/2R/3R), volatility timeout, Kelly sizing
- See `HANDOFF.md` for full detail

### ✅ Phase 3: Enhance XRP Swing
- ATR-based dynamic TP, conviction-based sizing, staged entry, regime-aware trailing
- See `HANDOFF.md` for full detail

### ✅ Phase 4: Agent Framework (Core Built)
- `spot/trading_modes.py` — BaseAgent ABC, AutoTrendAgent, XRPSwingAgent, SOLSwingAgent, P2PMarketAgent, ManualAgent, AgentRegistry, EventBus (821 lines)
- REST API at `/api/agents/` — start/stop/pause/resume/config endpoints
- `data/agent_configs.json` — Per-agent config persistence
- 12 tests were broken by partial wiring (need verification)

### ✅ Rate-Limit Resilience
- Exponential backoff on 429s, checkpoint save/load, auto-retry every 30s
- Real Binance OHLCV everywhere

---

## Key Configurations

### Auto-Trader (`spot/auto_trader.py`)
- ATR_TRAIL_ARM_K=1.5, TP1=1R/30%, TP2=2R/30%, TP3=3R/40%
- Vol ratio min=1.5, BTC SMA50 graduated gate, multi-TF confirmation
- Kelly sizing enabled, portfolio DD limit=10%, correlation cluster limit=3

### XRP Swing (`spot/xrp_swing.py`)
- XRP_ATR_PERIOD=14, TP multipliers=[1.0, 2.0, 3.0]
- Conviction mult: A=1.0, B=0.75, C=0.5
- Staged entry: 20%/40%/40%, cooldowns: 24h bear / 6h bull

### Agent Config (`data/agent_configs.json`)
- All agents `enabled: false`
- Strategy owners: `original_inkling_2026` (auto_trend), `adopted_phase3` (xrp_swing), `original_breakout` (sol_swing)

---

## Next Steps

### 🔄 Phase 4 Completion
- Fix concrete agent wiring in `trading_modes.py`
- Verify and fix the 12 broken tests from the strategy ABC addition
- Test agent start/stop/pause/resume end-to-end via API
- Verify `SOLSwingAgent` wiring (references `agent3_sol_swing.py`)

### 🔄 Phase 5: Testing & Validation
- Walk-forward with parameter sweep
- Monte Carlo simulation
- Out-of-sample test on recent 3 months
- Paper trading shadow mode (2 weeks)

---

## Development Commands
```bash
python3 -m pytest tests/ -q          # 234 tests should pass
python3 main.py                      # Start platform on :8000
cd frontend && npm run dev           # Frontend dev server
curl http://localhost:8000/api/status # Verify platform is live
```
