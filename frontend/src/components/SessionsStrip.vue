<template>
  <div class="sessions-strip">
    <div class="sstrip-header">
      <span class="sstrip-title">{{ t('timing.sessions_title') }}</span>
      <div class="sstrip-meta">
        <span class="sstrip-time">{{ localTimeStr }}</span>
        <span class="sstrip-tz">{{ tzShort }}</span>
      </div>
    </div>
    <div v-if="sessionOverlap" class="sstrip-overlap">
      {{ t('timing.overlap') }} · {{ overlapNames }}
    </div>
    <div class="sstrip-list">
      <div v-for="s in sessions" :key="s.name" class="sstrip-chip" :class="{ active: s.active }">
        <span class="sstrip-flag">{{ s.flag }}</span>
        <span class="sstrip-name">{{ s.name }}</span>
        <span class="sstrip-hours">{{ s.localHours }}</span>
        <span class="sstrip-status">
          <span v-if="s.active" class="sstrip-live">{{ t('timing.live') }}</span>
          <span v-else class="sstrip-opens">{{ t('timing.opens_in', { h: s.opensIn }) }}</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const now = ref(new Date())
let clockTimer
onMounted(() => { clockTimer = setInterval(() => { now.value = new Date() }, 60_000) })
onUnmounted(() => clearInterval(clockTimer))

const utcHour  = computed(() => now.value.getUTCHours())
const tzOffset = computed(() => -now.value.getTimezoneOffset() / 60)

const localTimeStr = computed(() =>
  now.value.toLocaleTimeString('en', { hour: '2-digit', minute: '2-digit', hour12: false })
)

const tzShort = computed(() => {
  const name    = Intl.DateTimeFormat().resolvedOptions().timeZone
  const off     = tzOffset.value
  const sign    = off >= 0 ? '+' : '-'
  const absOff  = Math.abs(off)
  const hours   = Math.floor(absOff)
  const minutes = Math.round((absOff - hours) * 60)
  const hh      = String(hours).padStart(2, '0')
  const mm      = String(minutes).padStart(2, '0')
  const label   = minutes ? `${hh}:${mm}` : `${hours}`
  return `${name} (UTC${sign}${label})`
})

const sessions = computed(() => {
  const h  = utcHour.value
  const tz = tzOffset.value
  function localRange(s, e) {
    const ls = ((s + tz) % 24 + 24) % 24
    const le = ((e + tz) % 24 + 24) % 24
    return `${String(ls).padStart(2, '0')}:00–${String(le).padStart(2, '0')}:00`
  }
  function opensIn(s, e) {
    // handles both normal (s < e) and cross-midnight (s > e) sessions
    const active = s <= e ? (h >= s && h < e) : (h >= s || h < e)
    if (active) return null
    if (s <= e) return h < s ? s - h : 24 - h + s
    return h >= e && h < s ? s - h : 0
  }
  return [
    { flag: '🌏', name: t('timing.ses_asian'),  localHours: localRange(0, 8),   active: h >= 0  && h < 8,  opensIn: opensIn(0, 8)   },
    { flag: '🌍', name: t('timing.ses_london'), localHours: localRange(7, 16),  active: h >= 7  && h < 16, opensIn: opensIn(7, 16)  },
    { flag: '🌎', name: t('timing.ses_us'),     localHours: localRange(13, 22), active: h >= 13 && h < 22, opensIn: opensIn(13, 22) },
  ]
})

const activeSessions = computed(() => sessions.value.filter(s => s.active))
const sessionOverlap = computed(() => activeSessions.value.length >= 2)
const overlapNames   = computed(() => activeSessions.value.map(s => s.name).join(' + '))
</script>

<style scoped>
.sessions-strip {
  border: 1px solid var(--color-border); border-radius: 0.55rem;
  padding: 0.45rem 0.6rem 0.4rem; background: #151821;
  display: flex; flex-direction: column; gap: 0.35rem;
}
.sstrip-header {
  display: flex; align-items: center; justify-content: space-between; gap: 0.5rem;
}
.sstrip-title {
  font-size: var(--font-size-sm-plus); font-weight: 700; color: var(--color-accent-strong);
  text-transform: uppercase; letter-spacing: 0.06em; flex-shrink: 0;
}
.sstrip-meta  { display: flex; align-items: center; gap: 0.5rem; }
.sstrip-time  {
  font-size: var(--font-size-sm-plus); font-weight: 700; color: var(--color-text);
  font-variant-numeric: tabular-nums; letter-spacing: 0.02em;
}
.sstrip-tz    { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.sstrip-overlap {
  font-size: var(--font-size-sm); font-weight: 600; color: var(--color-warning);
  background: rgba(246,173,85,0.08); border: 1px solid rgba(246,173,85,0.25);
  border-radius: 0.35rem; padding: 0.15rem 0.5rem;
}
.sstrip-list  { display: flex; flex-direction: column; gap: 0.2rem; }
.sstrip-chip {
  display: flex; align-items: center; gap: 0.4rem;
  background: #1e2130; border: 1px solid var(--color-border);
  border-radius: 0.4rem; padding: 0.22rem 0.5rem;
}
.sstrip-chip.active { border-color: var(--color-accent); background: #1a2c42; }
.sstrip-flag  { font-size: var(--font-size-base); flex-shrink: 0; }
.sstrip-name  { font-size: var(--font-size-sm-plus); font-weight: 600; color: var(--color-text); min-width: 60px; }
.sstrip-hours { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary-bright); flex: 1; font-variant-numeric: tabular-nums; }
.sstrip-status { margin-inline-start: auto; flex-shrink: 0; }
.sstrip-live  {
  font-size: var(--font-size-sm); font-weight: 700; color: var(--color-success);
  background: var(--color-success-bg); border: 1px solid var(--color-success-emphasis);
  border-radius: 999px; padding: 0.05rem 0.4rem;
}
.sstrip-opens { font-size: var(--font-size-sm); color: var(--color-text-muted); font-variant-numeric: tabular-nums; }
</style>
