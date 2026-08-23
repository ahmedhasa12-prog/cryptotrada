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
  background: var(--color-surface); border: 1px solid var(--color-border);
  border-radius: 1rem 1rem 0 0; width: 100%; max-width: 480px;
  max-height: 92dvh; overflow-y: auto; -webkit-overflow-scrolling: touch;
  padding-bottom: env(safe-area-inset-bottom);
}
@media (min-width: 600px) { .modal { border-radius: 1rem; } }

.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 1rem 1.1rem 0.75rem; border-bottom: 1px solid var(--color-border);
  position: sticky; top: 0; background: var(--color-surface); z-index: 1;
}
.modal-header h2 { font-size: var(--font-size-base); font-weight: 700; color: var(--color-accent-strong); margin: 0; }
.modal-close {
  background: none; border: none; color: var(--color-text-disabled); font-size: 1.1rem;
  cursor: pointer; min-width: 36px; min-height: 36px;
  display: flex; align-items: center; justify-content: center; border-radius: 50%;
}
.modal-body { padding: 1rem 1.1rem; display: flex; flex-direction: column; gap: 0.875rem; }

.field { display: flex; flex-direction: column; gap: 0.35rem; flex: 1; }
.field label { font-size: var(--font-size-xs); color: var(--color-text-secondary); text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }
.opt { font-weight: 400; color: var(--color-text-subtle); text-transform: none; font-size: var(--font-size-2xs-plus); }

.field input, .field textarea {
  background: var(--color-border); border: 1px solid var(--color-border-muted); color: var(--color-text);
  padding: 0.65rem 0.75rem; border-radius: 0.5rem; font-size: var(--font-size-base);
  font-family: inherit; width: 100%; box-sizing: border-box; min-height: 44px; resize: vertical;
}
.field input:focus, .field textarea:focus { outline: none; border-color: var(--color-accent); }
.field-row { display: flex; gap: 0.75rem; }

.type-toggle { display: flex; gap: 0.5rem; }
.type-btn {
  flex: 1; min-height: 44px; border-radius: 0.5rem; border: 1px solid var(--color-border-muted);
  background: var(--color-border); color: var(--color-text-secondary); font-size: var(--font-size-sm-plus); cursor: pointer;
}
.type-btn.active { background: var(--color-accent-muted); color: var(--color-accent-strong); border-color: var(--color-accent); }

.total-preview {
  font-size: var(--font-size-sm); color: var(--color-text-secondary); background: var(--color-border);
  padding: 0.5rem 0.75rem; border-radius: 0.4rem; margin-top: -0.25rem;
}
.total-preview strong { color: var(--color-success-strong); }
.form-error {
  font-size: var(--font-size-sm); color: var(--color-danger); background: var(--color-danger-bg);
  border: 1px solid var(--color-danger-mid); border-radius: 0.4rem; padding: 0.5rem 0.75rem; margin: 0;
}
.modal-footer { display: flex; gap: 0.75rem; padding-top: 0.25rem; }
.btn-cancel {
  flex: 1; min-height: 48px; border-radius: 0.5rem; border: 1px solid var(--color-border-muted);
  background: var(--color-border); color: var(--color-text-secondary); font-size: var(--font-size-sm-plus); cursor: pointer;
}
.btn-submit {
  flex: 2; min-height: 48px; border-radius: 0.5rem; border: none;
  background: #2b6cb0; color: #fff; font-size: var(--font-size-sm-plus); font-weight: 600; cursor: pointer;
}
.btn-submit:hover:not(:disabled) { background: #3182ce; }
.btn-submit:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
