<template>
  <!-- Mobile Drawer -->
  <Transition name="drawer">
    <div
      v-if="mobileDrawerOpen"
      class="mobile-drawer"
      :class="{ 'mobile-drawer--open': mobileDrawerOpen }"
      role="dialog"
      aria-modal="true"
      :aria-label="t('navigation.menu')"
    >
      <div class="mobile-drawer__header">
        <router-link to="/" class="mobile-drawer__logo" @click="closeDrawer">
          <span class="logo-icon">📈</span>
          <span class="logo-text">CryptoTrada</span>
        </router-link>
        <button
          class="btn btn-icon btn-ghost"
          @click="closeDrawer"
          :aria-label="t('navigation.close')"
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
      <nav class="mobile-drawer__nav" aria-label="Main navigation">
        <SideNavContent :collapsed="false" @navigate="closeDrawer" />
      </nav>
    </div>
  </Transition>

  <!-- Desktop SideNav -->
  <aside
    v-show="!isMobile"
    class="sidenav"
    :class="{
      'sidenav--collapsed': collapsed,
      'sidenav--open': !collapsed,
    }"
    :style="{ width: sidenavWidth + 'px' }"
    role="navigation"
    :aria-label="t('navigation.menu')"
  >
    <div class="sidenav__header">
      <router-link to="/" class="sidenav__logo" aria-label="CryptoTrada Dashboard">
        <span class="logo-icon">📈</span>
        <span v-show="!collapsed" class="logo-text">CryptoTrada</span>
      </router-link>
      <button
        v-show="!collapsed"
        class="btn btn-icon btn-ghost sidenav__toggle"
        @click="toggleCollapse"
        :aria-label="collapsed ? t('navigation.expand') : t('navigation.collapse')"
        :title="collapsed ? t('navigation.expand') : t('navigation.collapse')"
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline :points="collapsed ? '9 18 15 12 9 6' : '15 18 9 12 15 6'"></polyline>
        </svg>
      </button>
    </div>

    <nav class="sidenav__nav" aria-label="Main navigation">
      <SideNavContent :collapsed="collapsed" />
    </nav>

    <div class="sidenav__footer">
      <div class="sidenav__user" v-show="!collapsed">
        <div class="user-avatar">👤</div>
        <div class="user-info">
          <span class="user-name">Trader</span>
          <span class="user-role">{{ t('navigation.trader') }}</span>
        </div>
      </div>
      <div class="sidenav__version" v-show="!collapsed">
        v4.0.0 — Agent Architecture
      </div>
    </div>
  </aside>

  <!-- Backdrop for tablet -->
  <Transition name="fade">
    <div
      v-if="isTablet && !collapsed"
      class="sidenav-backdrop"
      @click="collapse"
      aria-hidden="true"
    ></div>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUIStore } from '@/stores/ui'
import SideNavContent from './SideNavContent.vue'

const { t } = useI18n()
const uiStore = useUIStore()

// Props would come from parent, but we use store directly
const collapsed = computed(() => uiStore.sideNavCollapsed)
const mobileDrawerOpen = computed(() => uiStore.mobileDrawerOpen)
const isMobile = computed(() => uiStore.isMobile)
const isTablet = computed(() => uiStore.isTablet)
const sidenavWidth = computed(() => uiStore.sideNavWidth)

function toggleCollapse() {
  uiStore.setSideNavCollapsed(!collapsed.value)
}

function collapse() {
  uiStore.setSideNavCollapsed(true)
}

function closeDrawer() {
  uiStore.closeSideNav()
}
</script>

<style scoped>
/* ════════════════════════════════════════════════════════════════════════
   MOBILE DRAWER
   ════════════════════════════════════════════════════════════════════════ */

.mobile-drawer {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 100%;
  max-width: 320px;
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  z-index: var(--z-modal);
  display: flex;
  flex-direction: column;
  transform: translateX(-100%);
  transition: transform var(--transition-base) ease-out;
  box-shadow: var(--shadow-xl);
}

.mobile-drawer--open {
  transform: translateX(0);
}

.mobile-drawer__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.mobile-drawer__logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  text-decoration: none;
  color: var(--color-text-primary);
  font-weight: var(--font-bold);
  font-size: var(--text-lg);
}

.mobile-drawer__nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-4);
}

/* ═════════════════════════════════════════════════════════════════════════
   DESKTOP SIDENAV
   ════════════════════════════════════════════════════════════════════════ */

.sidenav {
  position: fixed;
  top: var(--header-height, 56px);
  left: 0;
  bottom: 0;
  height: calc(100vh - var(--header-height, 56px));
  background: var(--color-surface);
  border-right: 1px solid var(--color-border);
  z-index: var(--z-sticky);
  display: flex;
  flex-direction: column;
  transition: width var(--transition-base) ease-out, transform var(--transition-base) ease-out;
  overflow: hidden;
}

.sidenav--collapsed {
  width: 72px;
}

.sidenav--open {
  width: 260px;
}

.sidenav__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  min-height: var(--header-height);
  flex-shrink: 0;
}

.sidenav__logo {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  text-decoration: none;
  color: var(--color-text-primary);
  font-weight: var(--font-bold);
  font-size: var(--text-lg);
  padding: var(--space-2);
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
  flex: 1;
  min-width: 0;
}

.sidenav__logo:hover {
  background: var(--color-surface-hover);
}

.sidenav__logo:focus-visible {
  outline: 2px solid var(--color-brand);
  outline-offset: 2px;
}

.logo-icon {
  font-size: var(--text-xl);
  flex-shrink: 0;
}

.logo-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  transition: opacity var(--transition-fast), width var(--transition-fast);
}

.sidenav--collapsed .logo-text {
  opacity: 0;
  width: 0;
}

.sidenav__toggle {
  flex-shrink: 0;
  color: var(--color-text-tertiary);
  transition: color var(--transition-fast);
}

.sidenav__toggle:hover {
  color: var(--color-brand-strong);
  background: var(--color-brand-subtle);
}

.sidenav__nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-3) var(--space-2);
}

.sidenav__footer {
  padding: var(--space-4);
  border-top: 1px solid var(--color-border);
  flex-shrink: 0;
}

.sidenav__user {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2);
  border-radius: var(--radius-lg);
  transition: background var(--transition-fast);
}

.sidenav__user:hover {
  background: var(--color-surface-hover);
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  background: var(--color-brand-subtle);
  color: var(--color-brand-strong);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-lg);
  flex-shrink: 0;
}

.user-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  overflow: hidden;
}

.user-name {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: var(--text-xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidenav__version {
  margin-top: var(--space-3);
  font-size: var(--text-2xs);
  color: var(--color-text-tertiary);
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* ═════════════════════════════════════════════════════════════════════════
   BACKDROP
   ════════════════════════════════════════════════════════════════════════ */

.sidenav-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(2px);
  z-index: calc(var(--z-sticky) - 1);
  animation: fade-in var(--transition-base) ease-out;
}

/* ═════════════════════════════════════════════════════════════════════════
   ANIMATIONS
   ════════════════════════════════════════════════════════════════════════ */

.drawer-enter-active,
.drawer-leave-active {
  transition: transform var(--transition-base) ease-out;
}

.drawer-enter-from,
.drawer-leave-to {
  transform: translateX(-100%);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--transition-base);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* ═════════════════════════════════════════════════════════════════════════
   RTL SUPPORT
   ════════════════════════════════════════════════════════════════════════ */

[dir="rtl"] .mobile-drawer {
  left: auto;
  right: 0;
  border-right: none;
  border-left: 1px solid var(--color-border);
}

[dir="rtl"] .mobile-drawer--open {
  transform: translateX(0);
}

[dir="rtl"] .mobile-drawer-enter-from,
[dir="rtl"] .mobile-drawer-leave-to {
  transform: translateX(100%);
}

[dir="rtl"] .sidenav {
  left: auto;
  right: 0;
  border-right: none;
  border-left: 1px solid var(--color-border);
}

[dir="rtl"] .sidenav-backdrop {
  /* Same */
}
</style>