<template>
  <Teleport to="body">
    <Transition name="cfm">
      <div v-if="show" class="cfm-overlay" @click.self="$emit('close')">
        <div class="cfm-card">
          <!-- Form first in the DOM so it lands on the RIGHT under
               `direction: rtl`, with the photograph on the left — the same
               shape as the customer-portal modal. -->
          <div class="cfm-pane cfm-pane--form">
            <header class="cfm-head">
              <div>
                <h3>{{ editing ? 'עריכת איש קשר' : (step === 1 ? 'בחרו חברה' : 'פרטי איש הקשר') }}</h3>
                <p class="cfm-sub">
                  {{ editing
                    ? 'הכתובת שאליה יישלחו בירורי עמלות אל החברה.'
                    : (step === 1
                      ? 'לאיזו חברה מוסיפים כתובת?'
                      : 'הכתובת שאליה יישלחו בירורי עמלות אל החברה.') }}
                </p>
              </div>
              <button class="cfm-x" @click="$emit('close')" aria-label="סגור">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
                </svg>
              </button>
            </header>

            <!-- Step 1 — pick the company. Choosing it first means the form
                 never asks you to type a name the app already knows, and the
                 logo confirms you picked the right insurer. -->
            <div v-if="step === 1" class="cfm-step1">
              <CompanyPicker
                :companies="pickerItems"
                confirm-label="המשך"
                @select="choose"
              />
              <div class="cfm-other">
                <input v-model="customCompany" placeholder="חברה אחרת…" @keydown.enter="chooseCustom" />
                <button type="button" :disabled="!customCompany.trim()" @click="chooseCustom">המשך</button>
              </div>
            </div>

            <!-- Step 2 — the fields. -->
            <form v-else @submit.prevent="submit">
              <div v-if="!editing" class="cfm-chosen">
                <CompanyLogo :company="form.company_name" :size="28" />
                <span>{{ form.company_name }}</span>
                <!-- Icon-only back, pointing right because that IS "back"
                     under RTL. Same glyph as the portal modal. -->
                <button
                  type="button"
                  class="cfm-back"
                  aria-label="חזרה לבחירת חברה"
                  title="חזרה לבחירת חברה"
                  @click="step = 1"
                >
                  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="m9 6 6 6-6 6" />
                  </svg>
                </button>
              </div>

              <label v-else class="cfm-field">
                <span>חברה</span>
                <input v-model="form.company_name" placeholder="שם החברה" required />
              </label>

              <label class="cfm-field">
                <span>אימייל</span>
                <input ref="emailEl" v-model="form.email" type="email" dir="ltr"
                       placeholder="commissions@company.co.il" required />
              </label>

              <label class="cfm-field">
                <span>איש קשר <em>(אופציונלי)</em></span>
                <input v-model="form.contact_name" placeholder="שם איש הקשר במחלקת העמלות" />
              </label>

              <label class="cfm-field">
                <span>הערות <em>(אופציונלי)</em></span>
                <input v-model="form.notes" placeholder="מספר סוכן, שעות מענה…" />
              </label>

              <p v-if="error" class="cfm-err">{{ error }}</p>

              <div class="cfm-actions">
                <button type="button" class="cfm-btn cfm-btn--ghost" @click="$emit('close')">ביטול</button>
                <button type="submit" class="cfm-btn cfm-btn--primary" :disabled="!isValid || saving">
                  <span v-if="saving" class="cfm-spin" aria-hidden="true"></span>
                  {{ saving ? 'שומר…' : (editing ? 'שמור שינויים' : 'הוסף איש קשר') }}
                </button>
              </div>
            </form>
          </div>

          <!-- Second in the DOM = left-hand side in RTL. Hidden below 820px,
               where a decorative column would push the form off-screen. -->
          <aside class="cfm-pane cfm-pane--art" aria-hidden="true">
            <img :src="artwork" alt="" />
            <div class="cfm-veil"></div>
          </aside>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import api from '../../api/client.js'
import CompanyLogo from './CompanyLogo.vue'
import CompanyPicker from './CompanyPicker.vue'
import artwork from '../../assets/emails/add-contact.webp'

const props = defineProps({
  show: { type: Boolean, default: false },
  editing: { type: Object, default: null },
  presetCompany: { type: String, default: '' },
  companies: { type: Array, default: () => [] },
  taken: { type: Array, default: () => [] },
})
const emit = defineEmits(['close', 'saved'])

const form = reactive({ company_name: '', email: '', contact_name: '', notes: '' })
const saving = ref(false)
const error = ref('')

// 1 = pick the company, 2 = fill the details. Editing skips step 1 — the
// company is already known and changing it is not what "edit" means here.
const step = ref(1)
const customCompany = ref('')
const emailEl = ref(null)

// Companies that already hold an address. A Set of trimmed names, because
// the `taken` list arrives from the server rows while the picker labels come
// from KNOWN_COMPANIES, and the two disagree on padding.
const takenSet = computed(
  () => new Set(props.taken.map((t) => String(t || '').trim())),
)
function isTaken(label) {
  return takenSet.value.has(String(label || '').trim())
}

// Items for the shared picker: the note tells you a company already has an
// address, so you are not adding a duplicate without noticing.
const pickerItems = computed(() =>
  props.companies.map((c) => ({
    label: c.label,
    note: isTaken(c.label) ? 'כבר יש כתובת' : '',
    noteOk: true,
  })),
)

function choose(label) {
  form.company_name = label
  step.value = 2
  // Land the caret where the work actually is.
  nextTick(() => emailEl.value?.focus())
}

function chooseCustom() {
  const v = customCompany.value.trim()
  if (v) choose(v)
}

const isValid = computed(() => !!form.company_name.trim() && !!form.email.trim())

// Reset on every open so a cancelled edit never leaks into the next add, and
// a company picked from a "missing" card arrives already filled in.
watch(() => props.show, (open) => {
  if (!open) return
  error.value = ''
  customCompany.value = ''
  const src = props.editing || {}
  form.company_name = src.company_name || props.presetCompany || ''
  form.email = src.email || ''
  form.contact_name = src.contact_name || ''
  form.notes = src.notes || ''
  // Straight to the fields when the company is already settled — editing, or
  // arriving from a "no address" chip that named the company.
  step.value = (props.editing || props.presetCompany) ? 2 : 1
  if (step.value === 2) nextTick(() => emailEl.value?.focus())
})

async function submit() {
  if (!isValid.value || saving.value) return
  saving.value = true
  error.value = ''
  try {
    const body = { ...form }
    if (props.editing) await api.put(`/company-contacts/${props.editing.id}`, body)
    else await api.post('/company-contacts', body)
    emit('saved')
  } catch (e) {
    error.value = e?.response?.data?.detail || 'השמירה נכשלה. נסו שוב.'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.cfm-overlay {
  position: fixed; inset: 0; z-index: 1010;
  background: rgba(0, 0, 0, 0.45);
  display: flex; align-items: center; justify-content: center; padding: 20px;
}
.cfm-card {
  display: grid; grid-template-columns: minmax(0, 1fr) 0.82fr;
  width: 100%; max-width: 880px;
  /* A FIXED height, not a max. With `max-height` the card resized every time
     the step or the company changed — the picture jumped, the buttons moved
     under the cursor. The form pane scrolls inside instead, and the
     photograph fills whatever height the card has, so the two panes stay in
     proportion at any viewport. */
  height: min(600px, calc(100vh - 40px));
  background: var(--card-bg); border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg); overflow: hidden;
}
.cfm-pane--form { padding: 28px; overflow-y: auto; min-width: 0; min-height: 0; }
.cfm-pane--art { position: relative; background: var(--bg); overflow: hidden; }
.cfm-pane--art img {
  width: 100%; height: 100%; object-fit: cover; object-position: center 58%; display: block;
}
/* A wash in this tab's own colour, so the photograph reads as part of the
   product rather than dropped-in stock. */
.cfm-veil {
  position: absolute; inset: 0; pointer-events: none;
  background:
    linear-gradient(200deg, color-mix(in srgb, var(--tab-company-emails, #D6336C) 26%, transparent) 0%, transparent 52%),
    linear-gradient(to left, rgba(255,255,255,0.28), transparent 38%);
}
@media (max-width: 820px) {
  .cfm-card { grid-template-columns: 1fr; max-width: 480px; }
  .cfm-pane--art { display: none; }
}

.cfm-head { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 18px; }
.cfm-head h3 { font-size: 17px; font-weight: 800; color: var(--text); }
.cfm-sub { margin-top: 4px; font-size: 12.5px; line-height: 1.6; color: var(--text-muted); }
.cfm-x {
  margin-inline-start: auto; border: none; background: none; cursor: pointer;
  color: var(--text-muted); padding: 2px; border-radius: 6px;
}
.cfm-x:hover { color: var(--text); }

/* The picker takes its accent from the tab it is used in. */
.cfm-step1 { display: flex; flex-direction: column; gap: 12px; --pick-accent: var(--tab-company-emails, #D6336C); }

/* The escape hatch for a company the app does not know. */
.cfm-other { display: flex; gap: 8px; }
.cfm-other input {
  flex: 1; padding: 9px 11px; font-family: inherit; font-size: 13px;
  border: 1px dashed var(--border); border-radius: var(--radius-sm);
  background: var(--card-bg); color: var(--text);
}
.cfm-other input:focus {
  outline: none; border-style: solid;
  border-color: var(--tab-company-emails, #D6336C);
}
.cfm-other button {
  padding: 0 15px; border-radius: var(--radius-sm); cursor: pointer;
  border: 1px solid var(--border); background: var(--bg);
  font-family: inherit; font-size: 12.5px; font-weight: 600; color: var(--text-muted);
}
.cfm-other button:disabled { opacity: 0.45; cursor: not-allowed; }

/* ── Step 2: the chosen company, shown rather than retyped ──────────── */
.cfm-chosen {
  display: flex; align-items: center; gap: 9px;
  padding: 9px 11px; margin-bottom: 16px;
  border-radius: var(--radius-sm);
  background: color-mix(in srgb, var(--tab-company-emails, #D6336C) 6%, var(--bg));
  font-size: 13.5px; font-weight: 700; color: var(--text);
}
.cfm-back {
  margin-inline-start: auto; flex: none;
  width: 30px; height: 30px; display: grid; place-items: center;
  border: 1px solid var(--border); border-radius: 9px;
  background: var(--card-bg); cursor: pointer; padding: 0;
  color: var(--tab-company-emails, #D6336C);
  transition: background 0.16s ease, border-color 0.16s ease, transform 0.16s ease;
}
.cfm-back:hover {
  background: color-mix(in srgb, var(--tab-company-emails, #D6336C) 10%, transparent);
  border-color: color-mix(in srgb, var(--tab-company-emails, #D6336C) 40%, transparent);
  transform: translateX(2px);
}
.cfm-back:active { transform: translateX(0); }
@media (prefers-reduced-motion: reduce) { .cfm-back { transition: none; } .cfm-back:hover { transform: none; } }

.cfm-field { display: block; margin-bottom: 14px; }
.cfm-field > span { display: block; font-size: 12.5px; font-weight: 600; color: var(--text); margin-bottom: 6px; }
.cfm-field em { font-style: normal; font-weight: 500; color: var(--text-muted); }
.cfm-field input {
  width: 100%; padding: 10px 12px; font-family: inherit; font-size: 13.5px;
  color: var(--text); background: var(--card-bg);
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.cfm-field input:focus {
  outline: none;
  border-color: var(--tab-company-emails, #D6336C);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tab-company-emails, #D6336C) 18%, transparent);
}

.cfm-err { font-size: 12.5px; color: var(--red-deep, #C23934); margin-bottom: 10px; }
.cfm-actions { display: flex; gap: 10px; justify-content: flex-start; margin-top: 18px; }
.cfm-btn {
  display: inline-flex; align-items: center; gap: 8px;
  padding: 10px 22px; border-radius: var(--radius-sm);
  font-family: inherit; font-size: 13.5px; font-weight: 700; cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.cfm-btn--primary { border: none; background: var(--tab-company-emails, #D6336C); color: #fff; }
.cfm-btn--primary:hover:not(:disabled) { filter: brightness(0.93); }
.cfm-btn--primary:disabled { opacity: 0.45; cursor: not-allowed; }
.cfm-btn--ghost { border: 1px solid var(--border); background: var(--bg); color: var(--text-muted); }
.cfm-btn--ghost:hover { color: var(--text); }
.cfm-spin {
  width: 13px; height: 13px; border-radius: 50%;
  border: 2px solid currentColor; border-top-color: transparent;
  animation: cfmSpin 0.7s linear infinite;
}
@keyframes cfmSpin { to { transform: rotate(360deg); } }

.cfm-enter-active, .cfm-leave-active { transition: opacity 0.2s ease; }
.cfm-enter-from, .cfm-leave-to { opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  .cfm-spin { animation-duration: 2s; }
}
</style>
