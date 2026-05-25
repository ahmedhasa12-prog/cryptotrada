# 🏦 Binance Trading Intelligence Platform
## Product Requirements Document (PRD)
### For Claude Code Implementation

---

## 1. PROJECT OVERVIEW

### 1.1 Vision
Build a personal multi-asset trading intelligence platform that combines:
- **P2P USDT/SDG trading automation** on Binance (primary income engine)
- **Spot trading intelligence** for XRP and SOL (growth/exploration layer)
- **Unified risk management** across both trading domains

### 1.2 Core Philosophy
- Start manual, graduate to automation — never skip steps
- Human always controls critical money-releasing actions
- Data informs every decision, even in manual mode
- Safety and reputation-building before profit maximization

### 1.3 The Operator
- Based in Sudan, trading USDT against Sudanese Pound (SDG)
- Has existing XRP (~629 XRP) and SOL holdings in Exodus wallet
- Holds Sudanese bank accounts (Bank of Khartoum + others)
- Technical background in AI, Python, WhatsApp automation, Arabic NLP
- Binance account — KYC pending, will be verified

---

## 2. SYSTEM ARCHITECTURE

### 2.1 High-Level Components

```
┌─────────────────────────────────────────────────┐
│              TELEGRAM COMMAND CENTER             │
│         (Primary UI — alerts + commands)         │
└──────────────┬──────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│                 CORE PLATFORM                    │
│  ┌─────────────────┐    ┌─────────────────────┐  │
│  │   P2P MODULE    │    │   SPOT MODULE       │  │
│  │  (USDT / SDG)   │    │  (XRP & SOL)        │  │
│  └────────┬────────┘    └──────────┬──────────┘  │
│           │                        │              │
│  ┌────────▼────────────────────────▼──────────┐  │
│  │         UNIFIED INTELLIGENCE LAYER         │  │
│  │  Market Monitor | Risk Engine | Portfolio  │  │
│  └────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
               │
┌──────────────▼──────────────────────────────────┐
│              DATA & STORAGE LAYER                │
│     SQLite DB | Trade Logs | Config Files        │
└─────────────────────────────────────────────────┘
```

### 2.2 Deployment
- Runs 24/7 on a VPS (Ubuntu, $5-10/month — DigitalOcean or Hetzner)
- Python 3.11+
- Telegram Bot as primary interface
- SQLite for local storage (no cloud DB needed initially)

---

## 3. OPERATING MODES

### 3.1 Three-Mode Toggle System

The entire platform operates in one of three modes, switchable via Telegram:

#### 🟢 MODE 1 — MANUAL + INSIGHTS
*Use during: First 4-6 weeks of operation*

**Behavior:**
- System monitors everything passively
- No automated actions whatsoever
- Every incoming trade → system analyzes and sends full insight report to Telegram
- Operator executes all actions manually on Binance app
- System logs all trades and timing for later learning

**Purpose:** Learn the market with data support. Build trade history and reputation.

#### 🟡 MODE 2 — SEMI-AUTO
*Use during: After 50-100 completed trades*

**Behavior:**
- Bot auto-adjusts P2P ad rates using Binance floating rate API
- Bot auto-scores incoming traders → recommends accept/decline
- Green-scored traders: bot suggests auto-accept
- Operator still manually confirms payments and releases crypto
- SMS parser active — detects bank payments and alerts immediately

**Purpose:** Reduce manual workload while keeping human control on money release.

#### 🔴 MODE 3 — FULL AUTO
*Use during: After 200+ trades, proven system*

**Behavior:**
- Full rate management automated
- Trader scoring and accept/decline automated
- Payment detection automated (SMS parsing)
- Operator notified only for disputes, unusual situations, or manual override
- All actions logged with full audit trail

**Purpose:** Scale operations, operate during sleep/unavailability.

---

### 3.2 Availability Toggle

Three availability states (separate from mode):

| State | Symbol | Behavior |
|-------|--------|----------|
| ONLINE | 🟢 | Full operation, ads active |
| SLOW | 🟡 | Ads active, extended windows, alert every trade |
| OFFLINE | 🔴 | Ads auto-paused, no new orders accepted |

**Critical:** Binance penalizes merchants who accept then don't respond. OFFLINE state must pause ads via API immediately when toggled.

---

## 4. P2P MODULE — FULL SPECIFICATION

### 4.1 Market Monitor

**Function:** Continuously tracks the USDT/SDG P2P market

**Data collected every 5 minutes:**
- Top 10 buy-side offers (merchants selling USDT): rates, limits, availability
- Top 10 sell-side offers (merchants buying USDT): rates, limits, availability
- Current spread (buy price minus sell price)
- Average spread over last 1h, 6h, 24h
- Volume indicators (number of active ads, available liquidity)
- Competitor rate changes (flag when top merchants update)

**Alerts triggered:**
- Spread widens above threshold → opportunity alert
- Spread narrows below threshold → warning, consider pausing
- Competitor drops rate significantly → rate adjustment needed
- Unusual volume spike → market movement possible

**Implementation:**
```python
# Binance P2P prices via web scraping or P2P API
# Endpoint: https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search
# Method: POST with payload specifying asset, fiat, tradeType
# Rate: every 5 minutes, respectful scraping
```

### 4.2 Trader Risk Scorer

**Function:** Scores every incoming trader before operator sees the alert

**Input:** Trader's Binance P2P profile data
**Output:** Score 0-100 + color rating + recommendation

**Scoring Algorithm:**

```
BASE SCORE: 50

POSITIVE FACTORS:
+ Total trades > 500:        +15 points
+ Total trades 100-500:      +10 points
+ Total trades 20-100:       +5 points
+ Completion rate > 98%:     +15 points
+ Completion rate 95-98%:    +10 points
+ Completion rate 90-95%:    +5 points
+ Positive feedback > 99%:   +10 points
+ Account age > 180 days:    +10 points
+ Account age 90-180 days:   +5 points
+ Previously traded OK:      +15 points (personal history)
+ KYC verified:              +5 points

NEGATIVE FACTORS:
- Any dispute history:       -30 points
- Completion rate < 85%:     -20 points
- Account age < 30 days:     -25 points
- Total trades < 5:          -20 points
- Order size >> their usual: -10 points
- Previously had issue:      -40 points (personal history)
```

**Color Ratings:**
- 🟢 GREEN (75-100): Auto-recommend accept
- 🟡 YELLOW (50-74): Manual review recommended
- 🔴 RED (0-49): Recommend decline

**Asymmetric Rules:**
- When WE ARE SELLING (buyers come to us):
  - During reputation building phase (<100 our trades): Accept yellow, consider even low red for small amounts
  - After reputation built (>100 trades): Standard rules apply
- When WE ARE BUYING (we approach sellers):
  - Always apply strict rules regardless of our trade count

### 4.3 Rate Auto-Adjuster (Semi-Auto + Full Auto modes)

**Function:** Keeps our ad rates optimally positioned vs competition

**Logic:**
```
TARGET POSITION: 2nd or 3rd best rate (not cheapest, not most expensive)

If our rate < best competitor rate by > 5 SDG:
    → Increase our rate (capture more profit)

If our rate > best competitor rate:
    → Decrease slightly (stay competitive, maintain order flow)

If spread < 10 SDG:
    → Alert operator: market tight, consider pausing

If spread > 25 SDG:
    → Alert operator: great opportunity, increase inventory if possible
```

**Rate update frequency:** Every 15 minutes or when competitor changes detected

**Implementation:** Binance P2P allows floating rate ads — set as percentage above/below market. Bot adjusts this percentage.

### 4.4 Payment SMS Parser

**Function:** Detects incoming bank payments without manual bank app checking

**How it works:**
- Android app or Tasker reads incoming SMS from Bank of Khartoum
- Parses amount, sender reference, timestamp
- Matches against pending P2P orders
- Sends Telegram alert: "Payment detected — [amount] SDG received — Order #[X] — Release now?"

**SMS patterns to parse (Bank of Khartoum format):**
```python
# Example patterns - adjust to actual bank SMS format
patterns = [
    r'credited.*?(\d+[\.,]\d+).*?SDG',
    r'received.*?(\d+[\.,]\d+).*?pound',
    r'تم إيداع.*?(\d+).*?جنيه',  # Arabic format
]
```

**Safety rule:** Never release based on SMS alone — operator must confirm and visually verify in bank app before releasing.

### 4.5 Trade Logger & Analytics

**Every completed trade records:**
```python
{
    'trade_id': str,
    'timestamp': datetime,
    'trade_type': 'buy' | 'sell',
    'amount_usdt': float,
    'rate_sdg': float,
    'total_sdg': float,
    'trader_username': str,
    'trader_score': int,
    'our_release_time_minutes': float,
    'profit_sdg': float,
    'mode': 'manual' | 'semi' | 'full',
    'bank_used': str,
    'notes': str
}
```

**Analytics generated daily:**
- Total trades, total volume, total profit (SDG + USD equivalent)
- Average release time (vs Binance ranking benchmark)
- Best/worst performing hours
- Trader score distribution of accepted trades
- Spread captured per trade

---

## 5. SPOT TRADING MODULE — FULL SPECIFICATION

### 5.1 Three Sub-Modes

#### 🧪 PAPER TRADING
- All signals generated as normal
- Fake trades executed and logged
- Real P&L calculated on fake positions
- No real money involved
- **Mandatory minimum 4 weeks before live trading**

#### 💡 LIVE SMALL ($10-30 per trade maximum)
- Real trades, tiny sizes
- Manual approval required for every trade
- Hard stop enforced by system

#### 📈 LIVE NORMAL (after proven track record)
- Increased position sizes
- Semi-automated entries possible
- Still manual approval on exits

### 5.2 Signal Engine

**Assets monitored:** XRP, SOL (expandable)

**Technical Indicators calculated:**
```python
indicators = {
    'RSI_14': {
        'oversold_threshold': 30,    # potential buy signal
        'overbought_threshold': 70,  # potential sell signal
    },
    'MACD': {
        'signal': 'bullish_crossover' | 'bearish_crossover' | 'neutral'
    },
    'EMA': {
        'fast': 20,
        'slow': 50,
        'position': 'above' | 'below'  # price vs EMAs
    },
    'volume': {
        'vs_average': float,  # ratio to 20-day average volume
        'spike_threshold': 2.0  # 2x average = significant
    },
    'support_resistance': {
        'nearest_support': float,
        'nearest_resistance': float,
        'distance_to_support_pct': float,
        'distance_to_resistance_pct': float
    },
    'bollinger_bands': {
        'position': 'lower' | 'middle' | 'upper',
        'squeeze': bool
    }
}
```

**Signal Generation:**
```python
# Composite signal from multiple indicators
# Each indicator votes: BUY / SELL / NEUTRAL
# Weighted voting → final signal with confidence %

signal = {
    'direction': 'BUY' | 'SELL' | 'HOLD',
    'confidence': float,  # 0-100%
    'suggested_entry': float,
    'suggested_stop_loss': float,
    'suggested_target': float,
    'risk_reward_ratio': float,
    'suggested_size_usd': float
}
```

**Only alert operator when confidence > 60%**

### 5.3 News & Fundamental Monitor

**XRP specific:**
- Ripple official blog RSS
- SEC/legal news keywords
- ETF filing updates
- Partnership announcements

**SOL specific:**
- Solana network status (outage history = risk factor)
- Ecosystem growth metrics
- Major protocol launches

**General crypto:**
- Bitcoin dominance index
- Crypto Fear & Greed Index
- Major exchange news

**Implementation:** RSS feeds + keyword monitoring of crypto news APIs (CoinGecko, CryptoCompare free tiers)

### 5.4 Risk Management — Hard Rules

```python
RISK_LIMITS = {
    'max_single_trade_usd': 30,          # paper: unlimited
    'max_daily_loss_usd': 50,            # system pauses if hit
    'max_total_exposure_usd': 150,       # max open positions
    'stop_loss_xrp_pct': 5,             # 5% max stop loss
    'stop_loss_sol_pct': 7,             # 7% max stop loss
    'max_trades_per_day': 5,            # prevents overtrading
    'min_risk_reward_ratio': 1.5,       # only trade if R:R >= 1.5
}

# Golden Rule — enforced programmatically:
# Stop loss can only move CLOSER to entry (to protect profit)
# Never move stop loss FURTHER from entry
```

### 5.5 Spot Trade Logger

```python
{
    'trade_id': str,
    'asset': 'XRP' | 'SOL',
    'mode': 'paper' | 'live_small' | 'live_normal',
    'direction': 'long' | 'short',
    'entry_price': float,
    'exit_price': float,
    'size': float,
    'stop_loss': float,
    'target': float,
    'pnl_usd': float,
    'pnl_pct': float,
    'signal_confidence': float,
    'indicators_at_entry': dict,
    'duration_minutes': float,
    'outcome': 'win' | 'loss' | 'breakeven',
    'notes': str
}
```

---

## 6. UNIFIED INTELLIGENCE LAYER

### 6.1 Portfolio Dashboard

**Real-time unified view:**
```
💼 PORTFOLIO SNAPSHOT
──────────────────────────────
P2P Float:        [X] USDT
XRP Holdings:     [X] XRP = $[X]
SOL Holdings:     [X] SOL = $[X]
USDC (Solana):    $[X]

Total Value:      ~$[X]

Today:
  P2P Profit:     +[X] SDG
  Spot P&L:       +/- $[X]
  Trades Done:    [X]

This Month:
  P2P Total:      +[X] SDG
  Spot Total:     +/- $[X]
  Best Trade:     [details]
  Worst Trade:    [details]
```

### 6.2 Cross-Module Intelligence

**P2P → Spot signals:**
- When P2P spread is very wide: focus energy on P2P, reduce spot activity
- When P2P spread is tight: can allocate more attention to spot

**Spot → P2P signals:**
- When crypto markets very volatile: P2P rates need more frequent updates
- Major XRP/SOL news → update P2P rates quickly (SDG market may react)

### 6.3 SDG Intelligence Layer

**Monitors:**
- SDG informal/parallel market rate (from Telegram trading groups, web sources)
- Divergence between P2P rate and informal rate
- SDG trend direction (strengthening or weakening)

**Alerts:**
- Large SDG rate movement → immediately alert operator to update P2P rates
- If P2P rate significantly below informal rate → opportunity to increase our selling rate

---

## 7. TELEGRAM BOT — FULL COMMAND INTERFACE

### 7.1 Commands

```
/mode [manual|semi|full]     — Switch operating mode
/status                      — Full platform status
/portfolio                   — Current portfolio snapshot
/p2p                         — P2P market snapshot + spread
/signals                     — Current spot trading signals
/trades [today|week|month]   — Trade history and stats
/pause                       — Set availability to OFFLINE
/slow                        — Set availability to SLOW
/online                      — Set availability to ONLINE
/score [username]            — Score a specific Binance trader
/risk                        — Current risk limits status
/help                        — Command list
```

### 7.2 Incoming Trade Alert Format (P2P)

```
🔔 NEW TRADE ORDER — P2P

👤 Trader: [username]
⭐ Score: [X]/100 [🟢/🟡/🔴]
📊 Trades: [X] | ✅ [X]% completion
📅 Account: [X] days old
💰 Order: [X] USDT ([X] SDG)
🏦 Payment: Bank of Khartoum

📉 MARKET NOW
Spread: [X] SDG (avg 24h: [X])
Your rate: [X] | Best competitor: [X]
Est. profit this trade: [X] SDG

💡 RECOMMENDATION: [ACCEPT/REVIEW/DECLINE]

Reply: /accept [id] | /decline [id]
```

### 7.3 Payment Detected Alert

```
💸 PAYMENT DETECTED

Order #[X] | Trader: [username]
Amount: [X] SDG
Bank: Bank of Khartoum
Time: [timestamp]

✅ Verify in your bank app then:
Reply /release [id] to confirm you've released
```

### 7.4 Daily Summary (sent at end of day)

```
📊 DAILY SUMMARY — [Date]

P2P TRADING:
  Trades: [X] completed
  Volume: [X] USDT
  Profit: [X] SDG (~$[X])
  Avg release time: [X] min
  Best trade: [X] SDG profit

SPOT TRADING:
  Signals generated: [X]
  Paper trades: [X] | P&L: $[X]
  Live trades: [X] | P&L: $[X]

REPUTATION:
  Current trade count: [X]
  Completion rate: [X]%
  Avg feedback: [X]%

Mode tomorrow: [current mode]
```

---

## 8. DATA MODELS

### 8.1 Database Schema (SQLite)

```sql
-- P2P Trades
CREATE TABLE p2p_trades (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    trade_type TEXT,  -- 'buy' or 'sell'
    amount_usdt REAL,
    rate_sdg REAL,
    total_sdg REAL,
    trader_username TEXT,
    trader_score INTEGER,
    release_time_minutes REAL,
    profit_sdg REAL,
    mode TEXT,
    bank_used TEXT,
    notes TEXT
);

-- Spot Trades
CREATE TABLE spot_trades (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    asset TEXT,
    mode TEXT,
    direction TEXT,
    entry_price REAL,
    exit_price REAL,
    size REAL,
    stop_loss REAL,
    target REAL,
    pnl_usd REAL,
    pnl_pct REAL,
    signal_confidence REAL,
    outcome TEXT,
    notes TEXT
);

-- Market Snapshots
CREATE TABLE market_snapshots (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    buy_best_rate REAL,
    sell_best_rate REAL,
    spread REAL,
    our_rate REAL,
    competitors_json TEXT
);

-- Trader History (personal blacklist/whitelist)
CREATE TABLE trader_history (
    username TEXT PRIMARY KEY,
    first_trade DATETIME,
    last_trade DATETIME,
    total_trades INTEGER,
    successful INTEGER,
    disputed INTEGER,
    notes TEXT,
    flagged BOOLEAN
);

-- System Events
CREATE TABLE system_events (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    event_type TEXT,
    description TEXT,
    mode TEXT
);
```

---

## 9. TECHNOLOGY STACK

### 9.1 Core Technologies

```
Language:       Python 3.11+
Bot Framework:  python-telegram-bot (v20+)
HTTP Client:    httpx (async)
Scheduler:      APScheduler
Database:       SQLite via SQLAlchemy
Data Analysis:  pandas, numpy, ta (technical analysis)
Config:         python-dotenv (.env files)
Logging:        loguru
Testing:        pytest
```

### 9.2 External APIs

```
Binance P2P:    https://p2p.binance.com/bapi/c2c/v2/
Binance Spot:   python-binance library (official SDK)
News/Prices:    CoinGecko API (free tier)
                CryptoCompare API (free tier)
Fear & Greed:   alternative.me API (free)
```

### 9.3 Project Structure

```
trading-platform/
├── main.py                  # Entry point
├── config.py                # Configuration management
├── .env                     # API keys (never commit)
├── requirements.txt
│
├── bot/
│   ├── telegram_bot.py      # Bot setup and routing
│   ├── commands.py          # All /commands handlers
│   └── formatters.py        # Message formatting
│
├── p2p/
│   ├── market_monitor.py    # P2P price monitoring
│   ├── trader_scorer.py     # Risk scoring engine
│   ├── rate_adjuster.py     # Rate optimization
│   ├── sms_parser.py        # Payment SMS parsing
│   └── p2p_logger.py        # Trade logging
│
├── spot/
│   ├── signal_engine.py     # Technical analysis
│   ├── news_monitor.py      # Fundamental monitoring
│   ├── risk_manager.py      # Position sizing & stops
│   ├── paper_trader.py      # Paper trading simulation
│   └── spot_logger.py       # Trade logging
│
├── intelligence/
│   ├── portfolio.py         # Unified portfolio view
│   ├── sdg_monitor.py       # SDG rate intelligence
│   ├── analytics.py         # Performance analytics
│   └── cross_signals.py     # Cross-module intelligence
│
├── data/
│   ├── database.py          # SQLite connection & ORM
│   ├── models.py            # SQLAlchemy models
│   └── trading.db           # SQLite database file
│
└── tests/
    ├── test_scorer.py
    ├── test_signals.py
    └── test_risk_manager.py
```

---

## 10. SECURITY REQUIREMENTS

### 10.1 API Key Management
- All API keys in .env file — never hardcoded
- .env in .gitignore — never committed to any repository
- Binance API keys: enable only required permissions (read + trade, never withdraw)
- Separate API keys for paper trading vs live trading

### 10.2 Telegram Security
- Bot only responds to YOUR Telegram user ID
- All other users get silent ignore
- Command whitelist — unknown commands rejected

```python
ALLOWED_USER_IDS = [your_telegram_id]

def restricted(func):
    def wrapper(update, context):
        if update.effective_user.id not in ALLOWED_USER_IDS:
            return  # Silent ignore
        return func(update, context)
    return wrapper
```

### 10.3 Trade Safety Rules (Hardcoded — Cannot Be Overridden)
- Maximum single P2P trade: configurable but requires confirmation above threshold
- Spot stop-loss: system sets it, operator cannot remove it (can only tighten)
- Daily loss limit: system pauses all trading if hit, requires manual restart
- All money-releasing actions: require explicit confirmation command

---

## 11. BUILD PHASES

### Phase 1 — Foundation (Week 1-2)
- [ ] Project structure setup
- [ ] Telegram bot base (mode toggle, availability toggle)
- [ ] P2P market monitor (price scraping, spread calculation)
- [ ] Basic trader scorer
- [ ] SQLite database setup
- [ ] Manual mode insights delivery via Telegram
- [ ] Daily summary message

**Milestone:** Can monitor P2P market and receive trade insights on Telegram

### Phase 2 — P2P Intelligence (Week 3-4)
- [ ] Full trader scoring algorithm
- [ ] Rate auto-adjuster (floating rate integration)
- [ ] Trade logger with analytics
- [ ] SDG informal rate monitor
- [ ] Competitor tracking
- [ ] Performance dashboard

**Milestone:** Full Semi-Auto mode operational

### Phase 3 — Payment Detection (Week 5-6)
- [ ] SMS parser (Android integration via Tasker or dedicated app)
- [ ] Payment matching against open orders
- [ ] Telegram payment confirmation flow
- [ ] Personal trader history (blacklist/whitelist)

**Milestone:** Near-complete P2P automation operational

### Phase 4 — Spot Module (Week 7-10)
- [ ] Binance spot API integration
- [ ] Technical indicator calculation (RSI, MACD, EMA, BB)
- [ ] Signal engine with confidence scoring
- [ ] Paper trading engine
- [ ] News/fundamental monitor
- [ ] Risk manager with hard limits

**Milestone:** Paper trading running for XRP and SOL

### Phase 5 — Unification (Week 11-12)
- [ ] Unified portfolio dashboard
- [ ] Cross-module intelligence signals
- [ ] Full analytics suite
- [ ] Performance reporting
- [ ] System health monitoring
- [ ] VPS deployment with auto-restart

**Milestone:** Full platform live, paper trading graduating to small live trades

---

## 12. SUCCESS METRICS

### P2P Section
- Average release time: < 3 minutes (beats Alteganie's 5.31)
- Completion rate: > 97%
- Monthly trade count: 500+ by month 3
- Zero fraud incidents
- Positive feedback: > 99%

### Spot Section
- Paper trading: 4 weeks minimum before any live trade
- Paper trading win rate: > 55% before going live
- Live trading max drawdown: < $50 ever
- Risk/reward achieved: > 1.5 on winning trades

### System Health
- Uptime: > 99%
- Alert delivery: < 30 seconds from event
- Rate update latency: < 15 minutes from market change

---

## 13. IMPORTANT NOTES FOR CLAUDE CODE

1. **Build incrementally** — Phase 1 must be fully working before Phase 2 begins
2. **Test everything** — especially the risk manager and trader scorer
3. **Binance P2P API** — use the unofficial P2P endpoint with respectful rate limiting (max 1 request/30 seconds for market data)
4. **SMS parsing** — design as a pluggable module since bank SMS formats vary
5. **Never auto-release crypto** — this action must always have explicit human confirmation
6. **Logging** — log everything with timestamps; this is financial data
7. **Error handling** — if Telegram bot crashes, it must auto-restart without losing state
8. **The .env file** must contain:
   ```
   TELEGRAM_BOT_TOKEN=
   TELEGRAM_USER_ID=
   BINANCE_API_KEY=
   BINANCE_SECRET_KEY=
   OPERATING_MODE=manual
   AVAILABILITY=online
   ```

---

*Document prepared for Claude Code implementation.*
*Start with Phase 1. Build, test, then proceed.*
*This is a personal financial tool — security and reliability over features.*
