<template>
  <!-- The side column: the local computer, the last run, and the state of each
       company at a glance — so the column beside the company list is never an
       empty void. Sticky, so it stays with you while the list scrolls. -->
  <aside class="activity">
    <!-- ── Nifra Robot — the local computer ─────────────────────── -->
    <section class="acard acard--robot" :class="worker.online ? 'is-on' : 'is-off'">
      <RobotComputerArt :online="!!worker.online" :width="168" />
      <strong class="robot-mark" dir="ltr">Nifra <b>Robot</b></strong>
      <span class="robot-status">
        <i class="robot-dot" aria-hidden="true"></i>
        <template v-if="worker.online">מחובר · {{ worker.hostname || 'מחשב הסוכן' }}</template>
        <template v-else-if="lastSeenText">לא מחובר · נראה לאחרונה {{ lastSeenText }}</template>
        <template v-else>לא מחובר · המחשב לא דיווח עדיין</template>
      </span>
      <p v-if="worker.online && worker.current_job" class="worker__job">{{ worker.current_job }}</p>
      <button
        v-if="worker.online"
        class="quiet-btn"
        type="button"
        :disabled="updating || worker.update_pending"
        title="מושך את הקוד העדכני ומפעיל מחדש את המחשב המקומי — בלי גיט ובלי לגעת במחשב"
        @click="onUpdateWorker"
      >
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M21 12a9 9 0 1 1-2.64-6.36" /><path d="M21 3v6h-6" />
        </svg>
        <span>{{ (updating || worker.update_pending) ? 'מתעדכן…' : 'עדכן עובד' }}</span>
      </button>
      <p v-if="updateMsg" class="worker__update-msg">{{ updateMsg }}</p>
    </section>

    <!-- ── Last batch result ─────────────────────────────────── -->
    <section class="acard">
      <h4 class="acard__eyebrow">ריצה אחרונה</h4>
      <div v-if="batch" class="batch">
        <div class="batch__row">
          <span class="batch__state"><i :class="`batch__dot batch__dot--${tone}`" aria-hidden="true"></i>{{ statusLabel }}</span>
          <span class="batch__when">{{ rel(batch.finished_at || batch.started_at) }}</span>
        </div>
        <div class="batch__counts">
          <span><b class="ltr-number">{{ batch.succeeded }}</b> הצליחו</span>
          <span><b class="ltr-number">{{ batch.failed }}</b> נכשלו</span>
        </div>
        <button class="quiet-btn quiet-btn--wide" type="button" @click="$emit('view-results')">
          צפה בתוצאות
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>
        </button>
      </div>
      <div v-else class="batch-empty">
        <AutoStatArt name="clock" :size="40" />
        <span>טרם בוצעה הורדה אוטומטית</span>
      </div>
    </section>

    <!-- ── The portal wheel: every company on one gear ──────────── -->
    <section v-if="companies.length" class="acard acard--wheel">
      <h4 class="acard__eyebrow">הפורטלים</h4>
      <PortalWheel :companies="companies" :last-run-at="batch ? (batch.finished_at || batch.started_at) : null" @select="goTo" />
    </section>
  </aside>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import { relativeHebrew } from '../../utils/relativeTime.js'
import AutoStatArt from './AutoStatArt.vue'
import PortalWheel from './PortalWheel.vue'
import RobotComputerArt from './RobotComputerArt.vue'
import CompanyLogo from './CompanyLogo.vue'
import { brandForLabel } from '../../utils/companyBrand.js'

const props = defineProps({ portalLabel: { type: Function, default: (k) => k } })
defineEmits(['view-results'])
const store = usePortalAutomationStore()

const updating = ref(false)
const updateMsg = ref('')
async function onUpdateWorker() {
  if (updating.value) return
  updating.value = true
  updateMsg.value = ''
  try {
    const res = await store.requestWorkerUpdate()
    updateMsg.value = res?.detail || 'בקשת עדכון נשלחה — המחשב יתעדכן ויופעל מחדש'
    await store.fetchWorkerStatus()
  } catch (e) {
    updateMsg.value = e?.response?.data?.detail || 'שליחת בקשת העדכון נכשלה'
  } finally {
    setTimeout(() => { updating.value = false }, 4000)
    setTimeout(() => { updateMsg.value = '' }, 9000)
  }
}

const worker = computed(() => store.workerStatus || { online: false })
const batch = computed(() => store.latestBatch)

const tone = computed(() => {
  const s = batch.value?.status
  if (s === 'failed') return 'fail'
  if (s === 'partial') return 'partial'
  if (['running', 'pending'].includes(s)) return 'live'
  return 'ok'
})
const statusLabel = computed(() => {
  const s = batch.value?.status
  if (s === 'failed') return 'נכשלה'
  if (s === 'partial') return 'הסתיימה חלקית'
  if (['running', 'pending'].includes(s)) return 'רצה כעת'
  return 'הצליחה'
})

function rel(iso) {
  return iso ? relativeHebrew(iso) : '—'
}

// A worker that never checked in comes back with a placeholder timestamp, and
// `relativeHebrew` dutifully formats it as an absolute date once it is older
// than a week — the card read "נראה לאחרונה 01.01.00", which is not a fact
// about anything. Anything older than a year is "never reported", not a date.
const YEAR_MS = 365 * 24 * 60 * 60 * 1000
const lastSeenText = computed(() => {
  const raw = worker.value?.last_seen
  if (!raw) return ''
  let str = String(raw)
  if (/T\d{2}:\d{2}/.test(str) && !/([zZ]|[+-]\d{2}:?\d{2})$/.test(str)) str += 'Z'
  const t = new Date(str).getTime()
  if (isNaN(t) || Date.now() - t > YEAR_MS) return ''
  return relativeHebrew(raw)
})

// Each company at a glance — the same grouping as the company list (by brand
// label), its health dots and freshest run. A row scrolls to that company.
const companies = computed(() => {
  const map = new Map()
  for (const c of store.credentials || []) {
    const lbl = props.portalLabel(c.portal_kind)
    const b = brandForLabel(lbl)
    const key = b.label && b.label !== '?' ? b.label : lbl
    if (!map.has(key)) map.set(key, { key, label: key, creds: [] })
    map.get(key).creds.push(c)
  }
  return [...map.values()].map((g) => ({
    ...g,
    total: g.creds.length,
    ok: g.creds.filter((c) => c.last_run_status === 'success').length,
    dots: g.creds.map((c) => (c.last_run_status === 'success' ? 'ok' : ['failed', 'timeout'].includes(c.last_run_status) ? 'fail' : c.last_run_status ? 'live' : 'none')),
    lastRunAt: g.creds.reduce((l, c) => (c.last_run_at && (!l || c.last_run_at > l) ? c.last_run_at : l), null),
  }))
})
const okCompanies = computed(() => companies.value.filter((c) => c.ok === c.total).length)
function goTo(c) {
  const el = document.getElementById('company-panel-body-' + String(c.key).replace(/\s+/g, '-'))
  el?.scrollIntoView({ behavior: window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' })
}

let poll = null
onMounted(() => {
  store.fetchWorkerStatus()
  poll = setInterval(() => store.fetchWorkerStatus(), 20000)
})
onUnmounted(() => { if (poll) clearInterval(poll) })
</script>

<style scoped>
.activity {
  --acc: var(--tab-automation, #0E8C8A);
  display: flex; flex-direction: column; gap: 12px;
  position: sticky; top: 80px; align-self: start;
  max-height: calc(100vh - 100px); overflow-y: auto; overscroll-behavior: contain;
  scrollbar-width: thin;
}
.acard {
  background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: 18px; padding: 16px;
  box-shadow: 0 1px 2px rgba(24, 24, 24, 0.03), 0 6px 18px rgba(24, 24, 24, 0.04);
  display: flex; flex-direction: column; gap: 12px;
}
.acard__eyebrow { margin: 0; display: flex; gap: 8px; font-size: 12px; font-weight: 600; color: var(--text-muted); }
.acard__eyebrow span { font-weight: 500; }

/* Nifra Robot — the computer illustration, the two-colour wordmark, the status */
.acard--robot { align-items: center; text-align: center; gap: 8px; padding-top: 20px; }
.robot-mark { font-size: 20px; font-weight: 900; letter-spacing: -0.03em; color: var(--text); }
.robot-mark b { color: var(--acc); font-weight: 900; }
.robot-status { display: inline-flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 500; color: var(--text-secondary); }
.robot-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--text-muted); }
.is-on .robot-dot { background: var(--green); box-shadow: 0 0 0 4px rgba(46, 132, 74, 0.15); }
.acard--robot .quiet-btn { align-self: center; }
.acard--wheel { align-items: stretch; }
.worker--on .worker--on .worker--off .worker__job { margin: 0; font-size: 12.5px; color: var(--text-secondary); background: var(--bg); border-radius: 10px; padding: 8px 10px; }
.worker__update-msg { margin: 0; font-size: 12px; color: var(--text-secondary); }
.quiet-btn {
  align-self: flex-start; display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  height: 36px; padding: 0 14px; border-radius: 999px; border: 1px solid var(--border-subtle); background: transparent;
  color: var(--text); font-family: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.quiet-btn:hover:not(:disabled) { border-color: var(--acc); background: color-mix(in srgb, var(--acc) 6%, transparent); }
.quiet-btn:focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }
.quiet-btn:disabled { opacity: 0.55; cursor: default; }
.quiet-btn--wide { align-self: stretch; }

/* last run */
.batch { display: flex; flex-direction: column; gap: 10px; }
.batch__row { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.batch__state { display: inline-flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 800; color: var(--text); }
.batch__dot { width: 8px; height: 8px; border-radius: 50%; }
.batch__dot--ok { background: var(--green); }
.batch__dot--partial { background: var(--amber); }
.batch__dot--fail { background: var(--red); }
.batch__dot--live { background: var(--acc); animation: wBlink 1.2s ease-in-out infinite; }
@keyframes wBlink { 50% { opacity: 0.3; } }
.batch__when { font-size: 12.5px; color: var(--text-muted); }
.batch__counts { display: flex; gap: 16px; font-size: 13px; color: var(--text-secondary); }
.batch__counts b { font-size: 18px; font-weight: 900; color: var(--text); margin-inline-end: 2px; }
.batch-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 8px; text-align: center; color: var(--text-muted); font-size: 13px; }


@media (max-width: 1023px) {
  .activity { position: static; max-height: none; overflow: visible; }
}
@media (prefers-reduced-motion: reduce) {
  .batch__dot--live { animation: none; }
}
</style>
