<template>
  <div class="trading-section">

    <div v-if="!m" class="card empty-card">
      <p class="empty">{{ t('macro.no_data') }}</p>
    </div>

    <div v-else class="macro-grid">

      <!-- ── BTC Dominance ──────────────────────────────────────────────── -->
      <div class="card dom-card" :class="`season-${m.season_color}`">
        <div class="dom-top">
          <div>
            <div class="dom-label">{{ t('macro.btc_dom') }}</div>
            <div class="dom-value">{{ m.btc_dominance?.toFixed(1) }}%</div>
            <div class="dom-change" v-if="m.btc_dominance_7d_change != null" :class="m.btc_dominance_7d_change < 0 ? 'falling' : 'rising'">
              {{ m.btc_dominance_7d_change > 0 ? '+' : '' }}{{ m.btc_dominance_7d_change?.toFixed(1) }}%
              {{ t('macro.dom_change', { d: 7 }) }}
            </div>
          </div>
          <div class="season-badge" :class="`badge-${m.season_color}`">
            {{ m.season_icon }} {{ ts('macro.season_' + m.market_season) }}
          </div>
        </div>
        <div class="dom-bar-wrap">
          <div class="dom-bar" :style="{ width: `${m.btc_dominance}%` }" />
        </div>
        <div class="season-advice">
          <div class="advice-row">
            <span class="advice-label">{{ t('macro.long_term') }}</span>
            <span class="advice-text">{{ ts('macro.lt_' + m.market_season) }}</span>
          </div>
          <div class="advice-row">
            <span class="advice-label">{{ t('macro.short_term') }}</span>
            <span class="advice-text">{{ ts('macro.st_' + m.market_season) }}</span>
          </div>
        </div>
      </div>

      <!-- ── Fear & Greed ──────────────────────────────────────────────── -->
      <div class="card fg-card">
        <div class="card-label">{{ t('macro.fg_title') }}</div>
        <div class="fg-body">
          <div class="fg-gauge-wrap">
            <svg viewBox="0 0 120 70" class="fg-gauge">
              <path d="M10,60 A50,50 0 0,1 110,60" fill="none" stroke="#2d3748" stroke-width="12" stroke-linecap="round"/>
              <path :d="gaugePath" fill="none" :stroke="fgColor" stroke-width="12" stroke-linecap="round"/>
              <line :x1="60" :y1="60" :x2="needleX" :y2="needleY" stroke="#e2e8f0" stroke-width="2" stroke-linecap="round"/>
              <circle cx="60" cy="60" r="3" fill="#e2e8f0"/>
            </svg>
            <div class="fg-value" :style="{ color: fgColor }">{{ m.fear_greed_value }}</div>
            <div class="fg-label-text" :style="{ color: fgColor }">{{ fgLabel(m.fear_greed_value) }}</div>
          </div>
          <div class="fg-history">
            <div class="fg-hist-row" v-if="m.fear_greed_yesterday != null">
              <span class="fg-hist-label">{{ t('macro.fg_yesterday') }}</span>
              <span class="fg-hist-val">{{ m.fear_greed_yesterday }} — {{ fgLabel(m.fear_greed_yesterday) }}</span>
            </div>
            <div class="fg-hist-row" v-if="m.fear_greed_last_week != null">
              <span class="fg-hist-label">{{ t('macro.fg_last_week') }}</span>
              <span class="fg-hist-val">{{ m.fear_greed_last_week }} — {{ fgLabel(m.fear_greed_last_week) }}</span>
            </div>
          </div>
        </div>
        <div class="fg-advice" v-if="m.fear_greed_value">
          <span class="advice-label">{{ t('macro.fg_advice') }}:</span> {{ fgAdvice(m.fear_greed_value) }}
        </div>
      </div>

      <!-- ── Active market sessions ─────────────────────────────────────── -->
      <SessionsStrip class="sessions-row" />

      <!-- ── Narrative tracker ─────────────────────────────────────────── -->
      <div class="card narrative-card">
        <div class="card-label">{{ t('macro.narratives_title') }}</div>
        <div class="narrative-list">
          <div v-for="group in narrativeGroups" :key="group.heat" class="narrative-group">
            <div class="heat-header" :class="`heat-${group.heat}`">
              {{ t(`macro.heat_${group.heat}`) }}
            </div>
            <div v-for="n in group.items" :key="n.name" class="narrative-item">
              <span class="narrative-name">{{ n.name }}</span>
              <span v-if="n.coins.length" class="narrative-coins">{{ n.coins.join(' · ') }}</span>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- ── Watchlist ────────────────────────────────────────────────────── -->
    <div class="card watchlist-card">
      <div class="card-label">{{ t('watchlist.title') }}</div>
      <div class="watchlist-groups">
        <div v-for="group in watchlistGroups" :key="group.type" class="wl-group">
          <div class="wl-group-header">{{ group.label }}</div>
          <div class="wl-coins">
            <div v-for="coin in group.coins" :key="coin.symbol" class="wl-coin">
              <span class="wl-symbol">{{ coin.symbol }}</span>
              <span class="wl-name">{{ coin.name }}</span>
              <span v-if="coin.narrative" class="wl-narrative">{{ coin.narrative }}</span>
              <span v-if="coin.is_narrative_leader" class="wl-leader">{{ t('watchlist.leader') }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="last-updated" v-if="m?.timestamp">
      {{ t('macro.last_updated') }}: {{ lastUpdated }}
      <button class="refresh-inline" @click="refresh" :disabled="loading">
        {{ loading ? '...' : '↻' }}
      </button>
    </div>

  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../../stores/platform'
import SessionsStrip from '../SessionsStrip.vue'

const { t, te } = useI18n()

// Safe dynamic key lookup — returns raw season name if key not yet translated
function ts(key, fallback) { return te(key) ? t(key) : (fallback ?? key.split('_').pop()) }
const store   = usePlatformStore()
const loading = ref(false)
const m       = computed(() => store.macro)

async function refresh() {
  loading.value = true
  try { await store.fetchMacro(true) } finally { loading.value = false }
}

onMounted(async () => {
  await Promise.all([
    store.fetchMacro(),
    store.fetchNarratives(),
    store.fetchWatchlist(),
  ])
})

// ── Fear & Greed ─────────────────────────────────────────────────────────────
const FG_COLORS = [
  [25,  '#fc8181'],
  [45,  '#f6ad55'],
  [55,  '#ecc94b'],
  [75,  '#9ae6b4'],
  [100, '#48bb78'],
]

function fgColorFor(v) {
  for (const [max, color] of FG_COLORS) if (v <= max) return color
  return '#48bb78'
}

function fgLabel(v) {
  if (!v && v !== 0) return '—'
  if (v <= 25) return t('macro.fg_extreme_fear')
  if (v <= 45) return t('macro.fg_fear')
  if (v <= 55) return t('macro.fg_neutral')
  if (v <= 75) return t('macro.fg_greed')
  return t('macro.fg_extreme_greed')
}

function fgAdvice(v) {
  if (!v) return ''
  if (v <= 25) return t('macro.fg_advice_extreme_fear')
  if (v <= 45) return t('macro.fg_advice_fear')
  if (v <= 55) return t('macro.fg_advice_neutral')
  if (v <= 75) return t('macro.fg_advice_greed')
  return t('macro.fg_advice_extreme_greed')
}

const fgColor = computed(() => fgColorFor(m.value?.fear_greed_value ?? 50))

const gaugePath = computed(() => {
  const val   = m.value?.fear_greed_value ?? 0
  const angle = Math.PI - (val / 100) * Math.PI
  const x = 60 + 50 * Math.cos(angle)
  const y = 60 - 50 * Math.sin(angle)
  return `M10,60 A50,50 0 0,1 ${x.toFixed(1)},${y.toFixed(1)}`
})

const needleX = computed(() => {
  const angle = Math.PI - ((m.value?.fear_greed_value ?? 0) / 100) * Math.PI
  return (60 + 42 * Math.cos(angle)).toFixed(1)
})
const needleY = computed(() => {
  const angle = Math.PI - ((m.value?.fear_greed_value ?? 0) / 100) * Math.PI
  return (60 - 42 * Math.sin(angle)).toFixed(1)
})

// ── Narratives ───────────────────────────────────────────────────────────────
const narrativeGroups = computed(() => {
  const order = ['hot', 'warming', 'cooling']
  return order.map(heat => ({
    heat,
    items: store.narratives.filter(n => n.heat === heat),
  })).filter(g => g.items.length)
})

// ── Watchlist ────────────────────────────────────────────────────────────────
const watchlistGroups = computed(() => {
  const coins = store.watchlist
  return [
    { type: 'long_term',  label: t('watchlist.long_term'),  coins: coins.filter(c => c.trade_type === 'long_term')  },
    { type: 'short_term', label: t('watchlist.short_term'), coins: coins.filter(c => c.trade_type === 'short_term') },
    { type: 'both',       label: t('watchlist.both'),       coins: coins.filter(c => c.trade_type === 'both')       },
  ].filter(g => g.coins.length)
})

const lastUpdated = computed(() => {
  if (!m.value?.timestamp) return ''
  return new Date(m.value.timestamp).toLocaleTimeString()
})
</script>

<style scoped>
.trading-section { display: flex; flex-direction: column; gap: 0.75rem; }

.empty-card { text-align: center; padding: 2rem; }

.macro-grid {
  display: flex; flex-direction: column; gap: 0.75rem;
}
@media (min-width: 600px) {
  .macro-grid { display: grid; grid-template-columns: 1fr 1fr; }
  .sessions-row  { grid-column: 1 / -1; }
  .narrative-card { grid-column: 1 / -1; }
}

.card-label {
  font-size: var(--font-size-sm-plus); color: var(--color-accent-strong);
  text-transform: uppercase; letter-spacing: 0.06em;
  margin-bottom: 0.6rem; font-weight: 700;
}

/* ── BTC Dominance ───────────────────────────────────────────────────────── */
.dom-card { display: flex; flex-direction: column; gap: 0.6rem; }
.dom-top  { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; flex-wrap: wrap; }
.dom-label { font-size: var(--font-size-sm-plus); color: var(--color-text-disabled); text-transform: uppercase; letter-spacing: 0.05em; }
.dom-value { font-size: 2rem; font-weight: 800; line-height: 1.1; }
.dom-change { font-size: var(--font-size-sm-plus); margin-top: 0.15rem; }
.dom-change.falling { color: var(--color-success-strong); }
.dom-change.rising  { color: var(--color-danger); }

.season-badge {
  font-size: var(--font-size-sm-plus); font-weight: 700;
  padding: 0.3rem 0.65rem; border-radius: 999px;
  white-space: nowrap; flex-shrink: 0;
}
.badge-green  { background: var(--color-success-bg); border: 1px solid var(--color-success-emphasis); color: var(--color-success-strong); }
.badge-orange { background: var(--color-warning-bg); border: 1px solid var(--color-warning-emphasis); color: var(--color-warning); }
.badge-yellow { background: var(--color-warning-bg); border: 1px solid var(--color-warning-emphasis); color: var(--color-warning-tint); }

.dom-bar-wrap { height: 6px; background: var(--color-border); border-radius: 3px; overflow: hidden; }
.dom-bar { height: 100%; border-radius: 3px; transition: width 0.5s ease; }
.season-green  .dom-bar { background: var(--color-success-strong); }
.season-orange .dom-bar { background: var(--color-warning); }
.season-yellow .dom-bar { background: var(--color-warning-tint); }

.season-advice { display: flex; flex-direction: column; gap: 0.3rem; }
.advice-row    { display: flex; gap: 0.4rem; font-size: var(--font-size-base); flex-wrap: wrap; }
.advice-label  { color: var(--color-text-disabled); font-size: var(--font-size-sm-plus); flex-shrink: 0; }
.advice-text   { color: var(--color-text); }

.season-green  { border-color: var(--color-success-emphasis) !important; background: #111a11; }
.season-orange { border-color: var(--color-warning-emphasis) !important; background: #1a1408; }
.season-yellow { border-color: var(--color-warning-emphasis) !important; background: #181508; }

/* ── Fear & Greed ────────────────────────────────────────────────────────── */
.fg-card { display: flex; flex-direction: column; }
.fg-body { display: flex; gap: 0.75rem; align-items: flex-start; flex-wrap: wrap; }

.fg-gauge-wrap { display: flex; flex-direction: column; align-items: center; min-width: 110px; }
.fg-gauge      { width: 110px; }
.fg-value      { font-size: 1.6rem; font-weight: 800; line-height: 1; margin-top: -0.5rem; }
.fg-label-text { font-size: var(--font-size-sm-plus); font-weight: 600; margin-top: 0.1rem; }

.fg-history  { display: flex; flex-direction: column; gap: 0.35rem; flex: 1; padding-top: 0.25rem; }
.fg-hist-row { display: flex; flex-direction: column; gap: 0.05rem; }
.fg-hist-label { font-size: var(--font-size-sm); color: var(--color-text-disabled); text-transform: uppercase; letter-spacing: 0.04em; }
.fg-hist-val   { font-size: var(--font-size-base); color: var(--color-text-secondary); }

.fg-advice {
  font-size: var(--font-size-base); color: var(--color-text-secondary);
  background: var(--color-border); padding: 0.5rem 0.65rem;
  border-radius: 0.4rem; margin-top: 0.5rem; line-height: 1.4;
}

/* ── Narratives ──────────────────────────────────────────────────────────── */
.narrative-list  { display: flex; flex-direction: column; gap: 0.75rem; }
.narrative-group { display: flex; flex-direction: column; gap: 0.3rem; }

@media (min-width: 480px) {
  .narrative-list { flex-direction: row; gap: 1rem; }
  .narrative-group { flex: 1; }
}

.heat-header {
  font-size: var(--font-size-sm-plus); font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.05em;
  padding: 0.2rem 0; border-bottom: 1px solid var(--color-border); margin-bottom: 0.2rem;
}
.heat-hot     .heat-header, .heat-hot     { color: var(--color-danger); }
.heat-warming .heat-header, .heat-warming { color: var(--color-warning); }
.heat-cooling .heat-header, .heat-cooling { color: var(--color-text-disabled); }

.narrative-item { display: flex; flex-direction: column; gap: 0.05rem; padding: 0.25rem 0; border-bottom: 1px solid var(--color-surface); }
.narrative-name  { font-size: var(--font-size-base); font-weight: 600; color: var(--color-text); }
.narrative-coins { font-size: var(--font-size-sm); color: var(--color-text-disabled); }

/* ── Watchlist ───────────────────────────────────────────────────────────── */
.watchlist-groups { display: flex; flex-direction: column; gap: 0.75rem; }
@media (min-width: 480px) {
  .watchlist-groups { flex-direction: row; }
  .wl-group { flex: 1; }
}

.wl-group-header { font-size: var(--font-size-sm-plus); color: var(--color-text-disabled); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem; font-weight: 600; }
.wl-coins { display: flex; flex-direction: column; gap: 0.35rem; }
.wl-coin  { display: flex; align-items: baseline; gap: 0.4rem; flex-wrap: wrap; }
.wl-symbol   { font-size: 1.05rem; font-weight: 700; color: var(--color-accent-strong); min-width: 40px; }
.wl-name     { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }
.wl-narrative { font-size: var(--font-size-sm); color: var(--color-text-subtle); background: var(--color-border); padding: 0.1rem 0.35rem; border-radius: 999px; }
.wl-leader   { font-size: var(--font-size-sm); color: var(--color-warning-tint); }

.last-updated {
  font-size: var(--font-size-sm); color: var(--color-text-subtle);
  display: flex; align-items: center; justify-content: flex-end; gap: 0.5rem;
  margin-top: -0.25rem;
}
.refresh-inline {
  background: none; border: 1px solid var(--color-border-muted); color: var(--color-text-muted);
  padding: 0.1rem 0.4rem; border-radius: 0.3rem; cursor: pointer;
  font-size: var(--font-size-base); line-height: 1;
}
.refresh-inline:active { background: var(--color-border); color: var(--color-text); }
</style>
