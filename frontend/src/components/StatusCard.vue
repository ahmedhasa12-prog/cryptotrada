<template>
  <div class="card">
    <div class="card-header">
      <h2>{{ t('status.title') }}</h2>
      <span class="connection-dot" :class="{ connected: store.connected }" :title="store.connected ? 'Live' : 'Disconnected'" />
    </div>

    <div class="status-grid">
      <div class="status-item">
        <label>{{ t('status.mode') }}</label>
        <select :value="store.mode" @change="changeMode($event.target.value)">
          <option value="manual">{{ t('status.modes.manual') }}</option>
          <option value="semi">{{ t('status.modes.semi') }}</option>
          <option value="full">{{ t('status.modes.full') }}</option>
        </select>
      </div>

      <div class="status-item">
        <label>{{ t('status.availability') }}</label>
        <div class="avail-buttons">
          <button
            v-for="opt in availOptions"
            :key="opt.value"
            :class="['avail-btn', { active: store.availability === opt.value }]"
            @click="changeAvail(opt.value)"
          >{{ opt.label }}</button>
        </div>
      </div>
    </div>

    <div v-if="store.isCriticalAlert" class="critical-banner">
      ⚠️ {{ t('status.critical') }}
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../stores/platform'

const { t } = useI18n()
const store = usePlatformStore()

const availOptions = computed(() => [
  { value: 'online',  label: t('status.avail.online')  },
  { value: 'slow',    label: t('status.avail.slow')    },
  { value: 'offline', label: t('status.avail.offline') },
])

async function changeMode(val)  { await store.setMode(val) }
async function changeAvail(val) { await store.setAvailability(val) }
</script>
