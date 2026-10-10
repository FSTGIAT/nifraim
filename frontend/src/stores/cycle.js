import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client.js'
import { usePortalAutomationStore } from './portalAutomation.js'

// Monthly cycle (מחזור) — mirrors GET /api/cycle/status, the server's single
// truth for: the Production tab lock, the manual-production window, the
// automation tab's "next cycle" card, and the cycle notification modal.
// Never derive any of it client-side (backend/app/services/cycle_service.py).

const HE_MONTHS = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']

export function monthName(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${HE_MONTHS[d.getMonth()]} ${d.getFullYear()}`
}

export function shortDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getDate()}.${d.getMonth() + 1}`
}

// Countdowns run on the SERVER's clock: an agent PC whose clock is off (or a
// local simulation's CYCLE_NOW_OVERRIDE) must not show a wrong countdown.
let _skewMs = 0
export function cycleNow() { return Date.now() + _skewMs }
export function cycleSkewMs() { return _skewMs }

export const useCycleStore = defineStore('cycle', () => {
  const status = ref(null)
  const loaded = ref(false)
  const notifications = ref([])
  let pollTimer = null

  const locked = computed(() => !!status.value?.locked)
  const manualUploadOpen = computed(() => !!status.value?.manual_upload_open)
  const workerWaiting = computed(() => !!status.value?.worker_waiting)
  const cycleRunning = computed(() => ['pending', 'running'].includes(status.value?.cycle_batch_status))

  async function fetchStatus() {
    try {
      const prev = status.value?.cycle_batch_status
      const res = await api.get('/cycle/status')
      if (res.data?.server_now) _skewMs = Date.parse(res.data.server_now) - Date.now()
      status.value = res.data
      // The worker just claimed this month's cycle batch → hand it to the
      // live progress widget (it deliberately ignores pending batches).
      if (prev === 'pending' && res.data?.cycle_batch_status === 'running') {
        usePortalAutomationStore().hydrateBatch()
      }
    } catch (_) {
      // Fail OPEN for display (the server still enforces every gate).
    } finally {
      loaded.value = true
    }
    _syncPolling()
    return status.value
  }

  // While the month's cycle batch is queued/running, keep the cards live.
  function _syncPolling() {
    const want = cycleRunning.value
    if (want && !pollTimer) {
      pollTimer = setInterval(fetchStatus, 30000)
    } else if (!want && pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  async function fetchNotifications() {
    try {
      const res = await api.get('/cycle/notifications')
      notifications.value = res.data || []
    } catch (_) {
      notifications.value = []
    }
    return notifications.value
  }

  async function markSeen(id) {
    notifications.value = notifications.value.filter((n) => n.id !== id)
    try {
      await api.post(`/cycle/notifications/${id}/seen`)
    } catch (_) { /* shown again next load — harmless */ }
  }

  function reset() {
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = null
    status.value = null
    loaded.value = false
    notifications.value = []
  }

  return {
    status, loaded, notifications,
    locked, manualUploadOpen, workerWaiting, cycleRunning,
    fetchStatus, fetchNotifications, markSeen, reset,
  }
})

// ── מסלקה timeline wording, shared by every surface (server fields only) ──
// The rule: a שיוך form submitted by the 26th → the מסלקה production arrives on
// the 15th of the next month; from the 27th on → the 15th of the month after.
export const MASLAKA_RULE = 'טופס שיוך שמוגש עד ה-26 בחודש — הפרודוקציה מהמסלקה מגיעה ב-15 בחודש הבא. מה-27 ואילך — ב-15 בחודש שאחריו.'

export function signupLine(st) {
  return st?.signup_at ? `נרשמתם ב-${shortDate(st.signup_at)}` : ''
}

function monthOnly(ym) {
  if (!ym) return ''
  const m = Number(String(ym).slice(5, 7))
  return HE_MONTHS[m - 1] || ''
}

/** Which months the "לא שולם" verdict compared: "פרודוקציה יולי · נפרעים יולי". */
export function judgedMonthsLine(productionYm, nifraimYm) {
  return [productionYm && `פרודוקציה ${monthOnly(productionYm)}`,
          nifraimYm && `נפרעים ${monthOnly(nifraimYm)}`].filter(Boolean).join(' · ')
}

/** When the next נפרעים run comes, and that "לא שולם" moves with it. */
export function nextNifraimLine(st) {
  if (!st?.next_cycle_at || !st?.next_period) return ''
  const m = monthOnly(st.next_period)
  return `נפרעים ${m} ירוצו ב-${shortDate(st.next_cycle_at)} — אז יתעדכן "לא שולם" ל${m}`
}

/**
 * Production arrived for a month with no נפרעים yet (the מסלקה's September
 * before the 21st). `newer` = { month, companies: [{ company, rows }] } from the
 * server. Says plainly that nothing was checked for that month yet.
 */
export function newerProductionLine(newer, st, judgedYm) {
  if (!newer?.companies?.length) return null
  const m = monthOnly(newer.month)
  const when = st?.next_cycle_at ? ` — ירוצו ב-${shortDate(st.next_cycle_at)}` : ''
  const judged = judgedYm ? `"לא שולם" מראה את ${monthOnly(judgedYm)}` : '"לא שולם" מראה את החודש הקודם'
  return {
    title: `אין עדיין נפרעים ל${m}${when}`,
    sub: `פרודוקציה ${m} הגיעה מהמסלקה${newer.arrived_at ? ` ב-${shortDate(newer.arrived_at)}` : ''} עבור ${newer.companies.map(c => c.company).join(', ')}. עד שהנפרעים יגיעו, ${judged}.`,
  }
}

/**
 * Which month each company's production is for, when the book mixes months
 * (a מסלקה book). Lines, the first a summary, then one per company that is
 * only partly on the new month, naming the families:
 *   "ספטמבר מהמסלקה: הפניקס, מור · עדיין יולי: הראל, מנורה"
 *   "הפניקס — גמל והשתלמות: ספטמבר · פנסיה וביטוח: עדיין יולי"
 * A family counts as arrived once any of its rows did (a few leftovers are
 * products the new answer no longer lists).
 */
function heJoin(list) {
  return list.length < 2 ? (list[0] || '') : `${list.slice(0, -1).join(', ')} ו${list[list.length - 1]}`
}
export function bookMonthsLines(companyMonths, companyFamilies) {
  if (!companyMonths) return []
  const months = new Set()
  for (const by of Object.values(companyMonths)) for (const m of Object.keys(by)) if (m !== '—') months.add(m)
  if (months.size < 2) return []
  const newest = [...months].sort().pop()
  const fresh = [], stale = new Map(), partial = []
  for (const [co, by] of Object.entries(companyMonths)) {
    const ms = Object.keys(by).filter(m => m !== '—')
    if (!ms.includes(newest)) {
      const m = ms.sort().pop()
      stale.set(m, [...(stale.get(m) || []), co])
      continue
    }
    fresh.push(co)
    const fams = companyFamilies?.[co] || {}
    const arrived = Object.keys(fams).filter(f => fams[f][newest])
    const waiting = Object.keys(fams).filter(f => !fams[f][newest])
    if (arrived.length && waiting.length) {
      const was = Object.keys(fams[waiting[0]]).filter(m => m !== '—').sort().pop()
      partial.push(`${co} — ${heJoin(arrived)}: ${monthOnly(newest)} · ${heJoin(waiting)}: עדיין ${monthOnly(was)}`)
    }
  }
  const head = [`${monthOnly(newest)} מהמסלקה: ${fresh.join(', ')}`]
  for (const [m, cos] of [...stale.entries()].sort().reverse()) head.push(`עדיין ${monthOnly(m)}: ${cos.join(', ')}`)
  return [head.join(' · '), ...partial]
}

/** Companies whose production for the judged month hasn't arrived — not checked. */
export function waitingProductionLine(waiting) {
  if (!waiting?.length) return ''
  const m = monthOnly(waiting[0].month)
  return `לא נבדקו (הפרודוקציה שלהן עדיין של ${m}): ${waiting.map(w => w.company).join(', ')}`
}

/** { title, sub, tone } describing where the agent stands with the מסלקה. */
export function maslakaLine(st) {
  if (!st) return null
  const s = st.maslaka_status
  if (s === 'approved') {
    return {
      tone: 'ok',
      title: `פרודוקציה מהמסלקה ב-${shortDate(st.maslaka_first_auto)}`,
      sub: [st.maslaka_submitted_at && `הוגש ב-${shortDate(st.maslaka_submitted_at)}`, st.maslaka_approved_at && `אושר ב-${shortDate(st.maslaka_approved_at)}`].filter(Boolean).join(' · '),
    }
  }
  if (s === 'submitted') {
    return {
      tone: 'wait',
      title: `פרודוקציה מהמסלקה ב-${shortDate(st.maslaka_first_auto)}`,
      sub: `הוגש ב-${shortDate(st.maslaka_submitted_at)} · ממתין לאישור המסלקה`,
    }
  }
  return {
    tone: 'todo',
    title: `הגישו את טופס השיוך עד ${shortDate(st.maslaka_deadline)}`,
    sub: `והפרודוקציה מהמסלקה תגיע ב-${shortDate(st.maslaka_if_submitted_now)}`,
  }
}
