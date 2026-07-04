<template>
  <Teleport to="body">
    <Transition name="email-modal">
      <div v-if="open" class="es-overlay" @click.self="close" @keydown.escape="close">
        <div class="es-card" role="dialog" aria-labelledby="es-title">
          <button class="es-close" @click="close" aria-label="סגור">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>

          <!-- ── Account hero ── -->
          <header class="es-hero">
            <div class="es-hero-glow" aria-hidden="true"></div>
            <div class="es-hero-row">
              <div class="es-avatar" :style="{ background: avatarBg }">{{ avatarLetter }}</div>
              <div class="es-hero-text" v-if="auth.user">
                <h3 id="es-title" class="es-hero-name">{{ auth.user.full_name || auth.user.email }}</h3>
                <span v-if="auth.user.full_name && auth.user.email" class="es-hero-email ltr-number">{{ auth.user.email }}</span>
                <div class="es-hero-meta">
                  <span v-if="auth.user.role" class="es-hero-role">{{ roleLabel(auth.user.role) }}</span>
                  <span v-if="subStore.status" class="es-status-pill" :class="subStatus.cls">{{ subStatus.label }}</span>
                </div>
              </div>
            </div>
          </header>

          <!-- ── Tabbed body: rail (right in RTL) + content ── -->
          <div class="es-shell">
            <nav class="es-rail" aria-label="הגדרות">
              <button
                v-for="t in tabs"
                :key="t.id"
                class="es-rail-btn"
                :class="{ active: activeTab === t.id }"
                :style="activeTab === t.id ? { '--accent': t.accent, '--deep': t.deep, '--soft': t.soft } : { '--accent': t.accent }"
                @click="activeTab = t.id"
              >
                <span class="es-rail-ico" v-html="t.icon"></span>
                <span class="es-rail-label">{{ t.label }}</span>
              </button>
            </nav>

            <div class="es-content" :style="{ '--accent': tab.accent, '--deep': tab.deep, '--soft': tab.soft, '--tint': tab.tint }">
              <!-- מנוי -->
              <section v-if="activeTab === 'subscription'" class="es-pane">
                <h4 class="es-pane-title">מנוי</h4>
                <div v-if="subStore.status" class="es-panel">
                  <div class="es-row">
                    <span class="es-row-label">מסלול</span>
                    <span class="es-row-value">{{ subStore.status.plan === 'monthly' ? 'חודשי' : subStore.status.plan === 'yearly' ? 'שנתי' : (subStore.status.plan || '—') }}</span>
                  </div>
                  <div class="es-row">
                    <span class="es-row-label">סטטוס</span>
                    <span class="es-status-pill" :class="subStatus.cls">{{ subStatus.label }}</span>
                  </div>
                  <div v-if="subStore.status.next_charge_at" class="es-row">
                    <span class="es-row-label">חיוב הבא</span>
                    <span class="es-row-value ltr-number">{{ formatDate(subStore.status.next_charge_at) }}</span>
                  </div>
                  <div v-else-if="subStore.status.expires_at" class="es-row">
                    <span class="es-row-label">בתוקף עד</span>
                    <span class="es-row-value ltr-number">{{ formatDate(subStore.status.expires_at) }}</span>
                  </div>
                  <div v-if="subStore.status.last4_digits" class="es-row">
                    <span class="es-row-label">כרטיס</span>
                    <span class="es-row-value ltr-number">****{{ subStore.status.last4_digits }}</span>
                  </div>
                  <button v-if="subStore.status.status === 'active'" class="es-cancel" @click="showCancelConfirm = true">ביטול מנוי</button>
                </div>
                <div v-else class="es-empty">אין כרגע מידע על מנוי בחשבון הזה.</div>
              </section>

              <!-- אוטומציה -->
              <section v-else-if="activeTab === 'automation'" class="es-pane">
                <h4 class="es-pane-title">אוטומציה</h4>

                <div class="es-block">
                  <div class="es-block-head">
                    <span class="es-block-label">העברת SMS אוטומטית</span>
                  </div>
                  <p class="es-help">כשפורטל ביטוח שולח קוד אימות לטלפון שלך — הטלפון מעביר אותו למערכת אוטומטית וההורדות ממשיכות בלי הקלדה.</p>
                  <button class="es-action" @click="phoneForwardOpen = true">
                    <span class="es-action-ico">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18h2"/></svg>
                    </span>
                    <span class="es-action-txt">הגדרת העברת SMS</span>
                    <svg class="es-action-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
                  </button>
                </div>

                <div class="es-block">
                  <div class="es-block-head">
                    <span class="es-block-label">חיבור המחשב</span>
                    <span class="es-worker-pill" :class="workerOnline ? 'on' : 'off'">
                      <span class="es-worker-dot"></span>{{ workerOnline ? 'מחובר' : 'לא מחובר' }}
                    </span>
                  </div>
                  <p class="es-help">ההורדות רצות ישירות מהמחשב שלך (כתובת IP ישראלית) כדי שכל החברות יעבדו. התקנה חד-פעמית.</p>
                  <button class="es-action" :disabled="workerDownloading" @click="downloadWorkerInstaller">
                    <span class="es-action-ico">
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>
                    </span>
                    <span class="es-action-txt">{{ workerDownloading ? 'מוריד…' : 'הורדת תוכנת החיבור' }}</span>
                    <span v-if="workerDownloading" class="es-spinner es-spinner--accent"></span>
                    <svg v-else class="es-action-arrow" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
                  </button>
                  <p v-if="workerHint" class="es-worker-hint">{{ workerHint }}</p>
                </div>
              </section>

              <!-- דוא"ל -->
              <section v-else class="es-pane">
                <h4 class="es-pane-title">ספק דוא"ל</h4>
                <p class="es-help">איפה ייפתח טופס חיבור-מייל כשתשלחו הודעה ללקוח או לחברה. ההגדרה נשמרת על הדפדפן הזה בלבד.</p>
                <div class="es-options">
                  <label
                    v-for="opt in options"
                    :key="opt.value"
                    class="es-option"
                    :class="{ selected: provider === opt.value }"
                  >
                    <input type="radio" name="email-provider" :value="opt.value" :checked="provider === opt.value" @change="onChange(opt.value)" />
                    <span class="es-option-radio" aria-hidden="true"><span class="es-option-dot" /></span>
                    <span class="es-option-text">
                      <span class="es-option-label">{{ opt.label }}</span>
                      <span class="es-option-desc">{{ opt.desc }}</span>
                    </span>
                  </label>
                </div>
              </section>
            </div>
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
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import PhoneForwardModal from './PhoneForwardModal.vue'
import api from '../../api/client.js'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open'])

const auth = useAuthStore()
const subStore = useSubscriptionStore()
const portalStore = usePortalAutomationStore()

// ── Tabs ──
const tabs = [
  { id: 'subscription', label: 'מנוי', accent: '#1FA88C', deep: '#0E7A64', soft: '#E4F5F0', tint: '#F3FBF8',
    icon: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="5" width="20" height="14" rx="2.5"/><line x1="2" y1="10" x2="22" y2="10"/></svg>' },
  { id: 'automation', label: 'אוטומציה', accent: '#4E9DD0', deep: '#2C6E9E', soft: '#E7F2FA', tint: '#F5FAFD',
    icon: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 3 14h8l-1 8 10-12h-8l1-8z"/></svg>' },
  { id: 'email', label: 'דוא"ל', accent: '#5B6EE1', deep: '#3A4BC0', soft: '#EAECFB', tint: '#F6F7FE',
    icon: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2.5"/><path d="m3 6 9 7 9-7"/></svg>' },
]
const activeTab = ref('automation')
const tab = computed(() => tabs.find((t) => t.id === activeTab.value) || tabs[1])

// ── Worker install (permanent download entry) ──
const workerDownloading = ref(false)
const workerHint = ref('')
const workerOnline = computed(() => !!portalStore.workerStatus?.online)

async function downloadWorkerInstaller() {
  workerDownloading.value = true
  workerHint.value = ''
  try {
    const res = await api.get('/portal-automation/worker/installer', { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/octet-stream' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'nifraim-worker-setup.bat'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    workerHint.value = 'הקובץ ירד. לחצו עליו פעמיים (Double-click). אם מופיעה אזהרת אבטחה — לחצו Run.'
  } catch (e) {
    workerHint.value = 'ההורדה נכשלה. נסו שוב או פנו לתמיכה.'
  } finally {
    workerDownloading.value = false
  }
}

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
// Deterministic cool-palette tint based on the user's name. Stays consistent
// across reloads, gives the modal a touch of personality without an upload.
const avatarBg = computed(() => {
  const seed = (auth.user?.full_name || auth.user?.email || '0').split('')
    .reduce((acc, ch) => acc + ch.charCodeAt(0), 0)
  const palette = [
    'linear-gradient(135deg, #8E6FD6, #5F429F)',
    'linear-gradient(135deg, #4E9DD0, #2C6E9E)',
    'linear-gradient(135deg, #1FA88C, #0E7A64)',
    'linear-gradient(135deg, #5B6EE1, #3A4BC0)',
  ]
  return palette[seed % palette.length]
})
function roleLabel(role) {
  if (role === 'admin') return 'מנהל מערכת'
  if (role === 'agent') return 'סוכן ביטוח'
  return role
}

// ── Subscription status → friendly label + pill class (unknown → neutral) ──
const SUB_STATUS = {
  active:    { label: 'פעיל',           cls: 'active' },
  trialing:  { label: 'תקופת ניסיון',   cls: 'trial' },
  trial:     { label: 'תקופת ניסיון',   cls: 'trial' },
  past_due:  { label: 'תשלום ממתין',    cls: 'warn' },
  cancelled: { label: 'מבוטל',          cls: 'ended' },
  canceled:  { label: 'מבוטל',          cls: 'ended' },
  expired:   { label: 'פג תוקף',        cls: 'ended' },
  none:      { label: 'ללא מנוי פעיל',  cls: 'neutral' },
  inactive:  { label: 'ללא מנוי פעיל',  cls: 'neutral' },
}
const subStatus = computed(() => {
  const key = String(subStore.status?.status || '').toLowerCase()
  return SUB_STATUS[key] || { label: 'ללא מנוי פעיל', cls: 'neutral' }
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
  portalStore.fetchWorkerStatus?.()
})
</script>

<style scoped>
.es-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  background: rgba(24, 24, 24, 0.5);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 11vh;
  font-family: 'Heebo', sans-serif;
  direction: rtl;
}

.es-card {
  position: relative;
  width: min(580px, 94vw);
  background: #FFFFFF;
  border-radius: 22px;
  box-shadow: 0 30px 64px rgba(24, 24, 24, 0.32), 0 4px 12px rgba(24, 24, 24, 0.10);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.es-close {
  position: absolute;
  top: 14px; left: 14px;
  z-index: 3;
  display: flex; align-items: center; justify-content: center;
  width: 32px; height: 32px;
  border: none;
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
  border-radius: 50%;
  cursor: pointer;
  transition: background 0.15s ease;
}
.es-close:hover { background: rgba(255, 255, 255, 0.32); }

/* ── Hero ── */
.es-hero {
  position: relative;
  overflow: hidden;
  padding: 22px 24px;
  background: linear-gradient(120deg, #5F429F 0%, #4E6BD0 52%, #2C6E9E 100%);
}
.es-hero-glow {
  position: absolute;
  top: -60%; left: -10%;
  width: 60%; height: 220%;
  background: radial-gradient(circle, rgba(255,255,255,0.22), transparent 70%);
  pointer-events: none;
}
.es-hero-row { position: relative; display: flex; align-items: center; gap: 15px; }
.es-avatar {
  width: 56px; height: 56px;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: 800; color: #fff;
  flex-shrink: 0;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255, 255, 255, 0.35);
  border: 2px solid rgba(255, 255, 255, 0.6);
}
.es-hero-text { min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.es-hero-name { margin: 0; font-size: 18px; font-weight: 800; color: #fff; overflow: hidden; text-overflow: ellipsis; }
.es-hero-email { font-size: 12.5px; color: rgba(255, 255, 255, 0.82); direction: ltr; text-align: right; overflow: hidden; text-overflow: ellipsis; }
.es-hero-meta { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.es-hero-role {
  font-size: 11px; font-weight: 700; color: #fff;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 999px; padding: 3px 10px;
}

/* ── Shell: rail + content ── */
.es-shell {
  display: grid;
  grid-template-columns: 148px 1fr;
  min-height: 292px;
  max-height: 60vh;
}
.es-rail {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px 10px;
  background: #FAFAFB;
  border-inline-end: 1px solid rgba(24, 24, 24, 0.06);
}
.es-rail-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: none;
  border-radius: 11px;
  background: transparent;
  color: var(--text-secondary, #55524E);
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.es-rail-btn:hover { background: rgba(24, 24, 24, 0.04); }
.es-rail-btn.active {
  background: var(--soft);
  color: var(--deep);
}
.es-rail-ico { display: grid; place-items: center; color: var(--accent); flex-shrink: 0; }
.es-rail-btn:not(.active) .es-rail-ico { color: rgba(24, 24, 24, 0.4); }
.es-rail-label { flex: 1; text-align: start; }

.es-content {
  padding: 20px 22px 8px;
  overflow-y: auto;
}
.es-pane { display: flex; flex-direction: column; gap: 14px; }
.es-pane-title { margin: 0; font-size: 16px; font-weight: 800; color: #181818; }
.es-pane-title::before {
  content: '';
  display: inline-block;
  width: 9px; height: 9px;
  border-radius: 3px;
  background: var(--accent);
  margin-inline-end: 8px;
  vertical-align: middle;
}

.es-help { margin: 0; font-size: 12.5px; line-height: 1.6; color: rgba(24, 24, 24, 0.58); }

/* Subscription panel */
.es-panel {
  background: var(--tint);
  border: 1px solid color-mix(in srgb, var(--accent) 22%, transparent);
  border-radius: 14px;
  padding: 12px 15px;
  display: flex; flex-direction: column; gap: 4px;
}
.es-row {
  display: flex; align-items: center; justify-content: space-between;
  font-size: 13px; padding: 6px 0;
  border-bottom: 1px dashed rgba(24, 24, 24, 0.08);
}
.es-row:last-of-type { border-bottom: none; }
.es-row-label { color: rgba(24, 24, 24, 0.5); }
.es-row-value { font-weight: 700; color: #181818; }
.es-empty {
  font-size: 13px; color: rgba(24, 24, 24, 0.5);
  background: #FAFAFB; border: 1px dashed rgba(24, 24, 24, 0.12);
  border-radius: 12px; padding: 18px; text-align: center;
}
.es-cancel {
  align-self: flex-start; margin-top: 6px;
  background: transparent; border: 1px solid rgba(194, 57, 52, 0.4);
  color: #C23934; font-family: inherit; font-size: 12px; font-weight: 700;
  padding: 6px 14px; border-radius: 8px; cursor: pointer; transition: background 0.15s ease;
}
.es-cancel:hover { background: rgba(194, 57, 52, 0.1); }

/* Status pill */
.es-status-pill {
  font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; letter-spacing: 0.02em;
}
.es-status-pill.active  { background: rgba(31, 168, 140, 0.16); color: #0E7A64; }
.es-status-pill.trial   { background: rgba(78, 157, 208, 0.16); color: #2C6E9E; }
.es-status-pill.warn    { background: rgba(214, 158, 46, 0.18); color: #9A6B12; }
.es-status-pill.ended   { background: rgba(194, 57, 52, 0.14); color: #C23934; }
.es-status-pill.neutral { background: rgba(255, 255, 255, 0.22); color: #fff; }
.es-panel .es-status-pill.neutral { background: rgba(24, 24, 24, 0.08); color: rgba(24, 24, 24, 0.55); }

/* Automation blocks */
.es-block { display: flex; flex-direction: column; gap: 9px; }
.es-block + .es-block { margin-top: 14px; padding-top: 16px; border-top: 1px solid rgba(24, 24, 24, 0.07); }
.es-block-head { display: flex; align-items: center; gap: 8px; }
.es-block-label { font-size: 13px; font-weight: 800; color: #181818; }
.es-block-head .es-worker-pill { margin-inline-start: auto; }

.es-action {
  display: flex; align-items: center; gap: 11px; width: 100%;
  padding: 12px 14px;
  background: var(--tint);
  border: 1.5px solid color-mix(in srgb, var(--accent) 28%, transparent);
  border-radius: 13px; color: #181818;
  font-family: inherit; font-size: 14px; font-weight: 700; cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.12s ease;
}
.es-action:hover:not(:disabled) {
  border-color: var(--accent);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--accent) 20%, transparent);
  transform: translateY(-1px);
}
.es-action:disabled { opacity: 0.6; cursor: default; }
.es-action-ico {
  display: grid; place-items: center; width: 32px; height: 32px;
  border-radius: 9px; background: var(--soft); color: var(--deep); flex-shrink: 0;
}
.es-action-txt { flex: 1; text-align: right; }
.es-action-arrow { color: color-mix(in srgb, var(--accent) 65%, #706E6B); flex-shrink: 0; transform: scaleX(-1); }

.es-worker-pill {
  display: inline-flex; align-items: center; gap: 6px;
  font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; letter-spacing: 0.02em;
}
.es-worker-pill.on  { background: rgba(31, 168, 140, 0.14); color: #0E7A64; }
.es-worker-pill.off { background: rgba(24, 24, 24, 0.07); color: rgba(24, 24, 24, 0.5); }
.es-worker-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.es-worker-pill.on .es-worker-dot { box-shadow: 0 0 0 0 rgba(31, 168, 140, 0.5); animation: es-worker-pulse 1.8s ease-out infinite; }
@keyframes es-worker-pulse { 70% { box-shadow: 0 0 0 6px rgba(31, 168, 140, 0); } 100% { box-shadow: 0 0 0 0 rgba(31, 168, 140, 0); } }
.es-worker-hint {
  margin: 0; font-size: 12px; line-height: 1.55; color: var(--deep);
  background: var(--soft); border-radius: 9px; padding: 8px 11px;
}
.es-spinner--accent { border-color: color-mix(in srgb, var(--accent) 30%, transparent); border-top-color: var(--accent); flex-shrink: 0; }

/* Email options */
.es-options { display: flex; flex-direction: column; gap: 8px; }
.es-option {
  display: flex; align-items: flex-start; gap: 12px; padding: 12px 14px;
  background: #FBFAFC; border: 1.5px solid rgba(24, 24, 24, 0.08); border-radius: 12px;
  cursor: pointer; transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}
.es-option:hover { border-color: color-mix(in srgb, var(--accent) 40%, transparent); }
.es-option.selected {
  border-color: var(--accent);
  background: var(--tint);
  box-shadow: 0 4px 14px color-mix(in srgb, var(--accent) 16%, transparent);
}
.es-option input[type="radio"] { position: absolute; opacity: 0; pointer-events: none; }
.es-option-radio {
  width: 18px; height: 18px; border-radius: 50%;
  border: 2px solid rgba(24, 24, 24, 0.22);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; margin-top: 2px; transition: border-color 0.15s ease;
}
.es-option.selected .es-option-radio { border-color: var(--accent); }
.es-option-dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--accent);
  transform: scale(0); transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.es-option.selected .es-option-dot { transform: scale(1); }
.es-option-text { display: flex; flex-direction: column; gap: 2px; }
.es-option-label { font-size: 14px; font-weight: 700; color: #181818; }
.es-option-desc  { font-size: 12px; color: rgba(24, 24, 24, 0.55); line-height: 1.5; }

/* Footer */
.es-footer {
  display: flex; align-items: center; justify-content: space-between;
  padding: 13px 22px 16px;
  border-top: 1px solid rgba(24, 24, 24, 0.06);
}
.es-saved {
  font-size: 12px; font-weight: 700; color: #0E7A64;
  padding: 4px 10px; background: rgba(31, 168, 140, 0.12); border-radius: 999px;
  animation: es-saved-fade 0.25s ease;
}
@keyframes es-saved-fade { from { opacity: 0; transform: translateY(-2px); } to { opacity: 1; transform: translateY(0); } }
.es-done {
  margin-inline-start: auto;
  background: linear-gradient(135deg, #5B6EE1, #4E9DD0);
  color: #fff; border: none; font-family: inherit; font-size: 14px; font-weight: 700;
  padding: 9px 26px; border-radius: 999px; cursor: pointer;
  box-shadow: 0 4px 14px rgba(91, 110, 225, 0.32);
  transition: box-shadow 0.15s ease, transform 0.15s ease;
}
.es-done:hover { transform: translateY(-1px); box-shadow: 0 6px 18px rgba(91, 110, 225, 0.4); }

.email-modal-enter-active, .email-modal-leave-active { transition: opacity 0.2s ease; }
.email-modal-enter-active .es-card, .email-modal-leave-active .es-card { transition: transform 0.24s cubic-bezier(0.34, 1.4, 0.64, 1), opacity 0.24s ease; }
.email-modal-enter-from, .email-modal-leave-to { opacity: 0; }
.email-modal-enter-from .es-card, .email-modal-leave-to .es-card { opacity: 0; transform: scale(0.95) translateY(-10px); }

/* Cancel-subscription confirmation */
.es-cancel-overlay {
  position: fixed; inset: 0; background: rgba(24, 24, 24, 0.55);
  display: flex; align-items: center; justify-content: center;
  z-index: 1200; padding: 24px; direction: rtl;
}
.es-cancel-card {
  background: #fff; border-radius: 16px; box-shadow: 0 28px 60px rgba(24, 24, 24, 0.35);
  padding: 24px; width: min(400px, 92vw);
}
.es-cancel-card h4 { margin: 0 0 8px; font-size: 17px; color: #181818; }
.es-cancel-card p  { margin: 0 0 18px; font-size: 13px; color: rgba(24, 24, 24, 0.65); line-height: 1.6; }
.es-cancel-actions { display: flex; gap: 10px; justify-content: flex-end; }
.es-btn-cancel, .es-btn-confirm { font-family: inherit; font-size: 13px; font-weight: 700; padding: 8px 18px; border-radius: 9px; cursor: pointer; }
.es-btn-cancel { background: transparent; border: 1px solid rgba(24, 24, 24, 0.18); color: rgba(24, 24, 24, 0.65); }
.es-btn-confirm { background: #C23934; color: #fff; border: none; min-width: 90px; display: inline-flex; align-items: center; justify-content: center; }
.es-btn-confirm:disabled { opacity: 0.6; cursor: not-allowed; }
.es-spinner { width: 14px; height: 14px; border-radius: 50%; border: 2px solid rgba(255, 255, 255, 0.35); border-top-color: #fff; animation: es-spin 0.8s linear infinite; }
@keyframes es-spin { to { transform: rotate(360deg); } }

/* Responsive: rail becomes a top strip */
@media (max-width: 560px) {
  .es-shell { grid-template-columns: 1fr; max-height: none; }
  .es-rail { flex-direction: row; overflow-x: auto; border-inline-end: none; border-bottom: 1px solid rgba(24,24,24,0.06); }
  .es-rail-label { white-space: nowrap; }
}
</style>
