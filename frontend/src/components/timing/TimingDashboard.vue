<template>
  <div class="timing-dash">

    <!-- ── Traffic light ─────────────────────────────────────────────────── -->
    <div class="card signal-card">
      <div class="signal-left">
        <div class="signal-dot" :class="signal.cls"></div>
        <div class="signal-text">
          <div class="signal-label">{{ signal.label }}</div>
          <div class="signal-sub">{{ signal.sub }}</div>
        </div>
      </div>
      <div class="signal-stats">
        <div class="sig-stat">
          <span class="sig-stat-label">{{ t('timing.now') }}</span>
          <span class="sig-stat-val">{{ fmtSpread(ctx?.current_spread) }}</span>
        </div>
        <div class="sig-stat">
          <span class="sig-stat-label">{{ t('timing.avg_this_hour') }}</span>
          <span class="sig-stat-val">{{ fmtSpread(hourAvg) }}</span>
        </div>
        <div class="sig-stat">
          <span class="sig-stat-label">{{ t('timing.percentile') }}</span>
          <span class="sig-stat-val" :class="pctClass">{{ ctx?.spread_percentile != null ? ctx.spread_percentile + '%' : '—' }}</span>
        </div>
      </div>
    </div>

    <!-- ── Market sessions ───────────────────────────────────────────────── -->
    <div class="card sessions-card">
      <div class="sessions-header">
        <h2>{{ t('timing.sessions_title') }}</h2>
        <div class="tz-badge">🕐 {{ localTimeStr }} &nbsp;·&nbsp; {{ tzShort }}</div>
      </div>
      <div class="sessions-row">
        <div v-for="s in sessions" :key="s.name" class="session-chip" :class="{ active: s.active }">
          <span class="ses-flag">{{ s.flag }}</span>
          <div class="ses-info">
            <span class="ses-name">{{ s.name }}</span>
            <span class="ses-hours">{{ s.localHours }}</span>
            <span class="ses-desc">{{ t('timing.' + s.descKey) }}</span>
          </div>
          <span v-if="s.active" class="ses-live">{{ t('timing.live') }}</span>
        </div>
      </div>
      <p class="session-note">{{ t('timing.session_note') }}</p>
    </div>

    <!-- ── Weekly heatmap ─────────────────────────────────────────────────── -->
    <div class="card heatmap-card">
      <div class="card-header">
        <h2>{{ t('timing.heatmap_title') }}</h2>
        <span class="tz-note">{{ t('timing.local_tz') }}</span>
      </div>
      <p class="heatmap-hint">{{ t('timing.heatmap_hint') }}</p>

      <div v-if="hasHeatmapData" class="heatmap-wrap">
        <!-- Hour labels along top -->
        <div class="heatmap-grid">
          <!-- top-left corner spacer -->
          <div class="hm-corner"></div>
          <div v-for="h in displayHours" :key="'h'+h" class="hm-hour-label"
               :class="{ 'hm-current': h === localHour }">
            {{ h % 6 === 0 ? h + ':00' : '' }}
          </div>

          <!-- Rows: one per day -->
          <template v-for="day in 7" :key="'row'+day">
            <div class="hm-day-label" :class="{ 'hm-today': (day - 1) === localWeekday }">
              {{ t('timing.days.' + (day - 1)) }}
            </div>
            <div v-for="h in displayHours" :key="'c'+(day-1)+'-'+h"
                 class="hm-cell"
                 :style="cellStyle(day - 1, h)"
                 :class="{
                   'hm-current': (day - 1) === localWeekday && h === localHour,
                   'hm-no-data': cellValue(day - 1, h) == null,
                 }"
                 :title="cellTitle(day - 1, h)">
            </div>
          </template>
        </div>

        <!-- Legend -->
        <div class="hm-legend">
          <span class="hm-leg-swatch hm-leg-nodata"></span><span>{{ t('timing.no_data') }}</span>
          <span class="hm-leg-swatch" style="background:#c53030"></span><span>{{ t('timing.tight') }}</span>
          <span class="hm-leg-swatch" style="background:#d69e2e"></span><span>{{ t('timing.moderate') }}</span>
          <span class="hm-leg-swatch" style="background:#276749"></span><span>{{ t('timing.wide') }}</span>
          <span class="hm-leg-current"></span><span>{{ t('timing.now_marker') }}</span>
        </div>
      </div>

      <div v-else class="empty heatmap-empty">
        {{ t('timing.heatmap_empty') }}
      </div>
    </div>

    <!-- ── Day-of-week bars ───────────────────────────────────────────────── -->
    <div class="card weekday-card">
      <h2>{{ t('timing.weekday_title') }}</h2>
      <p class="heatmap-hint">{{ t('timing.weekday_hint') }}</p>
      <div v-if="hasWeekdayData" class="weekday-bars">
        <div v-for="(slot, i) in store.weekdayPatterns" :key="i" class="wd-col">
          <div class="wd-bar-wrap" :title="wdTitle(slot)">
            <div class="wd-bar"
                 :style="wdBarStyle(slot)"
                 :class="{ 'wd-today': i === localWeekday, 'wd-unreliable': !slot.reliable }"/>
          </div>
          <span class="wd-label" :class="{ 'wd-today-label': i === localWeekday }">
            {{ t('timing.days_short.' + i) }}
          </span>
          <span class="wd-val">{{ slot.avg_spread != null ? slot.avg_spread.toFixed(0) : '—' }}</span>
        </div>
      </div>
      <div v-else class="empty">{{ t('timing.weekday_empty') }}</div>
    </div>

    <!-- ── Hourly bars (existing data, larger view) ───────────────────────── -->
    <div class="card hourly-card">
      <h2>{{ t('timing.hourly_title') }}</h2>
      <p class="heatmap-hint">{{ t('timing.hourly_hint') }}</p>
      <div v-if="hasHourlyData" class="hourly-bars">
        <div v-for="slot in store.hourlyPatterns" :key="slot.hour" class="hr-col">
          <div class="hr-bar-wrap" :title="hrTitle(slot)">
            <div class="hr-bar"
                 :style="hrBarStyle(slot)"
                 :class="{
                   'hr-current': slot.hour === utcHour,
                   'hr-unreliable': !slot.reliable,
                 }"/>
          </div>
          <span v-if="slot.hour % 6 === 0" class="hr-label">{{ localHourLabel(slot.hour) }}</span>
        </div>
      </div>
      <div v-else class="empty">{{ t('timing.hourly_empty') }}</div>
      <p class="tz-foot">{{ t('timing.local_tz') }}</p>
    </div>

  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../../stores/platform'

const { t } = useI18n()
const store = usePlatformStore()

// ── Clock ─────────────────────────────────────────────────────────────────────
const now = ref(new Date())
let clockTimer
onMounted(() => {
  store.fetchTimingData()
  store.fetchAnalytics(30)      // also load hourly patterns
  clockTimer = setInterval(() => { now.value = new Date() }, 60_000)
})
onUnmounted(() => clearInterval(clockTimer))

const utcHour    = computed(() => now.value.getUTCHours())
const localHour  = computed(() => now.value.getHours())
// 0=Mon…6=Sun (JS getDay: 0=Sun)
const localWeekday = computed(() => (now.value.getDay() + 6) % 7)
// UTC offset in hours (positive = east of UTC)
const tzOffset   = computed(() => -now.value.getTimezoneOffset() / 60)

const localTimeStr = computed(() =>
  now.value.toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit', hour12: false })
)
const tzShort = computed(() => {
  const name = Intl.DateTimeFormat().resolvedOptions().timeZone
  const off  = tzOffset.value
  const sign = off >= 0 ? '+' : '-'
  return `${name} (UTC${sign}${Math.abs(off)})`
})

// Map UTC hour to local hour for display column order
function utcToLocal(utcH) {
  return ((utcH + tzOffset.value) % 24 + 24) % 24
}
function localToUtc(localH) {
  return ((localH - tzOffset.value) % 24 + 24) % 24
}

// 24 display hours in local time order
const displayHours = computed(() => Array.from({ length: 24 }, (_, i) => i))

// ── Market context ────────────────────────────────────────────────────────────
const ctx = computed(() => store.marketContext)

// Avg spread for the current UTC hour from hourly patterns
const hourAvg = computed(() => {
  const slot = store.hourlyPatterns.find(p => p.hour === utcHour.value)
  return slot?.reliable ? slot.avg_spread : null
})

const overallAvg = computed(() => ctx.value?.spread_avg ?? null)

// ── Traffic light ─────────────────────────────────────────────────────────────
const signal = computed(() => {
  const spread = ctx.value?.current_spread
  const pct    = ctx.value?.spread_percentile

  if (spread == null) return { cls: 'sig-grey', label: t('timing.sig_loading'), sub: '' }

  const hourGood = hourAvg.value != null && overallAvg.value != null
    ? hourAvg.value >= overallAvg.value
    : true

  if (pct >= 65 && hourGood)
    return { cls: 'sig-green', label: t('timing.sig_green'), sub: t('timing.sig_green_sub') }
  if (pct >= 40 || hourGood)
    return { cls: 'sig-yellow', label: t('timing.sig_yellow'), sub: t('timing.sig_yellow_sub') }
  return { cls: 'sig-red', label: t('timing.sig_red'), sub: t('timing.sig_red_sub') }
})

const pctClass = computed(() => {
  const p = ctx.value?.spread_percentile
  if (p == null) return ''
  return p >= 65 ? 'pos' : p >= 40 ? '' : 'neg'
})

// ── Sessions ──────────────────────────────────────────────────────────────────
const sessions = computed(() => {
  const h = utcHour.value
  const tz = tzOffset.value
  function localRange(s, e) {
    const ls = ((s + tz) % 24 + 24) % 24
    const le = ((e + tz) % 24 + 24) % 24
    return `${String(ls).padStart(2, '0')}:00–${String(le).padStart(2, '0')}:00`
  }
  return [
    { flag: '🌏', name: t('timing.ses_asian'),  localHours: localRange(0, 8),   descKey: 'ses_asian_desc',  active: h >= 0  && h < 8  },
    { flag: '🌍', name: t('timing.ses_london'), localHours: localRange(7, 16),  descKey: 'ses_london_desc', active: h >= 7  && h < 16 },
    { flag: '🌎', name: t('timing.ses_us'),     localHours: localRange(13, 22), descKey: 'ses_us_desc',     active: h >= 13 && h < 22 },
  ]
})

// ── Heatmap ───────────────────────────────────────────────────────────────────
const heatmapMap = computed(() => {
  const m = new Map()
  for (const cell of store.heatmap) {
    m.set(`${cell.day}-${cell.hour}`, cell)
  }
  return m
})

function cellData(day, localH) {
  const utcH = localToUtc(localH)
  return heatmapMap.value.get(`${day}-${Math.round(utcH)}`) ?? null
}

function cellValue(day, localH) {
  return cellData(day, localH)?.avg_spread ?? null
}

// Global min/max across all reliable cells for colour scaling
const heatmapRange = computed(() => {
  const vals = store.heatmap.filter(c => c.reliable && c.avg_spread != null).map(c => c.avg_spread)
  if (!vals.length) return { min: 0, max: 1 }
  return { min: Math.min(...vals), max: Math.max(...vals) }
})

function cellStyle(day, localH) {
  const val = cellValue(day, localH)
  if (val == null) return {}
  const { min, max } = heatmapRange.value
  const ratio = (max - min) < 0.01 ? 0.5 : (val - min) / (max - min)
  // red(tight) → yellow(mid) → green(wide)
  const r = Math.round(197 - ratio * (197 - 39))
  const g = Math.round(48  + ratio * (103 - 48))
  const b = Math.round(48  - ratio * (48  - 73))
  return { background: `rgb(${r},${g},${b})` }
}

function cellTitle(day, localH) {
  const d = cellData(day, localH)
  if (!d || d.avg_spread == null) return t('timing.cell_no_data')
  return t('timing.cell_tip', { spread: d.avg_spread.toFixed(1), n: d.sample_count })
}

const hasHeatmapData = computed(() =>
  store.heatmap.some(c => c.reliable)
)

// ── Weekday bars ──────────────────────────────────────────────────────────────
const hasWeekdayData = computed(() =>
  store.weekdayPatterns.some(s => s.reliable)
)

const wdMax = computed(() => {
  const vals = store.weekdayPatterns.filter(s => s.reliable && s.avg_spread != null).map(s => s.avg_spread)
  return vals.length ? Math.max(...vals) : 1
})
const wdMin = computed(() => {
  const vals = store.weekdayPatterns.filter(s => s.reliable && s.avg_spread != null).map(s => s.avg_spread)
  return vals.length ? Math.min(...vals) : 0
})

function wdBarStyle(slot) {
  if (!slot.reliable || slot.avg_spread == null) return { height: '15%', background: '#2d3748' }
  const range = (wdMax.value - wdMin.value) || 1
  const pct   = Math.max(15, ((slot.avg_spread - wdMin.value) / range) * 100)
  const ratio = (slot.avg_spread - wdMin.value) / range
  const r = Math.round(197 - ratio * (197 - 39))
  const g = Math.round(48  + ratio * (103 - 48))
  const b = Math.round(48  - ratio * (48  - 73))
  return { height: `${pct}%`, background: `rgb(${r},${g},${b})` }
}

function wdTitle(slot) {
  if (!slot.reliable) return t('timing.no_data_yet', { n: slot.sample_count })
  return t('timing.wd_tip', { spread: slot.avg_spread?.toFixed(1), n: slot.sample_count })
}

// ── Hourly bars ───────────────────────────────────────────────────────────────
const hasHourlyData = computed(() =>
  store.hourlyPatterns.some(s => s.reliable)
)

const hrMax = computed(() => {
  const vals = store.hourlyPatterns.filter(s => s.reliable && s.avg_spread != null).map(s => s.avg_spread)
  return vals.length ? Math.max(...vals) : 1
})
const hrMin = computed(() => {
  const vals = store.hourlyPatterns.filter(s => s.reliable && s.avg_spread != null).map(s => s.avg_spread)
  return vals.length ? Math.min(...vals) : 0
})

function hrBarStyle(slot) {
  if (!slot.reliable || slot.avg_spread == null) return { height: '15%', background: '#2d3748' }
  const range = (hrMax.value - hrMin.value) || 1
  const pct   = Math.max(15, ((slot.avg_spread - hrMin.value) / range) * 100)
  const ratio = (slot.avg_spread - hrMin.value) / range
  const r = Math.round(197 - ratio * (197 - 39))
  const g = Math.round(48  + ratio * (103 - 48))
  const b = Math.round(48  - ratio * (48  - 73))
  return { height: `${pct}%`, background: `rgb(${r},${g},${b})` }
}

function hrTitle(slot) {
  const lh = utcToLocal(slot.hour)
  if (!slot.reliable) return t('timing.no_data_yet', { n: slot.sample_count })
  return t('timing.hr_tip', { hour: lh, spread: slot.avg_spread?.toFixed(1), n: slot.sample_count })
}

function localHourLabel(utcH) {
  return utcToLocal(utcH) + ':00'
}

function fmtSpread(v) {
  return v != null ? v.toFixed(1) + ' SDG' : '—'
}
</script>

<style scoped>
.timing-dash { display: flex; flex-direction: column; gap: 1rem; }

/* ── Traffic light card ───────────────────────────────────────────────────── */
.signal-card {
  display: flex; flex-wrap: wrap;
  align-items: center; gap: 1rem;
  padding: 1.25rem 1rem;
}
.signal-left { display: flex; align-items: center; gap: 1rem; flex: 1; min-width: 200px; }
.signal-dot {
  width: 52px; height: 52px; border-radius: 50%; flex-shrink: 0;
  box-shadow: 0 0 18px currentColor;
}
.sig-green  { background: var(--color-success-medium); color: var(--color-success-medium); }
.sig-yellow { background: var(--color-warning); color: var(--color-warning); }
.sig-red    { background: var(--color-danger-vivid); color: var(--color-danger-vivid); }
.sig-grey   { background: var(--color-text-muted); color: var(--color-text-muted); }

.signal-label { font-size: 1.35rem; font-weight: 700; color: var(--color-text); }
.signal-sub   { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); margin-top: 0.2rem; }

.signal-stats { display: flex; gap: 1.25rem; flex-wrap: wrap; }
.sig-stat { display: flex; flex-direction: column; gap: 0.15rem; }
.sig-stat-label { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); text-transform: uppercase; letter-spacing: 0.04em; }
.sig-stat-val   { font-size: 1.15rem; font-weight: 700; }
.pos { color: var(--color-success-strong); }
.neg { color: var(--color-danger); }

/* ── Sessions card ────────────────────────────────────────────────────────── */
.sessions-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.75rem; flex-wrap: wrap; gap: 0.5rem; }
.sessions-header h2 { font-size: 1.1rem; margin: 0; }
.tz-badge { font-size: var(--font-size-base); color: var(--color-accent-strong); font-weight: 500; }
.sessions-row { display: flex; flex-wrap: wrap; gap: 0.6rem; }
.session-chip {
  display: flex; align-items: center; gap: 0.6rem;
  background: var(--color-border); border: 1px solid var(--color-text-muted);
  border-radius: 0.5rem; padding: 0.65rem 0.9rem;
  transition: border-color 0.2s, background 0.2s;
}
.session-chip.active { border-color: var(--color-accent); background: #1a2c42; }
.ses-flag { font-size: 1.3rem; }
.ses-info { display: flex; flex-direction: column; gap: 0.1rem; }
.ses-name  { font-size: var(--font-size-sm-plus); font-weight: 600; color: var(--color-text); }
.ses-hours { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); }
.ses-desc  { font-size: var(--font-size-sm-plus); color: var(--color-text-cool); }
.ses-live  {
  font-size: var(--font-size-sm-plus); font-weight: 700; color: var(--color-success);
  background: var(--color-success-bg); border: 1px solid var(--color-success-emphasis);
  border-radius: 999px; padding: 0.1rem 0.45rem; margin-inline-start: 0.2rem;
  white-space: nowrap;
}
.session-note { font-size: var(--font-size-base); color: var(--color-text-secondary-bright); margin-top: 0.6rem; }

/* ── Heatmap ──────────────────────────────────────────────────────────────── */
.heatmap-card h2, .weekday-card h2, .hourly-card h2 {
  font-size: 1.1rem; margin-bottom: 0.25rem;
}
.heatmap-hint { font-size: var(--font-size-base); color: var(--color-text-cool); margin-bottom: 0.75rem; }
.tz-note { font-size: var(--font-size-sm-plus); color: var(--color-text-cool); }
.tz-foot { font-size: var(--font-size-sm-plus); color: var(--color-text-cool); margin-top: 0.5rem; text-align: end; }

.heatmap-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.heatmap-grid {
  display: grid;
  grid-template-columns: 36px repeat(24, minmax(22px, 1fr));
  gap: 2px;
  min-width: 580px;
}

.hm-corner { }
.hm-hour-label {
  font-size: var(--font-size-sm-plus); color: var(--color-text-cool);
  text-align: center; white-space: nowrap;
  padding-bottom: 2px;
}
.hm-hour-label.hm-current { color: var(--color-accent-strong); font-weight: 700; }

.hm-day-label {
  font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright);
  display: flex; align-items: center;
  white-space: nowrap; padding-right: 4px;
}
.hm-today { color: var(--color-accent-strong); font-weight: 700; }

.hm-cell {
  height: 22px; border-radius: 2px;
  background: var(--color-surface);
  transition: transform 0.1s;
  cursor: default;
}
.hm-cell.hm-no-data { background: var(--color-surface); border: 1px solid var(--color-border); }
.hm-cell.hm-current { outline: 2px solid var(--color-accent-strong); outline-offset: 1px; }

.hm-legend {
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
  font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); margin-top: 0.6rem;
}
.hm-leg-swatch {
  width: 14px; height: 14px; border-radius: 2px; display: inline-block; flex-shrink: 0;
}
.hm-leg-nodata { background: var(--color-surface); border: 1px solid var(--color-border); }
.hm-leg-current {
  width: 14px; height: 14px; border-radius: 2px; display: inline-block; flex-shrink: 0;
  outline: 2px solid var(--color-accent-strong); background: transparent;
}
.heatmap-empty { margin-top: 0.5rem; font-size: var(--font-size-sm-plus); }

/* ── Weekday bars ─────────────────────────────────────────────────────────── */
.weekday-bars {
  display: flex; align-items: flex-end;
  gap: 4px; height: 100px; margin-top: 0.25rem;
}
.wd-col { display: flex; flex-direction: column; align-items: center; flex: 1; height: 100%; }
.wd-bar-wrap { flex: 1; width: 100%; display: flex; align-items: flex-end; }
.wd-bar {
  width: 100%; border-radius: 3px 3px 0 0;
  transition: height 0.3s ease; min-height: 4px;
}
.wd-bar.wd-today { outline: 2px solid var(--color-accent-strong); outline-offset: 1px; }
.wd-bar.wd-unreliable { opacity: 0.3; }
.wd-label { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); margin-top: 4px; }
.wd-today-label { color: var(--color-accent-strong); font-weight: 700; }
.wd-val { font-size: var(--font-size-sm-plus); color: var(--color-text-cool); }

/* ── Hourly bars ──────────────────────────────────────────────────────────── */
.hourly-bars {
  display: flex; align-items: flex-end;
  gap: 2px; height: 100px; margin-top: 0.25rem;
}
.hr-col { display: flex; flex-direction: column; align-items: center; flex: 1; height: 100%; }
.hr-bar-wrap { flex: 1; width: 100%; display: flex; align-items: flex-end; }
.hr-bar {
  width: 100%; border-radius: 2px 2px 0 0;
  transition: height 0.3s ease; min-height: 3px;
}
.hr-bar.hr-current { outline: 2px solid var(--color-accent-strong); outline-offset: 1px; }
.hr-bar.hr-unreliable { opacity: 0.3; }
.hr-label { font-size: var(--font-size-sm-plus); color: var(--color-text-cool); margin-top: 3px; white-space: nowrap; }
</style>
