<template>
  <div class="agent-positions">
    <div class="positions-header">
      <h2>{{ t('agents.positions') }}</h2>
      <div class="positions-summary">
        <span class="summary-item">
          <span class="summary-value">{{ openCount }}</span>
          <span class="summary-label">{{ t('agents.open') }}</span>
        </span>
        <span class="summary-item">
          <span class="summary-value" :class="totalPnl >= 0 ? 'positive' : 'negative'">
            {{ formatPnL(totalPnl) }}
          </span>
          <span class="summary-label">{{ t('agents.unrealized_pnl') }}</span>
        </span>
      </div>
    </div>

    <div v-if="loading" class="positions-loading">
      <div class="spinner"></div>
      <span>{{ t('common.loading') }}</span>
    </div>

    <div v-else-if="positions.length === 0" class="positions-empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
        <path d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path>
      </svg>
      <p>{{ t('agents.no_open_positions') }}</p>
    </div>

    <div v-else class="positions-table-wrapper">
      <table class="positions-table">
        <thead>
          <tr>
            <th>{{ t('agents.symbol') }}</th>
            <th>{{ t('agents.side') }}</th>
            <th>{{ t('agents.size') }}</th>
            <th>{{ t('agents.entry_price') }}</th>
            <th>{{ t('agents.current_price') }}</th>
            <th>{{ t('agents.unrealized_pnl') }}</th>
            <th>{{ t('agents.pnl_pct') }}</th>
            <th>{{ t('agents.stop_loss') }}</th>
            <th>{{ t('agents.take_profit') }}</th>
            <th>{{ t('agents.duration') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="pos in positions" :key="pos.id" class="position-row">
            <td class="symbol-cell">
              <span class="symbol">{{ pos.symbol }}</span>
            </td>
            <td>
              <span class="side-badge" :class="pos.side === 'long' ? 'long' : 'short'">
                {{ pos.side }}
              </span>
            </td>
            <td class="numeric">{{ formatSize(pos.size) }}</td>
            <td class="numeric">{{ formatPrice(pos.entry_price) }}</td>
            <td class="numeric">{{ formatPrice(pos.current_price) }}</td>
            <td class="numeric">
              <span :class="pos.unrealized_pnl >= 0 ? 'positive' : 'negative'">
                {{ formatPnL(pos.unrealized_pnl) }}
              </span>
            </td>
            <td class="numeric">
              <span :class="pos.pnl_pct >= 0 ? 'positive' : 'negative'">
                {{ pos.pnl_pct >= 0 ? '+' : '' }}{{ pos.pnl_pct.toFixed(2) }}%
              </span>
            </td>
            <td class="numeric">{{ pos.stop_loss ? formatPrice(pos.stop_loss) : '—' }}</td>
            <td class="numeric">{{ pos.take_profit ? formatPrice(pos.take_profit) : '—' }}</td>
            <td>{{ formatDuration(pos.duration) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { usePlatformStore } from '@/stores/platform'

const { t } = useI18n()
const route = useRoute()
const platformStore = usePlatformStore()

const agentType = route.params.type as string
const loading = ref(true)
const positions = ref<Array<any>>([])

const openCount = computed(() => positions.value.length)
const totalPnl = computed(() => positions.value.reduce((sum, p) => sum + (p.unrealized_pnl || 0), 0))

async function fetchPositions() {
  loading.value = true
  try {
    // In real implementation, this would call the API
    // For now, mock data
    positions.value = [
      { id: 1, symbol: 'BTC', side: 'long', size: 0.5, entry_price: 67000, current_price: 67234, unrealized_pnl: 117, pnl_pct: 0.17, stop_loss: 65000, take_profit: 70000, duration: 3600000 },
      { id: 2, symbol: 'ETH', side: 'long', size: 2.0, entry_price: 3400, current_price: 3421, unrealized_pnl: 42, pnl_pct: 0.62, stop_loss: 3300, take_profit: 3600, duration: 7200000 },
      { id: 3, symbol: 'SOL', side: 'short', size: 50, entry_price: 145, current_price: 142, unrealized_pnl: 150, pnl_pct: 2.07, stop_loss: 150, take_profit: 135, duration: 1800000 },
    ]
  } catch (e) {
    console.error('Failed to fetch positions:', e)
  } finally {
    loading.value = false
  }
}

function formatSize(size: number): string {
  return size.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 4 })
}

function formatPrice(price: number): string {
  if (price >= 1000) return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (price >= 1) return price.toFixed(4)
  return price.toFixed(6)
}

function formatPnL(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatDuration(ms: number): string {
  if (ms < 60000) return `${Math.floor(ms / 1000)}s`
  if (ms < 3600000) return `${Math.floor(ms / 60000)}m`
  if (ms < 86400000) return `${Math.floor(ms / 3600000)}h`
  return `${Math.floor(ms / 86400000)}d`
}

onMounted(() => {
  fetchPositions()
})
</script>

<style scoped>
.agent-positions {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.positions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.positions-header h2 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.positions-summary {
  display: flex;
  gap: var(--space-6);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.summary-value {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.summary-value.positive { color: var(--color-success); }
.summary-value.negative { color: var(--color-danger); }

.summary-label {
  font-size: var(--text-2xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.positions-loading,
.positions-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) var(--space-4);
  text-align: center;
  color: var(--color-text-tertiary);
}

.positions-loading .spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-brand);
  border-radius: var(--radius-full);
  animation: spin 0.8s linear infinite;
  margin-bottom: var(--space-3);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.positions-empty svg {
  margin-bottom: var(--space-3);
  opacity: 0.5;
}

.positions-empty p {
  font-size: var(--text-sm);
  margin: 0;
}

.positions-table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
}

.positions-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-sm);
}

.positions-table th {
  text-align: start;
  color: var(--color-text-tertiary);
  font-weight: var(--font-medium);
  padding: var(--space-2) var(--space-3);
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  background: var(--color-surface-raised);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.positions-table td {
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border-subtle);
  white-space: nowrap;
}

.positions-table tbody tr:last-child td {
  border-bottom: none;
}

.positions-table tbody tr:hover {
  background: var(--color-surface-hover);
}

.position-row td {
  color: var(--color-text);
}

.symbol-cell .symbol {
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.side-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  min-width: 56px;
}

.side-badge.long {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success-border);
}

.side-badge.short {
  background: var(--color-danger-bg);
  color: var(--color-danger);
  border: 1px solid var(--color-danger-border);
}

.numeric {
  text-align: end;
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.positive { color: var(--color-success); }
.negative { color: var(--color-danger); }

@media (max-width: 639px) {
  .positions-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .positions-table th:nth-child(n+6),
  .positions-table td:nth-child(n+6) {
    display: none;
  }
}
</style>