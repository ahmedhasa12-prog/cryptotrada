<template>
  <header class="app-header" :style="{ height: headerHeight + 'px' }" ref="headerRef">
    <div class="header-left">
      <!-- Hamburger menu for mobile -->
      <button
        class="btn btn-icon btn-ghost header-hamburger"
        @click="toggleSideNav"
        :aria-label="t('header.menu')"
        :aria-expanded="mobileDrawerOpen"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="3" y1="6" x2="21" y2="6"></line>
          <line x1="3" y1="12" x2="21" y2="12"></line>
          <line x1="3" y1="18" x2="21" y2="18"></line>
        </svg>
      </button>

      <!-- Logo -->
      <router-link to="/" class="header-logo" aria-label="CryptoTrada Dashboard">
        <span class="logo-icon">📈</span>
        <span class="logo-text">CryptoTrada</span>
      </router-link>
    </div>

    <div class="header-center">
      <!-- Agent Quick Bar -->
      <div class="agent-quick-bar" role="group" :aria-label="t('agents.title')">
        <AgentStatusPill
          v-for="agent in agents"
          :key="agent.agent_type"
          :agent="agent"
          size="sm"
          clickable
          @click="navigateToAgent(agent.agent_type)"
        />
      </div>
    </div>

    <div class="header-right">
      <!-- Platform status indicator -->
      <div class="header-status" :title="t('status.availability')">
        <span class="connection-dot" :class="{ connected: availability === 'online' }"></span>
        <span class="status-text" v-show="!isMobile">{{ availabilityLabel }}</span>
      </div>

      <!-- Theme toggle -->
      <button
        class="btn btn-icon btn-ghost"
        @click="toggleTheme"
        :aria-label="theme === 'dark' ? t('header.light_mode') : t('header.dark_mode')"
        :title="theme === 'dark' ? t('header.light_mode') : t('header.dark_mode')"
      >
        <svg v-if="theme === 'dark'" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="5"></circle>
          <line x1="12" y1="1" x2="12" y2="3"></line>
          <line x1="12" y1="21" x2="12" y2="23"></line>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
          <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
          <line x1="1" y1="12" x2="3" y2="12"></line>
          <line x1="21" y1="12" x2="23" y2="12"></line>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
          <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        </svg>
        <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>
      </button>

      <!-- Language toggle -->
      <button
        class="btn btn-icon btn-ghost header-lang-btn"
        @click="toggleLang"
        :aria-label="t('header.lang')"
        :title="t('header.lang')"
      >
        <span class="lang-text">{{ locale === 'ar' ? 'EN' : 'عربي' }}</span>
      </button>

      <!-- Notifications -->
      <div class="header-notifications" ref="notificationsRef">
        <button
          class="btn btn-icon btn-ghost relative"
          @click="toggleNotifications"
          :aria-label="t('alerts.title')"
          :aria-expanded="notificationsOpen"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
            <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
          </svg>
          <span v-if="unreadAlerts > 0" class="notification-badge">{{ unreadAlerts > 9 ? '9+' : unreadAlerts }}</span>
        </button>

        <!-- Notifications dropdown -->
        <Transition name="fade-slide">
          <div v-if="notificationsOpen" class="notifications-dropdown" role="menu">
            <div class="notifications-header">
              <h3>{{ t('alerts.title') }}</h3>
              <button class="btn btn-ghost btn-sm" @click="clearAllAlerts">{{ t('alerts.clear') }}</button>
            </div>
            <div class="notifications-list" v-if="alerts.length > 0">
              <div
                v-for="alert in alerts"
                :key="alert.id"
                class="notification-item"
                :class="`alert-${alert.level}`"
                role="menuitem"
              >
                <span class="notification-icon">{{ alertIcon(alert.level) }}</span>
                <div class="notification-content">
                  <p class="notification-message">{{ alert.message }}</p>
                  <span class="notification-time">{{ formatTime(alert.timestamp) }}</span>
                </div>
                <button class="btn btn-ghost btn-icon btn-sm" @click="dismissAlert(alert.id)" aria-label="Dismiss">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>
            </div>
            <div v-else class="notifications-empty">
              {{ t('alerts.empty') }}
            </div>
          </div>
        </Transition>
      </div>

      <!-- Mute toggle -->
      <button
        class="btn btn-icon btn-ghost"
        @click="toggleMute"
        :aria-label="muted ? t('alerts.unmute') : t('alerts.mute')"
        :title="muted ? t('alerts.unmute') : t('alerts.mute')"
        :class="{ muted }"
      >
        <svg v-if="!muted" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
        </svg>
        <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"></path>
          <line x1="1" y1="1" x2="23" y2="23"></line>
        </svg>
      </button>
    </div>
  </header>

  <!-- Mobile drawer backdrop -->
  <Transition name="fade">
    <div
      v-if="mobileDrawerOpen"
      class="drawer-backdrop"
      @click="closeMobileDrawer"
      aria-hidden="true"
    ></div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '@/stores/platform'
import { useUIStore } from '@/stores/ui'
import { useTheme } from '@/composables/useTheme'
import AgentStatusPill from '@/components/agent/AgentStatusPill.vue'

const { t, locale } = useI18n()
const router = useRouter()
const platformStore = usePlatformStore()
const uiStore = useUIStore()
const { theme, toggleTheme } = useTheme()

// Refs
const headerRef = ref<HTMLElement | null>(null)
const notificationsRef = ref<HTMLElement | null>(null)

// State
const notificationsOpen = ref(false)
const headerHeight = ref(56)

// Computed
const agents = computed(() => platformStore.agents)
const availability = computed(() => platformStore.availability)
const availabilityLabel = computed(() => platformStore.availabilityLabel)
const alerts = computed(() => platformStore.alerts)
const unreadAlerts = computed(() => alerts.value.filter(a => !a.dismissed).length)
const muted = computed(() => platformStore.muted)
const mobileDrawerOpen = computed(() => uiStore.mobileDrawerOpen)
const isMobile = computed(() => uiStore.isMobile)

// Methods
function toggleSideNav() {
  uiStore.toggleSideNav()
}

function closeMobileDrawer() {
  uiStore.closeSideNav()
}

function navigateToAgent(agentType: string) {
  router.push(`/agents/${agentType.replace(/_/g, '-')}`)
  if (isMobile.value) {
    closeMobileDrawer()
  }
}

function toggleNotifications() {
  notificationsOpen.value = !notificationsOpen.value
}

function dismissAlert(id: number) {
  platformStore.dismissAlert(id)
}

function clearAllAlerts() {
  platformStore.alerts.forEach(a => platformStore.dismissAlert(a.id))
}

function toggleMute() {
  platformStore.toggleMute()
}

async function toggleLang() {
  const newLocale = locale.value === 'ar' ? 'en' : 'ar'
  const { setLocale } = await import('@/i18n.js')
  setLocale(newLocale)
}

function formatTime(iso: string) {
  const date = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  
  if (diff < 60000) return `${Math.floor(diff / 1000)}s`
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`
  return date.toLocaleDateString()
}

function alertIcon(level: string) {
  const icons: Record<string, string> = {
    info: 'ℹ️',
    warning: '⚠️',
    critical: '🚨',
    success: '✅',
  }
  return icons[level] || '🔔'
}

// Close notifications when clicking outside
function handleClickOutside(event: MouseEvent) {
  if (notificationsRef.value && !notificationsRef.value.contains(event.target as Node)) {
    notificationsOpen.value = false
  }
}

// Keyboard navigation
function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') {
    notificationsOpen.value = false
    if (mobileDrawerOpen.value) {
      closeMobileDrawer()
    }
  }
}

// Lifecycle
onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  document.addEventListener('keydown', handleKeydown)
  
  // Measure header height
  if (headerRef.value) {
    headerHeight.value = headerRef.value.offsetHeight
  }
  
  // Watch for header height changes
  const resizeObserver = new ResizeObserver(() => {
    if (headerRef.value) {
      headerHeight.value = headerRef.value.offsetHeight
    }
  })
  if (headerRef.value) {
    resizeObserver.observe(headerRef.value)
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: var(--z-sticky);
  background: var(--color-surface);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--space-4);
  gap: var(--space-4);
  transition: all var(--transition-base);
}

.app-header::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, var(--color-surface) 0%, var(--color-bg-elevated) 100%);
  z-index: -1;
}

/* Left section */
.header-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.header-hamburger {
  display: none;
}

@media (max-width: 1023px) {
  .header-hamburger {
    display: flex;
  }
}

.header-logo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  text-decoration: none;
  color: var(--color-text-primary);
  font-weight: var(--font-bold);
  font-size: var(--text-lg);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}

.header-logo:hover {
  background: var(--color-surface-hover);
}

.logo-icon {
  font-size: var(--text-xl);
}

.logo-text {
  display: none;
}

@media (min-width: 640px) {
  .logo-text {
    display: block;
  }
}

/* Center section - Agent Quick Bar */
.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  min-width: 0;
}

.agent-quick-bar {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
  justify-content: center;
  max-width: 100%;
}

@media (max-width: 767px) {
  .agent-quick-bar {
    gap: var(--space-1);
  }
}

/* Right section */
.header-right {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  flex-shrink: 0;
}

.header-status {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

@media (max-width: 639px) {
  .status-text {
    display: none;
  }
}

.header-lang-btn {
  min-width: 44px;
}

.lang-text {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Notifications */
.header-notifications {
  position: relative;
}

.notifications-dropdown {
  position: absolute;
  top: calc(100% + var(--space-2));
  right: 0;
  width: 360px;
  max-width: calc(100vw - var(--space-4));
  background: var(--color-surface-overlay);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-xl);
  z-index: var(--z-popover);
  overflow: hidden;
  animation: slide-down var(--transition-base) ease-out;
}

@media (max-width: 480px) {
  .notifications-dropdown {
    right: -var(--space-4);
    width: calc(100vw - var(--space-8));
  }
}

.notifications-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-surface-raised);
}

.notifications-header h3 {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.notifications-list {
  max-height: 400px;
  overflow-y: auto;
  padding: var(--space-2);
}

.notification-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3);
  border-radius: var(--radius-lg);
  transition: background var(--transition-fast);
  cursor: pointer;
}

.notification-item:hover {
  background: var(--color-surface-hover);
}

.notification-icon {
  flex-shrink: 0;
  font-size: var(--text-base);
  margin-top: 2px;
}

.notification-content {
  flex: 1;
  min-width: 0;
}

.notification-message {
  font-size: var(--text-sm);
  color: var(--color-text);
  line-height: var(--line-height-normal);
  margin: 0 0 var(--space-1);
}

.notification-time {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
}

.notification-item.alert-critical {
  background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-border);
}

.notification-item.alert-warning {
  background: var(--color-warning-bg);
  border: 1px solid var(--color-warning-border);
}

.notification-item.alert-info {
  background: var(--color-info-bg);
  border: 1px solid var(--color-info-border);
}

.notification-item.alert-success {
  background: var(--color-success-bg);
  border: 1px solid var(--color-success-border);
}

.notifications-empty {
  padding: var(--space-8) var(--space-4);
  text-align: center;
  color: var(--color-text-tertiary);
  font-size: var(--text-sm);
}

/* Mute button */
.btn.muted {
  color: var(--color-danger);
}

.btn.muted:hover {
  background: var(--color-danger-bg);
  color: var(--color-danger-strong);
}

/* Drawer backdrop */
.drawer-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  z-index: calc(var(--z-modal) - 1);
  animation: fade-in var(--transition-base) ease-out;
}

/* Animations */
@keyframes slide-down {
  from {
    opacity: 0;
    transform: translateY(-8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: all var(--transition-base);
}

.fade-slide-enter-from {
  opacity: 0;
  transform: translateY(-8px);
}

.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* RTL support */
:global([dir="rtl"]) .header-left {
  flex-direction: row-reverse;
}

:global([dir="rtl"]) .header-right {
  flex-direction: row-reverse;
}

:global([dir="rtl"]) .notifications-dropdown {
  right: auto;
  left: 0;
}

:global([dir="rtl"]) .drawer-backdrop {
  /* Handled by logical properties */
}
</style>