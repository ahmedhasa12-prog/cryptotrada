<template>
  <div
    class="agent-pill"
    :class="[
      'agent-pill--' + size,
      stateClass,
      clickable ? 'agent-pill--clickable' : '',
      loading ? 'agent-pill--loading' : ''
    ]"
    :title="tooltipText"
    @click="clickable && $emit('click')"
    role="button"
    tabindex="0"
    @keydown.enter="clickable && $emit('click')"
    @keydown.space.prevent="clickable && $emit('click')"
  >
    <!-- Icon -->
    <span class="agent-pill__icon" :aria-hidden="true">{{ icon }}</span>

    <!-- Name (hidden on sm) -->
    <span class="agent-pill__name" v-if="size !== 'sm'">{{ displayName }}</span>

    <!-- Status dot -->
    <span class="agent-pill__dot" :class="stateClass" aria-hidden="true"></span>

    <!-- Badge for running agents (md/lg only) -->
    <span
      v-if="size !== 'sm' && agent.state === 'running' && showMetrics"
      class="agent-pill__badge"
    >
      {{ formatMetric(agent.metrics?.total_actions || 0) }}
    </span>

    <!-- Loading spinner -->
    <span v-if="loading" class="agent-pill__spinner">
      <svg class="spinner" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
        <circle cx="12" cy="12" r="10" stroke-opacity="0.25"></circle>
        <path stroke-opacity="1" d="M12 2a10 10 0 0 1 10 10">
          <animateTransform attributeName="transform" type="rotate" dur="1s" from="0 12 12" to="360 12 12" repeatCount="indefinite"></animateTransform>
        </path>
      </svg>
    </span>

    <!-- Action buttons (lg only) -->
    <div v-if="size === 'lg' && showActions && !loading" class="agent-pill__actions">
      <button
        v-if="agent.state === 'stopped' || agent.state === 'error'"
        class="btn btn-icon btn-success btn-sm"
        @click.stop="$emit('action', { agentType: agent.agent_type, action: 'start' })"
        :aria-label="t('agents.start')"
        :title="t('agents.start')"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
      </button>

      <button
        v-else-if="agent.state === 'running'"
        class="btn btn-icon btn-warning btn-sm"
        @click.stop="$emit('action', { agentType: agent.agent_type, action: 'pause' })"
        :aria-label="t('agents.pause')"
        :title="t('agents.pause')"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <rect x="6" y="4" width="4" height="16"></rect>
          <rect x="14" y="4" width="4" height="16"></rect>
        </svg>
      </button>

      <button
        v-else-if="agent.state === 'paused'"
        class="btn btn-icon btn-success btn-sm"
        @click.stop="$emit('action', { agentType: agent.agent_type, action: 'resume' })"
        :aria-label="t('agents.resume')"
        :title="t('agents.resume')"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polygon points="5 3 19 12 5 21 5 3"></polygon>
        </svg>
      </button>

      <button
        v-if="agent.state !== 'stopped' && agent.state !== 'error'"
        class="btn btn-icon btn-danger btn-sm"
        @click.stop="$emit('action', { agentType: agent.agent_type, action: 'stop' })"
        :aria-label="t('agents.stop')"
        :title="t('agents.stop')"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <rect x="3" y="3" width="18" height="18" rx="2"></rect>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

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
  size: 'sm' | 'md' | 'lg'
  showMetrics?: boolean
  showActions?: boolean
  clickable?: boolean
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  size: 'md',
  showMetrics: false,
  showActions: false,
  clickable: false,
  loading: false,
})

const emit = defineEmits<{
  click: []
  action: [{ agentType: string; action: 'start' | 'stop' | 'pause' | 'resume' }]
}>()

const iconMap: Record<string, string> = {
  auto_trend: '📈',
  xrp_swing: '🌊',
  p2p_market: '🤝',
  manual: '👁️',
}

const nameMap: Record<string, string> = {
  auto_trend: 'Auto Trend',
  xrp_swing: 'XRP Swing',
  p2p_market: 'P2P Market',
  manual: 'Manual',
}

const icon = computed(() => iconMap[props.agent.agent_type] || '🤖')
const displayName = computed(() => nameMap[props.agent.agent_type] || props.agent.agent_type)

const stateClass = computed(() => {
  const state = props.agent.state
  return `agent-pill--${state}`
})

const tooltipText = computed(() => {
  const agent = props.agent
  const parts = [
    `${displayName.value}: ${t(`agents.${state.value}`)}`,
  ]
  
  if (props.showMetrics && agent.metrics) {
    parts.push(`${t('agents.cycles')}: ${agent.metrics.cycles_completed}`)
    parts.push(`${t('agents.fast_cycles')}: ${agent.metrics.fast_cycles_completed}`)
    if (agent.metrics.total_actions > 0) {
      parts.push(`${t('agents.total_actions')}: ${agent.metrics.total_actions}`)
    }
  }
  
  if (agent.error_message) {
    parts.push(`${t('agents.error')}: ${agent.error_message}`)
  }
  
  return parts.join('\n')
})

const state = computed(() => {
  const stateMap: Record<string, string> = {
    running: 'running',
    paused: 'paused',
    stopped: 'stopped',
    error: 'error',
    starting: 'starting',
    stopping: 'stopping',
  }
  return stateMap[props.agent.state] || 'stopped'
})

function formatMetric(value: number): string {
  if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M'
  if (value >= 1000) return (value / 1000).toFixed(1) + 'K'
  return value.toString()
}
</script>

<style scoped>
.agent-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  cursor: default;
  transition: all var(--transition-fast);
  white-space: nowrap;
  position: relative;
}

.agent-pill--sm {
  padding: var(--space-1) var(--space-2);
  gap: var(--space-1);
}

.agent-pill--lg {
  padding: var(--space-2) var(--space-4);
  gap: var(--space-3);
}

.agent-pill--clickable {
  cursor: pointer;
}

.agent-pill--clickable:hover {
  border-color: var(--color-brand);
  color: var(--color-brand-strong);
  background: var(--color-brand-subtle);
}

.agent-pill--clickable:focus-visible {
  outline: 2px solid var(--color-brand);
  outline-offset: 2px;
}

/* Icon */
.agent-pill__icon {
  font-size: var(--text-base);
  flex-shrink: 0;
}

.agent-pill--sm .agent-pill__icon {
  font-size: var(--text-sm);
}

.agent-pill--lg .agent-pill__icon {
  font-size: var(--text-lg);
}

/* Name */
.agent-pill__name {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.agent-pill--lg .agent-pill__name {
  font-size: var(--text-base);
}

/* Status dot */
.agent-pill__dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  flex-shrink: 0;
  transition: all var(--transition-base);
}

.agent-pill--sm .agent-pill__dot {
  width: 6px;
  height: 6px;
}

.agent-pill--lg .agent-pill__dot {
  width: 10px;
  height: 10px;
}

/* State variants */
.agent-pill--running {
  background: var(--color-agent-running-bg);
  border-color: var(--color-agent-running-border);
  color: var(--color-agent-running);
}

.agent-pill--running .agent-pill__dot {
  background: var(--color-agent-running);
  box-shadow: 0 0 8px var(--color-agent-running);
  animation: pulse-dot 2s ease-in-out infinite;
}

.agent-pill--paused {
  background: var(--color-agent-paused-bg);
  border-color: var(--color-agent-paused-border);
  color: var(--color-agent-paused);
}

.agent-pill--paused .agent-pill__dot {
  background: var(--color-agent-paused);
  box-shadow: 0 0 8px var(--color-agent-paused);
}

.agent-pill--stopped {
  background: var(--color-agent-stopped-bg);
  border-color: var(--color-agent-stopped-border);
  color: var(--color-agent-stopped);
}

.agent-pill--stopped .agent-pill__dot {
  background: var(--color-agent-stopped);
}

.agent-pill--error {
  background: var(--color-agent-error-bg);
  border-color: var(--color-agent-error-border);
  color: var(--color-agent-error);
}

.agent-pill--error .agent-pill__dot {
  background: var(--color-agent-error);
  box-shadow: 0 0 8px var(--color-agent-error);
  animation: pulse-dot 1.5s ease-in-out infinite;
}

.agent-pill--starting {
  background: var(--color-agent-starting-bg);
  border-color: var(--color-brand);
  color: var(--color-brand);
}

.agent-pill--starting .agent-pill__dot {
  background: var(--color-brand);
  animation: pulse-dot 1s ease-in-out infinite;
}

.agent-pill--stopping {
  background: var(--color-agent-stopped-bg);
  border-color: var(--color-agent-stopped-border);
  color: var(--color-agent-stopped);
}

.agent-pill--stopping .agent-pill__dot {
  background: var(--color-agent-stopped);
  animation: pulse-dot 1s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(0.9);
  }
}

/* Badge */
.agent-pill__badge {
  background: var(--color-brand);
  color: var(--color-text-inverse);
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  padding: 0 var(--space-1);
  border-radius: var(--radius-pill);
  min-width: 20px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

/* Spinner */
.agent-pill__spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-brand);
}

.agent-pill__spinner .spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Actions */
.agent-pill__actions {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  margin-left: var(--space-2);
  padding-left: var(--space-2);
  border-left: 1px solid var(--color-border);
}

.agent-pill__actions .btn {
  opacity: 0.8;
}

.agent-pill__actions .btn:hover {
  opacity: 1;
}

/* Loading state */
.agent-pill--loading {
  pointer-events: none;
  opacity: 0.7;
}

.agent-pill--loading .agent-pill__actions {
  display: none;
}

/* RTL support */
:global([dir="rtl"]) .agent-pill__actions {
  margin-left: 0;
  margin-right: var(--space-2);
  padding-left: 0;
  padding-right: var(--space-2);
  border-left: none;
  border-right: 1px solid var(--color-border);
}
</style>