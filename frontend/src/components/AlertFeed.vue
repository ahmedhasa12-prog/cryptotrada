<template>
  <div class="card alert-card">
    <div class="card-header">
      <h2>{{ t('alerts.title') }}</h2>
      <div class="ah-controls">
        <button class="mute-btn" :class="{ muted: store.muted }" @click="store.toggleMute()" :title="store.muted ? t('alerts.unmute') : t('alerts.mute')">
          {{ store.muted ? '🔕' : '🔔' }}
        </button>
        <button v-if="store.alerts.length" class="clear-btn" @click="clearAll">{{ t('alerts.clear') }}</button>
      </div>
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
.ah-controls { display: flex; align-items: center; gap: 0.5rem; }
.mute-btn {
  background: none; border: 1px solid var(--color-border); border-radius: 6px;
  cursor: pointer; font-size: var(--font-size-base); padding: 0.15rem 0.4rem; line-height: 1;
  transition: border-color 0.15s;
}
.mute-btn.muted { border-color: var(--color-danger-strong); }
.mute-btn:hover { border-color: var(--color-text-disabled); }
.alert-top {
  display: flex; align-items: center; gap: 0.4rem; margin-bottom: 0.3rem;
}
.alert-source {
  font-size: var(--font-size-2xs-plus); font-weight: 600; text-transform: uppercase;
  letter-spacing: 0.05em; color: var(--color-text-disabled); background: var(--color-border);
  padding: 0.1rem 0.4rem; border-radius: 999px;
}
.alert-time { font-size: var(--font-size-xs); color: var(--color-text-subtle); margin-inline-start: auto; }
.dismiss {
  background: none; border: none; color: var(--color-text-subtle); cursor: pointer;
  font-size: var(--font-size-sm-plus); min-width: 24px; min-height: 24px; margin-inline-start: 0.25rem; flex-shrink: 0;
}
.dismiss:active { color: var(--color-text); }
.alert-msg { font-size: var(--font-size-sm); line-height: 1.5; margin: 0; color: var(--color-text); padding-inline-start: 1.6rem; }
</style>
