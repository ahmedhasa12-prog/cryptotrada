<template>
  <div class="card">
    <div class="card-header">
      <h2>{{ t('snapshot.title') }}</h2>
      <button class="refresh-btn" @click="refresh" :disabled="loading">
        {{ loading ? t('snapshot.refreshing') : t('snapshot.refresh') }}
      </button>
    </div>

    <div v-if="snap">
      <div class="snapshot-grid">
        <div class="metric">
          <span class="metric-label">{{ t('snapshot.sell_at') }}</span>
          <span class="metric-value">{{ fmt(snap.buy_best_rate) }} SDG</span>
          <span class="metric-hint">{{ t('snapshot.sell_hint') }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">{{ t('snapshot.buy_at') }}</span>
          <span class="metric-value">{{ fmt(snap.sell_best_rate) }} SDG</span>
          <span class="metric-hint">{{ t('snapshot.buy_hint') }}</span>
        </div>
      </div>

      <div class="gap-strip" :class="gapClass">
        <div class="gap-left">
          <span class="gap-label">{{ t('snapshot.gap') }}</span>
          <span class="gap-value">{{ fmt(snap.spread) }} SDG</span>
        </div>
        <span class="gap-advice">{{ gapAdvice }}</span>
      </div>

      <div class="avg-row">
        <div class="avg-item">
          <span class="avg-label">{{ t('snapshot.avg_1h') }}</span>
          <span class="avg-val">{{ fmt(snap.avg_spread_1h) }} SDG</span>
        </div>
        <div class="avg-item">
          <span class="avg-label">{{ t('snapshot.avg_24h') }}</span>
          <span class="avg-val">{{ fmt(snap.avg_spread_24h) }} SDG</span>
        </div>
        <div class="avg-item">
          <span class="avg-label">{{ t('snapshot.last_updated') }}</span>
          <span class="avg-val time">{{ lastUpdated }}</span>
        </div>
      </div>

      <div class="market-tables">
        <div v-if="snap?.top_sellers?.length" class="market-side">
          <h3 class="side-header buy-side">{{ t('snapshot.buyers_title') }}</h3>
          <div class="side-table-wrap">
            <table>
              <thead><tr>
                <th>{{ t('snapshot.col_rank') }}</th>
                <th>{{ t('snapshot.col_merchant') }}</th>
                <th>{{ t('snapshot.col_pays') }}</th>
              </tr></thead>
              <tbody>
                <tr v-for="(s, i) in snap.top_sellers" :key="'b'+i">
                  <td>{{ i + 1 }}</td><td>{{ s.name }}</td>
                  <td class="price-cell buy-price">{{ s.price?.toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div v-if="snap?.active_sellers?.length" class="market-side">
          <h3 class="side-header sell-side">{{ t('snapshot.sellers_title') }}</h3>
          <div class="side-table-wrap">
            <table>
              <thead><tr>
                <th>{{ t('snapshot.col_rank') }}</th>
                <th>{{ t('snapshot.col_merchant') }}</th>
                <th>{{ t('snapshot.col_charges') }}</th>
              </tr></thead>
              <tbody>
                <tr v-for="(s, i) in snap.active_sellers" :key="'s'+i">
                  <td>{{ i + 1 }}</td><td>{{ s.name }}</td>
                  <td class="price-cell sell-price">{{ s.price?.toFixed(2) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <p v-if="!snap && !loading" class="empty">{{ t('snapshot.empty') }}</p>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../stores/platform'

const { t } = useI18n()
const store   = usePlatformStore()
const loading = ref(false)
const snap    = computed(() => store.snapshot)

const gapClass = computed(() => {
  const s = snap.value?.spread
  if (s == null) return 'gap-unknown'
  if (s >= 25)  return 'gap-wide'
  if (s < 10)   return 'gap-tight'
  return 'gap-normal'
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

function fmt(v) { return v != null ? Number(v).toFixed(2) : '—' }

async function refresh() {
  loading.value = true
  try { await store.fetchSnapshot() } finally { loading.value = false }
}

onMounted(refresh)
</script>

<style scoped>
.metric-hint { font-size: 0.65rem; color: #4a5568; margin-top: -0.1rem; }

.gap-strip {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.6rem 0.75rem; border-radius: 0.5rem; margin: 0.75rem 0;
  gap: 0.5rem; flex-wrap: wrap;
}
.gap-wide    { background: #1a2e1a; border: 1px solid #276227; }
.gap-normal  { background: #2a2516; border: 1px solid #7a6520; }
.gap-tight   { background: #2d1616; border: 1px solid #7a2020; }
.gap-unknown { background: #1a1d27; border: 1px solid #2d3748; }

.gap-left  { display: flex; flex-direction: column; gap: 0.1rem; }
.gap-label { font-size: 0.65rem; color: #718096; text-transform: uppercase; letter-spacing: 0.04em; }
.gap-value { font-size: 1.35rem; font-weight: 700; }
.gap-wide  .gap-value  { color: #68d391; }
.gap-tight .gap-value  { color: #fc8181; }
.gap-normal .gap-value { color: #f6ad55; }
.gap-advice { font-size: 0.82rem; color: #cbd5e0; }

.avg-row   { display: flex; gap: 1rem; margin-bottom: 0.875rem; flex-wrap: wrap; }
.avg-item  { display: flex; flex-direction: column; gap: 0.15rem; min-width: 80px; }
.avg-label { font-size: 0.65rem; color: #718096; text-transform: uppercase; letter-spacing: 0.04em; }
.avg-val   { font-size: 0.95rem; font-weight: 600; }
.avg-val.time { font-size: 0.8rem; font-weight: 400; color: #a0aec0; }

.market-tables { display: flex; flex-direction: column; gap: 1rem; margin-top: 0.25rem; }
@media (min-width: 600px) {
  .market-tables { flex-direction: row; }
  .market-side   { flex: 1; min-width: 0; }
}

.side-header { font-size: 0.75rem; font-weight: 600; margin: 0 0 0.4rem; text-transform: uppercase; letter-spacing: 0.04em; }
.buy-side    { color: #68d391; }
.sell-side   { color: #fc8181; }

.side-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.side-table-wrap table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
.side-table-wrap th { text-align: start; color: #718096; font-weight: 500; padding: 0.3rem 0.5rem; font-size: 0.7rem; text-transform: uppercase; }
.side-table-wrap td { padding: 0.4rem 0.5rem; border-top: 1px solid #2d3748; white-space: nowrap; }
.side-table-wrap td:first-child { color: #4a5568; width: 1.2rem; }

.price-cell { font-weight: 600; font-variant-numeric: tabular-nums; }
.buy-price  { color: #68d391; }
.sell-price { color: #fc8181; }
</style>
