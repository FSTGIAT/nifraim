<template>
  <div class="cr" :class="{ 'cr--reveal': reveal }">
    <!-- One call, calm and editorial: ink on white, one accent used sparingly.
         Read top-down: hero → the call as a timeline (numbered moments) →
         the summary → the action block (next step, tasks, context facts).
         The transcript lives in its own side sheet, opened from the hero or
         from a timeline moment. Empty groups render nothing. -->
    <header class="cr-hero cr-in" style="--i: 0">
      <div class="cr-hero-top">
        <h2 class="cr-title">{{ call.title || 'סיכום השיחה' }}</h2>
        <div class="cr-actions">
          <button v-if="hasTranscript" type="button" class="cr-act" aria-haspopup="dialog" @click="openSheet()">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5M9 13h6M9 17h4" />
            </svg>
            תמליל<span v-if="segments.length" class="cr-act-n ltr-number">{{ segments.length }}</span>
          </button>
          <button type="button" class="cr-act cr-act--quiet" :aria-expanded="personalOpen" @click="personalOpen = !personalOpen">אישית</button>
          <button type="button" class="cr-act cr-act--quiet" @click="$emit('delete')">מחיקה</button>
        </div>
      </div>
      <!-- a personal call (family, friends): hide it — and maybe never upload this number again -->
      <div v-if="personalOpen" class="cr-personal" role="group" aria-label="שיחה אישית">
        <span>שיחה אישית?</span>
        <button type="button" class="cr-act" @click="$emit('personal', false)">הסתרת השיחה</button>
        <button v-if="call.phone_number" type="button" class="cr-act" @click="$emit('personal', true)">
          הסתרה ולא להעלות את <span class="ltr-number">{{ call.phone_number }}</span> שוב
        </button>
      </div>
      <p class="cr-meta">
        <span v-if="phoneCall" class="cr-src">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z" />
          </svg>
          {{ phoneCall }}<span v-if="call.phone_number" class="ltr-number">{{ call.phone_number }}</span>
        </span>
        <span v-if="call.category_label" class="cr-cat">{{ call.category_label }}</span>
        <span v-if="customer" class="cr-cust">{{ customer.name }}<span v-if="customer.id_number" class="ltr-number"> · {{ customer.id_number }}</span></span>
        <span v-if="call.duration_s >= 1" class="ltr-number">{{ mmss(call.duration_s) }}</span>
        <span v-if="dateLabel" class="ltr-number">{{ dateLabel }}</span>
        <span v-if="actions.length"><span class="ltr-number">{{ actions.length }}</span> משימות</span>
        <span v-if="sentiment" class="cr-sent"><i :style="{ background: sentiment.color }"></i>{{ sentiment.word }}</span>
      </p>
      <p v-if="tldr" class="cr-tldr">{{ tldr }}</p>
      <p v-else-if="call.error" class="cr-quiet">{{ call.error }}</p>
    </header>

    <!-- the call as a graphic -->
    <section v-if="bars.length" class="cr-timeline cr-in" style="--i: 1" aria-label="ציר השיחה">
      <div class="cr-tl-wrap">
        <svg class="cr-tl" viewBox="0 0 1000 72" preserveAspectRatio="none" role="img" :aria-label="`ציר השיחה, ${mmss(totalDur)}`">
          <line x1="0" y1="71" x2="1000" y2="71" class="cr-tl-base" />
          <rect v-for="(b, i) in bars" :key="i" class="cr-tl-bar" :class="{ 'is-hot': hotBin === i }"
                :x="b.x" :y="71 - b.h" :width="b.w" :height="b.h" rx="1.5" :style="{ animationDelay: (i * 6) + 'ms' }" />
        </svg>
        <!-- moments that land on (almost) the same second share one marker: "2·3" -->
        <button v-for="(g, gi) in markerGroups" :key="'m' + gi" type="button" class="cr-tl-mark"
                :class="{ 'is-hover': g.idx.includes(hoverMoment) }" :style="{ left: (xOf(g.at) / 10) + '%', animationDelay: (450 + gi * 110) + 'ms' }"
                :aria-label="g.idx.map((i) => `רגע ${i + 1}: ${markedMoments[i].text}`).join('; ') + `, ${mmss(g.at)}`"
                @mouseenter="hoverMoment = g.idx[0]" @mouseleave="hoverMoment = null" @focus="hoverMoment = g.idx[0]" @blur="hoverMoment = null"
                @click="openSheet(g.at)">
          <span class="cr-tl-dot ltr-number">{{ g.idx.map((i) => i + 1).join('·') }}</span><span class="cr-tl-stem"></span>
        </button>
      </div>
      <div class="cr-tl-axis"><span class="ltr-number">00:00</span><span class="ltr-number">{{ mmss(totalDur) }}</span></div>

      <div v-if="talk" class="cr-talk" :aria-label="`הסוכן דיבר ${talk.agent}%, הלקוח ${talk.customer}%`">
        <div class="cr-talk-bar"><i :style="{ width: talk.agent + '%' }"></i></div>
        <div class="cr-talk-legend">
          <span><b class="cr-talk-dot cr-talk-dot--agent"></b>סוכן <span class="ltr-number">{{ talk.agent }}%</span></span>
          <span><b class="cr-talk-dot"></b>לקוח <span class="ltr-number">{{ talk.customer }}%</span></span>
        </div>
      </div>

      <ol v-if="markedMoments.length" class="cr-moments">
        <li v-for="(m, i) in markedMoments" :key="i">
          <button type="button" :class="{ 'is-hover': hoverMoment === i }" @mouseenter="hoverMoment = i" @mouseleave="hoverMoment = null"
                  @focus="hoverMoment = i" @blur="hoverMoment = null" @click="openSheet(m.at)">
            <b>{{ i + 1 }}</b>
            <span class="cr-moment-at ltr-number">{{ mmss(m.at) }}</span>
            <span class="cr-moment-text">{{ m.text }}</span>
          </button>
        </li>
      </ol>
    </section>

    <!-- the summary, readable, never folded -->
    <section v-if="call.summary" class="cr-summary cr-in" style="--i: 2">
      <h4 class="cr-k">סיכום</h4>
      <p>{{ call.summary }}</p>
    </section>

    <section v-if="quotes.length" class="cr-quotes cr-in" style="--i: 2">
      <h4 class="cr-k">ציטוטים מהלקוח</h4>
      <blockquote v-for="(t, i) in quotes" :key="i">{{ t }}</blockquote>
    </section>

    <!-- the action block -->
    <div v-if="nextStep || actions.length || facts.length" class="cr-block">
      <section v-if="nextStep" class="cr-next cr-in" :class="{ 'is-done': nextDone }" style="--i: 3">
        <div class="cr-next-main">
          <h4 class="cr-k">הצעד הבא</h4>
          <p class="cr-next-text">{{ nextStep.text }}</p>
          <span v-if="nextStep.due" class="cr-due ltr-number">{{ dueLabel(nextStep.due) }}</span>
        </div>
        <button type="button" class="cr-next-act" :aria-pressed="nextDone" @click="toggleNext">
          <svg v-if="nextDone" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
          {{ nextDone ? 'בוצע' : 'סימון כבוצע' }}
        </button>
      </section>

      <section v-if="actions.length" class="cr-section cr-in" style="--i: 4">
        <h4 class="cr-k">משימות <span class="cr-k-n ltr-number">{{ doneCount }}/{{ actions.length }}</span></h4>
        <ul class="cr-tasks">
          <li v-for="(a, i) in actions" :key="i" :class="{ 'is-done': checked.has(i) }">
            <button type="button" class="cr-check" :aria-pressed="checked.has(i)" :aria-label="(checked.has(i) ? 'סמן כלא בוצע: ' : 'סמן כבוצע: ') + a.text" @click="toggle(i)">
              <svg v-if="checked.has(i)" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg>
            </button>
            <span class="cr-task-text">{{ a.text }}</span>
            <span class="cr-task-meta">
              <span class="cr-owner">{{ a.owner === 'customer' ? 'לקוח' : 'סוכן' }}</span>
              <span v-if="a.due" class="cr-due ltr-number">{{ dueLabel(a.due) }}</span>
            </span>
          </li>
        </ul>
      </section>

      <section v-if="facts.length" class="cr-facts cr-in" style="--i: 5" :style="{ '--cols': facts.length }">
        <div v-for="f in facts" :key="f.key" class="cr-fact">
          <h4 class="cr-k">{{ f.label }}</h4>
          <ul><li v-for="(t, i) in f.items" :key="i">{{ t }}</li></ul>
        </div>
      </section>
    </div>

    <!-- the transcript sheet -->
    <Teleport to="body">
      <Transition name="cr-sheet" @after-enter="onSheetShown">
        <div v-if="sheetOpen" class="cr-sheet-layer" @keydown="onSheetKey">
          <div class="cr-sheet-scrim" @click="closeSheet"></div>
          <aside ref="sheetEl" class="cr-sheet" role="dialog" aria-modal="true" aria-labelledby="cr-sheet-title">
            <header class="cr-sheet-head">
              <div>
                <h3 id="cr-sheet-title">תמליל השיחה</h3>
                <span class="cr-sheet-sub"><span class="ltr-number">{{ mmss(totalDur) }}</span> · <span class="ltr-number">{{ segments.length }}</span> קטעים</span>
              </div>
              <button ref="closeBtn" type="button" class="cr-icon" aria-label="סגירת התמליל" @click="closeSheet">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
              </button>
            </header>
            <div class="cr-sheet-search">
              <label class="cr-search">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
                <input v-model="q" type="search" placeholder="חיפוש בתמליל" aria-label="חיפוש בתמליל" @keydown.enter.prevent="stepMatch($event.shiftKey ? -1 : 1)" />
              </label>
              <template v-if="q.trim()">
                <span class="cr-match ltr-number" aria-live="polite">{{ matches.length ? matchIdx + 1 : 0 }}/{{ matches.length }}</span>
                <button type="button" class="cr-icon cr-icon--sm" aria-label="ההתאמה הקודמת" :disabled="!matches.length" @click="stepMatch(-1)">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 15l-6-6-6 6" /></svg>
                </button>
                <button type="button" class="cr-icon cr-icon--sm" aria-label="ההתאמה הבאה" :disabled="!matches.length" @click="stepMatch(1)">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9l6 6 6-6" /></svg>
                </button>
              </template>
            </div>
            <div ref="txEl" class="cr-sheet-body">
              <section v-for="g in groups" :key="g.minute" class="cr-group">
                <h5 v-if="groups.length > 1" class="cr-group-h ltr-number">{{ mmss(g.minute * 60) }}</h5>
                <div v-for="s in g.rows" :key="s.start" class="cr-seg" :data-at="s.start"
                     :class="{ 'is-target': target === s.start, 'is-match': isCurrentMatch(s) }">
                  <span class="cr-seg-at ltr-number">{{ mmss(s.start) }}</span>
                  <p><b v-if="s.speaker" class="cr-who" :class="{ 'cr-who--agent': roleOf(s) === 'agent' }">{{ whoLabel(s) }}</b><template v-for="(part, j) in mark(s.text)" :key="j"><mark v-if="part.hit">{{ part.t }}</mark><template v-else>{{ part.t }}</template></template></p>
                </div>
              </section>
              <p v-if="!segments.length && call.transcript_text" class="cr-para">{{ call.transcript_text }}</p>
            </div>
          </aside>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { getUserFlag, setUserFlag } from '../../utils/userFlags'
import { useCallsStore } from '../../stores/calls'

const props = defineProps({
  call: { type: Object, required: true },
  reveal: { type: Boolean, default: true },
})
defineEmits(['delete', 'personal'])
const personalOpen = ref(false)

const ins = computed(() => props.call.insights || {})
const list = (k, max) => (ins.value[k] || []).filter((x) => x && String(x).trim()).slice(0, max)
// `_i` = the task's index on the server (insights.action_items[_i]) — ticks are saved there
const actions = computed(() => (ins.value.action_items || []).map((a, i) => ({ ...a, _i: i })).filter((a) => a && a.text).slice(0, 5))
const keyPoints = computed(() => list('key_points', 4))
const segments = computed(() => props.call.segments || [])
const hasTranscript = computed(() => segments.value.length > 0 || !!props.call.transcript_text)
const facts = computed(() => [
  { key: 'needs', label: 'הלקוח צריך', items: list('customer_needs', 4) },
  { key: 'products', label: 'מוצרים', items: list('products_mentioned', 4) },
  { key: 'objections', label: 'התנגדויות', items: list('objections', 4) },
].filter((f) => f.items.length))

const tldr = computed(() => {
  const t = (ins.value.tldr || '').trim()
  if (t) return t
  const s = (props.call.summary || '').trim()
  if (!s) return ''
  const m = s.match(/^.*?[.!?](\s|$)/)
  return (m ? m[0] : s).trim()
})
const nextStep = computed(() => {
  if (ins.value.follow_up) return { text: ins.value.follow_up, due: null }
  const a = actions.value.find((x) => x.owner !== 'customer')
  return a ? { text: a.text, due: a.due } : null
})

// ── speakers (diarization) + where the call came from ──
const roles = computed(() => ins.value.speaker_roles || {})
const roleOf = (s) => roles.value[s.speaker] || null
const whoLabel = (s) => ({ agent: 'סוכן', customer: 'לקוח' })[roleOf(s)] || ('דובר ' + String(s.speaker || '').replace(/\D/g, ''))
const talk = computed(() => {
  const p = ins.value.talk_ratio?.agent_pct
  return p == null ? null : { agent: p, customer: 100 - p }
})
const quotes = computed(() => list('customer_quotes', 3))
const phoneCall = computed(() => {
  if (!String(props.call.source || '').startsWith('phone')) return ''
  return { in: 'שיחה נכנסת', out: 'שיחה יוצאת' }[props.call.direction] || 'שיחת טלפון'
})
const customer = computed(() => (ins.value.customer?.matched ? ins.value.customer : null))

const SENT = {
  positive: { word: 'חיובית', color: '#2E844A' },
  neutral: { word: 'ניטרלית', color: '#9AA5B1' },
  mixed: { word: 'מעורבת', color: '#8A6300' },
  negative: { word: 'שלילית', color: '#C4001A' },
}
const sentiment = computed(() => SENT[ins.value.sentiment] || null)

// ── timeline: speech density per slice of the call, from the segment timings ──
const totalDur = computed(() => Math.max(Number(props.call.duration_s) || 0, ...segments.value.map((s) => Number(s.end) || 0), 1))
const BINS = 96
const bars = computed(() => {
  if (!segments.value.length) return []
  const D = totalDur.value
  const dens = new Array(BINS).fill(0)
  for (const s of segments.value) {
    const a = Number(s.start) || 0
    const b = Math.max(a + 0.2, Number(s.end) || a + 1)
    const rate = (s.text || '').length / (b - a)
    for (let i = Math.floor((a / D) * BINS); i <= Math.min(BINS - 1, Math.floor((b / D) * BINS)); i++) {
      const lo = (i / BINS) * D
      const hi = ((i + 1) / BINS) * D
      dens[i] += rate * (Math.max(0, Math.min(b, hi) - Math.max(a, lo)) / (hi - lo))
    }
  }
  const max = Math.max(...dens, 1)
  const w = 1000 / BINS
  // time runs right → left (RTL): the call starts at the right edge
  return dens.map((d, i) => ({ x: 1000 - (i + 1) * w + w * 0.18, w: w * 0.64, h: d > 0 ? 6 + (d / max) * 52 : 2 }))
})
const xOf = (t) => 1000 - (Math.min(totalDur.value, Math.max(0, t)) / totalDur.value) * 1000

const words = (t) => String(t || '').replace(/[^֐-׿a-zA-Z0-9% ]/g, ' ').split(/\s+/).filter((w) => w.length >= 3)
const markedMoments = computed(() => keyPoints.value.map((text) => {
  const kw = new Set(words(text))
  let best = null
  let score = 1
  for (const s of segments.value) {
    const hit = words(s.text).filter((w) => kw.has(w)).length
    if (hit > score) { score = hit; best = s }
  }
  return best ? { text, at: Number(best.start) || 0 } : null
}).filter(Boolean))
const markerGroups = computed(() => {
  const order = markedMoments.value.map((m, i) => ({ ...m, i })).sort((a, b) => a.at - b.at)
  const out = []
  for (const m of order) {
    const last = out[out.length - 1]
    if (last && Math.abs(xOf(m.at) - xOf(last.at)) < 28) last.idx.push(m.i)
    else out.push({ at: m.at, idx: [m.i] })
  }
  return out
})
const hoverMoment = ref(null)
const hotBin = computed(() => {
  const m = hoverMoment.value === null ? null : markedMoments.value[hoverMoment.value]
  return m ? Math.min(BINS - 1, Math.floor((m.at / totalDur.value) * BINS)) : null
})

function mmss(sec) {
  const s = Math.max(0, Math.floor(Number(sec) || 0))
  const h = Math.floor(s / 3600)
  const mm = String(Math.floor((s % 3600) / 60)).padStart(2, '0')
  const ss = String(s % 60).padStart(2, '0')
  return h ? `${h}:${mm}:${ss}` : `${mm}:${ss}`
}
const dateLabel = computed(() => {
  const d = new Date(props.call.created_at || '')
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('he-IL', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
})
function dueLabel(due) {
  const m = String(due).match(/^(\d{4})-(\d{2})-(\d{2})/)
  return m ? `${m[3]}.${m[2]}` : due
}

// ── tasks: done lives on the server (so Nifra Agent knows what is still open);
//    the next step is a per-user flag ──
const calls = useCallsStore()
const checked = computed(() => new Set(actions.value.map((a, pos) => (a.done ? pos : -1)).filter((p) => p >= 0)))
const nextDone = ref(false)
const flagKey = () => 'calls_tasks_' + props.call.id
function load() {
  nextDone.value = getUserFlag('calls_next_' + props.call.id) === '1'
  // ticks made before they were saved on the server: move them there once
  let old = []
  try { old = JSON.parse(getUserFlag(flagKey()) || '[]') } catch (_) { old = [] }
  if (old.length) {
    setUserFlag(flagKey(), '[]')
    for (const pos of old) {
      const a = actions.value[pos]
      if (a && !a.done) calls.setTaskDone(props.call, a._i, true)
    }
  }
}
function toggle(pos) {
  const a = actions.value[pos]
  if (a) calls.setTaskDone(props.call, a._i, !a.done)
}
function toggleNext() {
  nextDone.value = !nextDone.value
  setUserFlag('calls_next_' + props.call.id, nextDone.value ? '1' : '0')
}
const doneCount = computed(() => [...checked.value].filter((i) => i < actions.value.length).length)
load()

// ── transcript sheet ──
const sheetOpen = ref(false)
const sheetEl = ref(null)
const closeBtn = ref(null)
const txEl = ref(null)
const target = ref(null)
const q = ref('')
const matchIdx = ref(0)
let returnFocus = null

const groups = computed(() => {
  const out = []
  for (const s of segments.value) {
    const minute = Math.floor((Number(s.start) || 0) / 60)
    if (!out.length || out[out.length - 1].minute !== minute) out.push({ minute, rows: [] })
    out[out.length - 1].rows.push(s)
  }
  return out
})
const matches = computed(() => {
  const term = q.value.trim()
  return term ? segments.value.filter((s) => (s.text || '').includes(term)) : []
})
watch(q, () => { matchIdx.value = 0; nextTick(() => scrollToMatch()) })
const isCurrentMatch = (s) => matches.value.length > 0 && matches.value[matchIdx.value] === s
function stepMatch(d) {
  const n = matches.value.length
  if (!n) return
  matchIdx.value = (matchIdx.value + d + n) % n
  scrollToMatch()
}
function scrollTo(at) {
  txEl.value?.querySelector(`[data-at="${at}"]`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
function scrollToMatch() { const m = matches.value[matchIdx.value]; if (m) scrollTo(m.start) }
function mark(text) {
  const term = q.value.trim()
  if (!term || !text) return [{ t: text, hit: false }]
  const out = []
  let rest = text
  let idx
  while ((idx = rest.indexOf(term)) !== -1) {
    if (idx) out.push({ t: rest.slice(0, idx), hit: false })
    out.push({ t: term, hit: true })
    rest = rest.slice(idx + term.length)
  }
  if (rest) out.push({ t: rest, hit: false })
  return out
}

let pendingAt = null
function openSheet(at = null) {
  if (!hasTranscript.value) return
  returnFocus = document.activeElement
  target.value = at
  pendingAt = at
  q.value = ''
  sheetOpen.value = true
}
function onSheetShown() {
  if (pendingAt !== null) scrollTo(pendingAt)
  pendingAt = null
  closeBtn.value?.focus()
}
function closeSheet() {
  sheetOpen.value = false
  target.value = null
  returnFocus?.focus?.()
}
// Escape closes only the sheet (stopped here, so the studio's window listener
// never sees it); Tab stays inside the sheet.
function onSheetKey(e) {
  if (e.key === 'Escape') { e.stopPropagation(); e.preventDefault(); closeSheet(); return }
  if (e.key !== 'Tab' || !sheetEl.value) return
  const f = [...sheetEl.value.querySelectorAll('button:not([disabled]), input')].filter((el) => el.offsetParent !== null)
  if (!f.length) return
  const first = f[0]
  const last = f[f.length - 1]
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus() }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus() }
}
onBeforeUnmount(() => { sheetOpen.value = false })

watch(() => props.call.id, () => { q.value = ''; sheetOpen.value = false; load() })
</script>

<style scoped>
.cr { --acc: #A63A86; display: flex; flex-direction: column; gap: 32px; max-width: 1040px; margin: 0 auto; color: var(--text); }
.cr--reveal .cr-in { animation: crIn 0.5s cubic-bezier(0.32, 0.72, 0, 1) both; animation-delay: calc(120ms + var(--i, 0) * 60ms); }
@keyframes crIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
.cr-k { margin: 0; display: flex; align-items: baseline; gap: 8px; font-size: 12px; font-weight: 600; letter-spacing: 0.02em; color: var(--text-muted); line-height: 1.4; }
.cr-k-n { font-weight: 500; }

/* hero */
.cr-hero { display: flex; flex-direction: column; gap: 10px; }
.cr-hero-top { display: flex; align-items: flex-start; gap: 16px; }
.cr-title { flex: 1; margin: 0; font-size: clamp(26px, 2.6vw, 34px); font-weight: 800; letter-spacing: -0.03em; line-height: 1.15; }
.cr-actions { display: flex; gap: 8px; flex: none; padding-top: 4px; }
.cr-personal { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 10px; padding: 10px 12px; border-radius: 12px;
  background: var(--bg); font-size: 13.5px; color: var(--text-secondary); }
.cr-act {
  display: inline-flex; align-items: center; gap: 8px; min-height: 40px; padding: 0 14px; border-radius: 10px;
  border: 1px solid var(--border-subtle); background: var(--card-bg); color: var(--text); font: inherit; font-size: 14px; font-weight: 600; cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.cr-act:hover { background: var(--bg); border-color: #D5D2CE; }
.cr-act:focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }
.cr-act-n { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.cr-act--quiet { border-color: transparent; color: var(--text-muted); font-weight: 500; }
.cr-act--quiet:hover { color: var(--red); background: rgba(234, 0, 30, 0.06); border-color: transparent; }
.cr-meta { margin: 0; display: flex; flex-wrap: wrap; align-items: center; gap: 4px 16px; font-size: 14px; color: var(--text-muted); }
.cr-sent { display: inline-flex; align-items: center; gap: 6px; color: var(--text-secondary); }
.cr-sent i { width: 8px; height: 8px; border-radius: 50%; }
.cr-tldr { margin: 8px 0 0; font-size: clamp(19px, 1.8vw, 23px); line-height: 1.45; font-weight: 500; letter-spacing: -0.01em; max-width: 60ch; }
.cr-quiet { margin: 0; color: var(--text-muted); font-size: 14.5px; }

/* timeline */
.cr-timeline { display: flex; flex-direction: column; gap: 4px; }
.cr-tl-wrap { position: relative; padding-top: 14px; }
.cr-tl { display: block; width: 100%; height: 72px; overflow: visible; }
.cr-tl-base { stroke: var(--border-subtle); stroke-width: 1; vector-effect: non-scaling-stroke; }
.cr-tl-bar { fill: #2A2A2A; opacity: 0.15; transform-box: fill-box; transform-origin: bottom; transition: opacity 0.2s ease, fill 0.2s ease; }
.cr-tl-bar.is-hot { fill: var(--acc); opacity: 1; }
.cr--reveal .cr-tl-bar { animation: crBar 0.5s cubic-bezier(0.32, 0.72, 0, 1) both; }
@keyframes crBar { from { transform: scaleY(0); } }
.cr-tl-mark {
  position: absolute; top: 0; bottom: 1px; min-width: 28px; padding: 0; margin: 0; border: none; background: none;
  display: flex; flex-direction: column; align-items: center; cursor: pointer; transform: translateX(-50%);
}
.cr-tl-dot {
  min-width: 22px; height: 22px; padding: 0 5px; box-sizing: border-box; border-radius: 999px; display: grid; place-items: center; flex: none;
  font: 700 11px 'Heebo', sans-serif; color: var(--acc); background: #fff; border: 1.5px solid var(--acc); transition: background 0.15s ease, color 0.15s ease;
}
.cr-tl-stem { flex: 1; width: 1.5px; background: var(--acc); opacity: 0.4; }
.cr-tl-mark:hover .cr-tl-dot, .cr-tl-mark.is-hover .cr-tl-dot { background: var(--acc); color: #fff; }
.cr-tl-mark:focus-visible { outline: none; }
.cr-tl-mark:focus-visible .cr-tl-dot { box-shadow: 0 0 0 3px #F3DDEB; }
.cr--reveal .cr-tl-mark { animation: crMark 0.4s ease both; }
@keyframes crMark { from { opacity: 0; transform: translateX(-50%) translateY(6px); } to { opacity: 1; transform: translateX(-50%); } }
.cr-tl-axis { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.cr-moments { list-style: none; margin: 12px 0 0; padding: 0; display: flex; flex-direction: column; }
.cr-moments button {
  width: 100%; display: grid; grid-template-columns: 22px 44px minmax(0, 1fr); align-items: baseline; gap: 12px;
  text-align: start; border: none; background: none; padding: 8px 6px; border-radius: 8px; font: inherit; color: var(--text); cursor: pointer;
  transition: background 0.15s ease;
}
.cr-moments button:hover, .cr-moments button.is-hover { background: var(--bg); }
.cr-moments button:focus-visible { outline: 2px solid var(--acc); outline-offset: 0; }
.cr-moments b { width: 22px; height: 22px; border-radius: 50%; display: inline-grid; place-items: center; align-self: center; font-size: 11px; color: var(--acc); border: 1.5px solid var(--acc); }
.cr-moment-at { font-size: 13px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.cr-moment-text { font-size: 15px; line-height: 1.5; }

/* category chip — the call's own accent, one colour */
.cr-cat { display: inline-flex; align-items: center; padding: 2px 10px; border-radius: 999px; font-size: 12.5px; font-weight: 600;
  color: var(--acc); background: #F7EAF3; }
/* source + customer */
.cr-src, .cr-cust { display: inline-flex; align-items: center; gap: 6px; color: var(--text-secondary); font-weight: 500; }
.cr-cust { color: var(--text); font-weight: 600; }

/* talk ratio */
.cr-talk { margin-top: 12px; display: flex; flex-direction: column; gap: 6px; max-width: 360px; }
.cr-talk-bar { height: 6px; border-radius: 999px; background: #E4E1DC; overflow: hidden; }
.cr-talk-bar i { display: block; height: 100%; background: var(--acc); border-radius: 999px; transition: width 0.6s ease; }
.cr-talk-legend { display: flex; gap: 16px; font-size: 13px; color: var(--text-secondary); }
.cr-talk-legend > span { display: inline-flex; align-items: center; gap: 6px; }
.cr-talk-dot { width: 8px; height: 8px; border-radius: 50%; background: #CFCBC5; }
.cr-talk-dot--agent { background: var(--acc); }

/* customer quotes */
.cr-quotes { display: flex; flex-direction: column; gap: 8px; }
.cr-quotes blockquote { margin: 0; max-width: 68ch; padding: 4px 14px; border-inline-start: 3px solid #D9D5CF; font-size: 16px; line-height: 1.6; color: var(--text); }

/* summary */
.cr-summary { display: flex; flex-direction: column; gap: 8px; }
.cr-summary p { margin: 0; max-width: 68ch; font-size: 16px; line-height: 1.7; white-space: pre-wrap; }

/* action block */
.cr-block { width: 100%; max-width: 760px; margin: 0 auto; display: flex; flex-direction: column; gap: 32px; padding-top: 24px; border-top: 1px solid var(--border-subtle); }
.cr-next {
  display: flex; align-items: center; gap: 24px; padding: 16px 20px; border-radius: 12px;
  background: #FAF9F7; border-inline-start: 3px solid var(--acc);
}
.cr-next-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.cr-next-text {
  margin: 0; font-size: 17px; font-weight: 600; line-height: 1.45;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.cr-next .cr-due { align-self: flex-start; margin-top: 4px; }
.cr-next.is-done .cr-next-text { color: var(--text-muted); text-decoration: line-through; }
.cr-next-act {
  flex: none; display: inline-flex; align-items: center; gap: 6px; min-height: 40px; padding: 0 14px; border-radius: 10px;
  border: 1px solid var(--border-subtle); background: var(--card-bg); color: var(--text-secondary); font: inherit; font-size: 14px; font-weight: 500; cursor: pointer;
}
.cr-next-act:hover { border-color: #D5D2CE; color: var(--text); }
.cr-next-act[aria-pressed="true"] { color: var(--acc); border-color: transparent; background: transparent; }
.cr-next-act:focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }

.cr-section { display: flex; flex-direction: column; gap: 8px; }
.cr-tasks { list-style: none; margin: 0; padding: 0; }
.cr-tasks li {
  display: grid; grid-template-columns: 20px minmax(0, 1fr) auto; align-items: center; gap: 12px;
  min-height: 52px; padding: 8px 0; border-bottom: 1px solid var(--border-subtle);
}
.cr-check { width: 20px; height: 20px; padding: 0; border-radius: 6px; border: 1.5px solid #B9B6B2; background: #fff; color: #fff; display: grid; place-items: center; cursor: pointer; position: relative; }
.cr-check::before { content: ''; position: absolute; inset: -12px; } /* 44px hit area */
.cr-check:hover { border-color: var(--text); }
.cr-check:focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }
.cr-tasks .is-done .cr-check { background: var(--text); border-color: var(--text); }
.cr-task-text { font-size: 15.5px; line-height: 1.45; }
.cr-tasks .is-done .cr-task-text { color: var(--text-muted); text-decoration: line-through; }
.cr-task-meta { display: flex; align-items: center; gap: 6px; justify-content: flex-end; }
.cr-owner { font-size: 12px; font-weight: 500; color: var(--text-secondary); background: var(--bg); padding: 2px 9px; border-radius: 999px; }
.cr-due { font-size: 12px; font-weight: 600; color: var(--text-secondary); border: 1px solid var(--border-subtle); border-radius: 6px; padding: 1px 7px; font-variant-numeric: tabular-nums; }
.cr-tasks .is-done .cr-owner, .cr-tasks .is-done .cr-due { opacity: 0.6; }

.cr-facts { display: grid; grid-template-columns: repeat(var(--cols), minmax(0, 1fr)); gap: 24px; }
.cr-fact { display: flex; flex-direction: column; gap: 8px; }
.cr-fact ul { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 6px; }
.cr-fact li { position: relative; padding-inline-start: 14px; font-size: 15px; line-height: 1.5; }
.cr-fact li::before { content: ''; position: absolute; inset-inline-start: 0; top: 0.62em; width: 5px; height: 5px; border-radius: 50%; background: #C9C6C1; }

/* transcript sheet */
.cr-sheet-layer { position: fixed; inset: 0; z-index: 1600; }
.cr-sheet-scrim { position: absolute; inset: 0; background: rgba(12, 10, 14, 0.32); }
.cr-sheet {
  position: absolute; top: 0; bottom: 0; left: 0; width: min(440px, 100vw); display: flex; flex-direction: column;
  background: var(--card-bg); color: var(--text); box-shadow: 0 0 60px rgba(0, 0, 0, 0.22); font-family: 'Heebo', sans-serif;
}
.cr-sheet-head { display: flex; align-items: flex-start; gap: 12px; padding: 20px 20px 12px; }
.cr-sheet-head > div { flex: 1; display: flex; flex-direction: column; gap: 2px; }
.cr-sheet-head h3 { margin: 0; font-size: 19px; font-weight: 800; letter-spacing: -0.02em; }
.cr-sheet-sub { font-size: 13px; color: var(--text-muted); }
.cr-icon { width: 40px; height: 40px; flex: none; border-radius: 10px; border: none; background: none; color: var(--text-secondary); display: grid; place-items: center; cursor: pointer; }
.cr-icon:hover { background: var(--bg); color: var(--text); }
.cr-icon:disabled { opacity: 0.4; cursor: default; }
.cr-icon:focus-visible { outline: 2px solid var(--acc); outline-offset: 0; }
.cr-icon--sm { width: 34px; height: 34px; }
.cr-sheet-search { display: flex; align-items: center; gap: 4px; padding: 0 20px 12px; border-bottom: 1px solid var(--border-subtle); }
.cr-search { flex: 1; display: flex; align-items: center; gap: 8px; height: 40px; padding: 0 12px; border-radius: 10px; background: var(--bg); color: var(--text-muted); }
.cr-search:focus-within { box-shadow: 0 0 0 2px var(--text); background: var(--card-bg); }
.cr-search input { flex: 1; min-width: 0; border: none; background: none; outline: none; font: inherit; font-size: 15px; color: var(--text); }
.cr-search input:focus { outline: none; box-shadow: none; }
.cr-search input::-webkit-search-cancel-button { -webkit-appearance: none; appearance: none; }
.cr-match { min-width: 44px; text-align: center; font-size: 13px; font-weight: 600; color: var(--text-secondary); font-variant-numeric: tabular-nums; }
.cr-sheet-body { flex: 1; overflow-y: auto; padding: 8px 12px 32px; overscroll-behavior: contain; }
.cr-group { padding: 4px 0 8px; }
.cr-group + .cr-group { border-top: 1px solid var(--border-subtle); }
.cr-group-h { margin: 8px 8px 2px; font-size: 11px; font-weight: 700; color: var(--text-muted); letter-spacing: 0.04em; }
.cr-seg { display: grid; grid-template-columns: 44px minmax(0, 1fr); gap: 12px; padding: 8px; border-radius: 8px; transition: background 0.25s ease; }
.cr-seg-at { padding-top: 3px; font-size: 12px; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.cr-seg p { margin: 0; font-size: 15.5px; line-height: 1.7; }
.cr-who { margin-inline-end: 8px; font-size: 12px; font-weight: 700; color: var(--text-muted); }
.cr-who--agent { color: var(--acc); }
.cr-seg mark { background: #F6E7F0; color: inherit; border-radius: 3px; padding: 0 2px; }
.cr-seg.is-target { background: #FAF3F8; box-shadow: inset -3px 0 0 var(--acc); }
.cr-seg.is-match { background: var(--bg); }
.cr-seg.is-match mark { background: #EBC6DD; color: var(--text); box-shadow: 0 0 0 1.5px var(--acc); }
.cr-para { margin: 8px; font-size: 15.5px; line-height: 1.7; white-space: pre-wrap; }

/* the sheet slides in from the inline end (left in RTL), the scrim fades */
.cr-sheet-enter-active, .cr-sheet-leave-active { transition: opacity 0.28s ease; }
.cr-sheet-enter-active .cr-sheet { transition: transform 0.34s cubic-bezier(0.32, 0.72, 0, 1); }
.cr-sheet-leave-active .cr-sheet { transition: transform 0.22s ease-in; }
.cr-sheet-enter-from, .cr-sheet-leave-to { opacity: 0; }
.cr-sheet-enter-from .cr-sheet, .cr-sheet-leave-to .cr-sheet { transform: translateX(-24px); }

@media (max-width: 760px) {
  .cr { gap: 24px; }
  .cr-hero-top { flex-direction: column; gap: 10px; }
  .cr-actions { padding-top: 0; }
  .cr-facts { grid-template-columns: 1fr; }
  .cr-next { flex-direction: column; align-items: stretch; gap: 12px; }
  .cr-next-act { align-self: flex-start; }
  .cr-sheet { width: 100vw; }
}
@media (prefers-reduced-motion: reduce) {
  .cr--reveal .cr-in, .cr--reveal .cr-tl-bar, .cr--reveal .cr-tl-mark { animation: none; }
  .cr-sheet-enter-active, .cr-sheet-leave-active, .cr-sheet-enter-active .cr-sheet, .cr-sheet-leave-active .cr-sheet { transition: none; }
}
</style>
