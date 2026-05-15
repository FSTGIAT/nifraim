<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="cred-modal-overlay" @click.self="close">
        <div class="cred-modal" role="dialog" aria-modal="true" :aria-label="title">
          <header class="cred-head">
            <div class="cred-head-titles">
              <span class="cred-badge" aria-hidden="true">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M2 18v3c0 .6.4 1 1 1h4v-3h3v-3h2l1.4-1.4a6.5 6.5 0 1 0-4-4Z"/>
                  <circle cx="16.5" cy="7.5" r=".5" fill="currentColor"/>
                </svg>
              </span>
              <div>
                <h3 class="cred-title">{{ title }}</h3>
                <p class="cred-sub">פרטי כניסה לפורטל. הסיסמה נשמרת מוצפנת בלבד.</p>
              </div>
            </div>
            <button class="cred-x" aria-label="סגור" @click="close">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
              </svg>
            </button>
          </header>

          <div v-if="formError" class="cred-error">{{ formError }}</div>

          <div class="cred-body">
            <label class="row">
              <span class="row-label">פורטל <span class="req">*</span></span>
              <select
                v-model="form.portal_kind"
                class="ctrl"
                :class="{ invalid: formError && !form.portal_kind }"
                :disabled="mode === 'edit'"
              >
                <option value="" disabled>בחר חברה</option>
                <option v-for="k in store.portalKinds" :key="k.id" :value="k.id">
                  {{ k.label }}{{ k.implemented ? '' : ' (לא ממומש)' }}
                </option>
              </select>
            </label>

            <label class="row">
              <span class="row-label">שם משתמש <span class="req">*</span></span>
              <input
                v-model="form.username"
                class="ctrl"
                :class="{ invalid: formError && !form.username }"
                placeholder="שם המשתמש בפורטל"
              />
            </label>

            <label class="row">
              <span class="row-label">
                סיסמה
                <span v-if="mode === 'add'" class="req">*</span>
                <small v-else class="row-sub"> (השאר ריק לשמור על הקיים)</small>
              </span>
              <input
                v-model="form.password"
                type="password"
                class="ctrl"
                :class="{ invalid: formError && mode === 'add' && !form.password }"
                :placeholder="mode === 'edit' ? 'חדש (אופציונלי)' : ''"
                autocomplete="new-password"
              />
            </label>

            <label class="row">
              <span class="row-label">
                מספר Twilio בפורטל
                <small class="row-sub"> (אם נקבע — OTP יגיע למספר הזה)</small>
              </span>
              <input
                v-model="form.twilio_to_number"
                class="ctrl"
                placeholder="+972..."
                dir="ltr"
              />
            </label>
          </div>

          <footer class="cred-footer">
            <button class="btn-secondary" @click="close" :disabled="saving">ביטול</button>
            <button class="btn-primary" :disabled="saving" @click="save">
              {{ saving ? '⏳ שומר...' : (mode === 'add' ? 'הוסף פורטל' : 'שמור שינויים') }}
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { reactive, ref, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  mode: { type: String, default: 'add' }, // 'add' | 'edit'
  credential: { type: Object, default: null }, // when mode='edit'
  defaultPortalKind: { type: String, default: '' }, // pre-fill for 'add' from a dock click
})
const emit = defineEmits(['close', 'saved'])

const store = usePortalAutomationStore()

const form = reactive({
  portal_kind: '',
  username: '',
  password: '',
  twilio_to_number: '',
})
const formError = ref('')
const saving = ref(false)

const title = ref('')

watch(
  () => [props.open, props.mode, props.credential],
  ([isOpen, mode, cred]) => {
    if (!isOpen) return
    formError.value = ''
    saving.value = false
    if (mode === 'edit' && cred) {
      title.value = `עריכה — ${portalLabel(cred.portal_kind)}`
      form.portal_kind = cred.portal_kind
      form.username = cred.username
      form.password = ''
      form.twilio_to_number = cred.twilio_to_number || ''
    } else {
      const pre = props.defaultPortalKind || ''
      title.value = pre ? `הוספת ${portalLabel(pre)}` : 'הוספת פורטל חדש'
      form.portal_kind = pre
      form.username = ''
      form.password = ''
      form.twilio_to_number = ''
    }
  },
  { immediate: true },
)

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
  if (props.mode === 'add' && !form.portal_kind) missing.push('פורטל')
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
        twilio_to_number: form.twilio_to_number || null,
      })
      emit('saved', created)
    } else {
      const payload = {
        username: form.username,
        twilio_to_number: form.twilio_to_number || null,
      }
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
  background: rgba(17, 12, 6, 0.36);
  backdrop-filter: blur(4px);
  z-index: 1100;
  display: grid;
  place-items: center;
  padding: 20px;
}
.cred-modal {
  width: min(520px, 100%);
  background: #ffffff;
  border-radius: var(--radius-lg, 18px);
  box-shadow: 0 24px 60px rgba(17, 12, 6, 0.18), 0 4px 12px rgba(17, 12, 6, 0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: inherit;
}
.cred-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 20px 12px;
  background: linear-gradient(180deg, rgba(245, 124, 0, 0.06) 0%, #fff 100%);
  border-bottom: 1px solid var(--border-subtle);
}
.cred-head-titles { display: flex; gap: 12px; align-items: flex-start; min-width: 0; }
.cred-badge {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  flex-shrink: 0;
  box-shadow: 0 6px 14px rgba(245, 124, 0, 0.3);
}
.cred-title { margin: 0; font-size: 15px; font-weight: 800; color: var(--text); }
.cred-sub { margin: 4px 0 0; font-size: 12px; color: var(--text-muted); }
.cred-x {
  background: transparent;
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  cursor: pointer;
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.cred-x:hover { background: var(--bg); color: var(--text); border-color: var(--text-muted); }

.cred-error {
  margin: 12px 20px 0;
  padding: 8px 12px;
  font-size: 12px;
  color: #8A1111;
  background: rgba(234, 0, 30, 0.06);
  border: 1px solid rgba(234, 0, 30, 0.2);
  border-radius: var(--radius-sm, 8px);
}

.cred-body {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.row-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--text);
}
.row-sub {
  font-weight: 400;
  color: var(--text-muted);
}
.req { color: #ef4444; font-weight: 800; }

.ctrl {
  width: 100%;
  padding: 9px 12px;
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm, 8px);
  font-family: inherit;
  font-size: 13.5px;
  background: var(--bg);
  color: var(--text);
  transition: border-color 0.15s, box-shadow 0.15s, background 0.15s;
  outline: none;
  box-sizing: border-box;
}
.ctrl:focus {
  border-color: rgba(245, 124, 0, 0.5);
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.12);
  background: #fff;
}
.ctrl.invalid { border-color: #ef4444; box-shadow: 0 0 0 2px rgba(239, 68, 68, 0.12); }
.ctrl[disabled] { opacity: 0.6; cursor: not-allowed; }
select.ctrl { appearance: auto; }

.cred-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 20px 16px;
  border-top: 1px solid var(--border-subtle);
  background: var(--bg);
}
.btn-primary {
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 9px 18px;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
  letter-spacing: 0.1px;
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.3);
  transition: transform 0.15s, box-shadow 0.15s, opacity 0.15s;
}
.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(245, 124, 0, 0.4);
}
.btn-primary:disabled { opacity: 0.55; cursor: not-allowed; box-shadow: none; }

.btn-secondary {
  background: transparent;
  color: var(--text-secondary, var(--text-muted));
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 9px 16px;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s, border-color 0.15s;
}
.btn-secondary:hover:not(:disabled) { background: var(--bg); border-color: var(--text-muted); }
.btn-secondary:disabled { opacity: 0.55; cursor: not-allowed; }

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-active .cred-modal, .modal-leave-active .cred-modal {
  transition: transform 0.22s ease, opacity 0.22s ease;
}
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .cred-modal, .modal-leave-to .cred-modal {
  transform: translateY(8px) scale(0.98);
  opacity: 0;
}
</style>
