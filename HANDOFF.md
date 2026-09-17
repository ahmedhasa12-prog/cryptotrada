# 🔄 CryptoTrada — Session Handoff Protocol

**This is the FIRST document any new session should read.** Read it completely before doing anything else.

**Last verified:** 2026-09-17
**Current Phase:** Phase 4 — Agent framework complete and tested
**Project:** CryptoTrada — Cryptocurrency Trading Intelligence Platform
**Owner's goal:** Autonomous paper-trading agents that close trades with real, repeatable profits and a consistent strategy, with auto-resume on rate limits.
**Owner's style:** Full freedom to change anything, but wants small verified steps. Run tests after every change.

---

## ⚡ QUICK START (New Session)

```bash
# 1. Verify the project runs
cd /Users/ahmedabdelwahid/projects/cryptotrada
python3 -m pytest tests/ -q          # Should show 250 passed
python3 main.py &                     # Start the platform on :8000
curl http://localhost:8000/api/status # Should return JSON

# 2. Read THIS file
# 3. Check the live platform: http://localhost:8000
# 4. Check git log: git --no-pager log --oneline -10
```

---

## 🏗️ Project Architecture

| Layer | Tech |
|-------|------|
| Backend | Python 3.14, FastAPI, SQLAlchemy 2.0, SQLite |
| Frontend | Vue 3, Vite, Pinia, vue-router, vue-i18n (EN/AR + RTL) |
| Trading | Binance API (paper/live), real OHLCV + WebSocket prices |
| Agents | Custom Python agent framework (BaseAgent → concrete agents) |
| Scheduling | APScheduler (AsyncIOScheduler) |

### Core Modules
- `main.py` — Entry point, scheduler setup, lifespan management
- `spot/auto_trader.py` — Enhanced spot auto-trader (ATR trailing, partial takes, Kelly sizing)
- `spot/xrp_swing.py` — XRP swing specialist (3-layer engine, staged entry, TP3)
- `spot/trading_modes.py` — **Agent framework** (BaseAgent, AutoTrendAgent, XRPSwingAgent, SOLSwingAgent, P2PMarketAgent, ManualAgent + AgentRegistry + EventBus) — 821 lines
- `spot/positions.py` — Position management helpers
- `spot/streamer.py` — Price streaming via WebSocket
- `data/models.py` — SQLAlchemy models (SpotTrade, XRPSwingTrade, etc.)
- `data/database.py` — DB init & migrations
- `web/app.py` — FastAPI app factory with middleware & routers
- `web/routes/` — API routes (agents, spot, p2p, stream, analytics, journal, xrp_swing)
- `config.py` — Environment-based configuration
- `frontend/src/` — Vue 3 SPA with agent cards, dashboard, P2P, Intel, Journal views

### Live Platform
- **Local:** `http://localhost:8000` (FastAPI serves built Vue SPA)
- **Domain:** `https://cryptotrada.com` is a marketing page only (redirects to `/lander`)
- **API prefix:** `/api/` (e.g., `/api/agents/status`, `/api/spot/bot/status`)
- **Agent API:** `/api/agents/` with full CRUD (start/stop/pause/resume/config)

---

## 📊 Current State (VERIFY BEFORE PROCEEDING)

### Test Suite
```
python3 -m pytest tests/ -q
# Expected: 250 passed, 15052 warnings (datetime.utcnow deprecation)
```

### Agent Status (via API)
```bash
curl -s http://localhost:8000/api/agents/status | python3 -m json.tool
# All 5 agents: STOPPED, enabled: false
# AUTO_TREND total_pnl_usd: -17.16
```

### Platform Mode
```bash
curl -s http://localhost:8000/api/status
# {"mode":"manual","availability":"online","trading_mode":"manual"}
```

### Config Files
- `.env` — API keys, operating mode, P2P config, OpenRouter key
- `data/agent_configs.json` — Per-agent enabled/disabled + config params
- `data/trading.db` — SQLite database with all trade data

---

## ✅ Completed Phases

### Phase 1: Remove Capitulation Bot ✅
- Deleted 15 files, modified 11 files
- Removed `CapitulationTrade` model, capitulation routes, frontend components
- All references scrubbed from codebase

### Phase 2: Enhance Auto-Trader ✅
- ATR-based trailing from entry (arm at 1.5×ATR, trail at 1.0×ATR)
- Partial takes: TP1=30%@1R, TP2=30%@2R, TP3=40%@3R with scaling trail
- Volatility-adjusted timeout (0.5×ATR for 4 hours)
- Volume-confirmed breakout (vol_ratio ≥ 1.5), graduated BTC SMA50 gate, multi-TF confirmation
- Kelly/volatility sizing, correlation clustering (max 3/cluster), portfolio DD breaker (10%)

### Phase 3: Enhance XRP Swing ✅
- ATR-based dynamic TP levels (1×, 2×, 3× ATR, capped by resistance)
- Conviction-based sizing (A=100%, B=75%, C=50%)
- Staged auto-entry (20%/40%/40%), regime-based cooldowns (24h bear / 6h bull)
- TP3 support, regime-aware trailing, ATR-based stop

### Phase 4: Agent Framework ✅ (COMPLETE)
- `BaseAgent` ABC with lifecycle: STOPPED→STARTING→RUNNING→PAUSED→STOPPING→ERROR
- Concrete agents: `AutoTrendAgent`, `XRPSwingAgent`, `SOLSwingAgent`, `P2PMarketAgent`, `ManualAgent`
- `AgentRegistry` with start/stop/pause/resume/config + persistence to `data/agent_configs.json`
- `EventBus` for inter-agent communication
- `AgentConfig`, `AgentMetrics`, `AgentStatus` dataclasses
- REST API at `/api/agents/` with full CRUD
- **All 5 agents instantiate and run correctly** — verified via API and integration tests
- **Bug fixed**: `update_agent_config` now properly updates top-level `AgentConfig` fields
- **Bug fixed**: `SOLSwingAgent` constructor cleaned up (removed unused `strategy` param)
- **Refactored**: `agent3_sol_swing.py` moved to `spot/sol_swing.py`
- **16 new integration tests** added in `tests/test_trading_modes.py`

### Rate-Limit Resilience ✅
- Exponential backoff on 429s (1.5s base, 60s cap)
- Checkpoint save/load for state persistence
- Auto-retry job scheduled every 30s (`retry_failed_fetches`)
- Real Binance OHLCV everywhere (no synthetic/fallback data)

### UI/UX ✅
- Agent-first dashboard with AgentCard components (state badges, metrics, strategy tags)
- Strategy owner badges: `original_inkling_2026`, `adopted_phase3`, `original_breakout`
- "REAL DATA ONLY" tags on all agent cards
- Activity feed showing real trade events
- Dark/light theming, full RTL support (Arabi)
- 6 views: Dashboard, Agents, P2P, Intel, Journal, Settings

---

## 🔴 Known Issues & Gotchas

### Phase 4 Agent Wiring ✅ (RESOLVED)
- All concrete agent wiring is complete and verified
- Agent lifecycle works end-to-end via API (start/stop/pause/resume)
- 250 tests pass including 16 new agent integration tests
- **No remaining wiring issues**

### 2. datetime.utcnow() Deprecation
- 13635 deprecation warnings across test suite
- `spot/xrp_swing.py` uses `datetime.utcnow()` in multiple places
- Should migrate to `datetime.now(datetime.UTC)` — but this is low priority (doesn't break anything)

### 3. Agent Configs Are All Disabled
- `data/agent_configs.json` has all agents `enabled: false`
- Platform starts in `manual` mode — no auto-trading happens
- To enable agents, update `agent_configs.json` or use the API: `POST /api/agents/{type}/start`

### 4. Dead Orphan Files
- `solana_trader.py` at project root — dead code, do NOT touch unless asked
- `agent1_swing_explorer.py` at project root — legacy/experimental (imports now from `spot.sol_swing`)

### 5. .env Contains Real API Keys
- Binance API key and secret are in `.env`
- OpenRouter API key is in `.env`
- **Never commit `.env`** — it's in `.gitignore`

---

## 📋 Decision Log (Why Things Are This Way)

| Decision | Rationale |
|----------|-----------|
| Agent framework over simple scheduler | Independent agent lifecycle allows pause/resume/config per strategy |
| `data/agent_configs.json` for config persistence | Survives restarts, editable via API, no env vars needed |
| `BaseAgent` ABC instead of plain functions | Enforces consistent lifecycle, enables registry pattern |
| Manual mode default | Safety — no auto-trading until explicitly enabled |
| Real Binance OHLCV only | No synthetic data in production — trust but verify |
| `SOLSwingAgent` always enabled by default | Owner wants SOL trading autonomous |
| `XRP_SWING` auto mode in `agent_configs.json` | `auto_enabled: true` in config, but agent itself is disabled |
| `spot/trading_modes.py` is the unified module | Contains agents, registry, event bus, strategy context, trading mode enum |

---

## 🎯 Current Goal (DSH)

The project has a DSH goal set. Check with `get_goal` for the exact objective.

**Working protocol (owner-approved):**
1. Create a DSH goal immediately for any long-running objective
2. One small task per round — after each, run tests and update this file
3. Baseline first: run tests, confirm app boots, then touch strategy code
4. Commit small checkpoints: `git commit -m "brief description"`

---

## 📁 Key Files Map

### Backend (Python)
| File | Lines | Purpose |
|------|-------|---------|
| `main.py` | 355 | Entry point, scheduler, lifespan |
| `spot/trading_modes.py` | 821 | Agent framework (BaseAgent, agents, registry, event bus) |
| `spot/sol_swing.py` | 71 | SOL swing strategy (moved from root) |
| `spot/__init__.py` | 33 | Package exports |
| `spot/auto_trader.py` | ~900 | Enhanced spot auto-trader logic |
| `spot/xrp_swing.py` | ~850 | XRP swing specialist logic |
| `spot/positions.py` | ~200 | Position management helpers |
| `spot/streamer.py` | ~200 | WebSocket price streaming |
| `web/app.py` | 80 | FastAPI app factory |
| `web/routes/agents.py` | 373 | Agent CRUD API |
| `web/routes/spot.py` | ~300 | Spot trading API |
| `web/routes/p2p.py` | ~200 | P2P market API |
| `config.py` | 100 | Environment-based config |
| `data/models.py` | ~300 | SQLAlchemy models |
| `data/database.py` | ~200 | DB init & migrations |

### Frontend (Vue 3)
| File | Purpose |
|------|---------|
| `frontend/src/App.vue` | Root component with SideNav, Header, router-view |
| `frontend/src/router/index.ts` | Routes: /, /agents, /agents/:type, /p2p, /intel, /journal, /settings |
| `frontend/src/stores/platform.js` | Pinia store — all API calls, agent actions, alerts |
| `frontend/src/views/DashboardView.vue` | Main dashboard with agent cards + activity feed |
| `frontend/src/views/agents/AgentsView.vue` | Agent management grid |
| `frontend/src/views/agents/AgentDetailView.vue` | Individual agent detail |
| `frontend/src/components/agent/AgentCard.vue` | Reusable agent card with metrics + actions |
| `frontend/src/components/layout/SideNav.vue` | Navigation sidebar |
| `frontend/src/components/layout/AppHeader.vue` | Top header bar |

### Config & Data
| File | Purpose |
|------|---------|
| `.env` | API keys, operating mode, P2P config |
| `.env.example` | Template for env vars |
| `data/agent_configs.json` | Per-agent enabled/disabled + config params |
| `data/trading.db` | SQLite database |
| `data/agent_state.json` | Agent runtime state |

---

## 🛠️ Development Commands

```bash
# Run all tests
python3 -m pytest tests/ -q

# Run specific test file
python3 -m pytest tests/test_xrp_swing_strategy.py -v

# Start the platform
python3 main.py

# Frontend dev server (separate terminal)
cd frontend && npm run dev

# Check Python syntax
python3 -m py_compile spot/auto_trader.py spot/positions.py spot/xrp_swing.py spot/trading_modes.py

# Check agent API
curl -s http://localhost:8000/api/agents/status | python3 -m json.tool

# Check platform status
curl -s http://localhost:8000/api/status

# Check git history
git --no-pager log --oneline -15

# Check what's changed
git --no-pager diff --stat
```

---

## 📝 Session Log (Append Each Round)

Format: `[YYYY-MM-DD (model)] What happened. What's next.`

- 2025-09-12 (kimi-k3): Baseline 234 tests pass; boot confirmed; Phase 3 complete; added rate-limit resilience
- 2025-09-13 (nvidia/nemotron-3-ultra-550b): Added Strategy interface to trading_modes.py; 12 tests broken by partial agent wiring
- 2025-09-13 (groq/openai/gpt-oss-120b): Confirmed same state
- 2025-09-13 (openrouter/z-ai/glm-5.2): Confirmed same state
- 2025-09-13 (openai/inkling): Added clean review + auto-retry; user said "let's explore enhancements and efficiency!"
- 2025-09-16 (n/a): Phase 4 agent framework completed (BaseAgent, AutoTrendAgent, XRPSwingAgent, SOLSwingAgent, P2PMarketAgent, ManualAgent, AgentRegistry, EventBus); REST API at /api/agents/; UI redesigned with agent cards, strategy badges, backtest metrics
- 2025-09-17 (n/a): Phase 4 cleanup complete — moved agent3_sol_swing.py to spot/sol_swing.py, fixed SOLSwingAgent constructor, fixed update_agent_config bug, added 16 integration tests (250 total), created HANDOFF.md as canonical session handoff, fixed agent lifecycle via API verified end-to-end

---

## 🔗 Related Files

- `REFACTORING_PLAN.md` — Full roadmap (Phases 1-5, still relevant as reference)
- `UI_REBUILD_BRIEF.md` — Frontend rebuild brief (Phase 3 components still needed)
- `UI_REDESIGN_PLAN.md` — Design tokens, RTL groundwork, old redesign plan
- `binance_trading_platform_PRD.md` — Product requirements document (30KB)

---

## 🧠 How to Use This File

1. **New session starts** → Read this file completely → Run the QUICK START commands → Verify state
2. **After each round** → Update the Session Log section → Update any changed state → Commit
3. **When a phase completes** → Add it to Completed Phases → Update the test count → Remove from Next Steps
4. **When a bug is found** → Add it to Known Issues with the fix applied
5. **When a decision is made** → Add it to the Decision Log with rationale

**This file is the project's memory. Keep it current.**
