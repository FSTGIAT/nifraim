import { computed, ref } from 'vue'
import { usePortalAutomationStore } from '../stores/portalAutomation.js'
import { useCycleStore, shortDate } from '../stores/cycle.js'
import { useMailboxStore } from '../stores/mailbox.js'
import api from '../api/client.js'
import { useNotificationsStore } from '../stores/notifications.js'
import { getUserFlag, setUserFlag } from '../utils/userFlags.js'
import { CHART_PALETTE } from '../utils/chartPalette.js'

/**
 * Single source of truth for the new-user setup pipeline ("אשף ההפעלה").
 * Shared by SetupPipelineModal, SetupProgressCard and the empty-state guides,
 * so step order, copy, done-detection and flags live in exactly one place.
 *
 * Flags (per-user via userFlags):
 *   setup_completed — all steps done (or detected done on bootstrap).
 *   setup_closed    — the user ✕-closed the home card; bell reminder remains
 *                     the way back. Closing the modal itself sets nothing.
 * Legacy flags from the pre-wizard surfaces (activation_*) migrate forward on
 * bootstrap so existing users don't get re-onboarded.
 */

const DONE_KEY = 'setup_completed'
const CLOSED_KEY = 'setup_closed'
const REMINDER_ID = 'activation-setup'

// One hue per mission, shared by the wizard and the home card. Drawn from
// CHART_PALETTE (never orange: --primary is the brand ACTION colour, and the
// card's CTA is orange — an orange step read as one monochrome blob). `run`
// wears the automation tab's identity (--tab-automation), since that is where
// it lands. `deep` is the text ink — every accent-on-white fails or skirts
// 4.5:1, so text uses `deep` (≥4.7:1 on `soft`). Literal hexes, not var(),
// because the modal builds alpha variants by suffixing (`accent + '55'`).
export const SETUP_ACCENTS = {
  worker: { accent: CHART_PALETTE[3], deep: '#6C2E87', soft: '#F1E9F5', tint: '#FAF8FC' },  // purple
  phone:  { accent: CHART_PALETTE[1], deep: '#35719A', soft: '#EAF3F9', tint: '#F8FBFD' },  // sky (= --tab-portal-ink)
  portal: { accent: CHART_PALETTE[5], deep: '#B0245A', soft: '#FAE7ED', tint: '#FDF7F9' },  // magenta
  mail:    { accent: '#4E9DD0', deep: '#2F6C94', soft: '#E8F1F8', tint: '#F7FAFD' },        // sky (= --tab-mail)
  agreements: { accent: '#8E44AD', deep: '#6B2F86', soft: '#F3EAF7', tint: '#FBF8FD' },   // purple (= --tab-commission)
  maslaka: { accent: '#2C5F6B', deep: '#2C5F6B', soft: '#E4EDEF', tint: '#F6F9FA' },       // deep teal (= --tab-maslaka)
  run:    { accent: CHART_PALETTE[11], deep: '#0A6664', soft: '#E2F1F1', tint: '#F5FAFA' }, // teal (= --tab-automation)
}

// How many agreements the agent has on the shelf (documents + rate rows).
// Module-level so the modal, the home card and the locked tab share it.
const agreementsCount = ref(null)
// Agreement requests already emailed to insurers (the wizard's in-place flow).
const agreementRequestsSent = ref(0)

// Worker heartbeat poll is shared (modal + card may both be mounted).
let pollTimer = null
let pollRefs = 0

export function useSetupPipeline() {
  const store = usePortalAutomationStore()
  const notifications = useNotificationsStore()
  const cycle = useCycleStore()
  const mailbox = useMailboxStore()

  // "Done" = ever achieved, not live state: a veteran whose PC is off, or whose
  // last batch failed, has still finished setup and must not be re-onboarded.
  const workerDone = computed(() => !!(store.workerStatus?.online || store.workerStatus?.ever_connected))
  const phoneDone = computed(() => !!store.phoneForward?.token)
  const credsDone = computed(() => (store.credentials?.length || 0) > 0)
  const runDone = computed(() =>
    ['success', 'partial'].includes(store.latestBatch?.status) || !!store.setupStatus?.has_successful_run,
  )
  const mailDone = computed(() => !!(mailbox.config && mailbox.config.is_active))
  // Done once agreements are on the shelf OR the requests went out (the
  // replies load by themselves).
  const agreementsDone = computed(() => (agreementsCount.value || 0) > 0 || agreementRequestsSent.value > 0)
  // "Signed" = the שיוך form was SUBMITTED (approval may come later).
  const maslakaDone = computed(() => ['submitted', 'approved'].includes(cycle.status?.maslaka_status))
  const firstCycleLabel = computed(() => {
    const at = cycle.status?.first_cycle_at
    return at ? `${shortDate(at)} בשעה 06:00` : 'ה-21 בחודש בשעה 06:00'
  })

  // Phone comes first: the installer embeds the phone-forward token, so the
  // worker step can't be completed until the phone step is.
  const steps = computed(() => [
    {
      id: 'phone',
      title: 'חברו את Nifraim Sms App',
      body: 'קבלת OTP מחברות הביטוח.',
      cta: 'חבר את הטלפון',
      hint: '',
      done: phoneDone.value,
    },
    {
      id: 'worker',
      title: 'התקינו את Nifraim ROBOT',
      body: '',
      cta: 'הורד מתקין',
      hint: 'לחצו פעמיים על הקובץ שירד — תוך כ-20 שניות המחוון כאן יהפוך ל"מחובר".',
      done: workerDone.value,
    },
    {
      id: 'mail',
      title: 'חברו את Nifraim Mail Agent',
      body: 'קורא את המיילים מלקוחות ומחברות שאישרתם, מנסח תשובות מתוך הנתונים שלכם — ושולח באישורכם.',
      cta: 'פתיחת Mail Agent',
      hint: '',
      done: mailDone.value,
    },
    {
      id: 'agreements',
      title: 'מדף ההסכמים',
      body: 'ההסכמים מגיעים אליכם — לבד.',
      cta: 'העלאת הסכמים',
      hint: '',
      done: agreementsDone.value,
    },
    {
      id: 'maslaka',
      title: 'שיוך למסלקה',
      body: 'טופס חד-פעמי שמחבר אותך למסלקה הפנסיונית. טופס שמוגש עד ה-26 בחודש — הפרודוקציה מגיעה לבד כבר ב-15 בחודש הבא.',
      cta: 'מילוי טופס שיוך',
      hint: '',
      done: maslakaDone.value,
    },
    {
      id: 'portal',
      title: 'הוסיפו פורטל ראשון',
      body: 'שם משתמש וסיסמה לפורטל הסוכן של חברת הביטוח.',
      cta: 'הוסף פורטל',
      hint: '',
      done: credsDone.value,
    },
    {
      // Monthly cycle: there is no "run now" — the first cycle runs by itself.
      id: 'run',
      title: 'המחזור הראשון',
      body: `ב-${firstCycleLabel.value} Nifraim מוריד לבד את הנפרעים של החודש הקודם מכל החברות. אין צורך ללחוץ על כלום — רק שהמחשב יהיה דלוק.`,
      cta: 'לצפייה באוטומציה',
      hint: '',
      // Nothing to press: once every other step is done the first cycle is
      // simply SCHEDULED — count it, or the wizard would reopen for weeks.
      done: runDone.value || (phoneDone.value && workerDone.value && credsDone.value
        && mailDone.value && agreementsDone.value && maslakaDone.value),
    },
  ])

  const completedCount = computed(() => steps.value.filter((s) => s.done).length)
  const allDone = computed(() => completedCount.value >= steps.value.length)
  const firstIncompleteId = computed(() => steps.value.find((s) => !s.done)?.id || null)

  function migrateFlags() {
    if (getUserFlag(DONE_KEY) == null && getUserFlag('activation_completed') === 'true') {
      setUserFlag(DONE_KEY, 'true')
    }
    if (getUserFlag(CLOSED_KEY) == null && getUserFlag('activation_closed') === 'true') {
      setUserFlag(CLOSED_KEY, 'true')
    }
  }

  async function bootstrap() {
    migrateFlags()
    await Promise.all([
      store.fetchPhoneForward().catch(() => {}),
      store.fetchCredentials().catch(() => {}),
      store.fetchLatestBatch().catch(() => {}),
      store.fetchWorkerStatus().catch(() => {}),
      store.fetchSetupStatus().catch(() => {}),
      cycle.fetchStatus().catch(() => {}),
      mailbox.fetchConfig().catch(() => {}),
      fetchAgreementsCount(),
    ])
  }

  async function fetchAgreementsCount() {
    try {
      const [docs, rates, reqs] = await Promise.all([
        api.get('/ai/documents').catch(() => ({ data: [] })),
        api.get('/commission-rates').catch(() => ({ data: [] })),
        api.get('/agreement-requests').catch(() => ({ data: null })),
      ])
      agreementRequestsSent.value = reqs.data?.sent_count || 0
      const n = (d) => (Array.isArray(d) ? d.length : Array.isArray(d?.items) ? d.items.length : 0)
      agreementsCount.value = n(docs.data) + n(rates.data)
    } catch (_) { /* leave unknown */ }
  }

  function startWorkerPoll() {
    pollRefs++
    if (!pollTimer) {
      pollTimer = setInterval(() => store.fetchWorkerStatus().catch(() => {}), 8000)
    }
  }

  function stopWorkerPoll() {
    pollRefs = Math.max(0, pollRefs - 1)
    if (pollRefs === 0 && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  const isCompleted = () => getUserFlag(DONE_KEY) === 'true'
  const isClosed = () => getUserFlag(CLOSED_KEY) === 'true'

  function pinReminder() {
    notifications.pinAlert({
      id: REMINDER_ID,
      kind: 'activation',
      severity: 'info',
      title: 'השלם את הפעלת האוטומציה',
      body: 'נותרו צעדים להפעלת ההורדה האוטומטית מכל החברות',
      createdAt: new Date().toISOString(),
      actions: ['reopen_activation'],
      meta: {},
    })
  }

  function markCompleted() {
    setUserFlag(DONE_KEY, 'true')
    notifications.unpinAlert(REMINDER_ID)
  }

  function closeCard() {
    setUserFlag(CLOSED_KEY, 'true')
    if (!allDone.value) pinReminder()
  }

  return {
    steps,
    completedCount,
    allDone,
    firstIncompleteId,
    bootstrap,
    startWorkerPoll,
    stopWorkerPoll,
    migrateFlags,
    isCompleted,
    isClosed,
    pinReminder,
    markCompleted,
    closeCard,
    refreshAgreements: fetchAgreementsCount,
  }
}
