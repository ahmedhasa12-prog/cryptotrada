<template>
  <div class="card">
    <div class="card-header">
      <h2>{{ t('stats.title') }}</h2>
      <div class="header-actions">
        <button class="sync-btn" :disabled="syncing" @click="syncBinance">
          {{ syncing ? '⏳' : '☁️' }} {{ t('stats.sync_btn') }}
        </button>
        <button class="log-btn" @click="showModal = true">{{ t('stats.log_btn') }}</button>
      </div>
    </div>

    <div v-if="syncResult" class="sync-result" :class="syncResult.error ? 'sync-error' : 'sync-ok'">
      {{ syncResult.error
        ? `⚠️ ${syncResult.error}`
        : `✅ ${syncResult.imported} ${t('stats.sync_imported')}, ${syncResult.skipped} ${t('stats.sync_skipped')}` }}
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
const syncing   = ref(false)
const syncResult = ref(null)
const stats     = computed(() => store.todayStats)
const hasStats  = computed(() => stats.value && stats.value.count > 0)

const avgRelease = computed(() => {
  const v = stats.value?.avg_release_minutes
  return v != null ? `${v.toFixed(1)} ${t('stats.min')}` : '—'
})

async function syncBinance() {
  syncing.value = true
  syncResult.value = null
  try {
    const result = await store.syncFromBinance()
    syncResult.value = result
    if (result.imported > 0) await store.fetchTodayStats()
  } catch (e) {
    syncResult.value = { error: e?.response?.data?.detail || e.message }
  } finally {
    syncing.value = false
  }
}

function onSaved() {}
onMounted(() => store.fetchTodayStats())
</script>

<style scoped>
.header-actions { display: flex; gap: 0.5rem; align-items: center; }

.sync-btn {
  background: var(--color-border); border: 1px solid var(--color-border-muted); color: var(--color-accent-strong);
  padding: 0.35rem 0.65rem; border-radius: 0.4rem;
  cursor: pointer; font-size: var(--font-size-sm); font-weight: 600; min-height: 36px;
}
.sync-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.sync-btn:not(:disabled):active { background: var(--color-border-muted); }

.log-btn {
  background: #2b6cb0; border: none; color: #fff;
  padding: 0.35rem 0.75rem; border-radius: 0.4rem;
  cursor: pointer; font-size: var(--font-size-sm); font-weight: 600; min-height: 36px;
}
.log-btn:active { background: #3182ce; }

.sync-result {
  font-size: var(--font-size-sm); padding: 0.4rem 0.6rem;
  border-radius: 0.35rem; margin-bottom: 0.5rem;
}
.sync-ok    { background: var(--color-success-bg); color: var(--color-success-strong); border: 1px solid var(--color-success-emphasis); }
.sync-error { background: var(--color-danger-bg); color: var(--color-danger); border: 1px solid var(--color-danger-vivid); }

.profit { color: var(--color-success-strong); }
</style>
