<template>
  <!-- Nifra Insights — what the agent's calls add up to: products first (bars), today's promises,
       Nifra's proposed dates and an analyst read. Grows out of its circle and folds back into it. -->
  <Teleport to="body">
    <Transition name="nis" @enter="onEnter">
      <div v-if="open" class="nis-overlay" @click.self="close">
        <div ref="cardEl" class="nis" role="dialog" aria-label="Nifra Insights">
          <header class="nis-head">
            <div class="nis-title">
              <h2 dir="ltr">Nifra <b>Insights</b></h2>
              <p>מה עולה בשיחות</p>
            </div>
            <div class="nis-period" role="tablist" aria-label="תקופה">
              <span class="nis-pill" :style="pillStyle" aria-hidden="true"></span>
              <button v-for="(p, i) in PERIODS" :key="p.days" :ref="(el) => (periodEls[i] = el)" type="button" role="tab"
                      :aria-selected="days === p.days" :class="{ on: days === p.days }" @click="setDays(p.days)">{{ p.label }}</button>
            </div>
            <button type="button" class="nis-voice" :class="{ on: store.voiceOn }" :aria-pressed="store.voiceOn"
                    :title="store.voiceOn ? 'תזכורות קוליות פעילות' : 'השמע תזכורות'" @click="toggleVoice">
              <svg v-if="store.voiceOn" viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M11 5L6 9H3v6h3l5 4V5z" /><path d="M15.5 8.5a5 5 0 010 7M18.5 5.5a9 9 0 010 13" /></svg>
              <svg v-else viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M11 5L6 9H3v6h3l5 4V5z" /><path d="M22 9l-6 6M16 9l6 6" /></svg>
              <span>{{ store.voiceOn ? 'קול' : 'קול כבוי' }}</span>
            </button>
            <button type="button" class="nis-x" aria-label="סגירה" @click="close">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18" /></svg>
            </button>
          </header>

          <main class="nis-body">
            <div v-if="!board && store.loadingBoard" class="nis-skel" aria-label="טוען">
              <span v-for="i in 5" :key="i" :style="{ '--w': 100 - i * 14 + '%', '--i': i }"></span>
            </div>
            <p v-else-if="store.error && !board" class="nis-msg">{{ store.error }}</p>
            <div v-else-if="board && !board.products.length" class="nis-empty">
              <h3>{{ days ? 'אין שיחות בתקופה הזו' : 'עוד אין שיחות מסוכמות' }}</h3>
              <p>{{ days ? 'נסו טווח ארוך יותר.' : 'כל שיחה שתוקלט — בטלפון או באתר — תסוכם, ותופיע כאן לפי המוצר שדיברתם עליו.' }}</p>
            </div>
            <div v-else-if="board" class="nis-grid">
              <div class="nis-main">
                <div ref="kpisEl" class="nis-kpis" @mouseleave="kpiGlide.on = false">
                  <span class="nis-kpi-glide" :class="{ on: kpiGlide.on }" :style="kpiGlideStyle" aria-hidden="true"></span>
                  <button type="button" @mouseenter="glideTo" @click="openCalls({ title: 'כל השיחות', callIds: Object.keys(board.calls) }, $event.currentTarget)"><span>שיחות</span><b class="ltr-number">{{ st.calls }}</b></button>
                  <button type="button" @mouseenter="glideTo" @click="openCustomers($event.currentTarget)"><span>לקוחות</span><b class="ltr-number">{{ st.customers }}</b></button>
                  <button type="button" @mouseenter="glideTo" @click="openTasks('open', $event.currentTarget)"><span>משימות</span><b class="ltr-number">{{ st.agent_open }}</b></button>
                  <button v-if="st.overdue" type="button" @mouseenter="glideTo" class="is-late" @click="openTasks('late', $event.currentTarget)"><span>באיחור</span><b class="ltr-number">{{ st.overdue }}</b></button>
                </div>
                <section class="nis-card" style="--hv: 44, 95, 107">
                  <h3>על מה הלקוחות שלי מדברים <span v-if="board.themes_status === 'computing'" class="nis-chip">מסדרת…</span></h3>
                  <LineBars :items="productItems" :limit="5" :hot-key="store.hoverTheme" :hot-calls="store.hoverTheme ? null : store.hoverCalls"
                            @hover="(it) => store.hover(it && it.callIds, it && it.key)"
                            @select="(it, el) => openCalls({ title: it.label, callIds: it.callIds, customers: it.customers }, el)" />
                </section>
                <div class="nis-pair">
                  <section v-if="moodItems.length" class="nis-card" style="--hv: 15, 163, 155">
                    <h3>אווירה</h3>
                    <LineDonut :items="moodItems" @select="(a, el) => openCalls({ title: a.label, callIds: a.callIds }, el)" />
                  </section>
                  <section v-if="insurerItems.length" class="nis-card" style="--hv: 78, 157, 208">
                    <h3>חברות</h3>
                    <LineBars :items="insurerItems" :limit="4"
                              @select="(it, el) => openCalls({ title: it.label, callIds: it.callIds }, el)" />
                  </section>
                </div>
                <section v-if="weeks.length > 1" class="nis-card" style="--hv: 201, 162, 39">
                  <h3>שיחות בשבוע</h3>
                  <LineTrend :points="weeks" />
                </section>
              </div>
              <InsightsPanel :narrative="board.narrative" :status="board.themes_status" @open-calls="openCalls" />
            </div>
          </main>
        </div>
      </div>
    </Transition>

    <DataModal :open="!!drill" :origin="drillOrigin" :title="drill ? drill.title : ''" :badge="drill ? drill.badge : null"
               :subtitle="drill ? drill.subtitle : ''" accent="var(--tab-insights)" size="sm" :layer="1035" @close="drill = null">
      <template v-if="drill && drill.kind === 'customers'">
        <ul class="nis-calls">
          <li v-for="c in drill.customers" :key="c.key">
            <button type="button" @click="openCalls({ title: c.name, callIds: c.callIds, customers: 1 }, $event.currentTarget)">
              <span class="nis-call-top"><b>{{ c.name }}</b><span class="ltr-number">{{ c.callIds.length }} שיחות</span></span>
              <span v-if="c.insurers.length" class="nis-call-who">{{ c.insurers.join(' · ') }}</span>
              <span v-if="c.open" class="nis-call-tldr">{{ c.open }} משימות פתוחות<b v-if="c.late" class="nis-late"> · {{ c.late }} באיחור</b></span>
              <svg class="nis-call-chev" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
            </button>
          </li>
        </ul>
      </template>
      <template v-else-if="drill && drill.kind === 'tasks'">
        <ul class="nis-tasks">
          <li v-for="t in drill.tasks" :key="t.call_id + ':' + t.task_index" :class="{ 'is-late': t.overdue_days > 0 }">
            <button type="button" class="nis-task-main" @click="openCalls({ title: t.customer || 'שיחה', subtitle: t.text, callIds: [t.call_id], customers: 1 }, $event.currentTarget)">
              <b>{{ t.text }}</b>
              <span>{{ t.customer }}<template v-if="t.due_date"> · <span class="ltr-number">{{ t.overdue_days > 0 ? `+${t.overdue_days} ימים` : t.due_date.split('-').reverse().slice(0, 2).join('/') }}</span></template></span>
            </button>
            <button type="button" class="nis-task-done" title="בוצע" @click="doneTask(t)">
              <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M5 12l5 5 9-10" /></svg>
            </button>
          </li>
        </ul>
      </template>
      <template v-else-if="drill">
        <div class="nis-strip">
          <div><span>שיחות</span><b class="ltr-number">{{ drill.calls.length }}</b></div>
          <div v-if="drill.customers > 1"><span>לקוחות</span><b class="ltr-number">{{ drill.customers }}</b></div>
          <div v-if="drill.mood"><span>אווירה</span><b>{{ drill.mood }}</b></div>
        </div>
        <ul class="nis-calls">
          <li v-for="c in drill.calls" :key="c.id">
            <button type="button" @click="openCall(c.id)">
              <span class="nis-call-top"><b>{{ c.title || 'שיחה' }}</b><span class="ltr-number">{{ shortDate(c.when) }}</span></span>
              <span v-if="c.customer" class="nis-call-who">{{ c.customer }}</span>
              <span v-if="c.tldr" class="nis-call-tldr">{{ c.tldr }}</span>
              <svg class="nis-call-chev" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
            </button>
          </li>
        </ul>
      </template>
    </DataModal>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useOriginMorph } from '../../composables/useOriginMorph.js'
import { useCallsInsightsStore } from '../../stores/callsInsights.js'
import { useCallsStore } from '../../stores/calls.js'
import { askNotifyPermission, speak } from '../../utils/voice.js'
import DataModal from '../workspace/DataModal.vue'
import LineBars from './LineBars.vue'
import LineDonut from './LineDonut.vue'
import LineTrend from './LineTrend.vue'
import InsightsPanel from './InsightsPanel.vue'

const props = defineProps({ open: { type: Boolean, default: false }, originEl: { type: null, default: null } })
const emit = defineEmits(['update:open'])
const store = useCallsInsightsStore()
const callsStore = useCallsStore()
const SENT_HE = { positive: 'חיובית', neutral: 'ניטרלית', negative: 'שלילית', mixed: 'מעורבת' }
const board = computed(() => store.board)
const st = computed(() => (board.value && board.value.stats) || {})
const UNKNOWN = 'לקוח לא מזוהה'   // services/calls/insights_board.UNKNOWN_CUSTOMER — not counted as a customer
const productItems = computed(() => (board.value ? board.value.products : []).map((p) => ({
  key: p.theme, label: p.theme, value: p.calls, callIds: p.call_ids,
  customers: p.customers.filter((c) => c.name !== UNKNOWN).length,
})))
const SENT_ORDER = ['positive', 'neutral', 'mixed', 'negative']
const moodItems = computed(() => {
  const calls = Object.entries((board.value && board.value.calls) || {})
  return SENT_ORDER.map((k) => {
    const ids = calls.filter(([, c]) => c.sentiment === k).map(([id]) => id)
    return { key: k, label: SENT_HE[k], value: ids.length, callIds: ids }
  }).filter((x) => x.value)
})
const insurerItems = computed(() => (st.value.insurers || []).map((x) => ({ key: x.name, label: x.name, value: x.calls, callIds: x.call_ids })))
// calls per week, the last 8 weeks (Sunday-start, Israeli week)
const weeks = computed(() => {
  const calls = Object.values((board.value && board.value.calls) || {})
  if (!calls.length) return []
  const start = (d) => { const x = new Date(d + 'T12:00:00'); x.setDate(x.getDate() - x.getDay()); return x.toISOString().slice(0, 10) }
  const now = new Date(); now.setHours(12, 0, 0, 0); now.setDate(now.getDate() - now.getDay())
  const out = []
  for (let i = 7; i >= 0; i--) {
    const d = new Date(now); d.setDate(now.getDate() - i * 7)
    out.push({ key: d.toISOString().slice(0, 10), label: `${d.getDate()}/${d.getMonth() + 1}`, value: 0 })
  }
  for (const c of calls) {
    const w = out.find((x) => x.key === start(c.when))
    if (w) w.value += 1
  }
  const first = out.findIndex((x) => x.value > 0)
  return first < 0 ? [] : out.slice(Math.min(first, out.length - 2))
})

const PERIODS = [{ days: 0, label: 'הכל' }, { days: 30, label: '30 יום' }, { days: 7, label: 'השבוע' }]
const days = ref(store.boardDays)
const periodEls = []
const pill = ref({ left: 0, top: 0, width: 0, height: 0 })
const pillStyle = computed(() => ({ transform: `translate(${pill.value.left}px, ${pill.value.top}px)`,
  width: pill.value.width + 'px', height: pill.value.height + 'px' }))
function placePill() {
  const el = periodEls[PERIODS.findIndex((p) => p.days === days.value)]
  if (el) pill.value = { left: el.offsetLeft, top: el.offsetTop, width: el.offsetWidth, height: el.offsetHeight }
}
function setDays(d) { days.value = d; nextTick(placePill); store.loadBoard(d) }
onMounted(() => window.addEventListener('resize', placePill))
onBeforeUnmount(() => { window.removeEventListener('resize', placePill); document.body.classList.remove('mam-open'); clearTimeout(pollT) })
watch(() => props.open, (v) => document.body.classList.toggle('mam-open', !!v))

// the theme pass runs in the background the first time — re-read the board until it lands
let pollT = 0
let polls = 0
watch(() => board.value && board.value.themes_status, (st) => {
  clearTimeout(pollT)
  if (st === 'computing' && props.open && polls < 20) {
    polls += 1
    pollT = setTimeout(() => store.loadBoard(days.value), 4000)
  }
})

const morph = useOriginMorph()
const cardEl = ref(null)
function onEnter() {
  morph.remember(props.originEl)
  morph.grow(cardEl.value)
  nextTick(placePill)
  setTimeout(placePill, 900)
  polls = 0
  store.loadBoard(days.value)
  store.loadReminders()
}
async function close() {
  store.hover(null)
  if (morph.hasOrigin()) await morph.shrink(cardEl.value)
  emit('update:open', false)
}

async function toggleVoice() {
  const on = !store.voiceOn
  store.setVoice(on)
  if (on) {
    await askNotifyPermission()
    speak('התזכורות מהשיחות יושמעו כאן.')
  }
}

// ── drill: the calls behind a bar / customer / task ──
const drill = ref(null)
const drillOrigin = ref(null)
function openCalls({ title, subtitle, callIds, customers }, el) {
  const map = (board.value && board.value.calls) || {}
  const calls = [...new Set(callIds)].map((id) => ({ id, ...(map[id] || {}) })).sort((a, b) => (b.when || '').localeCompare(a.when || ''))
  const moods = calls.map((c) => c.sentiment).filter(Boolean)
  const top = moods.length ? Object.entries(moods.reduce((m, k) => ({ ...m, [k]: (m[k] || 0) + 1 }), {})).sort((a, b) => b[1] - a[1])[0][0] : ''
  drillOrigin.value = el || null
  // the bar's own customer count when it has one — the drill and the row it came from must agree
  const n = customers ?? new Set(calls.map((c) => c.customer).filter(Boolean)).size
  store.hover(null)   // the row under the pointer is covered by the drill — no stuck highlight
  drill.value = { kind: 'calls', title, subtitle, calls, badge: calls.length, customers: n, mood: SENT_HE[top] || '' }
}
// the hover highlight GLIDES from one KPI to the next (a pill that follows the pointer)
const kpisEl = ref(null)
const kpiGlide = reactive({ on: false, x: 0, y: 0, w: 0, h: 0 })
const kpiGlideStyle = computed(() => ({ transform: `translate(${kpiGlide.x}px, ${kpiGlide.y}px)`, width: kpiGlide.w + 'px', height: kpiGlide.h + 'px' }))
function glideTo(e) {
  const el = e.currentTarget
  Object.assign(kpiGlide, { on: true, x: el.offsetLeft, y: el.offsetTop, w: el.offsetWidth, h: el.offsetHeight })
}
// ── KPI drills: customers / open tasks / overdue — built from the same board rows the charts use ──
function allCustomers() {
  const m = new Map()
  for (const p of (board.value && board.value.products) || []) {
    for (const c of p.customers) {
      if (c.name === UNKNOWN) continue
      const x = m.get(c.key) || { key: c.key, name: c.name, callIds: new Set(), insurers: new Set(), tasks: new Map() }
      c.call_ids.forEach((id) => x.callIds.add(id))
      c.insurers.forEach((i) => x.insurers.add(i))
      c.tasks.forEach((t) => x.tasks.set(t.call_id + ':' + t.task_index, { ...t, customer: c.name }))
      m.set(c.key, x)
    }
  }
  return [...m.values()].map((x) => {
    const tasks = [...x.tasks.values()]
    return { key: x.key, name: x.name, callIds: [...x.callIds], insurers: [...x.insurers], tasks,
             open: tasks.length, late: tasks.filter((t) => t.overdue_days > 0).length }
  })
}
function openCustomers(el) {
  const list = allCustomers().sort((a, b) => b.late - a.late || b.callIds.length - a.callIds.length)
  store.hover(null)
  drillOrigin.value = el
  drill.value = { kind: 'customers', title: 'לקוחות', badge: list.length, customers: list }
}
function allTasks() {
  const m = new Map()
  for (const p of (board.value && board.value.products) || []) {
    for (const c of p.customers) for (const t of c.tasks) m.set(t.call_id + ':' + t.task_index, { ...t, customer: c.name === UNKNOWN ? '' : c.name })
  }
  return [...m.values()].sort((a, b) => b.overdue_days - a.overdue_days || (a.due_date || '9').localeCompare(b.due_date || '9'))
}
function openTasks(which, el) {
  const list = allTasks().filter((t) => which !== 'late' || t.overdue_days > 0)
  store.hover(null)
  drillOrigin.value = el
  drill.value = { kind: 'tasks', which, title: which === 'late' ? 'באיחור' : 'משימות', badge: list.length, tasks: list }
}
async function doneTask(t) {
  await store.markDone(t.call_id, t.task_index)
  if (drill.value && drill.value.kind === 'tasks') {
    const list = allTasks().filter((x) => drill.value.which !== 'late' || x.overdue_days > 0)
    drill.value = { ...drill.value, badge: list.length, tasks: list }
  }
}
async function openCall(id) {
  drill.value = null
  await close()
  callsStore.requestOpenCall(id, 'insights')
}
function shortDate(iso) {
  if (!iso) return ''
  const [, m, d] = iso.split('-')
  return `${+d}/${+m}`
}
</script>

<style scoped>
.nis-overlay {
  position: fixed; inset: 0; z-index: 1010; display: grid; place-items: center; padding: 16px;
  background: rgba(16, 28, 32, 0.34); backdrop-filter: blur(6px);
}
.nis {
  position: relative; width: min(1180px, 100%); height: min(860px, calc(100vh - 32px));
  display: flex; flex-direction: column; overflow: hidden; border-radius: 28px;
  /* its own light surface — a window, not the page (--app-canvas is the agent's page colour) */
  background: #F2F4F4; box-shadow: 0 40px 100px rgba(16, 32, 36, 0.3);
  font-family: 'Heebo', sans-serif; color: var(--text-primary, #181818);
}
.nis-head { display: flex; align-items: center; gap: 12px; padding: 18px 24px 10px; flex-wrap: wrap; }
.nis-title { margin-inline-end: auto; }
.nis-title h2 { margin: 0; font-size: 26px; font-weight: 900; letter-spacing: -0.02em; text-align: right; }
.nis-title h2 b { color: var(--tab-insights-ink); }
.nis-title p { margin: 2px 0 0; font-size: 13px; color: var(--text-secondary, #5C5C5C); }
.nis-period { position: relative; display: flex; gap: 2px; padding: 4px; border-radius: 12px; background: rgba(255, 255, 255, 0.75); }
.nis-period button { position: relative; z-index: 1; border: none; background: none; padding: 7px 14px; border-radius: 9px; font: inherit; font-size: 13px; font-weight: 700; cursor: pointer; color: var(--text-secondary, #5C5C5C); transition: color 0.4s; }
.nis-period button.on { color: #fff; }
.nis-pill { position: absolute; top: 0; left: 0; border-radius: 9px; background: var(--tab-insights); transition: transform 0.75s cubic-bezier(0.2, 0.8, 0.2, 1), width 0.75s cubic-bezier(0.2, 0.8, 0.2, 1); }
.nis-voice {
  display: inline-flex; align-items: center; gap: 6px; height: 36px; padding: 0 12px; border-radius: 10px; border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.75); font: inherit; font-size: 13px; font-weight: 700; cursor: pointer; color: var(--text-secondary, #5C5C5C);
  transition: background 0.2s, color 0.2s, border-color 0.2s;
}
.nis-voice.on { color: var(--tab-insights-ink); border-color: var(--tab-insights-soft); background: #fff; }
.nis-voice:hover { background: #fff; }
.nis-x { width: 36px; height: 36px; border-radius: 10px; border: none; cursor: pointer; display: grid; place-items: center; background: rgba(255, 255, 255, 0.75); color: var(--text-secondary, #5C5C5C); }
.nis-x:hover { background: #fff; color: var(--text-primary, #181818); }
.nis-body { flex: 1; min-height: 0; overflow-y: auto; padding: 4px 24px 20px; }
.nis-grid { display: grid; grid-template-columns: minmax(0, 1.6fr) minmax(290px, 1fr); gap: 12px; align-items: start; }
.nis-main { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.nis-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(90px, 1fr)); gap: 8px; padding: 8px; border-radius: 14px; background: #fff; }
.nis-kpis > button {
  display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 8px 12px; border: none; border-radius: 10px;
  background: none; font: inherit; color: inherit; cursor: pointer; text-align: start; transition: background 0.2s ease, transform 0.2s ease;
}
.nis-kpis { position: relative; }
.nis-kpis > button { position: relative; z-index: 1; }
.nis-kpi-glide {
  position: absolute; top: 0; left: 0; z-index: 0; border-radius: 10px; background: var(--tab-insights-wash);
  box-shadow: inset 0 0 0 1px rgba(44, 95, 107, 0.12); opacity: 0; pointer-events: none;
  transition: transform 0.45s cubic-bezier(0.2, 0.8, 0.2, 1), width 0.45s cubic-bezier(0.2, 0.8, 0.2, 1), opacity 0.25s ease;
}
.nis-kpi-glide.on { opacity: 1; }
.nis-kpis span { font-size: 12px; color: var(--text-secondary, #5C5C5C); }
.nis-kpis b { font-size: 24px; font-weight: 800; }
.nis-kpis > button:first-child b { color: var(--tab-insights-ink); }
.nis-kpis .is-late b { color: var(--red); }
.nis-card { background: #fff; border-radius: 14px; padding: 14px 16px; transition: background 0.25s ease, box-shadow 0.25s ease; animation: nisIn 0.7s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
.nis-card h3 { display: flex; align-items: center; gap: 8px; margin: 0 0 8px; font-size: 14px; font-weight: 900; }
/* hover fills the box — the agent sees which block they're in */
/* every box fills with ITS OWN colour (CHART_PALETTE, no purple) — --hv is the box's rgb */
.nis-card:hover { background: rgba(var(--hv, 44, 95, 107), 0.09); box-shadow: inset 0 0 0 1px rgba(var(--hv, 44, 95, 107), 0.32); }
.nis-tasks { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.nis-tasks li { display: flex; align-items: center; gap: 8px; padding: 4px 4px 4px 8px; border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 12px; background: #fff; transition: background 0.2s, border-color 0.2s; }
.nis-tasks li:hover { background: #F4F8F8; border-color: var(--tab-insights-soft); }
.nis-tasks li.is-late { border-inline-start: 3px solid var(--red); }
.nis-task-main { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 8px 10px; border: none; background: none; font: inherit; text-align: start; cursor: pointer; color: inherit; }
.nis-task-main b { font-size: 14px; }
.nis-task-main > span { font-size: 12px; color: var(--text-secondary, #5C5C5C); }
.nis-tasks li.is-late .nis-task-main .ltr-number { color: var(--red); font-weight: 700; }
.nis-task-done { width: 32px; height: 32px; flex-shrink: 0; display: grid; place-items: center; border-radius: 9px; border: 1px solid var(--border-subtle, #E5E5E5); background: #fff; cursor: pointer; color: var(--text-secondary, #5C5C5C); }
.nis-task-done:hover { color: #fff; background: var(--tab-insights); border-color: var(--tab-insights); }
.nis-late { color: var(--red); }
.nis-pair { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; }
.nis-chip { font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 999px; background: var(--tab-insights-wash); color: var(--tab-insights-ink); animation: nisPulse 1.8s ease-in-out infinite; }
.nis-skel { display: flex; flex-direction: column; gap: 8px; padding-top: 30px; }
.nis-skel span { height: 48px; width: var(--w); border-radius: 14px; background: linear-gradient(90deg, #fff 0%, #E8EEEF 50%, #fff 100%); background-size: 200% 100%; animation: nisShimmer 1.6s ease-in-out infinite; animation-delay: calc(var(--i) * 0.1s); }
.nis-msg { text-align: center; padding: 60px 0; color: var(--text-secondary, #5C5C5C); }
.nis-empty { max-width: 460px; margin: 80px auto; text-align: center; }
.nis-empty h3 { margin: 0 0 6px; font-size: 20px; font-weight: 900; }
.nis-empty p { margin: 0; color: var(--text-secondary, #5C5C5C); line-height: 1.6; }

.nis-strip { display: flex; gap: 0; border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 12px; margin-bottom: 12px; overflow: hidden; }
.nis-strip > div { flex: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 10px 14px; }
.nis-strip > div + div { border-inline-start: 1px solid var(--border-subtle, #E5E5E5); }
.nis-strip span { font-size: 12px; color: var(--text-secondary, #5C5C5C); }
.nis-strip b { font-size: 21px; font-weight: 800; }
.nis-strip > div:first-child b { color: var(--tab-insights-ink); }
.nis-calls { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.nis-calls button {
  position: relative; width: 100%; display: flex; flex-direction: column; align-items: flex-start; gap: 3px; padding: 10px 14px 10px 34px;
  border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 12px; background: #fff; font: inherit; text-align: start; cursor: pointer; color: inherit;
  transition: border-color 0.18s, transform 0.18s;
}
.nis-calls button:hover { border-color: var(--tab-insights); transform: translateY(-1px); }
.nis-call-top { display: flex; width: 100%; justify-content: space-between; gap: 10px; font-size: 14px; }
.nis-call-top span { font-size: 12px; color: var(--text-secondary, #5C5C5C); }
.nis-call-who { font-size: 12px; font-weight: 700; color: var(--tab-insights-ink); }
.nis-call-tldr { font-size: 13px; color: var(--text-secondary, #5C5C5C); }
.nis-call-chev { position: absolute; left: 12px; top: 50%; transform: translateY(-50%); color: var(--text-secondary, #5C5C5C); }
.nis-enter-active, .nis-leave-active { transition: opacity 0.3s ease; }
.nis-enter-from, .nis-leave-to { opacity: 0; }
@keyframes nisIn { from { opacity: 0; transform: translateY(8px); } }
@keyframes nisShimmer { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }
@keyframes nisPulse { 50% { opacity: 0.55; } }
@media (max-width: 900px) { .nis-grid { grid-template-columns: 1fr; } }
@media (max-width: 720px) {
  .nis { border-radius: 20px; height: calc(100vh - 24px); }
  .nis-head, .nis-body { padding-inline: 14px; }
  .nis-voice span { display: none; }
  .nis-title h2 { font-size: 22px; }
  .nis-kpis { grid-template-columns: repeat(2, 1fr); }
}
@media (prefers-reduced-motion: reduce) { .nis-pill { transition: none; } .nis-skel span, .nis-chip { animation: none; } }
</style>
