<template>
  <div class="card analytics-card">
    <div class="card-header">
      <h2>{{ t('analytics.title') }}</h2>
      <div class="range-toggle">
        <button :class="['range-btn', { active: days === 7  }]" @click="setDays(7)">7d</button>
        <button :class="['range-btn', { active: days === 30 }]" @click="setDays(30)">30d</button>
      </div>
    </div>

    <!-- ── Context strip ─────────────────────────────────────────────── -->
    <div v-if="ctx?.ok" class="context-strip">
      <div class="ctx-item">
        <span class="ctx-label">{{ t('analytics.current_gap') }}</span>
        <span class="ctx-val">{{ fmt(ctx.current_spread) }} SDG</span>
      </div>
      <div class="ctx-item">
        <span class="ctx-label">{{ t('analytics.avg_label', { days }) }}</span>
        <span class="ctx-val">{{ fmt(ctx.spread_avg) }} SDG</span>
      </div>
      <div class="ctx-item">
        <span class="ctx-label">{{ t('analytics.vs_avg') }}</span>
        <span class="ctx-val" :class="vsAvgClass">{{ vsAvgLabel }}</span>
      </div>
      <div class="ctx-item">
        <span class="ctx-label">{{ t('analytics.percentile') }}</span>
        <span class="ctx-val" :class="pctClass">{{ pctLabel }}</span>
      </div>
      <div class="ctx-item">
        <span class="ctx-label">{{ t('analytics.rate_range') }}</span>
        <span class="ctx-val range-val">
          {{ fmt(ctx.rate_24h_low) }} – {{ fmt(ctx.rate_24h_high) }}
        </span>
      </div>
      <div class="ctx-item">
        <span class="ctx-label">{{ t('analytics.data_points') }}</span>
        <span class="ctx-val muted">{{ ctx.sample_count }} {{ t('analytics.polls') }}</span>
      </div>
    </div>
    <p v-else-if="ctx && !ctx.ok" class="empty">{{ t('analytics.no_history') }}</p>

    <!-- ── Spread history chart ──────────────────────────────────────── -->
    <div v-if="chartPoints.length > 1" class="chart-section">
      <div class="section-title">{{ t('analytics.chart_title') }}</div>
      <div class="chart-wrap">
        <svg :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="none" class="chart-svg">
          <!-- zero / reference line at spread = 0 -->
          <line :x1="0" :y1="yPos(0)" :x2="W" :y2="yPos(0)"
                stroke="#4a5568" stroke-width="0.5" stroke-dasharray="3,3"/>
          <!-- average reference line -->
          <line v-if="ctx?.spread_avg != null"
                :x1="0" :y1="yPos(ctx.spread_avg)" :x2="W" :y2="yPos(ctx.spread_avg)"
                stroke="#718096" stroke-width="0.8" stroke-dasharray="5,3"/>
          <!-- area fill -->
          <path :d="areaPath" class="chart-area"/>
          <!-- line -->
          <polyline :points="chartPoints" class="chart-line"/>
          <!-- current value dot -->
          <circle v-if="chartPts.length"
            :cx="chartPts[chartPts.length-1].x"
            :cy="chartPts[chartPts.length-1].y"
            r="3" class="chart-dot"/>
        </svg>
        <!-- Y axis labels -->
        <div class="y-labels">
          <span>{{ fmt(yMax) }}</span>
          <span>{{ fmt(ctx?.spread_avg) }}</span>
          <span>{{ fmt(yMin) }}</span>
        </div>
      </div>
      <div class="chart-legend">
        <span class="legend-avg">— {{ t('analytics.chart_avg_label', { days, val: fmt(ctx?.spread_avg) }) }}</span>
        <span class="legend-note">{{ t('analytics.chart_note') }}</span>
      </div>
    </div>

    <!-- ── Hourly pattern chart ──────────────────────────────────────── -->
    <div v-if="hasPatternData" class="chart-section">
      <div class="section-title">{{ t('analytics.pattern_title') }}</div>
      <div class="pattern-grid">
        <div v-for="slot in store.hourlyPatterns" :key="slot.hour" class="pattern-slot">
          <div class="pattern-bar-wrap" :title="slotTitle(slot)">
            <div class="pattern-bar"
                 :style="patternBarStyle(slot)"
                 :class="{ unreliable: !slot.reliable }"/>
          </div>
          <span v-if="slot.hour % 6 === 0" class="pattern-label">{{ slot.hour }}:00</span>
        </div>
      </div>
      <div class="pattern-legend">
        <span class="legend-green">{{ t('analytics.pattern_wide') }}</span>
        <span class="legend-red">{{ t('analytics.pattern_tight') }}</span>
        <span class="legend-gray">{{ t('analytics.pattern_nodata') }}</span>
      </div>
    </div>
    <div v-else-if="store.hourlyPatterns.length" class="empty" style="margin-top:0.75rem">
      {{ t('analytics.no_patterns') }}
    </div>

  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../stores/platform'

const { t } = useI18n()
const store = usePlatformStore()
const days  = ref(7)

const W = 400
const H = 80

const ctx = computed(() => store.marketContext)

// ── Chart geometry ────────────────────────────────────────────────────────────
const history = computed(() => store.spreadHistory.filter(p => p.spread != null))

const yMin = computed(() => history.value.length ? Math.min(...history.value.map(p => p.spread)) : 0)
const yMax = computed(() => history.value.length ? Math.max(...history.value.map(p => p.spread)) : 20)

function yPos(v) {
  const pad = 6
  const range = (yMax.value - yMin.value) || 1
  return pad + (1 - (v - yMin.value) / range) * (H - pad * 2)
}

const chartPts = computed(() =>
  history.value.map((p, i) => ({
    x: history.value.length > 1 ? (i / (history.value.length - 1)) * W : W / 2,
    y: yPos(p.spread),
  }))
)

const chartPoints = computed(() =>
  chartPts.value.map(p => `${p.x},${p.y}`).join(' ')
)

const areaPath = computed(() => {
  if (!chartPts.value.length) return ''
  const pts = chartPts.value.map(p => `${p.x},${p.y}`).join(' ')
  return `M0,${H} ${pts} ${W},${H} Z`
})

// ── Context labels ─────────────────────────────────────────────────────────
const vsAvgLabel = computed(() => {
  const v = ctx.value?.spread_vs_avg
  if (v == null) return '—'
  return v >= 0 ? `+${v.toFixed(1)} SDG` : `${v.toFixed(1)} SDG`
})
const vsAvgClass = computed(() => {
  const v = ctx.value?.spread_vs_avg
  if (v == null) return ''
  return v >= 0 ? 'positive' : 'negative'
})

const pctLabel = computed(() => {
  const p = ctx.value?.spread_percentile
  if (p == null) return '—'
  if (p >= 75) return t('analytics.pct_great', { p })
  if (p >= 50) return t('analytics.pct_ok',    { p })
  return t('analytics.pct_low', { p })
})
const pctClass = computed(() => {
  const p = ctx.value?.spread_percentile
  if (p == null) return ''
  if (p >= 75) return 'positive'
  if (p >= 50) return ''
  return 'negative'
})

// ── Pattern bars ──────────────────────────────────────────────────────────────
const reliablePatterns = computed(() =>
  store.hourlyPatterns.filter(s => s.reliable)
)
const hasPatternData = computed(() => reliablePatterns.value.length >= 6)

const patMax = computed(() => {
  const vals = reliablePatterns.value.map(s => s.avg_spread)
  return vals.length ? Math.max(...vals) : 1
})
const patMin = computed(() => {
  const vals = reliablePatterns.value.map(s => s.avg_spread)
  return vals.length ? Math.min(...vals) : 0
})

function patternBarStyle(slot) {
  if (!slot.reliable || slot.avg_spread == null) {
    return { height: '20%', background: '#2d3748' }
  }
  const range = (patMax.value - patMin.value) || 1
  const pct   = Math.max(15, ((slot.avg_spread - patMin.value) / range) * 100)
  // Interpolate colour: red (tight) → yellow → green (wide)
  const ratio = (slot.avg_spread - patMin.value) / range
  const r = Math.round(252 - ratio * (252 - 104))
  const g = Math.round(129 + ratio * (211 - 129))
  const b = Math.round(74  - ratio * (74  - 80))
  return { height: `${pct}%`, background: `rgb(${r},${g},${b})` }
}

function slotTitle(slot) {
  if (!slot.reliable) return t('analytics.slot_no_data', { hour: slot.hour, count: slot.sample_count })
  return t('analytics.slot_avg', { hour: slot.hour, val: slot.avg_spread, count: slot.sample_count })
}

function fmt(v) {
  return v != null ? Number(v).toFixed(2) : '—'
}

// ── Data loading ─────────────────────────────────────────────────────────────
async function setDays(d) {
  days.value = d
  await store.fetchAnalytics(d)
}

onMounted(() => store.fetchAnalytics(days.value))
</script>

<style scoped>
.analytics-card { display: flex; flex-direction: column; gap: 1rem; }

/* Range toggle */
.range-toggle { display: flex; gap: 0.35rem; }
.range-btn {
  background: #2d3748; border: 1px solid #4a5568;
  color: #a0aec0; padding: 0.25rem 0.6rem;
  border-radius: 0.35rem; cursor: pointer; font-size: 0.8rem; min-height: 32px;
}
.range-btn.active { background: #2c4a6e; color: #90cdf4; border-color: #63b3ed; }

/* Context strip */
.context-strip {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.6rem 1rem;
}
@media (min-width: 480px) { .context-strip { grid-template-columns: repeat(3, 1fr); } }

.ctx-item   { display: flex; flex-direction: column; gap: 0.15rem; }
.ctx-label  { font-size: 0.65rem; color: #718096; text-transform: uppercase; letter-spacing: 0.04em; }
.ctx-val    { font-size: 0.95rem; font-weight: 600; }
.ctx-val.positive { color: #68d391; }
.ctx-val.negative { color: #fc8181; }
.ctx-val.muted    { color: #718096; font-weight: 400; font-size: 0.8rem; }
.ctx-val.range-val { font-size: 0.82rem; font-weight: 500; }

/* Section titles */
.section-title {
  font-size: 0.7rem; color: #718096;
  text-transform: uppercase; letter-spacing: 0.04em;
  margin-bottom: 0.4rem;
}
.chart-section { display: flex; flex-direction: column; }

/* SVG spread chart */
.chart-wrap { display: flex; align-items: stretch; gap: 0.4rem; }
.chart-svg  { flex: 1; height: 80px; display: block; }
.chart-area { fill: rgba(99,179,237,0.12); }
.chart-line { fill: none; stroke: #63b3ed; stroke-width: 1.5; stroke-linejoin: round; }
.chart-dot  { fill: #63b3ed; }

.y-labels {
  display: flex; flex-direction: column;
  justify-content: space-between;
  font-size: 0.6rem; color: #4a5568;
  text-align: right; padding: 4px 0;
  min-width: 36px;
}

.chart-legend {
  display: flex; justify-content: space-between;
  font-size: 0.65rem; color: #4a5568;
  margin-top: 0.25rem;
}
.legend-avg  { color: #718096; }
.legend-note { color: #4a5568; }

/* Hourly pattern bars */
.pattern-grid {
  display: flex;
  align-items: flex-end;
  gap: 2px;
  height: 64px;
}
.pattern-slot { display: flex; flex-direction: column; align-items: center; flex: 1; height: 100%; }
.pattern-bar-wrap { flex: 1; width: 100%; display: flex; align-items: flex-end; }
.pattern-bar {
  width: 100%; border-radius: 2px 2px 0 0;
  transition: height 0.3s ease;
  cursor: default;
}
.pattern-bar.unreliable { opacity: 0.3; }
.pattern-label { font-size: 0.55rem; color: #4a5568; margin-top: 2px; white-space: nowrap; }

.pattern-legend {
  display: flex; gap: 0.75rem; flex-wrap: wrap;
  font-size: 0.65rem; color: #718096; margin-top: 0.4rem;
}
.legend-green { color: #68d391; }
.legend-red   { color: #fc8181; }
.legend-gray  { color: #4a5568; }
</style>
