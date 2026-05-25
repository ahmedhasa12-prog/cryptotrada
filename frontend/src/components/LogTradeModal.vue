<template>
  <teleport to="body">
    <div class="modal-backdrop" @click.self="$emit('close')">
      <div class="modal" role="dialog" aria-modal="true">

        <div class="modal-header">
          <h2>{{ t('modal.title') }}</h2>
          <button class="modal-close" @click="$emit('close')">✕</button>
        </div>

        <form @submit.prevent="submit" class="modal-body">

          <div class="field">
            <label>{{ t('modal.direction') }}</label>
            <div class="type-toggle">
              <button type="button" :class="['type-btn', { active: form.trade_type === 'sell' }]" @click="form.trade_type = 'sell'">
                {{ t('modal.sold') }}
              </button>
              <button type="button" :class="['type-btn', { active: form.trade_type === 'buy' }]" @click="form.trade_type = 'buy'">
                {{ t('modal.bought') }}
              </button>
            </div>
          </div>

          <div class="field-row">
            <div class="field">
              <label>{{ t('modal.amount') }}</label>
              <input v-model.number="form.amount_usdt" type="number" min="0.01" step="0.01" required :placeholder="t('modal.amount_ph')" />
            </div>
            <div class="field">
              <label>{{ t('modal.rate') }}</label>
              <input v-model.number="form.rate_sdg" type="number" min="0.01" step="0.01" required :placeholder="t('modal.rate_ph')" />
            </div>
          </div>

          <div v-if="total" class="total-preview">
            {{ t('modal.total') }} <strong>{{ total }} SDG</strong>
          </div>

          <div class="field">
            <label>{{ t('modal.counterparty') }}</label>
            <input v-model.trim="form.trader_username" type="text" required :placeholder="t('modal.counterparty_ph')" />
          </div>

          <div class="field-row">
            <div class="field">
              <label>{{ t('modal.profit') }} <span class="opt">{{ t('modal.optional') }}</span></label>
              <input v-model.number="form.profit_sdg" type="number" step="0.01" :placeholder="t('modal.profit_ph')" />
            </div>
            <div class="field">
              <label>{{ t('modal.release') }} <span class="opt">{{ t('modal.optional') }}</span></label>
              <input v-model.number="form.release_time_minutes" type="number" min="0" step="1" :placeholder="t('modal.release_ph')" />
            </div>
          </div>

          <div class="field">
            <label>{{ t('modal.bank') }} <span class="opt">{{ t('modal.optional') }}</span></label>
            <input v-model.trim="form.bank_used" type="text" :placeholder="t('modal.bank_ph')" />
          </div>

          <div class="field">
            <label>{{ t('modal.notes') }} <span class="opt">{{ t('modal.optional') }}</span></label>
            <textarea v-model.trim="form.notes" rows="2" :placeholder="t('modal.notes_ph')" />
          </div>

          <p v-if="error" class="form-error">{{ error }}</p>

          <div class="modal-footer">
            <button type="button" class="btn-cancel" @click="$emit('close')">{{ t('modal.cancel') }}</button>
            <button type="submit" class="btn-submit" :disabled="saving">
              {{ saving ? t('modal.saving') : t('modal.submit') }}
            </button>
          </div>

        </form>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { usePlatformStore } from '../stores/platform'
import axios from 'axios'

const { t } = useI18n()
const API   = import.meta.env.VITE_API_BASE || ''
const emit  = defineEmits(['close', 'saved'])
const store = usePlatformStore()

const saving = ref(false)
const error  = ref('')

const form = reactive({
  trade_type: 'sell', amount_usdt: null, rate_sdg: null,
  trader_username: '', profit_sdg: null, release_time_minutes: null,
  bank_used: '', notes: '',
})

if (store.snapshot?.buy_best_rate) form.rate_sdg = store.snapshot.buy_best_rate

const total = computed(() => {
  if (form.amount_usdt > 0 && form.rate_sdg > 0)
    return (form.amount_usdt * form.rate_sdg).toFixed(2)
  return null
})

async function submit() {
  error.value = ''
  saving.value = true
  try {
    await axios.post(`${API}/api/p2p/trades`, {
      trade_type: form.trade_type, amount_usdt: form.amount_usdt,
      rate_sdg: form.rate_sdg, trader_username: form.trader_username,
      profit_sdg: form.profit_sdg || null,
      release_time_minutes: form.release_time_minutes || null,
      bank_used: form.bank_used || null, notes: form.notes || null,
    })
    await store.fetchTodayStats()
    emit('saved'); emit('close')
  } catch (e) {
    error.value = e?.response?.data?.detail ?? t('modal.error_default')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.modal-backdrop {
  position: fixed; inset: 0; background: rgba(0,0,0,0.65);
  z-index: 100; display: flex; align-items: flex-end; justify-content: center;
}
@media (min-width: 600px) { .modal-backdrop { align-items: center; padding: 1rem; } }

.modal {
  background: #1a1d27; border: 1px solid #2d3748;
  border-radius: 1rem 1rem 0 0; width: 100%; max-width: 480px;
  max-height: 92dvh; overflow-y: auto; -webkit-overflow-scrolling: touch;
  padding-bottom: env(safe-area-inset-bottom);
}
@media (min-width: 600px) { .modal { border-radius: 1rem; } }

.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1rem 1.1rem 0.75rem; border-bottom: 1px solid #2d3748;
  position: sticky; top: 0; background: #1a1d27; z-index: 1;
}
.modal-header h2 { font-size: 1rem; font-weight: 700; color: #90cdf4; margin: 0; }
.modal-close {
  background: none; border: none; color: #718096; font-size: 1.1rem;
  cursor: pointer; min-width: 36px; min-height: 36px;
  display: flex; align-items: center; justify-content: center; border-radius: 50%;
}
.modal-body { padding: 1rem 1.1rem; display: flex; flex-direction: column; gap: 0.875rem; }

.field { display: flex; flex-direction: column; gap: 0.35rem; flex: 1; }
.field label { font-size: 0.72rem; color: #a0aec0; text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }
.opt { font-weight: 400; color: #4a5568; text-transform: none; font-size: 0.68rem; }

.field input, .field textarea {
  background: #2d3748; border: 1px solid #4a5568; color: #e2e8f0;
  padding: 0.65rem 0.75rem; border-radius: 0.5rem; font-size: 1rem;
  font-family: inherit; width: 100%; box-sizing: border-box; min-height: 44px; resize: vertical;
}
.field input:focus, .field textarea:focus { outline: none; border-color: #63b3ed; }
.field-row { display: flex; gap: 0.75rem; }

.type-toggle { display: flex; gap: 0.5rem; }
.type-btn {
  flex: 1; min-height: 44px; border-radius: 0.5rem; border: 1px solid #4a5568;
  background: #2d3748; color: #a0aec0; font-size: 0.9rem; cursor: pointer;
}
.type-btn.active { background: #2c4a6e; color: #90cdf4; border-color: #63b3ed; }

.total-preview {
  font-size: 0.875rem; color: #a0aec0; background: #2d3748;
  padding: 0.5rem 0.75rem; border-radius: 0.4rem; margin-top: -0.25rem;
}
.total-preview strong { color: #68d391; }
.form-error {
  font-size: 0.85rem; color: #fc8181; background: #2d1616;
  border: 1px solid #7a2020; border-radius: 0.4rem; padding: 0.5rem 0.75rem; margin: 0;
}
.modal-footer { display: flex; gap: 0.75rem; padding-top: 0.25rem; }
.btn-cancel {
  flex: 1; min-height: 48px; border-radius: 0.5rem; border: 1px solid #4a5568;
  background: #2d3748; color: #a0aec0; font-size: 0.95rem; cursor: pointer;
}
.btn-submit {
  flex: 2; min-height: 48px; border-radius: 0.5rem; border: none;
  background: #2b6cb0; color: #fff; font-size: 0.95rem; font-weight: 600; cursor: pointer;
}
.btn-submit:hover:not(:disabled) { background: #3182ce; }
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
