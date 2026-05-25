<template>
  <div class="card">
    <div class="card-header">
      <h2>{{ t('stats.title') }}</h2>
      <button class="log-btn" @click="showModal = true">{{ t('stats.log_btn') }}</button>
    </div>

    <div v-if="hasStats" class="stats-grid">
      <div class="stat"><span class="stat-label">{{ t('stats.trades') }}</span><span class="stat-val">{{ stats.count }}</span></div>
      <div class="stat"><span class="stat-label">{{ t('stats.volume') }}</span><span class="stat-val">{{ stats.volume_usdt.toFixed(1) }} USDT</span></div>
      <div class="stat"><span class="stat-label">{{ t('stats.profit') }}</span><span class="stat-val profit">{{ stats.profit_sdg.toFixed(1) }} SDG</span></div>
      <div class="stat"><span class="stat-label">{{ t('stats.avg_release') }}</span><span class="stat-val">{{ avgRelease }}</span></div>
    </div>
    <p v-else class="empty">{{ t('stats.empty') }}</p>

    <LogTradeModal v-if="showModal" @close="showModal = false" @saved="onSaved" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../stores/platform'
import LogTradeModal from './LogTradeModal.vue'

const { t } = useI18n()
const store     = usePlatformStore()
const showModal = ref(false)
const stats     = computed(() => store.todayStats)
const hasStats  = computed(() => stats.value && stats.value.count > 0)

const avgRelease = computed(() => {
  const v = stats.value?.avg_release_minutes
  return v != null ? `${v.toFixed(1)} min` : '—'
})

function onSaved() {}
onMounted(() => store.fetchTodayStats())
</script>

<style scoped>
.log-btn {
  background: #2b6cb0; border: none; color: #fff;
  padding: 0.35rem 0.75rem; border-radius: 0.4rem;
  cursor: pointer; font-size: 0.82rem; font-weight: 600; min-height: 36px;
}
.log-btn:active { background: #3182ce; }
.profit { color: #68d391; }
</style>
