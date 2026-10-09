<template>
  <!-- נספח א' — the signed consent a 9100 declares to the מסלקה. Every path that
       sends a 9100 opens this first: the customer card's "עדכון מהמסלקה", the
       tab's ask form and Nifra's prepared request. The dates come from the signed
       form, never from today (a declaration to a regulator), and the server
       refuses a 9100 without it (api/maslaka.consent_record). -->
  <Teleport to="body">
    <Transition name="mcm" @enter="onEnter">
      <div v-if="show" class="mcm-overlay" @click.self="close">
        <div ref="cardEl" class="mcm-card" role="dialog" aria-modal="true" aria-labelledby="mcm-title">
          <header class="mcm-head">
            <div>
              <h3 id="mcm-title">טופס נספח א'</h3>
              <p class="mcm-sub">
                {{ customerName || 'לקוח' }} · <span class="ltr-number">{{ customerId }}</span>
              </p>
            </div>
            <button class="mcm-x" type="button" aria-label="סגור" @click="close">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          </header>

          <form class="mcm-form" @submit.prevent="submit">
            <p class="mcm-note">הפרטים כפי שמופיעים בטופס החתום.</p>
            <div class="mcm-two">
              <label class="mcm-field">
                <span>חתימת הלקוח</span>
                <input v-model="form.customer_signed" type="date" :max="today" required />
              </label>
              <label class="mcm-field">
                <span>חתימת הסוכן</span>
                <input v-model="form.agent_signed" type="date" :max="today" required />
              </label>
            </div>
            <div class="mcm-two">
              <label class="mcm-field">
                <span>עיר</span>
                <input v-model.trim="form.city" autocomplete="off" required />
              </label>
              <label class="mcm-field">
                <span>רחוב</span>
                <input v-model.trim="form.street" autocomplete="off" required />
              </label>
            </div>
            <div class="mcm-two">
              <label class="mcm-field">
                <span>מספר בית</span>
                <input v-model.trim="form.house" autocomplete="off" maxlength="10" required />
              </label>
              <label class="mcm-field">
                <span>מיקוד</span>
                <input v-model.trim="form.zip_code" inputmode="numeric" dir="ltr" maxlength="7" required />
              </label>
            </div>

            <fieldset class="mcm-seg">
              <legend>מוצר מוחרג בטופס</legend>
              <label :class="{ on: form.excluded_product === '2' }"><input v-model="form.excluded_product" type="radio" value="2" /> לא</label>
              <label :class="{ on: form.excluded_product === '1' }"><input v-model="form.excluded_product" type="radio" value="1" /> כן</label>
            </fieldset>

            <label class="mcm-check">
              <input v-model="form.form_in_hand" type="checkbox" />
              <span>יש בידי טופס נספח א' חתום על ידי הלקוח</span>
            </label>

            <p v-if="error" class="mcm-err" role="alert">{{ error }}</p>

            <div class="mcm-actions">
              <button type="submit" class="mcm-btn mcm-btn--primary" :disabled="!isValid || saving">
                <span v-if="saving" class="mcm-spin" aria-hidden="true"></span>
                {{ saving ? 'שולח…' : 'שליחה למסלקה' }}
              </button>
              <button type="button" class="mcm-btn mcm-btn--ghost" @click="close">ביטול</button>
            </div>
          </form>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useOriginMorph } from '../../composables/useOriginMorph.js'

const props = defineProps({
  show: { type: Boolean, default: false },
  origin: { type: null, default: null },
  customerId: { type: String, default: '' },
  customerName: { type: String, default: '' },
  // async (consent) => void — the caller sends (the tab's /maslaka/inquiry or
  // Nifra's /office-agent/act). A throw shows its message here.
  send: { type: Function, required: true },
})
const emit = defineEmits(['close', 'sent'])

const cardEl = ref(null)
const morph = useOriginMorph()
const saving = ref(false)
const error = ref('')
const today = new Date().toISOString().slice(0, 10)
const blank = () => ({ customer_signed: '', agent_signed: '', city: '', street: '', house: '', zip_code: '',
  excluded_product: '', form_in_hand: false })
const form = reactive(blank())

const isValid = computed(() => form.customer_signed && form.agent_signed
  && form.customer_signed <= today && form.agent_signed <= today
  && form.city.length >= 2 && form.street && form.house && /^\d{5,7}$/.test(form.zip_code)
  && (form.excluded_product === '1' || form.excluded_product === '2') && form.form_in_hand)

watch(() => props.show, (s) => { if (s) { Object.assign(form, blank()); error.value = '' } })

function onEnter(el) {
  morph.remember(props.origin)
  morph.grow(el.querySelector('.mcm-card'))
}
async function close() {
  if (saving.value) return
  if (morph.hasOrigin() && cardEl.value) await morph.shrink(cardEl.value)
  emit('close')
}
async function submit() {
  if (!isValid.value || saving.value) return
  saving.value = true
  error.value = ''
  try {
    await props.send({ ...form, country: 'ישראל' })
    if (morph.hasOrigin() && cardEl.value) await morph.shrink(cardEl.value)
    emit('sent')
  } catch (e) {
    error.value = e?.response?.data?.detail || e?.message || 'השליחה נכשלה. נסו שוב.'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.mcm-overlay {
  /* above the customer card (1030) and Nifra (1010) it opens from */
  position: fixed; inset: 0; z-index: 1040; display: flex; align-items: center; justify-content: center;
  padding: 20px; background: rgba(0, 0, 0, 0.45);
}
.mcm-card { width: 100%; max-width: 480px; max-height: calc(100vh - 40px); overflow-y: auto; padding: 26px;
  background: var(--card-bg); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg); }
.mcm-head { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 16px; }
.mcm-head h3 { margin: 0; font-size: 22px; font-weight: 900; letter-spacing: -0.02em; color: var(--text); }
.mcm-sub { margin: 4px 0 0; font-size: 13px; color: var(--text-muted); }
.mcm-x { margin-inline-start: auto; flex: none; width: 32px; height: 32px; display: grid; place-items: center;
  border: none; background: none; border-radius: 8px; color: var(--text-muted); cursor: pointer; }
.mcm-x:hover { background: var(--bg); color: var(--text); }

.mcm-form { display: flex; flex-direction: column; gap: 12px; }
.mcm-note { margin: 0; font-size: 13px; color: var(--text-muted); }
.mcm-two { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.mcm-field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.mcm-field > span { font-size: 12.5px; font-weight: 600; color: var(--text); }
.mcm-field input {
  width: 100%; padding: 10px 12px; font-family: inherit; font-size: 14px; color: var(--text);
  background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius-sm);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.mcm-field input[dir='ltr'] { text-align: right; }
.mcm-field input:focus { outline: none; border-color: var(--tab-maslaka);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tab-maslaka) 18%, transparent); }

.mcm-seg { display: flex; align-items: center; gap: 8px; margin: 2px 0 0; padding: 0; border: none; }
.mcm-seg legend { float: right; margin-inline-end: 10px; font-size: 12.5px; font-weight: 600; color: var(--text); }
.mcm-seg label { display: inline-flex; align-items: center; gap: 6px; padding: 7px 16px; border: 1px solid var(--border);
  border-radius: 99px; cursor: pointer; font-size: 13.5px; color: var(--text-secondary); }
.mcm-seg label.on { border-color: var(--tab-maslaka); background: var(--tab-maslaka-wash); color: var(--tab-maslaka); font-weight: 700; }
.mcm-seg input { position: absolute; opacity: 0; pointer-events: none; }
.mcm-seg label:focus-within { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }

.mcm-check { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border-radius: 10px;
  background: var(--bg); cursor: pointer; font-size: 13.5px; color: var(--text); }
.mcm-check input { width: 17px; height: 17px; accent-color: var(--tab-maslaka); }

.mcm-err { margin: 0; font-size: 12.5px; color: var(--red-deep, #C23934); }
.mcm-actions { display: flex; gap: 10px; margin-top: 4px; }
.mcm-btn { display: inline-flex; align-items: center; gap: 8px; padding: 10px 22px; border-radius: 10px;
  font-family: inherit; font-size: 13.5px; font-weight: 700; cursor: pointer; }
.mcm-btn--primary { border: none; background: var(--tab-maslaka); color: #fff;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--tab-maslaka) 26%, transparent); transition: transform 0.15s, filter 0.15s; }
.mcm-btn--primary:hover:not(:disabled) { transform: translateY(-1px); filter: brightness(1.1); }
.mcm-btn--primary:disabled { opacity: 0.45; cursor: not-allowed; box-shadow: none; }
.mcm-btn--ghost { border: 1px solid var(--border); background: var(--card-bg); color: var(--text-muted); }
.mcm-btn--ghost:hover { color: var(--text); }
.mcm-spin { width: 13px; height: 13px; border-radius: 50%; border: 2px solid currentColor; border-top-color: transparent; animation: mcmSpin 0.7s linear infinite; }
@keyframes mcmSpin { to { transform: rotate(360deg); } }

.mcm-enter-active, .mcm-leave-active { transition: opacity 0.2s ease; }
.mcm-enter-from, .mcm-leave-to { opacity: 0; }
@media (max-width: 420px) { .mcm-two { grid-template-columns: 1fr; } .mcm-card { padding: 20px; } }
</style>
