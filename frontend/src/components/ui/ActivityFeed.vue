<template>
  <div class="activity-feed">
    <div v-if="activities.length === 0" class="activity-feed__empty">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
        <path d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
      </svg>
      <p>{{ t('activity_feed.empty') }}</p>
    </div>
    
    <ul v-else class="activity-feed__list" role="list">
      <li
        v-for="activity in displayedActivities"
        :key="activity.id"
        class="activity-feed__item"
        :class="`activity-feed__item--${activity.agent}`"
      >
        <div class="activity-feed__icon" :class="activity.action.toLowerCase()" aria-hidden="true">
          <component :is="actionIcon(activity.action)" />
        </div>
        
        <div class="activity-feed__content">
          <div class="activity-feed__header">
            <span class="activity-feed__agent">{{ agentLabel(activity.agent) }}</span>
            <span class="activity-feed__action">{{ actionLabel(activity.action) }}</span>
            <span class="activity-feed__symbol" v-if="activity.symbol">{{ activity.symbol }}</span>
          </div>
          
          <div class="activity-feed__details" v-if="activity.price || activity.pnl !== undefined">
            <span class="activity-feed__price" v-if="activity.price">
              ${{ formatPrice(activity.price) }}
            </span>
            <span
              v-if="activity.pnl !== undefined"
              class="activity-feed__pnl"
              :class="activity.pnl >= 0 ? 'positive' : 'negative'"
            >
              {{ activity.pnl >= 0 ? '+' : '' }}{{ activity.pnl.toFixed(2) }}%
            </span>
          </div>
        </div>
        
        <time class="activity-feed__time" :datetime="formatISO(activity.time)">
          {{ formatRelativeTime(activity.time) }}
        </time>
      </li>
    </ul>
    
    <div v-if="activities.length > limit" class="activity-feed__more">
      <router-link :to="{ name: 'ActivityFeed' }" class="btn btn-ghost btn-sm">
        {{ t('activity_feed.view_all', { count: activities.length }) }}
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'

const { t } = useI18n()
const router = useRouter()

interface Activity {
  id: number | string
  agent: 'auto_trend' | 'xrp_swing' | 'sol_swing' | 'link_swing' | 'p2p_market' | 'manual'
  action: 'OPENED' | 'CLOSED' | 'TP1_HIT' | 'TP2_HIT' | 'TP3_HIT' | 'STAGE_ADDED' | 'PAUSED' | 'RESUMED' | 'ERROR'
  symbol?: string
  price?: number
  pnl?: number
  time: number
}

interface Props {
  activities: Activity[]
  limit?: number
}

const props = withDefaults(defineProps<Props>(), {
  limit: 10,
})

const displayedActivities = computed(() => props.activities.slice(0, props.limit))

function agentLabel(agent: string): string {
  const labels: Record<string, string> = {
    auto_trend: 'Auto Trend',
    xrp_swing: 'XRP Swing',
    p2p_market: 'P2P Market',
    manual: 'Manual',
  }
  return labels[agent] || agent
}

function actionLabel(action: string): string {
  const labels: Record<string, string> = {
    OPENED: 'Opened',
    CLOSED: 'Closed',
    TP1_HIT: 'TP1 Hit',
    TP2_HIT: 'TP2 Hit',
    TP3_HIT: 'TP3 Hit',
    STAGE_ADDED: 'Stage Added',
    PAUSED: 'Paused',
    RESUMED: 'Resumed',
    ERROR: 'Error',
  }
  return labels[action] || action
}

// Plain objects with a `template` string need Vue's runtime compiler, which
// this Vite build doesn't ship (SFCs are precompiled) — h() renders directly.
const SVG_ATTRS = { width: 16, height: 16, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 2.5 }

const ICON_RENDERERS: Record<string, () => any> = {
  opened: () => h('svg', SVG_ATTRS, [h('polyline', { points: '5 3 19 12 5 21 5 3' })]),
  closed: () => h('svg', SVG_ATTRS, [h('rect', { x: 3, y: 3, width: 18, height: 18, rx: 2 })]),
  tp1_hit: () => h('svg', SVG_ATTRS, [h('path', { d: 'M20 6L9 17l-5-5' })]),
  tp2_hit: () => h('svg', SVG_ATTRS, [h('path', { d: 'M20 6L9 17l-5-5' })]),
  tp3_hit: () => h('svg', SVG_ATTRS, [h('path', { d: 'M20 6L9 17l-5-5' })]),
  stage_added: () => h('svg', SVG_ATTRS, [
    h('line', { x1: 12, y1: 5, x2: 12, y2: 19 }),
    h('line', { x1: 5, y1: 12, x2: 19, y2: 12 }),
  ]),
  paused: () => h('svg', SVG_ATTRS, [
    h('rect', { x: 6, y: 4, width: 4, height: 16 }),
    h('rect', { x: 14, y: 4, width: 4, height: 16 }),
  ]),
  resumed: () => h('svg', SVG_ATTRS, [h('polyline', { points: '5 3 19 12 5 21 5 3' })]),
  error: () => h('svg', SVG_ATTRS, [
    h('circle', { cx: 12, cy: 12, r: 10 }),
    h('line', { x1: 15, y1: 9, x2: 9, y2: 15 }),
    h('line', { x1: 9, y1: 9, x2: 15, y2: 15 }),
  ]),
}

function actionIcon(action: string) {
  return { render: ICON_RENDERERS[action.toLowerCase()] || ICON_RENDERERS.opened }
}

function formatPrice(price: number): string {
  if (price >= 1000) return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  if (price >= 1) return price.toFixed(4)
  return price.toFixed(6)
}

function formatRelativeTime(timestamp: number): string {
  const diff = Date.now() - timestamp
  if (diff < 60000) return `${Math.floor(diff / 1000)}s`
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h`
  return new Date(timestamp).toLocaleDateString()
}

function formatISO(timestamp: number): string {
  return new Date(timestamp).toISOString()
}
</script>

<style scoped>
.activity-feed {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.activity-feed__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-8) var(--space-4);
  text-align: center;
  color: var(--color-text-tertiary);
}

.activity-feed__empty svg {
  margin-bottom: var(--space-3);
  opacity: 0.5;
}

.activity-feed__empty p {
  font-size: var(--text-sm);
  margin: 0;
}

.activity-feed__list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.activity-feed__item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  transition: all var(--transition-fast);
}

.activity-feed__item:hover {
  border-color: var(--color-brand);
  transform: translateX(2px);
}

.activity-feed__item--auto_trend .activity-feed__icon {
  color: var(--color-brand);
}

.activity-feed__item--xrp_swing .activity-feed__icon {
  color: var(--color-accent-purple);
}

.activity-feed__item--p2p_market .activity-feed__icon {
  color: var(--color-success);
}

.activity-feed__item--manual .activity-feed__icon {
  color: var(--color-warning);
}

.activity-feed__icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--radius-md);
  background: var(--color-surface);
  flex-shrink: 0;
}

.activity-feed__icon.opened { background: var(--color-success-bg); color: var(--color-success); }
.activity-feed__icon.closed { background: var(--color-danger-bg); color: var(--color-danger); }
.activity-feed__icon.tp1_hit,
.activity-feed__icon.tp2_hit,
.activity-feed__icon.tp3_hit { background: var(--color-success-bg); color: var(--color-success); }
.activity-feed__icon.stage_added { background: var(--color-brand-subtle); color: var(--color-brand); }
.activity-feed__icon.paused { background: var(--color-warning-bg); color: var(--color-warning); }
.activity-feed__icon.resumed { background: var(--color-success-bg); color: var(--color-success); }
.activity-feed__icon.error { background: var(--color-danger-bg); color: var(--color-danger); }

.activity-feed__content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.activity-feed__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.activity-feed__agent {
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  background: var(--color-surface);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-pill);
}

.activity-feed__action {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.activity-feed__symbol {
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--color-brand);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.activity-feed__details {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-size: var(--text-sm);
}

.activity-feed__price {
  color: var(--color-text-secondary);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.activity-feed__pnl {
  font-weight: var(--font-semibold);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.activity-feed__pnl.positive { color: var(--color-success); }
.activity-feed__pnl.negative { color: var(--color-danger); }

.activity-feed__time {
  font-size: var(--text-2xs);
  color: var(--color-text-tertiary);
  white-space: nowrap;
  flex-shrink: 0;
  margin-top: 2px;
}

.activity-feed__more {
  padding-top: var(--space-2);
  text-align: center;
}

/* RTL support */
[dir="rtl"] .activity-feed__item {
  flex-direction: row-reverse;
}

[dir="rtl"] .activity-feed__header {
  flex-direction: row-reverse;
}
</style>