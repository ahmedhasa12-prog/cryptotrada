<template>
  <div class="card alert-card">
    <div class="card-header">
      <h2>{{ t('alerts.title') }}</h2>
      <button v-if="store.alerts.length" class="clear-btn" @click="clearAll">{{ t('alerts.clear') }}</button>
    </div>

    <div class="alert-list">
      <transition-group name="alert-anim">
        <div
          v-for="alert in store.alerts"
          :key="alert.id"
          class="alert-item"
          :class="`alert-${alert.level}`"
        >
          <div class="alert-top">
            <span class="alert-icon">{{ levelIcon(alert.level) }}</span>
            <span class="alert-source">{{ sourceLabel(alert.source) }}</span>
            <span class="alert-time">{{ formatTime(alert.timestamp) }}</span>
            <button class="dismiss" @click="store.dismissAlert(alert.id)" title="Dismiss">✕</button>
          </div>
          <p class="alert-msg">{{ alert.message }}</p>
        </div>
      </transition-group>
      <p v-if="!store.alerts.length" class="empty">{{ t('alerts.empty') }}</p>
    </div>
  </div>
</template>

<script setup>
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../stores/platform'

const { t } = useI18n()
const store = usePlatformStore()

function clearAll() { store.alerts.splice(0) }

function levelIcon(level) {
  return { info: 'ℹ️', warning: '⚠️', critical: '🚨' }[level] ?? 'ℹ️'
}

function sourceLabel(source) {
  return t(`alerts.sources.${source}`, t('alerts.sources.default'))
}

function formatTime(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}
</script>

<style scoped>
.alert-top {
  display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.3rem;
}
.alert-source {
  font-size: 0.68rem; font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.05em; color: #718096; background: #2d3748;
  padding: 0.1rem 0.4rem; border-radius: 999px;
}
.alert-time { font-size: 0.72rem; color: #4a5568; margin-inline-start: auto; }
.dismiss {
  background: none; border: none; color: #4a5568; cursor: pointer;
  font-size: 0.9rem; min-width: 24px; min-height: 24px; margin-inline-start: 0.25rem; flex-shrink: 0;
}
.dismiss:active { color: #e2e8f0; }
.alert-msg { font-size: 0.875rem; line-height: 1.5; margin: 0; color: #e2e8f0; padding-inline-start: 1.6rem; }
</style>
