<template>
  <div class="agents-view">
    <div class="agents-header">
      <h1>{{ t('agents.title') }}</h1>
      <div class="agents-actions">
        <button class="btn btn-primary" @click="startAllEnabled" :disabled="allEnabledRunning">
          {{ t('agents.start_all') }}
        </button>
        <button class="btn btn-danger" @click="stopAll" :disabled="allStopped">
          {{ t('agents.stop_all') }}
        </button>
      </div>
    </div>

    <div class="agents-grid">
      <AgentCard
        v-for="agent in agents"
        :key="agent.agent_type"
        :agent="agent"
        :show-metrics="true"
        :show-actions="true"
        :clickable="true"
        @action="onAgentAction"
        @click="navigateToAgent(agent.agent_type)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { usePlatformStore } from '@/stores/platform'
import AgentCard from '@/components/agent/AgentCard.vue'

const { t } = useI18n()
const router = useRouter()
const platformStore = usePlatformStore()

const agents = computed(() => platformStore.agents)
const allEnabledRunning = computed(() => platformStore.runningAgents.length === agents.value.filter(a => a.enabled).length)
const allStopped = computed(() => platformStore.runningAgents.length === 0)

async function onAgentAction(event: { agentType: string; action: string }) {
  await platformStore.agentAction(event.agentType, event.action as any)
  await platformStore.fetchAgentsStatus()
}

async function startAllEnabled() {
  await platformStore.startAllAgents()
}

async function stopAll() {
  await platformStore.stopAllAgents()
}

function navigateToAgent(agentType: string) {
  router.push(`/agents/${agentType.replace(/_/g, '-')}`)
}

onMounted(async () => {
  await platformStore.fetchAgentsStatus()
})
</script>

<style scoped>
.agents-view {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
  padding: var(--space-6);
  max-width: var(--content-max-width);
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

.agents-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.agents-header h1 {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
}

.agents-actions {
  display: flex;
  gap: var(--space-3);
}

.agents-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
}

@media (min-width: 640px) {
  .agents-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .agents-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

@media (max-width: 639px) {
  .agents-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .agents-actions {
    width: 100%;
  }
  
  .agents-actions .btn {
    flex: 1;
  }
}
</style>