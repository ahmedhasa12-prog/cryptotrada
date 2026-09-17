<template>
  <div class="ui-spinner-wrap">
    <div class="ui-spinner" :style="{ width: size + 'px', height: size + 'px' }"></div>
    <span v-if="label">{{ label }}</span>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ size?: number; label?: string }>(), {
  size: 32,
})
</script>

<style scoped>
.ui-spinner-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
  padding: var(--space-8) var(--space-4);
}

.ui-spinner {
  border: 3px solid var(--color-border);
  border-top-color: var(--color-brand);
  border-radius: var(--radius-full);
  animation: ui-spin 0.8s linear infinite;
}

@keyframes ui-spin {
  to { transform: rotate(360deg); }
}
</style>
