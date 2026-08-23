<template>
  <div class="agent-overview">
    <div class="overview-grid">
      <!-- Trade Status -->
      <div class="overview-card">
        <h3>{{ t('agents.trade_status') }}</h3>
        <div class="overview-stats">
          <div class="stat">
            <span class="stat-value" :class="hasActiveTrade ? 'positive' : 'neutral'">
              {{ hasActiveTrade ? t('agents.active') : t('agents.no_active_trade') }}
            </span>
            <span class="stat-label">{{ t('agents.current_status') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ currentSetup || '—' }}</span>
            <span class="stat-label">{{ t('agents.current_setup') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ verdictLabel }}</span>
            <span class="stat-label">{{ t('agents.verdict') }}</span>
          </div>
        </div>
      </div>

      <!-- Performance -->
      <div class="overview-card">
        <h3>{{ t('agents.performance') }}</h3>
        <div class="overview-stats">
          <div class="stat">
            <span class="stat-value" :class="totalPnl >= 0 ? 'positive' : 'negative'">
              {{ formatPnL(totalPnl) }}
            </span>
            <span class="stat-label">{{ t('agents.total_pnl') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ winRate }}%</span>
            <span class="stat-label">{{ t('agents.win_rate') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ totalTrades }}</span>
            <span class="stat-label">{{ t('agents.total_trades') }}</span>
          </div>
        </div>
      </div>

      <!-- Auto Bot Status -->
      <div class="overview-card">
        <h3>{{ t('agents.auto_bot') }}</h3>
        <div class="overview-stats">
          <div class="stat">
            <span class="stat-value" :class="autoEnabled ? 'positive' : 'neutral'">
              {{ autoEnabled ? t('agents.enabled') : t('agents.disabled') }}
            </span>
            <span class="stat-label">{{ t('agents.auto_status') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">${{ autoSize }}</span>
            <span class="stat-label">{{ t('agents.auto_size') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ lastAction || '—' }}</span>
            <span class="stat-label">{{ t('agents.last_action') }}</span>
          </div>
        </div>
      </div>

      <!-- Configuration Summary -->
      <div class="overview-card">
        <h3>{{ t('agents.config_summary') }}</h3>
        <div class="config-list">
          <div class="config-item">
            <span class="config-label">{{ t('agents.risk_budget') }}</span>
            <span class="config-value">${{ agent.config?.config?.risk_budget_usd || '—' }}</span>
          </div>
          <div class="config-item">
            <span class="config-label">{{ t('agents.cooldown_hours') }}</span>
            <span class="config-value">{{ agent.config?.config?.cooldown_hours || '—' }}h</span>
          </div>
          <div class="config-item">
            <span class="config-label">{{ t('agents.trail_arm_atr') }}</span>
            <span class="config-value">{{ agent.config?.config?.xrp_trail_arm_atr || '—' }}×ATR</span>
          </div>
          <div class="config-item">
            <span class="config-label">{{ t('agents.stage_pcts') }}</span>
            <span class="config-value">{{ formatStagePcts }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="overview-actions">
      <router-link :to="`/agents/${agentType}/trade_monitor`" class="btn btn-primary">
        {{ t('agents.view_trade_monitor') }}
      </router-link>
      <router-link :to="`/agents/${agentType}/setup`" class="btn btn-secondary">
        {{ t('agents.view_setup') }}
      </router-link>
      <router-link :to="`/agents/${agentType}/history`" class="btn btn-secondary">
        {{ t('agents.view_history') }}
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
const hasActiveTrade = computed(() => false)
const currentSetup = computed(() => 'B')
const verdictLabel = computed(() => 'ENTRY_READY')
const totalPnl = computed(() => 1234.56)
const winRate = computed(() => 72)
const totalTrades = computed(() => 28)
const autoEnabled = computed(() => false)
const autoSize = computed(() => 300)
const lastAction = computed(() => 'Waiting for ENTRY_READY')

function formatPnL(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatStagePcts(): string {
  const pcts = agent.value?.config?.config?.xrp_auto_stage_pcts || [0.2, 0.4, 0.4]
  return pcts.map(p => (p * 100).toFixed(0) + '%').join(' / ')
}
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