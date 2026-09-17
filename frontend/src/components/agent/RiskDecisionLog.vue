<template>
  <div class="risk-log">
    <div class="risk-log__intro">
      <p>{{ t('risk_log.subtitle') }}</p>
    </div>

    <Spinner v-if="loading" :label="t('common.loading')" />

    <EmptyState v-else-if="!decisions.length" :message="t('risk_log.empty')" />

    <div v-else class="risk-log__list">
      <div v-for="d in decisions" :key="d.id" class="decision" :class="d.approved ? 'decision--approved' : 'decision--refused'">
        <div class="decision__header">
          <Badge :variant="d.approved ? 'success' : 'danger'" dot>
            {{ d.approved ? t('risk_log.approved') : t('risk_log.refused') }}
          </Badge>
          <span v-if="d.setup_type" class="decision__setup">{{ t('risk_log.setup') }} {{ d.setup_type }}</span>
          <span class="decision__time">{{ formatRelativeTime(d.decided_at) }}</span>
        </div>

        <p v-if="!d.approved && d.veto_reason_explain" class="decision__veto-explain">
          {{ d.veto_reason_explain }}
        </p>

        <div class="decision__terms">
          <MetricTile size="sm" :label="t('risk_log.entry')" :value="d.entry_price != null ? formatPrice(d.entry_price) : '—'" />
          <MetricTile size="sm" :label="t('risk_log.size')" :value="d.requested_size_usd != null ? '$' + d.requested_size_usd.toFixed(0) : '—'" />
          <MetricTile size="sm" :label="t('risk_log.stop')" :value="d.stop != null ? formatPrice(d.stop) : '—'" />
          <MetricTile size="sm" :label="t('risk_log.reward_risk')" :value="d.rr_ratio != null ? d.rr_ratio.toFixed(2) : '—'" />
        </div>

        <details class="decision__checks">
          <summary>{{ t('risk_log.checks') }} ({{ passCount(d) }}/{{ d.checks.length }})</summary>
          <ul>
            <li v-for="c in d.checks" :key="c.gate" :class="c.passed ? 'check--pass' : 'check--fail'">
              <span class="check__icon" aria-hidden="true">{{ c.passed ? '✓' : '✕' }}</span>
              <div class="check__body">
                <span class="check__name">{{ gateLabel(c.gate) }}</span>
                <span v-if="c.detail" class="check__detail">{{ c.detail }}</span>
                <span v-if="!c.passed && c.reason_explain" class="check__explain">{{ c.reason_explain }}</span>
              </div>
            </li>
          </ul>
        </details>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import axios from 'axios'
import Badge from '@/components/ui/Badge.vue'
import MetricTile from '@/components/ui/MetricTile.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import Spinner from '@/components/ui/Spinner.vue'
import { formatRelativeTime, formatPrice } from '@/composables/useFormatters'

const { t } = useI18n()
const API = import.meta.env.VITE_API_BASE || ''

const decisions = ref<any[]>([])
const loading = ref(true)

const GATE_LABELS: Record<string, string> = {
  no_duplicate_position: 'No duplicate position',
  not_in_cooldown: 'Not in cooldown',
  setup_not_already_consumed: 'Fresh setup',
  evaluation_is_fresh: 'Evaluation is recent',
  verdict_is_entry_ready: 'Verdict is Entry Ready',
  live_price_available: 'Live price available',
  reward_risk_sufficient: 'Reward:risk is sufficient',
}

function gateLabel(gate: string): string {
  return GATE_LABELS[gate] || gate.replace(/_/g, ' ')
}

function passCount(d: any): number {
  return d.checks.filter((c: any) => c.passed).length
}

async function load() {
  loading.value = true
  try {
    const { data } = await axios.get(`${API}/api/xrp-swing/risk-decisions?limit=30`)
    decisions.value = data.decisions ?? []
  } catch (e) {
    console.error('Failed to fetch risk decisions:', e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.risk-log { display: flex; flex-direction: column; gap: var(--space-4); }
.risk-log__intro p { font-size: var(--text-sm); color: var(--color-text-secondary); margin: 0; line-height: var(--line-height-relaxed); }

.risk-log__list { display: flex; flex-direction: column; gap: var(--space-3); }

.decision {
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-inline-start: 3px solid transparent;
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.decision--approved { border-inline-start-color: var(--color-success); }
.decision--refused { border-inline-start-color: var(--color-danger); }

.decision__header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.decision__setup {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.decision__time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  margin-inline-start: auto;
}

.decision__veto-explain {
  font-size: var(--text-sm);
  color: var(--color-danger);
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  margin: 0;
  line-height: var(--line-height-relaxed);
}

.decision__terms {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-2);
}

@media (min-width: 480px) {
  .decision__terms { grid-template-columns: repeat(4, 1fr); }
}

.decision__checks summary {
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  font-weight: var(--font-medium);
  user-select: none;
}

.decision__checks ul {
  list-style: none;
  margin: var(--space-3) 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.decision__checks li {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.check__icon { flex-shrink: 0; font-weight: var(--font-bold); width: 1.2em; text-align: center; }
.check--pass .check__icon { color: var(--color-success); }
.check--fail .check__icon { color: var(--color-danger); }

.check__body { display: flex; flex-direction: column; gap: 0.1rem; min-width: 0; }
.check__name { color: var(--color-text); font-weight: var(--font-medium); }
.check__detail { color: var(--color-text-tertiary); font-size: var(--text-xs); }
.check__explain { color: var(--color-text-secondary); font-size: var(--text-xs); line-height: var(--line-height-relaxed); }
</style>
