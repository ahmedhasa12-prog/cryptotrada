<template>
  <div class="ui-card">
    <div class="ui-card__header" v-if="title || $slots.header || $slots.actions">
      <slot name="header">
        <h3 v-if="title" class="ui-card__title">{{ title }}</h3>
      </slot>
      <div class="ui-card__actions" v-if="$slots.actions"><slot name="actions" /></div>
    </div>
    <div class="ui-card__body">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ title?: string }>()
</script>

<style scoped>
.ui-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
}

.ui-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5) 0;
}

.ui-card__title {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0;
}

.ui-card__body {
  padding: var(--space-5);
}
</style>
