<template>
  <div class="page-view">
    <!-- ═══════════════════════════════════════════════════════════════
         SECTION 1 — MARKET SNAPSHOT
         ═══════════════════════════════════════════════════════════════ -->
    <div class="card" v-if="snapshot">
      <div class="card-header">
        <h2>💱 {{ t('snapshot.title') }}</h2>
        <span class="conn-dot" :class="{ connected: snapshot.conditions.some(c => c.type === 'spread_wide') }"
              :title="snapshot.conditions.map(c => c.icon + ' ' + c.params.spread + ' SDG').join(', ')"></span>
      </div>

      <!-- Rate cards -->
      <div class="rates-grid">
        <div class="rate-card buy">
          <span class="rate-label">🟢 Best Buy Rate</span>
          <span class="rate-val big">{{ fmt(snapshot.buy_best_rate) }} SDG</span>
        </div>
        <div class="rate-card sell">
          <span class="rate-label">🔴 Best Sell Rate</span>
          <span class="rate-val big">{{ fmt(snapshot.sell_best_rate) }} SDG</span>
        </div>
        <div class="rate-card spread">
          <span class="rate-label">📊 Spread</span>
          <span class="rate-val big" :class="spreadClass">{{ fmt(snapshot.spread) }} SDG</span>
        </div>
        <div class="rate-card avg">
          <span class="rate-label">📈 Avg Spread (24h)</span>
          <span class="rate-val">{{ fmt(snapshot.avg_spread_24h) }} SDG</span>
        </div>
      </div>

      <!-- Conditions -->
      <div class="conditions-strip">
        <span v-for="(cond, i) in snapshot.conditions" :key="i"
              class="condition-badge" :class="cond.level">
          {{ cond.icon }} {{ cond.params.spread }} SDG
        </span>
      </div>

      <!-- Active Traders -->
      <div class="traders-section">
        <h3>🟢 Active Sellers</h3>
        <div class="traders-list">
          <div v-for="(s, i) in snapshot.active_sellers.slice(0, 8)" :key="i"
               class="trader-row">
            <span class="trader-name">{{ s.name }}</span>
            <span class="trader-price">{{ fmt(s.price) }} SDG</span>
            <span class="trader-range">{{ s.min }}–{{ fmtMax(s.max) }} USDT</span>
          </div>
        </div>
        <h3 style="margin-top:1rem">🟢 Top Buyers</h3>
        <div class="traders-list">
          <div v-for="(b, i) in snapshot.top_sellers.slice(0, 5)" :key="i"
               class="trader-row">
            <span class="trader-name">{{ b.name }}</span>
            <span class="trader-price">{{ fmt(b.price) }} SDG</span>
            <span class="trader-range">{{ b.min }}–{{ fmtMax(b.max) }} USDT</span>
          </div>
        </div>
      </div>
    </div>
    <p v-else class="empty">{{ t('snapshot.empty') }}</p>

    <!-- ═══════════════════════════════════════════════════════════════
         SECTION 2 — TODAY'S STATS
         ═══════════════════════════════════════════════════════════════ -->
    <TodayStats />

    <!-- ═══════════════════════════════════════════════════════════════
         SECTION 3 — SPREAD HISTORY CHART + HOURLY PATTERNS
         ═══════════════════════════════════════════════════════════════ -->
    <Analytics />

    <!-- ═══════════════════════════════════════════════════════════════
         SECTION 4 — WEEKDAY HEATMAP
         ═══════════════════════════════════════════════════════════════ -->
    <div class="card">
      <div class="card-header">
        <h2>🗓️ {{ t('timing.weekday_title') }}</h2>
        <span class="muted">{{ t('timing.weekly_patterns') || t('timing.weekday_hint') }}</span>
      </div>
      <div v-if="weekdayPatterns.length" class="heatmap-weekday">
        <div class="heatmap-header">
          <span class="heatmap-label">Day</span>
          <span class="heatmap-label">Avg Spread</span>
          <span class="heatmap-label">Samples</span>
        </div>
        <div v-for="wd in weekdayPatterns" :key="wd.day" class="heatmap-row">
          <span class="heatmap-label">{{ wd.day_key }}</span>
          <span class="heatmap-cell" :class="{ reliable: wd.reliable }">
            {{ wd.reliable ? fmt(wd.avg_spread) : '—' }}
          </span>
          <span class="heatmap-cell" :class="{ reliable: wd.reliable }">
            {{ wd.sample_count }}
          </span>
        </div>
      </div>
      <p v-else class="empty">{{ t('analytics.no_patterns') }}</p>
    </div>

    <!-- ═══════════════════════════════════════════════════════════════
         SECTION 5 — PRICE HISTORY TABLE
         ═══════════════════════════════════════════════════════════════ -->
    <div class="card">
      <div class="card-header">
        <h2>📋 {{ t('snapshot.last_updated') }} — {{ t('snapshot.title') }}</h2>
        <span class="muted">{{ t('analytics.data_points') }}</span>
      </div>
      <div class="table-wrap">
        <table class="price-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Time</th>
              <th>🟢 Buy Rate</th>
              <th>🔴 Sell Rate</th>
              <th>📊 Spread</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in priceHistory" :key="i">
              <td>{{ priceHistory.length - i }}</td>
              <td>{{ formatTime(row.t) }}</td>
              <td class="buy-color">{{ fmt(row.buy) }}</td>
              <td class="sell-color">{{ fmt(row.sell) }}</td>
              <td :class="row.spread > -1000 ? '' : 'negative'">{{ fmt(row.spread) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '@/stores/platform'
import Analytics from '@/components/Analytics.vue'
import TodayStats from '@/components/TodayStats.vue'

const { t } = useI18n()
const store = usePlatformStore()

const snapshot = computed(() => store.snapshot)
const weekdayPatterns = computed(() => store.weekdayPatterns)
// Spread history as simple array for the table
const priceHistory = computed(() => {
  return store.spreadHistory.slice(0, 30).reverse()
})

const spreadClass = computed(() => {
  if (!snapshot.value) return ''
  const s = snapshot.value.spread
  return s < -1500 ? 'negative' : s < -500 ? 'positive' : ''
})

function fmt(v: number | null): string {
  return v != null ? Number(v).toFixed(0) : '—'
}

function fmtMax(v: number): string {
  if (v == null) return '—'
  if (v >= 1000000) return (v / 1000000).toFixed(1) + 'M'
  if (v >= 1000) return (v / 1000).toFixed(1) + 'K'
  return String(v)
}

function formatTime(iso: string): string {
  const d = new Date(iso)
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false })
}

onMounted(async () => {
  await Promise.all([
    store.fetchSnapshot(),
    store.fetchTodayStats(),
    store.fetchTimingData(),
    store.fetchAnalytics(7),
  ])
})
</script>

<style scoped>
.page-view {
  display: flex;
  flex-direction: column;
  gap: var(--space-6, 1.5rem);
  padding: var(--space-6, 1.5rem);
  max-width: var(--content-max-width, 1280px);
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

/* Card */
.card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-brand-subtle);
  flex-wrap: wrap;
  gap: var(--space-2);
}

.card-header h2 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.muted {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

.conn-dot {
  width: 8px; height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-danger);
}
.conn-dot.connected {
  background: var(--color-success);
}

/* Rates grid */
.rates-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-3);
  padding: var(--space-4) var(--space-6);
}
@media (max-width: 640px) {
  .rates-grid { grid-template-columns: repeat(2, 1fr); }
}

.rate-card {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  padding: var(--space-3);
  border-radius: var(--radius-lg);
  background: var(--color-surface-raised);
}
.rate-label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.rate-val {
  font-size: var(--text-sm);
  color: var(--color-text);
}
.rate-val.big {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
}
.rate-card.buy .rate-val { color: var(--color-success); }
.rate-card.sell .rate-val { color: var(--color-danger); }
.rate-card.spread .rate-val { color: var(--color-accent); }
.negative { color: var(--color-danger); }
.positive { color: var(--color-success); }

/* Conditions */
.conditions-strip {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  flex-wrap: wrap;
}
.condition-badge {
  font-size: var(--text-sm);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
  border: 1px solid var(--color-border);
}
.condition-badge.tight { background: rgba(220, 53, 69, 0.1); border-color: var(--color-danger); color: var(--color-danger); }
.condition-badge.normal { background: rgba(40, 167, 69, 0.1); border-color: var(--color-success); color: var(--color-success); }
.condition-badge.wide { background: rgba(255, 193, 7, 0.1); border-color: #ffc107; color: #ffc107; }
.condition-badge.info { background: rgba(0, 123, 255, 0.1); border-color: var(--color-accent); color: var(--color-accent); }

/* Traders */
.traders-section {
  padding: var(--space-4) var(--space-6);
}
.traders-section h3 {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}
.traders-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}
.trader-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-md);
  background: var(--color-surface-raised);
  font-size: var(--text-sm);
}
.trader-name {
  flex: 1;
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}
.trader-price {
  font-weight: var(--font-semibold);
  color: var(--color-success);
}
.trader-range {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

/* Heatmap */
.heatmap-weekday { padding: var(--space-4) var(--space-6); }
.heatmap-header {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-bottom: var(--space-1);
}
.heatmap-label {
  width: 60px;
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  font-weight: var(--font-semibold);
  flex-shrink: 0;
}
.heatmap-hour {
  flex: 1;
  font-size: 0.55rem;
  color: var(--color-text-subtle);
  text-align: center;
  min-width: 0;
}
.heatmap-hour--hl { color: var(--color-text-secondary); }
.heatmap-row {
  display: flex;
  align-items: center;
  gap: 2px;
  margin-bottom: 2px;
}
.heatmap-cell {
  flex: 1;
  height: 20px;
  border-radius: 2px;
  text-align: center;
  font-size: 0.45rem;
  color: var(--color-text-subtle);
  line-height: 20px;
  min-width: 0;
}
.cell-empty { background: var(--color-border); opacity: 0.3; }
.cell { background: var(--color-accent); opacity: 0.3; }

/* Price table */
.table-wrap { overflow-x: auto; padding: var(--space-2) 0; }
.price-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}
.price-table th {
  text-align: left;
  padding: var(--space-2) var(--space-4);
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface-raised);
}
.price-table td {
  padding: var(--space-2) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-secondary);
}
.price-table tr:hover td { background: var(--color-surface-hover); }
.buy-color { color: var(--color-success); }
.sell-color { color: var(--color-danger); }

.empty {
  padding: var(--space-6);
  text-align: center;
  color: var(--color-text-tertiary);
}
</style>

<style scoped>
/* Mobile: compact P2P layout */
.p2p-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: var(--space-3);
}

@media (min-width: 768px) {
    .p2p-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

@media (min-width: 1024px) {
    .p2p-grid {
        grid-template-columns: repeat(3, 1fr);
    }
}

/* Touch-friendly P2P cards */
.p2p-card {
    min-height: 80px;
    padding: var(--space-3);
}

/* Responsive heatmap */
.heatmap-container {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}

.heatmap-grid {
    min-width: 100%;
}
</style>
