<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="show" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal-card">
          <!-- Form first in the DOM so it lands on the RIGHT under `direction:
               rtl`, with the image on the left. -->
          <div class="pane pane--form">
          <div class="modal-header">
            <div class="modal-heading">
              <h3>יצירת קישור לפורטל לקוח</h3>
              <p class="modal-sub">הלקוח יראה רק את התיק שלו, מאחורי סיסמה.</p>
            </div>
            <button class="close-btn" @click="$emit('close')" aria-label="סגור">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>

          <form @submit.prevent="onGenerate">
            <div class="field">
              <label>תעודת זהות</label>
              <input
                v-model="form.customer_id_number"
                placeholder="הקלד מספר ת.ז..."
                dir="ltr"
                @blur="autoFill"
              />
            </div>

            <div class="field">
              <label>שם הלקוח</label>
              <input v-model="form.customer_name" placeholder="שם מלא" />
              <span v-if="autoFilling" class="auto-hint">
                <div class="mini-spinner"></div>
                מחפש...
              </span>
            </div>

            <div class="field">
              <label>אימייל (אופציונלי)</label>
              <input v-model="form.customer_email" type="email" placeholder="email@example.com" dir="ltr" />
            </div>

            <div class="field">
              <label>סיסמה לפורטל</label>
              <div class="password-row">
                <input
                  :type="showPass ? 'text' : 'password'"
                  v-model="form.password"
                  placeholder="סיסמה"
                  dir="ltr"
                />
                <button type="button" class="gen-pass-btn" @click="generatePassword" title="צור סיסמה אוטומטית">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="1 4 1 10 7 10"/>
                    <path d="M3.51 15a9 9 0 102.13-9.36L1 10"/>
                  </svg>
                </button>
                <button type="button" class="toggle-pass" @click="showPass = !showPass">
                  {{ showPass ? 'הסתר' : 'הצג' }}
                </button>
              </div>
            </div>

            <div class="field">
              <label>תוקף (ימים)</label>
              <input v-model.number="form.expires_days" type="number" min="1" max="365" dir="ltr" />
            </div>

            <Transition name="fade">
              <p v-if="error" class="error-text">{{ error }}</p>
            </Transition>

            <div class="modal-actions">
              <button type="button" class="btn-secondary" @click="$emit('close')">ביטול</button>
              <button type="submit" class="btn-primary" :disabled="!isValid || generating">
                <div v-if="generating" class="btn-spinner"></div>
                <span>{{ generating ? 'יוצר...' : 'צור קישור' }}</span>
              </button>
            </div>
          </form>

          <!-- Success state -->
          <Transition name="fade">
            <div v-if="generatedLink" class="success-section">
              <div class="success-icon">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
                  <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
              </div>
              <p class="success-text">הקישור נוצר בהצלחה!</p>
              <div class="link-box">
                <input :value="portalUrl" readonly dir="ltr" />
                <button class="copy-btn" @click="copyLink">
                  {{ copied ? 'הועתק!' : 'העתק' }}
                </button>
              </div>
              <div class="success-actions">
                <button v-if="form.customer_email" class="btn-email" @click="sendEmail" :disabled="sendingEmail">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                    <polyline points="22,6 12,13 2,6"/>
                  </svg>
                  {{ sendingEmail ? 'שולח...' : 'שלח באימייל' }}
                </button>
                <button class="btn-secondary" @click="$emit('close')">סגור</button>
              </div>
            </div>
          </Transition>
          </div>

          <!-- Second in the DOM = left-hand side in RTL. Hidden below 820px,
               where a decorative column would push the form off-screen. -->
          <aside class="pane pane--art" aria-hidden="true">
            <img :src="artwork" alt="" />
            <div class="art-veil"></div>
          </aside>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import artwork from '../../assets/portal/create-portal.webp'

import { ref, reactive, computed } from 'vue'
import { usePortalStore } from '../../stores/portal.js'

const props = defineProps({ show: Boolean })
const emit = defineEmits(['close', 'generated'])

const portalStore = usePortalStore()

const form = reactive({
  customer_id_number: '',
  customer_name: '',
  customer_email: '',
  password: '',
  expires_days: 30,
})

const showPass = ref(false)
const generating = ref(false)
const generatedLink = ref(null)
const error = ref(null)
const copied = ref(false)
const autoFilling = ref(false)
const sendingEmail = ref(false)

const isValid = computed(() =>
  form.customer_id_number && form.customer_name && form.password
)

const portalUrl = computed(() => {
  if (!generatedLink.value) return ''
  return `${window.location.origin}/portal/${generatedLink.value.token}`
})

function generatePassword() {
  const chars = '0123456789'
  let pass = ''
  for (let i = 0; i < 6; i++) pass += chars[Math.floor(Math.random() * chars.length)]
  form.password = pass
  showPass.value = true
}

async function autoFill() {
  if (!form.customer_id_number || form.customer_id_number.length < 5) return
  autoFilling.value = true
  try {
    const info = await portalStore.getCustomerInfo(form.customer_id_number)
    if (info.name && !form.customer_name) form.customer_name = info.name
    if (info.email && !form.customer_email) form.customer_email = info.email
  } finally {
    autoFilling.value = false
  }
}

async function onGenerate() {
  if (!isValid.value) return
  generating.value = true
  error.value = null
  try {
    const link = await portalStore.generateLink({
      customer_id_number: form.customer_id_number,
      customer_name: form.customer_name,
      customer_email: form.customer_email || null,
      password: form.password,
      expires_days: form.expires_days,
    })
    generatedLink.value = link
    emit('generated', link)
  } catch (e) {
    error.value = portalStore.error || 'שגיאה ביצירת קישור'
  } finally {
    generating.value = false
  }
}

async function copyLink() {
  try {
    await navigator.clipboard.writeText(portalUrl.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {
    // fallback
    const input = document.createElement('input')
    input.value = portalUrl.value
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  }
}

async function sendEmail() {
  if (!generatedLink.value) return
  sendingEmail.value = true
  try {
    await portalStore.sendEmail(generatedLink.value.token)
  } catch {
    // error in store
  } finally {
    sendingEmail.value = false
  }
}
</script>

<style scoped>
/* Subtitle under the modal title — the screen never said what the link
   actually gives the client. */
.modal-heading { min-width: 0; }
.modal-sub {
  margin-top: 4px;
  font-size: 12.5px; line-height: 1.6; color: var(--text-muted);
}
/* Fields pick up the tab colour on focus instead of the generic brand orange,
   and the ring is 2px so the focus state stays visible (a11y focus-states). */
.field input:focus {
  outline: none;
  border-color: var(--tab-portal, #4E9DD0);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tab-portal, #4E9DD0) 18%, transparent);
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1010;
  padding: 20px;
}

/* Two panes: the form on the right (first in the DOM under `direction: rtl`)
   and the photograph on the left. The card itself no longer scrolls — only the
   form pane does, so the image stays put while the fields move. */
.modal-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 0.82fr;
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 100%;
  max-width: 880px;
  max-height: 90vh;
  overflow: hidden;
}
.pane--form {
  padding: 28px;
  overflow-y: auto;
  min-width: 0;
}
.pane--art {
  position: relative;
  background: var(--bg);
  overflow: hidden;
}
.pane--art img {
  width: 100%; height: 100%;
  object-fit: cover; object-position: center 62%;
  display: block;
}
/* A wash in the portal tab's own colour ties the photograph to the palette —
   the image is the only photo in the workspace, so it needs the tint to read
   as part of the product rather than dropped-in stock. */
.art-veil {
  position: absolute; inset: 0;
  background:
    linear-gradient(200deg,
      color-mix(in srgb, var(--chart-2, #4E9DD0) 26%, transparent) 0%,
      transparent 52%),
    linear-gradient(to left, rgba(255,255,255,0.30), transparent 38%);
  pointer-events: none;
}
@media (max-width: 820px) {
  /* Below this the photo would squeeze the fields; the form is the job. */
  .modal-card { grid-template-columns: 1fr; max-width: 480px; }
  .pane--art { display: none; }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.modal-header h3 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}

.close-btn {
  color: var(--text-muted);
  padding: 4px;
}
.close-btn:hover { color: var(--text); }

form { display: flex; flex-direction: column; gap: 16px; }

.field { display: flex; flex-direction: column; gap: 5px; position: relative; }

.field label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.field input {
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: inherit;
  background: var(--bg-surface);
  color: var(--text);
  transition: all 0.2s var(--transition);
}

.field input:focus {
  border-color: var(--primary);
  box-shadow: var(--shadow-glow);
}

.password-row {
  display: flex;
  gap: 8px;
}

.password-row input { flex: 1; }

.gen-pass-btn, .toggle-pass {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  background: var(--bg);
  transition: all 0.2s var(--transition);
  white-space: nowrap;
}

.gen-pass-btn:hover, .toggle-pass:hover {
  border-color: var(--tab-portal, #4E9DD0);
  color: var(--tab-portal-ink, #35719A);
}
.gen-pass-btn:focus-visible, .toggle-pass:focus-visible {
  outline: 2px solid var(--tab-portal, #4E9DD0);
  outline-offset: 2px;
}

.auto-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--text-muted);
  position: absolute;
  left: 8px;
  top: 32px;
}

.mini-spinner {
  width: 12px;
  height: 12px;
  border: 1.5px solid var(--border-subtle);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.error-text {
  font-size: 13px;
  color: var(--red);
  background: var(--red-light);
  padding: 8px 12px;
  border-radius: 6px;
  margin: 0;
}

.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-start;
  margin-top: 8px;
}

/* The portal tab's own colour (--chart-2 / --tab-portal). The old peach came
   from `--primary`, which is the brand ACTION orange and belongs to no palette
   on this screen. */
.btn-primary {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  background: var(--tab-portal, #4E9DD0);
  color: white;
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  transition: all 0.2s var(--transition);
}

.btn-primary:hover:not(:disabled) {
  background: var(--tab-portal-ink, #35719A);
}

.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; }

.btn-secondary {
  padding: 10px 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  background: var(--bg);
  transition: all 0.2s var(--transition);
}

.btn-secondary:hover { border-color: var(--text-muted); color: var(--text-secondary); }

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* Success */
.success-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border-subtle);
  text-align: center;
}

.success-icon { color: var(--green); margin-bottom: 8px; }

.success-text {
  font-size: 15px;
  font-weight: 700;
  color: var(--green);
  margin: 0 0 16px;
}

.link-box {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.link-box input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-family: monospace;
  background: var(--bg);
  color: var(--text-secondary);
}

.copy-btn {
  padding: 10px 16px;
  background: var(--primary);
  color: white;
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 700;
  font-family: inherit;
  white-space: nowrap;
  transition: all 0.2s var(--transition);
}

.copy-btn:hover { background: var(--primary-deep); }

.success-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
}

.btn-email {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  background: var(--green-light);
  color: var(--green);
  border: 1px solid rgba(46, 132, 74, 0.15);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  transition: all 0.2s var(--transition);
}

.btn-email:hover:not(:disabled) { background: var(--green); color: white; }
.btn-email:disabled { opacity: 0.5; cursor: not-allowed; }

/* Transitions */
.modal-enter-active { animation: modalIn 0.3s var(--transition); }
.modal-leave-active { animation: modalIn 0.2s var(--transition) reverse; }
@keyframes modalIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal-enter-active .modal-card { animation: slideUp 0.3s var(--transition); }
.modal-leave-active .modal-card { animation: slideUp 0.2s var(--transition) reverse; }
@keyframes slideUp {
  from { opacity: 0; transform: translateY(24px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
</style>
