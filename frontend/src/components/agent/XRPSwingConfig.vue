<template>
  <div class="xrp-config">
    <AgentConfigSummary :agent="agent" />

    <Card :title="t('agents.auto_bot')">
      <Spinner v-if="loading" :label="t('common.loading')" />
      <div v-else-if="status" class="config-summary">
        <div class="config-row">
          <span class="config-row__label">{{ t('agents.auto_status') }}</span>
          <Badge :variant="status.enabled ? 'success' : 'neutral'">
            {{ status.enabled ? t('agents.enabled') : t('agents.disabled') }}
          </Badge>
        </div>
        <div class="config-row">
          <span class="config-row__label">{{ t('agents.auto_size') }}</span>
          <span class="config-row__value">${{ status.auto_size_usd }}</span>
        </div>
        <div class="config-row" v-if="status.cooldown_until">
          <span class="config-row__label">{{ t('agents.cooldown_until') }}</span>
          <span class="config-row__value">{{ formatRelativeTime(status.cooldown_until) }}</span>
        </div>
        <div class="config-row" v-if="status.auto_stage">
          <span class="config-row__label">{{ t('agents.stage_progress') }}</span>
          <span class="config-row__value">{{ status.auto_stage }} / 3</span>
        </div>
        <div class="config-row">
          <span class="config-row__label">{{ t('agents.last_action') }}</span>
          <span class="config-row__value">{{ status.last_action || '—' }}</span>
        </div>
      </div>

      <p class="persists-note">{{ t('agents.persists_note') }}</p>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'
import Card from '@/components/ui/Card.vue'
import Badge from '@/components/ui/Badge.vue'
import Spinner from '@/components/ui/Spinner.vue'
import AgentConfigSummary from '@/components/agent/AgentConfigSummary.vue'
import { formatRelativeTime } from '@/composables/useFormatters'

defineProps<{ agent?: any }>()
const { t } = useI18n()
const API = import.meta.env.VITE_API_BASE || ''

const status = ref<any>(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const { data } = await axios.get(`${API}/api/xrp-swing/auto-status`)
    status.value = data
  } catch (e) {
    console.error('Failed to fetch XRP auto-status:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.xrp-config { display: flex; flex-direction: column; gap: var(--space-4); }

.config-summary {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
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

.persists-note {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin: 0;
  line-height: var(--line-height-relaxed);
}
</style>
