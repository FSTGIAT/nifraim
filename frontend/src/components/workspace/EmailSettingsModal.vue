<template>
  <Teleport to="body">
    <Transition name="email-modal">
      <div v-if="open" class="es-overlay" @click.self="close" @keydown.escape="close">
        <div class="es-card" role="dialog" aria-labelledby="es-title">
          <div class="es-head">
            <div class="es-head-left">
              <svg class="es-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <circle cx="12" cy="12" r="3"/>
                <path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>
              </svg>
              <h3 id="es-title">הגדרות חשבון</h3>
            </div>
            <button class="es-close" @click="close" aria-label="סגור">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>

          <div class="es-body">
            <!-- ── Account / user ── -->
            <section v-if="auth.user" class="es-section">
              <div class="es-user-card">
                <div class="es-avatar" :style="{ background: avatarBg }">{{ avatarLetter }}</div>
                <div class="es-user-text">
                  <span class="es-user-name">{{ auth.user.full_name || auth.user.email }}</span>
                  <span v-if="auth.user.full_name && auth.user.email" class="es-user-email ltr-number">{{ auth.user.email }}</span>
                  <span v-if="auth.user.role" class="es-user-role">{{ roleLabel(auth.user.role) }}</span>
                </div>
              </div>
            </section>

            <!-- ── Subscription ── -->
            <section v-if="subStore.status" class="es-section">
              <header class="es-section-head">
                <span class="es-section-label">מנוי</span>
                <span class="es-status-pill" :class="subStore.status.status">{{ subStatusLabel }}</span>
              </header>
              <div class="es-sub-card">
                <div class="es-sub-row">
                  <span class="es-sub-label">מסלול</span>
                  <span class="es-sub-value">{{ subStore.status.plan === 'monthly' ? 'חודשי' : 'שנתי' }}</span>
                </div>
                <div v-if="subStore.status.next_charge_at" class="es-sub-row">
                  <span class="es-sub-label">חיוב הבא</span>
                  <span class="es-sub-value ltr-number">{{ formatDate(subStore.status.next_charge_at) }}</span>
                </div>
                <div v-else-if="subStore.status.expires_at" class="es-sub-row">
                  <span class="es-sub-label">בתוקף עד</span>
                  <span class="es-sub-value ltr-number">{{ formatDate(subStore.status.expires_at) }}</span>
                </div>
                <div v-if="subStore.status.last4_digits" class="es-sub-row">
                  <span class="es-sub-label">כרטיס</span>
                  <span class="es-sub-value ltr-number">****{{ subStore.status.last4_digits }}</span>
                </div>
                <button
                  v-if="subStore.status.status === 'active'"
                  class="es-cancel"
                  @click="showCancelConfirm = true"
                >
                  ביטול מנוי
                </button>
              </div>
            </section>

            <!-- ── Phone-forward OTP automation ── -->
            <section class="es-section">
              <header class="es-section-head">
                <span class="es-section-label">העברת SMS אוטומטית</span>
              </header>
              <p class="es-help">
                כשפורטל ביטוח שולח קוד אימות לטלפון שלך — הטלפון מעביר אותו למערכת אוטומטית
                והאוטומציה ממשיכה בלי שתצטרך להזין כלום.
              </p>
              <button class="es-pf-btn" @click="phoneForwardOpen = true">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
                  <line x1="12" y1="18" x2="12.01" y2="18"/>
                </svg>
                <span>הגדרת העברת SMS</span>
                <svg class="es-pf-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="15 18 9 12 15 6"/>
                </svg>
              </button>
            </section>

            <!-- ── Email provider ── -->
            <section class="es-section">
              <header class="es-section-head">
                <span class="es-section-label">ספק דוא"ל</span>
              </header>
              <p class="es-help">
                איפה ייפתח טופס חיבור-מייל כשתשלחו הודעה ללקוח או לחברה.
                ההגדרה נשמרת על הדפדפן הזה בלבד.
              </p>
              <div class="es-options">
                <label
                  v-for="opt in options"
                  :key="opt.value"
                  class="es-option"
                  :class="{ selected: provider === opt.value }"
                >
                  <input
                    type="radio"
                    name="email-provider"
                    :value="opt.value"
                    :checked="provider === opt.value"
                    @change="onChange(opt.value)"
                  />
                  <span class="es-option-radio" aria-hidden="true">
                    <span class="es-option-dot" />
                  </span>
                  <span class="es-option-text">
                    <span class="es-option-label">{{ opt.label }}</span>
                    <span class="es-option-desc">{{ opt.desc }}</span>
                  </span>
                </label>
              </div>
            </section>
          </div>

          <div class="es-footer">
            <span class="es-saved" v-if="justSaved">נשמר ✓</span>
            <button class="es-done" @click="close">סיום</button>
          </div>
        </div>

        <!-- Cancel-subscription confirmation -->
        <Transition name="email-modal">
          <div v-if="showCancelConfirm" class="es-cancel-overlay" @click.self="showCancelConfirm = false">
            <div class="es-cancel-card">
              <h4>לבטל את המנוי?</h4>
              <p>תאבדו גישה למערכת בסוף התקופה הנוכחית. ניתן לחדש בכל עת.</p>
              <div class="es-cancel-actions">
                <button class="es-btn-cancel" @click="showCancelConfirm = false">חזרה</button>
                <button class="es-btn-confirm" :disabled="cancelLoading" @click="handleCancelSub">
                  <span v-if="cancelLoading" class="es-spinner"></span>
                  <span v-else>בטל מנוי</span>
                </button>
              </div>
            </div>
          </div>
        </Transition>

        <PhoneForwardModal :open="phoneForwardOpen" @close="phoneForwardOpen = false" />
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAuthStore } from '../../stores/auth.js'
import { useSubscriptionStore } from '../../stores/subscription.js'
import PhoneForwardModal from './PhoneForwardModal.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open'])

const auth = useAuthStore()
const subStore = useSubscriptionStore()

// ── Email provider ──
const options = [
  { value: 'mailto',  label: 'ברירת מחדל',  desc: 'פותח את אפליקציית המייל המוגדרת במחשב.' },
  { value: 'gmail',   label: 'Gmail',         desc: 'פותח טופס חיבור-מייל ב-Gmail בלשונית חדשה.' },
  { value: 'outlook', label: 'Outlook',       desc: 'פותח טופס חיבור-מייל ב-Outlook Web בלשונית חדשה.' },
]

const provider = ref(
  (typeof window !== 'undefined' && localStorage.getItem('emailProvider')) || 'mailto',
)
const justSaved = ref(false)
let savedTimer = null

function onChange(value) {
  provider.value = value
  if (typeof window !== 'undefined') {
    localStorage.setItem('emailProvider', value)
  }
  justSaved.value = true
  clearTimeout(savedTimer)
  savedTimer = setTimeout(() => { justSaved.value = false }, 1400)
}

function close() {
  emit('update:open', false)
}

// ── User avatar ──
const avatarLetter = computed(() => {
  const name = auth.user?.full_name || auth.user?.email || ''
  return name.trim().charAt(0).toUpperCase() || '?'
})
// Deterministic warm-palette tint based on the user's name. Stays consistent
// across reloads, gives the modal a touch of personality without an upload.
const avatarBg = computed(() => {
  const seed = (auth.user?.full_name || auth.user?.email || '0').split('')
    .reduce((acc, ch) => acc + ch.charCodeAt(0), 0)
  const palette = [
    'linear-gradient(135deg, #F57C00, #E65100)',
    'linear-gradient(135deg, #FF9800, #E8720A)',
    'linear-gradient(135deg, #E8720A, #181818)',
    'linear-gradient(135deg, #E65100, #181818)',
  ]
  return palette[seed % palette.length]
})
function roleLabel(role) {
  if (role === 'admin') return 'מנהל מערכת'
  if (role === 'agent') return 'סוכן ביטוח'
  return role
}

// ── Subscription ──
const subStatusLabel = computed(() => {
  const s = subStore.status?.status
  if (s === 'active') return 'פעיל'
  if (s === 'cancelled') return 'מבוטל'
  if (s === 'expired') return 'פג תוקף'
  return s || ''
})
function formatDate(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString('he-IL', { year: 'numeric', month: '2-digit', day: '2-digit' })
  } catch { return '' }
}
const showCancelConfirm = ref(false)
const cancelLoading = ref(false)
const phoneForwardOpen = ref(false)
async function handleCancelSub() {
  cancelLoading.value = true
  try {
    await subStore.cancelSubscription()
    showCancelConfirm.value = false
  } catch {
    /* error handled in store */
  } finally {
    cancelLoading.value = false
  }
}

// Re-read provider + refresh sub status on open
watch(() => props.open, (now) => {
  if (!now) return
  provider.value = (typeof window !== 'undefined' && localStorage.getItem('emailProvider')) || 'mailto'
  // Fire-and-forget — show whatever's cached, replace when the API answers.
  subStore.fetchStatus?.()
})
</script>

<style scoped>
.es-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  background: rgba(45, 37, 34, 0.45);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 14vh;
  font-family: 'Heebo', sans-serif;
  direction: rtl;
}

.es-card {
  width: min(480px, 92vw);
  background: #FFFFFF;
  border-radius: 14px;
  box-shadow:
    0 28px 56px rgba(45, 37, 34, 0.30),
    0 4px 12px rgba(45, 37, 34, 0.10);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.es-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px 12px;
  border-bottom: 1px solid rgba(45, 37, 34, 0.06);
}
.es-head-left { display: flex; align-items: center; gap: 10px; }
.es-icon { color: #E8720A; flex-shrink: 0; }
.es-head h3 { margin: 0; font-size: 16px; font-weight: 700; color: #181818; }
.es-close {
  display: flex; align-items: center; justify-content: center;
  width: 30px; height: 30px;
  border: none;
  background: rgba(45, 37, 34, 0.05);
  color: rgba(45, 37, 34, 0.6);
  border-radius: 50%;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.es-close:hover { background: rgba(232, 114, 10, 0.10); color: #E8720A; }

.es-body {
  padding: 14px 16px 4px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  max-height: 70vh;
  overflow-y: auto;
}

.es-section { display: flex; flex-direction: column; gap: 10px; }
.es-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 4px;
}
.es-section-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: rgba(45, 37, 34, 0.55);
}

/* ── User card ── */
.es-user-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 16px;
  background: linear-gradient(160deg, #FBF4ED 0%, #FFFFFF 100%);
  border: 1px solid rgba(232, 114, 10, 0.10);
  border-radius: 12px;
}
.es-avatar {
  width: 48px; height: 48px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 19px;
  font-weight: 800;
  color: #FFFFFF;
  letter-spacing: 0.02em;
  flex-shrink: 0;
  box-shadow: 0 6px 18px rgba(232, 114, 10, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.30);
}
.es-user-text { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.es-user-name {
  font-size: 15px;
  font-weight: 700;
  color: #181818;
  overflow: hidden;
  text-overflow: ellipsis;
}
.es-user-email {
  font-size: 12px;
  color: rgba(45, 37, 34, 0.55);
  direction: ltr;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
}
.es-user-role {
  font-size: 11px;
  font-weight: 700;
  color: #E8720A;
  margin-top: 4px;
  letter-spacing: 0.02em;
}

/* ── Subscription card ── */
.es-sub-card {
  background: linear-gradient(160deg, #FBF4ED 0%, #FFFFFF 100%);
  border: 1px solid rgba(232, 114, 10, 0.10);
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.es-sub-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  padding: 4px 0;
  border-bottom: 1px dashed rgba(45, 37, 34, 0.06);
}
.es-sub-row:last-of-type { border-bottom: none; }
.es-sub-label { color: rgba(45, 37, 34, 0.55); }
.es-sub-value { font-weight: 700; color: #181818; }

.es-status-pill {
  font-size: 11px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 999px;
  letter-spacing: 0.02em;
}
.es-status-pill.active    { background: rgba(46, 132, 74, 0.12); color: #2E844A; }
.es-status-pill.cancelled,
.es-status-pill.expired   { background: rgba(194, 57, 52, 0.12); color: #C23934; }

.es-cancel {
  align-self: flex-start;
  margin-top: 4px;
  background: transparent;
  border: 1px solid rgba(194, 57, 52, 0.4);
  color: #C23934;
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  padding: 6px 14px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s ease;
}
.es-cancel:hover { background: rgba(194, 57, 52, 0.10); }

.es-help {
  margin: 0 4px;
  font-size: 12px;
  line-height: 1.6;
  color: rgba(45, 37, 34, 0.6);
}

.es-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 0;
}

.es-option {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px 14px;
  background: linear-gradient(160deg, #FBF4ED 0%, #FFFFFF 100%);
  border: 1px solid rgba(45, 37, 34, 0.08);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}
.es-option:hover { border-color: rgba(232, 114, 10, 0.30); }
.es-option.selected {
  border-color: #E8720A;
  background: linear-gradient(160deg, #FFF1E5 0%, #FFFFFF 100%);
  box-shadow: 0 4px 12px rgba(232, 114, 10, 0.10);
}
.es-option input[type="radio"] {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}

.es-option-radio {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid rgba(45, 37, 34, 0.25);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
  transition: border-color 0.15s ease;
}
.es-option.selected .es-option-radio { border-color: #E8720A; }

.es-option-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #E8720A;
  transform: scale(0);
  transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.es-option.selected .es-option-dot { transform: scale(1); }

.es-pf-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 14px;
  background: linear-gradient(160deg, #FBF4ED 0%, #FFFFFF 100%);
  border: 1px solid rgba(232, 114, 10, 0.18);
  border-radius: 10px;
  color: #181818;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}
.es-pf-btn:hover {
  border-color: #E8720A;
  background: linear-gradient(160deg, #FFF1E5 0%, #FFFFFF 100%);
  box-shadow: 0 4px 12px rgba(232, 114, 10, 0.10);
}
.es-pf-btn svg:first-of-type { color: #E8720A; flex-shrink: 0; }
.es-pf-btn span { flex: 1; text-align: right; }
.es-pf-arrow { color: rgba(45, 37, 34, 0.4); flex-shrink: 0; transform: scaleX(-1); }

.es-option-text { display: flex; flex-direction: column; gap: 2px; }
.es-option-label { font-size: 14px; font-weight: 700; color: #181818; }
.es-option-desc  { font-size: 12px; color: rgba(45, 37, 34, 0.6); line-height: 1.5; }

.es-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px 18px;
  border-top: 1px solid rgba(45, 37, 34, 0.06);
  margin-top: 8px;
}
.es-saved {
  font-size: 12px;
  font-weight: 700;
  color: #2E844A;
  padding: 4px 10px;
  background: rgba(46, 132, 74, 0.10);
  border-radius: 999px;
  animation: es-saved-fade 0.25s ease;
}
@keyframes es-saved-fade {
  from { opacity: 0; transform: translateY(-2px); }
  to   { opacity: 1; transform: translateY(0); }
}
.es-done {
  margin-inline-start: auto;
  background: #E8720A;
  color: #fff;
  border: none;
  font-family: inherit;
  font-size: 13px;
  font-weight: 700;
  padding: 8px 22px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease;
}
.es-done:hover { background: #E65100; transform: translateY(-1px); }

.email-modal-enter-active,
.email-modal-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.email-modal-enter-from,
.email-modal-leave-to { opacity: 0; transform: translateY(-8px); }

/* ── Cancel-subscription confirmation ── */
.es-cancel-overlay {
  position: fixed;
  inset: 0;
  background: rgba(45, 37, 34, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1200;
  padding: 24px;
  direction: rtl;
}
.es-cancel-card {
  background: #FFFFFF;
  border-radius: 14px;
  box-shadow: 0 28px 60px rgba(45, 37, 34, 0.35);
  padding: 22px;
  width: min(400px, 92vw);
}
.es-cancel-card h4 { margin: 0 0 8px; font-size: 17px; color: #181818; }
.es-cancel-card p  { margin: 0 0 18px; font-size: 13px; color: rgba(45, 37, 34, 0.7); line-height: 1.6; }
.es-cancel-actions { display: flex; gap: 10px; justify-content: flex-end; }
.es-btn-cancel,
.es-btn-confirm {
  font-family: inherit;
  font-size: 13px;
  font-weight: 700;
  padding: 8px 18px;
  border-radius: 8px;
  cursor: pointer;
}
.es-btn-cancel {
  background: transparent;
  border: 1px solid rgba(45, 37, 34, 0.18);
  color: rgba(45, 37, 34, 0.7);
}
.es-btn-confirm {
  background: #C23934;
  color: #fff;
  border: none;
  min-width: 90px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.es-btn-confirm:disabled { opacity: 0.6; cursor: not-allowed; }
.es-spinner {
  width: 14px; height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  animation: es-spin 0.8s linear infinite;
}
@keyframes es-spin { to { transform: rotate(360deg); } }
</style>
