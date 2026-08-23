<template>
  <div class="page-view">
    <div class="page-header">
      <h1>{{ t('navigation.settings') }}</h1>
    </div>

    <div class="settings-section">
      <h2>{{ t('status.title') }}</h2>
      <div class="settings-grid">
        <div class="setting-row">
          <span class="setting-label">{{ t('status.mode') }}</span>
          <div class="setting-control">
            <select @change="setMode(($event.target as HTMLSelectElement).value)" :value="mode">
              <option value="manual">{{ t('status.modes.manual') }}</option>
              <option value="semi">{{ t('status.modes.semi') }}</option>
              <option value="full">{{ t('status.modes.full') }}</option>
            </select>
          </div>
        </div>
        <div class="setting-row">
          <span class="setting-label">{{ t('status.availability') }}</span>
          <div class="setting-control">
            <select @change="setAvailability(($event.target as HTMLSelectElement).value)" :value="availability">
              <option value="online">{{ t('status.avail.online') }}</option>
              <option value="slow">{{ t('status.avail.slow') }}</option>
              <option value="offline">{{ t('status.avail.offline') }}</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '@/stores/platform'

const { t } = useI18n()
const platformStore = usePlatformStore()

const mode = computed(() => platformStore.mode)
const availability = computed(() => platformStore.availability)

function setMode(val: string) { platformStore.setMode(val) }
function setAvailability(val: string) { platformStore.setAvailability(val) }
</script>

<style scoped>
.page-view {
  display: flex;
  flex-direction: column;
  gap: var(--space-6, 1.5rem);
  padding: var(--space-6, 1.5rem);
  max-width: 720px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

.page-header h1 {
  font-size: var(--text-3xl, 1.875rem);
  font-weight: var(--font-bold, 700);
  color: var(--color-text-primary, var(--color-text));
  margin: 0;
}

.settings-section {
  background: var(--color-surface, var(--color-bg));
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-lg, 0.5rem);
  padding: var(--space-6, 1.5rem);
}

.settings-section h2 {
  font-size: var(--text-lg, 1.125rem);
  font-weight: var(--font-semibold, 600);
  color: var(--color-text-primary, var(--color-text));
  margin: 0 0 var(--space-4, 1rem) 0;
}

.settings-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-4, 1rem);
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4, 1rem);
}

.setting-label {
  color: var(--color-text-secondary, var(--color-text));
  font-size: var(--text-sm, 0.875rem);
}

.setting-control select {
  padding: var(--space-2, 0.5rem) var(--space-3, 0.75rem);
  border: 1px solid var(--color-border, #e5e7eb);
  border-radius: var(--radius-md, 0.375rem);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: var(--text-sm, 0.875rem);
  cursor: pointer;
}
</style>
