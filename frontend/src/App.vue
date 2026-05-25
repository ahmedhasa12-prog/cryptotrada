<template>
  <div class="app">
    <header class="top-bar">
      <span class="logo">📈 CryptoTrada</span>
      <div class="top-bar-right">
        <span class="phase-badge">{{ t('header.phase') }}</span>
        <button class="lang-btn" @click="toggleLang">{{ t('header.lang') }}</button>
      </div>
    </header>

    <main class="grid">
      <StatusCard />
      <TodayStats />
      <P2PSnapshot class="wide" />
      <Analytics class="wide" />
      <AlertFeed class="wide" />
    </main>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { setLocale } from './i18n.js'
import { usePlatformStore } from './stores/platform'
import StatusCard from './components/StatusCard.vue'
import TodayStats from './components/TodayStats.vue'
import P2PSnapshot from './components/P2PSnapshot.vue'
import AlertFeed from './components/AlertFeed.vue'
import Analytics from './components/Analytics.vue'

const { t, locale } = useI18n()
const store = usePlatformStore()
let es

function toggleLang() {
  setLocale(locale.value === 'ar' ? 'en' : 'ar')
}

onMounted(async () => {
  await store.fetchStatus()
  es = store.startStream()
})

onUnmounted(() => es?.close())
</script>

<style>
/* ── Base (mobile-first) ─────────────────────────────────────────────────── */
body {
  font-family: 'Segoe UI', system-ui, sans-serif;
  background: #0f1117;
  color: #e2e8f0;
  min-height: 100dvh;
  -webkit-text-size-adjust: 100%;
  /* push content above iPhone home bar */
  padding-bottom: env(safe-area-inset-bottom);
}

.app { display: flex; flex-direction: column; min-height: 100dvh; }

/* ── Top bar ─────────────────────────────────────────────────────────────── */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.7rem 1rem;
  padding-top: calc(0.7rem + env(safe-area-inset-top));
  background: #1a1d27;
  border-bottom: 1px solid #2d3748;
  position: sticky;
  top: 0;
  z-index: 10;
}
.logo { font-size: 1.05rem; font-weight: 700; color: #63b3ed; }
.top-bar-right { display: flex; align-items: center; gap: 0.5rem; }

.phase-badge {
  font-size: 0.68rem;
  background: #2d3748;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  color: #a0aec0;
}

.lang-btn {
  font-size: 0.72rem;
  background: #2d3748;
  border: 1px solid #4a5568;
  color: #90cdf4;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  cursor: pointer;
  font-family: 'Segoe UI', system-ui, sans-serif;
  min-height: 28px;
}
.lang-btn:active { background: #4a5568; }

/* ── Grid — mobile: single column stack ─────────────────────────────────── */
.grid {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.75rem;
  flex: 1;
}

@media (min-width: 640px) {
  .grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    padding: 1rem 1.5rem;
  }
  .wide { grid-column: 1 / -1; }
}

/* ── Card ────────────────────────────────────────────────────────────────── */
.card {
  background: #1a1d27;
  border: 1px solid #2d3748;
  border-radius: 0.75rem;
  padding: 1rem;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.875rem;
}
.card h2 { font-size: 0.95rem; font-weight: 600; color: #90cdf4; }
.card h3 { font-size: 0.8rem; font-weight: 600; margin: 0.875rem 0 0.4rem; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.04em; }

/* ── Connection dot ──────────────────────────────────────────────────────── */
.connection-dot {
  width: 10px; height: 10px;
  border-radius: 50%;
  background: #e53e3e;
  display: inline-block;
  transition: background 0.3s;
}
.connection-dot.connected { background: #48bb78; }

/* ── Status card ─────────────────────────────────────────────────────────── */
.status-grid { display: flex; flex-direction: column; gap: 0.75rem; }
.status-item { display: flex; flex-direction: column; gap: 0.35rem; }
.status-item label { font-size: 0.72rem; color: #718096; text-transform: uppercase; letter-spacing: 0.04em; }
.status-item select {
  background: #2d3748;
  border: 1px solid #4a5568;
  color: #e2e8f0;
  padding: 0.6rem 0.75rem;
  border-radius: 0.5rem;
  font-size: 1rem;
  cursor: pointer;
  width: 100%;
  min-height: 44px;
  appearance: auto;
}

/* 3-equal-column availability buttons — easy to tap */
.avail-buttons { display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.5rem; }
.avail-btn {
  min-height: 44px;
  padding: 0.4rem 0.25rem;
  border-radius: 0.5rem;
  border: 1px solid #4a5568;
  background: #2d3748;
  color: #a0aec0;
  cursor: pointer;
  font-size: 0.8rem;
  text-align: center;
  transition: all 0.15s;
}
.avail-btn.active {
  background: #2c4a6e;
  color: #90cdf4;
  border-color: #63b3ed;
}

.critical-banner {
  margin-top: 0.75rem;
  background: #742a2a;
  border: 1px solid #c53030;
  border-radius: 0.4rem;
  padding: 0.6rem 0.75rem;
  font-size: 0.875rem;
  color: #fed7d7;
}

/* ── P2P Snapshot ────────────────────────────────────────────────────────── */
/* 2-column grid on mobile — big enough to read at a glance */
.snapshot-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.875rem;
  margin-bottom: 0.875rem;
}
.metric { display: flex; flex-direction: column; gap: 0.25rem; }
.metric-label { font-size: 0.65rem; color: #718096; text-transform: uppercase; letter-spacing: 0.05em; }
.metric-value { font-size: 1.25rem; font-weight: 700; }
.metric-value.time { font-size: 0.875rem; font-weight: 400; color: #a0aec0; }
.spread-wide .metric-value { color: #68d391; }
.spread-tight .metric-value { color: #fc8181; }

/* Table scrolls horizontally rather than wrapping weirdly */
.sellers-table { overflow-x: auto; -webkit-overflow-scrolling: touch; }
.sellers-table table { width: 100%; border-collapse: collapse; font-size: 0.875rem; min-width: 260px; }
.sellers-table th { text-align: left; color: #718096; font-weight: 500; padding: 0.35rem 0.5rem; font-size: 0.72rem; text-transform: uppercase; }
.sellers-table td { padding: 0.45rem 0.5rem; border-top: 1px solid #2d3748; white-space: nowrap; }
.sellers-table td:first-child { color: #718096; width: 1.5rem; }

/* ── Buttons ─────────────────────────────────────────────────────────────── */
.refresh-btn, .clear-btn {
  background: #2d3748;
  border: 1px solid #4a5568;
  color: #a0aec0;
  padding: 0.4rem 0.75rem;
  border-radius: 0.4rem;
  cursor: pointer;
  font-size: 0.8rem;
  min-height: 36px;
}
.refresh-btn:active, .clear-btn:active { background: #4a5568; color: #e2e8f0; }

/* ── Today stats ─────────────────────────────────────────────────────────── */
.stats-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0.875rem; }
.stat { display: flex; flex-direction: column; gap: 0.25rem; }
.stat-label { font-size: 0.65rem; color: #718096; text-transform: uppercase; letter-spacing: 0.05em; }
.stat-val { font-size: 1.25rem; font-weight: 700; }

/* ── Alert feed ──────────────────────────────────────────────────────────── */
.alert-card { display: flex; flex-direction: column; max-height: 55dvh; }

@media (min-width: 640px) {
  .alert-card { max-height: 400px; }
}

.alert-list {
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding-top: 0.25rem;
  /* momentum scrolling on iOS */
  -webkit-overflow-scrolling: touch;
}

.notif-banner {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #2d3748;
  padding: 0.5rem 0.75rem;
  border-radius: 0.4rem;
  font-size: 0.82rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}
.notif-banner button {
  margin-left: auto;
  background: #4a5568;
  border: none;
  color: #e2e8f0;
  padding: 0.35rem 0.75rem;
  border-radius: 0.3rem;
  cursor: pointer;
  min-height: 36px;
}

.alert-item {
  display: flex;
  flex-direction: column;
  padding: 0.6rem 0.75rem;
  border-radius: 0.4rem;
  border-left: 3px solid transparent;
  background: #2d3748;
  gap: 0.3rem;
}
.alert-info    { border-left-color: #63b3ed; }
.alert-warning { border-left-color: #f6ad55; background: #2d2516; }
.alert-critical { border-left-color: #fc8181; background: #2d1616; }

.alert-body { display: flex; gap: 0.4rem; flex: 1; font-size: 0.875rem; line-height: 1.45; }
.alert-icon { flex-shrink: 0; }
.alert-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  font-size: 0.72rem;
  color: #718096;
}
.dismiss {
  background: none;
  border: none;
  color: #718096;
  cursor: pointer;
  font-size: 1rem;
  line-height: 1;
  padding: 0.1rem 0.25rem;
  min-width: 28px;
  min-height: 28px;
}
.dismiss:active { color: #e2e8f0; }

/* ── Transitions ─────────────────────────────────────────────────────────── */
.alert-anim-enter-active { transition: all 0.2s ease; }
.alert-anim-enter-from { opacity: 0; transform: translateY(-6px); }

.empty { color: #4a5568; font-size: 0.85rem; margin-top: 0.5rem; }
</style>
