<template>
  <Card :title="t('agents.config')">
    <div class="config-summary">
      <div class="config-row">
        <span class="config-row__label">{{ t('agents.status_label') }}</span>
        <Badge :variant="agent?.enabled ? 'success' : 'neutral'">
          {{ agent?.enabled ? t('agents.enabled') : t('agents.disabled') }}
        </Badge>
      </div>
      <div class="config-row">
        <span class="config-row__label">{{ t('agents.main_cycle_interval') }}</span>
        <span class="config-row__value">{{ agent?.config?.main_cycle_interval_sec ?? '—' }}</span>
      </div>
      <div class="config-row">
        <span class="config-row__label">{{ t('agents.fast_cycle_interval') }}</span>
        <span class="config-row__value">{{ agent?.config?.fast_cycle_interval_sec ?? '—' }}</span>
      </div>
    </div>
    <slot />
  </Card>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'

defineProps<{ agent?: any }>()
const { t } = useI18n()
</script>

<style scoped>
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
