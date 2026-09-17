<template>
  <span class="ui-badge" :class="`ui-badge--${variant}`">
    <span v-if="dot" class="ui-badge__dot" aria-hidden="true"></span>
    <slot />
  </span>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  variant?: 'success' | 'danger' | 'warning' | 'brand' | 'neutral'
  dot?: boolean
}>(), {
  variant: 'neutral',
  dot: false,
})
</script>

<style scoped>
.ui-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
}

.ui-badge__dot {
  width: 6px;
  height: 6px;
  border-radius: var(--radius-full);
  background: currentColor;
  flex-shrink: 0;
}

.ui-badge--success {
  background: var(--color-success-bg);
  color: var(--color-success);
  border: 1px solid var(--color-success-border);
}

.ui-badge--danger {
  background: var(--color-danger-bg);
  color: var(--color-danger);
  border: 1px solid var(--color-danger-border);
}

.ui-badge--warning {
  background: var(--color-warning-bg);
  color: var(--color-warning);
  border: 1px solid var(--color-warning-border);
}

.ui-badge--brand {
  background: var(--color-brand-subtle);
  color: var(--color-brand-strong);
  border: 1px solid var(--color-brand);
}

.ui-badge--neutral {
  background: var(--color-agent-stopped-bg);
  color: var(--color-agent-stopped);
  border: 1px solid var(--color-agent-stopped-border);
}
</style>
