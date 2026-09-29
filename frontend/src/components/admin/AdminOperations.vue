<template>
  <!-- Admin · תפעול: everything that runs on its own, per agent — the monthly
       cycle on each worker, the worker itself, Nifraim Mail Agent, the מסלקה
       link + downloads, agreement requests. GET /api/admin/operations. -->
  <section class="ops">
    <header class="ops-head">
      <div class="ops-titles">
        <h2 class="ops-title">תפעול <span class="ops-title-acc">מערכות</span></h2>
        <p v-if="data && data.cycle.prelaunch" class="ops-sub">
          <span class="ops-chip ops-chip--muted">לפני ההשקה</span>
          המחזור הראשון <span class="ltr-number">{{ fmtDate(data.cycle.next_cycle_at) }}</span>
        </p>
        <p v-else-if="data" class="ops-sub">
          מחזור <strong>{{ data.cycle.current_period_label }}</strong>
          · המחזור הבא <span class="ltr-number">{{ fmtDate(data.cycle.next_cycle_at) }}</span>
        </p>
      </div>
      <div class="ops-actions">
        <span v-if="updatedAt" class="ops-updated">עודכן {{ ago(updatedAt) }}</span>
        <button type="button" class="ops-refresh" :disabled="loading" @click="load">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" :class="{ spin: loading }"><path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/></svg>
          רענון
        </button>
      </div>
    </header>

    <div v-if="error" class="ops-error">{{ error }}</div>

    <!-- KPIs -->
    <div v-if="data" class="ops-kpis">
      <div v-for="k in kpis" :key="k.label" class="ops-kpi" :class="'ops-kpi--' + k.tone">
        <span class="ops-kpi-n ltr-number">{{ k.value }}</span>
        <span class="ops-kpi-l">{{ k.label }}</span>
      </div>
    </div>

    <!-- filters -->
    <div v-if="data" class="ops-filters">
      <button v-for="f in FILTERS" :key="f.id" type="button" class="ops-filter" :class="{ on: filter === f.id }" @click="filter = f.id">
        {{ f.label }}<span class="ops-filter-n ltr-number">{{ countFor(f.id) }}</span>
      </button>
      <input v-model.trim="q" class="ops-search" type="search" placeholder="חיפוש סוכן / מייל" />
    </div>

    <div v-if="loading && !data" class="ops-loading">טוען…</div>

    <!-- table -->
    <div v-else-if="data" class="ops-table-wrap">
      <table class="ops-table">
        <thead>
          <tr>
            <th>סוכן</th>
            <th>מחשב</th>
            <th>מחזור חודשי</th>
            <th>Mail Agent</th>
            <th>מסלקה</th>
            <th>הסכמים</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="a in rows" :key="a.id" :class="{ 'ops-row--alert': needsAttention(a) }">
            <td>
              <div class="ops-agent">
                <strong>{{ a.full_name || a.email }}</strong>
                <span class="ltr-number">{{ a.email }}</span>
                <span class="ops-muted">
                  נרשם {{ dmy(a.created_at) }} · {{ a.is_active ? 'מנוי פעיל' : 'לא פעיל' }}<template v-if="a.is_admin"> · אדמין</template>
                </span>
              </div>
            </td>
            <td>
              <span class="ops-dot" :class="a.worker.online ? 'on' : 'off'"></span>
              <strong class="ops-state">{{ a.worker.online ? 'מחובר' : 'מנותק' }}</strong>
              <div class="ops-muted">
                <span v-if="a.worker.hostname" class="ltr-number">{{ a.worker.hostname }}</span>
                <template v-if="!a.worker.online && a.worker.last_seen"> · {{ ago(a.worker.last_seen) }}</template>
                <template v-else-if="!a.worker.last_seen"> לא הותקן</template>
              </div>
              <div class="ops-muted">{{ a.worker.portals }} פורטלים</div>
            </td>
            <td>
              <span class="ops-badge" :class="'b-' + CYCLE[a.cycle.state].tone">{{ CYCLE[a.cycle.state].label }}</span>
              <div v-if="a.cycle.state === 'locked'" class="ops-muted">מחזור ראשון: <span class="ltr-number">{{ a.cycle.first_cycle }}</span></div>
              <div v-if="a.cycle.batch_status && a.cycle.succeeded != null" class="ops-muted">
                <span class="ltr-number">{{ a.cycle.succeeded }}</span> הצליחו · <span class="ltr-number">{{ a.cycle.failed }}</span> נכשלו
              </div>
              <div v-if="a.cycle.last_batch_at" class="ops-muted">
                ריצה אחרונה {{ ago(a.cycle.last_batch_at) }} · {{ BATCH[a.cycle.last_batch_status] || a.cycle.last_batch_status }}
                <template v-if="a.cycle.last_batch_trigger === 'admin'"> (ידנית)</template>
              </div>
            </td>
            <td>
              <span class="ops-badge" :class="'b-' + mailTone(a.mail_agent)">{{ mailLabel(a.mail_agent) }}</span>
              <div v-if="a.mail_agent.address" class="ops-muted ltr-number">{{ a.mail_agent.address }}</div>
              <div v-if="a.mail_agent.connected" class="ops-muted">
                <span class="ltr-number">{{ a.mail_agent.watched_senders }}</span> שולחים ·
                <span class="ltr-number">{{ a.mail_agent.mails_30d }}</span> מיילים ב-30 יום ·
                <span class="ltr-number">{{ a.mail_agent.sent_30d }}</span> נשלחו
              </div>
            </td>
            <td>
              <span class="ops-badge" :class="'b-' + MASLAKA[a.maslaka.association].tone">{{ MASLAKA[a.maslaka.association].label }}</span>
              <div v-if="a.maslaka.submitted_at || a.maslaka.expected_first_production" class="ops-muted">
                <template v-if="a.maslaka.submitted_at">הוגש {{ dmy(a.maslaka.submitted_at) }}</template>
                <template v-if="a.maslaka.approved_at"> · אושר {{ dmy(a.maslaka.approved_at) }}</template>
                <template v-if="a.maslaka.expected_first_production"> · <strong>פרודוקציה {{ dmy(a.maslaka.expected_first_production) }}</strong></template>
              </div>
              <div class="ops-muted">
                <span class="ltr-number">{{ a.maslaka.customers }}</span> לקוחות
                <template v-if="a.maslaka.last_holding_at"> · עודכן {{ ago(a.maslaka.last_holding_at) }}</template>
              </div>
              <div v-if="Object.keys(a.maslaka.inquiries).length" class="ops-muted">
                בקשות:
                <span v-for="(n, st) in a.maslaka.inquiries" :key="st" class="ops-mini">{{ INQ[st] || st }} <span class="ltr-number">{{ n }}</span></span>
              </div>
            </td>
            <td>
              <template v-if="Object.keys(a.agreements).length">
                <div v-for="(n, st) in a.agreements" :key="st" class="ops-mini-row">{{ AGR[st] || st }} <span class="ltr-number">{{ n }}</span></div>
              </template>
              <span v-else class="ops-muted">—</span>
            </td>
          </tr>
          <tr v-if="!rows.length"><td colspan="6" class="ops-empty">אין סוכנים שתואמים לסינון</td></tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import api from '../../api/client.js'

const CYCLE = {
  prelaunch: { label: 'לפני ההשקה', tone: 'muted' },
  locked: { label: 'לפני המחזור הראשון', tone: 'info' },
  no_portals: { label: 'אין פורטלים', tone: 'muted' },
  not_queued: { label: 'לא נשלח', tone: 'warn' },
  queued: { label: 'בתור', tone: 'live' },
  waiting_worker: { label: 'ממתין למחשב', tone: 'warn' },
  running: { label: 'רץ עכשיו', tone: 'live' },
  success: { label: 'הושלם', tone: 'ok' },
  partial: { label: 'הושלם חלקית', tone: 'warn' },
  failed: { label: 'נכשל', tone: 'bad' },
}
const MASLAKA = {
  not_started: { label: 'לא התחיל', tone: 'muted' },
  form_downloaded: { label: 'בחתימה', tone: 'info' },
  submitted: { label: 'הוגש — ממתין', tone: 'warn' },
  approved: { label: 'מאושר', tone: 'ok' },
  rejected: { label: 'נדחה', tone: 'bad' },
}
const BATCH = { pending: 'בתור', running: 'רץ', success: 'הצליחה', partial: 'חלקית', failed: 'נכשלה' }
const INQ = { pending: 'ממתינות', submitted: 'נשלחו', sent: 'נשלחו', acknowledged: 'התקבלו', answered: 'נענו', completed: 'הושלמו', failed: 'נכשלו', rejected: 'נדחו', expired: 'פגו' }
const AGR = { sent: 'נשלחו', replied: 'נענו', imported: 'נטענו', failed: 'נכשלו' }
const FILTERS = [
  { id: 'all', label: 'הכל' },
  { id: 'attention', label: 'דורש טיפול' },
  { id: 'offline', label: 'מחשב מנותק' },
  { id: 'nomail', label: 'בלי Mail Agent' },
  { id: 'maslaka', label: 'מסלקה פעילה' },
]

const data = ref(null)
const loading = ref(false)
const error = ref('')
const updatedAt = ref(null)
const filter = ref('all')
const q = ref('')
const nowTick = ref(Date.now())
let timer = null
let tick = null

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = (await api.get('/admin/operations')).data
    updatedAt.value = new Date().toISOString()
  } catch (e) {
    error.value = e.response?.data?.detail || 'טעינת לוח התפעול נכשלה'
  } finally {
    loading.value = false
  }
}
onMounted(() => {
  load()
  timer = setInterval(load, 30000)
  tick = setInterval(() => { nowTick.value = Date.now() }, 10000)
})
onBeforeUnmount(() => { clearInterval(timer); clearInterval(tick) })

function needsAttention(a) {
  return ['failed', 'waiting_worker', 'not_queued', 'partial'].includes(a.cycle.state)
    || a.maslaka.association === 'rejected'
    || (a.mail_agent.connected && !!a.mail_agent.last_error)
}
const PRED = {
  all: () => true,
  attention: needsAttention,
  offline: (a) => !a.worker.online,
  nomail: (a) => !a.mail_agent.connected,
  maslaka: (a) => ['submitted', 'approved'].includes(a.maslaka.association) || a.maslaka.customers > 0,
}
const countFor = (id) => (data.value?.agents || []).filter(PRED[id]).length
const rows = computed(() => {
  const needle = q.value.toLowerCase()
  return (data.value?.agents || [])
    .filter(PRED[filter.value])
    .filter((a) => !needle || (a.email || '').toLowerCase().includes(needle) || (a.full_name || '').toLowerCase().includes(needle))
})

const kpis = computed(() => {
  const s = data.value.summary
  return [
    { label: 'סוכנים', value: s.agents, tone: 'ink' },
    { label: 'מחשבים מחוברים', value: s.workers_online, tone: 'ok' },
    { label: 'מחזור הושלם', value: s.cycle_success, tone: 'ok' },
    { label: 'ממתינים / רצים', value: s.cycle_waiting, tone: 'warn' },
    { label: 'מחזור נכשל', value: s.cycle_failed, tone: 'bad' },
    { label: 'Mail Agent מחובר', value: s.mail_agent, tone: 'info' },
    { label: 'מסלקה מאושרת', value: s.maslaka_approved, tone: 'teal' },
    { label: 'לקוחות מהמסלקה', value: s.maslaka_customers, tone: 'teal' },
  ]
})

function mailTone(m) {
  if (!m.connected) return 'muted'
  if (m.last_error) return 'bad'
  return m.can_send ? 'ok' : 'warn'
}
function mailLabel(m) {
  if (!m.connected) return 'לא מחובר'
  if (m.last_error) return 'שגיאה'
  return m.can_send ? 'מחובר · שולח' : 'קריאה בלבד'
}

function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getDate()}.${d.getMonth() + 1} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}
function dmy(iso) {
  if (!iso) return ''
  const raw = /T/.test(iso) && !/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso + 'Z' : iso
  const d = new Date(raw)
  return `${d.getDate()}.${d.getMonth() + 1}.${String(d.getFullYear()).slice(2)}`
}
function ago(iso) {
  if (!iso) return ''
  const raw = /[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z'   // naive UTC from the API
  const s = Math.max(0, Math.round((nowTick.value - new Date(raw).getTime()) / 1000))
  if (s < 60) return 'לפני רגע'
  if (s < 3600) return `לפני ${Math.round(s / 60)} ד׳`
  if (s < 86400) return `לפני ${Math.round(s / 3600)} ש׳`
  return `לפני ${Math.round(s / 86400)} ימים`
}
</script>

<style scoped>
.ops { display: flex; flex-direction: column; gap: 16px; font-family: 'Heebo', sans-serif; }
.ops-head { display: flex; align-items: flex-end; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
.ops-title { margin: 0; font-size: 28px; font-weight: 900; letter-spacing: -0.02em; color: var(--text-primary, #181818); }
.ops-title-acc { color: #0A6664; }
.ops-sub { margin: 4px 0 0; font-size: 14px; color: var(--text-secondary, #706E6B); display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ops-chip { padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 800; }
.ops-chip--muted { background: #F1EFEC; color: #5C5A57; }
.ops-actions { display: flex; align-items: center; gap: 10px; }
.ops-updated { font-size: 12.5px; color: var(--text-secondary, #706E6B); }
.ops-refresh {
  display: inline-flex; align-items: center; gap: 7px; height: 38px; padding: 0 16px; border-radius: 10px;
  border: 1px solid var(--border-subtle, #E5E5E5); background: #fff; font-family: inherit; font-size: 13.5px; font-weight: 700; cursor: pointer;
}
.spin { animation: opsSpin 0.9s linear infinite; }
@keyframes opsSpin { to { transform: rotate(-360deg); } }
.ops-error { padding: 10px 14px; border-radius: 10px; background: rgba(234, 0, 30, 0.06); color: #B91C1C; font-weight: 600; }

.ops-kpis { display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); gap: 10px; }
@media (max-width: 1200px) { .ops-kpis { grid-template-columns: repeat(4, minmax(0, 1fr)); } }
.ops-kpi {
  display: flex; flex-direction: column; gap: 2px; padding: 14px 16px; border-radius: 14px;
  background: #fff; border: 1px solid var(--border-subtle, #E5E5E5); box-shadow: var(--shadow-sm);
  border-top: 3px solid var(--k, #181818);
}
.ops-kpi-n { font-size: 28px; font-weight: 900; line-height: 1.1; color: var(--k, #181818); }
.ops-kpi-l { font-size: 12.5px; font-weight: 700; color: var(--text-secondary, #706E6B); }
.ops-kpi--ink { --k: #181818; } .ops-kpi--ok { --k: #2E844A; } .ops-kpi--warn { --k: #8A6300; }
.ops-kpi--bad { --k: #C23934; } .ops-kpi--info { --k: #2F6C94; } .ops-kpi--teal { --k: #2C5F6B; }

.ops-filters { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ops-filter {
  display: inline-flex; align-items: center; gap: 7px; height: 34px; padding: 0 14px; border-radius: 999px;
  border: 1px solid var(--border-subtle, #E5E5E5); background: #fff; font-family: inherit; font-size: 13px; font-weight: 700; cursor: pointer; color: #3E3E3C;
}
.ops-filter.on { background: #181818; color: #fff; border-color: #181818; }
.ops-filter-n { font-size: 11.5px; padding: 1px 7px; border-radius: 999px; background: rgba(0, 0, 0, 0.07); }
.ops-filter.on .ops-filter-n { background: rgba(255, 255, 255, 0.2); }
.ops-search { margin-inline-start: auto; height: 34px; min-width: 220px; padding: 0 12px; border-radius: 10px; border: 1px solid var(--border-subtle, #E5E5E5); font-family: inherit; font-size: 13px; }

.ops-loading, .ops-empty { padding: 24px; text-align: center; color: var(--text-secondary, #706E6B); }
.ops-table-wrap { overflow-x: auto; border-radius: 14px; border: 1px solid var(--border-subtle, #E5E5E5); background: #fff; box-shadow: var(--shadow-sm); }
.ops-table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.ops-table th {
  position: sticky; top: 0; background: #FAFAF9; text-align: start; padding: 11px 14px;
  font-size: 12px; font-weight: 800; color: #5C5A57; border-bottom: 1px solid #EEECEA; white-space: nowrap;
}
.ops-table td { padding: 12px 14px; border-bottom: 1px solid #F3F1EF; vertical-align: top; }
.ops-table tbody tr:hover { background: #FCFBFA; }
.ops-row--alert { box-shadow: inset -3px 0 0 #C23934; }
.ops-agent { display: flex; flex-direction: column; gap: 2px; }
.ops-agent strong { font-weight: 800; color: var(--text-primary, #181818); }
.ops-agent .ltr-number { font-size: 12.5px; color: #3E3E3C; }
.ops-muted { font-size: 12px; color: var(--text-secondary, #706E6B); margin-top: 3px; }
.ops-state { font-size: 13px; }
.ops-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-inline-end: 6px; vertical-align: middle; }
.ops-dot.on { background: #2E844A; box-shadow: 0 0 0 3px rgba(46, 132, 74, 0.15); animation: opsPulse 2s ease-in-out infinite; }
.ops-dot.off { background: #C9C6C2; }
@keyframes opsPulse { 50% { box-shadow: 0 0 0 6px rgba(46, 132, 74, 0.05); } }
.ops-badge { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 800; white-space: nowrap; }
.b-ok { background: #EAF5EE; color: #2E844A; }
.b-warn { background: #FBF4DC; color: #8A6300; }
.b-bad { background: rgba(234, 0, 30, 0.08); color: #B91C1C; }
.b-live { background: #E2F1F1; color: #0A6664; }
.b-info { background: #E8F1F8; color: #2F6C94; }
.b-muted { background: #F1EFEC; color: #5C5A57; }
.ops-mini { margin-inline-start: 6px; }
.ops-mini-row { font-size: 12.5px; color: #3E3E3C; }
@media (prefers-reduced-motion: reduce) { .ops-dot.on, .spin { animation: none; } }
</style>
