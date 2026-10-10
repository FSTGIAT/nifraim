<template>
  <!-- Beside the charts: today's promises, dates to confirm (one tap), and Nifra's short read.
       Few words; a card with nothing to say is not rendered. -->
  <aside class="ip">
    <section v-if="r" class="ip-card ip-today" style="--hv: 47, 115, 196">
      <header class="ip-h">
        <div class="ip-tabs" role="tablist">
          <button type="button" role="tab" :aria-selected="view === 'today'" :class="{ on: view === 'today' }" @click="view = 'today'">היום</button>
          <button type="button" role="tab" :aria-selected="view === 'week'" :class="{ on: view === 'week' }" @click="view = 'week'">
            השבוע<span v-if="r.week && r.week.total" class="ip-tab-n ltr-number">{{ r.week.total }}</span>
          </button>
        </div>
        <button type="button" class="ip-play" :class="{ on: playing }" :title="view === 'week' ? 'השמע את השבוע הקרוב' : 'השמע את סיכום היום'" @click="play">
          <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M11 5L6 9H3v6h3l5 4V5z" /><path d="M15.5 8.5a5 5 0 010 7M18.5 5.5a9 9 0 010 13" /></svg>
          השמע
        </button>
      </header>
      <template v-if="view === 'today'">
      <p v-if="!todayRows.length" class="ip-empty">אין לך משימות להיום</p>
      <ul v-if="todayRows.length" class="ip-rows">
        <li v-for="t in todayRows" :key="t.call_id + ':' + t.task_index" class="ip-row" :class="{ 'is-late': t.overdue_days > 0, 'is-hot': hot(t.call_id) }"
            @mouseenter="store.hover([t.call_id])" @mouseleave="store.hover(null)">
          <span class="ip-time ltr-number">{{ t.overdue_days > 0 ? `+${t.overdue_days}` : (t.due_time || 'היום') }}</span>
          <button type="button" class="ip-text" @click="$emit('open-calls', { title: t.customer || 'שיחה', subtitle: t.text, callIds: [t.call_id] }, $event.currentTarget)">
            <b>{{ t.text }}</b><span v-if="t.customer"> · {{ t.customer }}</span>
          </button>
          <button type="button" class="ip-done" title="בוצע" @click="store.markDone(t.call_id, t.task_index)">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M5 12l5 5 9-10" /></svg>
          </button>
        </li>
      </ul>
      <button v-if="moreLate" type="button" class="ip-all ip-all--late" @click="$emit('open-tasks', 'late', $event.currentTarget)">
        ועוד {{ moreLate }} באיחור
        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
      </button>
      </template>
      <!-- the week ahead, day by day (same tasks the spoken week brief reads) -->
      <template v-else>
        <p v-if="!r.week || !r.week.days.length" class="ip-empty">אין משימות עם תאריך בשבוע הקרוב</p>
        <div v-for="d in (r.week ? r.week.days : [])" :key="d.date" class="ip-day">
          <p class="ip-day-h">{{ d.label }} <span class="ltr-number">{{ d.date.split('-').reverse().slice(0, 2).join('/') }}</span></p>
          <ul class="ip-rows">
            <li v-for="t in d.tasks" :key="t.call_id + ':' + t.task_index" class="ip-row" :class="{ 'is-hot': hot(t.call_id) }"
                @mouseenter="store.hover([t.call_id])" @mouseleave="store.hover(null)">
              <span class="ip-time ltr-number">{{ t.due_time || '' }}</span>
              <button type="button" class="ip-text" @click="$emit('open-calls', { title: t.customer || 'שיחה', subtitle: t.text, callIds: [t.call_id] }, $event.currentTarget)">
                <b>{{ t.text }}</b><span v-if="t.customer"> · {{ t.customer }}</span>
              </button>
              <button type="button" class="ip-done" title="בוצע" @click="store.markDone(t.call_id, t.task_index)">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M5 12l5 5 9-10" /></svg>
              </button>
            </li>
          </ul>
        </div>
      </template>
      <p v-if="nextTimed" class="ip-next">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
        <span class="ltr-number">{{ whenLabel(nextTimed) }}</span> <b>{{ nextTimed.text }}</b>
      </p>
    </section>

    <section v-if="r && r.proposals.length" class="ip-card" style="--hv: 111, 168, 44">
      <header class="ip-h"><h3>לקבוע מועד</h3></header>
      <ul class="ip-props">
        <li v-for="p in r.proposals" :key="p.call_id + ':' + p.task_index" class="ip-prop" :class="{ 'is-hot': hot(p.call_id) }"
            @mouseenter="store.hover([p.call_id])" @mouseleave="store.hover(null)">
          <p class="ip-prop-text"><b>{{ p.text }}</b><span v-if="p.customer"> · {{ p.customer }}</span></p>
          <div class="ip-pick">
            <input v-model="picks[key(p)].date" type="date" :aria-label="'תאריך ל' + p.text" />
            <input v-model="picks[key(p)].time" type="time" step="900" :aria-label="'שעה ל' + p.text" />
            <button type="button" class="ip-ok" :disabled="busy === key(p)" title="אישור" @click="confirm(p)">
              <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M5 12l5 5 9-10" /></svg>
            </button>
          </div>
        </li>
      </ul>
      <button v-if="r.brief.undated.length > r.proposals.length" type="button" class="ip-all"
              @click="$emit('open-tasks', 'undated', $event.currentTarget)">
        ועוד {{ r.brief.undated.length - r.proposals.length }} בלי תאריך
        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M15 6l-6 6 6 6" /></svg>
      </button>
    </section>

    <section v-if="narrative.length || status === 'computing'" class="ip-card ip-narr" style="--hv: 214, 51, 108">
      <header class="ip-h"><h3 dir="ltr">Nifra</h3></header>
      <ul v-if="narrative.length"><li v-for="(n, i) in narrative.slice(0, 3)" :key="i" :style="{ '--i': i }">{{ n }}</li></ul>
      <p v-else class="ip-thinking"><span></span>חושבת…</p>
    </section>
  </aside>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { useCallsInsightsStore } from '../../stores/callsInsights.js'
import { isSpeaking, speak, stopSpeaking } from '../../utils/voice.js'

defineProps({
  narrative: { type: Array, default: () => [] },
  status: { type: String, default: '' },
})
defineEmits(['open-calls', 'open-tasks'])
const store = useCallsInsightsStore()
const r = computed(() => store.reminders)

function hot(id) { return !!store.hoverCalls && store.hoverCalls.has(id) }
const todayRows = computed(() => {
  if (!r.value) return []
  const b = r.value.brief
  return [...b.due_today, ...b.overdue].slice(0, 4)
})
const moreLate = computed(() => (r.value ? Math.max(0, r.value.brief.due_today.length + r.value.brief.overdue.length - 4) : 0))
const nextTimed = computed(() => (r.value ? r.value.timed.find((t) => !t.claimed && !t.late_today) : null))
function whenLabel(t) {
  const today = r.value.today
  return `${t.due_date === today ? 'היום' : 'מחר'} ${t.due_time}`
}
// on demand: read today's brief aloud (the same sentences the morning reminder speaks)
const view = ref('today')   // היום | השבוע
const playing = ref(false)
async function play() {
  if (playing.value) { stopSpeaking(); playing.value = false; return }
  if (!r.value) return
  playing.value = true
  const lines = view.value === 'week' ? (r.value.week || {}).sentences_he : r.value.brief.sentences_he
  if (!(await speak(lines || []))) { playing.value = false; return }
  const t = setInterval(() => { if (!isSpeaking()) { playing.value = false; clearInterval(t) } }, 400)
}
const key = (p) => p.call_id + ':' + p.task_index
const picks = reactive({})
watch(() => (r.value ? r.value.proposals : []), (list) => {
  for (const p of list) if (!picks[key(p)]) picks[key(p)] = { date: p.date, time: p.time }
}, { immediate: true })
const busy = ref('')
async function confirm(p) {
  const k = key(p)
  busy.value = k
  try { await store.schedule(p.call_id, p.task_index, picks[k].date, picks[k].time) } finally { busy.value = '' }
}
</script>

<style scoped>
.ip { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.ip-card { background: #fff; border-radius: 14px; padding: 14px 16px; box-shadow: 0 1px 2px rgba(24, 24, 24, 0.04); transition: background 0.25s ease, box-shadow 0.25s ease; animation: ipIn 0.7s cubic-bezier(0.2, 0.8, 0.2, 1) both; }
.ip-card:nth-child(2) { animation-delay: 0.08s; }
.ip-card:nth-child(3) { animation-delay: 0.16s; }
/* each box hovers in its own colour (--hv rgb, CHART_PALETTE — no purple) */
.ip-card:hover { background: rgba(var(--hv, 44, 95, 107), 0.09); box-shadow: inset 0 0 0 1px rgba(var(--hv, 44, 95, 107), 0.32); }
.ip-h { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }
.ip-h h3 { margin: 0; font-size: 15px; font-weight: 900; }
.ip-tabs { display: flex; gap: 2px; padding: 3px; border-radius: 10px; background: rgba(24, 24, 24, 0.05); }
.ip-tabs button { display: inline-flex; align-items: center; gap: 5px; padding: 5px 12px; border: none; border-radius: 8px; background: none; font: inherit; font-size: 14px; font-weight: 800; color: var(--text-secondary, #5C5C5C); cursor: pointer; transition: background 0.3s ease, color 0.3s ease; }
.ip-tabs button.on { background: #fff; color: var(--text-primary, #181818); box-shadow: 0 1px 3px rgba(24, 24, 24, 0.1); }
.ip-tab-n { min-width: 18px; padding: 0 5px; border-radius: 999px; background: rgb(var(--hv)); color: #fff; font-size: 11px; line-height: 18px; text-align: center; }
.ip-empty { margin: 4px 8px 2px; font-size: 13px; color: var(--text-secondary, #5C5C5C); }
.ip-day + .ip-day { margin-top: 6px; }
.ip-day-h { margin: 6px 8px 2px; font-size: 12px; font-weight: 800; color: rgb(var(--hv)); }
.ip-day-h span { font-weight: 600; color: var(--text-secondary, #5C5C5C); margin-inline-start: 4px; }
.ip-play {
  margin-inline-start: auto; display: inline-flex; align-items: center; gap: 5px; padding: 5px 11px; border-radius: 999px;
  border: 1px solid var(--tab-insights-soft); background: #fff; color: var(--tab-insights-ink); font: inherit; font-size: 12px; font-weight: 800; cursor: pointer;
  transition: background 0.2s, color 0.2s;
}
.ip-play:hover, .ip-play.on { background: var(--tab-insights); color: #fff; }
.ip-sub { font-size: 12px; color: var(--text-secondary, #5C5C5C); }
.ip-today .ip-h { margin-bottom: 6px; }
.ip-rows { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 2px; }
.ip-row { display: flex; align-items: center; gap: 10px; padding: 6px 8px; border-radius: 10px; transition: background 0.18s ease; }
.ip-row.is-hot, .ip-row:hover { background: var(--tab-insights-wash); }
.ip-time { min-width: 46px; font-size: 12px; font-weight: 800; color: var(--tab-insights-ink); }
.ip-row.is-late .ip-time { color: var(--red); }
.ip-text { flex: 1; min-width: 0; border: none; background: none; padding: 0; font: inherit; font-size: 13px; text-align: start; cursor: pointer; color: inherit; }
.ip-text b { font-weight: 700; }
.ip-text span { color: var(--text-secondary, #5C5C5C); }
.ip-done { width: 26px; height: 26px; border-radius: 8px; border: 1px solid var(--border-subtle, #E5E5E5); background: #fff; display: grid; place-items: center; cursor: pointer; color: var(--text-secondary, #5C5C5C); opacity: 0; transition: opacity 0.18s; }
.ip-row:hover .ip-done, .ip-done:focus-visible { opacity: 1; }
.ip-done:hover { color: var(--tab-insights-ink); border-color: var(--tab-insights); }
.ip-next { display: flex; align-items: center; gap: 6px; margin: 8px 0 0; padding-top: 8px; border-top: 1px solid var(--border-subtle, #E5E5E5); font-size: 12px; color: var(--text-secondary, #5C5C5C); }
.ip-next b { color: var(--text-primary, #181818); }
.ip-next svg { color: var(--tab-insights); flex-shrink: 0; }

.ip-props { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.ip-prop { padding: 8px 10px; border-radius: 10px; border: 1px solid var(--border-subtle, #E5E5E5); transition: border-color 0.18s, background 0.18s; }
.ip-prop.is-hot, .ip-prop:hover { border-color: var(--tab-insights-soft); background: var(--tab-insights-wash); }
.ip-prop-text { margin: 0; font-size: 13px; }
.ip-prop-text span { color: var(--text-secondary, #5C5C5C); }
.ip-prop-text { margin-bottom: 6px !important; }
.ip-pick { display: flex; gap: 6px; align-items: center; }
.ip-pick input { min-width: 0; flex: 1; padding: 5px 8px; border-radius: 8px; border: 1px solid var(--border-subtle, #E5E5E5); font: inherit; font-size: 12px; background: #fff; }
.ip-pick input[type='time'] { flex: 0 0 104px; }
.ip-ok { display: grid; place-items: center; width: 34px; height: 30px; padding: 0; border-radius: 8px; border: none; background: var(--tab-insights); color: #fff; font: inherit; font-size: 12px; font-weight: 800; cursor: pointer; box-shadow: 0 4px 10px rgba(44, 95, 107, 0.22); }
.ip-ok:disabled { opacity: 0.5; cursor: default; }

.ip-narr h3 { color: var(--tab-insights-ink); }
.ip-narr ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 8px; font-size: 13px; line-height: 1.5; }
.ip-narr li { padding-inline-start: 12px; border-inline-start: 2px solid var(--tab-insights-soft); }
.ip-all { display: inline-flex; align-items: center; gap: 4px; margin-top: 8px; padding: 4px 8px; border: none; background: none; font: inherit; font-size: 12px; font-weight: 800; color: var(--tab-insights-ink); cursor: pointer; border-radius: 8px; }
.ip-all:hover { background: rgba(var(--hv), 0.14); }
.ip-all--late { color: var(--red); }
.ip-more { margin: 4px 8px 0; font-size: 12px; color: var(--red); font-weight: 700; }
.ip-narr li { animation: ipIn 0.6s ease both; animation-delay: calc(0.3s + var(--i) * 0.12s); }
.ip-thinking { display: flex; align-items: center; gap: 8px; margin: 12px 0 0; font-size: 12px; color: var(--text-secondary, #5C5C5C); }
.ip-thinking span { width: 8px; height: 8px; border-radius: 50%; background: var(--tab-insights); animation: ipPulse 1.6s ease-in-out infinite; }
@keyframes ipIn { from { opacity: 0; transform: translateY(8px); } }
@keyframes ipPulse { 50% { opacity: 0.25; } }
@media (hover: none) { .ip-done { opacity: 1; } }
@media (prefers-reduced-motion: reduce) { .ip-card, .ip-narr li, .ip-thinking span { animation: none; } }
</style>
