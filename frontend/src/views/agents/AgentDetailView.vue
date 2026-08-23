<template>
  <div class="agent-detail-view">
    <div class="agent-detail-header">
      <div class="agent-detail-identity">
        <span class="agent-detail-icon">{{ agentIcon }}</span>
        <div>
          <h1>{{ displayName }}</h1>
          <div class="agent-detail-state" :class="stateClass">
            <span class="agent-detail-dot" aria-hidden="true"></span>
            <span>{{ stateLabel }}</span>
          </div>
        </div>
      </div>

      <div class="agent-detail-actions">
        <button
          v-if="agent.state === 'stopped' || agent.state === 'error'"
          class="btn btn-success"
          @click="onAction('start')"
          :disabled="loading"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
          {{ t('agents.start') }}
        </button>

        <button
          v-else-if="agent.state === 'running'"
          class="btn btn-warning"
          @click="onAction('pause')"
          :disabled="loading"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
            <rect x="6" y="4" width="4" height="16"></rect>
            <rect x="14" y="4" width="4" height="16"></rect>
          </svg>
          {{ t('agents.pause') }}
        </button>

        <button
          v-else-if="agent.state === 'paused'"
          class="btn btn-success"
          @click="onAction('resume')"
          :disabled="loading"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
            <polygon points="5 3 19 12 5 21 5 3"></polygon>
          </svg>
          {{ t('agents.resume') }}
        </button>

        <button
          v-if="agent.state !== 'stopped' && agent.state !== 'error'"
          class="btn btn-danger"
          @click="onAction('stop')"
          :disabled="loading"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="2"></rect>
          </svg>
          {{ t('agents.stop') }}
        </button>

        <button
          v-if="agent.state !== 'stopped' && agent.state !== 'error'"
          class="btn btn-ghost"
          @click="refreshStatus"
          :disabled="loading"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
            <polyline points="1 4 1 10 7 10"></polyline>
            <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
          </svg>
          {{ t('agents.refresh') }}
        </button>
      </div>
    </div>

    <!-- Metrics Bar -->
    <div class="agent-detail-metrics" v-if="agent.metrics">
      <div class="metric-item">
        <span class="metric-value">{{ formatMetric(agent.metrics.cycles_completed) }}</span>
        <span class="metric-label">{{ t('agents.cycles') }}</span>
      </div>
      <div class="metric-item">
        <span class="metric-value">{{ formatMetric(agent.metrics.fast_cycles_completed) }}</span>
        <span class="metric-label">{{ t('agents.fast_cycles') }}</span>
      </div>
      <div class="metric-item">
        <span class="metric-value" :class="pnlClass">{{ formatPnL(agent.metrics.total_pnl_usd || 0) }}</span>
        <span class="metric-label">{{ t('agents.total_pnl') }}</span>
      </div>
      <div class="metric-item">
        <span class="metric-value">{{ agent.metrics.total_entries || 0 }}</span>
        <span class="metric-label">{{ t('agents.total_entries') }}</span>
      </div>
      <div class="metric-item">
        <span class="metric-value">{{ agent.metrics.total_exits || 0 }}</span>
        <span class="metric-label">{{ t('agents.total_exits') }}</span>
      </div>
      <div class="metric-item">
        <span class="metric-value">{{ formatUptime(agent.metrics.uptime_started_at) }}</span>
        <span class="metric-label">{{ t('agents.uptime') }}</span>
      </div>
    </div>

    <!-- Error Banner -->
    <div v-if="agent.error_message" class="agent-detail-error">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
      <span>{{ agent.error_message }}</span>
    </div>

    <!-- Tab Navigation -->
    <div class="agent-detail-tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="['tab', { active: activeTab === tab.id }]"
        :aria-selected="activeTab === tab.id"
        :aria-controls="`panel-${tab.id}`"
        :id="`tab-${tab.id}`"
        role="tab"
        @click="activeTab = tab.id"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Tab Panels -->
    <div class="agent-detail-panels">
      <div
        v-for="tab in tabs"
        :key="tab.id"
        :id="`panel-${tab.id}`"
        role="tabpanel"
        :aria-labelledby="`tab-${tab.id}`"
        :hidden="activeTab !== tab.id"
        class="tab-panel"
      >
        <component :is="tab.component" :agent="agent" :agent-type="agentType" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { usePlatformStore } from '@/stores/platform'
import AutoTrendOverview from '@/components/agent/AutoTrendOverview.vue'
import AutoTrendPositions from '@/components/agent/AutoTrendPositions.vue'
import XRPSwingOverview from '@/components/agent/XRPSwingOverview.vue'
import P2PMarketOverview from '@/components/agent/P2PMarketOverview.vue'
import ManualOverview from '@/components/agent/ManualOverview.vue'

// Stub for tabs that reference components not yet built
const ComingSoon = { template: '<div class="coming-soon" style="padding:2rem;color:var(--color-text-secondary,#888);text-align:center;">Coming soon</div>' }

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const platformStore = usePlatformStore()

// URL param is hyphenated (auto-trend); API uses underscores (auto_trend)
const agentType = computed(() => (route.params.type as string).replace(/-/g, '_'))
const activeTab = ref('overview')
const loading = ref(false)
const agent = ref(null)

const tabs = computed(() => {
  const baseTabs = [
    { id: 'overview', label: t('agents.overview'), component: getOverviewComponent() },
    { id: 'config', label: t('agents.config'), component: getConfigComponent() },
  ]

  const specificTabs = getSpecificTabs()
  return [...specificTabs, ...baseTabs]
})

function getOverviewComponent() {
  switch (agentType.value) {
    case 'auto_trend': return AutoTrendOverview
    case 'xrp_swing': return XRPSwingOverview
    case 'p2p_market': return P2PMarketOverview
    case 'manual': return ManualOverview
    default: return ComingSoon
  }
}

function getConfigComponent() {
  return ComingSoon
}

function getSpecificTabs() {
  switch (agentType.value) {
    case 'auto_trend':
      return [
        { id: 'positions', label: t('agents.positions'), component: AutoTrendPositions },
        { id: 'signals', label: t('agents.signals'), component: ComingSoon },
        { id: 'history', label: t('agents.history'), component: ComingSoon },
      ]
    case 'xrp_swing':
      return [
        { id: 'trade_monitor', label: t('agents.trade_monitor'), component: ComingSoon },
        { id: 'setup', label: t('agents.setup_analysis'), component: ComingSoon },
        { id: 'history', label: t('agents.history'), component: ComingSoon },
      ]
    case 'p2p_market':
      return [
        { id: 'snapshot', label: t('agents.snapshot'), component: ComingSoon },
        { id: 'analytics', label: t('agents.analytics'), component: ComingSoon },
      ]
    case 'manual':
      return [
        { id: 'insights', label: t('agents.insights'), component: ComingSoon },
        { id: 'watchlist', label: t('agents.watchlist'), component: ComingSoon },
      ]
    default:
      return []
  }
}

const agentIcon = computed(() => {
  const icons: Record<string, string> = {
    auto_trend: '📈',
    xrp_swing: '🌊',
    p2p_market: '🤝',
    manual: '👁️',
  }
  return icons[agentType.value] || '🤖'
})

const displayName = computed(() => {
  const names: Record<string, string> = {
    auto_trend: 'Auto Trend',
    xrp_swing: 'XRP Swing',
    p2p_market: 'P2P Market',
    manual: 'Manual',
  }
  return names[agentType.value] || agentType.value
})

const stateClass = computed(() => `agent-detail--${agent.value?.state || 'stopped'}`)
const stateLabel = computed(() => {
  const labels: Record<string, string> = {
    running: t('agents.running'),
    paused: t('agents.paused'),
    stopped: t('agents.stopped'),
    error: t('agents.error'),
    starting: t('agents.starting'),
    stopping: t('agents.stopping'),
  }
  return labels[agent.value?.state] || agent.value?.state
})

const pnlClass = computed(() => {
  const pnl = agent.value?.metrics?.total_pnl_usd || 0
  return pnl >= 0 ? 'positive' : 'negative'
})

async function fetchAgentStatus() {
  loading.value = true
  try {
    await platformStore.fetchAgentsStatus()
    const found = platformStore.agents.find(a => a.agent_type === agentType.value)
    if (found) {
      agent.value = found
    }
  } catch (e) {
    console.error('Failed to fetch agent status:', e)
  } finally {
    loading.value = false
  }
}

async function onAction(action: 'start' | 'stop' | 'pause' | 'resume') {
  loading.value = true
  try {
    await platformStore.agentAction(agentType.value, action)
    await fetchAgentStatus()
  } catch (e) {
    console.error(`Failed to ${action} agent:`, e)
  } finally {
    loading.value = false
  }
}

async function refreshStatus() {
  await fetchAgentStatus()
}

function formatMetric(value: number): string {
  if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M'
  if (value >= 1000) return (value / 1000).toFixed(1) + 'K'
  return value.toString()
}

function formatPnL(value: number): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function formatUptime(startedAt: string | null): string {
  if (!startedAt) return '—'
  const diff = Date.now() - new Date(startedAt).getTime()
  if (diff < 60000) return `${Math.floor(diff / 1000)}s`
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`
  return `${Math.floor(diff / 86400000)}d`
}

let _interval: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await fetchAgentStatus()
  _interval = setInterval(fetchAgentStatus, 30000)
})

onUnmounted(() => {
  if (_interval) clearInterval(_interval)
})

watch(() => route.params.type, async () => {
  await fetchAgentStatus()
})
</script>

<style scoped>
.agent-detail-view {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-6);
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

/* Header */
.agent-detail-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-6);
  padding: var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  flex-wrap: wrap;
}

.agent-detail-identity {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  flex: 1;
  min-width: 0;
}

.agent-detail-icon {
  font-size: var(--text-4xl);
  width: 72px;
  height: 72px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-surface-raised);
  border-radius: var(--radius-xl);
  flex-shrink: 0.
}

.agent-detail-identity h1 {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.agent-detail-state {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-pill);
}

.agent-detail-dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  flex-shrink: 0.
}

.agent-detail--running .agent-detail-state {
  background: var(--color-agent-running-bg);
  color: var(--color-agent-running);
  border: 1px solid var(--color-agent-running-border);
}

.agent-detail--running .agent-detail-dot {
  background: var(--color-agent-running);
  box-shadow: 0 0 8px var(--color-agent-running);
  animation: pulse-dot 2s ease-in-out infinite;
}

.agent-detail--paused .agent-detail-state {
  background: var(--color-agent-paused-bg);
  color: var(--color-agent-paused);
  border: 1px solid var(--color-agent-paused-border);
}

.agent-detail--paused .agent-detail-dot {
  background: var(--color-agent-paused);
}

.agent-detail--stopped .agent-detail-state {
  background: var(--color-agent-stopped-bg);
  color: var(--color-agent-stopped);
  border: 1px solid var(--color-agent-stopped-border);
}

.agent-detail--stopped .agent-detail-dot {
  background: var(--color-agent-stopped);
}

.agent-detail--error .agent-detail-state {
  background: var(--color-agent-error-bg);
  color: var(--color-agent-error);
  border: 1px solid var(--color-agent-error-border);
}

.agent-detail--error .agent-detail-dot {
  background: var(--color-agent-error);
  animation: pulse-dot 1.5s ease-in-out infinite;
}

.agent-detail--starting .agent-detail-state {
  background: var(--color-agent-starting-bg);
  color: var(--color-brand);
  border: 1px solid var(--color-brand);
}

.agent-detail--starting .agent-detail-dot {
  background: var(--color-brand);
  animation: pulse-dot 1s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(0.9); }
}

.agent-detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  flex-shrink: 0.
}

/* Metrics Bar */
.agent-detail-metrics {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
  padding: var(--space-4) var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
}

@media (min-width: 640px) {
  .agent-detail-metrics {
    grid-template-columns: repeat(3, 1fr);
  }
}

@media (min-width: 1024px) {
  .agent-detail-metrics {
    grid-template-columns: repeat(6, 1fr);
  }
}

.metric-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-3);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  text-align: center;
}

.metric-item:hover {
  border-color: var(--color-brand);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.metric-value {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
  line-height: var(--line-height-tight);
}

.metric-value.positive { color: var(--color-success); }
.metric-value.negative { color: var(--color-danger); }

.metric-label {
  font-size: var(--text-2xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

/* Error Banner */
.agent-detail-error {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-6);
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-border);
  border-radius: var(--radius-lg);
  color: var(--color-danger);
  font-size: var(--text-sm);
  animation: slide-down var(--transition-base) ease-out;
}

@keyframes slide-down {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Tabs */
.agent-detail-tabs {
  display: flex;
  gap: var(--space-1);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-1);
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.tab {
  padding: var(--space-2) var(--space-4);
  background: none;
  border: none;
  border-radius: var(--radius-lg);
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  cursor: pointer;
  transition: all var(--transition-fast);
  white-space: nowrap;
}

.tab:hover {
  color: var(--color-text-secondary);
  background: var(--color-surface-hover);
}

.tab.active {
  color: var(--color-brand-strong);
  background: var(--color-brand-subtle);
}

.tab:focus-visible {
  outline: 2px solid var(--color-brand);
  outline-offset: 2px;
}

/* Panels */
.agent-detail-panels {
  padding: var(--space-6) 0 0;
}

.tab-panel {
  animation: fade-in var(--transition-base) ease-out;
}

@keyframes fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Responsive */
@media (max-width: 639px) {
  .agent-detail-header {
    flex-direction: column;
    align-items: stretch;
  }
  
  .agent-detail-actions {
    width: 100%;
  }
  
  .agent-detail-actions .btn {
    flex: 1;
  }
  
  .agent-detail-metrics {
    grid-template-columns: repeat(2, 1fr);
  }
}

/* RTL support */
:global([dir="rtl"]) .agent-detail-identity {
  flex-direction: row-reverse;
}

:global([dir="rtl"]) .agent-detail-actions {
  flex-direction: row-reverse;
}
</style>