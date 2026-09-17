<template>
  <div class="toast-container" role="region" aria-label="Notifications" aria-live="polite">
    <TransitionGroup name="toast" tag="div" class="toast-list">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast"
        :class="`toast--${toast.type}`"
        role="alert"
        :aria-live="toast.type === 'danger' ? 'assertive' : 'polite'"
      >
        <div class="toast__icon" aria-hidden="true">
          <component :is="iconComponent(toast.type)" />
        </div>
        <div class="toast__content">
          <div class="toast__title">{{ toast.title }}</div>
          <div v-if="toast.message" class="toast__message">{{ toast.message }}</div>
        </div>
        <button
          class="toast__close"
          @click="removeToast(toast.id)"
          :aria-label="t('toast.dismiss')"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
        <div class="toast__progress" :style="{ width: progressStyle(toast) }"></div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useUIStore } from '@/stores/ui'

const { t } = useI18n()
const uiStore = useUIStore()

const toasts = computed(() => uiStore.toasts)

function removeToast(id: number) {
  uiStore.removeToast(id)
}

// Plain objects with a `template` string need Vue's runtime compiler, which
// this Vite build doesn't ship (SFCs are precompiled) — h() renders directly.
const TOAST_ICON_ATTRS = { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 2.5 }

const TOAST_ICON_RENDERERS: Record<string, () => any> = {
  success: () => h('svg', TOAST_ICON_ATTRS, [h('polyline', { points: '20 6 9 17 4 12' })]),
  warning: () => h('svg', TOAST_ICON_ATTRS, [
    h('path', { d: 'M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z' }),
    h('line', { x1: 12, y1: 9, x2: 12, y2: 13 }),
    h('line', { x1: 12, y1: 17, x2: 12.01, y2: 17 }),
  ]),
  danger: () => h('svg', TOAST_ICON_ATTRS, [
    h('circle', { cx: 12, cy: 12, r: 10 }),
    h('line', { x1: 15, y1: 9, x2: 9, y2: 15 }),
    h('line', { x1: 9, y1: 9, x2: 15, y2: 15 }),
  ]),
  info: () => h('svg', TOAST_ICON_ATTRS, [
    h('circle', { cx: 12, cy: 12, r: 10 }),
    h('line', { x1: 12, y1: 16, x2: 12, y2: 12 }),
    h('line', { x1: 12, y1: 8, x2: 12.01, y2: 8 }),
  ]),
}

function iconComponent(type: string) {
  return { render: TOAST_ICON_RENDERERS[type] || TOAST_ICON_RENDERERS.info }
}

function progressStyle(toast: any) {
  // This would be animated via CSS
  return '100%'
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  bottom: var(--space-6);
  right: var(--space-6);
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  pointer-events: none;
  max-width: 420px;
  width: 100%;
}

@media (max-width: 640px) {
  .toast-container {
    left: var(--space-4);
    right: var(--space-4);
    bottom: var(--space-4);
    max-width: none;
  }
}

.toast-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  width: 100%;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-surface-overlay);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xl);
  min-width: 280px;
  max-width: 420px;
  pointer-events: auto;
  position: relative;
  overflow: hidden;
  animation: toast-in var(--transition-base) ease-out;
}

.toast.removing {
  animation: toast-out var(--transition-base) ease-in forwards;
}

@keyframes toast-in {
  from {
    opacity: 0;
    transform: translateX(100%);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes toast-out {
  from {
    opacity: 1;
    transform: translateX(0);
  }
  to {
    opacity: 0;
    transform: translateX(100%);
  }
}

/* Toast types */
.toast--success {
  border-left: 3px solid var(--color-success);
}

.toast--warning {
  border-left: 3px solid var(--color-warning);
}

.toast--danger {
  border-left: 3px solid var(--color-danger);
}

.toast--info {
  border-left: 3px solid var(--color-info);
}

/* Toast icon */
.toast__icon {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  margin-top: 2px;
}

.toast--success .toast__icon { color: var(--color-success); }
.toast--warning .toast__icon { color: var(--color-warning); }
.toast--danger .toast__icon { color: var(--color-danger); }
.toast--info .toast__icon { color: var(--color-info); }

/* Toast content */
.toast__content {
  flex: 1;
  min-width: 0;
}

.toast__title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-1);
  line-height: var(--line-height-tight);
}

.toast__message {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  line-height: var(--line-height-normal);
}

/* Toast close */
.toast__close {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: none;
  border: none;
  color: var(--color-text-tertiary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
  margin-top: -4px;
  margin-right: -4px;
}

.toast__close:hover {
  color: var(--color-text);
  background: var(--color-surface-raised);
}

.toast__close:focus-visible {
  outline: 2px solid var(--color-brand);
  outline-offset: 2px;
}

/* Toast progress bar */
.toast__progress {
  position: absolute;
  bottom: 0;
  left: 0;
  height: 3px;
  background: currentColor;
  opacity: 0.3;
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
  transform-origin: left;
  animation: toast-progress linear forwards;
}

.toast--success .toast__progress { color: var(--color-success); }
.toast--warning .toast__progress { color: var(--color-warning); }
.toast--danger .toast__progress { color: var(--color-danger); }
.toast--info .toast__progress { color: var(--color-info); }

@keyframes toast-progress {
  from { transform: scaleX(1); }
  to { transform: scaleX(0); }
}

/* RTL support */
[dir="rtl"] .toast-container {
  right: auto;
  left: var(--space-6);
}

@media (max-width: 640px) {
  [dir="rtl"] .toast-container {
    left: var(--space-4);
    right: var(--space-4);
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .toast,
  .toast__progress {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
</style>