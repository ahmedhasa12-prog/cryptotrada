<template>
  <div class="metric-tile" :class="`metric-tile--${size}`">
    <span class="metric-tile__value" :class="variantClass">{{ value }}</span>
    <span class="metric-tile__label">{{ label }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  label: string
  value: string | number
  variant?: 'neutral' | 'positive' | 'negative' | 'auto'
  size?: 'sm' | 'md'
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'neutral',
  size: 'md',
})

const variantClass = computed(() => {
  if (props.variant === 'auto') {
    const n = typeof props.value === 'number' ? props.value : parseFloat(String(props.value).replace(/[^0-9.-]/g, ''))
    return n >= 0 ? 'positive' : 'negative'
  }
  return props.variant === 'neutral' ? '' : props.variant
})
</script>

<style scoped>
.metric-tile {
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  text-align: center;
  transition: all var(--transition-fast);
}

.metric-tile:hover {
  border-color: var(--color-brand);
  transform: translateY(-2px);
  box-shadow: var(--shadow-sm);
}

.metric-tile--sm {
  padding: var(--space-2);
}

.metric-tile__value {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
  line-height: var(--line-height-tight);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.metric-tile--sm .metric-tile__value {
  font-size: var(--text-base);
}

.metric-tile__value.positive { color: var(--color-success); }
.metric-tile__value.negative { color: var(--color-danger); }

.metric-tile__label {
  font-size: var(--text-2xs, 0.6875rem);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
</style>
