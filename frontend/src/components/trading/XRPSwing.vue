<template>
  <div class="card xrp-card">
    <div class="card-header">
      <h2>⚡ XRP Swing</h2>
      <div class="header-actions">
        <span v-if="status" :class="['verdict-badge',
          `v-${(status.setup?.verdict || 'WATCHING').toLowerCase().replace('_','-')}`,
          ['ENTRY_READY','SHADOW_ENTRY'].includes(status.setup?.verdict) ? 'badge-pulse' : '']">
          {{ verdictLabel(status.setup?.verdict) }}
        </span>
        <button class="refresh-btn" @click="evaluate()" :disabled="evaluating" :title="t('xrp.eval_tip')">
          {{ evaluating ? '…' : '↻' }}
        </button>
      </div>
    </div>

    <!-- ── Auto-bot status bar ──────────────────────────────────────────────── -->
    <div class="auto-bar" :class="autoStatus?.enabled ? 'auto-on' : 'auto-off'">
      <div class="auto-left">
        <span class="auto-dot" :class="autoStatus?.enabled ? 'dot-on' : 'dot-off'"></span>
        <span class="auto-label">{{ t('xrp.auto_bot_title') }}</span>
        <span class="auto-state">{{ autoStatus?.enabled ? t('xrp.auto_enabled') : t('xrp.auto_disabled') }}</span>
        <span v-if="autoStatus?.verdict"
              :class="['auto-verdict-chip', `v-${(autoStatus.verdict).toLowerCase().replace('_','-')}`]">
          {{ verdictLabel(autoStatus.verdict) }}
        </span>
      </div>
      <div class="auto-right">
        <template v-if="!autoStatus?.enabled">
          <input type="number" v-model.number="autoSizeUsd"
                 class="auto-size-input" placeholder="300" min="10" max="10000" step="10"
                 :title="t('xrp.auto_size_lbl')" />
          <button class="auto-btn auto-enable-btn" @click="enableAuto" :disabled="autoActing">
            {{ t('xrp.auto_enable_btn') }}
          </button>
        </template>
        <button v-else class="auto-btn auto-disable-btn" @click="disableAuto" :disabled="autoActing">
          {{ t('xrp.auto_disable_btn') }}
        </button>
      </div>
    </div>
    <!-- Note below bar -->
    <div v-if="autoStatus?.enabled" class="auto-note">
      <span v-if="autoStatus.has_active_trade">{{ t('xrp.auto_monitoring') }}</span>
      <span v-else>{{ t('xrp.auto_waiting') }}</span>
    </div>

    <!-- ── Stale macro warning ─────────────────────────────────────────────── -->
    <div v-if="status?.macro_stale" class="stale-banner">
      ⚠ {{ t('xrp.stale_warning', { n: Math.round(status.macro_age_minutes) }) }}
    </div>

    <div v-if="loading" class="loading-msg">{{ t('xrp.loading') }}</div>

    <template v-else-if="status">

      <!-- ── Shadow Entry Banner ─────────────────────────────────────────── -->
      <div v-if="status.setup?.verdict === 'SHADOW_ENTRY'" class="shadow-banner">
        <span class="shadow-icon">⚡</span>
        <div class="shadow-text">
          <strong>{{ t('xrp.shadow_title') }}</strong>
          <span>{{ t('xrp.shadow_sub') }}</span>
        </div>
        <span class="shadow-tag">{{ t('xrp.shadow_discretion') }}</span>
      </div>

      <!-- ── Score bar ────────────────────────────────────────────────────── -->
      <div class="score-section">
        <div class="score-row">
          <span class="score-lbl">{{ t('xrp.score') }}</span>
          <div class="score-right">
            <span class="xrp-live-price" v-if="status.setup?.xrp_price">
              XRP <strong>${{ fmtPrice(status.setup.xrp_price) }}</strong>
            </span>
            <span class="score-val">{{ status.setup?.score ?? 0 }}<span class="score-max">/100</span></span>
          </div>
        </div>
        <div class="score-bar-bg">
          <div class="score-bar-fill"
               :style="{ width: (status.setup?.score ?? 0) + '%', background: scoreColor(status.setup?.score ?? 0) }">
          </div>
        </div>
        <!-- Gate summary pills -->
        <div class="gate-pills">
          <span :class="['gpill', status.setup?.gate_btc_sma50 ? 'gp-pass' : 'gp-fail']">BTC/SMA50</span>
          <span :class="['gpill', status.setup?.gate_dom_falling ? 'gp-pass' : 'gp-fail']">BTC.D</span>
          <span :class="['gpill', status.setup?.gate_fg_recovering ? 'gp-pass' : 'gp-fail']">F&G</span>
          <span :class="['gpill', status.setup?.gate_btc_weekly_green ? 'gp-pass' : 'gp-fail']">Weekly</span>
          <span class="gpill gp-count">
            {{ [status.setup?.gate_btc_sma50, status.setup?.gate_dom_falling,
                status.setup?.gate_fg_recovering, status.setup?.gate_btc_weekly_green
               ].filter(Boolean).length }} / 4
          </span>
        </div>
      </div>

      <!-- ── 2-column layout ─────────────────────────────────────────────── -->
      <div class="two-col">

        <!-- ── LEFT: Macro Gate ─────────────────────────────────────────── -->
        <section class="gate-section">
          <div class="section-title">{{ t('xrp.macro_gate') }}</div>
          <div class="gate-list">
            <div class="gate-item" :class="status.setup?.gate_btc_sma50 ? 'gate-pass' : 'gate-fail'">
              <span class="gate-icon">{{ status.setup?.gate_btc_sma50 ? '✅' : '❌' }}</span>
              <span class="gate-label">{{ t('xrp.btc_sma50') }}</span>
              <span class="gate-val" v-if="status.setup?.btc_price">${{ fmt(status.setup.btc_price) }}</span>
            </div>
            <div class="gate-item" :class="status.setup?.gate_dom_falling ? 'gate-pass' : 'gate-fail'">
              <span class="gate-icon">{{ status.setup?.gate_dom_falling ? '✅' : '❌' }}</span>
              <span class="gate-label">{{ t('xrp.dom_falling') }}</span>
              <div class="gate-val-col" v-if="status.setup?.btc_dom">
                <span class="gate-val">{{ status.setup.btc_dom.toFixed(2) }}%</span>
                <span class="gate-delta" v-if="status.dom_3d_change != null"
                      :class="status.dom_3d_change < -0.15 ? 'delta-good' : status.dom_3d_change > 0 ? 'delta-bad' : 'delta-flat'">
                  {{ status.dom_3d_change > 0 ? '+' : '' }}{{ status.dom_3d_change.toFixed(2) }}pp 3d
                </span>
                <span class="gate-threshold" v-if="!status.setup?.gate_dom_falling">
                  {{ status.setup.btc_dom > 54 ? `need ≤54% or −0.15pp` : '' }}
                </span>
              </div>
            </div>
            <div class="gate-item gate-fg" :class="status.setup?.gate_fg_recovering ? 'gate-pass' : 'gate-fail'">
              <span class="gate-icon">{{ status.setup?.gate_fg_recovering ? '✅' : '❌' }}</span>
              <span class="gate-label">{{ t('xrp.fg_gate') }}</span>
              <div class="gate-val-col" v-if="status.setup?.fg_value != null">
                <span class="gate-val">{{ status.setup.fg_value }}</span>
                <span class="gate-delta" v-if="status.fg_3d_change != null"
                      :class="status.fg_3d_change >= 2 ? 'delta-good' : status.fg_3d_change < 0 ? 'delta-bad' : 'delta-flat'">
                  {{ status.fg_3d_change >= 0 ? '+' : '' }}{{ status.fg_3d_change }} 3d
                </span>
                <!-- F&G zone indicator -->
                <span class="fg-zone" :class="fgZoneClass(status.setup.fg_value, status.fg_3d_change)">
                  {{ fgZoneLabel(status.setup.fg_value, status.fg_3d_change) }}
                </span>
              </div>
            </div>
            <div class="gate-item" :class="status.setup?.gate_btc_weekly_green ? 'gate-pass' : 'gate-fail'">
              <span class="gate-icon">{{ status.setup?.gate_btc_weekly_green ? '✅' : '❌' }}</span>
              <span class="gate-label">{{ t('xrp.btc_weekly') }}</span>
            </div>
          </div>

          <!-- ── Key levels ──────────────────────────────────────────────── -->
          <div class="section-title" style="margin-top:1.1rem">{{ t('xrp.key_levels') }}</div>
          <div class="levels-grid">
            <div class="level-col">
              <div class="level-col-lbl support-lbl">{{ t('xrp.support') }}</div>
              <div v-for="s in (status.setup?.key_levels?.support || [0.88, 0.95, 1.00])"
                   :key="s" class="level-item support-item">
                <span class="level-dot sup"></span>
                ${{ s.toFixed(2) }}
              </div>
            </div>
            <div class="level-col">
              <div class="level-col-lbl res-lbl">{{ t('xrp.resistance') }}</div>
              <div v-for="r in (status.setup?.key_levels?.resistance || [1.25, 1.50, 2.00]).slice(0,3)"
                   :key="r" class="level-item res-item">
                <span class="level-dot res"></span>
                ${{ r.toFixed(2) }}
              </div>
            </div>
          </div>
        </section>

        <!-- ── RIGHT: XRP Technicals ────────────────────────────────────── -->
        <section class="tech-section">
          <div class="section-title">{{ t('xrp.technicals') }}</div>
          <div class="tech-grid">
            <div class="tech-item">
              <span class="tech-lbl">{{ t('xrp.price_lbl') }}</span>
              <span class="tech-val">${{ status.setup?.xrp_price ? fmtPrice(status.setup.xrp_price) : '—' }}</span>
            </div>
            <div class="tech-item">
              <span class="tech-lbl">RSI 4H</span>
              <span class="tech-val" :class="rsiClass(status.setup?.xrp_rsi_4h)">
                {{ status.setup?.xrp_rsi_4h ?? '—' }}
              </span>
            </div>
            <div class="tech-item">
              <span class="tech-lbl">RSI 1D</span>
              <span class="tech-val" :class="rsiClass(status.setup?.xrp_rsi_1d)">
                {{ status.setup?.xrp_rsi_1d ?? '—' }}
              </span>
            </div>
            <div class="tech-item">
              <span class="tech-lbl">EMA 200</span>
              <span class="tech-val">${{ status.setup?.xrp_ema200 ? fmtPrice(status.setup.xrp_ema200) : '—' }}</span>
            </div>
            <div class="tech-item">
              <span class="tech-lbl">{{ t('xrp.vs_ema') }}</span>
              <span class="tech-val" :class="(status.setup?.xrp_ema200_pct ?? 0) > 0 ? 'pos' : 'neg'">
                {{ status.setup?.xrp_ema200_pct != null
                   ? ((status.setup.xrp_ema200_pct > 0 ? '+' : '') + status.setup.xrp_ema200_pct.toFixed(1) + '%')
                   : '—' }}
              </span>
            </div>
            <div class="tech-item">
              <span class="tech-lbl">{{ t('xrp.volume_lbl') }}</span>
              <span class="tech-val" :class="(status.setup?.xrp_volume_ratio ?? 1) >= 1.5 ? 'pos' : ''">
                {{ status.setup?.xrp_volume_ratio != null ? status.setup.xrp_volume_ratio.toFixed(1) + 'x' : '—' }}
              </span>
            </div>
          </div>

          <!-- Setup type chip -->
          <div v-if="status.setup?.setup_type" class="setup-chip">
            <span class="setup-type-badge">{{ t('xrp.setup_lbl') }} {{ status.setup.setup_type }}</span>
          </div>

          <!-- Setup description — Arabic when locale is ar, English otherwise -->
          <p class="setup-desc">{{ setupDesc }}</p>

          <div class="eval-time" v-if="status.setup?.evaluated_at">
            {{ t('xrp.updated') }} {{ relTime(status.setup.evaluated_at) }}
          </div>
        </section>
      </div>

      <!-- ── Active Trade Monitor ──────────────────────────────────────────── -->
      <template v-if="status.active_trade">
        <div class="section-divider"></div>

        <!-- Header: title + duration + big P&L -->
        <div class="monitor-hdr">
          <div class="monitor-title-row">
            <span class="section-title" style="margin-bottom:0">
              {{ t('xrp.open_trade_hdr') }} {{ status.active_trade.setup_type }}
            </span>
            <span class="duration-chip">⏱ {{ tradeDuration }}</span>
          </div>
          <div class="monitor-pnl" :class="(status.active_trade.live_pnl_pct ?? 0) >= 0 ? 'mp-pos' : 'mp-neg'">
            <span class="mp-pct">
              {{ status.active_trade.live_pnl_pct != null
                 ? ((status.active_trade.live_pnl_pct >= 0 ? '+' : '') + status.active_trade.live_pnl_pct.toFixed(2) + '%')
                 : '—' }}
            </span>
            <span class="mp-usd" v-if="status.active_trade.live_pnl_usd != null">
              {{ (status.active_trade.live_pnl_usd >= 0 ? '+$' : '-$') + Math.abs(status.active_trade.live_pnl_usd).toFixed(2) }}
            </span>
            <span class="mp-live">
              {{ t('xrp.live_lbl') }}: ${{ status.active_trade.live_price ? fmtPrice(status.active_trade.live_price) : '—' }}
            </span>
          </div>
        </div>

        <!-- P&L Sparkline (builds up as the session polls) -->
        <div class="spark-wrap" v-if="pnlHistory.length >= 3">
          <div class="spark-label">{{ t('xrp.monitor_trend') }}</div>
          <svg class="spark-svg" viewBox="0 0 300 50" preserveAspectRatio="none"
               xmlns="http://www.w3.org/2000/svg">
            <!-- Zero line -->
            <line x1="0" :y1="sparkZeroY" x2="300" :y2="sparkZeroY"
                  stroke="#4a5568" stroke-width="0.8" stroke-dasharray="3,3"/>
            <!-- Area fill -->
            <path :d="sparkAreaPath"
                  :fill="sparkPositive ? 'rgba(104,211,145,0.14)' : 'rgba(252,129,129,0.11)'" />
            <!-- Trend line -->
            <path :d="sparkLinePath"
                  :stroke="sparkPositive ? '#68d391' : '#fc8181'"
                  stroke-width="1.8" fill="none" stroke-linejoin="round" stroke-linecap="round"/>
            <!-- Last point dot -->
            <circle :cx="sparkLastX" :cy="sparkLastY" r="3.5"
                    :fill="sparkPositive ? '#68d391' : '#fc8181'"/>
          </svg>
          <div class="spark-axis">
            <span :class="pnlHistory[0].v >= 0 ? 'pos' : 'neg'">
              {{ (pnlHistory[0].v >= 0 ? '+' : '') + pnlHistory[0].v.toFixed(1) }}%
            </span>
            <span :class="sparkPositive ? 'pos' : 'neg'">
              {{ (pnlHistory[pnlHistory.length-1].v >= 0 ? '+' : '') + pnlHistory[pnlHistory.length-1].v.toFixed(1) }}%
            </span>
          </div>
        </div>

        <!-- Price Runway: SL ──── Entry ──── TP1 ──── TP2 -->
        <div class="runway-outer" v-if="runway">
          <div class="runway-bar">
            <!-- Colored zones -->
            <div class="rwb-zone rwb-red"    :style="{ width: runway.entryPct + '%' }"></div>
            <div class="rwb-zone rwb-yellow" :style="{ width: (runway.tp1Pct - runway.entryPct) + '%' }"></div>
            <div class="rwb-zone rwb-green"  :style="{ width: (100 - runway.tp1Pct) + '%' }"></div>
            <!-- Level ticks -->
            <div class="rwb-tick" :style="{ left: runway.entryPct + '%' }"></div>
            <div class="rwb-tick" :style="{ left: runway.tp1Pct   + '%' }"></div>
            <!-- Current price dot -->
            <div class="rwb-dot" :class="runway.aboveEntry ? 'rwb-profit' : 'rwb-loss'"
                 :style="{ left: runway.curPct + '%' }">
              <div class="rwb-dot-ring"></div>
              <div class="rwb-dot-core"></div>
              <div class="rwb-dot-label">
                ${{ status.active_trade.live_price ? fmtPrice(status.active_trade.live_price) : '—' }}
              </div>
            </div>
          </div>
          <!-- Level labels -->
          <div class="runway-labels">
            <span class="rwl rwl-start">
              <span class="rwl-name">{{ t('xrp.stop_lbl') }}</span>
              <span class="rwl-price neg">${{ fmtPrice(status.active_trade.stop_current) }}</span>
            </span>
            <span class="rwl rwl-abs" :style="{ left: runway.entryPct + '%' }">
              <span class="rwl-name">{{ t('xrp.avg_entry') }}</span>
              <span class="rwl-price">${{ fmtPrice(status.active_trade.avg_entry) }}</span>
            </span>
            <span class="rwl rwl-abs" :style="{ left: runway.tp1Pct + '%' }">
              <span class="rwl-name pos">TP1</span>
              <span class="rwl-price pos">${{ fmtPrice(status.active_trade.tp1_price) }}</span>
            </span>
            <span class="rwl rwl-end">
              <span class="rwl-name pos">TP2</span>
              <span class="rwl-price pos">${{ fmtPrice(status.active_trade.tp2_price) }}</span>
            </span>
          </div>
          <!-- Risk / Reward metrics -->
          <div class="rr-row">
            <span class="rr-item" v-if="runway.pctToStop">
              <span class="rr-lbl">{{ t('xrp.monitor_to_stop') }}</span>
              <span class="rr-val neg">−{{ runway.pctToStop }}%</span>
            </span>
            <span class="rr-sep" v-if="runway.pctToStop && runway.pctToTP1">·</span>
            <span class="rr-item" v-if="runway.pctToTP1">
              <span class="rr-lbl">{{ t('xrp.monitor_to_tp1') }}</span>
              <span class="rr-val pos">+{{ runway.pctToTP1 }}%</span>
            </span>
            <span class="rr-sep" v-if="runway.rrRatio">·</span>
            <span class="rr-item" v-if="runway.rrRatio">
              <span class="rr-lbl">{{ t('xrp.monitor_rr') }}</span>
              <span class="rr-val">1 : {{ runway.rrRatio }}</span>
            </span>
          </div>
        </div>

        <!-- Trade details + actions -->
        <div class="trade-panel">
          <div class="trade-grid">
            <div class="trade-row">
              <span class="tl">{{ t('xrp.avg_entry') }}</span>
              <span class="tv">${{ fmtPrice(status.active_trade.avg_entry) }}</span>
            </div>
            <div class="trade-row">
              <span class="tl">{{ t('xrp.size_lbl') }}</span>
              <span class="tv">${{ status.active_trade.total_size_usd?.toFixed(0) ?? '—' }}</span>
            </div>
            <div class="trade-row">
              <span class="tl">{{ t('xrp.stop_lbl') }}</span>
              <span class="tv neg">
                ${{ fmtPrice(status.active_trade.stop_current) }}
                <span v-if="status.active_trade.stop_at_be" class="be-badge">BE</span>
                <span v-if="status.active_trade.trailing_active" class="trail-badge">TRAIL</span>
              </span>
            </div>
            <div class="trade-row">
              <span class="tl">TP1</span>
              <span class="tv" :class="status.active_trade.tp1_hit_at ? 'tp-hit' : ''">
                ${{ fmtPrice(status.active_trade.tp1_price) }}
                <span v-if="status.active_trade.tp1_hit_at">✓ +${{ status.active_trade.tp1_pnl_usd?.toFixed(2) }}</span>
              </span>
            </div>
            <div class="trade-row">
              <span class="tl">TP2</span>
              <span class="tv" :class="status.active_trade.tp2_hit_at ? 'tp-hit' : ''">
                ${{ fmtPrice(status.active_trade.tp2_price) }}
                <span v-if="status.active_trade.tp2_hit_at">✓ +${{ status.active_trade.tp2_pnl_usd?.toFixed(2) }}</span>
              </span>
            </div>
            <div class="trade-row">
              <span class="tl">{{ t('xrp.stages_lbl') }}</span>
              <span class="tv">{{ status.active_trade.stages?.length ?? 0 }} / 3</span>
            </div>
          </div>

          <!-- Stages list -->
          <div class="stages-list" v-if="status.active_trade.stages?.length">
            <div v-for="(stage, i) in status.active_trade.stages" :key="i" class="stage-row">
              <span class="stage-num">{{ t('xrp.stage_n', { n: i + 1 }) }}</span>
              <span class="stage-price">${{ fmtPrice(stage.price) }}</span>
              <span class="stage-size">${{ stage.size_usd?.toFixed(0) }}</span>
              <span class="stage-time">{{ shortTime(stage.time) }}</span>
            </div>
          </div>

          <!-- Trade actions -->
          <div class="trade-actions">
            <button v-if="!status.active_trade.tp1_hit_at"
                    class="act-btn tp-btn" @click="markTP(1)" :disabled="acting">
              {{ t('xrp.mark_tp1') }}
            </button>
            <button v-if="status.active_trade.tp1_hit_at && !status.active_trade.tp2_hit_at"
                    class="act-btn tp-btn" @click="markTP(2)" :disabled="acting">
              {{ t('xrp.mark_tp2') }}
            </button>
            <button v-if="(status.active_trade.stages?.length ?? 0) < 3"
                    class="act-btn add-btn" @click="showAddStage = !showAddStage" :disabled="acting">
              {{ t('xrp.add_stage_btn') }}
            </button>
            <button class="act-btn close-btn" @click="showClose = !showClose" :disabled="acting">
              {{ t('xrp.close_trade_btn') }}
            </button>
          </div>

          <!-- Add stage form -->
          <div v-if="showAddStage" class="inline-form">
            <div class="form-title">
              {{ t('xrp.add_stage_title', { n: (status.active_trade.stages?.length ?? 0) + 1 }) }}
            </div>
            <div class="form-row">
              <label>{{ t('xrp.price_lbl') }}</label>
              <input type="number" v-model.number="addStagePrice" placeholder="1.05" step="0.0001" />
            </div>
            <div class="form-row">
              <label>{{ t('xrp.size_usd') }}</label>
              <input type="number" v-model.number="addStageSize" placeholder="200" step="1" />
            </div>
            <div class="form-btns">
              <button class="act-btn tp-btn" @click="submitAddStage" :disabled="acting">
                {{ t('xrp.add_btn') }}
              </button>
              <button class="act-btn" @click="showAddStage = false">{{ t('xrp.cancel_btn') }}</button>
            </div>
          </div>

          <!-- Close form -->
          <div v-if="showClose" class="inline-form">
            <div class="form-title">{{ t('xrp.close_trade_title') }}</div>
            <div class="form-row">
              <label>{{ t('xrp.exit_price') }}</label>
              <input type="number" v-model.number="closePrice"
                     :placeholder="status.active_trade.live_price?.toFixed(4) ?? '1.10'" step="0.0001" />
            </div>
            <div class="form-row">
              <label>{{ t('xrp.reason_lbl') }}</label>
              <select v-model="closeReason">
                <option value="manual">{{ t('xrp.reason_manual') }}</option>
                <option value="sl">{{ t('xrp.reason_sl') }}</option>
                <option value="tp">{{ t('xrp.reason_tp') }}</option>
                <option value="timeout">{{ t('xrp.reason_timeout') }}</option>
              </select>
            </div>
            <div class="form-btns">
              <button class="act-btn close-btn" @click="submitClose" :disabled="acting">
                {{ t('xrp.confirm_close') }}
              </button>
              <button class="act-btn" @click="showClose = false">{{ t('xrp.cancel_btn') }}</button>
            </div>
          </div>
        </div>
      </template>

      <!-- ── No active trade ───────────────────────────────────────────────── -->
      <template v-else>
        <div class="section-divider"></div>
        <div class="no-trade-row">
          <span class="no-trade-lbl">{{ t('xrp.no_active_trade') }}</span>
          <button class="act-btn add-btn" @click="showOpenForm = !showOpenForm">
            {{ t('xrp.open_trade_btn') }}
          </button>
        </div>

        <div v-if="showOpenForm" class="inline-form">
          <div class="form-title">{{ t('xrp.open_trade_form') }}</div>
          <div class="form-row">
            <label>{{ t('xrp.setup_type_lbl') }}</label>
            <select v-model="newSetupType">
              <option value="A">{{ t('xrp.setup_a') }}</option>
              <option value="B">{{ t('xrp.setup_b') }}</option>
              <option value="C">{{ t('xrp.setup_c') }}</option>
            </select>
          </div>
          <div class="form-row">
            <label>{{ t('xrp.entry_price') }}</label>
            <input type="number" v-model.number="newEntryPrice" placeholder="1.05" step="0.0001" />
          </div>
          <div class="form-row">
            <label>{{ t('xrp.stage1_size') }}</label>
            <input type="number" v-model.number="newSize" placeholder="300" step="1" />
          </div>
          <div class="form-row">
            <label>{{ t('xrp.stop_loss') }}</label>
            <input type="number" v-model.number="newStop" placeholder="0.99" step="0.0001" />
          </div>
          <div class="form-row">
            <label>TP1</label>
            <input type="number" v-model.number="newTP1" placeholder="1.18" step="0.0001" />
          </div>
          <div class="form-row">
            <label>TP2</label>
            <input type="number" v-model.number="newTP2" placeholder="1.35" step="0.0001" />
          </div>
          <div class="form-row">
            <label>{{ t('xrp.notes_lbl') }}</label>
            <input type="text" v-model="newNotes" :placeholder="t('xrp.notes_ph')" />
          </div>
          <div class="form-btns">
            <button class="act-btn tp-btn" @click="submitOpenTrade" :disabled="acting">
              {{ t('xrp.open_btn') }}
            </button>
            <button class="act-btn" @click="showOpenForm = false">{{ t('xrp.cancel_btn') }}</button>
          </div>
        </div>
      </template>

      <!-- ── Trade History ──────────────────────────────────────────────────── -->
      <div class="section-divider"></div>
      <div class="section-title history-hdr" @click="showHistory = !showHistory">
        {{ t('xrp.history_title') }}
        <span class="history-toggle">{{ showHistory ? '▲' : '▼' }}</span>
      </div>

      <div v-if="showHistory">
        <div v-if="!history.length" class="empty">{{ t('xrp.no_history') }}</div>
        <div v-else class="history-table-wrap">
          <table class="history-table">
            <thead>
              <tr>
                <th>{{ t('xrp.col_setup') }}</th>
                <th>{{ t('xrp.col_entry') }}</th>
                <th>{{ t('xrp.col_exit') }}</th>
                <th>{{ t('xrp.col_pnl') }}</th>
                <th>{{ t('xrp.col_status') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="trade in history" :key="trade.id">
                <td><span class="setup-badge">{{ trade.setup_type ?? '—' }}</span></td>
                <td>${{ trade.avg_entry ? fmtPrice(trade.avg_entry) : '—' }}</td>
                <td>${{ trade.exit_price ? fmtPrice(trade.exit_price) : '—' }}</td>
                <td :class="(trade.final_pnl_usd ?? 0) >= 0 ? 'pos' : 'neg'">
                  {{ trade.final_pnl_usd != null
                     ? ((trade.final_pnl_usd >= 0 ? '+' : '') + '$' + trade.final_pnl_usd.toFixed(2))
                     : '—' }}
                </td>
                <td class="status-cell">{{ statusLabel(trade.status) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

    </template>

    <div v-else class="empty">{{ t('xrp.no_data') }}</div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const { t, locale } = useI18n()

const status     = ref(null)
const history    = ref([])
const loading    = ref(true)
const evaluating = ref(false)
const acting     = ref(false)

const autoStatus  = ref(null)
const autoSizeUsd = ref(300)
const autoActing  = ref(false)

const pnlHistory  = ref([])   // [{ t: ms, v: pnl_pct }] — up to 40 readings

const showOpenForm  = ref(false)
const showAddStage  = ref(false)
const showClose     = ref(false)
const showHistory   = ref(false)

const newSetupType  = ref('B')
const newEntryPrice = ref(null)
const newSize       = ref(300)
const newStop       = ref(null)
const newTP1        = ref(null)
const newTP2        = ref(null)
const newNotes      = ref('')

const addStagePrice = ref(null)
const addStageSize  = ref(null)

const closePrice  = ref(null)
const closeReason = ref('manual')

// ── Computed ───────────────────────────────────────────────────────────────

const setupDesc = computed(() => {
  const s = status.value?.setup
  if (!s) return ''
  const type = s.setup_type   // A | B | C | null
  if (locale.value === 'ar') {
    const key = type ? `xrp.desc_${type.toLowerCase()}` : 'xrp.desc_none'
    return t(key)
  }
  // English: use backend-generated description (most precise)
  return s.setup_desc || t('xrp.desc_none')
})

// ── Trade monitor computeds ────────────────────────────────────────────────

const tradeDuration = computed(() => {
  const tr = status.value?.active_trade
  if (!tr?.opened_at) return ''
  const iso = tr.opened_at.includes('Z') ? tr.opened_at : tr.opened_at + 'Z'
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (mins < 60) return `${mins}m`
  return `${Math.floor(mins / 60)}h ${mins % 60}m`
})

const runway = computed(() => {
  const tr = status.value?.active_trade
  if (!tr) return null
  const stop  = tr.stop_current
  const entry = tr.avg_entry
  const tp1   = tr.tp1_price
  const tp2   = tr.tp2_price
  const cur   = tr.live_price
  if (!stop || !tp2 || stop >= tp2) return null
  const range = tp2 - stop
  const pct   = v => Math.max(0, Math.min(100, ((v - stop) / range) * 100))
  const curPct = cur != null ? pct(cur) : pct(entry)
  return {
    entryPct: pct(entry),
    tp1Pct:   pct(tp1),
    curPct,
    aboveEntry:  cur != null ? cur >= entry : null,
    pctToStop:   cur != null ? Math.abs(((cur - stop) / stop) * 100).toFixed(1) : null,
    pctToTP1:    cur != null && tp1 > cur ? ((tp1 - cur) / cur * 100).toFixed(1) : null,
    rrRatio:     (tp1 && entry && stop && entry > stop)
                   ? ((tp1 - entry) / (entry - stop)).toFixed(1) : null,
  }
})

// Sparkline helpers (viewBox 300 × 50)
const _SW = 300, _SH = 50

function _sparkMinMax() {
  const h = pnlHistory.value
  if (!h.length) return { min: -1, max: 1 }
  const vals = h.map(x => x.v)
  const min = Math.min(...vals, 0)
  const max = Math.max(...vals, 0)
  return { min, max: max === min ? max + 0.5 : max }
}

function _sy(v) {
  const { min, max } = _sparkMinMax()
  return _SH - ((v - min) / (max - min)) * _SH
}

function _sx(i) {
  return (i / Math.max(pnlHistory.value.length - 1, 1)) * _SW
}

const sparkLinePath = computed(() => {
  const h = pnlHistory.value
  if (h.length < 2) return ''
  return h.map((p, i) => `${i === 0 ? 'M' : 'L'}${_sx(i).toFixed(1)},${_sy(p.v).toFixed(1)}`).join(' ')
})

const sparkAreaPath = computed(() => {
  const h = pnlHistory.value
  if (h.length < 2) return ''
  const z = _sy(0).toFixed(1)
  const pts = h.map((p, i) => `${_sx(i).toFixed(1)},${_sy(p.v).toFixed(1)}`).join(' L')
  return `M${_sx(0).toFixed(1)},${z} L${pts} L${_sx(h.length - 1).toFixed(1)},${z} Z`
})

const sparkZeroY   = computed(() => _sy(0).toFixed(1))
const sparkLastX   = computed(() => { const h = pnlHistory.value; return h.length ? _sx(h.length - 1).toFixed(1) : '0' })
const sparkLastY   = computed(() => { const h = pnlHistory.value; return h.length ? _sy(h[h.length - 1].v).toFixed(1) : '25' })
const sparkPositive = computed(() => { const h = pnlHistory.value; return h.length ? h[h.length - 1].v >= 0 : true })

// ── API calls ──────────────────────────────────────────────────────────────

async function fetchAutoStatus() {
  try {
    const r = await fetch('/api/xrp-swing/auto-status')
    autoStatus.value = await r.json()
  } catch (e) {
    console.error('Auto-status fetch failed', e)
  }
}

async function enableAuto() {
  autoActing.value = true
  try {
    await fetch('/api/xrp-swing/auto/enable', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ size_usd: autoSizeUsd.value }),
    })
    await fetchAutoStatus()
  } finally {
    autoActing.value = false
  }
}

async function disableAuto() {
  autoActing.value = true
  try {
    await fetch('/api/xrp-swing/auto/disable', { method: 'POST' })
    await fetchAutoStatus()
  } finally {
    autoActing.value = false
  }
}

async function fetchStatus() {
  try {
    const r = await fetch('/api/xrp-swing/status')
    status.value = await r.json()
    const tr = status.value?.active_trade
    if (tr?.live_pnl_pct != null) {
      pnlHistory.value.push({ t: Date.now(), v: tr.live_pnl_pct })
      if (pnlHistory.value.length > 40) pnlHistory.value.shift()
    } else if (!tr) {
      pnlHistory.value = []
    }
  } catch (e) {
    console.error('XRP Swing status fetch failed', e)
  }
}

async function fetchHistory() {
  try {
    const r = await fetch('/api/xrp-swing/trades?limit=20')
    history.value = await r.json()
  } catch (e) {
    console.error('XRP Swing history fetch failed', e)
  }
}

async function evaluate() {
  evaluating.value = true
  try {
    await fetch('/api/xrp-swing/evaluate', { method: 'POST' })
    await fetchStatus()
  } finally {
    evaluating.value = false
  }
}

async function markTP(n) {
  if (!status.value?.active_trade) return
  const price = status.value.active_trade.live_price ??
                (n === 1 ? status.value.active_trade.tp1_price : status.value.active_trade.tp2_price)
  acting.value = true
  try {
    await fetch('/api/xrp-swing/hit-tp', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ trade_id: status.value.active_trade.id, tp_num: n, close_price: price }),
    })
    await fetchStatus()
  } finally {
    acting.value = false
  }
}

async function submitAddStage() {
  if (!status.value?.active_trade || !addStagePrice.value || !addStageSize.value) return
  acting.value = true
  try {
    await fetch('/api/xrp-swing/add-stage', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        trade_id: status.value.active_trade.id,
        price: addStagePrice.value,
        size_usd: addStageSize.value,
      }),
    })
    showAddStage.value  = false
    addStagePrice.value = null
    addStageSize.value  = null
    await fetchStatus()
  } finally {
    acting.value = false
  }
}

async function submitClose() {
  if (!status.value?.active_trade || !closePrice.value) return
  acting.value = true
  try {
    await fetch('/api/xrp-swing/close-trade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        trade_id:   status.value.active_trade.id,
        exit_price: closePrice.value,
        reason:     closeReason.value,
      }),
    })
    showClose.value   = false
    closePrice.value  = null
    closeReason.value = 'manual'
    await Promise.all([fetchStatus(), fetchHistory()])
  } finally {
    acting.value = false
  }
}

async function submitOpenTrade() {
  if (!newEntryPrice.value || !newStop.value || !newTP1.value || !newTP2.value) return
  acting.value = true
  try {
    await fetch('/api/xrp-swing/open-trade', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        setup_type:      newSetupType.value,
        stage1_price:    newEntryPrice.value,
        stage1_size_usd: newSize.value,
        stop:            newStop.value,
        tp1:             newTP1.value,
        tp2:             newTP2.value,
        notes:           newNotes.value,
      }),
    })
    showOpenForm.value = false
    await fetchStatus()
  } finally {
    acting.value = false
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────

function fgZoneClass(fg, change) {
  if (fg === null || fg === undefined) return ''
  if (fg <= 25 && change >= 2)  return 'fz-bounce'   // bounce — gate passes
  if (fg <= 25 && change < 0)   return 'fz-crash'    // crashing — falling knife
  if (fg <= 25)                 return 'fz-floor'    // at floor, not yet turning
  if (fg >= 40 && change >= 3)  return 'fz-recover'  // recovery — gate passes
  if (fg >= 40)                 return 'fz-near'     // above threshold but not enough change
  return 'fz-dead'                                   // dead zone 26-39 — neither path
}

function fgZoneLabel(fg, change) {
  if (fg === null || fg === undefined) return ''
  if (fg <= 25 && change >= 2)  return t('xrp.fg_zone_bounce')
  if (fg <= 25 && change < 0)   return t('xrp.fg_zone_crash')
  if (fg <= 25)                 return t('xrp.fg_zone_floor')
  if (fg >= 40 && change >= 3)  return t('xrp.fg_zone_recover')
  if (fg >= 40)                 return t('xrp.fg_zone_near')
  return t('xrp.fg_zone_dead')
}

function verdictLabel(v) {
  const map = {
    WATCHING:      t('xrp.verdict_watching'),
    SETUP_FORMING: t('xrp.verdict_forming'),
    ENTRY_READY:   t('xrp.verdict_ready'),
    IN_TRADE:      t('xrp.verdict_in_trade'),
    SHADOW_ENTRY:  t('xrp.verdict_shadow'),
  }
  return map[v] || t('xrp.verdict_watching')
}

function statusLabel(s) {
  const map = {
    open:           t('xrp.status_open'),
    closed_tp:      t('xrp.status_tp'),
    closed_sl:      t('xrp.status_sl'),
    closed_manual:  t('xrp.status_manual'),
    closed_timeout: t('xrp.status_timeout'),
  }
  return map[s] || s
}

function fmt(n) {
  return n ? Number(n).toLocaleString() : '—'
}

function fmtPrice(n) {
  if (n == null) return '—'
  return n < 10
    ? Number(n).toFixed(4)
    : Number(n).toLocaleString(undefined, { maximumFractionDigits: 2 })
}

function scoreColor(s) {
  if (s >= 75) return '#68d391'
  if (s >= 50) return '#f6ad55'
  return '#fc8181'
}

function rsiClass(v) {
  if (v == null) return ''
  if (v < 35) return 'rsi-low'
  if (v > 70) return 'rsi-high'
  return 'rsi-mid'
}

function relTime(iso) {
  if (!iso) return ''
  const diff = (Date.now() - new Date(iso + 'Z').getTime()) / 60000
  if (diff < 1)  return t('xrp.just_now')
  if (diff < 60) return t('xrp.mins_ago', { n: Math.round(diff) })
  return t('xrp.hours_ago', { n: Math.round(diff / 60) })
}

function shortTime(iso) {
  if (!iso) return ''
  const d = new Date(iso.includes('Z') ? iso : iso + 'Z')
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) + ' ' +
         d.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
}

onMounted(() => {
  fetchAutoStatus()
  setInterval(fetchAutoStatus, 30_000)
  setInterval(fetchStatus, 30_000)   // live P&L + sparkline polling
  Promise.all([fetchStatus(), fetchHistory()]).finally(() => {
    loading.value = false
  })
})
</script>

<style scoped>
.xrp-card { color: var(--color-text); }

.header-actions { display: flex; align-items: center; gap: 0.5rem; }

/* Verdict badge */
.verdict-badge {
  font-size: var(--font-size-sm);
  font-weight: 700;
  padding: 0.28rem 0.75rem;
  border-radius: 999px;
  letter-spacing: 0.04em;
}
.v-watching       { background: var(--color-border); color: var(--color-text-secondary); }
.v-setup-forming  { background: var(--color-warning-intense-bg); color: var(--color-warning); }
.v-entry-ready    { background: var(--color-success-emphasis); color: var(--color-success-strong); }
.v-in-trade       { background: var(--color-accent-muted); color: var(--color-accent-strong); }
.v-shadow-entry   { background: #4a3060; color: var(--color-accent-purple-tint); border: 1px solid var(--color-accent-purple)55; }

@keyframes badge-pulse {
  0%, 100% { opacity: 1; box-shadow: 0 0 0 0 currentColor; }
  50%       { opacity: 0.85; box-shadow: 0 0 0 5px transparent; }
}
.badge-pulse { animation: badge-pulse 2s ease-in-out infinite; }

/* Stale macro warning */
.stale-banner {
  background: #3a2a0a;
  border: 1px solid var(--color-warning)55;
  color: var(--color-warning);
  border-radius: 8px;
  padding: 0.55rem 0.85rem;
  font-size: var(--font-size-sm);
  margin-bottom: 0.75rem;
}

/* Shadow Entry Banner */
.shadow-banner {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: linear-gradient(135deg, #2d1b4e 0%, #1e1438 100%);
  border: 1px solid var(--color-accent-purple)66;
  border-radius: 10px;
  padding: 0.85rem 1rem;
  margin-bottom: 0.85rem;
  position: relative;
  overflow: hidden;
}
.shadow-banner::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, var(--color-accent-purple)18, transparent);
  animation: shimmer 2.5s ease-in-out infinite;
}
@keyframes shimmer {
  0%   { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
.shadow-icon { font-size: 1.5rem; flex-shrink: 0; }
.shadow-text { flex: 1; display: flex; flex-direction: column; gap: 0.15rem; }
.shadow-text strong { color: var(--color-accent-purple-tint); font-size: var(--font-size-sm-plus); letter-spacing: 0.02em; }
.shadow-text span   { color: #a78bda; font-size: var(--font-size-sm); }
.shadow-tag {
  font-size: var(--font-size-xs);
  font-weight: 600;
  color: var(--color-accent-purple);
  background: var(--color-accent-purple)22;
  border: 1px solid var(--color-accent-purple)44;
  border-radius: 6px;
  padding: 0.2rem 0.5rem;
  white-space: nowrap;
  flex-shrink: 0;
}

/* Score */
.score-section { margin-bottom: 0.9rem; }
.score-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem; }
.score-lbl { font-size: var(--font-size-xs); color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.06em; }
.score-right { display: flex; align-items: center; gap: 0.85rem; }
.xrp-live-price { font-size: var(--font-size-sm); color: var(--color-text-muted); }
.xrp-live-price strong { color: var(--color-text); font-size: var(--font-size-base); }
.score-val { font-weight: 700; font-size: 1.3rem; color: var(--color-text); }
.score-max { font-size: var(--font-size-xs); color: var(--color-text-muted); font-weight: 400; }
.score-bar-bg   { height: 7px; background: var(--color-border); border-radius: 4px; overflow: hidden; }
.score-bar-fill { height: 100%; border-radius: 4px; transition: width 0.5s ease; }

/* Gate summary pills under score bar */
.gate-pills { display: flex; gap: 0.4rem; margin-top: 0.55rem; flex-wrap: wrap; align-items: center; }
.gpill {
  font-size: var(--font-size-2xs-plus);
  font-weight: 600;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  letter-spacing: 0.03em;
}
.gp-pass { background: #1a3a28; color: var(--color-success-strong); }
.gp-fail { background: #3a1a1a; color: var(--color-danger); }
.gp-count { background: var(--color-border); color: var(--color-text-secondary); margin-inline-start: 0.25rem; }

/* Two-column */
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.85rem;
  margin-bottom: 0.6rem;
}
@media (max-width: 480px) {
  .two-col { grid-template-columns: 1fr; }
}

.section-title {
  font-size: var(--font-size-sm-plus);
  font-weight: 700;
  color: var(--color-accent-strong);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 0.55rem;
}

/* Gates */
.gate-list { display: flex; flex-direction: column; gap: 0.38rem; }
.gate-item {
  display: flex;
  align-items: flex-start;
  gap: 0.4rem;
  font-size: var(--font-size-sm-plus);
  padding: 0.35rem 0.45rem;
  border-radius: 0.35rem;
}
.gate-pass { background: rgba(104, 211, 145, 0.09); }
.gate-fail { background: rgba(252, 129, 129, 0.07); }
.gate-icon  { flex-shrink: 0; font-size: var(--font-size-sm-plus); padding-top: 0.05rem; }
.gate-label { flex: 1; font-size: var(--font-size-sm-plus); }
.gate-val   { font-size: var(--font-size-sm); color: var(--color-text-secondary); }

.gate-val-col { display: flex; flex-direction: column; align-items: flex-end; gap: 0.18rem; }
.gate-delta {
  font-size: var(--font-size-xs);
  font-weight: 600;
  padding: 0.05rem 0.3rem;
  border-radius: 4px;
}
.delta-good { background: #1a3a2844; color: var(--color-success-strong); }
.delta-bad  { background: #3a1a1a44; color: var(--color-danger); }
.delta-flat { background: var(--color-border)44; color: var(--color-text-secondary); }
.gate-threshold { font-size: var(--font-size-2xs-plus); color: var(--color-text-muted); }

/* F&G zone badge */
.fg-zone {
  font-size: var(--font-size-2xs-plus);
  font-weight: 700;
  letter-spacing: 0.03em;
  padding: 0.08rem 0.35rem;
  border-radius: 4px;
  text-transform: uppercase;
  white-space: nowrap;
}
.fz-bounce  { background: #1a4a2a; color: var(--color-success-strong); }   /* ✅ gate passes */
.fz-recover { background: #1a3a28; color: var(--color-success); }   /* ✅ gate passes */
.fz-crash   { background: #4a1a1a; color: var(--color-danger); }   /* falling knife */
.fz-floor   { background: #3a2a0a; color: var(--color-warning); }   /* at floor, not turned yet */
.fz-near    { background: #1a2a3a; color: var(--color-accent-strong); }   /* above 40 but change < 3 */
.fz-dead    { background: #2a2a3a; color: var(--color-text-muted); }   /* 26–39 dead zone */

/* Key levels */
.levels-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.3rem; }
.level-col   { display: flex; flex-direction: column; gap: 0.25rem; }
.level-col-lbl {
  font-size: var(--font-size-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 0.18rem;
}
.support-lbl { color: var(--color-success-strong); }
.res-lbl     { color: var(--color-danger); }
.level-item  { display: flex; align-items: center; gap: 0.3rem; font-size: var(--font-size-sm-plus); }
.level-dot   { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.sup { background: var(--color-success-strong); }
.res { background: var(--color-danger); }
.support-item { color: var(--color-success-tint2); }
.res-item     { color: var(--color-danger-tint); }

/* Technicals */
.tech-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.38rem 0.6rem;
  margin-bottom: 0.6rem;
}
.tech-item { display: flex; flex-direction: column; gap: 0.07rem; }
.tech-lbl  { font-size: var(--font-size-sm); color: var(--color-text-muted); text-transform: uppercase; }
.tech-val  { font-size: 1.05rem; font-weight: 600; }

.rsi-low  { color: var(--color-success-strong); }
.rsi-mid  { color: var(--color-text); }
.rsi-high { color: var(--color-danger); }
.pos      { color: var(--color-success-strong); }
.neg      { color: var(--color-danger); }

.setup-chip { margin: 0.5rem 0 0.3rem; }
.setup-type-badge {
  display: inline-block;
  font-size: var(--font-size-sm);
  font-weight: 700;
  background: var(--color-accent-muted);
  color: var(--color-accent-strong);
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
}
.setup-desc {
  font-size: var(--font-size-sm-plus);
  color: var(--color-text-secondary-bright);
  line-height: 1.6;
  margin: 0.3rem 0 0;
  padding: 0.5rem 0.65rem;
  background: rgba(144, 205, 244, 0.06);
  border-radius: 0.4rem;
  border-inline-start: 3px solid var(--color-accent);
}
.eval-time { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-top: 0.45rem; }

/* Section divider */
.section-divider { height: 1px; background: var(--color-border); margin: 0.9rem 0; }

/* Active trade panel */
.trade-panel { background: rgba(44, 74, 110, 0.12); border-radius: 0.55rem; padding: 0.75rem; }

.pnl-banner {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  padding: 0.5rem 0.75rem;
  border-radius: 0.45rem;
  margin-bottom: 0.65rem;
  flex-wrap: wrap;
}
.pnl-pos { background: rgba(104, 211, 145, 0.15); }
.pnl-neg { background: rgba(252, 129, 129, 0.12); }
.pnl-pct   { font-size: 1.5rem; font-weight: 700; }
.pnl-usd   { font-size: 1.05rem; color: var(--color-text-secondary-bright); }
.pnl-price { margin-inline-start: auto; font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }

.trade-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.3rem 0.85rem;
  margin-bottom: 0.6rem;
}
.trade-row { display: flex; gap: 0.4rem; align-items: baseline; }
.tl { font-size: var(--font-size-sm); color: var(--color-text-muted); min-width: 5rem; }
.tv { font-size: var(--font-size-base); font-weight: 600; }

.be-badge    { font-size: var(--font-size-xs); background: var(--color-warning); color: var(--color-surface); padding: 0.07rem 0.35rem; border-radius: 3px; margin-inline-start: 0.3rem; font-weight: 700; }
.trail-badge { font-size: var(--font-size-xs); background: var(--color-accent); color: var(--color-surface); padding: 0.07rem 0.35rem; border-radius: 3px; margin-inline-start: 0.3rem; font-weight: 700; }
.tp-hit { color: var(--color-success-strong); }

.stages-list { display: flex; flex-direction: column; gap: 0.3rem; margin-bottom: 0.6rem; }
.stage-row {
  display: flex;
  gap: 0.55rem;
  font-size: var(--font-size-sm-plus);
  align-items: center;
  background: rgba(255,255,255,0.04);
  padding: 0.3rem 0.5rem;
  border-radius: 0.35rem;
}
.stage-num   { color: var(--color-text-muted); min-width: 4rem; }
.stage-price { font-weight: 600; }
.stage-size  { color: var(--color-text-secondary); }
.stage-time  { color: var(--color-text-muted); margin-inline-start: auto; font-size: var(--font-size-sm); }

/* Action buttons */
.trade-actions { display: flex; gap: 0.45rem; flex-wrap: wrap; margin-top: 0.6rem; }
.act-btn {
  padding: 0.45rem 0.9rem;
  border-radius: 0.45rem;
  border: 1px solid var(--color-border-muted);
  background: var(--color-border);
  color: var(--color-text-secondary-bright);
  cursor: pointer;
  font-size: var(--font-size-sm-plus);
  font-family: inherit;
  min-height: 40px;
  transition: background 0.15s;
}
.act-btn:active   { background: var(--color-border-muted); }
.act-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.tp-btn    { background: var(--color-success-emphasis); border-color: var(--color-success); color: var(--color-success-tint2); }
.add-btn   { background: var(--color-accent-muted); border-color: var(--color-accent); color: #bee3f8; }
.close-btn { background: var(--color-danger-mid); border-color: var(--color-danger-vivid); color: var(--color-danger-tint); }

/* No active trade */
.no-trade-row { display: flex; align-items: center; justify-content: space-between; padding: 0.3rem 0; }
.no-trade-lbl { font-size: var(--font-size-base); color: var(--color-text-muted); }

/* Inline forms */
.inline-form {
  background: rgba(255,255,255,0.04);
  border-radius: 0.55rem;
  padding: 0.85rem;
  margin-top: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.form-title { font-size: var(--font-size-base); font-weight: 700; color: var(--color-accent-strong); margin-bottom: 0.3rem; }
.form-row {
  display: grid;
  grid-template-columns: 6rem 1fr;
  gap: 0.5rem;
  align-items: center;
}
.form-row label { font-size: var(--font-size-sm-plus); color: var(--color-text-secondary); }
.form-row input,
.form-row select {
  background: var(--color-surface);
  border: 1px solid var(--color-border-muted);
  color: var(--color-text);
  padding: 0.38rem 0.6rem;
  border-radius: 0.4rem;
  font-size: var(--font-size-sm-plus);
  font-family: inherit;
  min-height: 36px;
}
.form-btns { display: flex; gap: 0.45rem; margin-top: 0.3rem; }

/* History */
.history-hdr { cursor: pointer; user-select: none; }
.history-toggle { font-size: var(--font-size-sm); color: var(--color-text-muted); margin-inline-start: 0.4rem; }
.history-table-wrap { overflow-x: auto; -webkit-overflow-scrolling: touch; margin-top: 0.4rem; }
.history-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--font-size-sm-plus);
  min-width: 340px;
}
.history-table th {
  text-align: start;
  color: var(--color-text-secondary);
  font-weight: 600;
  padding: 0.4rem 0.6rem;
  font-size: var(--font-size-sm-plus);
}
.history-table td { padding: 0.4rem 0.6rem; border-top: 1px solid var(--color-border); }
.setup-badge {
  font-size: var(--font-size-sm);
  font-weight: 700;
  background: var(--color-border);
  padding: 0.12rem 0.4rem;
  border-radius: 3px;
  color: var(--color-accent-strong);
}
.status-cell { color: var(--color-text-secondary); font-size: var(--font-size-sm-plus); }

.loading-msg { color: var(--color-text-muted); font-size: 1.05rem; padding: 0.6rem 0; }
.empty       { color: var(--color-text-muted); font-size: 1.05rem; margin-top: 0.5rem; }

/* ── Auto-bot bar ─────────────────────────────────────────────────────────── */
.auto-bar {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
  padding: 0.55rem 0.8rem;
  border-radius: 0.55rem;
  margin-bottom: 0.75rem;
  border: 1px solid transparent;
}
.auto-on  { background: rgba(104, 211, 145, 0.08); border-color: rgba(104, 211, 145, 0.25); }
.auto-off { background: rgba(45, 55, 72, 0.5);     border-color: var(--color-border); }

.auto-left  { display: flex; align-items: center; gap: 0.45rem; flex-wrap: wrap; }
.auto-right { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; margin-inline-start: auto; }

/* Pulsing dot */
.auto-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-on  { background: var(--color-success-strong); box-shadow: 0 0 0 2px rgba(104,211,145,0.35); animation: pulse-on 2s infinite; }
.dot-off { background: var(--color-border-muted); }
@keyframes pulse-on {
  0%, 100% { box-shadow: 0 0 0 2px rgba(104,211,145,0.35); }
  50%       { box-shadow: 0 0 0 5px rgba(104,211,145,0.12); }
}

.auto-label { font-size: var(--font-size-sm-plus); font-weight: 700; color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.05em; }
.auto-state { font-size: var(--font-size-sm-plus); font-weight: 700; }
.auto-on .auto-state  { color: var(--color-success-strong); }
.auto-off .auto-state { color: var(--color-text-muted); }

.auto-verdict-chip {
  font-size: var(--font-size-xs);
  font-weight: 700;
  padding: 0.12rem 0.5rem;
  border-radius: 999px;
}

.auto-size-input {
  width: 62px;
  background: var(--color-surface);
  border: 1px solid var(--color-border-muted);
  color: var(--color-text);
  padding: 0.3rem 0.45rem;
  border-radius: 0.4rem;
  font-size: var(--font-size-sm);
  font-family: inherit;
  min-height: 34px;
}

.auto-btn {
  padding: 0.3rem 0.7rem;
  border-radius: 0.4rem;
  border: 1px solid var(--color-border-muted);
  background: var(--color-border);
  color: var(--color-text-secondary-bright);
  cursor: pointer;
  font-size: var(--font-size-sm);
  font-family: inherit;
  min-height: 34px;
  transition: background 0.15s;
}
.auto-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.auto-enable-btn  { background: var(--color-success-emphasis); border-color: var(--color-success); color: var(--color-success-tint2); font-weight: 700; }
.auto-disable-btn { background: var(--color-danger-mid); border-color: var(--color-danger-vivid); color: var(--color-danger-tint); }

.auto-note {
  font-size: var(--font-size-sm);
  color: var(--color-text-muted);
  padding: 0.3rem 0.6rem;
  margin-bottom: 0.5rem;
  background: rgba(255,255,255,0.03);
  border-radius: 0.4rem;
  border-inline-start: 3px solid var(--color-border-muted);
}

/* ── Trade Monitor ─────────────────────────────────────────────────────────── */

.monitor-hdr {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-bottom: 0.7rem;
}
.monitor-title-row {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: wrap;
}
.duration-chip {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  background: rgba(255,255,255,0.06);
  border-radius: 999px;
  padding: 0.15rem 0.55rem;
}
.monitor-pnl {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding: 0.4rem 0.7rem;
  border-radius: 0.45rem;
}
.mp-pos { background: rgba(104,211,145,0.12); }
.mp-neg { background: rgba(252,129,129,0.10); }
.mp-pct  { font-size: 1.6rem; font-weight: 800; letter-spacing: -0.01em; }
.mp-pos .mp-pct { color: var(--color-success-strong); }
.mp-neg .mp-pct { color: var(--color-danger); }
.mp-usd  { font-size: 1.05rem; color: var(--color-text-secondary-bright); font-weight: 600; }
.mp-live { font-size: var(--font-size-sm-plus); color: var(--color-text-muted); margin-inline-start: auto; }

/* Sparkline */
.spark-wrap { margin-bottom: 0.75rem; }
.spark-label { font-size: var(--font-size-xs); color: var(--color-text-muted); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.3rem; }
.spark-svg {
  width: 100%;
  height: 60px;
  display: block;
  border-radius: 0.4rem;
  background: rgba(255,255,255,0.025);
}
.spark-axis {
  display: flex;
  justify-content: space-between;
  font-size: var(--font-size-xs);
  color: var(--color-text-muted);
  margin-top: 0.2rem;
}

/* Price Runway */
.runway-outer { margin: 0.5rem 0 0.9rem; }

.runway-bar {
  position: relative;
  height: 14px;
  border-radius: 7px;
  display: flex;
  overflow: visible;
}
.rwb-zone { height: 100%; }
.rwb-zone:first-child { border-radius: 7px 0 0 7px; }
.rwb-zone:last-child  { border-radius: 0 7px 7px 0; }
.rwb-red    { background: rgba(252,129,129,0.38); }
.rwb-yellow { background: rgba(246,173,85,0.38); }
.rwb-green  { background: rgba(104,211,145,0.38); }

.rwb-tick {
  position: absolute;
  top: -3px;
  width: 2px;
  height: calc(100% + 6px);
  background: rgba(255,255,255,0.18);
  transform: translateX(-50%);
  border-radius: 1px;
}

.rwb-dot {
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
}
.rwb-dot-ring {
  position: absolute;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  opacity: 0.3;
  animation: ring-pulse 2s infinite;
}
.rwb-dot-core {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2.5px solid var(--color-surface);
  position: relative;
  z-index: 2;
}
.rwb-profit .rwb-dot-ring { background: var(--color-success-strong); }
.rwb-profit .rwb-dot-core { background: var(--color-success-strong); }
.rwb-loss   .rwb-dot-ring { background: var(--color-danger); }
.rwb-loss   .rwb-dot-core { background: var(--color-danger); }

@keyframes ring-pulse {
  0%, 100% { transform: scale(1); opacity: 0.3; }
  50%       { transform: scale(1.4); opacity: 0.12; }
}

.rwb-dot-label {
  position: absolute;
  top: -26px;
  font-size: var(--font-size-xs);
  font-weight: 700;
  white-space: nowrap;
  color: var(--color-text);
  background: rgba(26,29,39,0.92);
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  border: 1px solid var(--color-border-muted);
}

/* Runway labels row */
.runway-labels {
  position: relative;
  height: 36px;
  margin-top: 8px;
}
.rwl {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.06rem;
}
.rwl-start { left: 0; align-items: flex-start; }
.rwl-end   { right: 0; align-items: flex-end; }
.rwl-abs   { transform: translateX(-50%); }
.rwl-name  { font-size: var(--font-size-xs); color: var(--color-text-muted); text-transform: uppercase; white-space: nowrap; }
.rwl-price { font-size: var(--font-size-sm); font-weight: 600; white-space: nowrap; }

/* R:R row */
.rr-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.55rem;
  padding: 0.35rem 0.6rem;
  background: rgba(255,255,255,0.03);
  border-radius: 0.4rem;
}
.rr-item { display: flex; gap: 0.3rem; align-items: baseline; }
.rr-lbl  { font-size: var(--font-size-xs); color: var(--color-text-muted); }
.rr-val  { font-size: var(--font-size-sm-plus); font-weight: 700; }
.rr-sep  { color: var(--color-text-subtle); }
</style>
