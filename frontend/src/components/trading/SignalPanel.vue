<template>

  <!-- ── BTC Gate Open alert banner ──────────────────────────────────────── -->
  <Teleport to="body">
    <Transition name="gate-slide">
      <div v-if="gateAlert" class="gate-open-banner" @click="gateAlert = false">
        <span class="gob-pulse">🟢</span>
        <div class="gob-text">
          <span class="gob-title">{{ t('signal.gate_open') }}</span>
          <span class="gob-sub">{{ t('signal.gate_open_sub') }}</span>
        </div>
        <button class="gob-close" @click.stop="gateAlert = false">✕</button>
      </div>
    </Transition>
  </Teleport>

  <div class="card signal-card" v-bind="$attrs" @click.capture="unlockAudio">
    <div class="card-header">
      <h2>{{ t('signal.title') }}</h2>
      <div class="sp-header-right">
        <span v-if="lastUpdated" class="sp-age">{{ ageLabel }}</span>
        <button class="sp-refresh" :class="{ spinning: loading }" @click="unlockAudio(); loadAll()" title="Refresh">↻</button>
      </div>
    </div>

    <!-- ── Bot control strip ──────────────────────────────────────────────── -->
    <div class="bot-strip" :class="botEnabled ? 'bs-on' : 'bs-off'">

      <!-- Row 1: status + toggle -->
      <div class="bs-top">
        <div class="bs-info">
          <span class="bs-dot" :class="botEnabled ? 'dot-on' : 'dot-off'"></span>
          <span class="bs-status">{{ botEnabled ? t('signal.bot_on') : t('signal.bot_off') }}</span>
          <span v-if="botEnabled" class="bs-config">
            · {{ t('signal.bot_config', { enter: botConfig.hotness_min, max: botConfig.max_positions, usd: botConfig.position_usd }) }}
          </span>
        </div>
        <div class="bs-ctrl">
          <template v-if="showToggleConfirm">
            <span class="bs-ask">{{ botEnabled ? t('signal.toggle_confirm_off') : t('signal.toggle_confirm_on') }}</span>
            <button class="bs-yes" @click="doToggleBot">{{ t('signal.confirm_yes') }}</button>
            <button class="bs-no"  @click="showToggleConfirm = false">{{ t('signal.confirm_cancel') }}</button>
          </template>
          <button v-else class="bs-toggle" :class="botEnabled ? 'btn-off' : 'btn-on'" @click="showToggleConfirm = true">
            {{ botEnabled ? t('signal.pause_bot') : t('signal.enable_bot') }}
          </button>
        </div>
      </div>

      <!-- Row 2: quick stats -->
      <div class="bs-stats">
        <div class="bss-cell">
          <span class="bss-val">{{ openPositions }}</span>
          <span class="bss-lbl">{{ t('signal.bs_open') }}</span>
        </div>
        <div class="bss-sep"></div>
        <div class="bss-cell">
          <span class="bss-val">{{ totalClosedTrades }}</span>
          <span class="bss-lbl">{{ t('signal.bs_trades') }}</span>
        </div>
        <div class="bss-sep"></div>
        <div class="bss-cell">
          <span class="bss-val" :class="overallWinRate != null ? (overallWinRate >= 50 ? 'pnl-pos' : 'pnl-neg') : ''">
            {{ overallWinRate != null ? overallWinRate + '%' : '—' }}
          </span>
          <span class="bss-lbl">{{ t('signal.bs_winrate') }}</span>
        </div>
        <div class="bss-sep"></div>
        <div class="bss-cell">
          <span class="bss-val" :class="botNetPnl >= 0 ? 'pnl-pos' : 'pnl-neg'">
            {{ totalClosedTrades > 0 || openPositions > 0
               ? (botNetPnl >= 0 ? '+' : '') + '$' + Math.abs(botNetPnl).toFixed(0)
               : '—' }}
          </span>
          <span class="bss-lbl">{{ t('signal.bs_net') }}</span>
        </div>
      </div>

      <!-- Row 3: entry/exit score quality -->
      <div v-if="avgEntryScore != null" class="bs-quality">
        <span class="bsq-title">{{ t('signal.bs_quality') }}</span>
        <div class="bsq-scores">

          <!-- Entry gauge -->
          <div class="bsq-gauge">
            <div class="bsq-score-line">
              <span class="bsq-arrow-up">▲</span>
              <span class="bsq-score-val" :class="avgEntryScore >= botConfig.enter_at ? 'pnl-pos' : 'bsq-warn'">{{ avgEntryScore }}</span>
              <span class="bsq-score-max">/100</span>
            </div>
            <div class="bsq-bar">
              <div class="bsq-fill bsq-entry-fill" :style="{ width: avgEntryScore + '%' }"></div>
              <div class="bsq-thresh" :style="{ left: botConfig.enter_at + '%' }"></div>
            </div>
            <span class="bsq-lbl">{{ t('signal.bs_avg_entry') }}</span>
          </div>

          <span class="bsq-sep-arrow">→</span>

          <!-- Exit gauge -->
          <div class="bsq-gauge">
            <div class="bsq-score-line">
              <span class="bsq-arrow-dn">▼</span>
              <span class="bsq-score-val" :class="avgExitScore <= botConfig.exit_at ? 'pnl-pos' : 'bsq-warn'">{{ avgExitScore }}</span>
              <span class="bsq-score-max">/100</span>
            </div>
            <div class="bsq-bar">
              <div class="bsq-fill bsq-exit-fill" :style="{ width: avgExitScore + '%' }"></div>
              <div class="bsq-thresh" :style="{ left: botConfig.exit_at + '%' }"></div>
            </div>
            <span class="bsq-lbl">{{ t('signal.bs_avg_exit') }}</span>
          </div>

          <div class="bss-sep"></div>

          <!-- On-target exits -->
          <div class="bsq-target">
            <span class="bsq-target-val"
                  :class="onTargetExits >= 70 ? 'pnl-pos' : onTargetExits >= 50 ? 'bsq-warn' : 'pnl-neg'">
              {{ onTargetExits != null ? onTargetExits + '%' : '—' }}
            </span>
            <span class="bsq-lbl">{{ t('signal.bs_on_target') }}</span>
          </div>

        </div>
      </div>

      <!-- Row 4: last bot action -->
      <div v-if="botEnabled && botActivity.length" class="bs-last">
        <span class="bsl-lbl">{{ t('signal.bs_last') }}</span>
        <span class="bsl-action" :class="botActivity[0].action === 'OPENED' ? 'bsl-open' : 'bsl-close'">
          {{ botActivity[0].action === 'OPENED' ? '▶' : '◼' }} {{ botActivity[0].symbol }}
        </span>
        <span class="bsl-price">${{ botActivity[0].price?.toPrecision(5) }}</span>
        <span class="bsl-score">{{ botActivity[0].score }}/100</span>
        <span v-if="botActivity[0].pnl != null"
              class="bsl-pnl" :class="botActivity[0].pnl >= 0 ? 'pnl-pos' : 'pnl-neg'">
          {{ botActivity[0].pnl >= 0 ? '+' : '' }}{{ botActivity[0].pnl }}%
        </span>
        <span class="bsl-time">{{ fmtTime(botActivity[0].ts) }}</span>
      </div>

    </div>

    <!-- ── Atmosphere Panel (BTC gate + weather score + CB combined) ─────── -->
    <AtmospherePanel
      :score="atmScore"
      :label="atmLabel"
      :boost="atmBoost"
      :computed-at="atmComputedAt"
      :gate-on="atmGateOn"
      :boost-on="atmBoostOn"
      :loading="atmLoading"
      :btc-regime="btcRegime"
      :drawdown="drawdown"
      :cb-in-paper-mode="botConfig.cb_in_paper_mode ?? false"
      @toggle-gate="toggleAtmosphereGate"
      @toggle-boost="toggleAtmosphereBoost"
      @refresh="refreshAtmosphere"
    />

    <!-- ── Leaderboard ───────────────────────────────────────────────────── -->
    <div v-if="leaderboard.length" class="leaderboard">
      <div class="lb-title">
        {{ t('signal.lb_title') }}
        <span class="lb-total" :class="leaderboardTotal >= 0 ? 'pnl-pos' : 'pnl-neg'">
          {{ t('signal.lb_net_label') }} {{ leaderboardTotal >= 0 ? '+' : '' }}${{ leaderboardTotal.toFixed(2) }}
        </span>
      </div>
      <div class="lb-head">
        <span>{{ t('signal.lb_coin') }}</span>
        <span>{{ t('signal.lb_trades') }}</span>
        <span>{{ t('signal.lb_winrate') }}</span>
        <span class="lb-h-r">{{ t('signal.lb_realised') }}</span>
        <span class="lb-h-r">{{ t('signal.lb_open_pnl') }}</span>
        <span class="lb-h-r">{{ t('signal.lb_net') }}</span>
      </div>
      <div v-for="row in leaderboard" :key="row.symbol" class="lb-row" :class="row.net_usd >= 0 ? 'lb-pos' : 'lb-neg'">
        <span class="lb-sym">{{ row.symbol }}</span>
        <span class="lb-trades">{{ row.closed_trades }}c {{ row.open_trades > 0 ? row.open_trades + 'o' : '' }}</span>
        <span class="lb-wr">{{ row.win_rate != null ? row.win_rate + '%' : '—' }}</span>
        <span class="lb-val" :class="row.realised_usd >= 0 ? 'pnl-pos' : 'pnl-neg'">
          {{ row.realised_usd >= 0 ? '+' : '' }}${{ row.realised_usd.toFixed(2) }}
        </span>
        <span class="lb-val" :class="row.unrealised_usd !== 0 ? (row.unrealised_usd >= 0 ? 'pnl-pos' : 'pnl-neg') : 'lb-dash'">
          {{ row.unrealised_usd !== 0 ? (row.unrealised_usd >= 0 ? '+' : '') + '$' + row.unrealised_usd.toFixed(2) : '—' }}
        </span>
        <span class="lb-net" :class="row.net_usd >= 0 ? 'pnl-pos' : 'pnl-neg'">
          {{ row.net_usd >= 0 ? '+' : '' }}${{ row.net_usd.toFixed(2) }}
        </span>
      </div>
    </div>

    <!-- ── Bot activity log ───────────────────────────────────────────────── -->
    <div v-if="botActivity.length" class="activity-log">
      <div class="al-title">{{ t('signal.activity_title') }}</div>
      <div v-for="(ev, i) in botActivity" :key="i" class="al-row">
        <span class="al-action" :class="ev.action === 'OPENED' ? 'al-open' : 'al-close'">
          {{ ev.action === 'OPENED' ? t('signal.action_open') : t('signal.action_close') }}
        </span>
        <span class="al-sym">{{ ev.symbol }}</span>
        <span class="al-price">${{ ev.price?.toPrecision(5) }}</span>
        <span class="al-score">{{ ev.score }}/100</span>
        <span v-if="ev.pnl != null" class="al-pnl" :class="ev.pnl >= 0 ? 'pnl-pos' : 'pnl-neg'">
          {{ ev.pnl >= 0 ? '+' : '' }}{{ ev.pnl }}%
        </span>
        <span class="al-time">{{ fmtTime(ev.ts) }}</span>
      </div>
    </div>
    <div v-else-if="botEnabled" class="al-empty">{{ t('signal.bot_idle') }}</div>

    <!-- ── Trade History ─────────────────────────────────────────────────── -->
    <div v-if="tradeHistory.length" class="th-section">
      <div class="th-header">
        <span class="th-title">{{ t('signal.history_title') }}</span>
        <span class="th-count">{{ t('signal.history_count', { n: tradeHistory.length }) }}</span>
      </div>
      <div class="th-head">
        <span>{{ t('signal.th_coin') }}</span>
        <span>{{ t('signal.th_scores') }}</span>
        <span>{{ t('signal.th_entry_exit') }}</span>
        <span>{{ t('signal.th_held') }}</span>
        <span class="th-right">{{ t('signal.th_pnl') }}</span>
      </div>
      <div v-for="t in tradeHistory" :key="t.id"
           class="th-row" :class="t.pnl_usd >= 0 ? 'th-win' : 'th-loss'"
           @click="toggleHistory(t.id)" style="cursor:pointer">
        <div class="th-main">
          <span class="th-sym">{{ t.symbol }}</span>
          <span class="th-scores">
            <span class="th-sc-open">{{ t.open_score ?? '—' }}</span>
            <span class="th-arrow">→</span>
            <span class="th-sc-close" :class="(t.close_score ?? 99) <= 40 ? 'sc-exit' : ''">{{ t.close_score ?? '—' }}</span>
          </span>
          <span class="th-prices">{{ fmtP(t.entry_price) }} → {{ fmtP(t.exit_price) }}</span>
          <span class="th-dur">{{ fmtDur(t.duration_min) }}</span>
          <span class="th-pnl" :class="t.pnl_usd >= 0 ? 'pnl-pos' : 'pnl-neg'">
            {{ t.pnl_usd >= 0 ? '+' : '' }}${{ t.pnl_usd.toFixed(2) }}
            <span class="th-pct">({{ t.pnl_pct >= 0 ? '+' : '' }}{{ t.pnl_pct }}%)</span>
          </span>
        </div>
        <div v-if="historyExpanded.has(t.id)" class="th-detail">
          <div v-if="t.open_reasons" class="th-reason">
            <span class="th-rl">{{ t('signal.opened_label') }}</span> {{ t.open_reasons }}
          </div>
          <div v-if="t.close_reason" class="th-reason">
            <span class="th-rl">{{ t('signal.closed_label') }}</span> {{ t.close_reason }}
          </div>
          <div class="th-reason muted">
            {{ fmtDate(t.entry_time) }} → {{ fmtDate(t.exit_time) }}
          </div>
        </div>
      </div>
    </div>

    <div class="sp-divider"></div>

    <!-- ── Signal list ────────────────────────────────────────────────────── -->
    <div v-if="loading && !signals.length" class="sp-loading">{{ t('signal.loading') }}</div>

    <div v-else-if="!loading && !signals.length" class="sp-empty">
      {{ t('signal.no_signals') }}
    </div>

    <template v-else>
      <div v-if="actionSignals.length" class="sig-list">
        <div v-for="sig in actionSignals" :key="sig.symbol + sig.action"
             class="sig-row" :class="rowClass(sig)">
          <div class="sig-top">
            <span class="sig-sym">{{ sig.symbol }}</span>
            <span class="sig-action" :class="actionClass(sig)">{{ sig.action }}</span>
            <span class="sig-score">{{ sig.score }}/100</span>
            <span class="sig-badge" v-if="sig.held">HELD</span>
          </div>
          <div class="sig-reasons">
            <span v-for="(r, i) in sig.reasons" :key="i" class="sig-reason">{{ r }}</span>
          </div>
          <div class="sig-bar-wrap">
            <div class="sig-bar-fill" :class="barClass(sig)" :style="{ width: sig.score + '%' }"></div>
            <div class="sig-bar-mid"></div>
          </div>
        </div>
      </div>

      <div v-if="actionSignals.length && holdSignals.length" class="sp-divider"></div>

      <div v-if="holdSignals.length" class="hold-grid">
        <div v-for="sig in holdSignals" :key="sig.symbol"
             class="hold-cell" :class="holdCellClass(sig)" :title="sig.reasons.join(' · ')">
          <span class="hc-sym">{{ sig.symbol }}</span>
          <div class="hc-bar-wrap">
            <div class="hc-bar-fill" :class="barClass(sig)" :style="{ width: sig.score + '%' }"></div>
            <div class="hc-bar-mid"></div>
          </div>
          <span class="hc-score">{{ sig.score }}</span>
        </div>
      </div>

      <div class="sp-note">{{ t('signal.sp_note') }}</div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../../stores/platform'
import AtmospherePanel from './AtmospherePanel.vue'

const { t } = useI18n()

const store   = usePlatformStore()
const signals = ref([])
const loading = ref(false)
const lastUpdated  = ref(null)
const botEnabled   = ref(false)
const botConfig    = ref({ enter_at: 72, exit_at: 40, max_positions: 25, position_usd: 1000 })
const botActivity  = ref([])
const btcRegime    = ref(null)   // { bullish, btc_price, sma50, sma50_updated }
const drawdown     = ref(null)   // { daily_pnl_usd, weekly_pnl_usd, daily_limit, weekly_limit }
const leaderboard  = ref([])
const tradeHistory = ref([])
const historyExpanded = ref(new Set())
const showToggleConfirm = ref(false)
const gateAlert         = ref(false)
let   gateAlertTimer  = null
let   prevGateBullish = null   // null = first load, don't alert
let   timer

// ── Atmosphere ───────────────────────────────────────────────────────────────
const atmosphere     = ref(null)   // full API response
const atmLoading     = ref(false)

const atmScore      = computed(() => atmosphere.value?.score ?? 50)
const atmLabel      = computed(() => atmosphere.value?.label ?? 'neutral')
const atmBoost      = computed(() => atmosphere.value?.boost ?? 1.0)
const atmComponents = computed(() => atmosphere.value?.components ?? {})
const atmComputedAt = computed(() => atmosphere.value?.computed_at ?? null)
const atmGateOn     = computed(() => atmosphere.value?.settings?.gate_enabled ?? false)
const atmBoostOn    = computed(() => atmosphere.value?.settings?.boost_enabled ?? true)

const actionSignals    = computed(() => signals.value.filter(s => s.action !== 'HOLD'))
const holdSignals      = computed(() => signals.value.filter(s => s.action === 'HOLD'))
const leaderboardTotal = computed(() => leaderboard.value.reduce((s, r) => s + r.net_usd, 0))

const openPositions     = computed(() => leaderboard.value.reduce((s, r) => s + (r.open_trades   ?? 0), 0))
const totalClosedTrades = computed(() => leaderboard.value.reduce((s, r) => s + (r.closed_trades  ?? 0), 0))
const totalRealised     = computed(() => leaderboard.value.reduce((s, r) => s + (r.realised_usd   ?? 0), 0))
const totalUnrealised   = computed(() => leaderboard.value.reduce((s, r) => s + (r.unrealised_usd ?? 0), 0))
const botNetPnl         = computed(() => totalRealised.value + totalUnrealised.value)
const overallWinRate    = computed(() => {
  const total = tradeHistory.value.length
  if (!total) return null
  return Math.round(tradeHistory.value.filter(t => t.pnl_usd > 0).length / total * 100)
})

const scoredTrades  = computed(() => tradeHistory.value.filter(t => t.open_score != null))
const avgEntryScore = computed(() => {
  const t = scoredTrades.value
  if (!t.length) return null
  return Math.round(t.reduce((s, r) => s + r.open_score, 0) / t.length)
})
const avgExitScore  = computed(() => {
  const t = scoredTrades.value.filter(r => r.close_score != null)
  if (!t.length) return null
  return Math.round(t.reduce((s, r) => s + r.close_score, 0) / t.length)
})
const onTargetExits = computed(() => {
  // close_score is only set by the backend for signal-driven exits (not SL/TP/trailing),
  // so this filter already excludes mechanical exits by design.
  const eligible = tradeHistory.value.filter(r =>
    r.close_score != null && /score/i.test(r.close_reason ?? '')
  )
  if (!eligible.length) return null
  return Math.round(eligible.filter(r => r.close_score <= botConfig.value.exit_at).length / eligible.length * 100)
})

const ageLabel = computed(() => {
  if (!lastUpdated.value) return ''
  const secs = Math.round((Date.now() - lastUpdated.value) / 1000)
  return secs < 60 ? `${secs}s ago` : `${Math.round(secs / 60)}m ago`
})

async function loadSignals() {
  loading.value = true
  try {
    const data = await store.fetchSignals()
    signals.value    = data.signals ?? []
    lastUpdated.value = Date.now()
  } catch { /* silent */ } finally {
    loading.value = false
  }
}

async function loadBotStatus() {
  try {
    const data = await store.fetchBotStatus()
    botEnabled.value  = data.enabled
    botConfig.value   = data.config ?? botConfig.value
    botActivity.value = data.last_activity ?? []
    const regime = data.btc_regime ?? null
    const isOpen = regime?.bullish === true
    if (prevGateBullish === false && isOpen) triggerGateAlert()
    if (prevGateBullish === null) prevGateBullish = isOpen   // first load: record silently
    else prevGateBullish = isOpen
    btcRegime.value = regime
    drawdown.value  = data.drawdown ?? null
  } catch { /* silent */ }
}

async function loadLeaderboard() {
  try {
    const data = await store.fetchLeaderboard()
    leaderboard.value = data.rows ?? []
  } catch { /* silent */ }
}

async function loadHistory() {
  try {
    const data = await store.fetchBotHistory()
    tradeHistory.value = data.trades ?? []
  } catch { /* silent */ }
}

async function loadAtmosphere() {
  atmLoading.value = true
  try {
    const data = await fetch('/api/spot/atmosphere').then(r => r.json())
    atmosphere.value = data
  } catch { /* silent */ } finally {
    atmLoading.value = false
  }
}

async function refreshAtmosphere() {
  atmLoading.value = true
  try {
    const data = await fetch('/api/spot/atmosphere/refresh', { method: 'POST' }).then(r => r.json())
    atmosphere.value = data
  } catch { /* silent */ } finally {
    atmLoading.value = false
  }
}

async function toggleAtmosphereGate() {
  try {
    const data = await fetch('/api/spot/atmosphere/gate', { method: 'POST' }).then(r => r.json())
    if (atmosphere.value) atmosphere.value.settings = data.settings
  } catch { /* silent */ }
}

async function toggleAtmosphereBoost() {
  try {
    const data = await fetch('/api/spot/atmosphere/boost', { method: 'POST' }).then(r => r.json())
    if (atmosphere.value) atmosphere.value.settings = data.settings
  } catch { /* silent */ }
}

async function loadAll() {
  await Promise.all([loadSignals(), loadBotStatus(), loadLeaderboard(), loadHistory(), loadAtmosphere()])
}

async function doToggleBot() {
  showToggleConfirm.value = false
  try {
    const data = await store.toggleBot()
    botEnabled.value  = data.enabled
    botConfig.value   = data.config ?? botConfig.value
    botActivity.value = data.last_activity ?? []
    btcRegime.value   = data.btc_regime ?? null
    drawdown.value    = data.drawdown   ?? null
  } catch { /* silent */ }
}

function fmtTime(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit', hour12: false })
}

function fmtDate(iso) {
  if (!iso) return '—'
  return new Date(iso + 'Z').toLocaleString('en', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })
}

function fmtDur(min) {
  if (min == null) return '—'
  if (min < 60)   return `${min}m`
  if (min < 1440) return `${Math.floor(min / 60)}h ${min % 60}m`
  return `${Math.floor(min / 1440)}d ${Math.floor((min % 1440) / 60)}h`
}

function fmtP(p) {
  if (!p) return '—'
  if (p >= 10000) return '$' + p.toLocaleString('en', { maximumFractionDigits: 0 })
  if (p >= 1000)  return '$' + p.toFixed(1)
  if (p >= 1)     return '$' + p.toFixed(3)
  return '$' + p.toFixed(4)
}

function toggleHistory(id) {
  const s = new Set(historyExpanded.value)
  s.has(id) ? s.delete(id) : s.add(id)
  historyExpanded.value = s
}

function rowClass(sig) {
  if (sig.action === 'STRONG EXIT') return 'row-critical'
  if (sig.action === 'EXIT')        return 'row-warning'
  if (sig.action === 'MONITOR')     return 'row-monitor'
  if (sig.action === 'ENTER')       return 'row-enter'
  return ''
}
function actionClass(sig) {
  if (sig.action === 'STRONG EXIT') return 'act-critical'
  if (sig.action === 'EXIT')        return 'act-warning'
  if (sig.action === 'MONITOR')     return 'act-monitor'
  if (sig.action === 'ENTER')       return 'act-enter'
  return 'act-hold'
}
function barClass(sig) {
  return sig.score >= 65 ? 'bar-green' : sig.score >= 45 ? 'bar-yellow' : 'bar-red'
}
function holdCellClass(sig) {
  return sig.score >= 65 ? 'hc-green' : sig.score >= 45 ? 'hc-yellow' : 'hc-red'
}

// Shared AudioContext — unlocked on first user gesture (required by mobile browsers)
let audioCtx = null

function unlockAudio() {
  if (audioCtx) return
  try {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)()
  } catch { /* unsupported */ }
}

function playGateOpenSound() {
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)()
    if (audioCtx.state === 'suspended') audioCtx.resume()
    const ctx  = audioCtx
    const gain = ctx.createGain()
    gain.connect(ctx.destination)

    // Three ascending notes: C5 → E5 → G5 (major chord arpeggio)
    const notes = [523.25, 659.25, 783.99]
    notes.forEach((freq, i) => {
      const osc = ctx.createOscillator()
      osc.type = 'sine'
      osc.frequency.value = freq
      osc.connect(gain)
      const start = ctx.currentTime + i * 0.18
      gain.gain.setValueAtTime(0, start)
      gain.gain.linearRampToValueAtTime(0.22, start + 0.04)
      gain.gain.exponentialRampToValueAtTime(0.001, start + 0.55)
      osc.start(start)
      osc.stop(start + 0.6)
    })
  } catch { /* browser blocked audio — silent fail */ }
}

function triggerGateAlert() {
  gateAlert.value = true
  if (!store.muted) playGateOpenSound()
  clearTimeout(gateAlertTimer)
  gateAlertTimer = setTimeout(() => { gateAlert.value = false }, 7000)
}

onMounted(() => {
  loadAll()
  timer = setInterval(loadAll, 5 * 60 * 1000)
})
onUnmounted(() => {
  clearInterval(timer)
  clearTimeout(gateAlertTimer)
})
</script>

<style scoped>
.signal-card { display: flex; flex-direction: column; gap: 0; }

.sp-header-right { display: flex; align-items: center; gap: var(--space-sm); }
.sp-age   { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }
.sp-refresh { background: none; border: none; color: var(--color-text-secondary-bright); font-size: 1.1rem; cursor: pointer; padding: 0.1rem 0.3rem; border-radius: var(--radius-sm); }
.sp-refresh:hover { color: var(--color-text); }
.sp-refresh.spinning { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Bot strip ────────────────────────────────────────────────────────────── */
.bot-strip {
  display: flex;
  flex-direction: column;
  padding: 0.5rem 0.9rem 0.6rem;
  border-radius: var(--radius-lg);
  margin-bottom: 0.6rem;
  gap: var(--space-sm);
}
.bs-on  { background: #162416; border: 1px solid var(--color-success-emphasis); }
.bs-off { background: var(--color-surface-muted); border: 1px solid var(--color-border); }

.bs-top  { display: flex; align-items: center; justify-content: space-between; gap: var(--space-md); }
.bs-info { display: flex; align-items: center; flex: 1; gap: 0.45rem; min-width: 0; overflow: hidden; }
.bs-dot  { width: 8px; height: 8px; border-radius: var(--radius-circle); flex-shrink: 0; }
.dot-on  { background: var(--color-success); box-shadow: 0 0 6px var(--color-success); animation: pulse 2s infinite; }
.dot-off { background: var(--color-text-muted); }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.4; } }
.bs-status { font-size: var(--font-size-sm-plus); font-weight: var(--font-weight-bold); color: var(--color-text); white-space: nowrap; flex-shrink: 0; }
.bs-config { font-size: var(--font-size-xs); color: var(--color-text-blue-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

.bs-ctrl  { display: flex; align-items: center; gap: 0.4rem; flex-shrink: 0; }
.bs-ask   { font-size: var(--font-size-sm); color: var(--color-text-secondary-bright); white-space: nowrap; }
.bs-yes   { padding: 0.28rem 0.65rem; border-radius: var(--radius-sm); border: none; font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); cursor: pointer; background: var(--color-success-emphasis); color: var(--color-success-tint2); white-space: nowrap; }
.bs-yes:hover { background: #2f855a; }
.bs-no    { padding: 0.28rem 0.65rem; border-radius: var(--radius-sm); border: none; font-size: var(--font-size-sm); cursor: pointer; background: var(--color-surface-raised); color: var(--color-text-secondary-bright); white-space: nowrap; }
.bs-no:hover  { background: #374151; }

.bs-toggle {
  flex-shrink: 0;
  padding: 0.35rem 0.9rem;
  border-radius: var(--radius-md);
  border: none;
  font-size: var(--font-size-sm-plus);
  font-weight: var(--font-weight-bold);
  cursor: pointer;
  letter-spacing: 0.03em;
  white-space: nowrap;
}
.btn-on  { background: var(--color-success-emphasis); color: var(--color-success-tint2); }
.btn-on:hover  { background: #2f855a; }
.btn-off { background: var(--color-danger-mid); color: var(--color-danger-tint); }
.btn-off:hover { background: #9b2c2c; }

/* ── Bot stats row ─────────────────────────────────────────────────────────── */
.bs-stats {
  display: flex;
  align-items: center;
  padding-top: 0.45rem;
  border-top: 1px solid rgba(255,255,255,0.07);
}
.bss-cell {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.1rem;
}
.bss-sep  { width: 1px; height: 28px; background: rgba(255,255,255,0.1); flex-shrink: 0; }
.bss-val  { font-size: var(--font-size-base); font-weight: var(--font-weight-bold); color: var(--color-text); line-height: var(--line-height-tight); font-variant-numeric: tabular-nums; }
.bss-lbl  { font-size: var(--font-size-2xs-plus); color: var(--color-text-blue-dim); text-transform: uppercase; letter-spacing: 0.05em; }

/* ── Last action row ──────────────────────────────────────────────────────── */
.bs-last {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  padding-top: 0.4rem;
  border-top: 1px solid rgba(255,255,255,0.07);
  font-size: var(--font-size-sm);
  overflow: hidden;
}
.bsl-lbl    { color: var(--color-text-blue-dim); font-size: var(--font-size-xs); text-transform: uppercase; letter-spacing: 0.05em; flex-shrink: 0; }
.bsl-action { font-weight: var(--font-weight-bold); flex-shrink: 0; }
.bsl-open   { color: var(--color-success); }
.bsl-close  { color: var(--color-danger); }
.bsl-price  { color: var(--color-text-secondary-bright); flex-shrink: 0; }
.bsl-score  { color: var(--color-text-blue-dim); flex-shrink: 0; }
.bsl-pnl    { font-weight: var(--font-weight-semibold); flex-shrink: 0; }
.bsl-time   { color: var(--color-text-blue-dim); margin-inline-start: auto; flex-shrink: 0; }

/* ── Score quality row ─────────────────────────────────────────────────────── */
.bs-quality {
  padding-top: 0.45rem;
  border-top: 1px solid rgba(255,255,255,0.07);
  display: flex;
  flex-direction: column;
  gap: 0.38rem;
}
.bsq-title  { font-size: var(--font-size-xs); text-transform: uppercase; letter-spacing: 0.06em; color: var(--color-accent-strong); font-weight: var(--font-weight-bold); }
.bsq-scores { display: flex; align-items: center; gap: 0.55rem; }
.bsq-gauge  { flex: 1; display: flex; flex-direction: column; gap: 0.18rem; min-width: 0; }
.bsq-score-line { display: flex; align-items: baseline; gap: 0.2rem; }
.bsq-arrow-up  { color: var(--color-success); font-size: var(--font-size-xs); }
.bsq-arrow-dn  { color: var(--color-danger); font-size: var(--font-size-xs); }
.bsq-score-val { font-size: 1.1rem; font-weight: var(--font-weight-extrabold); font-variant-numeric: tabular-nums; }
.bsq-score-max { font-size: var(--font-size-xs); color: rgba(255,255,255,0.35); }
.bsq-lbl { font-size: var(--font-size-2xs-plus); color: var(--color-text-blue-dim); text-transform: uppercase; letter-spacing: 0.04em; }
.bsq-warn { color: var(--color-warning); }
.bsq-bar  {
  position: relative; height: 4px;
  background: rgba(255,255,255,0.1); border-radius: var(--radius-xs); overflow: visible;
}
.bsq-fill { height: 100%; border-radius: var(--radius-xs); transition: width 0.5s ease; }
.bsq-entry-fill { background: var(--color-success); }
.bsq-exit-fill  { background: var(--color-danger); }
.bsq-thresh {
  position: absolute; top: -3px; width: 2px; height: 10px;
  background: rgba(255,255,255,0.55); border-radius: 1px;
}
.bsq-sep-arrow { font-size: var(--font-size-sm-plus); color: rgba(255,255,255,0.25); flex-shrink: 0; margin-top: -14px; }
.bsq-target { display: flex; flex-direction: column; align-items: center; gap: 0.1rem; flex-shrink: 0; min-width: 46px; }
.bsq-target-val { font-size: var(--font-size-base); font-weight: var(--font-weight-extrabold); font-variant-numeric: tabular-nums; }

/* ── Gate status row ──────────────────────────────────────────────────────── */
.gate-row {
  display: flex; flex-wrap: wrap; align-items: center; gap: var(--space-sm);
  padding: 0.4rem 0.6rem;
  background: var(--color-bg); border-radius: 0.35rem;
  font-size: var(--font-size-sm-plus);
}
.gate-pill {
  font-weight: var(--font-weight-bold); padding: 0.15rem 0.55rem; border-radius: var(--radius-pill); font-size: var(--font-size-sm-plus);
  white-space: nowrap;
}
.gate-open   { background: var(--color-success-bg); color: var(--color-success-strong); border: 1px solid var(--color-success-emphasis); }
.gate-closed { background: #2d1515; color: var(--color-danger); border: 1px solid var(--color-danger-mid); }
.gate-detail { color: var(--color-text-secondary); }
.gate-sep     { color: var(--color-text-muted); }
.gate-neutral { background: var(--color-surface-muted); color: var(--color-text-secondary); border: 1px solid var(--color-border); }


/* ── Leaderboard ──────────────────────────────────────────────────────────── */
.leaderboard { margin-bottom: 0.8rem; }
.lb-title {
  display: flex; align-items: center; justify-content: space-between;
  font-size: var(--font-size-sm-plus); font-weight: var(--font-weight-bold); color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.05em;
  margin-bottom: 0.4rem;
}
.lb-total { font-size: var(--font-size-sm-plus); font-weight: var(--font-weight-bold); letter-spacing: 0; text-transform: none; }
.lb-head  {
  display: grid; grid-template-columns: 52px 54px 56px 1fr 1fr 1fr;
  font-size: var(--font-size-xs); color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.04em;
  padding: 0 0.4rem 0.25rem; gap: 0.3rem;
}
.lb-h-r { text-align: end; }
.lb-row   {
  display: grid; grid-template-columns: 52px 54px 56px 1fr 1fr 1fr;
  align-items: center; gap: 0.3rem;
  padding: 0.28rem 0.4rem; font-size: var(--font-size-sm-plus);
  border-radius: var(--radius-sm); margin-bottom: 1px;
}
.lb-pos { background: #0f1f12; }
.lb-neg { background: #1f0f0f; }
.lb-sym    { font-weight: var(--font-weight-bold); color: var(--color-text); }
.lb-trades { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }
.lb-wr     { color: var(--color-text-secondary-bright); }
.lb-val    { text-align: end; }
.lb-net    { text-align: end; font-weight: var(--font-weight-bold); }
.lb-dash   { text-align: end; color: var(--color-text-subtle); }
.pnl-pos   { color: var(--color-success-strong); }
.pnl-neg   { color: var(--color-danger); }

/* ── Activity log ─────────────────────────────────────────────────────────── */
.activity-log { margin-bottom: 0.6rem; }
.al-title { font-size: var(--font-size-sm-plus); font-weight: var(--font-weight-bold); color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem; }
.al-row   { display: flex; align-items: center; gap: var(--space-sm); padding: 0.22rem 0; font-size: var(--font-size-sm-plus); border-bottom: 1px solid var(--color-surface-muted); }
.al-action { font-weight: var(--font-weight-bold); font-size: var(--font-size-sm-plus); width: 58px; flex-shrink: 0; }
.al-open   { color: var(--color-success-strong); }
.al-close  { color: var(--color-danger); }
.al-sym    { font-weight: var(--font-weight-semibold); color: var(--color-text); width: 40px; }
.al-price  { color: var(--color-text-secondary-bright); flex: 1; }
.al-score  { color: var(--color-text-secondary); width: 44px; text-align: end; }
.al-pnl    { width: 52px; text-align: end; font-weight: var(--font-weight-semibold); }
.pnl-pos   { color: var(--color-success-strong); }
.pnl-neg   { color: var(--color-danger); }
.al-time   { color: var(--color-text-muted); width: 44px; text-align: end; }
.al-empty  { font-size: var(--font-size-sm-plus); color: var(--color-text-muted); padding: 0.3rem 0 0.6rem; }

/* ── Divider ──────────────────────────────────────────────────────────────── */
.sp-divider { height: 1px; background: var(--color-border); margin: var(--space-sm) 0; }

.sp-loading { padding: var(--space-lg) 0; color: var(--color-text-secondary); font-size: var(--font-size-sm-plus); text-align: center; }
.sp-empty   { padding: var(--space-lg) 0; color: var(--color-text-secondary); font-size: var(--font-size-base); text-align: center; line-height: var(--line-height-relaxed); }

/* ── Signal rows ──────────────────────────────────────────────────────────── */
.sig-list { display: flex; flex-direction: column; gap: 0.6rem; margin-bottom: 0.4rem; }
.sig-row  { padding: 0.7rem 0.9rem; border-radius: var(--radius-lg); border-inline-start: 3px solid transparent; background: var(--color-surface-muted); }
.row-critical { border-inline-start-color: var(--color-danger); background: var(--color-danger-bg); }
.row-warning  { border-inline-start-color: var(--color-warning); background: #2a1f0e; }
.row-monitor  { border-inline-start-color: var(--color-warning-tint); background: #252010; }
.row-enter    { border-inline-start-color: var(--color-success-strong); background: #162416; }

.sig-top { display: flex; align-items: center; gap: var(--space-sm); margin-bottom: 0.35rem; }
.sig-sym    { font-weight: var(--font-weight-bold); font-size: var(--font-size-base); color: var(--color-text); }
.sig-action { font-size: var(--font-size-sm-plus); font-weight: var(--font-weight-bold); letter-spacing: 0.05em; padding: 0.1rem 0.45rem; border-radius: var(--radius-sm); }
.act-critical { background: var(--color-danger-mid); color: var(--color-danger); }
.act-warning  { background: #7b341e; color: var(--color-warning); }
.act-monitor  { background: #5f4a00; color: var(--color-warning-tint); }
.act-enter    { background: #1a3d22; color: var(--color-success-strong); }
.act-hold     { background: #1a2535; color: var(--color-accent); }
.sig-score { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); margin-inline-start: auto; }
.sig-badge { font-size: var(--font-size-sm-plus); background: var(--color-surface-raised); color: var(--color-text-secondary-bright); padding: 0.1rem 0.35rem; border-radius: 3px; }

.sig-reasons { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.45rem; }
.sig-reason  { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); background: var(--color-surface-raised); padding: 0.1rem 0.4rem; border-radius: var(--radius-sm); }

.sig-bar-wrap { position: relative; height: 4px; background: var(--color-surface-raised); border-radius: var(--radius-xs); overflow: hidden; }
.sig-bar-fill { height: 100%; border-radius: var(--radius-xs); transition: width 0.4s ease; }
.sig-bar-mid  { position: absolute; inset-inline-start: 50%; top: 0; width: 1px; height: 100%; background: var(--color-text-muted); }
.bar-green  { background: var(--color-success); }
.bar-yellow { background: var(--color-warning-tint); }
.bar-red    { background: var(--color-danger); }

/* ── Hold grid ────────────────────────────────────────────────────────────── */
.hold-grid { display: flex; flex-direction: column; gap: 0.35rem; }
.hold-cell { display: grid; grid-template-columns: 56px 1fr 32px; align-items: center; gap: var(--space-sm); padding: 0.3rem 0.6rem; border-radius: var(--radius-md); background: var(--color-surface-muted); }
.hc-green  { border-inline-start: 2px solid var(--color-success); }
.hc-yellow { border-inline-start: 2px solid var(--color-warning-tint); }
.hc-red    { border-inline-start: 2px solid var(--color-danger); }
.hc-sym    { font-size: var(--font-size-sm-plus); font-weight: var(--font-weight-semibold); color: var(--color-text-secondary-bright); }
.hc-score  { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); text-align: end; }
.hc-bar-wrap { position: relative; height: 3px; background: var(--color-surface-raised); border-radius: var(--radius-xs); overflow: hidden; }
.hc-bar-fill { height: 100%; border-radius: var(--radius-xs); }
.hc-bar-mid  { position: absolute; inset-inline-start: 50%; top: 0; width: 1px; height: 100%; background: var(--color-text-muted); }

.sp-note { margin-top: 0.8rem; font-size: var(--font-size-sm-plus); color: var(--color-text-muted); text-align: center; line-height: var(--line-height-normal); }

/* ── Trade history ────────────────────────────────────────────────────────── */
.th-section { margin-bottom: 0.6rem; }
.th-header  { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.35rem; }
.th-title   { font-size: var(--font-size-sm-plus); font-weight: var(--font-weight-bold); color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.05em; }
.th-count   { font-size: var(--font-size-sm-plus); color: var(--color-text-muted); }

.th-head {
  display: grid;
  grid-template-columns: 48px 60px 1fr 44px 90px;
  font-size: var(--font-size-sm-plus); color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.04em;
  padding: 0 0.5rem 0.2rem; gap: 0.3rem;
}
.th-right { text-align: end; }

.th-row {
  border-radius: var(--radius-sm);
  margin-bottom: 2px;
  overflow: hidden;
}
.th-win  { background: #0d1a0f; border-inline-start: 2px solid var(--color-success-emphasis); }
.th-loss { background: #1a0d0d; border-inline-start: 2px solid var(--color-danger-mid); }

.th-main {
  display: grid;
  grid-template-columns: 48px 60px 1fr 44px 90px;
  align-items: center; gap: 0.3rem;
  padding: 0.32rem 0.5rem;
}
.th-sym    { font-size: var(--font-size-sm-plus); font-weight: var(--font-weight-bold); color: var(--color-text); }
.th-scores { display: flex; align-items: center; gap: 0.2rem; font-size: var(--font-size-sm-plus); }
.th-sc-open  { color: var(--color-success-strong); font-weight: var(--font-weight-semibold); }
.th-arrow    { color: var(--color-text-muted); font-size: var(--font-size-sm-plus); }
.th-sc-close { color: var(--color-text-secondary-bright); }
.sc-exit     { color: var(--color-danger); }
.th-prices { font-size: var(--font-size-xs); color: var(--color-text-secondary-bright); }
.th-dur    { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }
.th-pnl    { font-size: var(--font-size-sm-plus); font-weight: var(--font-weight-bold); text-align: end; }
.th-pct    { font-size: var(--font-size-sm-plus); font-weight: var(--font-weight-regular); }

.th-detail { padding: 0.3rem 0.5rem 0.4rem; border-top: 1px solid #1f2937; }
.th-reason { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); line-height: var(--line-height-relaxed); }
.th-rl     { color: var(--color-text-muted); font-size: var(--font-size-sm-plus); text-transform: uppercase; letter-spacing: 0.04em; }
.muted     { color: var(--color-text-muted) !important; }

/* ── BTC Gate Open banner ─────────────────────────────────────────────────── */
.gate-open-banner {
  position: fixed;
  top: 0;
  inset-inline: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.85rem var(--space-lg);
  background: linear-gradient(135deg, #1a3a1a 0%, #14532d 60%, #166534 100%);
  border-bottom: 2px solid var(--color-success-glow);
  box-shadow: 0 4px 24px rgba(34, 197, 94, 0.35);
  cursor: pointer;
  animation: gate-glow 1.8s ease-in-out infinite alternate;
}

@keyframes gate-glow {
  from { box-shadow: 0 4px 24px rgba(34, 197, 94, 0.35); }
  to   { box-shadow: 0 4px 36px rgba(34, 197, 94, 0.7);  }
}

.gob-pulse {
  font-size: 1.4rem;
  animation: gob-pop 0.6s ease-out;
}
@keyframes gob-pop {
  0%   { transform: scale(0.4); opacity: 0; }
  70%  { transform: scale(1.3); }
  100% { transform: scale(1);   opacity: 1; }
}

.gob-text  { display: flex; flex-direction: column; flex: 1; gap: 0.1rem; }
.gob-title { font-size: var(--font-size-base); font-weight: var(--font-weight-extrabold); color: #86efac; letter-spacing: 0.02em; }
.gob-sub   { font-size: var(--font-size-sm-plus); color: var(--color-success-pale); }

.gob-close {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.15);
  color: #86efac;
  width: 28px; height: 28px;
  border-radius: var(--radius-circle);
  cursor: pointer;
  font-size: var(--font-size-sm-plus);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.gob-close:active { background: rgba(255,255,255,0.2); }

/* Slide-down transition */
.gate-slide-enter-active { transition: transform 0.38s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.3s ease; }
.gate-slide-leave-active { transition: transform 0.28s ease-in, opacity 0.25s ease; }
.gate-slide-enter-from  { transform: translateY(-100%); opacity: 0; }
.gate-slide-leave-to    { transform: translateY(-100%); opacity: 0; }
</style>
