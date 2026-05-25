import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || ''

export const usePlatformStore = defineStore('platform', () => {
  // ── state ──────────────────────────────────────────────────────────────
  const mode = ref('manual')
  const availability = ref('online')
  const snapshot = ref(null)
  const todayStats = ref(null)
  const alerts = ref([])          // { id, message, level, timestamp, source }
  const connected = ref(false)
  const spreadHistory  = ref([])
  const marketContext  = ref(null)
  const hourlyPatterns = ref([])
  let nextAlertId = 0

  // ── getters ────────────────────────────────────────────────────────────
  const modeLabel = computed(() => ({
    manual: '🟢 MANUAL',
    semi:   '🟡 SEMI-AUTO',
    full:   '🔴 FULL AUTO',
  }[mode.value] ?? mode.value))

  const availabilityLabel = computed(() => ({
    online:  '🟢 ONLINE',
    slow:    '🟡 SLOW',
    offline: '🔴 OFFLINE',
  }[availability.value] ?? availability.value))

  const isCriticalAlert = computed(() =>
    alerts.value.some(a => a.level === 'critical')
  )

  // ── actions ────────────────────────────────────────────────────────────
  async function fetchStatus() {
    const { data } = await axios.get(`${API}/api/status`)
    mode.value = data.mode
    availability.value = data.availability
  }

  async function setMode(newMode) {
    const { data } = await axios.post(`${API}/api/mode`, { mode: newMode })
    mode.value = data.mode
  }

  async function setAvailability(newAvail) {
    const { data } = await axios.post(`${API}/api/availability`, { availability: newAvail })
    availability.value = data.availability
  }

  async function fetchSnapshot() {
    const { data } = await axios.get(`${API}/api/p2p/snapshot`)
    snapshot.value = data
  }

  async function fetchTodayStats() {
    const { data } = await axios.get(`${API}/api/p2p/stats/today`)
    todayStats.value = data
  }

  async function fetchAnalytics(days = 7) {
    const [histRes, ctxRes, patRes] = await Promise.all([
      axios.get(`${API}/api/p2p/analytics/history?days=${days}`),
      axios.get(`${API}/api/p2p/analytics/context?days=30`),
      axios.get(`${API}/api/p2p/analytics/patterns`),
    ])
    spreadHistory.value  = histRes.data
    marketContext.value  = ctxRes.data
    hourlyPatterns.value = patRes.data
  }

  function addAlert(alert) {
    alerts.value.unshift({ ...alert, id: nextAlertId++ })
    if (alerts.value.length > 50) alerts.value.pop()
    playBeep(alert.level)
  }

  function dismissAlert(id) {
    alerts.value = alerts.value.filter(a => a.id !== id)
  }

  // Soft tone via Web Audio API — no OS permission needed, no jarring sound
  function playBeep(level) {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)()
      const configs = {
        info:     [{ freq: 520, start: 0,    dur: 0.12 }],
        warning:  [{ freq: 600, start: 0,    dur: 0.12 }, { freq: 600, start: 0.18, dur: 0.12 }],
        critical: [{ freq: 720, start: 0,    dur: 0.12 }, { freq: 720, start: 0.18, dur: 0.12 }, { freq: 720, start: 0.36, dur: 0.14 }],
      }
      const tones = configs[level] ?? configs.info
      tones.forEach(({ freq, start, dur }) => {
        const osc  = ctx.createOscillator()
        const gain = ctx.createGain()
        osc.connect(gain)
        gain.connect(ctx.destination)
        osc.type = 'sine'
        osc.frequency.value = freq
        gain.gain.setValueAtTime(0.25, ctx.currentTime + start)
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + start + dur)
        osc.start(ctx.currentTime + start)
        osc.stop(ctx.currentTime + start + dur + 0.05)
      })
    } catch {
      // AudioContext not available (server-side render or blocked) — silent fallback
    }
  }

  function startStream() {
    const es = new EventSource(`${API}/api/stream`)

    es.onopen = () => { connected.value = true }
    es.onerror = () => { connected.value = false }

    es.onmessage = (event) => {
      try {
        const alert = JSON.parse(event.data)
        addAlert(alert)
      } catch {
        // ignore malformed events
      }
    }

    return es  // caller can close() if needed
  }

  return {
    mode, availability, snapshot, todayStats, alerts, connected,
    spreadHistory, marketContext, hourlyPatterns,
    modeLabel, availabilityLabel, isCriticalAlert,
    fetchStatus, setMode, setAvailability,
    fetchSnapshot, fetchTodayStats, fetchAnalytics,
    addAlert, dismissAlert, startStream,
  }
})
