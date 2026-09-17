<template>
  <div class="page-view">
    <Analytics />
    <TodayStats />
  </div>
</template>

<script setup lang="ts">
import Analytics from '@/components/Analytics.vue'
import TodayStats from '@/components/TodayStats.vue'
</script>

<style scoped>
.page-view {
  display: flex;
  flex-direction: column;
  gap: var(--space-6, 1.5rem);
  padding: var(--space-6, 1.5rem);
  max-width: var(--content-max-width, 1280px);
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}
</style>
