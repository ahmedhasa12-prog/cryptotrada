<template>
  <Teleport to="body">
    <div class="detail-overlay" @click.self="$emit('close')">
      <div class="detail-sheet">

        <!-- ── Header ──────────────────────────────────────────────────── -->
        <div class="detail-header">
          <div class="dh-info">
            <span class="dh-symbol">{{ coin.symbol }}</span>
            <span class="dh-name">{{ coin.name }}</span>
          </div>
          <div v-if="live" class="dh-price-block">
            <span class="dh-price">{{ formatPrice(live.price) }}</span>
            <span class="dh-change" :class="live.change_pct >= 0 ? 'pos' : 'neg'">
              {{ live.change_pct >= 0 ? '▲' : '▼' }}{{ Math.abs(live.change_pct).toFixed(2) }}%
            </span>
          </div>
          <button class="close-btn" @click="$emit('close')">✕</button>
        </div>

        <!-- ── Scrollable body ─────────────────────────────────────────── -->
        <div class="detail-body">

          <!-- Interval tabs -->
          <div class="interval-tabs">
            <button
              v-for="iv in INTERVALS" :key="iv"
              class="iv-btn" :class="{ active: interval === iv }"
              @click="changeInterval(iv)"
            >{{ iv }}</button>
          </div>

          <!-- Chart -->
          <div class="chart-wrap">
            <div ref="chartContainer" class="chart-inner"></div>
            <div v-if="chartLoading" class="chart-overlay">{{ t('coin_detail.chart_loading') }}</div>
            <div v-if="!chartLoading && noCandles" class="chart-overlay muted-txt">
              {{ t('coin_detail.no_candles') }}
            </div>
          </div>

          <!-- Score row -->
          <div class="score-row">
            <span class="sr-rating">{{ coin.rating }}</span>
            <div class="sr-bar-wrap">
              <div class="sr-bar" :class="`bar-${coin.rating_key}`"
                :style="{ width: `${(coin.score / 20) * 100}%` }"/>
            </div>
            <span class="sr-score">{{ coin.score }} / 20</span>
          </div>

          <!-- Breakdown -->
          <div class="section-title">{{ t('coin_detail.score_breakdown') }}</div>
          <div class="bd-list">
            <div v-for="(item, key) in coin.breakdown" :key="key" class="bd-row">
              <span class="bd-key">{{ BD_LABELS[key] ? BD_LABELS[key]() : key }}</span>
              <div class="bd-track">
                <div
                  class="bd-fill" :class="item[0] > 0 ? 'pos-fill' : 'neg-fill'"
                  :style="{ width: `${Math.min(Math.abs(item[0]) / (MAX_PTS[key] || 2) * 100, 100)}%` }"
                />
              </div>
              <span class="bd-pts" :class="item[0] > 0 ? 'pos' : item[0] < 0 ? 'neg' : 'muted'">
                {{ item[0] > 0 ? '+' : '' }}{{ item[0] }}
              </span>
              <span class="bd-reason">{{ item[1] }}</span>
            </div>
          </div>

          <!-- Key Indicators -->
          <div class="section-title">{{ t('coin_detail.key_indicators') }}</div>
          <div class="ind-grid">
            <div class="ind-cell" v-if="coin.rsi_1d != null">
              <span class="ic-label">{{ t('coin_detail.ind.rsi') }}</span>
              <span class="ic-val" :class="rsiClass(coin.rsi_1d)">{{ coin.rsi_1d }}</span>
            </div>
            <div class="ind-cell" v-if="coin.vol_ratio != null">
              <span class="ic-label">{{ t('coin_detail.ind.volume') }}</span>
              <span class="ic-val" :class="coin.vol_ratio >= 1.5 ? 'pos' : coin.vol_ratio < 0.7 ? 'neg' : ''">
                {{ coin.vol_ratio }}x avg
              </span>
            </div>
            <div class="ind-cell" v-if="coin.above_ema200 != null">
              <span class="ic-label">{{ t('coin_detail.ind.ema200') }}</span>
              <span class="ic-val" :class="coin.above_ema200 ? 'pos' : 'neg'">
                {{ coin.above_ema200 ? t('coin_detail.above') : t('coin_detail.below') }}
                <template v-if="coin.ema_200_pct != null">
                  ({{ coin.ema_200_pct > 0 ? '+' : '' }}{{ coin.ema_200_pct }}%)
                </template>
              </span>
            </div>
            <div class="ind-cell" v-if="coin.change_24h != null">
              <span class="ic-label">{{ t('coin_detail.ind.change_24h') }}</span>
              <span class="ic-val" :class="coin.change_24h >= 0 ? 'pos' : 'neg'">
                {{ coin.change_24h > 0 ? '+' : '' }}{{ coin.change_24h }}%
              </span>
            </div>
            <div class="ind-cell" v-if="coin.making_higher_lows != null">
              <span class="ic-label">{{ t('coin_detail.ind.structure') }}</span>
              <span class="ic-val" :class="coin.making_higher_lows ? 'pos' : 'muted'">
                {{ coin.making_higher_lows ? t('coin_detail.higher_lows') : t('coin_detail.no_structure') }}
              </span>
            </div>
            <div class="ind-cell" v-if="coin.macd_bullish != null">
              <span class="ic-label">{{ t('coin_detail.ind.macd') }}</span>
              <span class="ic-val" :class="coin.macd_bullish ? 'pos' : 'neg'">
                {{ coin.macd_bullish ? t('coin_detail.bullish') : t('coin_detail.bearish') }}
              </span>
            </div>
            <div class="ind-cell" v-if="coin.bb_position != null">
              <span class="ic-label">{{ t('coin_detail.ind.bollinger') }}</span>
              <span class="ic-val" :class="coin.bb_position < 0.3 ? 'pos' : coin.bb_position > 0.7 ? 'neg' : ''">
                {{ bbLabel(coin.bb_position) }}
              </span>
            </div>
            <div class="ind-cell" v-if="coin.volatility_20d != null">
              <span class="ic-label">{{ t('coin_detail.ind.volatility') }}</span>
              <span class="ic-val">{{ coin.volatility_20d }}%</span>
            </div>
          </div>

          <!-- Multi-Timeframe -->
          <template v-if="coin.timeframes && Object.keys(coin.timeframes).length">
            <div class="section-title">{{ t('coin_detail.multi_timeframe') }}</div>
            <div class="tf-grid">
              <div v-for="(tf, tfKey) in coin.timeframes" :key="tfKey" class="tf-cell">
                <span class="tf-key">{{ tfKey }}</span>
                <span class="tf-trend" :class="tf.macd_bullish ? 'pos' : 'neg'">
                  {{ tf.macd_bullish ? '▲' : '▼' }}
                </span>
                <span v-if="tf.rsi" class="tf-sub">RSI {{ tf.rsi }}</span>
                <span v-if="tf.vs_ema200 != null" class="tf-sub" :class="tf.vs_ema200 > 0 ? 'pos' : 'neg'">
                  EMA200 {{ tf.vs_ema200 > 0 ? '+' : '' }}{{ tf.vs_ema200 }}%
                </span>
              </div>
            </div>
          </template>

          <!-- Support / Resistance -->
          <template v-if="coin.supports?.length || coin.resistances?.length">
            <div class="section-title">{{ t('coin_detail.sr_levels') }}</div>
            <div class="levels-grid">
              <div class="lvl-col">
                <div class="lvl-header neg-txt">{{ t('coin_detail.resistance') }}</div>
                <div v-if="!coin.resistances?.length" class="lvl-empty">—</div>
                <div v-for="r in coin.resistances" :key="r.price" class="lvl-item res-item">
                  <span>{{ formatPrice(r.price) }}</span>
                  <span class="lvl-touches">×{{ r.touches }}</span>
                </div>
              </div>
              <div class="lvl-col">
                <div class="lvl-header pos-txt">{{ t('coin_detail.support') }}</div>
                <div v-if="!coin.supports?.length" class="lvl-empty">—</div>
                <div v-for="s in coin.supports" :key="s.price" class="lvl-item sup-item">
                  <span>{{ formatPrice(s.price) }}</span>
                  <span class="lvl-touches">×{{ s.touches }}</span>
                </div>
              </div>
            </div>
          </template>

        </div><!-- /detail-body -->
      </div><!-- /detail-sheet -->
    </div><!-- /detail-overlay -->
  </Teleport>
</template>

<script setup>
import { createChart } from 'lightweight-charts'
import { onMounted, onBeforeUnmount, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'

const { t } = useI18n()

const props = defineProps({
  coin: { type: Object, required: true },
  live: { type: Object, default: null },
})
defineEmits(['close'])

const API       = import.meta.env.VITE_API_BASE || ''
const INTERVALS = ['15m', '1h', '4h', '1d', '1w']

const interval      = ref('1h')
const chartContainer = ref(null)
const chartLoading  = ref(false)
const noCandles     = ref(false)
let chart        = null
let candleSeries = null
let ro           = null

const BD_LABELS = {
  btc_dominance:      () => t('coin_detail.bd.btc_dominance'),
  fear_greed:         () => t('coin_detail.bd.fear_greed'),
  narrative:          () => t('coin_detail.bd.narrative'),
  narrative_position: () => t('coin_detail.bd.narrative_position'),
  rsi:                () => t('coin_detail.bd.rsi'),
  ema_200:            () => t('coin_detail.bd.ema_200'),
  volume:             () => t('coin_detail.bd.volume'),
  structure:          () => t('coin_detail.bd.structure'),
  catalyst:           () => t('coin_detail.bd.catalyst'),
}
const MAX_PTS = {
  btc_dominance:      2,
  fear_greed:         2,
  narrative:          2,
  narrative_position: 2,
  rsi:                2,
  ema_200:            2,
  volume:             2,
  structure:          2,
  catalyst:           4,
}

function formatPrice(p) {
  if (!p) return '—'
  if (p >= 10000) return '$' + p.toLocaleString('en', { maximumFractionDigits: 0 })
  if (p >= 1000)  return '$' + p.toFixed(1)
  if (p >= 100)   return '$' + p.toFixed(2)
  if (p >= 1)     return '$' + p.toFixed(3)
  return '$' + p.toFixed(4)
}

function rsiClass(v) {
  if (v < 30 || (v >= 35 && v <= 50)) return 'pos'
  if (v > 75) return 'neg'
  return ''
}

function bbLabel(v) {
  if (v < 0.2) return t('coin_detail.near_lower')
  if (v > 0.8) return t('coin_detail.near_upper')
  return t('coin_detail.mid_band')
}

async function loadCandles(iv) {
  if (!chart || !candleSeries) return
  chartLoading.value = true
  noCandles.value    = false
  try {
    const limit = iv === '1w' ? 208 : iv === '1d' ? 365 : 200
    const { data } = await axios.get(
      `${API}/api/spot/coin/${props.coin.symbol}/candles`,
      { params: { interval: iv, limit } }
    )
    if (data.candles?.length) {
      candleSeries.setData(data.candles)
      chart.timeScale().fitContent()
    } else {
      candleSeries.setData([])
      noCandles.value = true
    }
  } catch (e) {
    console.error('Failed to load candles', e)
    noCandles.value = true
  } finally {
    chartLoading.value = false
  }
}

function changeInterval(iv) {
  interval.value = iv
  loadCandles(iv)
}

onMounted(() => {
  chart = createChart(chartContainer.value, {
    layout: {
      background: { color: '#1a1d27' },
      textColor:  '#718096',
    },
    grid: {
      vertLines: { color: '#2d3748' },
      horzLines: { color: '#2d3748' },
    },
    crosshair: {
      vertLine: { color: '#4a5568' },
      horzLine: { color: '#4a5568' },
    },
    rightPriceScale: { borderColor: '#2d3748' },
    timeScale: { borderColor: '#2d3748', timeVisible: true },
    width:  chartContainer.value.clientWidth,
    height: 260,
  })

  candleSeries = chart.addCandlestickSeries({
    upColor:        '#48bb78',
    downColor:      '#fc8181',
    borderUpColor:  '#48bb78',
    borderDownColor:'#fc8181',
    wickUpColor:    '#48bb78',
    wickDownColor:  '#fc8181',
  })

  ro = new ResizeObserver(entries => {
    for (const e of entries)
      chart.applyOptions({ width: e.contentRect.width })
  })
  ro.observe(chartContainer.value)

  loadCandles(interval.value)
})

onBeforeUnmount(() => {
  ro?.disconnect()
  chart?.remove()
  chart = null
  candleSeries = null
})
</script>

<style scoped>
/* ── Overlay ──────────────────────────────────────────────────────────────── */
.detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  z-index: 200;
  display: flex;
  align-items: flex-end;
}

/* ── Sheet ────────────────────────────────────────────────────────────────── */
.detail-sheet {
  width: 100%;
  max-height: 93dvh;
  background: var(--color-surface);
  border-radius: 1rem 1rem 0 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.22s ease;
}
@keyframes slideUp {
  from { transform: translateY(50px); opacity: 0; }
  to   { transform: translateY(0);    opacity: 1; }
}

/* ── Header ───────────────────────────────────────────────────────────────── */
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.9rem 1rem;
  border-bottom: 1px solid var(--color-border);
  flex-shrink: 0;
  gap: 0.5rem;
}
.dh-info    { display: flex; align-items: baseline; gap: 0.4rem; flex: 1; }
.dh-symbol  { font-size: 1.35rem; font-weight: 800; color: var(--color-text); }
.dh-name    { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }
.dh-price-block { display: flex; flex-direction: column; align-items: flex-end; }
.dh-price   { font-size: 1.1rem; font-weight: 700; color: var(--color-text); }
.dh-change  { font-size: var(--font-size-sm-plus); font-weight: 600; }
.close-btn  {
  background: var(--color-border); border: none; color: var(--color-text-secondary-bright);
  font-size: var(--font-size-base); width: 34px; height: 34px;
  border-radius: 50%; cursor: pointer; flex-shrink: 0;
}
.close-btn:active { background: var(--color-text-muted); }

/* ── Body ─────────────────────────────────────────────────────────────────── */
.detail-body {
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  flex: 1;
  padding: 0.75rem 1rem 2rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* ── Interval tabs ────────────────────────────────────────────────────────── */
.interval-tabs { display: flex; gap: 0.4rem; flex-wrap: wrap; }
.iv-btn {
  padding: 0.3rem 0.7rem; border-radius: 999px;
  border: 1px solid var(--color-text-muted); background: var(--color-border);
  color: var(--color-text-secondary-bright); font-size: var(--font-size-sm-plus); cursor: pointer;
  min-height: 32px;
}
.iv-btn.active { background: var(--color-accent-muted); color: var(--color-accent-strong); border-color: var(--color-accent); }

/* ── Chart ────────────────────────────────────────────────────────────────── */
.chart-wrap    { position: relative; margin: 0.25rem 0; border-radius: 0.4rem; overflow: hidden; }
.chart-inner   { width: 100%; }
.chart-overlay {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(26, 29, 39, 0.75);
  font-size: var(--font-size-sm-plus); color: var(--color-text-secondary);
}

/* ── Score row ────────────────────────────────────────────────────────────── */
.score-row { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.25rem; }
.sr-rating { font-size: var(--font-size-sm-plus); white-space: nowrap; }
.sr-bar-wrap { flex: 1; height: 7px; background: var(--color-border); border-radius: 4px; }
.sr-bar { height: 100%; border-radius: 4px; transition: width 0.4s ease; }
.bar-very_hot { background: var(--color-danger); }
.bar-warm     { background: var(--color-warning); }
.bar-cold     { background: var(--color-text-muted); }
.bar-avoid    { background: var(--color-border); }
.sr-score { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); white-space: nowrap; }

/* ── Section title ────────────────────────────────────────────────────────── */
.section-title {
  font-size: var(--font-size-sm-plus); color: var(--color-text-secondary);
  text-transform: uppercase; letter-spacing: 0.07em;
  padding-top: 0.75rem;
}

/* ── Breakdown bars ───────────────────────────────────────────────────────── */
.bd-list { display: flex; flex-direction: column; gap: 0.35rem; }
.bd-row  { display: flex; align-items: center; gap: 0.4rem; }
.bd-key  { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); min-width: 72px; }
.bd-track { flex: 0 0 80px; height: 6px; background: var(--color-border); border-radius: 3px; overflow: hidden; }
.bd-fill  { height: 100%; border-radius: 3px; transition: width 0.4s; }
.pos-fill { background: var(--color-success); }
.neg-fill { background: var(--color-danger); }
.bd-pts   { font-size: var(--font-size-sm-plus); font-weight: 700; min-width: 22px; text-align: end; }
.bd-reason { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); flex: 1; }

/* ── Indicators grid ──────────────────────────────────────────────────────── */
.ind-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.5rem;
}
.ind-cell {
  background: var(--color-border); border-radius: 0.4rem;
  padding: 0.5rem 0.65rem;
  display: flex; flex-direction: column; gap: 0.15rem;
}
.ic-label { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; }
.ic-val   { font-size: var(--font-size-sm-plus); font-weight: 600; }

/* ── Multi-TF ─────────────────────────────────────────────────────────────── */
.tf-grid { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.tf-cell {
  background: var(--color-border); border-radius: 0.4rem;
  padding: 0.4rem 0.65rem;
  display: flex; flex-direction: column; gap: 0.1rem;
  min-width: 72px;
}
.tf-key   { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); text-transform: uppercase; }
.tf-trend { font-size: 1.05rem; font-weight: 700; }
.tf-sub   { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); }

/* ── S/R Levels ───────────────────────────────────────────────────────────── */
.levels-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.lvl-col  { display: flex; flex-direction: column; gap: 0.3rem; }
.lvl-header { font-size: var(--font-size-sm-plus); font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; padding-bottom: 0.15rem; }
.lvl-item { display: flex; justify-content: space-between; align-items: center; font-size: var(--font-size-base); padding: 0.3rem 0.55rem; border-radius: 0.3rem; }
.res-item { background: var(--color-danger-bg); color: var(--color-danger); }
.sup-item { background: var(--color-success-bg); color: var(--color-success-strong); }
.lvl-touches { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }
.lvl-empty   { font-size: var(--font-size-sm-plus); color: var(--color-text-muted); }

/* ── Colour helpers ───────────────────────────────────────────────────────── */
.pos     { color: var(--color-success-strong); }
.neg     { color: var(--color-danger); }
.muted   { color: var(--color-text-secondary); }
.muted-txt { color: var(--color-text-muted); }
.pos-txt { color: var(--color-success-strong); }
.neg-txt { color: var(--color-danger); }
</style>
