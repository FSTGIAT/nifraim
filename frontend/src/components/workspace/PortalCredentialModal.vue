<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="cred-modal-overlay" @click.self="close">
        <div class="cred-modal" role="dialog" aria-modal="true" :aria-label="title">
          <header class="cred-head">
            <div class="cred-head-titles">
              <span class="cred-badge" aria-hidden="true">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="3" y="11" width="18" height="10" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/>
                </svg>
              </span>
              <div>
                <h3 class="cred-title">{{ title }}</h3>
                <p class="cred-sub">בוחרים חברה, מזינים פרטי כניסה — הכול נשמר מוצפן.</p>
              </div>
            </div>
            <button class="cred-x" aria-label="סגור" @click="close">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
            </button>
          </header>

          <div v-if="formError" class="cred-error">{{ formError }}</div>

          <div class="cred-body">
            <!-- ── Step 1 · company ── -->
            <section class="cred-section">
              <div class="cred-step-head">
                <span class="cred-step-num">1</span>
                <div class="cred-step-txt">
                  <h4 class="cred-step-title">{{ mode === 'edit' ? 'החברה' : 'בחרו חברה' }}</h4>
                  <p class="cred-step-sub">{{ mode === 'edit' ? 'לא ניתן לשנות חברה בעריכה' : 'לאיזו חברת ביטוח מתחברים?' }}</p>
                </div>
              </div>
              <div class="cred-grid">
                <button
                  v-for="c in companies"
                  :key="c.company"
                  type="button"
                  class="cred-tile"
                  :class="{ 'cred-tile--on': selectedCompany === c.company, 'cred-tile--dim': mode === 'edit' && selectedCompany !== c.company }"
                  :style="tileStyle(c.company, selectedCompany === c.company)"
                  :disabled="mode === 'edit'"
                  @click="selectCompany(c)"
                >
                  <span class="cred-tile-mono" :style="monoStyle(c.company)">{{ mono(c.company) }}</span>
                  <span class="cred-tile-name">{{ c.company }}</span>
                  <span class="cred-tile-meta">{{ c.kinds.length }} {{ c.kinds.length === 1 ? 'דוח' : 'דוחות' }}</span>
                  <span v-if="selectedCompany === c.company" class="cred-tile-check" :style="{ background: brand(c.company) }">
                    <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </span>
                </button>
              </div>
            </section>

            <!-- ── Step 2 · report type (only when the company has more than one) ── -->
            <section v-if="selectedCompany && companyKinds.length > 1" class="cred-section">
              <div class="cred-step-head">
                <span class="cred-step-num">2</span>
                <div class="cred-step-txt">
                  <h4 class="cred-step-title">איזה דוח?</h4>
                  <p class="cred-step-sub">בחרו את הדוח להורדה</p>
                </div>
              </div>
              <div class="cred-chips">
                <button
                  v-for="k in companyKinds"
                  :key="k.id"
                  type="button"
                  class="cred-chip"
                  :class="{ 'cred-chip--on': form.portal_kind === k.id }"
                  :style="form.portal_kind === k.id ? { borderColor: brand(selectedCompany), color: brandInk(selectedCompany), background: tint(selectedCompany, 0.9) } : null"
                  @click="form.portal_kind = k.id"
                >
                  {{ k.category || k.label }}
                </button>
              </div>
            </section>

            <!-- ── Step 3 · credentials + OTP ── -->
            <transition name="cred-reveal">
              <section v-if="form.portal_kind" class="cred-section">
                <div class="cred-step-head">
                  <span class="cred-step-num">{{ companyKinds.length > 1 ? 3 : 2 }}</span>
                  <div class="cred-step-txt">
                    <h4 class="cred-step-title">פרטי כניסה</h4>
                    <p v-if="selectedUrl" class="cred-step-sub ltr-number">{{ selectedUrl }}</p>
                    <p v-else class="cred-step-sub">שם המשתמש והסיסמה לפורטל הסוכן</p>
                  </div>
                </div>

                <div class="cred-creds">
                  <label class="cred-field">
                    <span class="cred-flabel">שם משתמש <span class="req">*</span></span>
                    <input v-model="form.username" class="ctrl" :class="{ invalid: formError && !form.username }" placeholder="שם המשתמש בפורטל" />
                  </label>

                  <label class="cred-field">
                    <span class="cred-flabel">
                      סיסמה
                      <span v-if="mode === 'add'" class="req">*</span>
                      <small v-else class="cred-flabel-sub"> (ריק = ללא שינוי)</small>
                    </span>
                    <input
                      v-model="form.password"
                      type="password"
                      class="ctrl"
                      :class="{ invalid: formError && mode === 'add' && !form.password }"
                      :placeholder="mode === 'edit' ? 'חדשה (אופציונלי)' : ''"
                      autocomplete="new-password"
                    />
                  </label>

                  <!-- OTP delivery — personal phone only (no manual entry) -->
                  <div class="cred-otp">
                    <span class="cred-flabel">איך קוד האימות (OTP) יגיע?</span>
                    <div v-if="phoneForwardConfigured" class="cred-otp-card cred-otp-card--ready">
                      <span class="cred-otp-ico">
                        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18h2"/></svg>
                      </span>
                      <div class="cred-otp-txt">
                        <strong>מהטלפון האישי שלך — אוטומטי</strong>
                        <small>הקוד מגיע כ-SMS לטלפון, והטלפון מעביר אותו למערכת לבד. בלי הקלדה.</small>
                      </div>
                      <svg class="cred-otp-tick" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                    </div>
                    <div v-else class="cred-otp-card cred-otp-card--setup">
                      <span class="cred-otp-ico cred-otp-ico--warn">
                        <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18h2"/></svg>
                      </span>
                      <div class="cred-otp-txt">
                        <strong>קודם נחבר את הטלפון</strong>
                        <small>הגדרה חד-פעמית של "העברת SMS אוטומטית", ומשם הכול רץ לבד.</small>
                      </div>
                      <button type="button" class="cred-otp-btn" @click="$emit('setup-phone')">הגדרה</button>
                    </div>
                  </div>
                </div>
              </section>
            </transition>
          </div>

          <footer class="cred-footer">
            <button class="btn-secondary" @click="close" :disabled="saving">ביטול</button>
            <button class="btn-primary" :disabled="saving || !form.portal_kind" @click="save">
              <span v-if="saving" class="cred-spin"></span>
              {{ saving ? 'שומר…' : (mode === 'add' ? 'הוסף פורטל' : 'שמור שינויים') }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  mode: { type: String, default: 'add' }, // 'add' | 'edit'
  credential: { type: Object, default: null }, // when mode='edit'
  defaultPortalKind: { type: String, default: '' }, // pre-fill for 'add' from a dock click
})
const emit = defineEmits(['close', 'saved', 'setup-phone'])

const store = usePortalAutomationStore()

// OTP is always the personal-phone forward path — manual entry was removed on
// purpose (the app is fully hands-free; a manual fallback trains users to babysit
// the phone). If the phone isn't connected yet we nudge them to set it up.
const form = reactive({
  portal_kind: '',
  username: '',
  password: '',
  otp_method: 'phone_forward',
})
const formError = ref('')
const saving = ref(false)
const title = ref('')
const selectedCompany = ref('')

const phoneForwardConfigured = computed(() => !!store.phoneForward?.token)

// ── Pastel brand tiles (copyright-safe: brand hue as a soft tint + Hebrew name,
// never the logo). Each tile is a calm wash of the company's colour. ──
const BRAND = {
  'מגדל': '#1F5FBF', 'מנורה': '#D8434B', 'הראל': '#1E86C7', 'הפניקס': '#EC7A2A',
  'כלל': '#2C6CB0', 'כלל בריאות': '#2C8FCB', 'מור': '#5AA24B', 'אלטשולר': '#2AA6AB',
  'מיטב דש': '#2A9E5C', 'ילין לפידות': '#2D74B8', 'הכשרה': '#3D66B5',
  'אקסלנס': '#78A63F', 'איילון': '#2C6FB5',
}
const brand = (c) => BRAND[c] || '#5B6EE1'
function _mix(hex, pct, toward) {
  const n = parseInt(hex.slice(1), 16), r = n >> 16, g = (n >> 8) & 255, b = n & 255
  const t = toward === 'white' ? 255 : 0
  const m = (v) => Math.round(v + (t - v) * pct)
  return `rgb(${m(r)},${m(g)},${m(b)})`
}
const tint = (c, pct) => _mix(brand(c), pct, 'white')      // soft pastel wash
const brandInk = (c) => _mix(brand(c), 0.2, 'black')       // readable text on pastel
function tileStyle(company, on) {
  const b = brand(company)
  return on
    ? { background: tint(company, 0.87), borderColor: b, boxShadow: `0 10px 24px ${tint(company, 0.8)}` }
    : { background: tint(company, 0.955), borderColor: tint(company, 0.85) }
}
function monoStyle(company) {
  return { background: tint(company, 0.8), color: brandInk(company) }
}
function mono(company) {
  // 2-letter Hebrew monogram avoids single-letter collisions (מגדל/מנורה/מור…).
  return (company || '').replace(/\s/g, '').slice(0, 2)
}

// Only implemented portals; keep the edit-mode selection visible regardless.
const pickerKinds = computed(() =>
  (store.portalKinds || []).filter((k) => k.implemented || k.id === form.portal_kind),
)
const companies = computed(() => {
  const map = new Map()
  for (const k of pickerKinds.value) {
    if (!map.has(k.company)) map.set(k.company, [])
    map.get(k.company).push(k)
  }
  return [...map.entries()].map(([company, kinds]) => ({ company, kinds }))
})
const companyKinds = computed(
  () => companies.value.find((c) => c.company === selectedCompany.value)?.kinds || [],
)
const selectedUrl = computed(
  () => store.portalKinds.find((x) => x.id === form.portal_kind)?.url || '',
)

function selectCompany(c) {
  if (props.mode === 'edit') return
  selectedCompany.value = c.company
  form.portal_kind = c.kinds.length === 1 ? c.kinds[0].id : ''
}

watch(
  () => [props.open, props.mode, props.credential],
  ([isOpen, mode, cred]) => {
    if (!isOpen) return
    formError.value = ''
    saving.value = false
    form.otp_method = 'phone_forward'
    if (mode === 'edit' && cred) {
      title.value = `עריכה — ${portalLabel(cred.portal_kind)}`
      form.portal_kind = cred.portal_kind
      form.username = cred.username
      form.password = ''
      selectedCompany.value = companyOf(cred.portal_kind)
    } else {
      const pre = props.defaultPortalKind || ''
      title.value = 'הוספת פורטל חדש'
      form.portal_kind = pre
      form.username = ''
      form.password = ''
      selectedCompany.value = pre ? companyOf(pre) : ''
    }
    store.fetchPhoneForward().catch(() => {})
  },
  { immediate: true },
)

function companyOf(kind) {
  return store.portalKinds.find((k) => k.id === kind)?.company || ''
}
function portalLabel(kind) {
  return store.portalKinds.find((k) => k.id === kind)?.label || kind
}

function close() {
  if (saving.value) return
  emit('close')
}

async function save() {
  formError.value = ''
  const missing = []
  if (props.mode === 'add' && !form.portal_kind) missing.push('חברה')
  if (!form.username) missing.push('שם משתמש')
  if (props.mode === 'add' && !form.password) missing.push('סיסמה')
  if (missing.length) {
    formError.value = 'חסרים שדות חובה: ' + missing.join(', ')
    return
  }

  saving.value = true
  try {
    if (props.mode === 'add') {
      const created = await store.createCredential({
        portal_kind: form.portal_kind,
        username: form.username,
        password: form.password,
        otp_method: form.otp_method,
      })
      emit('saved', created)
    } else {
      const payload = { username: form.username, otp_method: form.otp_method }
      if (form.password) payload.password = form.password
      const updated = await store.updateCredential(props.credential.id, payload)
      emit('saved', updated)
    }
    emit('close')
  } catch (e) {
    formError.value = store.error || e.response?.data?.detail || 'שגיאה בשמירה'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.cred-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(24, 24, 24, 0.5);
  backdrop-filter: blur(5px);
  z-index: 1100;
  display: grid;
  place-items: center;
  padding: 20px;
  font-family: 'Heebo', sans-serif;
  direction: rtl;
}
.cred-modal {
  width: min(580px, 100%);
  max-height: calc(100vh - 40px);
  background: #fff;
  border-radius: 22px;
  box-shadow: 0 28px 64px rgba(24, 24, 24, 0.3), 0 4px 12px rgba(24, 24, 24, 0.1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.cred-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 20px 24px 16px;
  background: linear-gradient(180deg, #F6F7FE 0%, #fff 100%);
  border-bottom: 1px solid rgba(24, 24, 24, 0.05);
}
.cred-head-titles { display: flex; gap: 13px; align-items: center; min-width: 0; }
.cred-badge {
  width: 40px; height: 40px; border-radius: 12px;
  display: grid; place-items: center;
  background: linear-gradient(135deg, #7C8CF0, #5FB0DE);
  color: #fff; flex-shrink: 0;
  box-shadow: 0 8px 18px rgba(91, 110, 225, 0.28);
}
.cred-title { margin: 0; font-size: 18px; font-weight: 800; color: #181818; }
.cred-sub { margin: 3px 0 0; font-size: 12.5px; color: rgba(24, 24, 24, 0.5); }
.cred-x {
  background: rgba(24, 24, 24, 0.05); border: none; color: rgba(24, 24, 24, 0.5);
  cursor: pointer; width: 30px; height: 30px; display: grid; place-items: center;
  border-radius: 50%; transition: background 0.15s, color 0.15s; flex-shrink: 0;
}
.cred-x:hover { background: rgba(91, 110, 225, 0.12); color: #5B6EE1; }

.cred-error {
  margin: 14px 24px 0; padding: 9px 12px; font-size: 12.5px; color: #C23934;
  background: rgba(194, 57, 52, 0.08); border: 1px solid rgba(194, 57, 52, 0.2); border-radius: 10px;
}

.cred-body { padding: 20px 24px 8px; display: flex; flex-direction: column; gap: 22px; overflow-y: auto; }
.cred-section { display: flex; flex-direction: column; gap: 12px; }

/* Numbered step heads — stronger hierarchy */
.cred-step-head { display: flex; align-items: center; gap: 11px; }
.cred-step-num {
  flex-shrink: 0; width: 26px; height: 26px; border-radius: 50%;
  display: grid; place-items: center;
  background: #EEF0FE; color: #4E5CC7;
  font-size: 13px; font-weight: 800;
}
.cred-step-txt { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.cred-step-title { margin: 0; font-size: 15.5px; font-weight: 800; color: #181818; }
.cred-step-sub { margin: 0; font-size: 12px; color: rgba(24, 24, 24, 0.48); }
.cred-step-sub.ltr-number { direction: ltr; text-align: left; word-break: break-all; }
.req { color: #C23934; font-weight: 800; }

/* Company grid — pastel tiles */
.cred-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(98px, 1fr));
  gap: 10px;
}
.cred-tile {
  position: relative;
  display: flex; flex-direction: column; align-items: center; gap: 7px;
  padding: 15px 8px 12px;
  border: 1.5px solid transparent;
  border-radius: 16px;
  cursor: pointer;
  font-family: inherit;
  transition: border-color 0.15s, box-shadow 0.15s, transform 0.12s, opacity 0.15s;
}
.cred-tile:hover:not(:disabled) { transform: translateY(-2px); }
.cred-tile--dim { opacity: 0.4; }
.cred-tile:disabled { cursor: default; }
.cred-tile-mono {
  width: 42px; height: 42px; border-radius: 12px;
  display: grid; place-items: center;
  font-size: 15px; font-weight: 800; letter-spacing: -0.5px;
}
.cred-tile-name { font-size: 13px; font-weight: 700; color: #2A2A2A; }
.cred-tile-meta { font-size: 10.5px; color: rgba(24, 24, 24, 0.4); }
.cred-tile-check {
  position: absolute; top: 8px; inset-inline-start: 8px;
  width: 18px; height: 18px; border-radius: 50%;
  display: grid; place-items: center;
}
.cred-tile-check svg { width: 11px; height: 11px; }

/* Report-type chips */
.cred-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.cred-chip {
  padding: 8px 15px; border: 1.5px solid rgba(24, 24, 24, 0.12);
  border-radius: 999px; background: #fff;
  font-family: inherit; font-size: 12.5px; font-weight: 700; color: rgba(24, 24, 24, 0.62);
  cursor: pointer; transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.cred-chip:hover { border-color: rgba(24, 24, 24, 0.25); }

/* Credentials */
.cred-creds { display: flex; flex-direction: column; gap: 14px; }
.cred-field { display: flex; flex-direction: column; gap: 6px; }
.cred-flabel { font-size: 12.5px; font-weight: 700; color: #181818; }
.cred-flabel-sub { font-weight: 400; color: rgba(24, 24, 24, 0.45); }
.ctrl {
  width: 100%; padding: 11px 13px;
  border: 1.5px solid rgba(24, 24, 24, 0.12); border-radius: 12px;
  font-family: inherit; font-size: 14px; background: #FBFAFC; color: #181818;
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
  outline: none; box-sizing: border-box;
}
.ctrl:focus { border-color: #5B6EE1; box-shadow: 0 0 0 3px rgba(91, 110, 225, 0.14); background: #fff; }
.ctrl.invalid { border-color: #C23934; box-shadow: 0 0 0 3px rgba(194, 57, 52, 0.12); }

/* OTP card */
.cred-otp { display: flex; flex-direction: column; gap: 7px; }
.cred-otp-card { display: flex; align-items: center; gap: 12px; padding: 13px 15px; border-radius: 14px; border: 1.5px solid; }
.cred-otp-card--ready { background: #F1FAF6; border-color: rgba(31, 168, 140, 0.28); }
.cred-otp-card--setup { background: #FBF6ED; border-color: rgba(214, 158, 46, 0.32); }
.cred-otp-ico { flex-shrink: 0; width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; background: rgba(31, 168, 140, 0.14); color: #0E7A64; }
.cred-otp-ico--warn { background: rgba(214, 158, 46, 0.18); color: #9A6B12; }
.cred-otp-txt { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.cred-otp-txt strong { font-size: 13px; font-weight: 800; color: #181818; }
.cred-otp-txt small { font-size: 11.5px; color: rgba(24, 24, 24, 0.55); line-height: 1.45; }
.cred-otp-tick { width: 20px; height: 20px; color: #1FA88C; flex-shrink: 0; }
.cred-otp-btn { flex-shrink: 0; border: none; border-radius: 9px; padding: 8px 15px; background: #9A6B12; color: #fff; font-family: inherit; font-size: 12.5px; font-weight: 700; cursor: pointer; transition: opacity 0.15s; }
.cred-otp-btn:hover { opacity: 0.9; }

.cred-reveal-enter-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.cred-reveal-enter-from { opacity: 0; transform: translateY(-6px); }

/* Footer */
.cred-footer { display: flex; justify-content: flex-end; gap: 10px; padding: 15px 24px 18px; border-top: 1px solid rgba(24, 24, 24, 0.05); }
.btn-primary {
  display: inline-flex; align-items: center; gap: 8px;
  background: linear-gradient(135deg, #5B6EE1, #4E9DD0); color: #fff; border: none;
  border-radius: 12px; padding: 11px 24px; font-weight: 800; font-size: 14px;
  cursor: pointer; font-family: inherit;
  box-shadow: 0 4px 14px rgba(91, 110, 225, 0.32);
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
}
.btn-primary:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(91, 110, 225, 0.42); }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }
.btn-secondary {
  background: transparent; color: rgba(24, 24, 24, 0.6);
  border: 1.5px solid rgba(24, 24, 24, 0.14); border-radius: 12px;
  padding: 11px 18px; font-weight: 700; font-size: 14px; cursor: pointer; font-family: inherit;
  transition: background 0.15s, border-color 0.15s;
}
.btn-secondary:hover:not(:disabled) { background: rgba(24, 24, 24, 0.04); }
.btn-secondary:disabled { opacity: 0.55; cursor: not-allowed; }
.cred-spin { width: 14px; height: 14px; border-radius: 50%; border: 2px solid rgba(255, 255, 255, 0.4); border-top-color: #fff; animation: cred-spin 0.8s linear infinite; }
@keyframes cred-spin { to { transform: rotate(360deg); } }

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-active .cred-modal, .modal-leave-active .cred-modal { transition: transform 0.24s cubic-bezier(0.34,1.4,0.64,1), opacity 0.24s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .cred-modal, .modal-leave-to .cred-modal { opacity: 0; transform: scale(0.95) translateY(10px); }
</style>
