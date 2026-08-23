<template>
  <div class="page-view">
    <div class="page-header">
      <h1>{{ t('journal.title') }}</h1>
    </div>
    <LogTradeModal v-if="showModal" @close="showModal = false" />
    <TodayStats />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import TodayStats from '@/components/TodayStats.vue'
import LogTradeModal from '@/components/LogTradeModal.vue'

const { t } = useI18n()
const showModal = ref(false)
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

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.page-header h1 {
  font-size: var(--text-3xl, 1.875rem);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary, var(--color-text));
  margin: 0;
}
</style>
