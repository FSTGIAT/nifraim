import { computed } from 'vue'
import { usePortalAutomationStore } from '../stores/portalAutomation.js'
import { useNotificationsStore } from '../stores/notifications.js'
import { getUserFlag, setUserFlag } from '../utils/userFlags.js'

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

// Worker heartbeat poll is shared (modal + card may both be mounted).
let pollTimer = null
let pollRefs = 0

export function useSetupPipeline() {
  const store = usePortalAutomationStore()
  const notifications = useNotificationsStore()

  const workerDone = computed(() => !!store.workerStatus?.online)
  const phoneDone = computed(() => !!store.phoneForward?.token)
  const credsDone = computed(() => (store.credentials?.length || 0) > 0)
  const runDone = computed(() => ['success', 'partial'].includes(store.latestBatch?.status))

  const steps = computed(() => [
    {
      id: 'worker',
      title: 'התקינו את המחשב',
      body: 'התקנה חד-פעמית: ההורדות ירוצו ישירות מהמחשב שלך (כתובת IP ישראלית), וכל החברות יעבדו.',
      cta: 'הורד מתקין',
      hint: 'לחצו פעמיים על הקובץ שירד — תוך כ-20 שניות המחוון כאן יהפוך ל"מחובר".',
      done: workerDone.value,
    },
    {
      id: 'phone',
      title: 'חברו את הטלפון',
      body: 'הטלפון מעביר את קוד האימות (SMS) אוטומטית — בלי הקלדה. הגדרה חד-פעמית.',
      cta: 'חבר את הטלפון',
      hint: '',
      done: phoneDone.value,
    },
    {
      id: 'portal',
      title: 'הוסיפו פורטל ראשון',
      body: 'שם משתמש וסיסמה לפורטל הסוכן של חברת הביטוח — מוסיפים פעם אחת, ומכאן הכל אוטומטי.',
      cta: 'הוסף פורטל',
      hint: '',
      done: credsDone.value,
    },
    {
      id: 'run',
      title: 'הריצו הורדה אוטומטית',
      body: 'לחיצה אחת מורידה את הדוחות מכל החברות ומאחדת אותם לשני קבצים: פרודוקציה + נפרעים.',
      cta: 'הרץ עכשיו',
      hint: '',
      done: runDone.value,
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
    ])
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
  }
}
