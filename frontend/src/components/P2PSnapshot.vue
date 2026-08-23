<template>
  <div class="p2p-page">

    <!-- ── Live rate bar ───────────────────────────────────────────── -->
    <div class="live-bar">
      <div class="rate-tile sell-tile">
        <div class="rate-eyebrow">{{ t('snapshot.sell_at') }}</div>
        <div class="rate-num sell-num">{{ fmt(snap?.buy_best_rate) }}</div>
        <div class="rate-unit">SDG / USDT</div>
        <div class="rate-hint">{{ t('snapshot.sell_hint') }}</div>
      </div>

      <div class="spread-tile" :class="spreadClass">
        <div class="rate-eyebrow">{{ t('snapshot.gap') }}</div>
        <div class="spread-num" :class="spreadClass + '-num'">
          {{ snap?.spread != null ? (snap.spread >= 0 ? '+' : '') + fmt(snap.spread) : '—' }}
        </div>
        <div class="spread-bar-wrap">
          <div class="spread-bar" :style="spreadBarStyle"></div>
        </div>
        <div class="spread-verdict">{{ gapAdvice }}</div>
      </div>

      <div class="rate-tile buy-tile">
        <div class="rate-eyebrow">{{ t('snapshot.buy_at') }}</div>
        <div class="rate-num buy-num">{{ fmt(snap?.sell_best_rate) }}</div>
        <div class="rate-unit">SDG / USDT</div>
        <div class="rate-hint">{{ t('snapshot.buy_hint') }}</div>
      </div>

      <button class="refresh-btn" @click="refresh" :disabled="loading" :title="t('snapshot.refresh')">
        <span :class="{ spinning: loading }">↻</span>
      </button>
    </div>

    <!-- ── Condition pills ─────────────────────────────────────────── -->
    <div v-if="snap?.conditions?.length" class="pills-row">
      <div
        v-for="c in snap.conditions" :key="c.type"
        class="pill" :class="`pill-${c.level}`"
      >{{ c.icon }} {{ conditionText(c) }}</div>
    </div>

    <!-- ── Avg row ──────────────────────────────────────────────────── -->
    <div class="avg-row">
      <div class="avg-cell">
        <span class="avg-lbl">{{ t('snapshot.avg_1h') }}</span>
        <span class="avg-val">{{ fmt(snap?.avg_spread_1h) }} SDG</span>
      </div>
      <div class="avg-cell">
        <span class="avg-lbl">{{ t('snapshot.avg_24h') }}</span>
        <span class="avg-val">{{ fmt(snap?.avg_spread_24h) }} SDG</span>
      </div>
      <div class="avg-cell">
        <span class="avg-lbl">{{ t('snapshot.last_updated') }}</span>
        <span class="avg-val time-val">{{ lastUpdated }}</span>
      </div>
    </div>

    <!-- ── Recent rate chart ───────────────────────────────────────── -->
    <div class="chart-card">
      <div class="chart-hdr">
        <span class="chart-ttl">{{ t('snapshot.chart_title') }}
          <span class="chart-pts">— {{ historyPoints.length }} {{ t('snapshot.pts') }}</span>
        </span>
        <div class="chart-leg">
          <span class="leg-dot" style="background:#68d391"></span>
          <span class="leg-lbl">{{ t('snapshot.buy_leg_short') }}</span>
          <span class="leg-dot" style="background:#fc8181;margin-inline-start:.75rem"></span>
          <span class="leg-lbl">{{ t('snapshot.sell_leg_short') }}</span>
        </div>
      </div>
      <div class="canvas-wrap" ref="recentWrap">
        <canvas ref="recentCanvas" class="chart-canvas" @mousemove="onRecentMove" @mouseleave="onRecentLeave"></canvas>
        <div class="crosshair-tt" ref="recentTt"></div>
      </div>
      <div class="chart-foot">
        <span>{{ histStart }}</span><span>{{ histEnd }}</span>
      </div>
    </div>

    <!-- ── SDG Market Intelligence (historical) ────────────────────── -->
    <div class="intel-section">
      <div class="intel-eyebrow">
        <span class="intel-badge">{{ t('snapshot.intel_title') }}</span>
        <span class="intel-sub">{{ t('snapshot.intel_sub') }}</span>
      </div>

      <!-- Key stats row -->
      <div class="intel-stats">
        <div class="is-cell">
          <div class="is-lbl">{{ t('snapshot.intel_open') }}</div>
          <div class="is-val buy-c" dir="ltr">{{ dailyOpen }}</div>
          <div class="is-sub">{{ t('snapshot.intel_launch_date') }}</div>
        </div>
        <div class="is-cell">
          <div class="is-lbl">{{ t('snapshot.intel_floor') }}</div>
          <div class="is-val red-c" dir="ltr">3,301</div>
          <div class="is-sub">{{ t('snapshot.intel_frozen_sub') }}</div>
        </div>
        <div class="is-cell">
          <div class="is-lbl">{{ t('snapshot.intel_now') }}</div>
          <div class="is-val buy-c" dir="ltr">{{ dailyCurrent }}</div>
          <div class="is-sub">{{ t('snapshot.intel_today') }}</div>
        </div>
        <div class="is-cell">
          <div class="is-lbl">{{ t('snapshot.intel_change') }}</div>
          <div class="is-val grn-c" dir="ltr">+41.6%</div>
          <div class="is-sub">{{ t('snapshot.intel_since_launch') }}</div>
        </div>
      </div>

      <!-- Historical canvas chart -->
      <div class="canvas-wrap hist-wrap" ref="histWrap">
        <canvas ref="histCanvas" class="chart-canvas hist-canvas" @mousemove="onHistMove" @mouseleave="onHistLeave"></canvas>
        <div class="crosshair-tt" ref="histTt"></div>
      </div>
      <div class="chart-foot hist-foot">
        <span>{{ t('phases.ax_may23') }}</span>
        <span>{{ t('phases.ax_jun1') }}</span>
        <span>{{ t('phases.ax_jun15') }}</span>
        <span>{{ t('phases.ax_jul1') }}</span>
        <span>{{ t('phases.ax_jul15') }}</span>
        <span>{{ t('phases.ax_jul21') }}</span>
      </div>

      <!-- Phase pills -->
      <div class="phase-row">
        <div v-for="ph in PHASES" :key="ph.id" class="phase-pill" :style="`border-inline-start-color:${ph.color}`">
          <div class="pp-name">{{ ph.name }}</div>
          <div class="pp-dates">{{ ph.dates }}</div>
          <div class="pp-val" :style="`color:${ph.color}`">{{ ph.val }}</div>
        </div>
      </div>
    </div>

    <!-- ── Merchant tables ─────────────────────────────────────────── -->
    <div class="market-tables">
      <div v-if="snap?.top_sellers?.length" class="market-side">
        <div class="side-hdr buy-side-hdr">
          <span class="side-dot buy-dot"></span>{{ t('snapshot.buyers_title') }}
        </div>
        <table class="m-table">
          <thead><tr>
            <th>#</th>
            <th>{{ t('snapshot.col_merchant') }}</th>
            <th>{{ t('snapshot.col_pays') }}</th>
          </tr></thead>
          <tbody>
            <tr v-for="(s, i) in snap.top_sellers" :key="'b'+i" :class="i===0?'top-row':''">
              <td class="rank-cell">{{ i + 1 }}</td>
              <td>{{ s.name }}</td>
              <td class="price-cell buy-price">{{ s.price?.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="snap?.active_sellers?.length" class="market-side">
        <div class="side-hdr sell-side-hdr">
          <span class="side-dot sell-dot"></span>{{ t('snapshot.sellers_title') }}
        </div>
        <table class="m-table">
          <thead><tr>
            <th>#</th>
            <th>{{ t('snapshot.col_merchant') }}</th>
            <th>{{ t('snapshot.col_charges') }}</th>
          </tr></thead>
          <tbody>
            <tr v-for="(s, i) in snap.active_sellers" :key="'s'+i" :class="i===0?'top-row':''">
              <td class="rank-cell">{{ i + 1 }}</td>
              <td>{{ s.name }}</td>
              <td class="price-cell sell-price">{{ s.price?.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <p v-if="!snap && !loading" class="empty">{{ t('snapshot.empty') }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../stores/platform'
import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || ''
const { t, locale } = useI18n()
const store   = usePlatformStore()
const loading = ref(false)
const snap    = computed(() => store.snapshot)

// ── Recent history ────────────────────────────────────────────────────────────
const history = ref([])

// ── Daily history (for the 60-day intel chart) ────────────────────────────────
const dailyHistory = ref([])

const PHASES = computed(() => [
  { id:1, name: t('phases.normal'),   dates: t('phases.d_p1'), color:'#2ed47a', val:'+2.7%' },
  { id:2, name: t('phases.stress'),   dates: t('phases.d_p2'), color:'#e8960e', val:'−7.4%' },
  { id:3, name: t('phases.crash'),    dates: t('phases.d_p3'), color:'#e84250', val:'−12.3%' },
  { id:4, name: t('phases.frozen'),   dates: t('phases.d_p4'), color:'#9b82f4', val: t('phases.frozen_days') },
  { id:5, name: t('phases.shock'),    dates: t('phases.d_p5'), color:'#a8d8f0', val:'+47.4%' },
  { id:6, name: t('phases.recovery'), dates: t('phases.d_p6'), color:'#18d0e2', val:'+20%' },
])

// ── Canvas refs ───────────────────────────────────────────────────────────────
const recentCanvas = ref(null)
const recentWrap   = ref(null)
const recentTt     = ref(null)
const histCanvas   = ref(null)
const histWrap     = ref(null)
const histTt       = ref(null)

// ── Computed helpers ──────────────────────────────────────────────────────────
const historyPoints = computed(() => history.value.filter(d => d.buy != null && d.sell != null))

const histStart = computed(() => {
  const ts = historyPoints.value[0]?.t
  return ts ? new Date(ts).toLocaleDateString([], { month: 'short', day: 'numeric' }) : ''
})
const histEnd = computed(() => {
  const ts = historyPoints.value.at(-1)?.t
  return ts ? new Date(ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''
})

const dailyOpen = computed(() => {
  const d = dailyHistory.value[0]
  return d ? Number(d.buy).toFixed(0) : '4,087'
})
const dailyCurrent = computed(() => {
  const d = dailyHistory.value.at(-1)
  return d ? Number(d.buy).toFixed(0) : (snap.value?.buy_best_rate ? Number(snap.value.buy_best_rate).toFixed(0) : '—')
})

const spreadClass = computed(() => {
  const s = snap.value?.spread
  if (s == null) return 'spread-unknown'
  if (s >= 25)  return 'spread-wide'
  if (s < 10)   return 'spread-tight'
  return 'spread-normal'
})

const spreadBarStyle = computed(() => {
  const s = snap.value?.spread
  if (s == null) return { width: '0%' }
  const pct = Math.min(100, Math.max(0, (s / 80) * 100))
  const col = s >= 25 ? '#2ed47a' : s >= 10 ? '#f6ad55' : '#fc8181'
  return { width: pct + '%', background: col }
})

const gapAdvice = computed(() => {
  const s = snap.value?.spread
  if (s == null) return t('snapshot.advice_waiting')
  if (s >= 25)  return t('snapshot.advice_wide')
  if (s < 10)   return t('snapshot.advice_tight')
  return t('snapshot.advice_normal')
})

const lastUpdated = computed(() => {
  if (!snap.value?.timestamp) return '—'
  return new Date(snap.value.timestamp).toLocaleTimeString()
})

function fmt(v) { return v != null ? Number(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '—' }
function conditionText(c) { return t(`conditions.${c.type}`, c.params || {}) }

// ── Data loading ──────────────────────────────────────────────────────────────
async function loadHistory() {
  try {
    const { data } = await axios.get(`${API}/api/p2p/history?limit=500`)
    history.value = data.filter(d => d.buy != null && d.sell != null)
  } catch { /* chart stays hidden */ }
}

async function loadDailyHistory() {
  try {
    const { data } = await axios.get(`${API}/api/p2p/history/daily`)
    dailyHistory.value = data.filter(d => d.buy != null && d.sell != null)
  } catch { /* silently fail */ }
}

async function refresh() {
  loading.value = true
  try {
    await Promise.all([store.fetchSnapshot(), loadHistory(), loadDailyHistory()])
  } finally {
    loading.value = false
  }
}

// ── Generic canvas chart ──────────────────────────────────────────────────────
const DPR = window.devicePixelRatio || 1
const M = { top: 24, right: 16, bottom: 20, left: 58 }

function drawChart(canvas, wrap, pts, opts = {}) {
  if (!canvas || !wrap || pts.length < 2) return
  const W = wrap.clientWidth
  const H = opts.height || 150
  canvas.width  = W * DPR
  canvas.height = H * DPR
  canvas.style.width  = W + 'px'
  canvas.style.height = H + 'px'
  const ctx = canvas.getContext('2d')
  ctx.scale(DPR, DPR)
  ctx.clearRect(0, 0, W, H)

  const pw = W - M.left - M.right
  const ph = H - M.top - M.bottom

  const buys  = pts.map(p => p.buy)
  const sells = pts.map(p => p.sell)
  const allV  = [...buys, ...sells]
  const lo = Math.min(...allV), hi = Math.max(...allV)
  const pad = Math.max((hi - lo) * 0.1, 20)
  const ylo = lo - pad, yhi = hi + pad
  const n = pts.length

  const tx = i => M.left + (i / (n - 1)) * pw
  const ty = v => M.top + (1 - (v - ylo) / (yhi - ylo)) * ph

  // Phase bands (hist chart only)
  if (opts.phaseBands && opts.totalDays) {
    opts.phaseBands.forEach(b => {
      const x0 = M.left + (b.from / opts.totalDays) * pw
      const x1 = M.left + (Math.min(b.to, opts.totalDays) / opts.totalDays) * pw
      ctx.fillStyle = b.fill
      ctx.fillRect(x0, M.top, x1 - x0, ph)
    })
  }

  // Grid lines
  const ySteps = 4
  ctx.font = `${10 * DPR / DPR}px ui-monospace,Menlo,monospace`
  ctx.textAlign = 'right'
  for (let i = 0; i <= ySteps; i++) {
    const v = ylo + (i / ySteps) * (yhi - ylo)
    const y = ty(v)
    ctx.strokeStyle = 'rgba(255,255,255,0.05)'
    ctx.lineWidth = 1
    ctx.beginPath(); ctx.moveTo(M.left, y); ctx.lineTo(M.left + pw, y); ctx.stroke()
    ctx.fillStyle = '#456070'
    ctx.fillText(Math.round(v).toLocaleString(), M.left - 4, y + 3.5)
  }

  // Inter-line fill
  ctx.beginPath()
  pts.forEach((pt, j) => { j === 0 ? ctx.moveTo(tx(j), ty(pt.sell)) : ctx.lineTo(tx(j), ty(pt.sell)) })
  for (let j = pts.length - 1; j >= 0; j--) ctx.lineTo(tx(j), ty(pts[j].buy))
  ctx.closePath()
  ctx.fillStyle = 'rgba(155,130,244,0.07)'
  ctx.fill()

  // Sell line
  ctx.beginPath()
  pts.forEach((pt, j) => { j === 0 ? ctx.moveTo(tx(j), ty(pt.sell)) : ctx.lineTo(tx(j), ty(pt.sell)) })
  ctx.strokeStyle = '#fc8181'
  ctx.lineWidth = 1.5
  ctx.setLineDash([])
  ctx.stroke()

  // Buy line
  ctx.beginPath()
  pts.forEach((pt, j) => { j === 0 ? ctx.moveTo(tx(j), ty(pt.buy)) : ctx.lineTo(tx(j), ty(pt.buy)) })
  ctx.strokeStyle = '#68d391'
  ctx.lineWidth = 2
  ctx.stroke()

  // Last-point dots
  const lx = tx(n - 1)
  ctx.beginPath(); ctx.arc(lx, ty(buys[n-1]),  3.5, 0, Math.PI*2)
  ctx.fillStyle = '#68d391'; ctx.fill()
  ctx.beginPath(); ctx.arc(lx, ty(sells[n-1]), 3.5, 0, Math.PI*2)
  ctx.fillStyle = '#fc8181'; ctx.fill()

  // Phase labels (hist only)
  if (opts.phaseLabels && opts.totalDays) {
    ctx.font = `600 ${9.5}px system-ui,sans-serif`
    ctx.textAlign = 'left'
    opts.phaseLabels.forEach(pl => {
      const x = M.left + (pl.xi / opts.totalDays) * pw + 3
      ctx.fillStyle = pl.color + 'aa'
      ctx.fillText(pl.label, x, M.top + 13)
    })
  }
}

function tooltipAt(canvas, wrap, ttEl, pts, pxX, opts = {}) {
  if (!canvas || !wrap || !ttEl || pts.length < 2) return
  const W = wrap.clientWidth
  const H = canvas.height / DPR
  const pw = W - M.left - M.right
  const n = pts.length
  const frac = (pxX - M.left) / pw
  const idx = Math.round(frac * (n - 1))
  if (idx < 0 || idx >= n) { ttEl.style.display = 'none'; return }
  const pt = pts[idx]
  const sp = pt.buy - pt.sell
  const spStr = `${sp >= 0 ? '+' : ''}${sp.toFixed(1)} SDG`
  const spCol = sp >= 0 ? '#2ed47a' : sp > -100 ? '#f6ad55' : '#e84250'
  const label = pt.date || (pt.t ? new Date(pt.t).toLocaleString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '')
  ttEl.innerHTML = `<div class="tt-d">${label}</div>
    <div class="tt-r"><span class="tt-l" style="color:#68d391">Buy</span><span class="tt-n">${Number(pt.buy).toFixed(1)} SDG</span></div>
    <div class="tt-r"><span class="tt-l" style="color:#fc8181">Sell</span><span class="tt-n">${Number(pt.sell).toFixed(1)} SDG</span></div>
    <div class="tt-sp">Spread: <b style="color:${spCol}">${spStr}</b></div>`
  ttEl.style.display = 'block'
  const ttW = 160, ttH = 88
  let lx = pxX + 12, ly = 20
  if (lx + ttW > W) lx = pxX - ttW - 12
  ttEl.style.left = lx + 'px'
  ttEl.style.top  = ly + 'px'

  // Redraw with crosshair
  drawChart(canvas, wrap, pts, opts)
  const cy = M.top + canvas.height / DPR - M.top - M.bottom
  const ctx = canvas.getContext('2d')
  ctx.scale(1, 1) // already scaled from draw
  const x = M.left + (idx / (n - 1)) * pw
  ctx.strokeStyle = 'rgba(255,255,255,0.15)'
  ctx.lineWidth = 1
  ctx.setLineDash([3,3])
  ctx.beginPath(); ctx.moveTo(x, M.top); ctx.lineTo(x, H - M.bottom); ctx.stroke()
  ctx.setLineDash([])

  const ph = H - M.top - M.bottom
  const buys = pts.map(p => p.buy), sells = pts.map(p => p.sell)
  const allV = [...buys, ...sells]
  const lo = Math.min(...allV), hi = Math.max(...allV)
  const pad = Math.max((hi - lo) * 0.1, 20)
  const ylo = lo - pad, yhi = hi + pad
  const ty = v => M.top + (1 - (v - ylo) / (yhi - ylo)) * ph
  ctx.beginPath(); ctx.arc(x, ty(pt.buy),  4, 0, Math.PI*2); ctx.fillStyle = '#68d391'; ctx.fill()
  ctx.beginPath(); ctx.arc(x, ty(pt.sell), 4, 0, Math.PI*2); ctx.fillStyle = '#fc8181'; ctx.fill()
}

// ── Recent chart handlers ─────────────────────────────────────────────────────
function drawRecent() {
  drawChart(recentCanvas.value, recentWrap.value, historyPoints.value, { height: 150 })
}

function onRecentMove(e) {
  const rect = recentCanvas.value?.getBoundingClientRect()
  if (!rect) return
  tooltipAt(recentCanvas.value, recentWrap.value, recentTt.value, historyPoints.value,
    e.clientX - rect.left, { height: 150 })
}

function onRecentLeave() {
  if (recentTt.value) recentTt.value.style.display = 'none'
  drawRecent()
}

// ── Historical chart handlers ─────────────────────────────────────────────────
const HIST_BANDS = [
  { from: 0,  to: 4,   fill: 'rgba(46,212,122,.06)' },
  { from: 5,  to: 9,   fill: 'rgba(232,150,14,.07)' },
  { from: 10, to: 17,  fill: 'rgba(232,66,80,.07)' },
  { from: 18, to: 47,  fill: 'rgba(155,130,244,.08)' },
  { from: 48, to: 49,  fill: 'rgba(155,130,244,.18)' },
  { from: 50, to: 200, fill: 'rgba(24,208,226,.06)' },
]

const histLabels = computed(() => [
  { xi: 2,    label: `① ${t('phases.normal')}`,       color: '#2ed47a' },
  { xi: 7,    label: `② ${t('phases.stress')}`,       color: '#e8960e' },
  { xi: 13,   label: `③ ${t('phases.crash')}`,        color: '#e84250' },
  { xi: 30,   label: `④ ${t('phases.frozen_label')}`, color: '#9b82f4' },
  { xi: 48.5, label: '⑤',                              color: '#a8d8f0' },
  { xi: 53,   label: `⑥ ${t('phases.recovery')}`,    color: '#18d0e2' },
])

function histOpts(n) {
  return {
    height: 200,
    phaseBands:  HIST_BANDS,
    phaseLabels: histLabels.value,
    totalDays: n - 1,
  }
}

function drawHist() {
  const pts = dailyHistory.value
  if (pts.length < 2) return
  drawChart(histCanvas.value, histWrap.value, pts, histOpts(pts.length))
}

function onHistMove(e) {
  const pts = dailyHistory.value
  if (pts.length < 2) return
  const rect = histCanvas.value?.getBoundingClientRect()
  if (!rect) return
  tooltipAt(histCanvas.value, histWrap.value, histTt.value, pts,
    e.clientX - rect.left, histOpts(pts.length))
}

function onHistLeave() {
  if (histTt.value) histTt.value.style.display = 'none'
  drawHist()
}

// ── ResizeObserver ────────────────────────────────────────────────────────────
let ros = []
function attachRO(wrap, drawFn) {
  const ro = new ResizeObserver(() => drawFn())
  ro.observe(wrap)
  ros.push(ro)
}

onMounted(async () => {
  await refresh()
  await nextTick()
  if (recentWrap.value) attachRO(recentWrap.value, drawRecent)
  if (histWrap.value)   attachRO(histWrap.value,   drawHist)
  drawRecent()
  drawHist()
})
onUnmounted(() => ros.forEach(r => r.disconnect()))

watch(historyPoints, async () => { await nextTick(); drawRecent() })
watch(dailyHistory,  async () => { await nextTick(); drawHist() })
watch(locale,        async () => { await nextTick(); drawHist() })
</script>

<style scoped>
/* ── Page wrapper ─────────────────────────────────────────────── */
.p2p-page { display: flex; flex-direction: column; gap: var(--space-lg); }

/* ── Live rate bar ────────────────────────────────────────────── */
.live-bar {
  display: grid;
  grid-template-columns: 1fr auto 1fr auto;
  gap: 1px;
  background: var(--color-surface-tile);
  border: 1px solid var(--color-surface-tile);
  border-radius: var(--radius-xl);
  overflow: hidden;
  align-items: stretch;
}
.rate-tile {
  background: #0f1822;
  padding: 1.1rem 1.25rem 1rem;
  display: flex; flex-direction: column; gap: 0.15rem;
}
.rate-eyebrow {
  font-size: var(--font-size-2xs); letter-spacing: 0.13em; text-transform: uppercase;
  color: var(--color-text-faint); font-weight: var(--font-weight-semibold);
}
.rate-num {
  font-size: 2rem; font-weight: var(--font-weight-extrabold); line-height: var(--line-height-tight);
  font-family: ui-monospace, Menlo, monospace;
  font-variant-numeric: tabular-nums;
}
.sell-num { color: var(--color-success-strong); }
.buy-num  { color: var(--color-danger); }
.rate-unit { font-size: var(--font-size-2xs-plus); color: var(--color-text-faint); letter-spacing: 0.06em; }
.rate-hint { font-size: var(--font-size-xs); color: var(--color-text-dim); margin-top: 0.15rem; }

.spread-tile {
  background: var(--color-surface-sunken);
  padding: 1.1rem 1.5rem 1rem;
  display: flex; flex-direction: column; gap: var(--space-2xs);
  align-items: center; justify-content: center; text-align: center;
  min-width: 160px;
}
.spread-num {
  font-size: 1.7rem; font-weight: var(--font-weight-extrabold);
  font-family: ui-monospace, Menlo, monospace;
  font-variant-numeric: tabular-nums; line-height: var(--line-height-tight);
}
.spread-wide-num   { color: var(--color-success-vivid); }
.spread-normal-num { color: var(--color-warning); }
.spread-tight-num  { color: var(--color-danger); }
.spread-unknown-num{ color: var(--color-text-muted); }
.spread-bar-wrap {
  width: 100%; height: 4px; background: var(--color-border-subtle); border-radius: var(--radius-xs); margin: 0.3rem 0;
}
.spread-bar { height: 100%; border-radius: var(--radius-xs); transition: width 0.4s; }
.spread-verdict { font-size: var(--font-size-xs); color: var(--color-text-muted); }

.refresh-btn {
  background: var(--color-surface-sunken); border: none; color: var(--color-text-faint); cursor: pointer;
  font-size: 1.2rem; padding: var(--space-sm) var(--space-lg);
  transition: color 0.15s; align-self: stretch; display: flex; align-items: center;
}
.refresh-btn:hover:not(:disabled) { color: var(--color-text-secondary-bright); }
.refresh-btn:disabled { opacity: 0.4; cursor: default; }
.spinning { display: inline-block; animation: spin 1s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Condition pills ──────────────────────────────────────────── */
.pills-row { display: flex; flex-wrap: wrap; gap: var(--space-xs); }
.pill {
  font-size: var(--font-size-xs); padding: var(--space-xs) 0.7rem; border-radius: var(--radius-pill);
  border: 1px solid transparent; line-height: var(--line-height-normal);
}
.pill-wide    { background: var(--color-success-bg); border-color: var(--color-success-border); color: var(--color-success-tint); }
.pill-normal  { background: #132618; border-color: #245c36; color: var(--color-success-tint); }
.pill-tight   { background: #2a1416; border-color: #762020; color: #feb2b2; }
.pill-warning { background: #27210e; border-color: var(--color-warning-border); color: var(--color-warning); }
.pill-info    { background: var(--color-info-bg); border-color: var(--color-info-border); color: var(--color-accent-strong); }

/* ── Avg row ──────────────────────────────────────────────────── */
.avg-row {
  display: flex; gap: var(--space-xl); flex-wrap: wrap;
  padding: 0.6rem 0.25rem; border-bottom: 1px solid var(--color-border-subtle);
}
.avg-cell { display: flex; flex-direction: column; gap: 0.1rem; }
.avg-lbl  { font-size: var(--font-size-2xs-plus); letter-spacing: 0.1em; text-transform: uppercase; color: var(--color-text-faint); }
.avg-val  { font-size: var(--font-size-sm); font-weight: var(--font-weight-semibold); font-variant-numeric: tabular-nums; }
.time-val { font-size: var(--font-size-sm); font-weight: var(--font-weight-regular); color: var(--color-text-muted); }

/* ── Chart card ───────────────────────────────────────────────── */
.chart-card {
  background: var(--color-surface-sunken); border: 1px solid var(--color-border-subtle); border-radius: 0.65rem;
  overflow: hidden;
}
.chart-hdr {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.7rem var(--space-lg) var(--space-sm); border-bottom: 1px solid var(--color-border-subtle);
}
.chart-ttl { font-size: var(--font-size-xs); font-weight: var(--font-weight-semibold); color: var(--color-text-secondary-bright); }
.chart-pts { font-size: var(--font-size-2xs-plus); color: var(--color-text-faint); font-weight: var(--font-weight-regular); }
.chart-leg { display: flex; align-items: center; gap: 0.3rem; font-size: var(--font-size-2xs-plus); color: var(--color-text-dim); }
.leg-dot   { width: 8px; height: 8px; border-radius: var(--radius-circle); flex-shrink: 0; }
.leg-lbl   { white-space: nowrap; }

.canvas-wrap { position: relative; width: 100%; }
.chart-canvas { display: block; width: 100%; }
.hist-canvas  { min-height: 200px; }

.chart-foot {
  display: flex; justify-content: space-between;
  padding: var(--space-2xs) 0.9rem var(--space-sm);
  font-size: var(--font-size-2xs); color: var(--color-text-faint);
}
.hist-foot { padding-inline-start: 3.6rem; justify-content: space-between; }

/* ── Crosshair tooltip ────────────────────────────────────────── */
.crosshair-tt {
  position: absolute; display: none; pointer-events: none;
  background: #0a1220; border: 1px solid #1e3040;
  padding: 0.45rem 0.7rem; font-size: var(--font-size-xs); min-width: 155px;
  box-shadow: 0 4px 20px rgba(0,0,0,.55); z-index: 10;
  border-radius: var(--radius-sm);
}

/* ── SDG Intel section ────────────────────────────────────────── */
.intel-section {
  background: #09111c; border: 1px solid var(--color-border-subtle); border-radius: var(--radius-xl);
  overflow: hidden; padding: 1.1rem;
}
.intel-eyebrow {
  display: flex; align-items: center; gap: var(--space-md); margin-bottom: var(--space-lg);
}
.intel-badge {
  font-size: var(--font-size-2xs-plus); letter-spacing: 0.15em; text-transform: uppercase;
  color: var(--color-info); font-weight: var(--font-weight-bold); white-space: nowrap;
}
.intel-sub { font-size: var(--font-size-xs); color: var(--color-text-faint); }

/* Intel stats */
.intel-stats {
  display: grid; grid-template-columns: repeat(4, 1fr);
  gap: 1px; background: var(--color-border-subtle);
  border: 1px solid var(--color-border-subtle); border-radius: 0.4rem;
  overflow: hidden; margin-bottom: var(--space-lg);
}
.is-cell { background: #0c1826; padding: var(--space-md) 0.8rem; }
.is-lbl  { font-size: var(--font-size-2xs-plus); letter-spacing: 0.1em; text-transform: uppercase; color: var(--color-text-faint); margin-bottom: var(--space-2xs); }
.is-val  { font-size: 1.25rem; font-weight: var(--font-weight-extrabold); font-family: ui-monospace, Menlo, monospace; font-variant-numeric: tabular-nums; line-height: 1; }
.is-sub  { font-size: var(--font-size-2xs); color: var(--color-text-faint); margin-top: 0.2rem; }
.buy-c   { color: var(--color-success-strong); }
.red-c   { color: var(--color-danger-crimson); }
.grn-c   { color: var(--color-success-vivid); }

.hist-wrap { border-top: 1px solid var(--color-border-subtle); border-bottom: 1px solid var(--color-border-subtle); margin: 0 -1.1rem; }

/* Phase pills */
.phase-row {
  display: grid; grid-template-columns: repeat(6, 1fr);
  gap: var(--space-sm); margin-top: var(--space-lg);
}
.phase-pill {
  background: #0d1826; border: 1px solid var(--color-border-subtle); border-inline-start: 3px solid transparent;
  border-radius: 0 0.4rem 0.4rem 0; padding: 0.55rem 0.6rem;
}
.pp-name  { font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); color: var(--color-text-secondary-bright); margin-bottom: 0.1rem; }
.pp-dates { font-size: var(--font-size-2xs-plus); color: var(--color-text-faint); margin-bottom: 0.2rem; font-variant-numeric: tabular-nums; }
.pp-val   { font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); font-family: ui-monospace, Menlo, monospace; }

/* ── Merchant tables ──────────────────────────────────────────── */
.market-tables {
  display: flex; gap: var(--space-lg);
}
.market-side { flex: 1; min-width: 0; }
.side-hdr {
  display: flex; align-items: center; gap: var(--space-sm);
  font-size: var(--font-size-xs); font-weight: var(--font-weight-bold); text-transform: uppercase;
  letter-spacing: 0.08em; padding: var(--space-sm) 0; color: var(--color-text-muted);
}
.side-dot  { width: 8px; height: 8px; border-radius: var(--radius-circle); flex-shrink: 0; }
.buy-dot   { background: var(--color-success-strong); }
.sell-dot  { background: var(--color-danger); }
.buy-side-hdr  { color: var(--color-success-strong); }
.sell-side-hdr { color: var(--color-danger); }

.m-table { width: 100%; border-collapse: collapse; font-size: var(--font-size-sm); }
.m-table th {
  text-align: start; color: var(--color-text-faint); font-weight: var(--font-weight-medium);
  padding: var(--space-xs) var(--space-sm); font-size: var(--font-size-2xs); text-transform: uppercase;
  letter-spacing: 0.08em; border-bottom: 1px solid var(--color-border-subtle);
}
.m-table td { padding: 0.4rem var(--space-sm); border-bottom: 1px solid #0e1a28; }
.m-table tr.top-row td { background: #0e1e30; }
.rank-cell { color: var(--color-text-faint); width: 1.5rem; }
.price-cell { font-weight: var(--font-weight-bold); font-variant-numeric: tabular-nums; text-align: end; }
.buy-price  { color: var(--color-success-strong); }
.sell-price { color: var(--color-danger); }

/* ── Tooltip internals (non-scoped via :deep or global via child class) ── */
:deep(.tt-d)  { font-size: var(--font-size-2xs); letter-spacing: 0.08em; text-transform: uppercase; color: var(--color-text-faint); margin-bottom: 0.3rem; }
:deep(.tt-r)  { display: flex; justify-content: space-between; gap: var(--space-lg); margin-top: 0.15rem; }
:deep(.tt-l)  { color: var(--color-text-dim); }
:deep(.tt-n)  { font-family: ui-monospace, Menlo, monospace; font-variant-numeric: tabular-nums; }
:deep(.tt-sp) { font-size: var(--font-size-2xs-plus); margin-top: 0.3rem; padding-top: 0.3rem; border-top: 1px solid var(--color-border-subtle); color: var(--color-text-dim); }

/* ── Responsive ───────────────────────────────────────────────── */
@media (max-width: 680px) {
  .live-bar { grid-template-columns: 1fr 1fr; grid-template-rows: auto auto; }
  .spread-tile { min-width: unset; grid-column: 1 / -1; flex-direction: row; justify-content: flex-start; gap: var(--space-lg); }
  .refresh-btn { grid-column: 1 / -1; border-top: 1px solid var(--color-border-subtle); justify-content: center; }
  .intel-stats { grid-template-columns: 1fr 1fr; }
  .phase-row   { grid-template-columns: repeat(3, 1fr); }
  .market-tables { flex-direction: column; }
}
@media (max-width: 400px) {
  .phase-row { grid-template-columns: repeat(2, 1fr); }
  .rate-num  { font-size: 1.5rem; }
}

.empty { color: var(--color-text-faint); font-size: var(--font-size-sm); padding: var(--space-lg) 0; }
</style>
