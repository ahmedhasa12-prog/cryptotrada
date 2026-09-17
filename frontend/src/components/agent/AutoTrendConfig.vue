<template>
  <div class="at-config">
    <AgentConfigSummary :agent="agent" />

    <Card :title="t('agents.risk_settings')">
      <Spinner v-if="loading" :label="t('common.loading')" />
      <div v-else-if="config" class="config-summary">
        <div class="config-row">
          <span class="config-row__label">{{ t('agents.position_size') }}</span>
          <span class="config-row__value">${{ config.position_usd }}</span>
        </div>
        <div class="config-row">
          <span class="config-row__label">{{ t('agents.max_positions') }}</span>
          <span class="config-row__value">{{ config.max_positions }}</span>
        </div>
        <div class="config-row">
          <span class="config-row__label">{{ t('agents.equity_usd') }}</span>
          <span class="config-row__value">${{ config.equity_usd }}</span>
        </div>
        <div class="config-row">
          <span class="config-row__label">{{ t('agents.risk_pct') }}</span>
          <span class="config-row__value">{{ (config.risk_pct_per_trade * 100).toFixed(1) }}%</span>
        </div>
        <div class="config-row">
          <span class="config-row__label">{{ t('agents.atr_stop_k') }}</span>
          <span class="config-row__value">{{ config.atr_stop_k }}×ATR</span>
        </div>
        <div class="config-row">
          <span class="config-row__label">{{ t('agents.cooldown_minutes') }}</span>
          <span class="config-row__value">{{ config.cooldown_min }}min</span>
        </div>
        <div class="config-row">
          <span class="config-row__label">{{ t('agents.daily_loss_limit') }}</span>
          <span class="config-row__value">${{ config.daily_loss_limit_usd }}</span>
        </div>
        <div class="config-row">
          <span class="config-row__label">{{ t('agents.weekly_loss_limit') }}</span>
          <span class="config-row__value">${{ config.weekly_loss_limit_usd }}</span>
        </div>
        <div class="config-row">
          <span class="config-row__label">{{ t('agents.btc_trend_gate') }}</span>
          <Badge :variant="config.btc_trend_gate ? 'success' : 'neutral'">
            {{ config.btc_trend_gate ? t('agents.enabled') : t('agents.disabled') }}
          </Badge>
        </div>
      </div>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '@/stores/platform'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Spinner from '@/components/ui/Spinner.vue'
import AgentConfigSummary from '@/components/agent/AgentConfigSummary.vue'

defineProps<{ agent?: any }>()
const { t } = useI18n()
const platformStore = usePlatformStore()

const config = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const data = await platformStore.fetchBotStatus()
    config.value = data.config ?? null
  } catch (e) {
    console.error('Failed to fetch bot config:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.at-config { display: flex; flex-direction: column; gap: var(--space-4); }

.config-summary {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.config-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.config-row__label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.config-row__value {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

</style>
