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

/* ════════════════════════════════════════════════════════════════════════
   MOBILE-FIRST RESPONSIVE STYLES
   ════════════════════════════════════════════════════════════════════════ */

/* --- Base: mobile (< 768px) --- */
@media (max-width: 767px) {
  .app-main {
    margin-left: 0 !important;
    padding-top: calc(var(--header-height) + env(safe-area-inset-top));
    padding-left: var(--space-3);
    padding-right: var(--space-3);
    padding-bottom: env(safe-area-inset-bottom, 0);
  }

  /* Touch-friendly tap targets (min 44x44px) */
  .btn,
  button,
  .router-link-active,
  a {
    min-height: 44px;
    min-width: 44px;
  }

  /* Responsive typography */
  h1 { font-size: 1.25rem; }
  h2 { font-size: 1.1rem; }
  h3 { font-size: 1rem; }
  .text-sm { font-size: 0.8rem; }
  .text-xs { font-size: 0.75rem; }

  /* Cards: single column on mobile */
  .card-grid,
  .dashboard-grid {
    grid-template-columns: 1fr !important;
    gap: var(--space-3) !important;
  }

  /* Agent cards: full width */
  .agent-card {
    width: 100% !important;
    padding: var(--space-3) !important;
  }

  /* Tables: scrollable on mobile */
  table,
  .table-container {
    font-size: 0.8rem;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
  th, td {
    padding: var(--space-2) !important;
  }

  /* Navigation items: taller touch targets */
  .nav-item,
  .sidenav__nav a,
  .side-nav-item {
    padding: var(--space-3) var(--space-4) !important;
    min-height: 48px;
  }

  /* Metric tiles: compact on mobile */
  .metric-tile {
    flex-direction: column;
    align-items: flex-start;
    gap: var(--space-1);
  }
  .metric-tile .metric-value {
    font-size: 1.5rem;
  }

  /* Header: compact */
  .app-header {
    padding: var(--space-2) var(--space-3);
    height: auto;
    min-height: var(--header-height);
  }

  /* Charts: full width */
  .chart-container,
  .canvas-wrapper {
    width: 100% !important;
    min-height: 200px;
  }

  /* Toast: full width on mobile */
  .toast-container {
    left: var(--space-3);
    right: var(--space-3);
    max-width: none !important;
  }

  /* P2P market cards: compact */
  .p2p-card {
    padding: var(--space-2);
    font-size: 0.8rem;
  }

  /* Settings pages */
  .settings-group {
    padding: var(--space-3);
  }

  /* Reduce header padding on mobile */
  .header-title {
    font-size: 1rem;
  }
}

/* --- Tablet (768px - 1023px) --- */
@media (min-width: 768px) and (max-width: 1023px) {
  .app-main {
    margin-left: 72px !important;
    padding-top: calc(var(--header-height) + env(safe-area-inset-top));
    padding-left: var(--space-4);
    padding-right: var(--space-4);
  }

  .card-grid,
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr) !important;
    gap: var(--space-4) !important;
  }

  .btn, button, a {
    min-height: 40px;
  }
}

/* --- Desktop (≥ 1024px) --- */
@media (min-width: 1024px) {
  .app-main {
    margin-left: 260px;
    padding-top: var(--header-height);
    padding-left: var(--space-6);
    padding-right: var(--space-6);
  }
}

/* --- Safe area support for notched devices --- */
@supports (padding: max(0px)) {
  .app-main {
    padding-left: max(var(--space-4), env(safe-area-inset-left));
    padding-right: max(var(--space-4), env(safe-area-inset-right));
    padding-bottom: max(var(--space-4), env(safe-area-inset-bottom));
    padding-top: max(var(--header-height), env(safe-area-inset-top));
  }
}

/* --- High-DPI / Retina display optimization --- */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
  .app {
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
}

/* --- Landscape orientation --- */
@media (orientation: landscape) and (max-height: 500px) {
  .app-main {
    padding-top: var(--space-2);
  }
  .card-grid, .dashboard-grid {
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)) !important;
  }
}

/* ═════════════════════════════════════════════════════════════════════════
   END MOBILE-FIRST RESPONSIVE STYLES
   ════════════════════════════════════════════════════════════════════════ */

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
