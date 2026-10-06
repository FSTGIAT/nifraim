<template>
  <!-- לקוח חדש (walk-in): a customer who isn't in any production file yet. Saving
       the phone tells the Nifraim App to take calls with them — including the
       recordings of the last 3 hours. Same shape as ContactFormModal (form on
       the right, picture on the left); the picture arrives zoomed in and
       settles out, then its Kling loop plays. -->
  <Teleport to="body">
    <Transition name="wfm">
      <div v-if="show" class="wfm-overlay" @click.self="$emit('close')">
        <div class="wfm-card" role="dialog" aria-modal="true" aria-labelledby="wfm-title">
          <div class="wfm-pane wfm-pane--form">
            <header class="wfm-head">
              <div>
                <h3 id="wfm-title">{{ editing ? 'עריכת לקוח' : 'לקוח חדש' }}</h3>
                <p class="wfm-sub">שיחות עם המספר הזה יגיעו ל-Nifra Calls, גם מ-3 השעות האחרונות.</p>
              </div>
              <button class="wfm-x" type="button" aria-label="סגור" @click="$emit('close')">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
              </button>
            </header>

            <form class="wfm-form" @submit.prevent="submit">
              <div class="wfm-two">
                <label class="wfm-field">
                  <span>שם פרטי</span>
                  <input ref="firstEl" v-model.trim="form.first_name" autocomplete="off" required />
                </label>
                <label class="wfm-field">
                  <span>שם משפחה</span>
                  <input v-model.trim="form.last_name" autocomplete="off" />
                </label>
              </div>
              <label class="wfm-field">
                <span>ת.ז</span>
                <input v-model.trim="form.id_number" inputmode="numeric" dir="ltr" maxlength="10" required />
              </label>
              <label class="wfm-field">
                <span>טלפון</span>
                <input v-model.trim="form.phone" type="tel" inputmode="tel" dir="ltr" placeholder="050-0000000" required />
              </label>
              <label class="wfm-field">
                <span>מייל <em>(אופציונלי)</em></span>
                <input v-model.trim="form.email" type="email" dir="ltr" placeholder="name@example.com" />
              </label>

              <p v-if="error" class="wfm-err" role="alert">{{ error }}</p>

              <div class="wfm-actions">
                <button type="submit" class="wfm-btn wfm-btn--primary" :disabled="!isValid || saving">
                  <span v-if="saving" class="wfm-spin" aria-hidden="true"></span>
                  {{ saving ? 'שומר…' : (editing ? 'שמירה' : 'הוספת לקוח') }}
                </button>
                <button type="button" class="wfm-btn wfm-btn--ghost" @click="$emit('close')">ביטול</button>
              </div>
            </form>
          </div>

          <aside class="wfm-pane wfm-pane--art" aria-hidden="true">
            <div class="wfm-zoom" :class="{ 'wfm-zoom--still': reduced }">
              <video v-if="!reduced" class="wfm-media" :src="loop" :poster="poster" muted loop playsinline autoplay preload="auto"></video>
              <img v-else class="wfm-media" :src="poster" alt="" />
            </div>
            <div class="wfm-veil"></div>
          </aside>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import api from '../../api/client.js'
import poster from '../../assets/emails/walkin.webp'
import loop from '../../assets/emails/walkin.mp4'

const props = defineProps({
  show: { type: Boolean, default: false },
  editing: { type: Object, default: null },
})
const emit = defineEmits(['close', 'saved'])
const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

const form = reactive({ first_name: '', last_name: '', id_number: '', phone: '', email: '' })
const error = ref('')
const saving = ref(false)
const firstEl = ref(null)

const digits = (s) => String(s || '').replace(/\D/g, '')
const isValid = computed(() => {
  const id = digits(form.id_number).replace(/^0+/, '')
  const ph = digits(form.phone)
  return !!form.first_name && id.length >= 5 && id.length <= 9 && ph.length >= 9 &&
    (!form.email || /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(form.email))
})

watch(() => props.show, async (open) => {
  if (!open) return
  const src = props.editing || {}
  Object.assign(form, { first_name: src.first_name || '', last_name: src.last_name || '', id_number: src.id_number || '',
    phone: src.phone || '', email: src.email || '' })
  error.value = ''
  await nextTick()
  firstEl.value?.focus()
})

async function submit() {
  if (!isValid.value || saving.value) return
  saving.value = true
  error.value = ''
  try {
    const body = { ...form }
    const res = props.editing
      ? await api.put(`/walkin-customers/${props.editing.id}`, body)
      : await api.post('/walkin-customers', body)
    emit('saved', res.data)
  } catch (e) {
    error.value = e?.response?.data?.detail || 'השמירה נכשלה. נסו שוב.'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.wfm-overlay {
  position: fixed; inset: 0; z-index: 1010; display: flex; align-items: center; justify-content: center;
  padding: 20px; background: rgba(0, 0, 0, 0.45);
}
.wfm-card {
  display: grid; grid-template-columns: minmax(0, 1fr) 0.82fr; width: 100%; max-width: 880px;
  height: min(600px, calc(100vh - 40px)); overflow: hidden;
  background: var(--card-bg); border-radius: var(--radius-lg); box-shadow: var(--shadow-lg);
}
.wfm-pane--form { padding: 28px; overflow-y: auto; min-width: 0; min-height: 0; }
.wfm-pane--art { position: relative; overflow: hidden; background: #EDE6DC; }
/* the picture arrives zoomed in and settles out — then the loop plays on its own */
.wfm-zoom { position: absolute; inset: 0; transform-origin: 46% 60%; animation: wfmSettle 1.6s cubic-bezier(0.22, 1, 0.36, 1) both; }
.wfm-zoom--still { animation: none; }
@keyframes wfmSettle {
  0% { transform: scale(1.32); filter: blur(3px); opacity: 0.4; }
  55% { filter: blur(0); opacity: 1; }
  100% { transform: scale(1); filter: blur(0); opacity: 1; }
}
.wfm-media { width: 100%; height: 100%; object-fit: cover; object-position: center 62%; display: block; }
.wfm-veil {
  position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(200deg, color-mix(in srgb, var(--tab-emails) 20%, transparent) 0%, transparent 50%);
}

.wfm-head { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 22px; }
.wfm-head h3 { margin: 0; font-size: 22px; font-weight: 900; letter-spacing: -0.02em; color: var(--text); }
.wfm-sub { margin: 6px 0 0; font-size: 13px; line-height: 1.6; color: var(--text-muted); }
.wfm-x { margin-inline-start: auto; flex: none; width: 32px; height: 32px; display: grid; place-items: center;
  border: none; background: none; border-radius: 8px; color: var(--text-muted); cursor: pointer; }
.wfm-x:hover { background: var(--bg); color: var(--text); }

.wfm-form { display: flex; flex-direction: column; gap: 14px; }
.wfm-two { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.wfm-field { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.wfm-field > span { font-size: 12.5px; font-weight: 600; color: var(--text); }
.wfm-field em { font-style: normal; font-weight: 500; color: var(--text-muted); }
.wfm-field input {
  width: 100%; padding: 10px 12px; font-family: inherit; font-size: 14px; color: var(--text);
  background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius-sm);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.wfm-field input[dir='ltr'] { text-align: right; }
.wfm-field input:focus { outline: none; border-color: var(--tab-emails);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tab-emails) 18%, transparent); }

.wfm-err { margin: 0; font-size: 12.5px; color: var(--red-deep, #C23934); }
.wfm-actions { display: flex; gap: 10px; margin-top: 8px; }
.wfm-btn { display: inline-flex; align-items: center; gap: 8px; padding: 10px 22px; border-radius: 10px;
  font-family: inherit; font-size: 13.5px; font-weight: 700; cursor: pointer; }
.wfm-btn--primary { border: none; background: var(--tab-emails-ink); color: #fff;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--tab-emails) 26%, transparent); transition: transform 0.15s, filter 0.15s; }
.wfm-btn--primary:hover:not(:disabled) { transform: translateY(-1px); filter: brightness(0.93); }
.wfm-btn--primary:disabled { opacity: 0.45; cursor: not-allowed; box-shadow: none; }
.wfm-btn--ghost { border: 1px solid var(--border); background: var(--card-bg); color: var(--text-muted); }
.wfm-btn--ghost:hover { color: var(--text); }
.wfm-spin { width: 13px; height: 13px; border-radius: 50%; border: 2px solid currentColor; border-top-color: transparent; animation: wfmSpin 0.7s linear infinite; }
@keyframes wfmSpin { to { transform: rotate(360deg); } }

.wfm-enter-active, .wfm-leave-active { transition: opacity 0.2s ease; }
.wfm-enter-from, .wfm-leave-to { opacity: 0; }

@media (max-width: 820px) {
  .wfm-card { grid-template-columns: 1fr; max-width: 480px; height: auto; max-height: calc(100vh - 40px); }
  .wfm-pane--art { display: none; }
}
@media (max-width: 420px) { .wfm-two { grid-template-columns: 1fr; } }
</style>
