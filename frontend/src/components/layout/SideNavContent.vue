<template>
  <ul class="sidenav-list" role="list">
    <!-- Dashboard -->
    <li class="sidenav-item">
      <router-link
        to="/"
        class="sidenav-link"
        :class="{ active: isActive('/') }"
        @click="$emit('navigate')"
      >
        <span class="sidenav-link__icon" aria-hidden="true">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="7" height="7" rx="1"></rect>
            <rect x="14" y="3" width="7" height="7" rx="1"></rect>
            <rect x="3" y="14" width="7" height="7" rx="1"></rect>
            <rect x="14" y="14" width="7" height="7" rx="1"></rect>
          </svg>
        </span>
        <span v-show="!collapsed" class="sidenav-link__text">{{ t('navigation.dashboard') }}</span>
      </router-link>
    </li>

    <!-- Agents Section -->
    <li class="sidenav-section" v-show="!collapsed">
      <span class="sidenav-section__label">{{ t('navigation.agents') }}</span>
    </li>

    <li class="sidenav-item" v-for="agent in agents" :key="agent.agent_type">
      <router-link
        :to="`/agents/${agent.agent_type.replace(/_/g, '-')}`"
        class="sidenav-link"
        :class="{
          active: isActive(`/agents/${agent.agent_type.replace(/_/g, '-')}`),
          'sidenav-link--agent': true,
        }"
        @click="$emit('navigate')"
      >
        <span class="sidenav-link__icon" aria-hidden="true">{{ agentIcon(agent.agent_type) }}</span>
        <span v-show="!collapsed" class="sidenav-link__text">{{ agentName(agent.agent_type) }}</span>
        <span
          v-show="!collapsed"
          class="sidenav-link__badge"
          :class="agentStateClass(agent.state)"
        >
          {{ agentStateLabel(agent.state) }}
        </span>
      </router-link>
    </li>

    <!-- Divider -->
    <li class="sidenav-divider" v-show="!collapsed"></li>

    <!-- P2P Market -->
    <li class="sidenav-item">
      <router-link
        to="/p2p"
        class="sidenav-link"
        :class="{ active: isActive('/p2p') }"
        @click="$emit('navigate')"
      >
        <span class="sidenav-link__icon" aria-hidden="true">🤝</span>
        <span v-show="!collapsed" class="sidenav-link__text">{{ t('navigation.p2p_market') }}</span>
      </router-link>
    </li>

    <!-- Intelligence -->
    <li class="sidenav-item">
      <router-link
        to="/intel"
        class="sidenav-link"
        :class="{ active: isActive('/intel') }"
        @click="$emit('navigate')"
      >
        <span class="sidenav-link__icon" aria-hidden="true">🧠</span>
        <span v-show="!collapsed" class="sidenav-link__text">{{ t('navigation.intelligence') }}</span>
      </router-link>
    </li>

    <!-- Journal -->
    <li class="sidenav-item">
      <router-link
        to="/journal"
        class="sidenav-link"
        :class="{ active: isActive('/journal') }"
        @click="$emit('navigate')"
      >
        <span class="sidenav-link__icon" aria-hidden="true">📓</span>
        <span v-show="!collapsed" class="sidenav-link__text">{{ t('navigation.journal') }}</span>
      </router-link>
    </li>

    <!-- Divider -->
    <li class="sidenav-divider" v-show="!collapsed"></li>

    <!-- Settings -->
    <li class="sidenav-item">
      <router-link
        to="/settings"
        class="sidenav-link"
        :class="{ active: isActive('/settings') }"
        @click="$emit('navigate')"
      >
        <span class="sidenav-link__icon" aria-hidden="true">⚙️</span>
        <span v-show="!collapsed" class="sidenav-link__text">{{ t('navigation.settings') }}</span>
      </router-link>
    </li>
  </ul>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '@/stores/platform'

const { t } = useI18n()
const route = useRoute()
const platformStore = usePlatformStore()

const props = defineProps<{
  collapsed: boolean
}>()

const emit = defineEmits<{
  navigate: []
}>()

const agents = computed(() => platformStore.agents)

function isActive(path: string): boolean {
  return route.path === path || route.path.startsWith(path + '/')
}

function agentIcon(type: string): string {
  const icons: Record<string, string> = {
    auto_trend: '📈',
    xrp_swing: '🌊',
    p2p_market: '🤝',
    manual: '👁️',
  }
  return icons[type] || '🤖'
}

function agentName(type: string): string {
  const names: Record<string, string> = {
    auto_trend: 'Auto Trend',
    xrp_swing: 'XRP Swing',
    p2p_market: 'P2P Market',
    manual: 'Manual',
  }
  return names[type] || type
}

function agentStateClass(state: string): string {
  return `sidenav-badge--${state}`
}

function agentStateLabel(state: string): string {
  const labels: Record<string, string> = {
    running: 'Running',
    paused: 'Paused',
    stopped: 'Stopped',
    error: 'Error',
    starting: 'Starting...',
    stopping: 'Stopping...',
  }
  return labels[state] || state
}
</script>

<style scoped>
.sidenav-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.sidenav-item {
  position: relative;
}

.sidenav-section {
  padding: var(--space-3) var(--space-3) var(--space-1);
}

.sidenav-section__label {
  font-size: var(--text-2xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidenav-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-lg);
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: all var(--transition-fast);
  position: relative;
  min-height: 44px;
}

.sidenav-link:hover {
  background: var(--color-surface-hover);
  color: var(--color-text);
}

.sidenav-link:focus-visible {
  outline: 2px solid var(--color-brand);
  outline-offset: -2px;
}

.sidenav-link.active {
  background: var(--color-brand-subtle);
  color: var(--color-brand-strong);
}

.sidenav-link.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 24px;
  background: var(--color-brand);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}

.sidenav-link__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  font-size: var(--text-lg);
  color: inherit;
  transition: color var(--transition-fast);
}

.sidenav-link__text {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
  transition: opacity var(--transition-fast), width var(--transition-fast);
}

.sidenav-link__badge {
  font-size: var(--text-2xs);
  font-weight: var(--font-bold);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
  flex-shrink: 0;
}

.sidenav-badge--running {
  background: var(--color-agent-running-bg);
  color: var(--color-agent-running);
  border: 1px solid var(--color-agent-running-border);
}

.sidenav-badge--paused {
  background: var(--color-agent-paused-bg);
  color: var(--color-agent-paused);
  border: 1px solid var(--color-agent-paused-border);
}

.sidenav-badge--stopped {
  background: var(--color-agent-stopped-bg);
  color: var(--color-agent-stopped);
  border: 1px solid var(--color-agent-stopped-border);
}

.sidenav-badge--error {
  background: var(--color-agent-error-bg);
  color: var(--color-agent-error);
  border: 1px solid var(--color-agent-error-border);
}

.sidenav-badge--starting {
  background: var(--color-agent-starting-bg);
  color: var(--color-brand);
  border: 1px solid var(--color-brand);
}

.sidenav-badge--stopping {
  background: var(--color-agent-stopped-bg);
  color: var(--color-agent-stopped);
  border: 1px solid var(--color-agent-stopped-border);
}

.sidenav-divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-3) var(--space-2);
}

/* Collapsed state */
.sidenav--collapsed .sidenav-link {
  justify-content: center;
  padding: var(--space-2);
}

.sidenav--collapsed .sidenav-link__text,
.sidenav--collapsed .sidenav-link__badge,
.sidenav--collapsed .sidenav-section,
.sidenav--collapsed .sidenav-divider {
  display: none;
}

.sidenav--collapsed .sidenav-link.active::before {
  display: none;
}

.sidenav--collapsed .sidenav-link__icon {
  width: 28px;
  height: 28px;
  font-size: var(--text-xl);
}

/* RTL support */
[dir="rtl"] .sidenav-link.active::before {
  left: auto;
  right: 0;
  border-radius: var(--radius-sm) 0 0 var(--radius-sm);
}
</style>