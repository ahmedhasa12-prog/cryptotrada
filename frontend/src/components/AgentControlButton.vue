<template>
  <div class="agent-btn" :class="stateClass">
    <span class="agent-icon">{{ icon }}</span>
    <span class="agent-name">{{ displayName }}</span>
    <span class="agent-status-dot" :class="stateClass"></span>
    
    <div class="agent-actions">
      <!-- Start button -->
      <button
        v-if="agent.state === 'stopped' || agent.state === 'error'"
        class="agent-action-btn"
        @click="$emit('action', { agentType: agent.agent_type, action: 'start' })"
        :title="t('agents.start')"
      >
        ▶
      </button>
      
      <!-- Pause button -->
      <button
        v-else-if="agent.state === 'running'"
        class="agent-action-btn"
        @click="$emit('action', { agentType: agent.agent_type, action: 'pause' })"
        :title="t('agents.pause')"
      >
        ⏸
      </button>
      
      <!-- Resume button -->
      <button
        v-else-if="agent.state === 'paused'"
        class="agent-action-btn"
        @click="$emit('action', { agentType: agent.agent_type, action: 'resume' })"
        :title="t('agents.resume')"
      >
        ▶
      </button>
      
      <!-- Stop button (always available when not stopped) -->
      <button
        v-if="agent.state !== 'stopped' && agent.state !== 'error'"
        class="agent-action-btn"
        @click="$emit('action', { agentType: agent.agent_type, action: 'stop' })"
        :title="t('agents.stop')"
      >
        ■
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  agent: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits(['action'])

const iconMap = {
  auto_trend: '📈',
  xrp_swing: '🌊',
  p2p_market: '🤝',
  manual: '👁️',
}

const nameMap = {
  auto_trend: 'agents.auto_trend',
  xrp_swing: 'agents.xrp_swing',
  p2p_market: 'agents.p2p_market',
  manual: 'agents.manual',
}

const icon = computed(() => iconMap[props.agent.agent_type] || '🤖')
const displayName = computed(() => t(nameMap[props.agent.agent_type] || props.agent.agent_type))

const stateClass = computed(() => {
  const state = props.agent.state
  if (state === 'running') return 'running'
  if (state === 'paused') return 'paused'
  if (state === 'error') return 'error'
  return 'stopped'
})
</script>

<style scoped>
/* Styles are in App.vue for global access */
</style>