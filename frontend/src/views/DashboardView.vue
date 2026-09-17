<template>
  <div class="dashboard">
    <!-- Global Status Bar -->
    <div class="dashboard-status-bar">
      <div class="status-item">
        <span class="connection-dot" :class="{ connected: platformStore.availability === 'online' }"></span>
        <span>{{ platformStore.availabilityLabel }}</span>
      </div>
      <div class="status-item">
        <span class="agent-count">
          <span class="running">{{ runningAgentsCount }}</span> / {{ totalAgentsCount }} {{ t('dashboard.agents_running') }}
        </span>
      </div>
      <div class="status-item">
        <span class="last-update">{{ t('dashboard.last_update') }} {{ lastUpdateTime }}</span>
      </div>
    </div>

    <!-- TOP ROW: 3 agent cards side-by-side (key data) -->
    <div class="section-label">
      <h2>{{ t('dashboard.agent_overview') }}</h2>
    </div>
    <div class="dashboard-grid-top">
      <AgentCard
        v-for="agent in agents"
        :key="agent.agent_type"
        :agent="agent"
        @action="onAgentAction"
        @click="navigateToAgent(agent.agent_type)"
        :show-metrics="true"
        :show-actions="true"
        :clickable="true"
      />
    </div>

    <!-- BOTTOM ROW: 3 cards stacked vertically -->
    <div class="section-label">
      <h2>{{ t('dashboard.agent_details') }}</h2>
    </div>
    <div class="dashboard-grid-bottom">
      <div v-for="agent in agents" :key="'detail-' + agent.agent_type" class="detail-card">
        <div class="detail-card__header">
          <span class="detail-card__icon">{{ agentIcon(agent.agent_type) }}</span>
          <h3 class="detail-card__name">{{ agentDisplayName(agent.agent_type) }}</h3>
          <span class="detail-card__state" :class="stateClass(agent.state)">
            {{ stateLabel(agent.state) }}
          </span>
        </div>
        <div class="detail-card__body">
          <div class="detail-card__metric">
            <span class="detail-card__label">{{ t('agents.total_pnl') }}</span>
            <span class="detail-card__value">{{ formatPnL(agent.metrics?.total_pnl_usd || 0) }}</span>
          </div>
          <div class="detail-card__metric">
            <span class="detail-card__label">{{ t('agents.total_entries') }}</span>
            <span class="detail-card__value">{{ agent.metrics?.total_entries || 0 }}</span>
          </div>
          <div class="detail-card__metric">
            <span class="detail-card__label">{{ t('agents.total_exits') }}</span>
            <span class="detail-card__value">{{ agent.metrics?.total_exits || 0 }}</span>
          </div>
          <div class="detail-card__metric">
            <span class="detail-card__label">{{ t('agents.uptime') }}</span>
            <span class="detail-card__value">{{ formatUptime(agent.metrics?.uptime_started_at) }}</span>
          </div>
          <div class="detail-card__metric">
            <span class="detail-card__label">{{ t('agents.max_positions') }}</span>
            <span class="detail-card__value">{{ agent.config?.max_positions || 3 }}</span>
          </div>
          <div class="detail-card__metric">
            <span class="detail-card__label">{{ t('agents.interval') }}</span>
            <span class="detail-card__value">{{ (agent.config?.main_cycle_interval_sec || 300) / 60 }}min</span>
          </div>
        </div>
        <div class="detail-card__actions">
          <button
            v-if="agent.state === 'stopped' || agent.state === 'error'"
            class="btn btn-success btn-sm"
            @click.stop="startAgent(agent.agent_type)"
          >{{ t('agents.start') }}</button>
          <button
            v-else-if="agent.state === 'running'"
            class="btn btn-warning btn-sm"
            @click.stop="pauseAgent(agent.agent_type)"
          >{{ t('agents.pause') }}</button>
          <button
            v-else
            class="btn btn-ghost btn-sm"
            @click.stop="navigateToAgent(agent.agent_type)"
          >{{ t('dashboard.details') }}</button>
        </div>
      </div>
    </div>

    <!-- Recent Activity -->
    <div class="dashboard-section">
      <div class="section-header">
        <h2>{{ t('dashboard.recent_activity') }}</h2>
        <router-link to="/agents" class="btn btn-ghost btn-sm">{{ t('dashboard.view_all') }}</router-link>
      </div>
      <ActivityFeed :activities="recentActivities" :limit="10" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import axios from 'axios'
import { usePlatformStore } from '@/stores/platform'
import { useUIStore } from '@/stores/ui'
import AgentCard from '@/components/agent/AgentCard.vue'
import ActivityFeed from '@/components/ui/ActivityFeed.vue'

const TRADING_AGENT_TYPES = ['xrp_swing', 'sol_swing', 'link_swing']
const { t } = useI18n()
const router = useRouter()
const platformStore = usePlatformStore()
const uiStore = useUIStore()

const agents = computed(() => platformStore.tradingAgents)
const runningAgentsCount = computed(() => platformStore.runningAgents.filter(a => TRADING_AGENT_TYPES.includes(a.agent_type)).length)
const totalAgentsCount = computed(() => agents.value.length)

const recentActivities = ref<Array<any>>([])
const lastUpdateTime = ref('')

const API = import.meta.env.VITE_API_BASE || ''

// Helper: agent icon mapping
const agentIconMap: Record<string, string> = {
  'xrp_swing': '💱',
  'sol_swing': '🟣',
  'link_swing': '🔗',
}

function agentIcon(agentType: string): string {
  return agentIconMap[agentType] || '🤖'
}

function agentDisplayName(agentType: string): string {
  const names: Record<string, string> = {
    'xrp_swing': 'XRP Swing',
    'sol_swing': 'SOL Swing',
    'link_swing': 'LINK Swing',
  }
  return names[agentType] || agentType
}

function stateClass(state: string): string {
  const map: Record<string, string> = {
    'running': 'state--running',
    'stopped': 'state--stopped',
    'error': 'state--error',
    'paused': 'state--paused',
  }
  return map[state] || ''
}

function stateLabel(state: string): string {
  const labels: Record<string, string> = {
    'running': 'Running',
    'stopped': 'Stopped',
    'error': 'Error',
    'paused': 'Paused',
  }
  return labels[state] || state
}

function formatUptime(uptimeStart: string | undefined): string {
  if (!uptimeStart) return '—'
  const start = new Date(uptimeStart).getTime()
  const diff = Date.now() - start
  const hours = Math.floor(diff / 3600000)
  const minutes = Math.floor((diff % 3600000) / 60000)
  return `${hours}h ${minutes}m`
}

function formatPnL(pnl: number): string {
  if (pnl >= 0) return `+$${pnl.toFixed(2)}`
  return `-$${Math.abs(pnl).toFixed(2)}`
}

// Agent actions
async function startAgent(agentType: string) {
  try {
    const { data } = await axios.post(`${API}/api/agents/${agentType.replace(/_/g, '-')}/start`)
    if (data.success) fetchActivities()
  } catch (e) {
    console.error('Failed to start agent:', e)
  }
}

async function pauseAgent(agentType: string) {
  try {
    const { data } = await axios.post(`${API}/api/agents/${agentType.replace(/_/g, '-')}/pause`)
    if (data.success) fetchActivities()
  } catch (e) {
    console.error('Failed to pause agent:', e)
  }
}

let _interval: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  await fetchActivities()
  _interval = setInterval(fetchActivities, 30000)
})

onUnmounted(() => {
  if (_interval) clearInterval(_interval)
})
</script>

<style scoped>
.dashboard {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-6);
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

/* Status Bar */
.dashboard-status-bar {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  padding: var(--space-4) var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  flex-wrap: wrap;
}

.status-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.status-item .connection-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-danger);
}

.status-item .connection-dot.connected {
  background: var(--color-success);
  box-shadow: 0 0 8px var(--color-success);
}

.agent-count {
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.agent-count .running {
  color: var(--color-success);
}

.last-update {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

/* Section labels */
.section-label {
  margin-bottom: var(--space-2);
}

.section-label h2 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0;
  padding: var(--space-2) 0;
}

/* TOP ROW: 3 agent cards side-by-side */
.dashboard-grid-top {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

@media (min-width: 640px) {
  .dashboard-grid-top {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .dashboard-grid-top {
    grid-template-columns: repeat(3, 1fr);
  }
}

/* Agent card styling for top row */
.agent-card {
  min-height: 140px;
  padding: var(--space-4);
  cursor: pointer;
  transition: transform var(--transition-fast), box-shadow var(--transition-fast);
}

.agent-card--clickable:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-lg);
}

.agent-card:active {
  transform: scale(0.98);
}

/* BOTTOM ROW: 3 detail cards stacked vertically */
.dashboard-grid-bottom {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-bottom: var(--space-6);
}

@media (min-width: 640px) {
  .dashboard-grid-bottom {
    flex-direction: column;
    gap: var(--space-4);
  }
}

/* Detail card */
.detail-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  overflow: hidden;
  transition: border-color var(--transition-fast);
}

.detail-card:hover {
  border-color: var(--color-brand);
}

.detail-card__header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-brand-subtle);
}

.detail-card__icon {
  font-size: var(--text-xl);
}

.detail-card__name {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0;
  flex: 1;
}

.detail-card__state {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-full);
}

.detail-card__state.state--running {
  background: rgba(34, 197, 94, 0.15);
  color: var(--color-success);
}

.detail-card__state.state--stopped {
  background: rgba(234, 179, 8, 0.15);
  color: var(--color-warning);
}

.detail-card__state.state--error {
  background: rgba(239, 68, 68, 0.15);
  color: var(--color-danger);
}

.detail-card__state.state--paused {
  background: rgba(107, 114, 128, 0.15);
  color: var(--color-text-tertiary);
}

.detail-card__body {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-2);
  padding: var(--space-4);
}

@media (min-width: 640px) {
  .detail-card__body {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .detail-card__body {
    grid-template-columns: repeat(3, 1fr);
  }
}

.detail-card__metric {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.detail-card__label {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.detail-card__value {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.detail-card__actions {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  border-top: 1px solid var(--color-border);
  flex-wrap: wrap;
}

.detail-card__actions .btn {
  min-height: 36px;
}

/* Status Bar */
.dashboard-status-bar {
  display: flex;
  align-items: center;
  gap: var(--space-6);
  padding: var(--space-4) var(--space-6);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  flex-wrap: wrap;
}

.status-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.status-item .connection-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-full);
  background: var(--color-danger);
}

.status-item .connection-dot.connected {
  background: var(--color-success);
  box-shadow: 0 0 8px var(--color-success);
}

.agent-count {
  font-weight: var(--font-semibold);
  color: var(--color-text);
}

.agent-count .running {
  color: var(--color-success);
}

.last-update {
  color: var(--color-text-tertiary);
  font-size: var(--text-xs);
}

/* Section */
.dashboard-section {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  overflow: hidden;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) var(--space-6);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-brand-subtle);
}

.section-header h2 {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

/* Responsive */
@media (max-width: 639px) {
  .dashboard {
    padding: var(--space-4);
  }
  
  .dashboard-status-bar {
    padding: var(--space-3) var(--space-4);
    gap: var(--space-4);
  }

  .detail-card__header {
    padding: var(--space-3);
  }

  .detail-card__body {
    padding: var(--space-3);
  }

  .detail-card__actions {
    padding: var(--space-2) var(--space-3);
  }
}
</style>
