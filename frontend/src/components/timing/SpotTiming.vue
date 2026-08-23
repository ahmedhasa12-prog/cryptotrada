<template>
  <div class="card spot-timing-card">

    <!-- ── Active market sessions ─────────────────────────────────────── -->
    <SessionsStrip />

    <!-- ══ COIN CARDS (accordion) ══════════════════════════════════════════ -->
    <div class="coin-cards">
      <div v-for="coin in sortedCoins" :key="coin.symbol" class="coin-group">

        <!-- Summary card row -->
        <div class="coin-card"
             :class="[cardBorderClass(coin.symbol), { 'cc-active': selectedCoin === coin.symbol }]"
             @click="selectCoin(coin.symbol)">

          <div class="cc-left">
            <span class="cc-sym">{{ coin.symbol }}</span>
            <span v-if="coin.held"        class="cc-badge badge-held">HELD</span>
            <span v-else-if="coin.pinned" class="cc-badge badge-pin">★</span>
          </div>

          <div class="cc-mid">
            <template v-if="allTimings[coin.symbol]">
              <span class="cc-dot" :class="dotClass(coin.symbol)"></span>
              <div class="cc-texts">
                <span class="cc-verdict" :class="verdictClass(coin.symbol)">{{ verdictLabel(coin.symbol) }}</span>
                <span class="cc-meta">{{ cardMeta(coin.symbol) }}</span>
              </div>
            </template>
            <template v-else-if="allStatuses[coin.symbol]?.backfilling">
              <span class="cc-dot dot-loading"></span>
              <div class="cc-texts">
                <span class="cc-verdict">{{ t('spot_timing.loading_coin') }}</span>
                <span class="cc-meta">{{ allStatuses[coin.symbol].pct_complete }}% · {{ allStatuses[coin.symbol].days_covered }}d</span>
              </div>
            </template>
            <template v-else>
              <span class="cc-dot dot-unknown"></span>
              <div class="cc-texts">
                <span class="cc-verdict col-dim">{{ allStatuses[coin.symbol] ? t('spot_timing.tap_to_load') : '…' }}</span>
                <span class="cc-meta">{{ allStatuses[coin.symbol]?.days_covered ? allStatuses[coin.symbol].days_covered + 'd stored' : '' }}</span>
              </div>
            </template>
          </div>

          <div class="cc-right" v-if="allTimings[coin.symbol]">
            <div class="cc-hr"><span class="hr-arrow pos">↑</span><span class="hr-val">{{ bestEnterHour(coin.symbol) }}</span></div>
            <div class="cc-hr"><span class="hr-arrow neg">↓</span><span class="hr-val">{{ bestExitHour(coin.symbol) }}</span></div>
          </div>

          <span class="cc-chev">›</span>
        </div><!-- /coin-card -->

        <!-- ── Inline detail panel ──────────────────────────────────────── -->
        <div v-if="selectedCoin === coin.symbol" class="detail-panel"
             :ref="el => { if (el) detailRefs[coin.symbol] = el }">

          <!-- Loading state -->
          <div v-if="allStatuses[coin.symbol]?.backfilling || (!allTimings[coin.symbol] && allStatuses[coin.symbol]?.ready)" class="status-bar">
            <div class="status-fill fill-loading" :style="{ width: (allStatuses[coin.symbol]?.pct_complete || 0) + '%' }"></div>
            <span class="status-text">⏳ {{ t('spot_timing.backfilling', { pct: allStatuses[coin.symbol]?.pct_complete, days: allStatuses[coin.symbol]?.days_covered }) }}</span>
          </div>

          <template v-if="timing?.hourly">

            <!-- ── NOW panel — at-a-glance current position ────────────── -->
            <div class="now-panel">
              <div class="now-title">{{ t('spot_timing.right_now') }}</div>
              <div class="now-grid">
                <div class="now-cell" :class="nowCellClass(nowHourSlot)">
                  <span class="now-lbl">{{ t('spot_timing.this_hour') }}</span>
                  <span class="now-val">{{ nowHourSlot?.reliable ? fmtRet(nowHourSlot.avg_return_pct) : '—' }}</span>
                  <span class="now-sub">{{ pad(localHr(utcHour)) }}:00 local</span>
                </div>
                <div class="now-cell" :class="nowCellClass(nowDaySlot)">
                  <span class="now-lbl">{{ t('spot_timing.today') }}</span>
                  <span class="now-val">{{ nowDaySlot?.reliable ? fmtRet(nowDaySlot.avg_return_pct) : '—' }}</span>
                  <span class="now-sub">{{ t('timing.days.' + localWeekday) }}</span>
                </div>
                <div class="now-cell" :class="nowCellClass(nowWeekSlot)">
                  <span class="now-lbl">{{ t('spot_timing.this_week') }}</span>
                  <span class="now-val">{{ nowWeekSlot?.reliable ? fmtRet(nowWeekSlot.avg_return_pct) : '—' }}</span>
                  <span class="now-sub">{{ t('spot_timing.week_of_month', { n: currentWeek }) }}</span>
                </div>
                <div class="now-cell" :class="nowCellClass(nowMonthSlot)">
                  <span class="now-lbl">{{ t('spot_timing.this_month') }}</span>
                  <span class="now-val">{{ nowMonthSlot?.reliable ? fmtRet(nowMonthSlot.avg_return_pct) : '—' }}</span>
                  <span class="now-sub">{{ t('spot_timing.months_short.' + currentMonth) }}</span>
                </div>
              </div>
              <div class="now-data-note" v-if="allStatuses[coin.symbol]">
                {{ t('spot_timing.days_of_data', { n: allStatuses[coin.symbol].days_covered }) }}
                <span v-if="allStatuses[coin.symbol].days_covered < 30" class="low-conf-note"> · {{ t('spot_timing.more_data_conf') }}</span>
              </div>
            </div>

            <!-- ── Master summary card ────────────────────────────────── -->
            <div class="master-card">
              <div class="eg-grid">
                <div class="eg-col eg-enter">
                  <div class="eg-head">{{ t('spot_timing.enter_col') }}</div>
                  <div class="eg-sub">{{ t('spot_timing.enter_hint') }}</div>
                  <template v-if="topHours.length">
                    <div v-for="h in topHours" :key="h.hour" class="eg-row">
                      <span class="eg-time">{{ pad(h.localHr) }}:00</span>
                      <span class="eg-arrow" :class="h.avg_return_pct >= 0 ? 'eg-pos' : 'eg-neg'">{{ h.avg_return_pct >= 0 ? '▲' : '▼' }}</span>
                      <span class="eg-ret"   :class="h.avg_return_pct >= 0 ? 'eg-pos' : 'eg-neg'">{{ fmtRet(h.avg_return_pct) }}</span>
                      <span v-if="!h.reliable" class="eg-low-conf" :title="t('spot_timing.low_conf_tip')">~</span>
                    </div>
                  </template>
                  <span v-else class="eg-empty">—</span>
                </div>
                <div class="eg-divider"></div>
                <div class="eg-col eg-exit">
                  <div class="eg-head">{{ t('spot_timing.exit_col') }}</div>
                  <div class="eg-sub">{{ t('spot_timing.exit_hint') }}</div>
                  <template v-if="bottomHours.length">
                    <div v-for="h in bottomHours" :key="h.hour" class="eg-row">
                      <span class="eg-time">{{ pad(h.localHr) }}:00</span>
                      <span class="eg-arrow" :class="h.avg_return_pct <= 0 ? 'eg-neg' : 'eg-pos'">{{ h.avg_return_pct <= 0 ? '▼' : '▲' }}</span>
                      <span class="eg-ret"   :class="h.avg_return_pct <= 0 ? 'eg-neg' : 'eg-pos'">{{ fmtRet(h.avg_return_pct) }}</span>
                      <span v-if="!h.reliable" class="eg-low-conf" :title="t('spot_timing.low_conf_tip')">~</span>
                    </div>
                  </template>
                  <span v-else class="eg-empty">—</span>
                </div>
              </div>

              <div class="summary-row" v-if="topDays.length || bottomDays.length">
                <template v-if="topDays.length">
                  <span class="sr-lbl">{{ t('spot_timing.best_days_lbl') }}</span>
                  <span v-for="d in topDays" :key="d.day" class="day-chip" :class="d.reliable ? 'chip-good' : 'chip-good-dim'">{{ t('timing.days_short.' + d.day) }}</span>
                </template>
                <span class="sr-sep" v-if="topDays.length && bottomDays.length">·</span>
                <template v-if="bottomDays.length">
                  <span class="sr-lbl">{{ t('spot_timing.weak_days_lbl') }}</span>
                  <span v-for="d in bottomDays" :key="d.day" class="day-chip" :class="d.reliable ? 'chip-bad' : 'chip-bad-dim'">{{ t('timing.days_short.' + d.day) }}</span>
                </template>
              </div>

              <div class="summary-row" v-if="timing.week_of_month?.some(w => w.avg_return_pct != null)">
                <span class="sr-lbl">{{ t('spot_timing.week_this', { n: currentWeek }) }}</span>
                <span v-for="w in timing.week_of_month" :key="w.week" class="wom-chip"
                      :class="{ 'wom-cur': w.week === currentWeek, 'wom-pos': w.avg_return_pct > 0, 'wom-neg': w.avg_return_pct <= 0, 'wom-dim': !w.reliable }">
                  {{ t('spot_timing.wk_abbr') }}{{ w.week }}<span v-if="w.avg_return_pct != null" class="wom-ret"> {{ fmtRet(w.avg_return_pct) }}</span>
                </span>
                <span class="week-rank" v-if="weekRank">· {{ weekRank }}</span>
              </div>

              <div class="summary-row" v-if="timing.month_of_year?.some(m => m.avg_return_pct != null)">
                <span class="sr-lbl">{{ t('spot_timing.month_this', { name: t('spot_timing.months_short.' + currentMonth) }) }}</span>
                <span v-for="m in timing.month_of_year.filter(m => m.sample_count > 0)" :key="m.month" class="wom-chip"
                      :class="{ 'wom-cur': m.month === currentMonth, 'wom-pos': m.avg_return_pct > 0, 'wom-neg': m.avg_return_pct <= 0, 'wom-dim': !m.reliable }">
                  {{ t('spot_timing.months_short.' + m.month) }}<span v-if="m.avg_return_pct != null" class="wom-ret"> {{ fmtRet(m.avg_return_pct) }}</span>
                </span>
                <span class="week-rank" v-if="monthRank">· {{ monthRank }}</span>
              </div>
            </div>

            <!-- ── Hourly chart ────────────────────────────────────────── -->
            <div class="chart-section">
              <div class="cs-header">
                <span class="cs-title">{{ t('spot_timing.hourly_ret_title') }}</span>
                <span class="cs-hint">{{ t('spot_timing.hourly_ret_hint') }}</span>
              </div>
              <div class="dv-wrap">
                <div class="dv-zero"></div>
                <div v-for="slot in timing.hourly" :key="slot.hour"
                     class="dv-col" :class="{ 'dv-now': slot.hour === utcHour, 'dv-dim': !slot.reliable }"
                     :title="hrTooltip(slot)">
                  <div class="dv-upper">
                    <div v-if="slot.avg_return_pct > 0" class="dv-bar"
                         :class="slot.reliable ? 'dv-pos' : 'dv-pos-dim'"
                         :style="{ height: dvHeight(slot.avg_return_pct, maxAbsHr) }"></div>
                  </div>
                  <div class="dv-lower">
                    <div v-if="slot.avg_return_pct < 0" class="dv-bar"
                         :class="slot.reliable ? 'dv-neg' : 'dv-neg-dim'"
                         :style="{ height: dvHeight(slot.avg_return_pct, maxAbsHr) }"></div>
                  </div>
                  <span class="dv-lbl">{{ pad(localHr(slot.hour)) }}</span>
                </div>
              </div>
            </div>

            <!-- ── Month of year chart ─────────────────────────────────── -->
            <div class="chart-section" v-if="timing.month_of_year?.some(m => m.sample_count > 0)">
              <div class="cs-header">
                <span class="cs-title">{{ t('spot_timing.month_of_year_title') }}</span>
                <span class="cs-hint">{{ t('spot_timing.month_of_year_hint') }}</span>
              </div>
              <div class="mo-wrap">
                <div class="mo-zero"></div>
                <div v-for="m in timing.month_of_year" :key="m.month"
                     class="mo-col" :class="{ 'mo-cur-col': m.month === currentMonth }"
                     :title="moTooltip(m)">
                  <div class="mo-upper">
                    <div v-if="m.sample_count > 0 && m.avg_return_pct > 0" class="mo-bar"
                         :class="m.reliable ? 'mo-pos' : 'mo-pos-dim'"
                         :style="{ height: dvHeight(m.avg_return_pct, maxAbsMo) }"></div>
                  </div>
                  <div class="mo-lower">
                    <div v-if="m.sample_count > 0 && m.avg_return_pct < 0" class="mo-bar"
                         :class="m.reliable ? 'mo-neg' : 'mo-neg-dim'"
                         :style="{ height: dvHeight(m.avg_return_pct, maxAbsMo) }"></div>
                  </div>
                  <div class="mo-lbl" :class="{ 'mo-lbl-cur': m.month === currentMonth }">
                    {{ t('spot_timing.months_short.' + m.month) }}
                  </div>
                  <div v-if="m.sample_count > 0" class="mo-ret-lbl" :class="m.avg_return_pct > 0 ? 'pos' : 'neg'">
                    {{ fmtRet(m.avg_return_pct) }}
                  </div>
                </div>
              </div>
            </div>

            <!-- ── Week of month chart ────────────────────────────────── -->
            <div class="chart-section" v-if="timing.week_of_month?.some(w => w.sample_count > 0)">
              <div class="cs-header">
                <span class="cs-title">{{ t('spot_timing.week_of_month_title') }}</span>
                <span class="cs-hint">{{ t('spot_timing.week_of_month_hint') }}</span>
              </div>
              <div class="wom-wrap">
                <div class="wom-zero"></div>
                <div v-for="w in timing.week_of_month" :key="w.week"
                     class="wom-col" :class="{ 'wom-cur-col': w.week === currentWeek }"
                     :title="womTooltip(w)">
                  <div class="wom-upper">
                    <div v-if="w.sample_count > 0 && w.avg_return_pct > 0" class="wom-bar"
                         :class="w.reliable ? 'wom-pos' : 'wom-pos-dim'"
                         :style="{ height: dvHeight(w.avg_return_pct, maxAbsWom) }"></div>
                  </div>
                  <div class="wom-lower">
                    <div v-if="w.sample_count > 0 && w.avg_return_pct < 0" class="wom-bar"
                         :class="w.reliable ? 'wom-neg' : 'wom-neg-dim'"
                         :style="{ height: dvHeight(w.avg_return_pct, maxAbsWom) }"></div>
                  </div>
                  <div class="wom-lbl" :class="{ 'wom-lbl-cur': w.week === currentWeek }">Wk {{ w.week }}</div>
                  <div v-if="w.sample_count > 0" class="wom-ret-lbl" :class="w.avg_return_pct > 0 ? 'pos' : 'neg'">{{ fmtRet(w.avg_return_pct) }}</div>
                </div>
              </div>
            </div>

            <!-- ── Day of week chart ──────────────────────────────────── -->
            <div class="chart-section">
              <div class="cs-header">
                <span class="cs-title">{{ t('spot_timing.weekday_ret_title') }}</span>
                <span class="cs-hint">{{ t('spot_timing.weekday_ret_hint') }}</span>
              </div>
              <div class="wd-wrap">
                <div class="wd-zero"></div>
                <div v-for="(slot, i) in timing.weekday" :key="i"
                     class="wd-col" :class="{ 'wd-today': i === localWeekday }"
                     :title="wdTooltip(slot)">
                  <div class="wd-upper">
                    <div v-if="slot.sample_count > 0 && slot.avg_return_pct > 0" class="wd-bar"
                         :class="slot.reliable ? 'wd-pos' : 'wd-pos-dim'"
                         :style="{ height: dvHeight(slot.avg_return_pct, maxAbsWd) }"></div>
                  </div>
                  <div class="wd-lower">
                    <div v-if="slot.sample_count > 0 && slot.avg_return_pct <= 0" class="wd-bar"
                         :class="slot.reliable ? 'wd-neg' : 'wd-neg-dim'"
                         :style="{ height: dvHeight(slot.avg_return_pct, maxAbsWd) }"></div>
                  </div>
                  <div class="wd-lbl" :class="{ 'wd-lbl-today': i === localWeekday }">{{ t('timing.days_short.' + i) }}</div>
                  <div v-if="slot.sample_count > 0" class="wd-ret" :class="slot.avg_return_pct > 0 ? 'pos' : 'neg'">{{ fmtRet(slot.avg_return_pct) }}</div>
                </div>
              </div>
            </div>

          </template><!-- /timing.hourly -->
        </div><!-- /detail-panel -->

      </div><!-- /coin-group -->
    </div><!-- /coin-cards -->

  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../../stores/platform'
import SessionsStrip from '../SessionsStrip.vue'

const { t } = useI18n()
const store  = usePlatformStore()

// ── Clock ──────────────────────────────────────────────────────────────────────
const now = ref(new Date())
let clockTimer
onMounted(() => { clockTimer = setInterval(() => { now.value = new Date() }, 60_000) })
onUnmounted(() => { clearInterval(clockTimer); stopAllPolls() })

const utcHour      = computed(() => now.value.getUTCHours())
const localWeekday = computed(() => (now.value.getDay() + 6) % 7)
const tzOffset     = computed(() => -now.value.getTimezoneOffset() / 60)
const currentWeek  = computed(() => Math.min(4, Math.floor((now.value.getDate() - 1) / 7) + 1))
const currentMonth = computed(() => now.value.getMonth() + 1)
function localHr(utcH) { return ((utcH + tzOffset.value) % 24 + 24) % 24 }
function pad(n) { return String(Math.round(n)).padStart(2, '0') }

// ── Per-coin data ──────────────────────────────────────────────────────────────
const allTimings  = reactive({})
const allStatuses = reactive({})
const pollTimers  = {}
const detailRefs  = reactive({})

function stopAllPolls() { Object.values(pollTimers).forEach(id => clearInterval(id)) }

const selectedCoin = ref(null)
const timing = computed(() => selectedCoin.value ? (allTimings[selectedCoin.value] ?? null) : null)

// ── Load on mount ──────────────────────────────────────────────────────────────
onMounted(async () => {
  if (!store.watchlist.length) await store.fetchWatchlist()
  const coins = store.watchlist.filter(w => w.active).map(w => w.symbol)
  await Promise.all(coins.map(sym => loadCoinStatus(sym)))
  await Promise.all(coins.filter(sym => allStatuses[sym]?.ready).map(sym => loadCoinPatterns(sym)))
  // Auto-start 730-day backfill for any coin that hasn't reached the target yet
  await Promise.all(coins.map(async (sym) => {
    const s = allStatuses[sym]
    if (s?.ready && (s.pct_complete ?? 0) < 95 && !s.backfilling) {
      try { allStatuses[sym] = await store.startSpotBackfill(sym); pollCoin(sym) } catch { /* ignore */ }
    }
  }))
})

async function loadCoinStatus(sym) {
  try { allStatuses[sym] = await store.fetchSpotTimingStatus(sym) } catch { /* ignore */ }
}
async function loadCoinPatterns(sym) {
  try {
    const data = await store.fetchSpotTimingPatterns(sym)
    if (data?.hourly) allTimings[sym] = data
  } catch { /* ignore */ }
}
function pollCoin(sym) {
  if (pollTimers[sym]) return
  pollTimers[sym] = setInterval(async () => {
    await loadCoinStatus(sym)
    if (!allStatuses[sym]?.backfilling) {
      clearInterval(pollTimers[sym]); delete pollTimers[sym]
      if (allStatuses[sym]?.ready) await loadCoinPatterns(sym)
    }
  }, 4000)
}

async function selectCoin(sym) {
  if (selectedCoin.value === sym) { selectedCoin.value = null; return }
  selectedCoin.value = sym
  if (!allStatuses[sym]) await loadCoinStatus(sym)
  const s = allStatuses[sym]
  if (!s) return
  if (!s.backfilling && (s.pct_complete ?? 0) < 95) {
    try { allStatuses[sym] = await store.startSpotBackfill(sym) } catch { /* ignore */ }
    pollCoin(sym)
  }
  if (s.ready && !allTimings[sym]) await loadCoinPatterns(sym)
  await nextTick()
  detailRefs[sym]?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
}

// ── Sorted coins ───────────────────────────────────────────────────────────────
const sortedCoins = computed(() =>
  [...store.watchlist.filter(w => w.active)].sort((a, b) => {
    const pri = c => c.held ? 0 : c.pinned ? 1 : 2
    if (pri(a) !== pri(b)) return pri(a) - pri(b)
    return currentHourReturn(b.symbol) - currentHourReturn(a.symbol)
  })
)

// ── Card signal helpers ────────────────────────────────────────────────────────
function currentHourSlot(sym) {
  return allTimings[sym]?.hourly?.[utcHour.value] ?? null
}
function currentHourReturn(sym) {
  const s = currentHourSlot(sym)
  return s?.avg_return_pct ?? -999
}
function dotClass(sym) {
  const s = currentHourSlot(sym)
  if (!s || s.sample_count === 0) return 'dot-unknown'
  const r = s.avg_return_pct
  if (!s.reliable) return r > 0 ? 'dot-green-dim' : 'dot-red-dim'
  if (r >  0.02) return 'dot-strong-green'
  if (r >  0)    return 'dot-green'
  if (r < -0.02) return 'dot-strong-red'
  return 'dot-red'
}
function verdictClass(sym) {
  const s = currentHourSlot(sym)
  if (!s || s.sample_count === 0) return 'col-dim'
  const r = s.avg_return_pct
  if (!s.reliable) return r >= 0 ? 'col-green-dim' : 'col-red-dim'
  return r >= 0 ? 'col-green' : 'col-red'
}
function verdictLabel(sym) {
  const s = currentHourSlot(sym)
  if (!s || s.sample_count === 0) return t('spot_timing.no_data_hour')
  const r = s.avg_return_pct
  const conf = s.reliable ? '' : '~'
  if (r >  0.02) return conf + t('spot_timing.verdict_strong_up')
  if (r >  0)    return conf + t('spot_timing.verdict_good_up')
  if (r < -0.02) return conf + t('spot_timing.verdict_avoid')
  if (r <  0)    return conf + t('spot_timing.verdict_weak')
  return conf + t('spot_timing.verdict_neutral')
}
function cardMeta(sym) {
  const s = currentHourSlot(sym)
  const t = allTimings[sym]
  if (!s || s.sample_count === 0 || !t) return ''
  const ret = (s.avg_return_pct >= 0 ? '+' : '') + s.avg_return_pct.toFixed(3) + '%'
  const moy = t.month_of_year?.find(m => m.month === currentMonth.value)
  const moArrow = moy?.sample_count > 0 ? (moy.avg_return_pct > 0 ? '▲' : '▼') : ''
  const moName  = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][currentMonth.value]
  const conf = s.reliable ? '' : '~ '
  const days = allStatuses[sym]?.days_covered ?? 0
  const daysStr = days >= 365 ? `${Math.round(days / 365)}yr` : days >= 30 ? `${Math.round(days / 30)}mo` : `${Math.round(days)}d`
  return `${conf}${ret} · ${daysStr} · ${moName} ${moArrow}`
}
function cardBorderClass(sym) {
  const s = currentHourSlot(sym)
  if (!s || s.sample_count === 0) return ''
  const r = s.avg_return_pct
  if (r >  0.01) return 'cc-border-green'
  if (r < -0.01) return 'cc-border-red'
  return ''
}
function bestEnterHour(sym) {
  const h = allTimings[sym]?.hourly
  if (!h) return '—'
  const top = [...h].filter(s => s.sample_count > 0 && s.avg_return_pct != null)
    .sort((a, b) => b.avg_return_pct - a.avg_return_pct)[0]
  return top ? pad(localHr(top.hour)) + ':00' : '—'
}
function bestExitHour(sym) {
  const h = allTimings[sym]?.hourly
  if (!h) return '—'
  const w = [...h].filter(s => s.sample_count > 0 && s.avg_return_pct != null)
    .sort((a, b) => a.avg_return_pct - b.avg_return_pct)[0]
  return w ? pad(localHr(w.hour)) + ':00' : '—'
}

// ── NOW panel helpers ──────────────────────────────────────────────────────────
const nowHourSlot  = computed(() => timing.value?.hourly?.[utcHour.value] ?? null)
const nowDaySlot   = computed(() => timing.value?.weekday?.[localWeekday.value] ?? null)
const nowWeekSlot  = computed(() => timing.value?.week_of_month?.find(w => w.week === currentWeek.value) ?? null)
const nowMonthSlot = computed(() => timing.value?.month_of_year?.find(m => m.month === currentMonth.value) ?? null)

function nowCellClass(slot) {
  if (!slot || slot.sample_count === 0) return 'now-cell-neutral'
  const r = slot.avg_return_pct
  if (!slot.reliable) return r > 0 ? 'now-cell-green-dim' : r < 0 ? 'now-cell-red-dim' : 'now-cell-neutral'
  if (r > 0.005)  return 'now-cell-green'
  if (r < -0.005) return 'now-cell-red'
  return 'now-cell-neutral'
}

// ── Detail panel computeds ─────────────────────────────────────────────────────
const topHours = computed(() => {
  if (!timing.value?.hourly) return []
  return [...timing.value.hourly]
    .filter(s => s.sample_count > 0 && s.avg_return_pct != null)
    .sort((a, b) => b.avg_return_pct - a.avg_return_pct).slice(0, 3)
    .map(s => ({ ...s, localHr: localHr(s.hour) }))
})
const bottomHours = computed(() => {
  if (!timing.value?.hourly) return []
  return [...timing.value.hourly]
    .filter(s => s.sample_count > 0 && s.avg_return_pct != null)
    .sort((a, b) => a.avg_return_pct - b.avg_return_pct).slice(0, 3)
    .map(s => ({ ...s, localHr: localHr(s.hour) }))
})
const topDays = computed(() => {
  if (!timing.value?.weekday) return []
  return [...timing.value.weekday]
    .filter(s => s.sample_count > 0 && s.avg_return_pct != null)
    .sort((a, b) => b.avg_return_pct - a.avg_return_pct).slice(0, 3)
})
const bottomDays = computed(() => {
  if (!timing.value?.weekday) return []
  return [...timing.value.weekday]
    .filter(s => s.sample_count > 0 && s.avg_return_pct != null)
    .sort((a, b) => a.avg_return_pct - b.avg_return_pct).slice(0, 2)
})

const weekRank = computed(() => {
  const wom = timing.value?.week_of_month?.filter(w => w.reliable && w.avg_return_pct != null)
    .sort((a, b) => b.avg_return_pct - a.avg_return_pct)
  if (!wom?.length) return ''
  const rank = wom.findIndex(w => w.week === currentWeek.value)
  if (rank === -1) return ''
  if (rank === 0) return t('spot_timing.week_rank_strong')
  if (rank === wom.length - 1) return t('spot_timing.week_rank_weak')
  return t('spot_timing.week_rank_avg')
})
const monthRank = computed(() => {
  const moy = timing.value?.month_of_year?.filter(m => m.reliable && m.avg_return_pct != null)
    .sort((a, b) => b.avg_return_pct - a.avg_return_pct)
  if (!moy?.length) return ''
  const rank = moy.findIndex(m => m.month === currentMonth.value)
  if (rank === -1) return ''
  if (rank === 0) return t('spot_timing.month_rank_strong')
  if (rank === moy.length - 1) return t('spot_timing.month_rank_weak')
  return t('spot_timing.month_rank_avg')
})

const maxAbsHr = computed(() => {
  const v = timing.value?.hourly?.filter(s => s.sample_count > 0 && s.avg_return_pct != null).map(s => Math.abs(s.avg_return_pct))
  return v?.length ? Math.max(...v, 0.001) : 0.05
})
const maxAbsWd = computed(() => {
  const v = timing.value?.weekday?.filter(s => s.sample_count > 0 && s.avg_return_pct != null).map(s => Math.abs(s.avg_return_pct))
  return v?.length ? Math.max(...v, 0.001) : 0.05
})
const maxAbsWom = computed(() => {
  const v = timing.value?.week_of_month?.filter(s => s.sample_count > 0 && s.avg_return_pct != null).map(s => Math.abs(s.avg_return_pct))
  return v?.length ? Math.max(...v, 0.001) : 0.05
})
const maxAbsMo = computed(() => {
  const v = timing.value?.month_of_year?.filter(m => m.sample_count > 0 && m.avg_return_pct != null).map(m => Math.abs(m.avg_return_pct))
  return v?.length ? Math.max(...v, 0.001) : 0.05
})

function dvHeight(val, maxAbs) {
  if (val == null || maxAbs === 0) return '0%'
  return Math.min(100, Math.max(6, (Math.abs(val) / maxAbs) * 100)) + '%'
}
function fmtRet(v) {
  if (v == null) return '—'
  return (v >= 0 ? '+' : '') + v.toFixed(3) + '%'
}
function hrTooltip(slot) {
  const lh = pad(localHr(slot.hour))
  if (!slot.sample_count) return `${lh}:00 — no data`
  const conf = slot.reliable ? '' : ' (low confidence)'
  return `${lh}:00 local | avg ${fmtRet(slot.avg_return_pct)} | ${slot.bull_pct?.toFixed(0)}% bullish | ${slot.sample_count} candles${conf}`
}
function wdTooltip(slot) {
  if (!slot.sample_count) return 'no data'
  return `${slot.day_key} | avg ${fmtRet(slot.avg_return_pct)} | ${slot.bull_pct?.toFixed(0)}% bullish | ${slot.sample_count} candles`
}
function womTooltip(w) {
  if (!w.sample_count) return `Week ${w.week} — no data`
  return `Week ${w.week} | avg ${fmtRet(w.avg_return_pct)} | ${w.bull_pct?.toFixed(0)}% bullish | ${w.sample_count} candles`
}
function moTooltip(m) {
  const name = ['','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][m.month]
  if (!m.sample_count) return `${name} — no data`
  return `${name} | avg ${fmtRet(m.avg_return_pct)} | ${m.bull_pct?.toFixed(0)}% bullish | ${m.sample_count} candles`
}
</script>

<style scoped>
.spot-timing-card {
  display: flex; flex-direction: column; gap: 0.5rem;
  padding: 0.5rem 0.6rem 0.6rem;
}

/* ── COIN CARDS ─────────────────────────────────────────────────────────────── */
.coin-cards { display: flex; flex-direction: column; gap: 0.4rem; }
.coin-group { display: flex; flex-direction: column; }

.coin-card {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.7rem 0.9rem;
  background: #1e2130; border: 1px solid var(--color-border); border-radius: 0.6rem;
  cursor: pointer; transition: border-color 0.15s, background 0.15s;
  -webkit-tap-highlight-color: transparent;
}
.coin-card:active { background: #252a3a; }
.cc-active        { background: #1a2035; border-color: var(--color-accent) !important; border-bottom-left-radius: 0; border-bottom-right-radius: 0; }
.cc-border-green  { border-color: rgba(34,197,94,0.45); }
.cc-border-red    { border-color: rgba(239,68,68,0.35); }

.cc-left  { display: flex; flex-direction: column; align-items: center; gap: 0.2rem; min-width: 44px; }
.cc-sym   { font-size: var(--font-size-base); font-weight: 800; color: var(--color-text); }
.cc-badge { font-size: var(--font-size-sm-plus); font-weight: 700; padding: 0.1rem 0.35rem; border-radius: 3px; white-space: nowrap; }
.badge-held { background: rgba(144,205,244,0.15); color: var(--color-accent-strong); border: 1px solid rgba(144,205,244,0.3); }
.badge-pin  { background: rgba(246,173,85,0.15);  color: var(--color-warning); border: 1px solid rgba(246,173,85,0.3); }

.cc-mid { flex: 1; display: flex; align-items: center; gap: 0.55rem; min-width: 0; }
.cc-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.dot-strong-green { background: var(--color-success-glow); box-shadow: 0 0 8px var(--color-success-glow); }
.dot-green        { background: var(--color-success-pale); }
.dot-green-dim    { background: var(--color-success-pale); opacity: 0.55; }
.dot-strong-red   { background: var(--color-danger-alert); box-shadow: 0 0 8px var(--color-danger-alert); }
.dot-red          { background: var(--color-danger-soft); }
.dot-red-dim      { background: var(--color-danger-soft); opacity: 0.55; }
.dot-unknown      { background: var(--color-text-muted); }
.dot-loading      { background: var(--color-warning); animation: pulse 1.5s ease-in-out infinite; }
@keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: 0.4 } }

.cc-texts   { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
.cc-verdict { font-size: var(--font-size-sm-plus); font-weight: 700; white-space: nowrap; }
.cc-meta    { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.col-green     { color: var(--color-success-glow); }
.col-green-dim { color: var(--color-success-pale); opacity: 0.7; }
.col-red       { color: var(--color-danger-alert); }
.col-red-dim   { color: var(--color-danger-soft); opacity: 0.7; }
.col-dim       { color: var(--color-text-secondary); font-weight: 500; }

.cc-right { display: flex; flex-direction: column; gap: 0.2rem; align-items: flex-end; flex-shrink: 0; }
.cc-hr    { display: flex; align-items: center; gap: 0.25rem; }
.hr-arrow { font-size: var(--font-size-sm-plus); font-weight: 700; }
.hr-val   { font-size: var(--font-size-sm-plus); font-weight: 600; color: var(--color-text-secondary-bright); font-variant-numeric: tabular-nums; }
.hr-arrow.pos { color: var(--color-success-glow); }
.hr-arrow.neg { color: var(--color-danger-alert); }

.cc-chev {
  font-size: 1.2rem; color: var(--color-text-muted); flex-shrink: 0;
  transition: transform 0.2s, color 0.15s; display: inline-block;
}
.cc-active .cc-chev { transform: rotate(90deg); color: var(--color-accent); }

/* ── DETAIL PANEL ───────────────────────────────────────────────────────────── */
.detail-panel {
  background: #13151f;
  border: 1px solid var(--color-accent);
  border-top: none;
  border-radius: 0 0 0.6rem 0.6rem;
  padding: 0.85rem;
  display: flex; flex-direction: column; gap: 1.1rem;
  overflow-x: hidden; /* prevent this panel from widening the page on mobile */
}

/* ── NOW PANEL ──────────────────────────────────────────────────────────────── */
.now-panel { display: flex; flex-direction: column; gap: 0.5rem; }
.now-title { font-size: var(--font-size-sm-plus); font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--color-text-secondary); }
.now-grid  { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.4rem; }
.now-cell  {
  display: flex; flex-direction: column; align-items: center;
  padding: 0.55rem 0.3rem; border-radius: 0.45rem;
  border: 1px solid var(--color-border); gap: 0.1rem; text-align: center;
}
.now-lbl  { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); font-weight: 600; text-transform: uppercase; }
.now-val  { font-size: var(--font-size-base); font-weight: 800; font-variant-numeric: tabular-nums; }
.now-sub  { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }

.now-cell-green     { background: rgba(34,197,94,0.1);  border-color: rgba(34,197,94,0.4); }
.now-cell-green     .now-val { color: var(--color-success-glow); }
.now-cell-green-dim { background: rgba(34,197,94,0.05); border-color: rgba(34,197,94,0.2); }
.now-cell-green-dim .now-val { color: var(--color-success-pale); opacity: 0.75; }
.now-cell-red       { background: rgba(239,68,68,0.1);  border-color: rgba(239,68,68,0.4); }
.now-cell-red       .now-val { color: var(--color-danger-alert); }
.now-cell-red-dim   { background: rgba(239,68,68,0.05); border-color: rgba(239,68,68,0.2); }
.now-cell-red-dim   .now-val { color: var(--color-danger-soft); opacity: 0.75; }
.now-cell-neutral   { background: rgba(255,255,255,0.02); }
.now-cell-neutral   .now-val { color: var(--color-text-secondary-bright); }

.now-data-note  { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }
.low-conf-note  { color: var(--color-warning); }

.status-bar { position: relative; height: 30px; background: var(--color-border); border-radius: 0.35rem; overflow: hidden; display: flex; align-items: center; }
.status-fill  { position: absolute; left: 0; top: 0; bottom: 0; transition: width 0.5s; }
.fill-loading { background: var(--color-accent-muted); }
.status-text  { position: relative; z-index: 1; font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); padding: 0 0.85rem; }

/* ── MASTER CARD ────────────────────────────────────────────────────────────── */
.master-card { border: 1px solid var(--color-text-muted); border-radius: 0.75rem; overflow: hidden; background: var(--color-surface); }

.eg-grid    { display: flex; }
.eg-col     { flex: 1; padding: 1rem 1.1rem; }
.eg-divider { width: 1px; background: var(--color-border); flex-shrink: 0; }
.eg-head { font-size: var(--font-size-sm-plus); font-weight: 800; text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 0.15rem; }
.eg-enter .eg-head { color: var(--color-success-glow); }
.eg-exit  .eg-head { color: var(--color-danger-alert); }
.eg-sub  { font-size: var(--font-size-sm-plus); color: var(--color-text-cool); margin-bottom: 0.8rem; }
.eg-row  { display: flex; align-items: baseline; gap: 0.4rem; margin-bottom: 0.5rem; }
.eg-time { font-size: 1.25rem; font-weight: 800; color: #f7fafc; font-variant-numeric: tabular-nums; min-width: 56px; }
.eg-arrow { font-size: var(--font-size-sm-plus); font-weight: 700; }
.eg-ret   { font-size: var(--font-size-sm-plus); font-weight: 600; font-variant-numeric: tabular-nums; }
.eg-pos   { color: var(--color-success-glow); }
.eg-neg   { color: var(--color-danger-alert); }
.eg-empty { color: var(--color-text-muted); font-size: var(--font-size-sm-plus); }
.eg-low-conf { font-size: var(--font-size-sm-plus); color: var(--color-warning); margin-inline-start: 0.2rem; }

.summary-row { display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem; padding: 0.65rem 1.1rem; border-top: 1px solid var(--color-border); }
.sr-lbl { font-size: var(--font-size-sm-plus); color: var(--color-text-cool); white-space: nowrap; }
.sr-sep { color: var(--color-text-muted); }

.day-chip { padding: 0.2rem 0.6rem; border-radius: 4px; font-size: var(--font-size-sm-plus); font-weight: 700; }
.chip-good     { background: rgba(34,197,94,0.12); color: var(--color-success-glow); border: 1px solid rgba(34,197,94,0.35); }
.chip-good-dim { background: rgba(34,197,94,0.06); color: var(--color-success-pale); border: 1px solid rgba(34,197,94,0.2); opacity: 0.8; }
.chip-bad      { background: rgba(239,68,68,0.12);  color: var(--color-danger-alert); border: 1px solid rgba(239,68,68,0.35); }
.chip-bad-dim  { background: rgba(239,68,68,0.06);  color: var(--color-danger-soft); border: 1px solid rgba(239,68,68,0.2); opacity: 0.8; }

.wom-chip {
  display: inline-flex; align-items: baseline; gap: 0.2rem;
  padding: 0.2rem 0.65rem; border-radius: 4px; font-size: var(--font-size-sm-plus); font-weight: 600;
  background: #1e2130; border: 1px solid var(--color-text-muted); color: var(--color-text-cool);
}
.wom-chip.wom-pos { color: var(--color-success-glow); border-color: rgba(34,197,94,0.4); background: rgba(34,197,94,0.08); }
.wom-chip.wom-neg { color: var(--color-danger-alert); border-color: rgba(239,68,68,0.4); background: rgba(239,68,68,0.08); }
.wom-chip.wom-dim { opacity: 0.65; }
.wom-chip.wom-cur { outline: 2px solid var(--color-accent-strong); outline-offset: 2px; }
.wom-ret  { font-size: var(--font-size-sm-plus); }
.week-rank { font-size: var(--font-size-sm); color: var(--color-text-cool); }

/* ── CHARTS ─────────────────────────────────────────────────────────────────── */
.chart-section { display: flex; flex-direction: column; gap: 0.45rem; }
.cs-header { display: flex; flex-direction: column; gap: 0.1rem; }
.cs-title  { font-size: 1.05rem; font-weight: 700; color: var(--color-text); }
.cs-hint   { font-size: var(--font-size-sm); color: var(--color-text-cool); }

.dv-wrap  { display: flex; gap: 2px; height: 190px; position: relative; overflow-x: auto; -webkit-overflow-scrolling: touch; }
.dv-zero  { position: absolute; top: 85px; left: 0; right: 0; height: 1px; background: var(--color-text-muted); z-index: 1; }
.dv-col   { flex: 1; min-width: 14px; display: flex; flex-direction: column; position: relative; cursor: default; }
.dv-col.dv-now  { background: rgba(144,205,244,0.06); border-radius: 3px; }
.dv-upper { height: 85px; display: flex; flex-direction: column; justify-content: flex-end; }
.dv-lower { height: 85px; display: flex; flex-direction: column; justify-content: flex-start; }
.dv-bar   { width: 100%; }
.dv-pos      { background: var(--color-success-glow); border-radius: 3px 3px 0 0; min-height: 4px; }
.dv-neg      { background: var(--color-danger-alert); border-radius: 0 0 3px 3px; min-height: 4px; }
.dv-pos-dim  { background: rgba(34,197,94,0.4);  border-radius: 3px 3px 0 0; min-height: 4px; }
.dv-neg-dim  { background: rgba(239,68,68,0.4);  border-radius: 0 0 3px 3px; min-height: 4px; }
.dv-lbl   { height: 18px; font-size: var(--font-size-sm-plus); color: var(--color-text-cool); text-align: center; padding-top: 3px; white-space: nowrap; overflow: hidden; }

.mo-wrap  { display: flex; gap: 4px; height: 180px; position: relative; overflow-x: auto; -webkit-overflow-scrolling: touch; }
.mo-zero  { position: absolute; top: 80px; left: 0; right: 0; height: 1px; background: var(--color-text-muted); z-index: 1; }
.mo-col   { flex: 1; min-width: 36px; display: flex; flex-direction: column; align-items: center; cursor: default; }
.mo-upper { height: 80px; width: 100%; display: flex; flex-direction: column; justify-content: flex-end; }
.mo-lower { height: 80px; width: 100%; display: flex; flex-direction: column; justify-content: flex-start; }
.mo-bar   { width: 100%; }
.mo-pos     { background: var(--color-success-glow); border-radius: 4px 4px 0 0; min-height: 5px; }
.mo-neg     { background: var(--color-danger-alert); border-radius: 0 0 4px 4px; min-height: 5px; }
.mo-pos-dim { background: rgba(34,197,94,0.35); border-radius: 4px 4px 0 0; min-height: 5px; }
.mo-neg-dim { background: rgba(239,68,68,0.35); border-radius: 0 0 4px 4px; min-height: 5px; }
.mo-cur-col .mo-pos, .mo-cur-col .mo-neg,
.mo-cur-col .mo-pos-dim, .mo-cur-col .mo-neg-dim { outline: 2px solid var(--color-accent-strong); outline-offset: 3px; }
.mo-lbl     { font-size: var(--font-size-sm-plus); font-weight: 600; color: var(--color-text-secondary-bright); margin-top: 4px; white-space: nowrap; overflow: hidden; }
.mo-lbl-cur { color: var(--color-accent-strong); }
.mo-ret-lbl { font-size: var(--font-size-sm-plus); font-weight: 700; white-space: nowrap; overflow: hidden; }

.wom-wrap { display: flex; gap: 20px; height: 180px; position: relative; overflow-x: auto; -webkit-overflow-scrolling: touch; }
.wom-zero { position: absolute; top: 80px; left: 0; right: 0; height: 1px; background: var(--color-text-muted); z-index: 1; }
.wom-col  { flex: 1; min-width: 48px; display: flex; flex-direction: column; align-items: center; cursor: default; }
.wom-upper { height: 80px; width: 100%; display: flex; flex-direction: column; justify-content: flex-end; }
.wom-lower { height: 80px; width: 100%; display: flex; flex-direction: column; justify-content: flex-start; }
.wom-bar   { width: 100%; }
.wom-pos     { background: var(--color-success-glow); border-radius: 6px 6px 0 0; min-height: 7px; }
.wom-neg     { background: var(--color-danger-alert); border-radius: 0 0 6px 6px; min-height: 7px; }
.wom-pos-dim { background: rgba(34,197,94,0.35); border-radius: 6px 6px 0 0; min-height: 7px; }
.wom-neg-dim { background: rgba(239,68,68,0.35); border-radius: 0 0 6px 6px; min-height: 7px; }
.wom-cur-col .wom-pos, .wom-cur-col .wom-neg,
.wom-cur-col .wom-pos-dim, .wom-cur-col .wom-neg-dim { outline: 2px solid var(--color-accent-strong); outline-offset: 3px; }
.wom-lbl     { font-size: var(--font-size-sm-plus); font-weight: 600; color: var(--color-text-secondary-bright); margin-top: 5px; }
.wom-lbl-cur { color: var(--color-accent-strong); }
.wom-ret-lbl { font-size: var(--font-size-sm-plus); font-weight: 700; }

.wd-wrap  { display: flex; gap: 10px; height: 180px; position: relative; overflow-x: auto; -webkit-overflow-scrolling: touch; }
.wd-zero  { position: absolute; top: 80px; left: 0; right: 0; height: 1px; background: var(--color-text-muted); z-index: 1; }
.wd-col   { flex: 1; min-width: 40px; display: flex; flex-direction: column; align-items: center; cursor: default; }
.wd-upper { height: 80px; width: 100%; display: flex; flex-direction: column; justify-content: flex-end; }
.wd-lower { height: 80px; width: 100%; display: flex; flex-direction: column; justify-content: flex-start; }
.wd-bar   { width: 100%; }
.wd-pos     { background: var(--color-success-glow); border-radius: 4px 4px 0 0; min-height: 5px; }
.wd-neg     { background: var(--color-danger-alert); border-radius: 0 0 4px 4px; min-height: 5px; }
.wd-pos-dim { background: rgba(34,197,94,0.35); border-radius: 4px 4px 0 0; min-height: 5px; }
.wd-neg-dim { background: rgba(239,68,68,0.35); border-radius: 0 0 4px 4px; min-height: 5px; }
.wd-today .wd-pos, .wd-today .wd-neg,
.wd-today .wd-pos-dim, .wd-today .wd-neg-dim { outline: 2px solid var(--color-accent-strong); outline-offset: 3px; }
.wd-lbl       { font-size: var(--font-size-base); font-weight: 600; color: var(--color-text-secondary-bright); margin-top: 5px; }
.wd-lbl-today { color: var(--color-accent-strong); }
.wd-ret       { font-size: var(--font-size-sm-plus); font-weight: 700; }

.pos   { color: var(--color-success-glow); }
.neg   { color: var(--color-danger-alert); }
.empty { color: var(--color-text-muted); font-size: var(--font-size-sm-plus); }
</style>
