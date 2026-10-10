/**
 * Nifra reminders in the browser — mounted ONCE (ReminderToasts in WorkspaceView).
 *
 * - The morning brief: the first time the agent is in the app each day (tab visible), once.
 * - The heads-up: 15 minutes before a task's time (said exactly in the call, or confirmed by the agent).
 *
 * Dedupe is the SERVER claim (POST /calls-insights/reminders/claim): two tabs, two devices — the
 * first claimer speaks, everyone else stays quiet. Speech needs a user gesture on the page first, so
 * a reminder that lands before any click waits for the first click/key and speaks then; a hidden
 * tab gets a desktop Notification. A 30s tick (not long timers — background tabs throttle those).
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useCallsInsightsStore } from '../stores/callsInsights.js'
import { askNotifyPermission, notify, speak } from '../utils/voice.js'

const REFRESH_MS = 5 * 60 * 1000
const TICK_MS = 30 * 1000
const MISSED_AFTER_MS = 30 * 60 * 1000   // more than half an hour past the time: missed, don't nag
const SNOOZE_MS = 10 * 60 * 1000

export function useVoiceReminders() {
  const store = useCallsInsightsStore()
  const toasts = ref([])
  const handled = new Set()       // keys this page already took care of
  let pending = null              // sentences waiting for the first click
  let tick = 0
  let refresh = 0
  let checking = false
  const snoozes = new Set()

  const visible = () => document.visibilityState === 'visible'
  const activated = () => (navigator.userActivation ? navigator.userActivation.hasBeenActive : true)

  async function say(sentences, title, body) {
    if (!store.voiceOn) return
    if (!visible()) { notify(title, body); pending = sentences; return }
    if (activated() && await speak(sentences)) return
    pending = sentences
  }
  let asked = false
  function onGesture() {
    // the first click also asks once for desktop notifications — the only channel a hidden tab has
    if (store.voiceOn && !asked) { asked = true; askNotifyPermission() }
    if (pending && store.voiceOn) speak(pending)
    pending = null
  }
  // another window is up (Nifra Agent greeting, a call's follow-up letter, the setup wizard): the brief waits
  const windowOpen = () => !!document.querySelector('.na-overlay, .cfl-overlay, .spm-overlay, .nms-overlay')

  function present(t) {
    toasts.value = [...toasts.value.filter((x) => x.id !== t.id), t].slice(-3)
    say(t.sentences, t.title, t.text)
  }
  function dismiss(id) {
    toasts.value = toasts.value.filter((x) => x.id !== id)
    pending = null
  }

  function briefToast(b) {
    return { id: b.key, kind: 'brief', title: b.sentences_he[0], text: b.headline, sentences: b.sentences_he }
  }
  function taskToast(t) {
    const soon = !t.late_today && Date.now() < Date.parse(t.fire_at) + 15 * 60 * 1000
    return {
      id: t.key, kind: 'task', item: t,
      title: soon ? `בעוד רבע שעה · ${t.due_time}` : `הגיע הזמן · ${t.due_time}`,
      text: t.customer ? `${t.text} · ${t.customer}` : t.text,
      sentences: [t.speak_he],
    }
  }

  async function check() {
    const r = store.reminders
    if (!r || checking) return
    checking = true
    try {
      const b = r.brief
      // the brief is for when the agent is actually here — a background tab waits until it's looked at
      // nothing open from the calls → no brief at all (agents who don't use calls never hear from us)
      if (r.open > 0 && visible() && !windowOpen() && !b.claimed && !handled.has(b.key)) {
        handled.add(b.key)
        if (await store.claim(b.key)) { b.claimed = true; present(briefToast(b)) }
      }
      const now = Date.now()
      for (const t of r.timed) {
        if (t.claimed || handled.has(t.key)) continue
        const fire = Date.parse(t.fire_at)
        if (now < fire || now > fire + 15 * 60 * 1000 + MISSED_AFTER_MS) continue
        handled.add(t.key)
        if (await store.claim(t.key)) { t.claimed = true; present(taskToast(t)) }
      }
    } finally {
      checking = false
    }
  }

  async function reload() {
    await store.loadReminders()
    await check()
  }
  function onVisible() { if (visible()) reload() }

  function snooze(toast) {
    dismiss(toast.id)
    const h = setTimeout(() => { snoozes.delete(h); present({ ...toast, title: 'תזכורת חוזרת', sentences: toast.sentences }) }, SNOOZE_MS)
    snoozes.add(h)
  }
  async function done(toast) {
    dismiss(toast.id)
    if (toast.item) await store.markDone(toast.item.call_id, toast.item.task_index)
  }
  async function replay(toast) { if (await speak(toast.sentences)) pending = null }

  onMounted(() => {
    reload()
    tick = setInterval(check, TICK_MS)
    refresh = setInterval(reload, REFRESH_MS)
    document.addEventListener('visibilitychange', onVisible)
    document.addEventListener('pointerdown', onGesture, true)
    document.addEventListener('keydown', onGesture, true)
  })
  onBeforeUnmount(() => {
    clearInterval(tick)
    clearInterval(refresh)
    snoozes.forEach(clearTimeout)
    document.removeEventListener('visibilitychange', onVisible)
    document.removeEventListener('pointerdown', onGesture, true)
    document.removeEventListener('keydown', onGesture, true)
  })

  return { toasts, dismiss, snooze, done, replay }
}
