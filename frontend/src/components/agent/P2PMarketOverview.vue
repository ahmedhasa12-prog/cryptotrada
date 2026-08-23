<template>
  <div class="agent-overview">
    <div class="overview-grid">
      <!-- Market Status -->
      <div class="overview-card">
        <h3>{{ t('agents.market_status') }}</h3>
        <div class="overview-stats">
          <div class="stat">
            <span class="stat-value">{{ spread }}</span>
            <span class="stat-label">{{ t('agents.current_spread') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value" :class="spreadClass">{{ spreadAdvice }}</span>
            <span class="stat-label">{{ t('agents.market_condition') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ lastUpdate }}</span>
            <span class="stat-label">{{ t('agents.last_update') }}</span>
          </div>
        </div>
      </div>

      <!-- Rates -->
      <div class="overview-card">
        <h3>{{ t('agents.rates') }}</h3>
        <div class="overview-stats">
          <div class="stat">
            <span class="stat-value positive">{{ buyRate }}</span>
            <span class="stat-label">{{ t('agents.buy_rate') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value negative">{{ sellRate }}</span>
            <span class="stat-label">{{ t('agents.sell_rate') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ avg1h }}</span>
            <span class="stat-label">{{ t('agents.avg_1h') }}</span>
          </div>
        </div>
      </div>

      <!-- Volume -->
      <div class="overview-card">
        <h3>{{ t('agents.volume') }}</h3>
        <div class="overview-stats">
          <div class="stat">
            <span class="stat-value">{{ todayVolume }}</span>
            <span class="stat-label">{{ t('agents.today_volume') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ todayTrades }}</span>
            <span class="stat-label">{{ t('agents.today_trades') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ todayProfit }}</span>
            <span class="stat-label">{{ t('agents.today_profit') }}</span>
          </div>
        </div>
      </div>

      <!-- Configuration Summary -->
      <div class="overview-card">
        <h3>{{ t('agents.config_summary') }}</h3>
        <div class="config-list">
          <div class="config-item">
            <span class="config-label">{{ t('agents.auto_adjust') }}</span>
            <span class="config-value">{{ autoAdjust ? t('common.enabled') : t('common.disabled') }}</span>
          </div>
          <div class="config-item">
            <span class="config-label">{{ t('agents.adjustment_step') }}</span>
            <span class="config-value">{{ adjustmentStep }} SDG</span>
          </div>
          <div class="config-item">
            <span class="config-label">{{ t('agents.min_spread') }}</span>
            <span class="config-value">{{ minSpread }} SDG</span>
          </div>
          <div class="config-item">
            <span class="config-label">{{ t('agents.max_spread') }}</span>
            <span class="config-value">{{ maxSpread }} SDG</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="overview-actions">
      <router-link :to="`/agents/${agentType}/snapshot`" class="btn btn-primary">
        {{ t('agents.view_snapshot') }}
      </router-link>
      <router-link :to="`/agents/${agentType}/analytics`" class="btn btn-secondary">
        {{ t('agents.view_analytics') }}
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { usePlatformStore } from '@/stores/platform'

const { t } = useI18n()
const route = useRoute()
const platformStore = usePlatformStore()

const agentType = route.params.type as string
const agent = computed(() => platformStore.agents.find(a => a.agent_type === agentType))

// Mock data - in real implementation, this would come from API
const spread = computed(() => '+42 SDG')
const spreadClass = computed(() => 'positive')
const spreadAdvice = computed(() => 'Wide spread - great time to post ads')
const buyRate = computed(() => '4,125 SDG')
const sellRate = computed(() => '4,083 SDG')
const avg1h = computed(() => '+38 SDG')
const todayVolume = computed(() => '12,450 USDT')
const todayTrades = computed(() => 23)
const todayProfit = computed(() => '+1,234 SDG')
const autoAdjust = computed(() => true)
const adjustmentStep = computed(() => 5)
const minSpread = computed(() => 10)
const maxSpread = computed(() => 100)
const lastUpdate = computed(() => '2m ago')
</script>

<style scoped>
.agent-overview {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.overview-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
}

@media (min-width: 640px) {
  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .overview-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.overview-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
}

.overview-card h3 {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0 0 var(--space-4);
}

.overview-stats {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.stat-value {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.stat-value.positive { color: var(--color-success); }
.stat-value.negative { color: var(--color-danger); }
.stat-value.neutral { color: var(--color-text-secondary); }

.stat-label {
  font-size: var(--text-2xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.config-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.config-value {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.overview-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  padding-top: var(--space-2);
}

@media (max-width: 639px) {
  .overview-actions .btn {
    flex: 1;
  }
}
</style>