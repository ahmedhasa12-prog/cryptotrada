<template>
  <div
    class="agent-card"
    :class="[
      'agent-card--' + agent.agent_type,
      stateClass,
      clickable ? 'agent-card--clickable' : ''
    ]"
    @click="clickable && $emit('click')"
    @keydown.enter="clickable && $emit('click')"
    @keydown.space.prevent="clickable && $emit('click')"
    tabindex="0"
    role="button"
    :aria-label="ariaLabel"
  >
    <!-- Header -->
    <div class="agent-card__header">
      <div class="agent-card__identity">
        <span class="agent-card__icon" aria-hidden="true">{{ icon }}</span>
        <div class="agent-card__info">
          <h3 class="agent-card__name">{{ displayName }}</h3>
          <div class="agent-card__state" :class="stateClass">
            <span class="agent-card__dot" aria-hidden="true"></span>
            <span>{{ stateLabel(agent.state) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Divider -->
    <div class="agent-card__divider"></div>

    <!-- Main Metrics -->
    <div class="agent-card__metrics" v-if="showMetrics && agent.metrics">
      <div class="metric-row">
        <MetricTile :label="t('agents.total_pnl')" :value="formatPnL(agent.metrics.total_pnl_usd || 0)" variant="auto" />
        <MetricTile :label="t('agents.total_entries')" :value="agent.metrics.total_entries || 0" />
        <MetricTile :label="t('agents.total_exits')" :value="agent.metrics.total_exits || 0" />
        <MetricTile :label="t('agents.uptime')" :value="formatUptime(agent.metrics.uptime_started_at)" />
      </div>
    </div>

    <!-- Error message -->
    <div v-if="agent.error_message" class="agent-card__error">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      <span>{{ agent.error_message }}</span>
    </div>

    <!-- Actions -->
    <div class="agent-card__actions" v-if="showActions && !loading">
      <button
        v-if="agent.state === 'stopped' || agent.state === 'error'"
        class="btn btn-success btn-sm"
        @click.stop="$emit('action', { agentType: agent.agent_type, action: 'start' })"
        :disabled="loading"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        {{ t('agents.start') }}
      </button>

      <button
        v-else-if="agent.state === 'running'"
        class="btn btn-warning btn-sm"
        @click.stop="$emit('action', { agentType: agent.agent_type, action: 'pause' })"
        :disabled="loading"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
          <rect x="6" y="4" width="4" height="16"></rect>
          <rect x="14" y="4" width="4" height="16"></rect>
        </svg>
        {{ t('agents.pause') }}
      </button>

      <button
        v-else-if="agent.state === 'paused'"
        class="btn btn-success btn-sm"
        @click.stop="$emit('action', { agentType: agent.agent_type, action: 'resume' })"
        :disabled="loading"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
        {{ t('agents.resume') }}
      </button>

      <button
        v-if="agent.state !== 'stopped' && agent.state !== 'error'"
        class="btn btn-danger btn-sm"
        @click.stop="$emit('action', { agentType: agent.agent_type, action: 'stop' })"
        :disabled="loading"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
          <rect x="3" y="3" width="18" height="18" rx="2"></rect>
        </svg>
        {{ t('agents.stop') }}
      </button>

      <button
        v-if="agent.state !== 'stopped' && agent.state !== 'error'"
        class="btn btn-ghost btn-sm"
        @click="$emit('click')"
        :disabled="loading"
      >
        {{ t('agents.view_details') }}
      </button>
    </div>

    <!-- Backtest & Strategy Metrics -->
    <div class="agent-card__backtest" v-if="agent.config?.config?.strategy_owner || agent.metrics?.backtest_win_rate !== undefined">
      <div class="metric-row metric-row--backtest">
        <div class="backtest-tag" :class="agent.config?.config?.strategy_owner ? 'backtest-tag--original' : 'backtest-tag--adopt'">
          {{ agent.config?.config?.strategy_owner ? (agent.config.config.strategy_owner.includes('original') ? 'ORIGINAL' : 'ADOPTED') : 'NEW' }}
        </div>
        <div v-if="agent.metrics?.backtest_win_rate !== undefined" class="backtest-stat">
          <span class="label">Win Rate</span>
          <span class="value" :class="agent.metrics.backtest_win_rate >= 0.5 ? 'positive' : 'negative'">
            {{ (agent.metrics.backtest_win_rate * 100).toFixed(0) }}%
          </span>
        </div>
        <div v-if="agent.metrics?.profit_factor !== undefined" class="backtest-stat">
          <span class="label">PF</span>
          <span class="value">{{ agent.metrics.profit_factor.toFixed(2) }}</span>
        </div>
        <div class="backtest-tag backtest-tag--real">
          <span>REAL DATA ONLY</span>
        </div>
      </div>
    </div>

    <!-- Loading overlay -->
    <div v-if="loading" class="agent-card__loading">
      <div class="spinner" aria-hidden="true"></div>
      <span>{{ t('agents.loading') }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAgentMeta } from '@/composables/useAgentMeta'
import { formatPnL, formatUptime } from '@/composables/useFormatters'
import MetricTile from '@/components/ui/MetricTile.vue'

const { t } = useI18n()
const { agentIcon, agentDisplayName, stateLabel } = useAgentMeta()

interface AgentMetrics {
  cycles_completed: number
  fast_cycles_completed: number
  last_cycle_at: string | null
  last_fast_cycle_at: string | null
  last_error: string | null
  last_error_at: string | null
  total_actions: number
  total_entries: number
  total_exits: number
  total_pnl_usd: number
  uptime_started_at: string | null
}

interface AgentConfig {
  main_cycle_interval_sec: number
  fast_cycle_interval_sec: number
  config: Record<string, any>
}

interface AgentStatus {
  agent_type: string
  state: 'stopped' | 'starting' | 'running' | 'paused' | 'stopping' | 'error'
  enabled: boolean
  config: AgentConfig
  metrics: AgentMetrics
  error_message: string | null
}

interface Props {
  agent: AgentStatus
  showMetrics?: boolean
  showActions?: boolean
  clickable?: boolean
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  showMetrics: true,
  showActions: true,
  clickable: true,
  loading: false,
})

const emit = defineEmits<{
  click: []
  action: [{ agentType: string; action: 'start' | 'stop' | 'pause' | 'resume' }]
}>()

const icon = computed(() => agentIcon(props.agent.agent_type))
const displayName = computed(() => agentDisplayName(props.agent.agent_type))
const stateClass = computed(() => `agent-card--${props.agent.state}`)
const ariaLabel = computed(() => `${displayName.value}, ${stateLabel(props.agent.state)}`)
</script>

<style scoped>
.agent-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: all var(--transition-base);
  position: relative;
}

.agent-card--clickable {
  cursor: pointer;
}

.agent-card--clickable:hover {
  border-color: var(--color-brand);
  box-shadow: var(--shadow-md);
}

/* State variants */
.agent-card--running {
  border-color: var(--color-agent-running-border);
}

.agent-card--running::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--color-agent-running), var(--color-success-strong));
}

.agent-card--paused {
  border-color: var(--color-agent-paused-border);
}

.agent-card--paused::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--color-agent-paused);
}

.agent-card--stopped {
  border-color: var(--color-agent-stopped-border);
  opacity: 0.8;
}

.agent-card--error {
  border-color: var(--color-agent-error-border);
}

.agent-card--error::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--color-agent-error);
}

.agent-card--starting::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: var(--color-brand);
  animation: shimmer 1.5s ease-in-out infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

/* Header */
.agent-card__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.agent-card__identity {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  flex: 1;
  min-width: 0;
}

.agent-card__icon {
  font-size: var(--text-2xl);
  flex-shrink: 0;
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-raised);
  border-radius: var(--radius-lg);
}

.agent-card__info {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  min-width: 0;
}

.agent-card__name {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.agent-card__state {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  width: fit-content;
}

.agent-card__dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
}

.agent-card__state.agent-card--running {
  background: var(--color-agent-running-bg);
  color: var(--color-agent-running);
  border: 1px solid var(--color-agent-running-border);
}

.agent-card__state.agent-card--running .agent-card__dot {
  background: var(--color-agent-running);
  box-shadow: 0 0 6px var(--color-agent-running);
  animation: pulse-dot 2s ease-in-out infinite;
}

.agent-card__state.agent-card--paused {
  background: var(--color-agent-paused-bg);
  color: var(--color-agent-paused);
  border: 1px solid var(--color-agent-paused-border);
}

.agent-card__state.agent-card--paused .agent-card__dot {
  background: var(--color-agent-paused);
}

.agent-card__state.agent-card--stopped {
  background: var(--color-agent-stopped-bg);
  color: var(--color-agent-stopped);
  border: 1px solid var(--color-agent-stopped-border);
}

.agent-card__state.agent-card--stopped .agent-card__dot {
  background: var(--color-agent-stopped);
}

.agent-card__state.agent-card--error {
  background: var(--color-agent-error-bg);
  color: var(--color-agent-error);
  border: 1px solid var(--color-agent-error-border);
}

.agent-card__state.agent-card--error .agent-card__dot {
  background: var(--color-agent-error);
  animation: pulse-dot 1.5s ease-in-out infinite;
}

.agent-card__state.agent-card--starting {
  background: var(--color-agent-starting-bg);
  color: var(--color-brand);
  border: 1px solid var(--color-brand);
}

.agent-card__state.agent-card--starting .agent-card__dot {
  background: var(--color-brand);
  animation: pulse-dot 1s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.9); }
}

/* Divider */
.agent-card__divider {
  height: 1px;
  background: var(--color-border);
  margin: 0 var(--space-4);
}

/* Metrics */
.agent-card__metrics {
  padding: var(--space-4) var(--space-5);
  flex: 1;
}

.metric-row {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-3);
}

@media (min-width: 640px) {
  .metric-row {
    grid-template-columns: repeat(4, 1fr);
  }
}


/* Error */
.agent-card__error {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-4);
  background: var(--color-danger-bg);
  border-top: 1px solid var(--color-danger-border);
  border-bottom: 1px solid var(--color-danger-border);
  color: var(--color-danger);
  font-size: var(--text-sm);
  animation: slide-down var(--transition-base) ease-out;
}

@keyframes slide-down {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Actions */
.agent-card__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-5);
  border-top: 1px solid var(--color-border);
  background: var(--color-surface-raised);
}

.agent-card__actions .btn {
  flex: 1;
  min-width: 100px;
  justify-content: center;
}

@media (max-width: 480px) {
  .agent-card__actions .btn {
    flex: 1 1 calc(50% - var(--space-1));
  }
  
  .agent-card__actions .btn:last-child {
    flex: 1 1 100%;
  }
}

/* Backtest & Strategy Tags */
.agent-card__backtest {
  padding: var(--space-2) var(--space-4);
  border-top: 1px dashed var(--color-border);
  background: linear-gradient(90deg, rgba(16, 185, 129, 0.05), rgba(244, 63, 94, 0.05));
}

.metric-row--backtest {
  grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
  gap: var(--space-2);
  align-items: center;
  font-family: var(--font-mono);
  font-size: var(--text-2xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.backtest-tag {
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  font-weight: var(--font-bold);
  font-size: var(--text-2xs);
}

.backtest-tag--original {
  background: var(--color-brand-subtle);
  color: var(--color-brand-strong);
  border: 1px solid var(--color-brand);
}

.backtest-tag--adopt {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border: 1px solid #3b82f6;
}

.backtest-tag--real {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid #10b981;
  white-space: nowrap;
}

.backtest-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.backtest-stat .label {
  color: var(--color-text-secondary);
  font-size: 9px;
}

.backtest-stat .value {
  font-weight: var(--font-bold);
  font-size: 12px;
}

.backtest-stat .value.positive { color: #10b981; }
.backtest-stat .value.negative { color: #f43f5e; }

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

/* Loading */
.agent-card__loading {
  position: absolute;
  inset: 0;
  background: rgba(10, 13, 20, 0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  z-index: 10;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.agent-card__loading .spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-brand);
  border-radius: var(--radius-full);
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

</style>