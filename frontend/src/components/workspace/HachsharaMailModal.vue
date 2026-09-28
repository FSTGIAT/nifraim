<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="hm-overlay" @click.self="$emit('close')">
        <div class="hm-card hm-card--wide">
          <!-- visual pane: the Mail Agent story as a loop instead of a paragraph -->
          <aside class="hm-visual" aria-hidden="true">
            <RemotionLoopIsland
              component="MailAgentLoop"
              frames-key="MAIL_AGENT_LOOP_FRAMES"
              :width="480"
              :height="720"
              :input-props="{ accent: '#4E9DD0', deep: '#2F6C94', soft: '#E8F1F8' }"
            >
              <img v-if="stillArt" :src="stillArt" alt="" class="hm-visual-still" />
            </RemotionLoopIsland>
          </aside>
          <div class="hm-body">
          <button class="hm-close" aria-label="סגירה" @click="$emit('close')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" /></svg>
          </button>

          <header class="hm-head">
            <span class="hm-kicker">{{ purpose === 'general' ? 'חיבור המייל' : 'הפרודוקציה של הכשרה' }}</span>
            <h3 v-if="purpose === 'general'" class="hm-title hm-title--brand" dir="ltr"><span>Nifraim</span> <span class="hm-title-acc">Mail Agent</span></h3>
            <h3 v-else class="hm-title hm-title--brand">חיבור <span class="hm-title-acc">תיבת המייל</span></h3>
            <p v-if="purpose === 'general'" class="hm-sub">קורא את המיילים מהשולחים שאישרתם, מנסח תשובות מהנתונים — ושולח באישורכם.</p>
            <p v-else class="hm-sub">הכשרה שולחת את הפרודוקציה במייל — נזהה ונטען אותה לבד.</p>
            <!-- Honest about sending: only a Gmail app-password mailbox can
                 send today (Outlook needs Mail.Send consent — not yet). -->
            <p v-if="purpose === 'general' && store.detected && store.detected !== 'google'" class="hm-sub hm-sub--note">
              מהתיבה הזו נוכל לקרוא ולעקוב. שליחה אוטומטית זמינה כרגע מ-Gmail.
            </p>
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
            <span class="hm-label">{{ purpose === 'general' ? 'כתובת המייל שלך' : 'כתובת המייל שאליה הכשרה שולחת' }}</span>
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
            <p class="hm-lead">קוד אפליקציה בן 16 תווים — לא הסיסמה הרגילה.</p>
            <ol class="hm-flow">
              <li class="hm-flow-step" :class="{ 'is-done': openedGoogle }" style="--i: 0">
                <span class="hm-flow-n">1</span>
                <div class="hm-flow-main">
                  <strong>פותחים את דף הקודים של Google</strong>
                  <!-- Straight to the one page that matters (the security page no
                       longer links to app passwords — a dead end). -->
                  <a class="hm-flow-btn" href="https://myaccount.google.com/apppasswords" target="_blank" rel="noopener" @click="openedGoogle = true">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>
                    פתיחה ב-Google
                  </a>
                </div>
              </li>
              <li class="hm-flow-step" style="--i: 1">
                <span class="hm-flow-n">2</span>
                <div class="hm-flow-main">
                  <strong>יוצרים קוד בשם <span dir="ltr" class="hm-chip-name">Nifraim</span> ומעתיקים</strong>
                </div>
              </li>
              <li class="hm-flow-step" :class="{ 'is-done': appPassword.length >= 16 }" style="--i: 2">
                <span class="hm-flow-n">3</span>
                <div class="hm-flow-main">
                  <strong>מדביקים כאן</strong>
                  <input v-model.trim="appPassword" class="hm-input ltr-number" type="password" placeholder="abcd efgh ijkl mnop" autocomplete="off" aria-label="סיסמת אפליקציה" />
                </div>
              </li>
            </ol>
            <p class="hm-tip">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
              לא מופיע? מפעילים קודם "אימות דו-שלבי" בחשבון Google.
            </p>
            <button class="hm-cta hm-cta--solid" :disabled="!email || !appPassword || store.saving" @click="saveGoogle">
              {{ store.saving ? 'מחבר…' : (purpose === 'general' ? 'חיבור Nifraim Mail Agent' : 'חיבור התיבה') }}
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
            <div v-if="problem.action || problem.adminAction" class="hm-problem-actions">
              <button v-if="problem.action" class="hm-link" @click="onProblemAction">
                {{ isAdminOnly && adminCopied ? 'הקישור הועתק' : problem.action }}
              </button>
              <!-- A second, distinct action: Microsoft's refusal can't tell us whether
                   retrying is even permitted in this organisation, so we offer both. -->
              <button v-if="problem.adminAction" class="hm-link" @click="copyAdminLink">
                {{ adminCopied ? 'הקישור הועתק' : problem.adminAction }}
              </button>
            </div>
            <!-- Only offer the escape we can actually honour: without inbound mail
                 configured, "עבור להעברה" walks the agent into "לא זמין כאן". -->
            <p v-if="problem.escape && store.capabilities.forwarding" class="hm-escape">
              {{ problem.escape }}
              <button class="hm-link" @click="switchToForwarding">עבור להעברה</button>
            </p>
            <p v-else-if="problem.escape" class="hm-escape">
              עד שהחיבור יאושר — אפשר לגרור את הקובץ מהכשרה ישירות ללשונית הפרודוקציה, והוא ייקלט מיד.
            </p>
          </div>

          <footer class="hm-foot">
            <button v-if="cfg" class="hm-disconnect" @click="disconnect">ניתוק</button>
            <button class="hm-done" @click="$emit('close')">סיום</button>
          </footer>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useMailboxStore } from '../../stores/mailbox.js'
import RemotionLoopIsland from './RemotionLoopIsland.vue'
import { CONNECTED_NO_MAIL_YET, errorCopy, lastReceivedLabel } from '../../utils/mailboxCopy.js'

const props = defineProps({
  open: Boolean,
  // 'hachshara' = production intake by mail (read-only copy);
  // 'general'   = the setup wizard's "connect your mailbox" (send + track).
  purpose: { type: String, default: 'hachshara' },
})
defineEmits(['close'])

const store = useMailboxStore()
// Reduced-motion still for the visual pane (the wizard's Mail Agent picture).
const stillArt = Object.values(import.meta.glob('../../assets/welcome/step-mail.webp', { eager: true, import: 'default' }))[0] || ''
const openedGoogle = ref(false)
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

// admin_consent_required has ONE move (the admin approves); its primary button is
// the copy-link, not a retry that will fail the same way.
const isAdminOnly = computed(() => cfg.value?.last_error === 'admin_consent_required')

function onProblemAction() {
  if (isAdminOnly.value) return copyAdminLink()
  return connectMicrosoft()
}

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
.hm-sub.hm-sub--note { margin-top: 6px; color: var(--amber, #8A6300); font-weight: 600; }
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

/* ═══════════ Nifraim Mail Agent — wide, designed window ═══════════ */
.hm-card--wide {
  width: min(960px, 94vw); max-width: none; max-height: min(760px, 94vh);
  padding: 0; display: grid; grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr); overflow: hidden;
}
.hm-visual { position: relative; background: linear-gradient(170deg, #fff 0%, #E8F1F8 100%); border-left: 1px solid #E3EDF5; display: flex; align-items: center; justify-content: center; }
.hm-visual :deep(.rli) { width: 100%; max-height: 100%; }
.hm-visual-still { width: 100%; height: 100%; object-fit: cover; }
.hm-body { position: relative; padding: 30px 32px 22px; overflow-y: auto; display: flex; flex-direction: column; gap: 12px; }
.hm-card--wide .hm-close { top: 16px; left: 16px; }
.hm-head { display: flex; flex-direction: column; gap: 4px; margin-bottom: 6px; }
.hm-kicker { align-self: flex-start; padding: 4px 11px; border-radius: 999px; background: #E8F1F8; color: #2F6C94; font-size: 11.5px; font-weight: 800; }
.hm-title--brand { margin: 4px 0 0; font-size: clamp(26px, 2.6vw, 34px); font-weight: 900; letter-spacing: -0.02em; line-height: 1.1; color: var(--text, #181818); }
.hm-title--brand[dir='ltr'] { text-align: right; }
.hm-title-acc { color: #2F6C94; }
.hm-card--wide .hm-sub { margin: 0; font-size: 15px; line-height: 1.6; color: var(--text-secondary, #3E3E3C); }
.hm-card--wide .hm-sub--note { color: #8A6300; font-weight: 700; font-size: 13.5px; }
.hm-card--wide .hm-input { height: 46px; border-radius: 12px; font-size: 15px; }
.hm-lead { margin: 0; font-size: 14px; font-weight: 700; color: #2F6C94; }

.hm-flow { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 10px; }
.hm-flow-step {
  position: relative; display: flex; align-items: flex-start; gap: 12px; padding: 12px 14px;
  border-radius: 14px; background: #fff; border: 1px solid #E3EDF5;
  box-shadow: 0 4px 14px rgba(47, 108, 148, 0.06);
  animation: hmIn 0.45s cubic-bezier(0.32, 0.72, 0, 1) both; animation-delay: calc(var(--i) * 0.12s);
}
@keyframes hmIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
.hm-flow-n {
  flex: none; width: 30px; height: 30px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: #E8F1F8; color: #2F6C94; font-size: 14px; font-weight: 900;
  transition: background 0.25s ease, color 0.25s ease;
}
.hm-flow-step.is-done { border-color: rgba(46, 132, 74, 0.35); }
.hm-flow-step.is-done .hm-flow-n { background: #2E844A; color: #fff; }
.hm-flow-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.hm-flow-main strong { font-size: 15px; font-weight: 800; color: var(--text, #181818); line-height: 1.4; }
.hm-chip-name { padding: 1px 8px; border-radius: 6px; background: #E8F1F8; color: #2F6C94; }
.hm-flow-btn {
  align-self: flex-start; display: inline-flex; align-items: center; gap: 7px; height: 36px; padding: 0 14px;
  border-radius: 10px; border: 1.5px solid #BFD8EA; color: #2F6C94; background: #F7FAFD;
  font-size: 13.5px; font-weight: 800; text-decoration: none;
}
.hm-flow-btn:hover { background: #E8F1F8; }
.hm-tip { margin: 0; display: flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--text-secondary, #706E6B); }
.hm-cta--solid {
  height: 50px; border: none; border-radius: 12px; background: #2F6C94; color: #fff;
  font-size: 15.5px; font-weight: 800; box-shadow: 0 8px 20px rgba(47, 108, 148, 0.28);
}
.hm-cta--solid:hover:not(:disabled) { background: #265a7c; transform: translateY(-1px); }
.hm-cta--solid:disabled { opacity: 0.55; box-shadow: none; }
@media (max-width: 760px) {
  .hm-card--wide { grid-template-columns: 1fr; max-height: 94vh; overflow-y: auto; }
  .hm-visual { height: 220px; border-left: none; border-bottom: 1px solid #E3EDF5; }
  .hm-body { overflow: visible; padding: 22px 20px; }
}
@media (prefers-reduced-motion: reduce) { .hm-flow-step { animation: none; } }
</style>
