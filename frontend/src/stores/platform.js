import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

const API = import.meta.env.VITE_API_BASE || ''

export const usePlatformStore = defineStore('platform', () => {
  // ── state ──────────────────────────────────────────────────────────────
  const mode = ref('manual')
  const availability = ref('online')
  const tradingMode = ref('auto_trend')
  const snapshot = ref(null)
  const todayStats = ref(null)
  const alerts = ref([])          // { id, message, level, timestamp, source }
  const connected = ref(false)
  const spreadHistory  = ref([])
  const marketContext  = ref(null)
  const hourlyPatterns = ref([])
  // Trading section
  const macro           = ref(null)
  const narratives      = ref([])
  const watchlist       = ref([])
  const weekdayPatterns = ref([])
  const heatmap         = ref([])
  const spotTiming      = ref(null)   // { ready, status, hourly, weekday, sessions }
  const spotTimingStatus = ref(null)  // { candles_1h, pct_complete, backfilling, ready }
  // Agent system
  const agents = ref([])              // Array of agent status objects
  let nextAlertId = 0
  const muted = ref(localStorage.getItem('alerts_muted') === 'true')

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

  const TRADING_AGENT_TYPES = ['auto_trend', 'xrp_swing', 'sol_swing']

  const runningAgents = computed(() =>
    agents.value.filter(a => a.state === 'running')
  )

  const pausedAgents = computed(() =>
    agents.value.filter(a => a.state === 'paused')
  )

  const stoppedAgents = computed(() =>
    agents.value.filter(a => a.state === 'stopped' || a.state === 'error')
  )

  // Trading agents only (excludes p2p_market and manual)
  const tradingAgents = computed(() =>
    agents.value.filter(a => TRADING_AGENT_TYPES.includes(a.agent_type))
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
  
  async function setTradingMode(newTradingMode) {
    const { data } = await axios.post(`${API}/api/trading-mode`, { trading_mode: newTradingMode })
    tradingMode.value = data.trading_mode
  }

  async function fetchSnapshot() {
    const { data } = await axios.get(`${API}/api/p2p/snapshot`)
    snapshot.value = data
  }

  async function fetchTodayStats() {
    const { data } = await axios.get(`${API}/api/p2p/stats/today`)
    todayStats.value = data
  }

  async function fetchTimingData() {
    const [wdRes, hmRes] = await Promise.all([
      axios.get(`${API}/api/p2p/analytics/weekday-patterns`),
      axios.get(`${API}/api/p2p/analytics/heatmap`),
    ])
    weekdayPatterns.value = wdRes.data
    heatmap.value         = hmRes.data
  }

  async function fetchSpotTimingStatus(symbol) {
    const { data } = await axios.get(`${API}/api/spot/timing/${symbol}/status`)
    spotTimingStatus.value = data
    return data
  }

  async function startSpotBackfill(symbol) {
    const { data } = await axios.post(`${API}/api/spot/timing/${symbol}/backfill`)
    spotTimingStatus.value = data
    return data
  }

  async function fetchSpotTimingPatterns(symbol) {
    const { data } = await axios.get(`${API}/api/spot/timing/${symbol}/patterns`)
    spotTiming.value = data
    return data
  }

  async function fetchSignals() {
    const { data } = await axios.get(`${API}/api/spot/signals`)
    return data
  }

  async function fetchBotStatus() {
    const { data } = await axios.get(`${API}/api/spot/bot/status`)
    return data
  }

  async function toggleBot() {
    const { data } = await axios.post(`${API}/api/spot/bot/toggle`)
    return data
  }

  async function seedBotTest() {
    const { data } = await axios.post(`${API}/api/spot/bot/seed-test`)
    return data
  }

  async function fetchLeaderboard() {
    const { data } = await axios.get(`${API}/api/spot/bot/leaderboard`)
    return data
  }

  async function fetchBotHistory() {
    const { data } = await axios.get(`${API}/api/spot/bot/history`)
    return data
  }

  async function syncFromBinance() {
    const { data } = await axios.post(`${API}/api/p2p/trades/sync`)
    return data   // { imported, skipped, error }
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

  async function fetchMacro(forceRefresh = false) {
    const url = forceRefresh ? `${API}/api/spot/macro/refresh` : `${API}/api/spot/macro`
    const method = forceRefresh ? 'post' : 'get'
    const { data } = await axios[method](url)
    macro.value = data
  }

  async function fetchNarratives() {
    const { data } = await axios.get(`${API}/api/spot/narratives`)
    narratives.value = data
  }

  async function fetchWatchlist() {
    const { data } = await axios.get(`${API}/api/spot/watchlist`)
    watchlist.value = data
  }

  // ── Agent Actions ──────────────────────────────────────────────────────
  
  async function fetchAgentsStatus() {
    try {
      const { data } = await axios.get(`${API}/api/agents/status`)
      agents.value = Object.values(data.agents)
    } catch (e) {
      console.error('Failed to fetch agents status:', e)
      agents.value = []
    }
  }

  async function agentAction(agentType, action) {
    const validActions = ['start', 'stop', 'pause', 'resume']
    if (!validActions.includes(action)) {
      throw new Error(`Invalid action: ${action}`)
    }
    
    await axios.post(`${API}/api/agents/${agentType}/${action}`)
  }

  async function startAllAgents() {
    const { data } = await axios.post(`${API}/api/agents/start-all`)
    agents.value = Object.values(data.agents)
  }

  async function stopAllAgents() {
    const { data } = await axios.post(`${API}/api/agents/stop-all`)
    agents.value = Object.values(data.agents)
  }

  async function updateAgentConfig(agentType, config) {
    const { data } = await axios.patch(`${API}/api/agents/${agentType}/config`, config)
    // Update local state
    const idx = agents.value.findIndex(a => a.agent_type === agentType)
    if (idx >= 0) {
      agents.value[idx] = data
    }
  }

  function toggleMute() {
    muted.value = !muted.value
    localStorage.setItem('alerts_muted', muted.value)
  }

  function addAlert(alert) {
    alerts.value.unshift({ ...alert, id: nextAlertId++ })
    if (alerts.value.length > 50) alerts.value.pop()
    if (!muted.value) playBeep(alert.level)
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
    mode, availability, tradingMode, snapshot, todayStats, alerts, connected,
    spreadHistory, marketContext, hourlyPatterns,
    macro, narratives, watchlist, weekdayPatterns, heatmap,
    spotTiming, spotTimingStatus,
    agents, runningAgents, pausedAgents, stoppedAgents,
    fetchSpotTimingStatus, startSpotBackfill, fetchSpotTimingPatterns, fetchSignals,
    fetchBotStatus, toggleBot, seedBotTest, fetchLeaderboard, fetchBotHistory,
    modeLabel, availabilityLabel, isCriticalAlert,
    fetchStatus, setMode, setAvailability, setTradingMode,
    fetchSnapshot, fetchTodayStats, syncFromBinance, fetchAnalytics, fetchTimingData,
    fetchMacro, fetchNarratives, fetchWatchlist,
    muted, toggleMute,
    addAlert, dismissAlert, startStream,
    // Agent actions
    fetchAgentsStatus, agentAction, startAllAgents, stopAllAgents, updateAgentConfig,
  }
})
