<template>
  <div class="app" :dir="locale === 'ar' ? 'rtl' : 'ltr'">
    <!-- SideNav -->
    <SideNav />

    <!-- App Header -->
    <AppHeader />

    <!-- Main Content -->
    <main class="app-main" :style="{ marginLeft: sidenavMarginLeft }">
      <router-view v-slot="{ Component }">
        <Transition name="page" mode="out-in">
          <component :is="Component" />
        </Transition>
      </router-view>
    </main>

    <!-- Toast Container -->
    <ToastContainer />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useUIStore } from '@/stores/ui'
import { usePlatformStore } from '@/stores/platform'
import { useTheme } from '@/composables/useTheme'
import AppHeader from '@/components/layout/AppHeader.vue'
import SideNav from '@/components/layout/SideNav.vue'
import ToastContainer from '@/components/ui/ToastContainer.vue'

const { locale } = useI18n()
const route = useRoute()
const uiStore = useUIStore()
const platformStore = usePlatformStore()
const { theme } = useTheme()

let _agentsInterval: ReturnType<typeof setInterval> | null = null

onMounted(async () => {
  document.documentElement.setAttribute('data-theme', theme.value)

  // The sidebar's agent list needs this regardless of which page loads
  // first — landing directly on /p2p, /intel, etc. used to leave it empty
  // all session since only Dashboard/Agents/AgentDetail ever fetched it.
  await platformStore.fetchAgentsStatus()
  _agentsInterval = setInterval(() => platformStore.fetchAgentsStatus(), 30000)
})

onUnmounted(() => {
  if (_agentsInterval) clearInterval(_agentsInterval)
})

const sidenavMarginLeft = computed(() => {
  if (uiStore.isMobile) return '0'
  return (uiStore.sideNavCollapsed ? 72 : 260) + 'px'
})
</script>

<style>
/* App root styles */
.app {
  min-height: 100dvh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg);
  color: var(--color-text);
  font-family: var(--font-sans);
  transition: background var(--transition-base), color var(--transition-base);
}

/* Main content area */
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  transition: margin-left var(--transition-base) ease-out;
  padding-top: var(--header-height);
}

/* Page transitions */
.page-enter-active,
.page-leave-active {
  transition: opacity var(--transition-base), transform var(--transition-base);
}

.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* RTL support */
[dir="rtl"] .app-main {
  /* margin-left becomes margin-right in RTL via logical properties */
}

/* Focus visible for the whole app */
:focus-visible {
  outline: 2px solid var(--color-brand);
  outline-offset: 2px;
}

/* Skip link for accessibility */
.skip-link {
  position: absolute;
  top: -100%;
  left: var(--space-4);
  background: var(--color-brand);
  color: var(--color-text-inverse);
  padding: var(--space-2) var(--space-4);
  border-radius: var(--radius-md);
  z-index: var(--z-tooltip);
  transition: top var(--transition-fast);
}

.skip-link:focus {
  top: var(--space-4);
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .app,
  .app-main,
  .page-enter-active,
  .page-leave-active,
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
