<template>
  <div class="agent-overview">
    <div class="overview-grid">
      <!-- Insights Summary -->
      <div class="overview-card">
        <h3>{{ t('agents.insights_summary') }}</h3>
        <div class="overview-stats">
          <div class="stat">
            <span class="stat-value">{{ totalInsights }}</span>
            <span class="stat-label">{{ t('agents.total_insights') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ activeWatchlist }}</span>
            <span class="stat-label">{{ t('agents.active_watchlist') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ pendingReviews }}</span>
            <span class="stat-label">{{ t('agents.pending_reviews') }}</span>
          </div>
        </div>
      </div>

      <!-- Market Coverage -->
      <div class="overview-card">
        <h3>{{ t('agents.market_coverage') }}</h3>
        <div class="overview-stats">
          <div class="stat">
            <span class="stat-value">{{ macroCoverage }}%</span>
            <span class="stat-label">{{ t('agents.macro_coverage') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ technicalCoverage }}%</span>
            <span class="stat-label">{{ t('agents.technical_coverage') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ narrativeCoverage }}%</span>
            <span class="stat-label">{{ t('agents.narrative_coverage') }}</span>
          </div>
        </div>
      </div>

      <!-- Recent Activity -->
      <div class="overview-card">
        <h3>{{ t('agents.recent_activity') }}</h3>
        <div class="overview-stats">
          <div class="stat">
            <span class="stat-value">{{ insightsToday }}</span>
            <span class="stat-label">{{ t('agents.insights_today') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ alertsThisWeek }}</span>
            <span class="stat-label">{{ t('agents.alerts_this_week') }}</span>
          </div>
          <div class="stat">
            <span class="stat-value">{{ lastInsightTime }}</span>
            <span class="stat-label">{{ t('agents.last_insight') }}</span>
          </div>
        </div>
      </div>

      <!-- Configuration Summary -->
      <div class="overview-card">
        <h3>{{ t('agents.config_summary') }}</h3>
        <div class="config-list">
          <div class="config-item">
            <span class="config-label">{{ t('agents.auto_refresh') }}</span>
            <span class="config-value">{{ autoRefresh ? t('common.enabled') : t('common.disabled') }}</span>
          </div>
          <div class="config-item">
            <span class="config-label">{{ t('agents.refresh_interval') }}</span>
            <span class="config-value">{{ refreshInterval }}min</span>
          </div>
          <div class="config-item">
            <span class="config-label">{{ t('agents.alert_threshold') }}</span>
            <span class="config-value">{{ alertThreshold }}</span>
          </div>
          <div class="config-item">
            <span class="config-label">{{ t('agents.data_retention') }}</span>
            <span class="config-value">{{ dataRetention }}d</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="overview-actions">
      <router-link :to="`/agents/${agentType}/insights`" class="btn btn-primary">
        {{ t('agents.view_insights') }}
      </router-link>
      <router-link :to="`/agents/${agentType}/watchlist`" class="btn btn-secondary">
        {{ t('agents.view_watchlist') }}
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { usePlatformStore } from '@/stores/platform'

const { t } = useI18n()
const route = useRoute()
const platformStore = usePlatformStore()

const agentType = route.params.type as string
const agent = computed(() => platformStore.agents.find(a => a.agent_type === agentType))

// Mock data - in real implementation, this would come from API
const totalInsights = computed(() => 156)
const activeWatchlist = computed(() => 24)
const pendingReviews = computed(() => 3)
const macroCoverage = computed(() => 95)
const technicalCoverage = computed(() => 87)
const narrativeCoverage = computed(() => 72)
const insightsToday = computed(() => 12)
const alertsThisWeek = computed(() => 8)
const lastInsightTime = computed(() => '5m ago')
const autoRefresh = computed(() => true)
const refreshInterval = computed(() => 5)
const alertThreshold = computed(() => 'Medium')
const dataRetention = computed(() => 90)
</script>

<style scoped>
.agent-overview {
  display: flex;
  flex-direction: column;
  gap: var(--space-6);
}

.overview-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: var(--space-4);
}

@media (min-width: 640px) {
  .overview-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (min-width: 1024px) {
  .overview-grid {
    grid-template-columns: repeat(4, 1fr);
  }
}

.overview-card {
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-5);
}

.overview-card h3 {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin: 0 0 var(--space-4);
}

.overview-stats {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.stat-value {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.stat-value.positive { color: var(--color-success); }
.stat-value.negative { color: var(--color-danger); }
.stat-value.neutral { color: var(--color-text-secondary); }

.stat-label {
  font-size: var(--text-2xs);
  color: var(--color-text-tertiary);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.config-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2) var(--space-3);
  background: var(--color-surface-raised);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.config-label {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.config-value {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
  font-variant-numeric: tabular-nums;
  font-family: var(--font-mono);
}

.overview-actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  padding-top: var(--space-2);
}

@media (max-width: 639px) {
  .overview-actions .btn {
    flex: 1;
  }
}
</style>