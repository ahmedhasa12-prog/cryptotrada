<template>
  <div class="atm-card" :class="`atm-${label}`">

    <!-- ── Animated background ─────────────────────────────────────────────── -->
    <div class="atm-bg" aria-hidden="true">

      <!-- HOSTILE: blazing desert -->
      <template v-if="label === 'hostile'">
        <div class="bg-sun">
          <div class="sun-core"></div>
          <div v-for="i in 8" :key="i" class="sun-ray" :style="`--ri:${i}`"></div>
        </div>
        <div v-for="i in 6" :key="i" class="bg-crack" :style="`--ci:${i}`"></div>
        <div class="bg-shimmer"></div>
      </template>

      <!-- LOW_NEUTRAL: hazy dust -->
      <template v-else-if="label === 'low_neutral'">
        <div class="bg-haze-sun">
          <div class="haze-core"></div>
        </div>
        <div class="bg-dust-band bd1"></div>
        <div class="bg-dust-band bd2"></div>
        <div class="bg-shimmer"></div>
      </template>

      <!-- NEUTRAL: dry savanna -->
      <template v-else-if="label === 'neutral'">
        <div class="bg-horizon"></div>
        <div class="bg-dust-haze"></div>
        <svg class="bg-silhouette" viewBox="0 0 120 70" fill="none">
          <ellipse cx="60" cy="46" rx="22" ry="11" fill="rgba(90,56,20,0.45)"/>
          <path d="M76 36 Q82 26 78 18" stroke="rgba(90,56,20,0.45)" stroke-width="3.5" fill="none" stroke-linecap="round"/>
          <ellipse cx="79" cy="20" rx="7" ry="5.5" fill="rgba(90,56,20,0.45)"/>
          <line x1="82" y1="15" x2="87" y2="5" stroke="rgba(90,56,20,0.45)" stroke-width="2" stroke-linecap="round"/>
          <line x1="87" y1="5" x2="91" y2="10" stroke="rgba(90,56,20,0.45)" stroke-width="1.5" stroke-linecap="round"/>
          <line x1="65" y1="56" x2="63" y2="68" stroke="rgba(90,56,20,0.45)" stroke-width="3" stroke-linecap="round"/>
          <line x1="56" y1="57" x2="54" y2="68" stroke="rgba(90,56,20,0.45)" stroke-width="3" stroke-linecap="round"/>
          <line x1="48" y1="56" x2="50" y2="68" stroke="rgba(90,56,20,0.45)" stroke-width="3" stroke-linecap="round"/>
          <line x1="39" y1="54" x2="37" y2="66" stroke="rgba(90,56,20,0.45)" stroke-width="3" stroke-linecap="round"/>
        </svg>
      </template>

      <!-- FAVOURABLE: gathering clouds + light rain -->
      <template v-else-if="label === 'favourable'">
        <div class="bg-cloud bfc1"></div>
        <div class="bg-cloud bfc2"></div>
        <div class="bg-cloud bfc3"></div>
        <div v-for="i in 22" :key="i" class="bg-drop" :style="`--di:${i}`"></div>
        <svg class="bg-pair" viewBox="0 0 200 80" fill="none">
          <g opacity="0.3">
            <ellipse cx="60" cy="56" rx="22" ry="11" fill="#6aaa7f"/>
            <path d="M76 42 Q84 26 80 18" stroke="#6aaa7f" stroke-width="3.5" fill="none" stroke-linecap="round"/>
            <ellipse cx="81" cy="20" rx="7" ry="5.5" fill="#6aaa7f"/>
            <line x1="84" y1="14" x2="89" y2="4"  stroke="#6aaa7f" stroke-width="2" stroke-linecap="round"/>
            <line x1="64" y1="66" x2="62" y2="78" stroke="#6aaa7f" stroke-width="3" stroke-linecap="round"/>
            <line x1="55" y1="67" x2="53" y2="78" stroke="#6aaa7f" stroke-width="3" stroke-linecap="round"/>
            <line x1="46" y1="66" x2="48" y2="77" stroke="#6aaa7f" stroke-width="3" stroke-linecap="round"/>
            <line x1="38" y1="64" x2="36" y2="76" stroke="#6aaa7f" stroke-width="3" stroke-linecap="round"/>
          </g>
          <g opacity="0.22" transform="translate(108,14) scale(0.74)">
            <ellipse cx="60" cy="56" rx="22" ry="11" fill="#4d8f64"/>
            <path d="M76 44 Q82 32 78 24" stroke="#4d8f64" stroke-width="3.5" fill="none" stroke-linecap="round"/>
            <ellipse cx="79" cy="26" rx="7" ry="5.5" fill="#4d8f64"/>
            <line x1="64" y1="66" x2="62" y2="78" stroke="#4d8f64" stroke-width="3" stroke-linecap="round"/>
            <line x1="55" y1="67" x2="53" y2="78" stroke="#4d8f64" stroke-width="3" stroke-linecap="round"/>
            <line x1="46" y1="66" x2="48" y2="77" stroke="#4d8f64" stroke-width="3" stroke-linecap="round"/>
            <line x1="38" y1="64" x2="36" y2="76" stroke="#4d8f64" stroke-width="3" stroke-linecap="round"/>
          </g>
        </svg>
      </template>

      <!-- EXCEPTIONAL: full storm + jumping herd -->
      <template v-else-if="label === 'exceptional'">
        <div class="bg-storm-cloud bsc1"></div>
        <div class="bg-storm-cloud bsc2"></div>
        <div class="bg-lightning bl1">⚡</div>
        <div class="bg-lightning bl2">⚡</div>
        <div v-for="i in 38" :key="i" class="bg-hdrop" :style="`--di:${i}`"></div>
        <div v-for="(a, i) in herd" :key="i"
             class="bg-jumper"
             :style="`left:${a.x}%;bottom:${a.b}px;animation-delay:${a.d}s;opacity:${a.o}`">
          <svg :width="a.w" viewBox="0 0 100 65" fill="none">
            <ellipse cx="50" cy="44" rx="21" ry="11" fill="#4a8a60"/>
            <path d="M65 34 Q73 22 69 14 Q75 8 71 6" stroke="#4a8a60" stroke-width="3.5" fill="none" stroke-linecap="round"/>
            <ellipse cx="72" cy="8" rx="7" ry="5.5" fill="#4a8a60"/>
            <line x1="75" y1="3"  x2="80" y2="-6" stroke="#4a8a60" stroke-width="2" stroke-linecap="round"/>
            <line x1="80" y1="-6" x2="85" y2="-1" stroke="#4a8a60" stroke-width="1.5" stroke-linecap="round"/>
            <line x1="60" y1="54" x2="65" y2="64" stroke="#4a8a60" stroke-width="3" stroke-linecap="round"/>
            <line x1="50" y1="55" x2="44" y2="64" stroke="#4a8a60" stroke-width="3" stroke-linecap="round"/>
            <line x1="40" y1="54" x2="45" y2="63" stroke="#4a8a60" stroke-width="3" stroke-linecap="round"/>
            <line x1="30" y1="52" x2="25" y2="62" stroke="#4a8a60" stroke-width="3" stroke-linecap="round"/>
          </svg>
        </div>
      </template>

    </div><!-- end .atm-bg -->

    <!-- Dark overlay -->
    <div class="atm-overlay"></div>

    <!-- ── Foreground content ──────────────────────────────────────────────── -->
    <div class="atm-content">

      <!-- ── Row 1: Header ──────────────────────────────────────────────────── -->
      <div class="atm-head-row">
        <span class="atm-title">{{ t('signal.atm_title') }}</span>
        <div class="atm-controls">
          <button class="atm-tog" :class="gateOn ? 'tog-on' : 'tog-off'" @click="$emit('toggleGate')"
                  :title="gateOn ? t('signal.atm_gate_on_tip') : t('signal.atm_gate_off_tip')">
            {{ t('signal.atm_gate') }} {{ gateOn ? '●' : '○' }}
          </button>
          <button class="atm-tog" :class="boostOn ? 'tog-on' : 'tog-off'" @click="$emit('toggleBoost')"
                  :title="boostOn ? t('signal.atm_boost_on_tip') : t('signal.atm_boost_off_tip')">
            {{ t('signal.atm_boost') }} {{ boostOn ? '●' : '○' }}
          </button>
          <button class="atm-ref" :class="{ spinning: loading }" @click="$emit('refresh')" :title="t('signal.atm_refresh_tip')">↻</button>
        </div>
      </div>

      <!-- ── Row 2: Score + condition pill + gauge ─────────────────────────── -->
      <div class="atm-score-row">

        <!-- Weather icon -->
        <div class="wx-icon" :class="`wx-${label}`">
          <svg v-if="label === 'hostile'" viewBox="0 0 40 40" width="42" height="42" fill="currentColor">
            <circle cx="20" cy="20" r="7"/>
            <line x1="20" y1="2"  x2="20" y2="9"  stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
            <line x1="20" y1="31" x2="20" y2="38" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
            <line x1="2"  y1="20" x2="9"  y2="20" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
            <line x1="31" y1="20" x2="38" y2="20" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
            <line x1="6.5"  y1="6.5"  x2="11" y2="11" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="29"   y1="29"   x2="33.5" y2="33.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="33.5" y1="6.5"  x2="29"   y2="11" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            <line x1="11"   y1="29"   x2="6.5"  y2="33.5" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
          </svg>
          <!-- low_neutral: hazy sun half-obscured -->
          <svg v-else-if="label === 'low_neutral'" viewBox="0 0 40 40" width="42" height="42" fill="none">
            <circle cx="20" cy="21" r="6" fill="currentColor" opacity="0.75"/>
            <line x1="20" y1="4"  x2="20" y2="10" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" opacity="0.55"/>
            <line x1="4"  y1="21" x2="10" y2="21" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" opacity="0.55"/>
            <line x1="30" y1="21" x2="36" y2="21" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" opacity="0.55"/>
            <line x1="7"  y1="8"  x2="11.5" y2="12.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
            <line x1="33" y1="8"  x2="28.5" y2="12.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" opacity="0.4"/>
            <!-- haze bands -->
            <path d="M4 30 Q12 27 20 30 Q28 33 36 30" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" opacity="0.45"/>
            <path d="M4 35 Q12 32 20 35 Q28 38 36 35" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round" opacity="0.28"/>
          </svg>
          <svg v-else-if="label === 'neutral'" viewBox="0 0 40 40" width="42" height="42" fill="none">
            <path d="M2 30 Q20 26 38 30" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
            <path d="M6 30 Q20 14 34 30" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
            <circle cx="30" cy="10" r="5" fill="currentColor" opacity="0.7"/>
          </svg>
          <svg v-else-if="label === 'favourable'" viewBox="0 0 40 40" width="42" height="42" fill="currentColor">
            <path d="M7 23 Q7 15 15 15 Q16 9 23 11 Q30 9 30 15 Q36 15 36 21 Q36 27 28 27 L12 27 Q7 27 7 23Z"/>
            <line x1="14" y1="30" x2="12" y2="38" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
            <line x1="22" y1="30" x2="20" y2="38" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
            <line x1="30" y1="30" x2="28" y2="38" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
          </svg>
          <svg v-else viewBox="0 0 40 40" width="42" height="42">
            <path d="M4 23 Q4 15 12 15 Q13 9 21 11 Q27 9 27 15 Q33 15 33 21 Q33 26 27 26 L9 26 Q4 26 4 23Z" fill="currentColor"/>
            <path d="M20 26 L16 34 L21 31 L18 40 L26 30 L21 33Z" fill="#ffe866"/>
          </svg>
        </div>

        <!-- Score block + gauge -->
        <div class="atm-score-block">

          <!-- Number row -->
          <div class="atm-num-row">
            <span class="wx-num" :class="`wxn-${label}`">{{ score }}</span>
            <span class="wx-den">/100</span>
            <span class="atm-cond-pill" :class="`pill-${label}`">{{ condLabel }}</span>
            <div v-if="boostOn && boost !== 1.0" class="wx-boost" :class="`boost-${boost > 1 ? 'up' : 'down'}`">
              ×{{ boost.toFixed(2) }}
            </div>
          </div>

          <!-- Gauge bar -->
          <div class="atm-gauge">
            <div class="gauge-track">
              <div class="gz gz-hostile"    title="Scorching (0–39)"></div>
              <div class="gz gz-lowneutral" title="Dry Spell (40–49)"></div>
              <div class="gz gz-neutral"    title="Dry Breeze (50–64)"></div>
              <div class="gz gz-favourable" title="Rain Clouds (65–79)"></div>
              <div class="gz gz-exceptional"title="Profit Storm (80–100)"></div>
            </div>
            <div class="gauge-marker" :class="`gm-${label}`" :style="`left:${gaugeMarkerLeft}`"></div>
          </div>

          <!-- Zone labels -->
          <div class="gauge-zone-labels">
            <span>0</span>
            <span style="left:39%">40</span>
            <span style="left:49%">50</span>
            <span style="left:64%">65</span>
            <span style="left:79%">80</span>
            <span style="left:100%">100</span>
          </div>

        </div>
      </div><!-- end .atm-score-row -->

      <!-- ── Row 3: BTC gate ────────────────────────────────────────────────── -->
      <div class="atm-btc-row">
        <template v-if="btcRegime">
          <div class="gate-badge" :class="btcRegime.bullish ? 'gb-open' : 'gb-closed'">
            {{ btcRegime.bullish ? t('signal.gate_open') : t('signal.gate_closed') }}
          </div>
          <div class="gate-price-stack">
            <div class="gps-line">
              <span class="gps-label">BTC</span>
              <span class="gps-val">${{ (btcRegime.btc_price || 0).toLocaleString() }}</span>
            </div>
            <div class="gps-line">
              <span class="gps-label">SMA50</span>
              <span class="gps-val gps-sma">${{ (btcRegime.sma50 || 0).toLocaleString() }}</span>
            </div>
            <div v-if="!btcRegime.bullish && btcRegime.sma50" class="gps-pct-row">
              ▼ {{ ((btcRegime.btc_price - btcRegime.sma50) / btcRegime.sma50 * 100).toFixed(1) }}% below SMA50
            </div>
          </div>
        </template>
        <div v-else class="gate-pending">⏳ BTC...</div>
      </div>

      <!-- ── Row 4: CB strip ────────────────────────────────────────────────── -->
      <div class="atm-cb-row" v-if="drawdown">
        <template v-if="!cbInPaperMode">
          <span class="cb-badge cb-off">{{ t('signal.cb_off_paper') }}</span>
          <span class="cb-nums">
            {{ t('signal.cb_day') }} ${{ drawdown.daily_pnl_usd?.toFixed(0) }}/-${{ drawdown.daily_limit }}
            &nbsp;·&nbsp;
            {{ t('signal.cb_week') }} ${{ drawdown.weekly_pnl_usd?.toFixed(0) }}/-${{ drawdown.weekly_limit }}
          </span>
        </template>
        <template v-else>
          <span class="cb-badge" :class="cbTripped ? 'cb-tripped' : 'cb-ok'">
            {{ cbTripped ? t('signal.cb_tripped') : t('signal.cb_ok') }}
          </span>
          <span class="cb-nums">
            {{ t('signal.cb_day') }} ${{ drawdown.daily_pnl_usd?.toFixed(0) }}/-${{ drawdown.daily_limit }}
            &nbsp;·&nbsp;
            {{ t('signal.cb_week') }} ${{ drawdown.weekly_pnl_usd?.toFixed(0) }}/-${{ drawdown.weekly_limit }}
          </span>
        </template>
      </div>

    </div><!-- end .atm-content -->
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  score:        { type: Number,  default: 50 },
  label:        { type: String,  default: 'neutral' },
  boost:        { type: Number,  default: 1.0 },
  computedAt:   { type: String,  default: null },
  gateOn:       { type: Boolean, default: false },
  boostOn:      { type: Boolean, default: true },
  loading:      { type: Boolean, default: false },
  btcRegime:    { type: Object,  default: null },
  drawdown:     { type: Object,  default: null },
  cbInPaperMode:{ type: Boolean, default: false },
})

defineEmits(['toggleGate', 'toggleBoost', 'refresh'])

const condLabel = computed(() => t(`signal.cond_${props.label}`) || props.label)

// Piecewise score→pixel mapping so the marker lands inside the correct zone.
// Zone widths (px%): hostile 0–39 → 39%, low_neutral 40–49 → 11%,
//                   neutral 50–64 → 15%, favourable 65–79 → 15%, exceptional 80–100 → 20%
const gaugeMarkerLeft = computed(() => {
  const s = Math.max(0, Math.min(100, props.score))
  const zones = [
    { sMin: 0,  sMax: 39,  pxStart: 0,  pxEnd: 39  },
    { sMin: 40, sMax: 49,  pxStart: 39, pxEnd: 50  },
    { sMin: 50, sMax: 64,  pxStart: 50, pxEnd: 65  },
    { sMin: 65, sMax: 79,  pxStart: 65, pxEnd: 80  },
    { sMin: 80, sMax: 100, pxStart: 80, pxEnd: 100 },
  ]
  const z = zones.find(z => s >= z.sMin && s <= z.sMax) ?? zones[zones.length - 1]
  const t = (s - z.sMin) / (z.sMax - z.sMin)
  return (z.pxStart + t * (z.pxEnd - z.pxStart)).toFixed(2) + '%'
})

const cbTripped = computed(() => {
  if (!props.drawdown) return false
  return (
    props.drawdown.daily_pnl_usd  <= -props.drawdown.daily_limit ||
    props.drawdown.weekly_pnl_usd <= -props.drawdown.weekly_limit
  )
})

const herd = [
  { x: 4,  b: 4, d: 0.0, w: 52, o: 0.28 },
  { x: 17, b: 6, d: 0.3, w: 64, o: 0.32 },
  { x: 32, b: 3, d: 0.1, w: 58, o: 0.25 },
  { x: 48, b: 7, d: 0.5, w: 50, o: 0.22 },
  { x: 62, b: 4, d: 0.2, w: 62, o: 0.30 },
  { x: 78, b: 5, d: 0.4, w: 54, o: 0.26 },
]
</script>

<style scoped>
/* ─────────────────────────────────────────────────────────────────────────── */
/* Card shell                                                                  */
/* ─────────────────────────────────────────────────────────────────────────── */
.atm-card {
  position: relative;
  overflow: hidden;
  border-radius: 10px;
  border: 1px solid rgba(255,255,255,0.10);
  margin: 0 0 6px;
}

.atm-hostile    { background: linear-gradient(135deg, #1c0900 0%, #2e1300 60%, #1a0800 100%); }
.atm-low_neutral{ background: linear-gradient(135deg, #160d00 0%, #241600 60%, #1a1000 100%); }
.atm-neutral    { background: linear-gradient(135deg, #161005 0%, #251a08 60%, #1a1208 100%); }
.atm-favourable { background: linear-gradient(135deg, #050d1a 0%, #091728 60%, #061220 100%); }
.atm-exceptional{ background: linear-gradient(135deg, #02050e 0%, #03091a 60%, #020810 100%); }

/* ─────────────────────────────────────────────────────────────────────────── */
/* Background animation layer                                                  */
/* ─────────────────────────────────────────────────────────────────────────── */
.atm-bg {
  position: absolute; inset: 0; z-index: 0;
  pointer-events: none; overflow: hidden;
}

/* ── Hostile: desert sun ────────────────────────────────────────────────── */
.bg-sun {
  position: absolute; top: -6px; right: 20px;
  animation: pulse-sun 2.8s ease-in-out infinite;
}
.sun-core {
  width: 52px; height: 52px; border-radius: 50%;
  background: radial-gradient(circle, #ffe066 30%, #ff8c00 100%);
  box-shadow: 0 0 28px 12px rgba(255,160,0,0.35); opacity: 0.45;
}
.sun-ray {
  position: absolute; width: 2.5px; height: 18px;
  background: #ffcc44; border-radius: 2px;
  top: 50%; left: 50%;
  transform-origin: 0 -30px;
  transform: translate(-50%, -100%) rotate(calc(var(--ri) * 45deg)) translateY(-30px);
  opacity: 0.3;
}
@keyframes pulse-sun { 0%,100%{transform:scale(1)} 50%{transform:scale(1.07)} }

.bg-crack {
  position: absolute;
  bottom: calc(var(--ci) * 5px); left: calc(var(--ci) * 12% + 5%);
  width: 2px; height: calc(6px + var(--ci) * 4px);
  background: rgba(80,35,5,0.55); border-radius: 1px;
  transform: rotate(calc(var(--ci) * 15deg));
}
.bg-shimmer {
  position: absolute; inset: 0;
  background: linear-gradient(0deg, rgba(150,60,0,0.12) 0%, transparent 50%);
  animation: shimmer 3s ease-in-out infinite alternate;
}
@keyframes shimmer { 0%{opacity:0.5} 100%{opacity:1} }

/* ── Low-neutral: haze ───────────────────────────────────────────────────── */
.bg-haze-sun {
  position: absolute; top: -4px; right: 24px;
  animation: pulse-sun 4s ease-in-out infinite;
}
.haze-core {
  width: 44px; height: 44px; border-radius: 50%;
  background: radial-gradient(circle, #e8c06a 20%, #b07020 100%);
  box-shadow: 0 0 22px 10px rgba(180,110,20,0.22); opacity: 0.32;
}
.bg-dust-band {
  position: absolute; left: 0; right: 0; height: 14px;
  background: linear-gradient(90deg, transparent, rgba(120,75,10,0.22), transparent);
  animation: shimmer 5s ease-in-out infinite alternate;
}
.bd1 { bottom: 16px; }
.bd2 { bottom: 4px; opacity: 0.6; }

/* ── Neutral: savanna ────────────────────────────────────────────────────── */
.bg-horizon {
  position: absolute; bottom: 0; left: 0; right: 0; height: 22px;
  background: rgba(70,45,12,0.35);
  border-radius: 50% 50% 0 0 / 6px 6px 0 0;
}
.bg-dust-haze {
  position: absolute; bottom: 12px; left: 0; right: 0; height: 18px;
  background: linear-gradient(0deg, rgba(140,90,30,0.2) 0%, transparent 100%);
  animation: shimmer 4s ease-in-out infinite alternate;
}
.bg-silhouette {
  position: absolute; bottom: 10px; right: 14px; width: 110px;
  animation: breathe 3.5s ease-in-out infinite;
}
@keyframes breathe { 0%,100%{transform:scaleY(1)} 50%{transform:scaleY(1.04)} }

/* ── Favourable: clouds + light rain ────────────────────────────────────── */
.bg-cloud {
  position: absolute; border-radius: 40px;
  background: rgba(160,185,210,0.28);
  animation: drift 7s ease-in-out infinite alternate;
}
.bfc1 { width:90px; height:28px; top:4px;  left:8%;  animation-delay:0s; }
.bfc2 { width:70px; height:22px; top:12px; left:36%; animation-delay:1s; opacity:0.8; }
.bfc3 { width:80px; height:24px; top:6px;  right:6%; animation-delay:1.8s; }
@keyframes drift { 0%{transform:translateX(-10px)} 100%{transform:translateX(10px)} }

.bg-drop {
  position: absolute;
  top: calc(var(--di) * 4.5%); left: calc(var(--di) * 4.5%);
  width: 1.2px; height: 13px;
  background: linear-gradient(180deg, transparent, rgba(130,180,220,0.5));
  border-radius: 1px;
  animation: fall-light 1.6s linear infinite;
  animation-delay: calc(var(--di) * 0.072s);
}
@keyframes fall-light {
  0%  { transform: translateY(-18px) rotate(12deg); opacity: 0; }
  25% { opacity: 0.7; }
  100%{ transform: translateY(150px) rotate(12deg); opacity: 0; }
}
.bg-pair { position: absolute; bottom: 6px; right: 10px; width: 160px; }

/* ── Exceptional: full storm ─────────────────────────────────────────────── */
.bg-storm-cloud {
  position: absolute; border-radius: 40px;
  background: rgba(60,80,100,0.5);
  animation: storm-drift 5s ease-in-out infinite alternate;
}
.bsc1 { width:130px; height:38px; top:2px;  left:4%;  animation-delay:0s;   box-shadow:0 4px 16px rgba(60,80,100,0.4); }
.bsc2 { width:110px; height:32px; top:10px; right:4%; animation-delay:1.4s; box-shadow:0 4px 16px rgba(60,80,100,0.4); }
@keyframes storm-drift { 0%{transform:translateX(-6px)} 100%{transform:translateX(6px)} }

.bg-lightning {
  position: absolute; font-size: 26px;
  animation: strike 4s ease-in-out infinite;
  filter: drop-shadow(0 0 7px #ffe866);
}
.bl1 { top:-2px; left:24%; animation-delay:0s; }
.bl2 { top:2px; right:22%; animation-delay:2.1s; }
@keyframes strike { 0%,86%,90%,94%,100%{opacity:0} 87%,89%,93%{opacity:0.85} }

.bg-hdrop {
  position: absolute;
  top: calc((var(--di) * 2.6%) - 4px); left: calc(var(--di) * 2.6%);
  width: 1.5px; height: 16px;
  background: linear-gradient(180deg, transparent, rgba(110,170,210,0.6));
  border-radius: 1px;
  animation: fall-heavy 0.75s linear infinite;
  animation-delay: calc(var(--di) * 0.02s);
}
@keyframes fall-heavy {
  0%  { transform: translateY(-22px) rotate(14deg); opacity: 0; }
  18% { opacity: 0.9; }
  100%{ transform: translateY(160px) rotate(14deg); opacity: 0; }
}
.bg-jumper { position: absolute; animation: jump 1.2s ease-in-out infinite; }
@keyframes jump { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-16px)} }

/* ─────────────────────────────────────────────────────────────────────────── */
/* Overlay                                                                     */
/* ─────────────────────────────────────────────────────────────────────────── */
.atm-overlay { position: absolute; inset: 0; z-index: 1; pointer-events: none; }
.atm-hostile    .atm-overlay { background: linear-gradient(180deg, rgba(20,8,0,0.72)  0%, rgba(16,6,0,0.60)   100%); }
.atm-low_neutral .atm-overlay{ background: linear-gradient(180deg, rgba(18,10,2,0.74) 0%, rgba(14,8,0,0.62)   100%); }
.atm-neutral    .atm-overlay { background: linear-gradient(180deg, rgba(18,12,4,0.70) 0%, rgba(14,10,3,0.58)  100%); }
.atm-favourable .atm-overlay { background: linear-gradient(180deg, rgba(4,10,22,0.74) 0%, rgba(4,10,22,0.60)  100%); }
.atm-exceptional .atm-overlay{ background: linear-gradient(180deg, rgba(2,5,14,0.78)  0%, rgba(2,5,14,0.65)   100%); }

/* ─────────────────────────────────────────────────────────────────────────── */
/* Content                                                                     */
/* ─────────────────────────────────────────────────────────────────────────── */
.atm-content { position: relative; z-index: 2; }

/* ── Header row ──────────────────────────────────────────────────────────── */
.atm-head-row {
  display: flex; align-items: center; justify-content: space-between;
  gap: 0.5rem;
  padding: 0.42rem 0.75rem;
  background: var(--color-accent-subtle);
  border-bottom: 1px solid var(--color-border);
}
.atm-title {
  font-size: var(--font-size-base); font-weight: var(--font-weight-bold); color: var(--color-accent-strong); margin: 0;
}
.atm-controls { display: flex; gap: 6px; align-items: center; }

.atm-tog {
  flex-shrink: 0;
  padding: 0.28rem 0.7rem; border-radius: var(--radius-md); border: none;
  font-size: var(--font-size-sm); font-weight: var(--font-weight-bold); cursor: pointer;
  letter-spacing: 0.02em; white-space: nowrap; transition: background 0.2s;
}
.tog-on  { background: var(--color-success-emphasis); color: var(--color-success-tint2); }
.tog-on:hover  { background: #2f855a; }
.tog-off { background: var(--color-surface-raised); color: var(--color-text-disabled); }
.tog-off:hover { background: #374151; }

.atm-ref {
  background: none; border: none; color: var(--color-text-secondary-bright);
  font-size: 1.1rem; cursor: pointer;
  padding: 0.1rem 0.3rem; border-radius: var(--radius-sm); transition: color 0.2s;
}
.atm-ref:hover { color: var(--color-text); }
.atm-ref.spinning { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Score row ─────────────────────────────────────────────────────────────── */
.atm-score-row {
  display: flex; align-items: flex-start; gap: 12px;
  padding: 12px 14px 4px;
}
.atm-score-row .wx-icon { flex-shrink: 0; margin-top: 2px; }

.wx-icon { display: flex; align-items: center; justify-content: center; }
.wx-hostile    { color: #ffaa33; filter: drop-shadow(0 0 8px rgba(255,160,40,0.70)); }
.wx-low_neutral{ color: #d4882a; filter: drop-shadow(0 0 6px rgba(200,120,30,0.55)); }
.wx-neutral    { color: #d4a44c; filter: drop-shadow(0 0 5px rgba(180,130,50,0.50)); }
.wx-favourable { color: #7ab8d8; filter: drop-shadow(0 0 6px rgba(100,170,210,0.55)); }
.wx-exceptional{ color: #c8d8e8; filter: drop-shadow(0 0 6px rgba(160,190,220,0.55)); }

/* Score block: number + pill + gauge */
.atm-score-block { flex: 1; min-width: 0; }

.atm-num-row {
  display: flex; align-items: baseline; gap: 4px; flex-wrap: wrap;
  margin-bottom: 8px;
}
.wx-num {
  font-size: 42px; font-weight: 800; line-height: 1;
  text-shadow: 0 2px 8px rgba(0,0,0,0.8);
}
.wx-den {
  font-size: var(--font-size-base); font-weight: 500; line-height: 1;
  color: rgba(255,255,255,0.30); margin-inline-end: 4px;
}
.wxn-hostile    { color: #ffcc55; }
.wxn-low_neutral{ color: #e0a040; }
.wxn-neutral    { color: #e0b85a; }
.wxn-favourable { color: #7ee89a; }
.wxn-exceptional{ color: #ffe866; }

/* Condition pill — replaces plain text */
.atm-cond-pill {
  font-size: var(--font-size-2xs-plus); font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
  padding: 3px 10px; border-radius: 20px; border: 1px solid;
  white-space: nowrap; align-self: center;
  text-shadow: 0 1px 3px rgba(0,0,0,0.5);
}
.pill-hostile     { background: rgba(180,60,10,0.30); border-color: rgba(255,150,50,0.55); color: #ffaa55; }
.pill-low_neutral { background: rgba(160,90,10,0.28); border-color: rgba(210,140,40,0.50); color: #e0a040; }
.pill-neutral     { background: rgba(140,100,20,0.28); border-color: rgba(200,160,60,0.45); color: #d4b06a; }
.pill-favourable  { background: rgba(20,80,40,0.30);  border-color: rgba(63,185,80,0.50);  color: #7ee89a; }
.pill-exceptional { background: rgba(140,120,0,0.28); border-color: rgba(255,230,60,0.50); color: #ffe866; }

/* Boost badge */
.wx-boost {
  font-size: var(--font-size-xs); font-weight: 700;
  padding: 2px 9px; border-radius: 10px;
  text-shadow: none; margin-inline-start: 4px; align-self: center;
}
.boost-up   { background: rgba(63,185,80,0.20); border: 1px solid rgba(63,185,80,0.45); color: #7ee89a; }
.boost-down { background: rgba(220,80,60,0.18); border: 1px solid rgba(220,80,60,0.40); color: #ff8070; }

/* ── Gauge bar ────────────────────────────────────────────────────────────── */
.atm-gauge {
  position: relative;
  margin-bottom: 3px;
  direction: ltr; /* always LTR: red(0) left → blue(100) right, marker left% correct in both ar/en */
}

.gauge-track {
  display: flex; height: 10px; border-radius: 5px; overflow: hidden;
  border: 1px solid rgba(255,255,255,0.15);
  box-shadow: 0 1px 4px rgba(0,0,0,0.5);
}
.gz { height: 100%; }
.gz-hostile    { width: 39%; background: linear-gradient(90deg, #d01800, #e84000); }
.gz-lowneutral { width: 11%; background: linear-gradient(90deg, #e84000, #d07800); }
.gz-neutral    { width: 15%; background: linear-gradient(90deg, #d07800, #8aaa00); }
.gz-favourable { width: 15%; background: linear-gradient(90deg, #3aaa50, #1898b0); }
.gz-exceptional{ width: 20%; background: linear-gradient(90deg, #1898b0, #0060e0); }

.gauge-marker {
  position: absolute; top: -4px;
  width: 16px; height: 16px; border-radius: 50%;
  border: 2.5px solid rgba(255,255,255,0.95);
  transform: translateX(-50%);
  box-shadow: 0 0 6px rgba(0,0,0,0.7);
  transition: left 0.5s ease;
  pointer-events: none;
}
.gm-hostile    { background: #e84000; box-shadow: 0 0 10px rgba(232,64,0,0.85); }
.gm-low_neutral{ background: #d07800; box-shadow: 0 0 8px  rgba(208,120,0,0.75); }
.gm-neutral    { background: #b0a000; box-shadow: 0 0 7px  rgba(176,160,0,0.70); }
.gm-favourable { background: #1898b0; box-shadow: 0 0 8px  rgba(24,152,176,0.75); }
.gm-exceptional{ background: #0060e0; box-shadow: 0 0 10px rgba(0,96,224,0.85); }

.gauge-zone-labels {
  position: relative; display: flex; height: 14px;
  font-size: var(--font-size-2xs-plus); color: rgba(255,255,255,0.28); font-variant-numeric: tabular-nums;
}
.gauge-zone-labels span {
  position: absolute; transform: translateX(-50%);
}
.gauge-zone-labels span:first-child { left: 0; transform: none; }
.gauge-zone-labels span:last-child  { left: 100%; transform: translateX(-100%); }

/* ── BTC gate row ──────────────────────────────────────────────────────────── */
.atm-btc-row {
  display: flex; align-items: center; gap: 14px;
  padding: 10px 14px 10px;
  border-top: 1px solid rgba(255,255,255,0.08);
}
.gate-price-stack { display: flex; flex-direction: column; gap: 2px; }
.gps-line { display: flex; align-items: baseline; gap: 6px; }
.gps-label {
  font-size: var(--font-size-2xs); font-weight: 600;
  color: rgba(255,255,255,0.35); text-transform: uppercase; letter-spacing: 0.05em;
  width: 40px; flex-shrink: 0;
}
.gps-val {
  font-size: var(--font-size-sm-plus); font-weight: 800; font-variant-numeric: tabular-nums;
  color: rgba(255,255,255,0.92); text-shadow: 0 1px 4px rgba(0,0,0,0.6);
}
.gps-sma { color: rgba(255,255,255,0.80); }
.gps-pct-row {
  font-size: var(--font-size-2xs-plus); font-weight: 700; color: var(--color-danger);
  margin-top: 2px; letter-spacing: 0.02em;
}

.gate-badge {
  display: inline-flex; align-items: center;
  padding: 5px 14px; border-radius: 22px; border: 1px solid;
  font-size: var(--font-size-sm); font-weight: 700;
  white-space: nowrap; flex-shrink: 0;
  text-shadow: 0 1px 4px rgba(0,0,0,0.6);
}
.gb-open   { background: rgba(20,60,30,0.80); border-color: var(--color-success-vivid); color: #7ee89a; }
.gb-closed { background: rgba(60,15,15,0.80); border-color: var(--color-danger-crimson); color: var(--color-danger); }
.gate-pending { font-size: var(--font-size-sm); color: rgba(255,255,255,0.45); }

/* ── CB strip ──────────────────────────────────────────────────────────────── */
.atm-cb-row {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 14px 11px;
  border-top: 1px solid rgba(255,255,255,0.08);
  flex-wrap: wrap;
}
.cb-badge {
  font-size: var(--font-size-2xs-plus); font-weight: 700; padding: 3px 11px;
  border-radius: 12px; border: 1px solid; white-space: nowrap; flex-shrink: 0;
}
.cb-off     { background: rgba(30,34,42,0.85); border-color: rgba(255,255,255,0.18); color: rgba(255,255,255,0.55); }
.cb-ok      { background: rgba(20,60,30,0.80); border-color: var(--color-success-vivid); color: #7ee89a; }
.cb-tripped { background: rgba(60,15,15,0.80); border-color: var(--color-danger-crimson); color: var(--color-danger); }
.cb-nums {
  font-size: var(--font-size-2xs-plus); color: rgba(255,255,255,0.55);
  text-shadow: 0 1px 3px rgba(0,0,0,0.6); line-height: 1.5;
}
</style>
