<template>
  <div class="card journal-card">

    <!-- ── Header ─────────────────────────────────────────────────────────── -->
    <div class="card-header">
      <h2>{{ t('journal.title') }}</h2>
      <div class="header-actions">
        <button class="refresh-icon-btn" :class="{ spinning: refreshing }" @click="refreshAll" :disabled="refreshing" title="Refresh">↻</button>
        <button v-if="journalTab === 'trades'" class="log-btn" @click="toggleForm">
          {{ showForm ? t('journal.cancel') : t('journal.log_btn') }}
        </button>
      </div>
    </div>

    <!-- ── Summary grid ──────────────────────────────────────────────────── -->
    <div class="jsum-grid">
      <div class="jsum-cell">
        <span class="jsum-label">{{ t('journal.pnl') }}</span>
        <span class="jsum-val" :class="totalPnlUsd >= 0 ? 'pos' : 'neg'">
          {{ totalPnlUsd >= 0 ? '+' : '' }}${{ totalPnlUsd.toFixed(2) }}
        </span>
        <span v-if="unrealizedPnlUsd !== 0" class="jsum-sub" :class="unrealizedPnlUsd >= 0 ? 'pos' : 'neg'">
          {{ unrealizedPnlUsd >= 0 ? '▲' : '▼' }} ${{ Math.abs(unrealizedPnlUsd).toFixed(2) }} {{ t('journal.live_badge') }}
        </span>
        <span v-else class="jsum-sub muted">{{ t('journal.realized_only') }}</span>
      </div>
      <div class="jsum-cell">
        <span class="jsum-label">{{ t('journal.win_rate') }}</span>
        <span class="jsum-val neutral">{{ summary.win_rate != null ? summary.win_rate + '%' : '—' }}</span>
        <span v-if="summary.wins != null" class="jsum-sub muted">{{ summary.wins }}W · {{ summary.losses }}L</span>
        <span v-else class="jsum-sub muted">—</span>
      </div>
      <div class="jsum-cell jsum-cell-sm">
        <span class="jsum-label">{{ t('journal.trades_lbl') }}</span>
        <div class="jsum-counts">
          <span class="jsum-count-item">
            <span class="jsum-count-dot dot-open"></span>
            <span class="jsum-count-n">{{ summary.open_count ?? 0 }}</span>
            <span class="jsum-count-lbl">{{ t('journal.open_lbl') }}</span>
          </span>
          <span class="jsum-count-sep">·</span>
          <span class="jsum-count-item">
            <span class="jsum-count-dot dot-closed"></span>
            <span class="jsum-count-n">{{ summary.closed_count ?? 0 }}</span>
            <span class="jsum-count-lbl">{{ t('journal.closed_lbl') }}</span>
          </span>
        </div>
        <span v-if="avgPnlUsd !== null" class="jsum-sub" :class="avgPnlUsd >= 0 ? 'pos' : 'neg'">
          {{ t('journal.avg_trade') }} {{ avgPnlUsd >= 0 ? '+' : '' }}${{ avgPnlUsd.toFixed(2) }}
        </span>
      </div>
      <div class="jsum-cell jsum-cell-sm">
        <span class="jsum-label">{{ t('journal.best_worst_lbl') }}</span>
        <div class="jsum-bw">
          <div class="jsum-bw-row">
            <span class="jsum-bw-arrow pos">▲</span>
            <span class="jsum-bw-val pos">{{ summary.best_trade != null ? (summary.best_trade >= 0 ? '+' : '') + '$' + summary.best_trade.toFixed(2) : '—' }}</span>
          </div>
          <div class="jsum-bw-row">
            <span class="jsum-bw-arrow neg">▼</span>
            <span class="jsum-bw-val neg">{{ summary.worst_trade != null ? '$' + summary.worst_trade.toFixed(2) : '—' }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Internal sub-tabs ──────────────────────────────────────────────── -->
    <div class="journal-tabs">
      <button :class="['jtab-btn', { active: journalTab === 'trades' }]"   @click="journalTab = 'trades'">{{ t('journal.tab_trades') }}</button>
      <button :class="['jtab-btn', { active: journalTab === 'rankings' }]" @click="switchToRankings">{{ t('journal.tab_rankings') }}</button>
    </div>

    <!-- ══════════════════════ TRADES TAB ════════════════════════════════════ -->
    <template v-if="journalTab === 'trades'">

      <!-- ── Log Trade form ──────────────────────────────────────────────── -->
      <div v-if="showForm" class="trade-form">
        <div class="form-row">
          <label>{{ t('journal.form_symbol') }}</label>
          <select v-model="form.symbol" class="form-input">
            <option value="">— select —</option>
            <option v-for="c in watchlist" :key="c.symbol" :value="c.symbol">
              {{ c.symbol }} — {{ c.name }}
            </option>
          </select>
        </div>

        <div class="form-row">
          <label>{{ t('journal.form_mode') }}</label>
          <div class="mode-toggle">
            <button :class="['mode-btn', { active: form.mode === 'paper' }]" @click="form.mode = 'paper'">
              {{ t('journal.paper') }}
            </button>
            <button :class="['mode-btn', { active: form.mode === 'live' }]" @click="form.mode = 'live'">
              {{ t('journal.live') }}
            </button>
          </div>
        </div>

        <div class="form-row">
          <label>{{ t('journal.form_entry') }}</label>
          <input v-model.number="form.entry_price" type="number" step="any"
            class="form-input" :placeholder="livePriceHint" />
        </div>

        <div class="form-row">
          <label>{{ t('journal.form_size') }}</label>
          <input v-model.number="form.size_usd" type="number" step="any"
            class="form-input" :placeholder="t('journal.form_size_ph')" />
        </div>

        <!-- Analysis suggestions banner -->
        <div v-if="hasSuggestions" :class="['suggest-banner', hasAnalysis ? 'suggest-analysis' : 'suggest-default']">
          <div class="suggest-info">
            <template v-if="canSuggest">
              <span v-if="suggestedSL">SL: {{ formatPrice(suggestedSL) }}</span>
              <span v-if="suggestedTarget">TP: {{ formatPrice(suggestedTarget) }}</span>
              <span v-if="hasAnalysis && coinDetail?.rating" class="suggest-rating">{{ coinDetail.rating }}</span>
              <span v-else class="suggest-default-label">{{ t('journal.suggest_default_pct') }}</span>
            </template>
            <span v-else class="suggest-default-label">{{ t('journal.suggest_enter_price') }}</span>
          </div>
          <button v-if="canSuggest" type="button" class="suggest-btn" @click="applySuggestions">
            {{ hasAnalysis ? t('journal.suggest_analysis') : t('journal.suggest_fill') }}
          </button>
        </div>

        <div class="form-row">
          <label>{{ t('journal.form_sl') }} <span class="opt">{{ t('journal.optional') }}</span></label>
          <input v-model.number="form.stop_loss" type="number" step="any" class="form-input"
            :placeholder="suggestedSL ? `Suggested: ${formatPrice(suggestedSL)}` : '—'" />
        </div>

        <div class="form-row">
          <label>{{ t('journal.form_target') }} <span class="opt">{{ t('journal.optional') }}</span></label>
          <input v-model.number="form.target" type="number" step="any" class="form-input"
            :placeholder="suggestedTarget ? `Suggested: ${formatPrice(suggestedTarget)}` : '—'" />
        </div>

        <div class="form-row">
          <label>{{ t('journal.trailing_lbl') }} <span class="opt">{{ t('journal.optional') }}</span></label>
          <input v-model.number="form.trailing_stop_pct" type="number" step="0.5" min="0.5" class="form-input"
            :placeholder="t('journal.trailing_ph')" />
          <span class="field-hint">{{ t('journal.trailing_hint') }}</span>
        </div>

        <div class="form-row">
          <label>{{ t('journal.form_notes') }} <span class="opt">{{ t('journal.optional') }}</span></label>
          <textarea v-model="form.notes" class="form-input form-textarea" rows="2" placeholder="…"></textarea>
        </div>

        <div v-if="formError" class="form-error">{{ formError }}</div>
        <button class="submit-btn" :disabled="submitting" @click="submitTrade">
          {{ submitting ? t('journal.saving') : t('journal.submit') }}
        </button>
      </div>

      <!-- ── Open Positions ──────────────────────────────────────────────── -->
      <div class="section-title">{{ t('journal.open_section') }} ({{ openTrades.length }})</div>

      <div v-if="!openTrades.length" class="empty">{{ t('journal.no_open') }}</div>

      <div v-for="trade in openTrades" :key="trade.id" class="trade-card open-card">
        <div class="tc-top" @click="toggleExpand(trade.id)" style="cursor:pointer">
          <div class="tc-left">
            <span class="tc-symbol">{{ trade.symbol }}</span>
            <span class="tc-badge" :class="trade.mode === 'paper' ? 'badge-paper' : 'badge-live'">
              {{ t(`journal.${trade.mode}_badge`) }}
            </span>
            <span class="expand-toggle">{{ expanded.has(trade.id) ? '▼' : '▶' }}</span>
          </div>
          <div class="tc-right">
            <span v-if="livePnl(trade) != null" class="tc-pnl" :class="livePnl(trade) >= 0 ? 'pos' : 'neg'">
              {{ livePnl(trade) >= 0 ? '+' : '' }}${{ livePnl(trade).toFixed(2) }}
              <span class="tc-pnl-pct">({{ livePnlPct(trade) >= 0 ? '+' : '' }}{{ livePnlPct(trade).toFixed(2) }}%)</span>
            </span>
          </div>
        </div>
        <div class="tc-details">
          <span class="tc-detail"><span class="tc-dlabel">{{ t('journal.entry_lbl') }}</span> {{ formatPrice(trade.entry_price) }}</span>
          <span class="tc-detail"><span class="tc-dlabel">{{ t('journal.size_lbl') }}</span> ${{ trade.size_usd }}</span>
          <span v-if="trade.stop_loss" class="tc-detail neg"><span class="tc-dlabel">SL</span> {{ formatPrice(trade.stop_loss) }}</span>
          <span v-if="trade.target" class="tc-detail pos"><span class="tc-dlabel">TP</span> {{ formatPrice(trade.target) }}</span>
          <span v-if="trade.trailing_stop_pct" class="tc-detail trailing-active">
            <span class="tc-dlabel">{{ t('journal.trail_btn') }}</span> {{ trade.trailing_stop_pct }}%
            <template v-if="trade.trailing_stop_peak">
              · {{ t('journal.trail_peak') }} {{ formatPrice(trade.trailing_stop_peak) }}
              · {{ t('journal.trail_stop_lbl') }} {{ formatPrice(trade.trailing_stop_peak * (1 - trade.trailing_stop_pct / 100)) }}
            </template>
          </span>
          <span class="tc-detail muted"><span class="tc-dlabel">{{ t('journal.duration') }}</span> {{ elapsed(trade.entry_time) }}</span>
        </div>

        <!-- ── Expanded risk panel ─────────────────────────────────────── -->
        <div v-if="expanded.has(trade.id)" class="risk-panel">
          <div class="risk-title">{{ t('journal.risk_title') }}</div>
          <div class="risk-grid">
            <template v-if="livePrice(trade.symbol)">
              <span class="rk-label">{{ t('journal.risk_live_price') }}</span>
              <span class="rk-val">{{ formatPrice(livePrice(trade.symbol)) }}</span>
              <span class="rk-sub"></span>
            </template>
            <span class="rk-label">{{ t('journal.entry_lbl') }}</span>
            <span class="rk-val">{{ formatPrice(trade.entry_price) }}</span>
            <span class="rk-sub muted">${{ trade.size_usd }} {{ t('journal.risk_deployed') }}</span>
            <template v-if="trade.stop_loss">
              <span class="rk-label neg">{{ t('journal.risk_sl') }}</span>
              <span class="rk-val neg">{{ formatPrice(trade.stop_loss) }}</span>
              <span class="rk-sub neg">
                {{ slDistPct(trade) }}% {{ t('journal.risk_from') }} {{ livePrice(trade.symbol) ? t('journal.risk_from_live') : t('journal.risk_from_entry') }}
                · {{ t('journal.risk_maxloss') }} <b>${{ slRiskUsd(trade) }}</b>
              </span>
            </template>
            <template v-if="trade.target">
              <span class="rk-label pos">{{ t('journal.risk_tp') }}</span>
              <span class="rk-val pos">{{ formatPrice(trade.target) }}</span>
              <span class="rk-sub pos">
                +{{ tpDistPct(trade) }}% {{ t('journal.risk_away') }} · {{ t('journal.risk_gain') }} <b>${{ tpGainUsd(trade) }}</b>
              </span>
            </template>
            <template v-if="trade.stop_loss && trade.target">
              <span class="rk-label muted">{{ t('journal.risk_rr') }}</span>
              <span class="rk-val" :class="rrRatio(trade) >= 1.5 ? 'pos' : rrRatio(trade) < 1 ? 'neg' : ''">
                1 : {{ rrRatio(trade).toFixed(1) }}
              </span>
              <span class="rk-sub muted">{{ rrRatio(trade) >= 2 ? t('journal.risk_good') : rrRatio(trade) >= 1.5 ? t('journal.risk_acceptable') : t('journal.risk_tight') }}</span>
            </template>
            <template v-if="trade.trailing_stop_pct">
              <span class="rk-label" style="color:#7ec8e3">{{ t('journal.risk_trail_lbl') }}</span>
              <span class="rk-val" style="color:#7ec8e3">{{ formatPrice(trailLevel(trade)) }}</span>
              <span class="rk-sub" style="color:#7ec8e3">
                {{ trade.trailing_stop_pct }}% {{ t('journal.risk_trail_below') }} {{ formatPrice(trade.trailing_stop_peak || trade.entry_price) }}
                <template v-if="livePrice(trade.symbol) && trailLevel(trade)">
                  · {{ trailDistPct(trade) }}% {{ t('journal.risk_cushion') }}
                </template>
              </span>
            </template>
          </div>
        </div>

        <div v-if="trade.notes" class="tc-notes">{{ trade.notes }}</div>

        <!-- Inline close form -->
        <div v-if="closing === trade.id" class="close-form">
          <input v-model.number="closePrice" type="number" step="any"
            class="form-input" :placeholder="livePrice(trade.symbol) ? String(livePrice(trade.symbol)) : 'Exit price'" />
          <div class="close-actions">
            <button class="confirm-btn" @click="confirmClose(trade.id)">{{ t('journal.confirm') }}</button>
            <button class="cancel-sm-btn" @click="closing = null">{{ t('journal.cancel') }}</button>
          </div>
        </div>

        <!-- Inline set-trailing form -->
        <div v-else-if="settingTrailing === trade.id" class="close-form">
          <input v-model.number="trailingPct" type="number" step="0.5" min="0.5"
            class="form-input" :placeholder="t('journal.trailing_ph')" />
          <div class="close-actions">
            <button class="confirm-btn trailing-confirm-btn" @click="confirmTrailing(trade.id)">{{ t('journal.set_trailing') }}</button>
            <button class="cancel-sm-btn" @click="settingTrailing = null">{{ t('journal.cancel') }}</button>
          </div>
        </div>

        <div v-else class="tc-actions">
          <button class="close-trade-btn" @click="startClose(trade)">{{ t('journal.close_btn') }}</button>
          <button class="trail-btn" @click="startTrailing(trade)" :title="trade.trailing_stop_pct ? t('journal.trail_tooltip', { pct: trade.trailing_stop_pct }) : t('journal.set_trailing')">
            {{ trade.trailing_stop_pct ? `🔄 ${trade.trailing_stop_pct}%` : t('journal.trail_btn') }}
          </button>
          <button class="del-btn" @click="deleteTrade(trade.id)">{{ t('journal.delete_btn') }}</button>
        </div>
      </div>

      <!-- ── Trade History ─────────────────────────────────────────────── -->
      <div class="section-title-row">
        <span class="section-title">{{ t('journal.hist_section') }} ({{ closedTrades.length }})</span>
        <button v-if="closedTrades.length" class="expand-all-btn" @click="toggleAllClosed">
          {{ allClosedExpanded ? t('journal.collapse_all') : t('journal.expand_all') }}
        </button>
      </div>

      <div v-if="!closedTrades.length" class="empty">{{ t('journal.no_closed') }}</div>

      <div v-for="trade in closedTrades" :key="trade.id" class="trade-card closed-card">
        <!-- Always-visible collapsed summary row — click anywhere to expand -->
        <div class="tc-top closed-header" @click="toggleExpand(trade.id)">
          <div class="closed-col-left">
            <span class="tc-symbol">{{ trade.symbol }}</span>
            <div class="closed-badges-row">
              <span class="tc-badge" :class="trade.mode === 'paper' ? 'badge-paper' : 'badge-live'">
                {{ t(`journal.${trade.mode}_badge`) }}
              </span>
              <span v-if="trade.outcome" class="outcome-badge" :class="`outcome-${trade.outcome}`">
                {{ t(`journal.outcome_${trade.outcome === 'breakeven' ? 'be' : trade.outcome}`) }}
              </span>
              <span class="expand-toggle">{{ expanded.has(trade.id) ? '▼' : '▶' }}</span>
              <span class="price-route">
                {{ formatPrice(trade.entry_price) }} → {{ formatPrice(trade.exit_price) }}
              </span>
            </div>
          </div>
          <div class="tc-right">
            <template v-if="trade.pnl_usd != null">
              <span class="closed-pnl-usd" :class="trade.pnl_usd >= 0 ? 'pos' : 'neg'">
                {{ trade.pnl_usd >= 0 ? '+' : '' }}${{ Math.abs(trade.pnl_usd).toFixed(2) }}
              </span>
              <span class="closed-pnl-pct" :class="(trade.pnl_pct ?? 0) >= 0 ? 'pos-muted' : 'neg-muted'">
                {{ (trade.pnl_pct ?? 0) >= 0 ? '+' : '' }}{{ (trade.pnl_pct ?? 0).toFixed(2) }}%
              </span>
            </template>
            <span v-else class="muted">—</span>
          </div>
        </div>

        <!-- Expanded details -->
        <template v-if="expanded.has(trade.id)">
          <div class="tc-details">
            <span class="tc-detail"><span class="tc-dlabel">{{ t('journal.entry_lbl') }}</span> {{ formatPrice(trade.entry_price) }}</span>
            <span class="tc-detail"><span class="tc-dlabel">→</span> {{ formatPrice(trade.exit_price) }}</span>
            <span class="tc-detail"><span class="tc-dlabel">{{ t('journal.size_lbl') }}</span> ${{ trade.size_usd }}</span>
            <span class="tc-detail muted">{{ shortDate(trade.entry_time) }}</span>
          </div>
          <div v-if="trade.notes" class="tc-notes">{{ closedNotes(trade.notes) }}</div>
          <div class="tc-actions">
            <button class="del-btn" @click.stop="deleteTrade(trade.id)">{{ t('journal.delete_btn') }}</button>
          </div>
        </template>
      </div>

    </template>

    <!-- ══════════════════════ RANKINGS TAB ══════════════════════════════════ -->
    <template v-else-if="journalTab === 'rankings'">

      <div class="rankings-header">
        <span class="rankings-hint">{{ t('journal.rankings_hint') }}</span>
        <button class="refresh-btn" @click="loadLeaderboard">↻</button>
      </div>

      <div v-if="!leaderboard.length" class="empty">{{ t('journal.rankings_empty') }}</div>

      <div v-for="(row, i) in leaderboard" :key="row.symbol" class="rank-card"
           :class="{ 'rank-top': i < 3, 'rank-pos': row.net_usd > 0, 'rank-neg': row.net_usd < 0 }">
        <!-- Medal + symbol -->
        <div class="rank-left">
          <span class="rank-medal">{{ i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}` }}</span>
          <div class="rank-coin">
            <span class="rank-symbol">{{ row.symbol }}</span>
            <span class="rank-trades">{{ row.closed_trades }} {{ row.closed_trades !== 1 ? t('journal.rank_trades') : t('journal.rank_trade') }}
              <template v-if="row.open_trades"> · {{ row.open_trades }} {{ t('journal.rank_open_suffix') }}</template>
            </span>
          </div>
        </div>
        <!-- P&L numbers -->
        <div class="rank-right">
          <span class="rank-net" :class="row.net_usd >= 0 ? 'pos' : 'neg'">
            {{ row.net_usd >= 0 ? '+' : '' }}${{ row.net_usd.toFixed(2) }}
          </span>
          <div class="rank-breakdown">
            <span v-if="row.closed_trades" class="rank-detail">
              {{ t('journal.rank_closed_lbl') }} <span :class="row.realised_usd >= 0 ? 'pos' : 'neg'">{{ row.realised_usd >= 0 ? '+' : '' }}${{ row.realised_usd.toFixed(2) }}</span>
            </span>
            <span v-if="row.open_trades" class="rank-detail">
              {{ t('journal.rank_live_lbl') }} <span :class="row.unrealised_usd >= 0 ? 'pos' : 'neg'">{{ row.unrealised_usd >= 0 ? '+' : '' }}${{ row.unrealised_usd.toFixed(2) }}</span>
            </span>
            <span v-if="row.win_rate != null" class="rank-detail muted">
              {{ row.win_rate }}{{ t('journal.rank_win_pct') }}
            </span>
          </div>
        </div>
      </div>

    </template>

  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'

const { t } = useI18n()
const API   = import.meta.env.VITE_API_BASE || ''

// ── State ─────────────────────────────────────────────────────────────────────
const trades      = ref([])
const summary     = ref({})
const watchlist   = ref([])
const prices      = ref({})
const leaderboard = ref([])
const journalTab  = ref('trades')
const showForm    = ref(false)
const submitting  = ref(false)
const formError   = ref('')
const refreshing      = ref(false)
const closing         = ref(null)
const closePrice      = ref(null)
const settingTrailing = ref(null)
const trailingPct     = ref(null)
const coinDetail      = ref(null)
const expanded        = ref(new Set())
let   priceTimer      = null

const form = reactive({
  symbol:            '',
  mode:              'paper',
  entry_price:       null,
  size_usd:          null,
  stop_loss:         null,
  target:            null,
  trailing_stop_pct: null,
  notes:             '',
})

// ── Computed ──────────────────────────────────────────────────────────────────
const openTrades   = computed(() => trades.value.filter(t => t.status === 'open'))
const closedTrades = computed(() => trades.value.filter(t => t.status === 'closed'))

const allClosedExpanded = computed(() =>
  closedTrades.value.length > 0 && closedTrades.value.every(t => expanded.value.has(t.id))
)

const unrealizedPnlUsd = computed(() =>
  openTrades.value.reduce((sum, tr) => sum + (livePnl(tr) ?? 0), 0)
)

const totalPnlUsd = computed(() =>
  parseFloat(((summary.value.total_pnl_usd ?? 0) + unrealizedPnlUsd.value).toFixed(2))
)

const avgPnlUsd = computed(() => {
  const n = summary.value.closed_count
  if (!n) return null
  return parseFloat((summary.value.total_pnl_usd / n).toFixed(2))
})

const livePriceHint = computed(() => {
  const p = prices.value[form.symbol]
  return p ? `Live: ${formatPrice(p.price)}` : 'e.g. 1.35'
})

const refPrice = computed(() => {
  const live = prices.value[form.symbol]?.price
  return form.entry_price || live || null
})

const hasAnalysis = computed(() => !!coinDetail.value)

const suggestedSL = computed(() => {
  if (coinDetail.value?.supports?.length) return coinDetail.value.supports[0].price
  const p = refPrice.value
  return p ? parseFloat((p * 0.95).toFixed(6)) : null
})

const suggestedTarget = computed(() => {
  if (coinDetail.value?.resistances?.length) return coinDetail.value.resistances[0].price
  const p = refPrice.value
  return p ? parseFloat((p * 1.10).toFixed(6)) : null
})

const suggestedNotes = computed(() => {
  const d = coinDetail.value
  if (d) {
    const parts = []
    const bd = d.breakdown || {}
    if (bd.rsi?.[1])       parts.push(bd.rsi[1])
    if (bd.ema_200?.[1])   parts.push(bd.ema_200[1])
    if (bd.volume?.[1])    parts.push(bd.volume[1])
    if (bd.narrative?.[1]) parts.push(bd.narrative[1])
    if (d.rating)          parts.push(`Score: ${d.score}/20 (${d.rating.replace(/[^\w\s]/g, '').trim()})`)
    return parts.join('. ')
  }
  return refPrice.value ? 'Paper trade. Default risk levels: SL -5%, TP +10% (2:1 R/R).' : ''
})

const hasSuggestions = computed(() => !!form.symbol)
const canSuggest    = computed(() => refPrice.value != null)

// ── Data fetching ─────────────────────────────────────────────────────────────
async function refreshAll() {
  refreshing.value = true
  try {
    await Promise.all([loadAll(), fetchPrices()])
  } finally {
    refreshing.value = false
  }
}

async function loadAll() {
  const [tradesRes, summaryRes, wlRes] = await Promise.all([
    axios.get(`${API}/api/journal/trades`),
    axios.get(`${API}/api/journal/summary`),
    axios.get(`${API}/api/spot/watchlist`),
  ])
  trades.value    = tradesRes.data.trades  || []
  summary.value   = summaryRes.data        || {}
  watchlist.value = wlRes.data             || []
}

async function fetchPrices() {
  try {
    const { data } = await axios.get(`${API}/api/spot/prices`)
    prices.value = data.prices || {}
  } catch {}
}

async function refreshSummary() {
  const { data } = await axios.get(`${API}/api/journal/summary`)
  summary.value = data
}

async function loadLeaderboard() {
  try {
    const { data } = await axios.get(`${API}/api/spot/bot/leaderboard`)
    leaderboard.value = data.rows || []
  } catch {}
}

async function fetchCoinDetail(symbol) {
  if (!symbol) { coinDetail.value = null; return }
  try {
    const { data } = await axios.get(`${API}/api/spot/coin/${symbol}`)
    coinDetail.value = data
  } catch { coinDetail.value = null }
}

watch(() => form.symbol, fetchCoinDetail)

function applySuggestions() {
  if (suggestedSL.value != null)     form.stop_loss = parseFloat(suggestedSL.value.toFixed(4))
  if (suggestedTarget.value != null) form.target    = parseFloat(suggestedTarget.value.toFixed(4))
  if (suggestedNotes.value)          form.notes     = suggestedNotes.value
}

async function switchToRankings() {
  journalTab.value = 'rankings'
  await loadLeaderboard()
}

// ── Trade actions ─────────────────────────────────────────────────────────────
function toggleForm() {
  showForm.value = !showForm.value
  formError.value = ''
  if (!showForm.value) resetForm()
}

function resetForm() {
  Object.assign(form, { symbol: '', mode: 'paper', entry_price: null, size_usd: null, stop_loss: null, target: null, trailing_stop_pct: null, notes: '' })
  coinDetail.value = null
}

async function submitTrade() {
  if (!form.symbol)      return (formError.value = t('journal.err_select_coin'))
  if (!form.entry_price) return (formError.value = t('journal.err_entry_price'))
  if (!form.size_usd)    return (formError.value = t('journal.err_size'))
  formError.value = ''
  submitting.value = true
  try {
    const { data } = await axios.post(`${API}/api/journal/trades`, {
      symbol:            form.symbol,
      mode:              form.mode,
      direction:         'long',
      entry_price:       form.entry_price,
      size_usd:          form.size_usd,
      stop_loss:         form.stop_loss        || null,
      target:            form.target           || null,
      trailing_stop_pct: form.trailing_stop_pct || null,
      notes:             form.notes            || null,
      hotness_at_entry:  null,
    })
    trades.value.unshift(data)
    showForm.value = false
    resetForm()
    await refreshSummary()
  } catch (e) {
    formError.value = e.response?.data?.detail || t('journal.err_save')
  } finally {
    submitting.value = false
  }
}

function startClose(trade) {
  closing.value   = trade.id
  closePrice.value = livePrice(trade.symbol) || trade.entry_price
}

async function confirmClose(id) {
  if (!closePrice.value) return
  try {
    const { data } = await axios.patch(`${API}/api/journal/trades/${id}/close`, {
      exit_price: closePrice.value,
    })
    const idx = trades.value.findIndex(t => t.id === id)
    if (idx !== -1) trades.value[idx] = data
    closing.value   = null
    closePrice.value = null
    await refreshSummary()
  } catch (e) {
    console.error('Close failed', e)
  }
}

function startTrailing(trade) {
  settingTrailing.value = trade.id
  trailingPct.value     = trade.trailing_stop_pct || null
}

async function confirmTrailing(id) {
  if (!trailingPct.value || trailingPct.value <= 0) return
  try {
    const { data } = await axios.patch(`${API}/api/journal/trades/${id}/trailing-stop`, {
      pct: trailingPct.value,
    })
    const idx = trades.value.findIndex(t => t.id === id)
    if (idx !== -1) trades.value[idx] = data
    settingTrailing.value = null
    trailingPct.value     = null
  } catch (e) {
    console.error('Set trailing stop failed', e)
  }
}

async function deleteTrade(id) {
  await axios.delete(`${API}/api/journal/trades/${id}`)
  trades.value = trades.value.filter(t => t.id !== id)
  await refreshSummary()
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function livePrice(symbol) {
  return prices.value[symbol]?.price || null
}

function livePnl(trade) {
  const p = livePrice(trade.symbol)
  if (!p || !trade.entry_price) return null
  return parseFloat(((p - trade.entry_price) / trade.entry_price * trade.size_usd).toFixed(2))
}

function livePnlPct(trade) {
  const p = livePrice(trade.symbol)
  if (!p || !trade.entry_price) return 0
  return parseFloat(((p - trade.entry_price) / trade.entry_price * 100).toFixed(2))
}

function formatPrice(p) {
  if (!p) return '—'
  if (p >= 10000) return '$' + p.toLocaleString('en', { maximumFractionDigits: 0 })
  if (p >= 1000)  return '$' + p.toFixed(1)
  if (p >= 100)   return '$' + p.toFixed(2)
  if (p >= 1)     return '$' + p.toFixed(3)
  return '$' + p.toFixed(4)
}

function elapsed(isoStr) {
  if (!isoStr) return ''
  const diff = Date.now() - new Date(isoStr + 'Z').getTime()
  const h = Math.floor(diff / 3_600_000)
  const m = Math.floor((diff % 3_600_000) / 60_000)
  if (h >= 24) return `${Math.floor(h / 24)}d`
  if (h)  return `${h}h ${m}m`
  return `${m}m`
}

function shortDate(isoStr) {
  if (!isoStr) return ''
  return new Date(isoStr + 'Z').toLocaleDateString('en', { month: 'short', day: 'numeric' })
}

function toggleExpand(id) {
  const s = new Set(expanded.value)
  s.has(id) ? s.delete(id) : s.add(id)
  expanded.value = s
}

function toggleAllClosed() {
  const s = new Set(expanded.value)
  if (allClosedExpanded.value) {
    closedTrades.value.forEach(t => s.delete(t.id))
  } else {
    closedTrades.value.forEach(t => s.add(t.id))
  }
  expanded.value = s
}

function closedNotes(notes) {
  if (!notes) return ''
  // Strip the verbose "[BOT] Score …" prefix to keep card clean
  return notes.replace(/^\[BOT\][^|]+\|?\s*/, '').trim()
}

// ── Risk measure helpers ──────────────────────────────────────────────────────
function _ref(trade) {
  return livePrice(trade.symbol) || trade.entry_price
}

function slDistPct(trade) {
  const ref = _ref(trade)
  if (!ref || !trade.stop_loss) return '0.00'
  return ((trade.stop_loss - ref) / ref * 100).toFixed(2)
}

function slRiskUsd(trade) {
  if (!trade.entry_price || !trade.stop_loss) return '0.00'
  const risk = (trade.entry_price - trade.stop_loss) / trade.entry_price * trade.size_usd
  return risk.toFixed(2)
}

function tpDistPct(trade) {
  const ref = _ref(trade)
  if (!ref || !trade.target) return '0.00'
  return ((trade.target - ref) / ref * 100).toFixed(2)
}

function tpGainUsd(trade) {
  if (!trade.entry_price || !trade.target) return '0.00'
  const gain = (trade.target - trade.entry_price) / trade.entry_price * trade.size_usd
  return gain.toFixed(2)
}

function rrRatio(trade) {
  if (!trade.entry_price || !trade.stop_loss || !trade.target) return 0
  const risk   = trade.entry_price - trade.stop_loss
  const reward = trade.target - trade.entry_price
  if (!risk || risk <= 0) return 0
  return reward / risk
}

function trailLevel(trade) {
  const peak = trade.trailing_stop_peak || trade.entry_price
  return peak * (1 - trade.trailing_stop_pct / 100)
}

function trailDistPct(trade) {
  const cur = livePrice(trade.symbol)
  const lvl = trailLevel(trade)
  if (!cur || !lvl) return '—'
  return ((cur - lvl) / cur * 100).toFixed(2)
}

// ── Lifecycle ─────────────────────────────────────────────────────────────────
onMounted(async () => {
  await loadAll()
  await fetchPrices()
  priceTimer = setInterval(fetchPrices, 15_000)
})
onUnmounted(() => clearInterval(priceTimer))
</script>

<style scoped>
.journal-card { display: flex; flex-direction: column; gap: 0.75rem; }

/* ── Summary grid ───────────────────────────────────────────────────────────── */
.jsum-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.45rem;
}
.jsum-cell {
  display: flex; flex-direction: column; gap: 0.18rem;
  background: #151821;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  padding: 0.6rem 0.75rem;
}
.jsum-cell-sm { padding: 0.45rem 0.75rem; }
.jsum-label {
  font-size: var(--font-size-xs); font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase; letter-spacing: 0.07em;
  margin-bottom: 0.1rem;
}
.jsum-val {
  font-size: 1.45rem; font-weight: 800;
  color: var(--color-text); line-height: 1.15;
  font-variant-numeric: tabular-nums;
}
.jsum-cell-sm .jsum-val { font-size: 1.25rem; }
.jsum-val.neutral { color: var(--color-text-secondary-bright); }
.jsum-sub { font-size: var(--font-size-sm); font-weight: 500; color: var(--color-text-secondary); }
.jsum-sub.muted { color: var(--color-text-muted); }

/* counts row */
.jsum-counts {
  display: flex; align-items: center; gap: 0.4rem;
  flex-wrap: wrap;
}
.jsum-count-item { display: flex; align-items: center; gap: 0.25rem; }
.jsum-count-dot  { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.dot-open   { background: var(--color-accent); }
.dot-closed { background: var(--color-text-secondary); }
.jsum-count-n   { font-size: 1.2rem; font-weight: 800; color: var(--color-text); font-variant-numeric: tabular-nums; }
.jsum-count-lbl { font-size: var(--font-size-sm); color: var(--color-text-muted); }
.jsum-count-sep { color: var(--color-border); font-size: var(--font-size-base); }

/* best / worst */
.jsum-bw     { display: flex; flex-direction: column; gap: 0.25rem; margin-top: 0.1rem; }
.jsum-bw-row { display: flex; align-items: baseline; gap: 0.3rem; }
.jsum-bw-arrow { font-size: var(--font-size-sm); font-weight: 700; }
.jsum-bw-val   { font-size: var(--font-size-base); font-weight: 700; font-variant-numeric: tabular-nums; }

/* ── Internal sub-tabs ──────────────────────────────────────────────────────── */
.journal-tabs {
  display: flex;
  gap: 0.25rem;
  border-bottom: 2px solid var(--color-border);
  padding-bottom: 0;
  margin-bottom: 0.25rem;
}
.jtab-btn {
  padding: 0.45rem 1rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm-plus);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  min-height: 38px;
}
.jtab-btn.active { color: var(--color-accent-strong); border-bottom-color: var(--color-accent); }
.jtab-btn:active { color: var(--color-text); }

/* ── Header actions ─────────────────────────────────────────────────────────── */
.header-actions { display: flex; align-items: center; gap: 0.5rem; }

.refresh-icon-btn {
  background: var(--color-border);
  border: 1px solid var(--color-text-muted);
  color: var(--color-text-secondary-bright);
  font-size: 1.1rem;
  width: 38px; height: 38px;
  border-radius: 0.4rem;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: color 0.15s;
}
.refresh-icon-btn:hover:not(:disabled) { color: var(--color-text); border-color: var(--color-text-secondary); }
.refresh-icon-btn:disabled { opacity: 0.5; cursor: default; }
.refresh-icon-btn.spinning { animation: spin 0.7s linear infinite; }

@keyframes spin { to { transform: rotate(360deg); } }

/* ── Log trade button ───────────────────────────────────────────────────────── */
.log-btn {
  align-self: flex-start;
  background: var(--color-accent-muted);
  border: 1px solid var(--color-accent);
  color: var(--color-accent-strong);
  padding: 0.45rem 0.9rem;
  border-radius: 0.4rem;
  cursor: pointer;
  font-size: var(--font-size-sm-plus);
  font-weight: 600;
  min-height: 40px;
}
.log-btn:active { background: #1a3a5c; }

/* ── Form ───────────────────────────────────────────────────────────────────── */
.trade-form {
  background: #151821;
  border: 1px solid var(--color-border);
  border-radius: 0.5rem;
  padding: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}
.form-row { display: flex; flex-direction: column; gap: 0.25rem; }
.form-row label { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; }
.opt { font-size: var(--font-size-sm-plus); color: var(--color-text-muted); text-transform: lowercase; }
.form-input {
  background: var(--color-border);
  border: 1px solid var(--color-text-muted);
  color: var(--color-text);
  padding: 0.55rem 0.75rem;
  border-radius: 0.4rem;
  font-size: var(--font-size-base);
  width: 100%;
  min-height: 44px;
  box-sizing: border-box;
}
.form-textarea { min-height: 64px; resize: vertical; }
.form-error { font-size: var(--font-size-sm-plus); color: var(--color-danger); }
.mode-toggle { display: flex; gap: 0.5rem; }
.mode-btn {
  flex: 1; padding: 0.4rem; border-radius: 0.4rem;
  border: 1px solid var(--color-text-muted); background: var(--color-border);
  color: var(--color-text-secondary-bright); cursor: pointer; font-size: var(--font-size-sm-plus); min-height: 40px;
}
.mode-btn.active { background: var(--color-accent-muted); color: var(--color-accent-strong); border-color: var(--color-accent); }
.submit-btn {
  background: var(--color-success-emphasis); border: 1px solid var(--color-success-medium);
  color: var(--color-success-tint2); padding: 0.6rem;
  border-radius: 0.4rem; cursor: pointer;
  font-size: var(--font-size-sm-plus); font-weight: 600; min-height: 44px;
}
.submit-btn:disabled { opacity: 0.5; }

/* ── Section title ──────────────────────────────────────────────────────────── */
.section-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.section-title {
  font-size: var(--font-size-sm-plus); color: var(--color-text-secondary);
  text-transform: uppercase; letter-spacing: 0.06em;
}
.expand-all-btn {
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: var(--font-size-sm-plus);
  cursor: pointer;
  padding: 0.1rem 0.25rem;
  letter-spacing: 0.03em;
}
.expand-all-btn:hover { color: var(--color-text-secondary); }

/* ── Closed card header ─────────────────────────────────────────────────────── */
.closed-header { cursor: pointer; }

.closed-col-left {
  display: flex;
  flex-direction: column;
  gap: 0.22rem;
  flex: 1;
  min-width: 0;
}
.closed-badges-row {
  display: flex;
  align-items: center;
  gap: 0.3rem;
  flex-wrap: nowrap;
}
.price-route {
  font-size: var(--font-size-sm-plus);
  color: var(--color-text-secondary);
  white-space: nowrap;
  margin-inline-start: 0.1rem;
}

/* ── Trade cards ────────────────────────────────────────────────────────────── */
.trade-card {
  border: 1px solid var(--color-border);
  border-radius: 0.55rem;
  padding: 0.7rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}
.open-card   { border-inline-start: 3px solid var(--color-accent); }
.closed-card { border-inline-start: 3px solid var(--color-text-muted); }

.tc-top { display: flex; justify-content: space-between; align-items: flex-start; }
.tc-left  { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
.tc-right { display: flex; flex-direction: column; align-items: flex-end; }
.tc-symbol { font-size: 1.1rem; font-weight: 800; color: var(--color-text); }

.tc-badge {
  font-size: var(--font-size-sm-plus); font-weight: 700; letter-spacing: 0.05em;
  padding: 0.1rem 0.4rem; border-radius: 999px;
}
.badge-paper { background: var(--color-warning-bg); color: var(--color-warning); border: 1px solid var(--color-warning-intense-bg); }
.badge-live  { background: var(--color-success-bg); color: var(--color-success-strong); border: 1px solid var(--color-success-emphasis); }

.outcome-badge {
  font-size: var(--font-size-sm-plus); font-weight: 700;
  padding: 0.1rem 0.4rem; border-radius: 999px;
}
.outcome-win       { background: var(--color-success-bg); color: var(--color-success-strong); }
.outcome-loss      { background: var(--color-danger-bg); color: var(--color-danger); }
.outcome-breakeven { background: var(--color-border); color: var(--color-text-secondary-bright); }

/* Open position P&L */
.tc-pnl { font-size: var(--font-size-base); font-weight: 700; }
.tc-pnl-pct { font-size: var(--font-size-sm-plus); font-weight: 400; }

/* Closed trade P&L — USD is the hero */
.closed-pnl-usd {
  font-size: 1.15rem;
  font-weight: 800;
  letter-spacing: -0.01em;
}
.closed-pnl-pct {
  font-size: var(--font-size-sm-plus);
  font-weight: 500;
  text-align: end;
}
.pos-muted { color: var(--color-success); }
.neg-muted { color: #e05252; }

.tc-details {
  display: flex; flex-wrap: wrap; gap: 0.4rem 0.75rem;
}
.tc-detail { font-size: var(--font-size-sm-plus); }
.tc-dlabel { color: var(--color-text-muted); font-size: var(--font-size-sm-plus); }
.tc-notes { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); font-style: italic; }

/* Inline close form */
.close-form { display: flex; flex-direction: column; gap: 0.4rem; margin-top: 0.25rem; }
.close-actions { display: flex; gap: 0.5rem; }
.confirm-btn {
  flex: 1; background: var(--color-success-emphasis); border: 1px solid var(--color-success-medium);
  color: var(--color-success-tint2); padding: 0.4rem; border-radius: 0.4rem;
  cursor: pointer; font-size: var(--font-size-sm-plus); min-height: 40px;
}
.cancel-sm-btn {
  flex: 1; background: var(--color-border); border: 1px solid var(--color-text-muted);
  color: var(--color-text-secondary-bright); padding: 0.4rem; border-radius: 0.4rem;
  cursor: pointer; font-size: var(--font-size-sm-plus); min-height: 40px;
}

/* Trade actions */
.tc-actions { display: flex; gap: 0.5rem; margin-top: 0.1rem; }
.close-trade-btn {
  flex: 1; background: var(--color-accent-muted); border: 1px solid var(--color-accent);
  color: var(--color-accent-strong); padding: 0.4rem; border-radius: 0.4rem;
  cursor: pointer; font-size: var(--font-size-sm-plus); min-height: 38px;
}
.del-btn {
  background: var(--color-border); border: 1px solid var(--color-text-muted);
  color: var(--color-text-secondary); padding: 0.4rem 0.65rem; border-radius: 0.4rem;
  cursor: pointer; font-size: var(--font-size-sm-plus); min-height: 38px;
}
.del-btn:active { color: var(--color-danger); border-color: var(--color-danger); }

.trail-btn {
  background: var(--color-surface-tile); border: 1px solid #4a90b8;
  color: var(--color-accent-sky); padding: 0.4rem 0.65rem; border-radius: 0.4rem;
  cursor: pointer; font-size: var(--font-size-sm-plus); min-height: 38px; white-space: nowrap;
}
.trail-btn:active { background: #152333; }
.trailing-confirm-btn { background: var(--color-surface-tile); border-color: #4a90b8; color: var(--color-accent-sky); }
.trailing-active { color: var(--color-accent-sky); }
.field-hint { font-size: var(--font-size-sm-plus); color: var(--color-text-muted); margin-top: 0.1rem; }

/* ── Expand toggle ───────────────────────────────────────────────────────────── */
.expand-toggle { font-size: var(--font-size-sm-plus); color: var(--color-text-muted); margin-inline-start: 0.2rem; }

/* ── Risk panel ──────────────────────────────────────────────────────────────── */
.risk-panel {
  background: #0f1319;
  border: 1px solid var(--color-border);
  border-radius: 0.45rem;
  padding: 0.65rem 0.75rem;
  margin: 0.1rem 0;
}
.risk-title {
  font-size: var(--font-size-sm-plus);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.07em;
  margin-bottom: 0.5rem;
}
.risk-grid {
  display: grid;
  grid-template-columns: 6rem 7rem 1fr;
  gap: 0.3rem 0.5rem;
  align-items: baseline;
}
.rk-label { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }
.rk-val   { font-size: var(--font-size-base); font-weight: 700; }
.rk-sub   { font-size: var(--font-size-sm-plus); }

/* ── Rankings tab ───────────────────────────────────────────────────────────── */
.rankings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.25rem;
}
.rankings-hint {
  font-size: var(--font-size-sm-plus);
  color: var(--color-text-muted);
  font-style: italic;
}

.rank-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border: 1px solid var(--color-border);
  border-radius: 0.55rem;
  padding: 0.65rem 0.75rem;
  gap: 0.5rem;
}
.rank-top { border-color: var(--color-text-muted); background: #141820; }
.rank-pos { border-inline-start: 3px solid var(--color-success-medium); }
.rank-neg { border-inline-start: 3px solid var(--color-danger-vivid); }

.rank-left  { display: flex; align-items: center; gap: 0.55rem; min-width: 0; }
.rank-right { display: flex; flex-direction: column; align-items: flex-end; flex-shrink: 0; }

.rank-medal  { font-size: 1.3rem; flex-shrink: 0; min-width: 1.8rem; text-align: center; }
.rank-coin   { display: flex; flex-direction: column; gap: 0.1rem; }
.rank-symbol { font-size: var(--font-size-base); font-weight: 800; color: var(--color-text); }
.rank-trades { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }

.rank-net {
  font-size: 1.2rem;
  font-weight: 800;
  letter-spacing: -0.01em;
}
.rank-breakdown { display: flex; gap: 0.5rem; flex-wrap: wrap; justify-content: flex-end; margin-top: 0.1rem; }
.rank-detail    { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }

.refresh-btn {
  background: var(--color-border); border: 1px solid var(--color-text-muted);
  color: var(--color-text-secondary-bright); padding: 0.3rem 0.6rem;
  border-radius: 0.4rem; cursor: pointer;
  font-size: var(--font-size-sm-plus); min-height: 32px;
}
.refresh-btn:active { background: var(--color-text-muted); }

/* ── Helpers ────────────────────────────────────────────────────────────────── */
.pos   { color: var(--color-success-strong); }
.neg   { color: var(--color-danger); }
.muted { color: var(--color-text-secondary); }
.empty { font-size: var(--font-size-sm-plus); color: var(--color-text-muted); }

/* ── Analysis suggestions banner ─────────────────────────────────────────── */
.suggest-banner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-radius: 0.4rem;
  padding: 0.45rem 0.7rem;
  gap: 0.5rem;
}
.suggest-analysis {
  background: var(--color-success-bg);
  border: 1px solid var(--color-success-emphasis);
}
.suggest-default {
  background: #1a2130;
  border: 1px solid var(--color-text-muted);
}
.suggest-info {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  font-size: var(--font-size-sm-plus);
  color: var(--color-success-strong);
}
.suggest-default .suggest-info {
  color: var(--color-accent-strong);
}
.suggest-rating {
  color: var(--color-warning);
}
.suggest-default-label {
  color: var(--color-text-secondary);
  font-size: var(--font-size-sm-plus);
}
.suggest-btn {
  background: var(--color-success-emphasis);
  border: 1px solid var(--color-success-medium);
  color: var(--color-success-tint2);
  padding: 0.3rem 0.65rem;
  border-radius: 0.35rem;
  cursor: pointer;
  font-size: var(--font-size-sm-plus);
  font-weight: 600;
  white-space: nowrap;
  min-height: 32px;
}
.suggest-btn:active { background: #1a4731; }
</style>
