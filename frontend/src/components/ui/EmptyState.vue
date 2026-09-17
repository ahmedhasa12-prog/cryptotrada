<template>
  <div class="empty-state">
    <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
      <path v-if="icon === 'inbox'" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4"></path>
      <template v-else>
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="9" y1="12" x2="15" y2="12"></line>
      </template>
    </svg>
    <p>{{ message }}</p>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{ message: string; icon?: 'inbox' | 'dash' }>(), {
  icon: 'inbox',
})
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) var(--space-4);
  text-align: center;
  color: var(--color-text-tertiary);
  gap: var(--space-3);
}

.empty-state svg {
  opacity: 0.5;
}

.empty-state p {
  font-size: var(--text-sm);
  margin: 0;
}
</style>
