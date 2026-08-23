<template>
  <div class="card scanner-card" v-bind="$attrs">

    <!-- Header -->
    <div class="card-header">
      <h2>
        {{ t('scanner.title') }}
        <span class="stream-dot" :class="{ live: streamLive }">●</span>
      </h2>
      <div class="header-btns">
        <button class="refresh-btn" @click="recalculate" :disabled="calcLoading">
          {{ calcLoading ? t('scanner.calculating') : t('scanner.recalculate') }}
        </button>
      </div>
    </div>

    <!-- Macro strip -->
    <div v-if="macroSummary" class="macro-strip">
      <span class="macro-chip" :class="seasonChip"
            title="Market season: Altcoin = most coins rising; BTC = Bitcoin leading the market">
        {{ macroSummary.season_label }}
      </span>
      <span class="macro-chip neutral"
            title="Bitcoin's share of the total crypto market. Below 50% = altcoin season (good for other coins)">
        BTC Dom {{ macroSummary.btc_dominance?.toFixed(1) }}%
      </span>
      <span class="macro-chip" :class="fgChipClass"
            title="Overall market mood 0–100: below 30 = panic (often a buy opportunity), above 75 = hype (be cautious)">
        Mood {{ macroSummary.fear_greed }}/100
      </span>
      <span v-if="lastScreened" class="macro-chip neutral"
            title="Date when coins were last ranked from all Binance pairs using our scoring system">
        🗓 Ranked {{ lastScreened }}
      </span>
    </div>

    <!-- Loading -->
    <div v-if="calcLoading || listLoading" class="loading-state">
      <div class="spinner"/>
      <p class="empty">{{ listLoading ? t('scanner.loading_hotness') : t('scanner.calculating') }}</p>
    </div>

    <template v-if="!calcLoading && !listLoading">

      <!-- ── ANCHORS strip ───────────────────────────────────────────────────── -->
      <div v-if="anchors.length" class="anchors-strip">
        <div v-for="c in anchors" :key="c.symbol" class="anchor-pill">
          <span class="anchor-sym">{{ c.symbol }}</span>
          <template v-if="prices[c.symbol]">
            <span class="anchor-price">{{ fmtPrice(prices[c.symbol].price) }}</span>
            <span class="anchor-chg" :class="prices[c.symbol].change_pct >= 0 ? 'pos' : 'neg'">
              {{ prices[c.symbol].change_pct >= 0 ? '▲' : '▼' }}{{ Math.abs(prices[c.symbol].change_pct).toFixed(2) }}%
            </span>
          </template>
          <span>📌</span>
        </div>
      </div>

      <!-- ── HOLDINGS section ────────────────────────────────────────────────── -->
      <div class="section-block">
        <div class="section-hdr">
          {{ t('scanner.holdings_tab') }}
          <span class="section-note">
            {{ holdings.length ? t('scanner.holdings_monitored') : t('scanner.holdings_empty') }}
          </span>
        </div>
        <div v-for="c in holdings" :key="'h-' + c.symbol"
             class="coin-card held-card" @click="toggle(c.symbol)">
          <!-- coin row -->
          <div class="coin-top">
            <div class="coin-left">
              <span class="coin-symbol">{{ c.symbol }}</span>
              <span class="coin-name">{{ c.name }}</span>
              <span v-if="c.is_narrative_leader" class="badge-leader">★</span>
              <span v-if="c.held"   class="badge-sm">💼</span>
              <span v-if="c.pinned" class="badge-sm">📌</span>
            </div>
            <div class="coin-right">
              <template v-if="prices[c.symbol]">
                <span class="lp-price">{{ fmtPrice(prices[c.symbol].price) }}</span>
                <span class="lp-chg" :class="prices[c.symbol].change_pct >= 0 ? 'pos' : 'neg'">
                  {{ prices[c.symbol].change_pct >= 0 ? '▲' : '▼' }}{{ Math.abs(prices[c.symbol].change_pct).toFixed(2) }}%
                </span>
              </template>
              <span v-if="adviceBadge(c)" class="advice-badge" :class="adviceBadge(c).cls">{{ adviceBadge(c).text }}</span>
              <span class="cons-badge" :class="consClass(c)" :title="consTitle(c)">{{ consLabel(c) }}</span>
              <span class="screen-score" title="Strength score vs all Binance coins (0–100)">{{ c.screen_score?.toFixed(0) ?? '—' }}</span>
              <button class="pin-btn" :class="{ active: c.pinned }"
                      @click.stop="togglePin(c)" :title="c.pinned ? t('scanner.unpin_tip') : t('scanner.pin_tip')">
                {{ c.pinned ? '📌' : '📍' }}
              </button>
            </div>
          </div>
          <div class="score-bar-wrap">
            <div class="score-bar" :style="{ width: (c.screen_score || 0) + '%' }"/>
          </div>

          <!-- ── Live P&L (shown when coin has an open journal trade) ───────── -->
          <div v-if="pnlMap[c.symbol]" class="pnl-row">
            <span class="pnl-label">{{ t('scanner.entry_lbl') }}</span>
            <span class="pnl-entry-price">{{ fmtPrice(pnlMap[c.symbol].pos.entry_price) }}</span>
            <span class="pnl-arrow">→</span>
            <span class="pnl-now" :class="pnlMap[c.symbol].pnlPct >= 0 ? 'pos' : 'neg'">
              {{ fmtPrice(pnlMap[c.symbol].livePrice) }}
            </span>
            <span class="pnl-badge" :class="pnlMap[c.symbol].pnlPct >= 0 ? 'pnl-pos' : 'pnl-neg'">
              {{ pnlMap[c.symbol].pnlPct >= 0 ? '+' : '' }}{{ pnlMap[c.symbol].pnlUsd.toFixed(0) }} USD
              &nbsp;({{ pnlMap[c.symbol].pnlPct >= 0 ? '+' : '' }}{{ pnlMap[c.symbol].pnlPct.toFixed(2) }}%)
            </span>
            <span v-if="pnlMap[c.symbol].pos.trailing_stop_peak" class="pnl-peak"
                  title="Highest price reached — trailing stop follows this">
              {{ t('scanner.peak_lbl') }} {{ fmtPrice(pnlMap[c.symbol].pos.trailing_stop_peak) }}
            </span>
          </div>

          <!-- ── SL / Target bar ────────────────────────────────────────────── -->
          <div v-if="slBarMap[c.symbol]" class="sl-target-wrap">
            <span v-if="slBarMap[c.symbol].trailing" class="sl-label trailing-sl-label"
                  :title="`Trailing stop: fires when price drops ${pnlMap[c.symbol].pos.trailing_stop_pct}% from the peak of ${fmtPrice(slBarMap[c.symbol].peak)}`">
              🔄 {{ fmtPrice(slBarMap[c.symbol].sl) }}
            </span>
            <span v-else class="sl-label" title="Stop-loss: the price at which you would cut the loss">
              SL {{ fmtPrice(slBarMap[c.symbol].sl) }}
            </span>
            <div class="sl-bar-track">
              <div class="sl-bar-gradient"/>
              <div class="sl-marker" :style="{ left: slBarMap[c.symbol].pct + '%' }"/>
            </div>
            <span v-if="slBarMap[c.symbol].trailing" class="target-label trailing-peak-label"
                  title="Current peak — trailing stop tracks this price">
              {{ t('scanner.peak_lbl') }} {{ fmtPrice(slBarMap[c.symbol].peak) }}
            </span>
            <span v-else class="target-label" title="Take-profit: the target price to sell for a gain">
              TP {{ fmtPrice(slBarMap[c.symbol].target) }}
            </span>
          </div>

          <div class="coin-indicators">
            <div v-if="hotnessMap[c.symbol]?.rsi_1d != null" class="ind-item">
              <span class="ind-label">RSI (momentum)</span>
              <span class="ind-val" :class="rsiCls(hotnessMap[c.symbol].rsi_1d)">{{ hotnessMap[c.symbol].rsi_1d }}</span>
            </div>
            <div v-if="hotnessMap[c.symbol]?.vol_ratio != null" class="ind-item">
              <span class="ind-label">Volume (activity)</span>
              <span class="ind-val" :class="hotnessMap[c.symbol].vol_ratio >= 1.5 ? 'pos' : hotnessMap[c.symbol].vol_ratio < 0.7 ? 'neg' : ''">
                {{ hotnessMap[c.symbol].vol_ratio }}x
              </span>
            </div>
            <div v-if="hotnessMap[c.symbol]?.above_ema200 != null" class="ind-item">
              <span class="ind-label">Trend (EMA200)</span>
              <span class="ind-val" :class="hotnessMap[c.symbol].above_ema200 ? 'pos' : 'neg'">
                {{ hotnessMap[c.symbol].above_ema200 ? '✓' : '✗' }}
                {{ hotnessMap[c.symbol].ema_200_pct != null ? (hotnessMap[c.symbol].ema_200_pct > 0 ? '+' : '') + hotnessMap[c.symbol].ema_200_pct + '%' : '' }}
              </span>
            </div>
            <div v-if="c.narrative" class="ind-item">
              <span class="ind-label">Theme</span>
              <span class="ind-val narrative-tag">{{ c.narrative }}</span>
            </div>
          </div>
          <!-- expanded breakdown -->
          <div v-if="selected === c.symbol" class="breakdown">
            <div v-if="hotnessMap[c.symbol]?.breakdown" class="breakdown-title">{{ t('scanner.hotness_breakdown') }}</div>
            <div v-for="(item, key) in hotnessMap[c.symbol]?.breakdown" :key="key" class="breakdown-row">
              <span class="bd-key">{{ bdLabel(key) }}</span>
              <span class="bd-pts" :class="item[0] > 0 ? 'pos' : item[0] < 0 ? 'neg' : 'muted'">{{ item[0] > 0 ? '+' : '' }}{{ item[0] }}</span>
              <span class="bd-reason">{{ item[1] }}</span>
            </div>
            <div v-if="hotnessMap[c.symbol]?.supports?.length" class="levels">
              <span class="level-label">{{ t('scanner.support_lbl') }}</span>
              <span v-for="s in hotnessMap[c.symbol].supports" :key="s.price" class="support-val">${{ s.price.toFixed(4) }}</span>
            </div>
            <div v-if="hotnessMap[c.symbol]?.resistances?.length" class="levels">
              <span class="level-label">{{ t('scanner.resistance_lbl') }}</span>
              <span v-for="r in hotnessMap[c.symbol].resistances" :key="r.price" class="resistance-val">${{ r.price.toFixed(4) }}</span>
            </div>
            <button class="full-analysis-btn" @click.stop="detailCoin = hotnessMap[c.symbol] || c">{{ t('scanner.full_analysis') }}</button>
          </div>
        </div>
      </div>

      <!-- ── DISCOVERY POOL ──────────────────────────────────────────────────── -->
      <div class="section-block">
        <div class="section-hdr">
          {{ t('scanner.discovery_tab') }}
          <span class="section-note">{{ t('scanner.discovery_note', { n: discovery.length }) }}</span>
        </div>
        <div v-if="!discovery.length" class="empty-state">
          <p class="empty">{{ t('scanner.no_data') }}</p>
          <p class="empty-hint">{{ t('scanner.no_data_hint') }}</p>
        </div>
        <div v-for="(c, idx) in discovery" :key="'d-' + c.symbol"
             class="coin-card" :class="consistencyBorder(c)"
             @click="toggle(c.symbol)">
          <div class="coin-top">
            <div class="coin-left">
              <span class="coin-rank">#{{ idx + 1 }}</span>
              <span class="coin-symbol">{{ c.symbol }}</span>
              <span class="coin-name">{{ c.name }}</span>
              <span v-if="c.is_narrative_leader" class="badge-leader">★</span>
              <span v-if="c.held"   class="badge-sm">💼</span>
              <span v-if="c.pinned" class="badge-sm">📌</span>
            </div>
            <div class="coin-right">
              <template v-if="prices[c.symbol]">
                <span class="lp-price">{{ fmtPrice(prices[c.symbol].price) }}</span>
                <span class="lp-chg" :class="prices[c.symbol].change_pct >= 0 ? 'pos' : 'neg'">
                  {{ prices[c.symbol].change_pct >= 0 ? '▲' : '▼' }}{{ Math.abs(prices[c.symbol].change_pct).toFixed(2) }}%
                </span>
              </template>
              <span v-if="adviceBadge(c)" class="advice-badge" :class="adviceBadge(c).cls">{{ adviceBadge(c).text }}</span>
              <span class="cons-badge" :class="consClass(c)" :title="consTitle(c)">{{ consLabel(c) }}</span>
              <span class="screen-score" title="Strength score vs all Binance coins (0–100)">{{ c.screen_score?.toFixed(0) ?? '—' }}</span>
              <button class="pin-btn" :class="{ active: c.pinned }"
                      @click.stop="togglePin(c)" :title="c.pinned ? t('scanner.unpin_tip') : t('scanner.pin_tip')">
                {{ c.pinned ? '📌' : '📍' }}
              </button>
            </div>
          </div>
          <div class="score-bar-wrap">
            <div class="score-bar" :style="{ width: (c.screen_score || 0) + '%' }"/>
          </div>
          <div class="coin-indicators">
            <div v-if="hotnessMap[c.symbol]?.rsi_1d != null" class="ind-item">
              <span class="ind-label">RSI (momentum)</span>
              <span class="ind-val" :class="rsiCls(hotnessMap[c.symbol].rsi_1d)">{{ hotnessMap[c.symbol].rsi_1d }}</span>
            </div>
            <div v-if="hotnessMap[c.symbol]?.vol_ratio != null" class="ind-item">
              <span class="ind-label">Volume (activity)</span>
              <span class="ind-val" :class="hotnessMap[c.symbol].vol_ratio >= 1.5 ? 'pos' : hotnessMap[c.symbol].vol_ratio < 0.7 ? 'neg' : ''">
                {{ hotnessMap[c.symbol].vol_ratio }}x
              </span>
            </div>
            <div v-if="hotnessMap[c.symbol]?.above_ema200 != null" class="ind-item">
              <span class="ind-label">Trend (EMA200)</span>
              <span class="ind-val" :class="hotnessMap[c.symbol].above_ema200 ? 'pos' : 'neg'">
                {{ hotnessMap[c.symbol].above_ema200 ? '✓' : '✗' }}
                {{ hotnessMap[c.symbol].ema_200_pct != null ? (hotnessMap[c.symbol].ema_200_pct > 0 ? '+' : '') + hotnessMap[c.symbol].ema_200_pct + '%' : '' }}
              </span>
            </div>
            <div v-if="c.narrative" class="ind-item">
              <span class="ind-label">Theme</span>
              <span class="ind-val narrative-tag">{{ c.narrative }}</span>
            </div>
          </div>
          <div v-if="selected === c.symbol" class="breakdown">
            <div v-if="hotnessMap[c.symbol]?.breakdown" class="breakdown-title">{{ t('scanner.hotness_breakdown') }}</div>
            <div v-for="(item, key) in hotnessMap[c.symbol]?.breakdown" :key="key" class="breakdown-row">
              <span class="bd-key">{{ bdLabel(key) }}</span>
              <span class="bd-pts" :class="item[0] > 0 ? 'pos' : item[0] < 0 ? 'neg' : 'muted'">{{ item[0] > 0 ? '+' : '' }}{{ item[0] }}</span>
              <span class="bd-reason">{{ item[1] }}</span>
            </div>
            <div v-if="hotnessMap[c.symbol]?.supports?.length" class="levels">
              <span class="level-label">{{ t('scanner.support_lbl') }}</span>
              <span v-for="s in hotnessMap[c.symbol].supports" :key="s.price" class="support-val">${{ s.price.toFixed(4) }}</span>
            </div>
            <div v-if="hotnessMap[c.symbol]?.resistances?.length" class="levels">
              <span class="level-label">{{ t('scanner.resistance_lbl') }}</span>
              <span v-for="r in hotnessMap[c.symbol].resistances" :key="r.price" class="resistance-val">${{ r.price.toFixed(4) }}</span>
            </div>
            <button class="full-analysis-btn" @click.stop="detailCoin = hotnessMap[c.symbol] || c">{{ t('scanner.full_analysis') }}</button>
          </div>
        </div>
      </div>

    </template>
  </div>

  <CoinDetail v-if="detailCoin" :coin="detailCoin"
              :live="prices[detailCoin.symbol] || null"
              @close="detailCoin = null" />
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'
import CoinDetail from './CoinDetail.vue'

const { t } = useI18n()
const API   = import.meta.env.VITE_API_BASE || ''

const ANCHOR_SYMS = new Set(['BTC', 'ETH'])

const watchlist    = ref([])
const hotnessMap   = ref({})
const positionMap  = ref({})   // open journal trades keyed by symbol
const macroSummary = ref(null)
const prices       = ref({})
const streamLive   = ref(false)
const calcLoading  = ref(false)
const listLoading  = ref(false)
const selected     = ref(null)
const detailCoin   = ref(null)
let   priceTimer   = null

const anchors   = computed(() => watchlist.value.filter(c => ANCHOR_SYMS.has(c.symbol)))
const holdings  = computed(() => watchlist.value.filter(c => !ANCHOR_SYMS.has(c.symbol) && (c.pinned || c.held)))
const discovery = computed(() =>
  [...watchlist.value]
    .filter(c => !ANCHOR_SYMS.has(c.symbol))
    .sort((a, b) => (b.screen_score || 0) - (a.screen_score || 0))
)

const lastScreened = computed(() =>
  watchlist.value.find(c => c.last_screened)?.last_screened?.slice(0, 10) ?? null
)

// Live P&L — recomputes automatically whenever prices update (every 15s)
const pnlMap = computed(() => {
  const result = {}
  for (const c of watchlist.value) {
    const pos = positionMap.value[c.symbol]
    const livePrice = prices.value[c.symbol]?.price
    if (!pos || !livePrice) continue
    const pnlPct = (livePrice - pos.entry_price) / pos.entry_price * 100
    const pnlUsd = pos.size_usd * (pnlPct / 100)
    result[c.symbol] = { pnlPct, pnlUsd, pos, livePrice }
  }
  return result
})

// SL / Target range bar — supports both fixed SL/TP and trailing stop mode
const slBarMap = computed(() => {
  const result = {}
  for (const [sym, pnl] of Object.entries(pnlMap.value)) {
    const { pos, livePrice } = pnl

    if (pos.trailing_stop_pct) {
      // Trailing stop mode: bar shows entry → peak, marker = current price
      const peak = pos.trailing_stop_peak || pos.entry_price
      const tsLevel = peak * (1 - pos.trailing_stop_pct / 100)
      // Only show bar once trailing stop is above entry (gain is locked in)
      if (tsLevel <= pos.entry_price) continue
      const range = peak - tsLevel
      if (range <= 0) continue
      const pct = Math.max(0, Math.min(100, (livePrice - tsLevel) / range * 100))
      result[sym] = { pct, sl: tsLevel, target: peak, trailing: true, peak }
    } else {
      // Fixed SL/TP mode
      if (!pos.stop_loss || !pos.target) continue
      const range = pos.target - pos.stop_loss
      if (range <= 0) continue
      const pct = Math.max(0, Math.min(100, (livePrice - pos.stop_loss) / range * 100))
      result[sym] = { pct, sl: pos.stop_loss, target: pos.target, trailing: false }
    }
  }
  return result
})
const seasonChip = computed(() => {
  const s = macroSummary.value?.season_label?.toLowerCase() || ''
  return s.includes('alt') ? 'season-green' : 'season-orange'
})
const fgChipClass = computed(() => {
  const v = macroSummary.value?.fear_greed
  return !v ? 'neutral' : v <= 45 ? 'fg-fear' : v >= 75 ? 'fg-greed' : 'neutral'
})

async function loadWatchlist() {
  const { data } = await axios.get(`${API}/api/spot/watchlist`)
  watchlist.value = data
}
async function loadPositions() {
  const { data } = await axios.get(`${API}/api/spot/positions`)
  // If multiple open trades per symbol, keep the most recent one
  const map = {}
  for (const p of data) {
    if (!map[p.symbol]) map[p.symbol] = p
  }
  positionMap.value = map
}
async function loadHotness() {
  const { data } = await axios.get(`${API}/api/spot/hotness`)
  macroSummary.value = data.macro_summary
  hotnessMap.value   = Object.fromEntries((data.coins || []).map(c => [c.symbol, c]))
}
async function fetchPrices() {
  try {
    const { data } = await axios.get(`${API}/api/spot/prices`)
    prices.value     = data.prices    || {}
    streamLive.value = data.connected || false
  } catch { streamLive.value = false }
}
async function recalculate() {
  calcLoading.value = true; selected.value = null
  try { await axios.post(`${API}/api/spot/hotness/recalculate`); await loadHotness() }
  finally { calcLoading.value = false }
}
async function refreshList() {
  listLoading.value = true; selected.value = null
  try {
    await axios.post(`${API}/api/spot/watchlist/refresh`)
    await Promise.all([loadWatchlist(), loadHotness(), loadPositions()])
  } finally { listLoading.value = false }
}
async function togglePin(c) {
  await axios.post(`${API}/api/spot/watchlist/${c.symbol}/${c.pinned ? 'unpin' : 'pin'}`)
  await loadWatchlist()
}
function toggle(sym) { selected.value = selected.value === sym ? null : sym }

function fmtPrice(p) {
  if (!p) return '—'
  if (p >= 10000) return '$' + p.toLocaleString('en', { maximumFractionDigits: 0 })
  if (p >= 1000)  return '$' + p.toFixed(1)
  if (p >= 100)   return '$' + p.toFixed(2)
  if (p >= 1)     return '$' + p.toFixed(3)
  return '$' + p.toFixed(5)
}
function rsiCls(v) { return v < 35 || (v >= 40 && v <= 55) ? 'pos' : v > 70 ? 'neg' : '' }

function consLabel(c) {
  const con = c.consistency
  if (!con || !con.total_runs) return '—'
  return `${con.appearances}/${con.total_runs}`
}
function consClass(c) {
  const con = c.consistency
  if (!con || !con.total_runs) return 'cons-none'
  if (!con.mature) return 'cons-building'
  return con.pct >= 70 ? 'cons-high' : con.pct >= 40 ? 'cons-mid' : 'cons-low'
}
function consTitle(c) {
  const con = c.consistency
  if (!con || !con.total_runs) return 'No history yet'
  if (!con.mature) return `Building history (${con.total_runs}/4 weeks minimum)`
  return `Appeared ${con.appearances}/${con.total_runs} weeks (${con.pct}%)`
}
function consistencyBorder(c) {
  const con = c.consistency
  if (!con || !con.total_runs || !con.mature) return ''
  return con.pct >= 70 ? 'cons-border-high' : con.pct >= 40 ? 'cons-border-mid' : 'cons-border-low'
}

const BD_LABELS = {
  btc_dominance:      'Market Share (BTC)',
  fear_greed:         'Market Mood (0=panic · 100=hype)',
  narrative:          'Theme Heat',
  narrative_position: 'Theme Leader?',
  rsi:                'RSI (momentum)',
  ema_200:            'Trend Line (EMA200)',
  volume:             'Volume (vs average)',
  structure:          'Price Pattern',
  catalyst:           'News / Event',
}
function bdLabel(key) { return BD_LABELS[key] || key }
function adviceBadge(c) {
  const h = hotnessMap.value[c.symbol]
  if (!h) return null
  const k = h.rating_key
  if (k === 'very_hot') return { cls: 'ab-buy',   text: t('scanner.badge_buy') }
  if (k === 'warm')     return { cls: 'ab-watch',  text: t('scanner.badge_watch') }
  if (k === 'cold')     return { cls: 'ab-wait',   text: t('scanner.badge_wait') }
  return                       { cls: 'ab-skip',   text: t('scanner.badge_skip') }
}

onMounted(async () => {
  await Promise.all([loadWatchlist(), loadHotness(), loadPositions(), fetchPrices()])
  priceTimer = setInterval(fetchPrices, 15_000)
})
onUnmounted(() => clearInterval(priceTimer))
</script>

<style scoped>
.scanner-card { display: flex; flex-direction: column; gap: 0.75rem; }
.header-btns  { display: flex; gap: 0.4rem; }

.macro-strip { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.macro-chip { font-size: var(--font-size-sm-plus); font-weight: 600; padding: 0.25rem 0.6rem; border-radius: 999px; white-space: nowrap; }
.macro-chip.neutral       { background: var(--color-border); color: var(--color-text-secondary); }
.macro-chip.season-green  { background: var(--color-success-bg); color: var(--color-success-strong); border: 1px solid var(--color-success-emphasis); }
.macro-chip.season-orange { background: var(--color-warning-bg); color: var(--color-warning); border: 1px solid var(--color-warning-emphasis); }
.macro-chip.fg-fear  { background: var(--color-success-bg); color: var(--color-success-strong); }
.macro-chip.fg-greed { background: var(--color-danger-bg); color: var(--color-danger); }

.loading-state { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 1rem; }
.spinner { width: 28px; height: 28px; border: 3px solid var(--color-border); border-top-color: var(--color-accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* Anchors */
.anchors-strip { display: flex; gap: 0.5rem; flex-wrap: wrap; background: #141720; border: 1px solid var(--color-border); border-radius: 0.6rem; padding: 0.55rem 0.75rem; }
.anchor-pill   { display: flex; align-items: center; gap: 0.4rem; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: 0.4rem; padding: 0.3rem 0.65rem; }
.anchor-sym    { font-size: 1.05rem; font-weight: 800; color: var(--color-accent-strong); }
.anchor-price  { font-size: var(--font-size-sm-plus); color: var(--color-text); }
.anchor-chg    { font-size: var(--font-size-sm); font-weight: 600; }

/* Sections */
.section-block { display: flex; flex-direction: column; gap: 0.4rem; }
.section-hdr   { font-size: var(--font-size-sm); font-weight: 700; color: var(--color-text-disabled); text-transform: uppercase; letter-spacing: 0.05em; }
.section-note  { font-weight: 400; color: var(--color-text-subtle); font-size: var(--font-size-xs); text-transform: none; letter-spacing: 0; }

/* Coin cards */
.coin-card  { border: 1px solid var(--color-border); border-radius: 0.6rem; padding: 0.7rem 0.8rem; cursor: pointer; transition: border-color 0.15s; }
.held-card  { border-color: var(--color-accent-muted); background: #0d1520; }
.coin-card:active { border-color: var(--color-accent); }

.cons-border-high { border-inline-start: 3px solid var(--color-success); }
.cons-border-mid  { border-inline-start: 3px solid var(--color-warning); }
.cons-border-low  { border-inline-start: 3px solid var(--color-danger); }

.coin-top   { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem; }
.coin-left  { display: flex; align-items: baseline; gap: 0.4rem; flex-wrap: wrap; }
.coin-right { display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; flex-wrap: wrap; justify-content: flex-end; }

.coin-rank   { font-size: var(--font-size-sm); color: var(--color-text-subtle); min-width: 22px; }
.coin-symbol { font-size: 1.25rem; font-weight: 800; color: var(--color-text); }
.coin-name   { font-size: var(--font-size-sm-plus); color: var(--color-text-disabled); }
.badge-leader { font-size: var(--font-size-sm); color: var(--color-warning); }
.badge-sm     { font-size: var(--font-size-sm); }

.lp-price { font-size: var(--font-size-sm-plus); font-weight: 700; color: var(--color-text); }
.lp-chg   { font-size: var(--font-size-sm); font-weight: 600; }

.cons-badge  { font-size: var(--font-size-sm); font-weight: 700; padding: 0.12rem 0.4rem; border-radius: 999px; white-space: nowrap; }
.cons-none     { background: var(--color-border); color: var(--color-text-subtle); }
.cons-building { background: var(--color-border); color: var(--color-text-secondary); }
.cons-high     { background: var(--color-success-bg); color: var(--color-success-strong); }
.cons-mid      { background: var(--color-warning-bg); color: var(--color-warning); }
.cons-low      { background: var(--color-danger-bg); color: var(--color-danger); }

/* Action advice badge — most prominent element, visible at a glance */
.advice-badge { font-size: var(--font-size-sm); font-weight: 700; padding: 0.18rem 0.55rem; border-radius: 0.35rem; white-space: nowrap; letter-spacing: 0.01em; }
.ab-buy   { background: var(--color-success-bg); color: var(--color-success-strong); border: 1px solid var(--color-success-emphasis); }
.ab-watch { background: var(--color-warning-bg); color: var(--color-warning); border: 1px solid var(--color-warning-emphasis); }
.ab-wait  { background: var(--color-border); color: var(--color-text-secondary); border: 1px solid var(--color-border-muted); }
.ab-skip  { background: var(--color-danger-bg); color: var(--color-danger); border: 1px solid var(--color-danger-mid); }

.screen-score { font-size: var(--font-size-sm-plus); font-weight: 700; color: var(--color-accent-strong); min-width: 28px; text-align: end; }

.pin-btn { background: none; border: none; cursor: pointer; font-size: var(--font-size-base); padding: 0 0.15rem; opacity: 0.35; transition: opacity 0.15s; min-height: 32px; }
.pin-btn:active, .pin-btn.active { opacity: 1; }

.score-bar-wrap { height: 4px; background: var(--color-border); border-radius: 2px; margin-bottom: 0.5rem; }
.score-bar { height: 100%; background: var(--color-accent); border-radius: 2px; transition: width 0.4s ease; max-width: 100%; }

.coin-indicators { display: flex; flex-wrap: wrap; gap: 0.4rem 0.9rem; }
.ind-item  { display: flex; flex-direction: column; gap: 0.05rem; }
.ind-label { font-size: var(--font-size-xs); color: var(--color-text-subtle); text-transform: uppercase; letter-spacing: 0.04em; }
.ind-val   { font-size: var(--font-size-base); font-weight: 600; }
.narrative-tag { font-size: var(--font-size-sm) !important; font-weight: 500 !important; color: var(--color-text-secondary) !important; }

.breakdown       { margin-top: 0.6rem; padding-top: 0.6rem; border-top: 1px solid var(--color-border); }
.breakdown-title { font-size: var(--font-size-sm); color: var(--color-text-disabled); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.4rem; font-weight: 600; }
.breakdown-row   { display: flex; align-items: baseline; gap: 0.4rem; padding: 0.15rem 0; }
.bd-key    { min-width: 150px; color: var(--color-text-secondary); font-size: var(--font-size-sm); }
.bd-pts    { min-width: 30px; font-weight: 700; font-size: var(--font-size-sm-plus); text-align: end; }
.bd-reason { color: var(--color-text-disabled); font-size: var(--font-size-sm); flex: 1; }

.levels       { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; margin-top: 0.4rem; }
.level-label  { color: var(--color-text-disabled); font-size: var(--font-size-sm); }
.support-val    { color: var(--color-success-strong); background: var(--color-success-bg); padding: 0.12rem 0.35rem; border-radius: 0.2rem; font-size: var(--font-size-sm); }
.resistance-val { color: var(--color-danger); background: var(--color-danger-bg); padding: 0.12rem 0.35rem; border-radius: 0.2rem; font-size: var(--font-size-sm); }

.full-analysis-btn { margin-top: 0.6rem; width: 100%; padding: 0.6rem; background: var(--color-accent-muted); border: 1px solid var(--color-accent); color: var(--color-accent-strong); border-radius: 0.4rem; cursor: pointer; font-size: var(--font-size-base); font-weight: 600; min-height: 44px; }
.full-analysis-btn:active { background: #1a3a5c; }

.stream-dot { font-size: var(--font-size-2xs-plus); color: var(--color-text-subtle); vertical-align: middle; margin-inline-start: 0.3rem; transition: color 0.4s; }
.stream-dot.live { color: var(--color-success); }
.empty-state { text-align: center; padding: 0.75rem; }
.empty       { color: var(--color-text-subtle); font-size: var(--font-size-base); margin-top: 0.5rem; }
.empty-hint  { font-size: var(--font-size-sm-plus); color: var(--color-text-subtle); margin-top: 0.2rem; }

.pos   { color: var(--color-success-strong); }
.neg   { color: var(--color-danger); }
.muted { color: var(--color-text-disabled); }

/* ── Live P&L row ────────────────────────────────────────────────────────── */
.pnl-row {
  display: flex; align-items: center; gap: 0.4rem;
  flex-wrap: wrap; margin-bottom: 0.4rem; font-size: var(--font-size-sm-plus);
}
.pnl-label       { color: var(--color-text-subtle); font-size: var(--font-size-sm); }
.pnl-entry-price { color: var(--color-text-disabled); font-weight: 600; }
.pnl-arrow       { color: var(--color-text-subtle); }
.pnl-now         { font-weight: 700; }
.pnl-badge {
  font-size: var(--font-size-sm-plus); font-weight: 700;
  padding: 0.12rem 0.55rem; border-radius: 0.35rem;
  margin-inline-start: auto; white-space: nowrap;
}
.pnl-pos { background: var(--color-success-bg); color: var(--color-success-strong); border: 1px solid var(--color-success-emphasis); }
.pnl-neg { background: var(--color-danger-bg); color: var(--color-danger); border: 1px solid var(--color-danger-mid); }

/* ── SL / Target range bar ───────────────────────────────────────────────── */
.sl-target-wrap {
  display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem;
}
.sl-label          { font-size: var(--font-size-sm); color: var(--color-danger); white-space: nowrap; font-weight: 600; }
.target-label      { font-size: var(--font-size-sm); color: var(--color-success-strong); white-space: nowrap; font-weight: 600; }
.trailing-sl-label { color: #7ec8e3; }
.trailing-peak-label { color: #b794f4; }
.pnl-peak          { font-size: var(--font-size-xs); color: #b794f4; white-space: nowrap; margin-inline-start: 0.25rem; }
.sl-bar-track {
  flex: 1; height: 8px; background: var(--color-border);
  border-radius: 4px; position: relative; overflow: visible;
}
.sl-bar-gradient {
  position: absolute; inset: 0; border-radius: 4px;
  background: linear-gradient(to right, var(--color-danger-vivid), #dd6b20, var(--color-success-emphasis));
  opacity: 0.65;
}
.sl-marker {
  position: absolute; top: -4px;
  width: 4px; height: 16px;
  background: var(--color-text); border-radius: 2px;
  transform: translateX(-50%);
  box-shadow: 0 0 4px rgba(0,0,0,0.7);
  z-index: 1;
  transition: left 0.4s ease;
}
</style>
