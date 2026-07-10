<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="hm-overlay" @click.self="$emit('close')">
        <div class="hm-card">
          <button class="hm-close" aria-label="סגירה" @click="$emit('close')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>

          <header class="hm-head">
            <span class="hm-ico">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2" /><path d="m2 7 10 6 10-6" /></svg>
            </span>
            <div>
              <h3 class="hm-title">חיבור תיבת המייל</h3>
              <p class="hm-sub">הכשרה שולחת את קובץ הפרודוקציה למייל שלך פעם בחודש. נתחבר לתיבה בקריאה בלבד, נזהה את הקובץ ונטען אותו לבד — בלי שתצטרך לעשות כלום.</p>
            </div>
          </header>

          <!-- Status: only after a mailbox exists. -->
          <div v-if="cfg" class="hm-status" :class="statusTone">
            <span class="hm-dot" />
            <span class="hm-status-txt">{{ lastReceivedLabel(cfg.last_received_at) }}</span>
            <button class="hm-link" :disabled="store.polling" @click="check">
              {{ store.polling ? 'בודק…' : 'בדוק עכשיו' }}
            </button>
          </div>

          <!-- The only question we ask. Everything else is derived from it. -->
          <label class="hm-field">
            <span class="hm-label">כתובת המייל שאליה הכשרה שולחת</span>
            <input
              v-model.trim="email"
              class="hm-input ltr-number"
              type="email"
              inputmode="email"
              placeholder="moshe@eitam-finance.com"
              @blur="onDetect"
            />
          </label>
          <p v-if="detecting" class="hm-hint">מזהים את ספק המייל…</p>

          <!-- Detection is a hint. Vanity MX, split delivery and security gateways
               all mislead it, so the agent can always say "that's not my provider". -->
          <p v-if="host && !detecting" class="hm-hint">
            {{ hostLabel }}
            <button class="hm-link" @click="manual = !manual">{{ manual ? 'סגור' : 'לא נכון? בחר ידנית' }}</button>
          </p>
          <div v-if="manual" class="hm-manual">
            <button v-for="o in hostOptions" :key="o.id" class="hm-chip" :class="{ on: host === o.id }" @click="host = o.id">
              {{ o.label }}
            </button>
          </div>

          <!-- Microsoft: nothing to type. One click, then consent. -->
          <div v-if="host === 'microsoft' && !store.capabilities.microsoft" class="hm-problem hm-problem--muted">
            <strong class="hm-problem-title">חיבור ל-Microsoft עדיין לא זמין כאן</strong>
            <p class="hm-problem-body">אפשר בינתיים להעביר אלינו את הדואר מהכשרה אוטומטית — זה עובד בכל ספק מייל.</p>
            <button class="hm-link" @click="switchToForwarding">עבור להעברה</button>
          </div>
          <div v-else-if="host === 'microsoft'" class="hm-branch">
            <button class="hm-cta" :disabled="!email || store.saving" @click="connectMicrosoft">
              <span class="hm-cta-ico">
                <svg width="15" height="15" viewBox="0 0 23 23" aria-hidden="true"><rect x="1" y="1" width="10" height="10" fill="#F25022" /><rect x="12" y="1" width="10" height="10" fill="#7FBA00" /><rect x="1" y="12" width="10" height="10" fill="#00A4EF" /><rect x="12" y="12" width="10" height="10" fill="#FFB900" /></svg>
              </span>
              <span>{{ store.saving ? 'מתחבר…' : 'התחברות עם Microsoft' }}</span>
            </button>
            <p class="hm-help">נבקש הרשאת קריאה בלבד. לא נשלח מיילים, לא נמחק כלום, ואפשר לנתק בכל רגע.</p>
          </div>

          <!-- Google: an app password, and the mistake everyone makes, named. -->
          <div v-else-if="host === 'google'" class="hm-branch">
            <label class="hm-field">
              <span class="hm-label">סיסמת אפליקציה</span>
              <input v-model.trim="appPassword" class="hm-input ltr-number" type="password" placeholder="abcd efgh ijkl mnop" autocomplete="off" />
            </label>
            <p class="hm-help">
              זו לא הסיסמה הרגילה של Gmail. Google מייצרת קוד נפרד בן 16 תווים לאפליקציה הזו בלבד —
              כך הסיסמה שלך נשארת אצלך, ותוכל לבטל את הגישה בכל רגע.
            </p>
            <!-- Send the agent straight to the one page that matters. Telling them to
                 "turn on 2-Step Verification" first lands them on Google's security
                 page, which no longer links to app passwords at all — a dead end. -->
            <a class="hm-cta hm-cta--ghost" href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener">
              <span class="hm-cta-ico">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>
              </span>
              <span>פתיחת דף סיסמאות האפליקציה ב-Google</span>
            </a>
            <ol class="hm-steps">
              <li>בדף שנפתח: כתוב שם — למשל Nifraim — ולחץ "Create".</li>
              <li>Google תציג קוד בן 16 תווים. העתק אותו.</li>
              <li>חזור לכאן והדבק אותו בשדה למעלה.</li>
            </ol>
            <p class="hm-hint">אם Google כותבת שהאפשרות אינה זמינה — צריך קודם להפעיל "אימות דו-שלבי" בחשבון.</p>
            <p class="hm-note">
              הקוד נותן גישת קריאה לכל תיבת המייל, והוא מתבטל אוטומטית בכל פעם שתחליף סיסמה ב-Google.
              מעדיף לא לשמור קוד אצלנו? <button class="hm-link" @click="switchToForwarding">אפשר להעביר אלינו את הדואר במקום</button>
            </p>
            <button class="hm-cta" :disabled="!email || !appPassword || store.saving" @click="saveGoogle">
              {{ store.saving ? 'שומר…' : 'חיבור התיבה' }}
            </button>
          </div>

          <!-- Everything else: forward to us. No credential at all. -->
          <div v-else-if="host === 'other' && !store.capabilities.forwarding" class="hm-problem hm-problem--muted">
            <strong class="hm-problem-title">קליטת דואר עדיין לא זמינה כאן</strong>
            <p class="hm-problem-body">בינתיים אפשר לגרור את הקובץ מהכשרה ישירות ללשונית הפרודוקציה, והוא ייקלט מיד.</p>
          </div>
          <div v-else-if="host === 'other'" class="hm-branch">
            <p class="hm-help">העתק את הכתובת הזו, ובמייל שלך הגדר העברה אוטומטית של ההודעות מהכשרה אליה. זה לוקח דקה.</p>
            <!-- A saved address must never trap the agent: if they retype the email
                 (or switch provider), offer to save it again instead of only showing
                 the old forwarding address. -->
            <div v-if="cfg?.forward_address && !dirty" class="hm-copyrow">
              <input class="hm-input ltr-number" :value="cfg.forward_address" readonly />
              <button class="hm-copy" @click="copyAddress">{{ copied ? 'הועתק' : 'העתק' }}</button>
            </div>
            <button v-else class="hm-cta" :disabled="!email || store.saving" @click="saveOther">
              {{ store.saving ? 'שומר…' : (cfg ? 'עדכון הכתובת' : 'יצירת כתובת העברה') }}
            </button>
            <p class="hm-note">בדרך הזו איננו שומרים שום סיסמה, ורואים רק את ההודעות שתעביר אלינו.</p>
          </div>

          <!-- Gentle errors. Codes never reach the screen. -->
          <div v-if="problem" class="hm-problem" :class="'hm-problem--' + problem.tone">
            <strong class="hm-problem-title">{{ problem.title }}</strong>
            <p class="hm-problem-body">{{ problem.body }}</p>
            <div v-if="problem.action && cfg?.last_error === 'admin_consent_required'" class="hm-problem-actions">
              <button class="hm-link" @click="copyAdminLink">{{ adminCopied ? 'הקישור הועתק' : problem.action }}</button>
            </div>
            <button v-else-if="problem.action" class="hm-link" @click="connectMicrosoft">{{ problem.action }}</button>
            <p v-if="problem.escape" class="hm-escape">
              {{ problem.escape }}
              <button class="hm-link" @click="switchToForwarding">עבור להעברה</button>
            </p>
          </div>

          <footer class="hm-foot">
            <button v-if="cfg" class="hm-disconnect" @click="disconnect">ניתוק</button>
            <button class="hm-done" @click="$emit('close')">סיום</button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useMailboxStore } from '../../stores/mailbox.js'
import { CONNECTED_NO_MAIL_YET, errorCopy, lastReceivedLabel } from '../../utils/mailboxCopy.js'

const props = defineProps({ open: Boolean })
defineEmits(['close'])

const store = useMailboxStore()
const email = ref('')
const appPassword = ref('')
const host = ref(null)
const detecting = ref(false)
const manual = ref(false)
const copied = ref(false)
const adminCopied = ref(false)
const adminUrl = ref('')

const cfg = computed(() => store.config)

// The typed address (or chosen host) differs from what's saved. Drives whether we
// show "save" instead of the saved forwarding address — otherwise a configured
// mailbox is a dead end you can only escape by disconnecting.
const dirty = computed(() =>
  !!cfg.value && (email.value !== cfg.value.email_address || host.value !== cfg.value.mail_host),
)

// Google Workspace deliberately lands on "העברה": since 2025 it refuses an app
// password over IMAP, so offering that field would be a dead end.
const hostOptions = [
  { id: 'microsoft', label: 'Microsoft 365 / Outlook' },
  { id: 'google', label: 'Gmail פרטי' },
  { id: 'other', label: 'ספק אחר / העברה' },
]
const hostLabel = computed(() => {
  const map = {
    microsoft: 'זיהינו: תיבה מנוהלת ע"י Microsoft.',
    google: 'זיהינו: Gmail פרטי.',
    other: 'נשתמש בהעברה אוטומטית — עובד בכל ספק.',
  }
  return map[host.value] || ''
})

// Connected + nothing yet is the NORMAL state 29 days a month. It must not read
// as a failure, or agents stop trusting a feature that works.
const problem = computed(() => {
  if (cfg.value?.last_error) return errorCopy(cfg.value.last_error)
  if (cfg.value?.connected && !cfg.value.last_received_at) return CONNECTED_NO_MAIL_YET
  return null
})

const statusTone = computed(() => {
  if (cfg.value?.last_error) return 'hm-status--warn'
  return cfg.value?.last_received_at ? 'hm-status--ok' : 'hm-status--idle'
})

watch(() => props.open, async (isOpen) => {
  if (!isOpen) return
  copied.value = false
  adminCopied.value = false
  manual.value = false
  await store.fetchConfig()
  if (store.config) {
    email.value = store.config.email_address
    host.value = store.config.mail_host
  }
})

async function onDetect() {
  if (!email.value || !email.value.includes('@')) return
  detecting.value = true
  try {
    host.value = await store.detect(email.value)
  } finally {
    detecting.value = false
  }
}

async function connectMicrosoft() {
  await store.save({ emailAddress: email.value, mailHost: 'microsoft' })
  const { url, admin_consent_url: adminConsentUrl } = await store.microsoftConsentUrl()
  adminUrl.value = adminConsentUrl
  window.location.href = url
}

async function saveGoogle() {
  await store.save({ emailAddress: email.value, appPassword: appPassword.value, mailHost: 'google' })
  appPassword.value = ''
  await store.pollNow()
}

async function saveOther() {
  await store.save({ emailAddress: email.value, mailHost: 'other' })
}

async function switchToForwarding() {
  host.value = 'other'
  await saveOther()
}

async function check() {
  await store.pollNow()
}

async function copyAddress() {
  await navigator.clipboard.writeText(cfg.value.forward_address)
  copied.value = true
}

async function copyAdminLink() {
  if (!adminUrl.value) {
    const { admin_consent_url: adminConsentUrl } = await store.microsoftConsentUrl()
    adminUrl.value = adminConsentUrl
  }
  await navigator.clipboard.writeText(adminUrl.value)
  adminCopied.value = true
}

async function disconnect() {
  await store.disconnect()
  email.value = ''
  host.value = null
}
</script>

<style scoped>
.hm-overlay {
  position: fixed; inset: 0; z-index: 1300;
  display: flex; align-items: center; justify-content: center;
  background: rgba(24, 24, 24, 0.5); backdrop-filter: blur(5px);
  padding: 20px;
}
.hm-card {
  position: relative;
  width: min(520px, 100%); max-height: 90vh; overflow-y: auto;
  background: #fff; border-radius: var(--radius-xl, 24px);
  box-shadow: 0 26px 70px rgba(24, 24, 24, 0.28);
  font-family: 'Heebo', sans-serif;
  padding: 26px 26px 20px;
  display: flex; flex-direction: column; gap: 16px;
  --accent: var(--tab-automation, #1FA88C);
  --tint: color-mix(in srgb, var(--accent) 8%, transparent);
}
.hm-close {
  position: absolute; inset-inline-end: 16px; top: 16px;
  background: none; border: none; cursor: pointer; color: rgba(24, 24, 24, 0.4);
  padding: 4px; border-radius: 8px;
}
.hm-close:hover { color: #181818; background: rgba(24, 24, 24, 0.05); }

.hm-head { display: flex; gap: 12px; align-items: flex-start; padding-inline-end: 28px; }
.hm-ico {
  flex-shrink: 0; width: 34px; height: 34px; border-radius: 11px;
  display: grid; place-items: center;
  background: var(--tint); color: var(--accent);
}
.hm-title { margin: 0 0 4px; font-size: 16px; font-weight: 800; color: #181818; }
.hm-sub { margin: 0; font-size: 12.5px; line-height: 1.6; color: rgba(24, 24, 24, 0.58); }

.hm-status {
  display: flex; align-items: center; gap: 8px;
  padding: 9px 12px; border-radius: 999px; font-size: 12px; font-weight: 700;
}
.hm-status--ok   { background: rgba(31, 168, 140, 0.14); color: #0E7A64; }
.hm-status--warn { background: #FBF3E2; color: #8A6D3B; }
.hm-status--idle { background: rgba(24, 24, 24, 0.06); color: rgba(24, 24, 24, 0.55); }
.hm-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; flex-shrink: 0; }
.hm-status-txt { flex: 1; }

.hm-field { display: flex; flex-direction: column; gap: 6px; }
.hm-label { font-size: 12.5px; font-weight: 700; color: #181818; }
.hm-input {
  width: 100%; padding: 11px 13px;
  border: 1.5px solid var(--border, #DDDBDA); border-radius: 12px;
  font-family: inherit; font-size: 14px; color: #181818;
  direction: ltr; text-align: left;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.hm-input:focus-visible {
  outline: none; border-color: var(--accent);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--accent) 18%, transparent);
}
.hm-input[readonly] { background: rgba(24, 24, 24, 0.03); }

.hm-steps {
  margin: 0; padding-inline-start: 18px;
  display: flex; flex-direction: column; gap: 5px;
  font-size: 12.5px; line-height: 1.6; color: rgba(24, 24, 24, 0.62);
}
.hm-steps li::marker { color: var(--accent); font-weight: 700; }

.hm-manual { display: flex; flex-wrap: wrap; gap: 7px; }
.hm-chip {
  padding: 7px 12px; border-radius: 999px; cursor: pointer;
  border: 1.5px solid var(--border, #DDDBDA); background: #fff;
  font-family: inherit; font-size: 12px; font-weight: 700; color: rgba(24, 24, 24, 0.65);
}
.hm-chip.on { border-color: var(--accent); background: var(--tint); color: #181818; }

.hm-branch { display: flex; flex-direction: column; gap: 10px; }
.hm-cta {
  display: flex; align-items: center; justify-content: center; gap: 9px;
  width: 100%; padding: 12px 14px;
  background: var(--tint);
  border: 1.5px solid color-mix(in srgb, var(--accent) 28%, transparent);
  border-radius: 13px; color: #181818;
  font-family: inherit; font-size: 14px; font-weight: 700; cursor: pointer;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.12s ease;
}
.hm-cta:hover:not(:disabled) {
  border-color: var(--accent);
  box-shadow: 0 4px 14px color-mix(in srgb, var(--accent) 16%, transparent);
  transform: translateY(-1px);
}
.hm-cta:disabled { opacity: 0.55; cursor: default; }
.hm-cta-ico { display: grid; place-items: center; }
/* Secondary: it leaves the app, so it must not compete with "חיבור התיבה". */
.hm-cta--ghost {
  background: #fff; border-color: var(--border, #DDDBDA);
  color: rgba(24, 24, 24, 0.75); text-decoration: none; font-size: 13px;
}
.hm-cta--ghost:hover { border-color: var(--accent); color: #181818; }

.hm-copyrow { display: flex; gap: 8px; align-items: center; }
.hm-copy {
  flex-shrink: 0; padding: 11px 15px; border-radius: 12px;
  background: var(--accent); color: #fff; border: none;
  font-family: inherit; font-size: 13px; font-weight: 700; cursor: pointer;
}

.hm-help, .hm-hint { margin: 0; font-size: 12.5px; line-height: 1.6; color: rgba(24, 24, 24, 0.58); }
.hm-note {
  margin: 0; font-size: 12px; line-height: 1.6;
  color: rgba(24, 24, 24, 0.5);
  background: rgba(24, 24, 24, 0.035); border-radius: 10px; padding: 9px 11px;
}
.hm-a { color: var(--accent); font-weight: 700; }

.hm-problem { border-radius: 13px; padding: 12px 14px; display: flex; flex-direction: column; gap: 5px; }
.hm-problem--warn   { background: #FBF3E2; color: #8A6D3B; }
.hm-problem--danger { background: #FBEAE7; color: #C0392B; }
.hm-problem--muted  { background: rgba(24, 24, 24, 0.04); color: rgba(24, 24, 24, 0.62); }
.hm-problem-title { font-size: 13px; font-weight: 800; }
.hm-problem-body { margin: 0; font-size: 12.5px; line-height: 1.6; }
.hm-escape { margin: 4px 0 0; font-size: 12px; line-height: 1.6; }
.hm-link {
  background: none; border: none; padding: 0; cursor: pointer;
  font-family: inherit; font-size: 12px; font-weight: 800;
  color: inherit; text-decoration: underline;
}
.hm-link:disabled { opacity: 0.6; cursor: default; }

.hm-foot { display: flex; align-items: center; gap: 10px; margin-top: 2px; }
.hm-disconnect {
  background: none; border: none; cursor: pointer; font-family: inherit;
  font-size: 12.5px; font-weight: 700; color: rgba(24, 24, 24, 0.45);
}
.hm-disconnect:hover { color: #C0392B; }
.hm-done {
  margin-inline-start: auto; padding: 10px 22px; border-radius: 12px; border: none;
  background: #181818; color: #fff; font-family: inherit; font-size: 13.5px; font-weight: 700; cursor: pointer;
}

@media (prefers-reduced-motion: reduce) {
  .hm-cta { transition: none; }
  .hm-cta:hover:not(:disabled) { transform: none; }
}

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .hm-card, .modal-leave-to .hm-card { transform: scale(0.94) translateY(12px); opacity: 0; }
.hm-card { transition: transform 0.24s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.2s ease; }
</style>
