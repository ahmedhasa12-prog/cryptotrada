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

    <!-- Agent Cards Grid -->
    <div class="dashboard-grid">
      <AgentCard
        v-for="agent in agents"
        :key="agent.agent_type"
        :agent="agent"
        @action="onAgentAction"
        @click="navigateToAgent(agent.agent_type)"
      />
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

const { t } = useI18n()
const router = useRouter()
const platformStore = usePlatformStore()
const uiStore = useUIStore()

const agents = computed(() => platformStore.agents)
const runningAgentsCount = computed(() => platformStore.runningAgents.length)
const totalAgentsCount = computed(() => agents.value.length)

const recentActivities = ref<Array<any>>([])
const lastUpdateTime = ref('')

const API = import.meta.env.VITE_API_BASE || ''

async function fetchActivities() {
  try {
    const { data } = await axios.get(`${API}/api/agents/activity?limit=10`)
    recentActivities.value = data.activities ?? []
    lastUpdateTime.value = formatRelativeTime(Date.now())
  } catch (e) {
    console.error('Failed to fetch activities:', e)
  }
}

function formatRelativeTime(timestamp: number): string {
  const diff = Date.now() - timestamp
  if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  return new Date(timestamp).toLocaleDateString()
}

function onAgentAction(event: { agentType: string; action: string }) {
  // The AgentCard emits this, we can handle it here if needed
  console.log('Agent action:', event)
}

function navigateToAgent(agentType: string) {
  router.push(`/agents/${agentType.replace(/_/g, '-')}`)
}

let _interval: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  // Agent status is fetched/polled by App.vue so the sidebar's agent list
  // stays populated no matter which page loads first — just read it here.
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

/* Grid */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
}

@media (min-width: 640px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .dashboard-grid {
    grid-template-columns: repeat(4, 1fr);
  }
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
}
</style>