<template>
  <Teleport to="body">
    <Transition :css="false" @enter="onEnter" @leave="onLeave" @after-leave="onAfterLeave">
      <div v-if="open" ref="rootEl" class="cs" tabindex="-1" role="dialog" aria-modal="true" aria-label="Nifra Calls">
        <!-- Nifra Calls — calm on purpose: one flat canvas, one orb in the
             middle that IS the record button, and the history on a ruler at
             the bottom. A call opens like an iPhone app from its ruler item. -->
        <header class="cs-top">
          <span class="cs-mark" dir="ltr">Nifra <b>Calls</b></span>
          <span class="cs-fill"></span>
          <!-- three big numbers: all calls · being processed now · waiting in the queue -->
          <dl class="cs-stats" aria-label="סטטוס השיחות">
            <div class="cs-stat">
              <dd><Transition name="cs-num" mode="out-in"><span :key="counts.total" class="ltr-number">{{ counts.total }}</span></Transition></dd>
              <dt>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M4 10v4M8 7v10M12 4v16M16 7v10M20 10v4" /></svg>
                שיחות
              </dt>
            </div>
            <i class="cs-stat-sep" aria-hidden="true"></i>
            <div class="cs-stat cs-stat--working" :class="{ 'is-on': counts.working }">
              <dd><Transition name="cs-num" mode="out-in"><span :key="counts.working" class="ltr-number">{{ counts.working }}</span></Transition></dd>
              <dt>
                <svg class="cs-spin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-9-9" /></svg>
                בעיבוד
              </dt>
            </div>
            <i class="cs-stat-sep" aria-hidden="true"></i>
            <div class="cs-stat cs-stat--waiting" :class="{ 'is-on': counts.waiting }">
              <dd><Transition name="cs-num" mode="out-in"><span :key="counts.waiting" class="ltr-number">{{ counts.waiting }}</span></Transition></dd>
              <dt>
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg>
                ממתינות
              </dt>
            </div>
          </dl>
          <span class="cs-fill"></span>
          <button type="button" class="cs-icon" :aria-label="phase === 'recording' ? 'סגירה — ההקלטה ממשיכה' : 'סגירה'" @click="close">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
          </button>
        </header>

        <main class="cs-stage">
          <button ref="orbEl" type="button" class="cs-orb" @mouseenter="orbHover = true" @mouseleave="orbHover = false" :class="['cs-orb--' + phase, motionClass]" :aria-label="orbLabel"
                  :disabled="phase === 'uploading' || phase === 'requesting'" @click="onOrb">
            <CallsOrb :size="orbSize" :state="orbState" :level="store.micLevel" />
            <span v-if="motionClass === 'cs-orb--start'" class="cs-ripple" aria-hidden="true"></span>
            <span class="cs-glyph" aria-hidden="true">
              <Transition name="cs-glyph" mode="out-in">
                <svg v-if="phase === 'recording'" key="stop" width="22" height="22" viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2.5" fill="currentColor" /></svg>
                <svg v-else-if="phase === 'idle'" key="mic" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="9" y="2.5" width="6" height="12" rx="3" /><path d="M5 11a7 7 0 0 0 14 0" /><path d="M12 18v3.5" />
                </svg>
              </Transition>
            </span>
          </button>

          <div class="cs-status-slot" aria-live="polite">
            <Transition name="cs-status" mode="out-in">
              <p v-if="phase === 'recording'" key="rec" class="cs-status"><i class="cs-dot"></i><CallTimer /> · לחצו לעצירה</p>
              <p v-else-if="phase === 'uploading'" key="up" class="cs-status">שולח <span class="ltr-number">{{ Math.round(store.uploadProgress * 100) }}%</span></p>
              <p v-else-if="phase === 'requesting'" key="req" class="cs-status">מאשר מיקרופון…</p>
              <p v-else-if="store.notice" key="notice" class="cs-status cs-status--notice">{{ store.notice }}</p>
              <p v-else-if="orbHover && phase === 'idle'" key="hint" class="cs-status cs-hint">לחצו כדי להתחיל להקליט</p>
            </Transition>
          </div>

          <Transition name="cs-pop">
            <div v-if="consentOpen" class="cs-consent" role="dialog" aria-label="הסכמה להקלטה">
              <label><input v-model="consentTick" type="checkbox" /> הלקוח יודע שהשיחה מוקלטת</label>
              <div class="cs-consent-actions">
                <button type="button" class="cs-go" :disabled="!consentTick" @click="acceptConsent">הקלטה</button>
                <button type="button" class="cs-ghost" @click="consentOpen = false">ביטול</button>
              </div>
            </div>
          </Transition>
          <p v-if="store.error" class="cs-err" role="alert">{{ store.error }}</p>
        </main>

        <!-- history band -->
        <footer ref="bandEl" class="cs-band" aria-label="היסטוריית שיחות">
          <div class="cs-band-tools">
            <button type="button" class="cs-icon cs-icon--sm" :aria-label="searchOpen ? 'סגירת חיפוש' : 'חיפוש שיחות'" @click="toggleSearch">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
            </button>
            <input v-show="searchOpen" ref="searchEl" v-model="query" class="cs-search" type="search" placeholder="חיפוש בשיחות"
                   aria-label="חיפוש בשיחות" @keydown.esc.stop="toggleSearch" />
          </div>
          <RulerCarouselIsland
            v-if="items.length"
            :items="items"
            :active="activeIdx"
            :colors="rulerColors"
            :item-width="narrow ? 190 : 240"
            :gap="narrow ? 28 : 48"
            :fresh-id="freshId"
            @active="(i) => (activeIdx = i)"
            @open="openDetail"
          />
          <p v-else class="cs-empty">{{ query ? 'לא נמצאו שיחות.' : 'עוד אין שיחות.' }}</p>
        </footer>

        <!-- the opened call -->
        <div v-if="detailOpen" class="cs-scrim" @click="closeDetail"></div>
        <article v-if="detailOpen && detailCall" ref="detailEl" class="cs-detail" role="dialog" aria-modal="true" :aria-label="detailCall.title || 'שיחה'">
          <div class="cs-detail-bar">
            <button type="button" class="cs-back" @click="closeDetail">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6" /></svg>
              כל השיחות
            </button>
            <span class="cs-fill"></span>
            <button v-if="detailCall.status !== 'done'" type="button" class="cs-del" @click="onDelete(detailCall.id)">מחיקה</button>
          </div>
          <div class="cs-detail-body">
            <Transition name="cs-swap" mode="out-in">
              <CallWaiting v-if="detailCall.status !== 'done'" :key="detailCall.id + '-w'" :call="detailCall" />
              <CallResult v-else :key="detailCall.id + '-r'" :call="detailCall" @delete="onDelete(detailCall.id)"
                          @personal="(block) => onPersonal(detailCall.id, block)" />
            </Transition>
          </div>
        </article>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { useCallsStore, CALL_TERMINAL, isNoSpeech } from '../../stores/calls'
import { getUserFlag, setUserFlag } from '../../utils/userFlags'
import { useOriginMorph } from '../../composables/useOriginMorph'
import CallsOrb from './CallsOrb.vue'
import CallWaiting from './CallWaiting.vue'
import CallResult from './CallResult.vue'
import RulerCarouselIsland from './RulerCarouselIsland.vue'
import CallTimer from './CallTimer.vue'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['update:open', 'seen'])
const store = useCallsStore()

const rootEl = ref(null)
const searchEl = ref(null)
const detailEl = ref(null)

const vw = ref(window.innerWidth)
function onResize() { vw.value = window.innerWidth }
window.addEventListener('resize', onResize)
onBeforeUnmount(() => window.removeEventListener('resize', onResize))
const narrow = computed(() => vw.value < 700)
const orbSize = computed(() => (narrow.value ? 220 : 330))

const canvasDark = ref(false)
const rulerColors = computed(() => (canvasDark.value
  ? { text: '#F2F0F3', faint: 'rgba(242,240,243,0.6)', tick: 'rgba(242,240,243,0.28)', accent: '#D96AB5', button: 'rgba(255,255,255,0.08)' }
  : { text: '#181818', faint: 'rgba(24,24,24,0.55)', tick: 'rgba(24,24,24,0.25)', accent: '#A63A86', button: 'rgba(24,24,24,0.06)' }))

// ── recording ──
const phase = computed(() => {
  if (store.recState === 'recording') return 'recording'
  if (store.recState === 'requesting') return 'requesting'
  if (store.recState === 'uploading') return 'uploading'
  return 'idle'
})
// the orb never waits on the queue (with many agents a summary can take minutes) — it is free again as soon as the call is sent
const orbState = computed(() => (phase.value === 'recording' ? 'recording' : phase.value !== 'idle' ? 'processing' : 'idle'))
const orbLabel = computed(() => (phase.value === 'recording' ? 'עצירה ושליחה' : 'התחלת הקלטה'))

const orbHover = ref(false)
const consentOpen = ref(false)
const consentTick = ref(false)
async function onOrb() {
  if (phase.value === 'recording') {
    const c = await store.stopAndUpload()
    if (c && !isNoSpeech(c) && c.status !== 'failed') {
      store.showNotice('השיחה נשלחה · הסיכום יופיע כאן כשיהיה מוכן')
      query.value = ''
      activeIdx.value = 0
      freshId.value = c.id
      setTimeout(() => { if (freshId.value === c.id) freshId.value = null }, 1600)
    }
    return
  }
  if (phase.value !== 'idle') return
  if (getUserFlag('calls_consent_ack') !== '1') { consentTick.value = false; consentOpen.value = true; return }
  store.startRecording()
}
function acceptConsent() {
  setUserFlag('calls_consent_ack', '1')
  consentOpen.value = false
  store.startRecording()
}

// ── search ──
const searchOpen = ref(false)
const query = ref('')
let prefetched = false
async function toggleSearch() {
  searchOpen.value = !searchOpen.value
  if (!searchOpen.value) { query.value = ''; return }
  await nextTick()
  searchEl.value?.focus()
}
// The list omits transcripts. Fetch them once per open: search reaches them,
// and older calls whose transcript is only filler ("אההה") drop out of the
// ruler (isNoSpeech) — they were never real conversations.
function prefetchTranscripts() {
  if (prefetched) return
  prefetched = true
  for (const c of store.calls.filter((x) => x.status === 'done' && !x.segments).slice(0, 40)) store.fetchCall(c.id).catch(() => {})
}
const freshId = ref(null)
const hay = (c) => [c.title, c.summary, c.insights?.tldr, c.transcript_text, ...(c.segments || []).map((s) => s.text)].filter(Boolean).join(' ')
const filtered = computed(() => {
  const q = query.value.trim()
  const shown = store.calls.filter((c) => !isNoSpeech(c)) // empty calls never reach the history
  return q ? shown.filter((c) => hay(c).includes(q)) : shown
})

const counts = computed(() => {
  const shown = store.calls.filter((c) => !isNoSpeech(c) && c.status !== 'failed')
  return {
    total: shown.length,
    working: shown.filter((c) => c.status === 'transcribing' || c.status === 'summarizing').length,
    waiting: shown.filter((c) => c.status === 'uploaded' || c.status === 'queued').length,
  }
})

function dateLabel(iso) {
  const d = new Date(iso || '')
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('he-IL', { day: '2-digit', month: '2-digit' })
}
const items = computed(() => filtered.value.map((c) => ({
  id: c.id,
  label: c.title || (c.status === 'done' && c.error ? c.error : CALL_TERMINAL.has(c.status) ? `שיחה · ${dateLabel(c.created_at)}` : `ממתינה לסיכום · ${dateLabel(c.created_at)}`),
  live: !CALL_TERMINAL.has(c.status),
})))
const activeIdx = ref(0)
// a summary that lands while the studio is open gets one calm line under the orb
watch(() => store.calls.map((c) => c.id + ':' + c.status).join(','), (now, before) => {
  if (!before) return
  const was = new Map(before.split(',').map((x) => x.split(':')))
  for (const c of store.calls) {
    if (c.status === 'done' && was.has(c.id) && was.get(c.id) !== 'done' && !isNoSpeech(c)) {
      store.showNotice(`הסיכום מוכן · ${c.title || 'שיחה'}`)
    }
  }
})
watch(() => filtered.value.length, () => { if (activeIdx.value > filtered.value.length - 1) activeIdx.value = 0 })

// ── the iPhone-style open ──
const morph = useOriginMorph()
const detailOpen = ref(false)
const detailId = ref(null)
const detailCall = computed(() => store.calls.find((c) => c.id === detailId.value) || null)
async function openDetail(i, el) {
  const c = filtered.value[i]
  if (!c) return
  detailId.value = c.id
  morph.remember(el)
  detailOpen.value = true
  await nextTick()
  morph.grow(detailEl.value)
  try {
    const full = await store.fetchCall(c.id)
    if (!CALL_TERMINAL.has(full.status)) store.pollCall(c.id)
  } catch (_) { /* keep the list version */ }
}
// opened from elsewhere (Nifra Agent's "לסיכום המלא"): straight to that call
async function openById(id) {
  store.openCallId = null
  if (!id) return
  detailId.value = id
  morph.remember(null)
  detailOpen.value = true
  try {
    const full = await store.fetchCall(id)
    if (!CALL_TERMINAL.has(full.status)) store.pollCall(id)
  } catch (_) { /* keep the list version */ }
}
watch(() => [props.open, store.openCallId], ([o, id]) => { if (o && id) nextTick(() => openById(id)) }, { immediate: true })

async function closeDetail() {
  if (!detailOpen.value) return
  await morph.shrink(detailEl.value)
  detailOpen.value = false
  detailId.value = null
}
async function onPersonal(id, block) {
  detailOpen.value = false
  detailId.value = null
  await store.markPersonal(id, block)
  store.showNotice(block ? 'השיחה הוסתרה, והמספר לא יעלה שוב' : 'השיחה הוסתרה')
}
async function onDelete(id) {
  if (!window.confirm('למחוק את השיחה, התמליל והסיכום?')) return
  detailOpen.value = false
  detailId.value = null
  await store.deleteCall(id)
}

// ── motion: start (dip → swell + one ripple), stop (exhale + a pulse to the ruler) ──
const reducedMotion = !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
const orbEl = ref(null)
const bandEl = ref(null)
const motionClass = ref('')
let motionTimer = null
function playClass(name, ms) {
  if (reducedMotion) return
  motionClass.value = ''
  requestAnimationFrame(() => {
    motionClass.value = name
    clearTimeout(motionTimer)
    motionTimer = setTimeout(() => { motionClass.value = '' }, ms)
  })
}
function pulseToRuler() {
  if (reducedMotion || !orbEl.value || !bandEl.value || !rootEl.value) return
  const a = orbEl.value.getBoundingClientRect()
  const b = bandEl.value.getBoundingClientRect()
  const dot = document.createElement('span')
  dot.className = 'cs-travel'
  rootEl.value.appendChild(dot)
  const x = a.left + a.width / 2 - 7
  const y0 = a.top + a.height / 2 - 7
  const y1 = b.top + 40
  dot.animate(
    [
      { transform: `translate(${x}px, ${y0}px) scale(1.6)`, opacity: 0 },
      { transform: `translate(${x}px, ${y0 + 40}px) scale(1)`, opacity: 1, offset: 0.2 },
      { transform: `translate(${x}px, ${y1}px) scale(0.6)`, opacity: 0.9, offset: 0.85 },
      { transform: `translate(${x}px, ${y1}px) scale(2.4)`, opacity: 0 },
    ],
    { duration: 900, easing: 'cubic-bezier(0.32, 0.72, 0, 1)' },
  ).finished.finally(() => dot.remove())
}
watch(phase, (now, before) => {
  if (now === 'recording' && before !== 'recording') playClass('cs-orb--start', 750)
  if (before === 'recording' && now !== 'recording') { playClass('cs-orb--stop', 700); setTimeout(pulseToRuler, 120) }
})

// ── open/close: the studio grows out of the home widget and folds back into it ──
function widgetCircle() {
  const w = document.querySelector('.cw-ring')
  if (!w) return null
  const r = w.getBoundingClientRect()
  if (!r.width) return null
  return { cx: r.left + r.width / 2, cy: r.top + r.height / 2, r: r.width / 2 }
}
const FULL = () => Math.hypot(window.innerWidth, window.innerHeight)
function onEnter(el, done) {
  const c = widgetCircle()
  if (reducedMotion || !c) { el.animate([{ opacity: 0 }, { opacity: 1 }], { duration: reducedMotion ? 1 : 300 }).finished.then(done); return }
  el.animate(
    [{ clipPath: `circle(${c.r}px at ${c.cx}px ${c.cy}px)`, opacity: 0.6 }, { clipPath: `circle(${FULL()}px at ${c.cx}px ${c.cy}px)`, opacity: 1 }],
    { duration: 560, easing: 'cubic-bezier(0.32, 0.72, 0, 1)' },
  ).finished.then(done)
}
function onLeave(el, done) {
  const c = widgetCircle()
  if (reducedMotion || !c) { el.animate([{ opacity: 1 }, { opacity: 0 }], { duration: reducedMotion ? 1 : 220 }).finished.then(done); return }
  el.animate(
    [{ clipPath: `circle(${FULL()}px at ${c.cx}px ${c.cy}px)`, opacity: 1 }, { clipPath: `circle(${c.r}px at ${c.cx}px ${c.cy}px)`, opacity: 0.4 }],
    { duration: 420, easing: 'cubic-bezier(0.4, 0, 0.6, 1)', fill: 'forwards' },
  ).finished.then(done)
}

function close() {
  // closing while recording = minimizing: the recorder lives in the store,
  // so it keeps going; the home widget shows it (live orb, timer, red dot)
  detailOpen.value = false
  searchOpen.value = false
  query.value = ''
  consentOpen.value = false
  emit('update:open', false)
}
// Escape on the window: a button that disables itself drops focus to <body>
function onKey(e) {
  if (e.key !== 'Escape') return
  if (detailOpen.value) closeDetail()
  else if (consentOpen.value) consentOpen.value = false
  else close()
}
watch(() => props.open, (o) => {
  if (o) {
    emit('seen')
    prefetchTranscripts()
    canvasDark.value = document.documentElement.dataset.canvas === 'dark'
    document.documentElement.style.overflow = 'hidden'
    window.addEventListener('keydown', onKey)
    nextTick(() => rootEl.value?.focus?.())
  } else {
    window.removeEventListener('keydown', onKey)
  }
}, { immediate: true })
function onAfterLeave() { document.documentElement.style.overflow = '' }
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.cs {
  position: fixed; inset: 0; z-index: 1500; outline: none; overflow: hidden;
  display: flex; flex-direction: column;
  background: var(--app-canvas); color: var(--on-canvas, var(--text)); font-family: 'Heebo', sans-serif;
}
.cs-top { display: flex; align-items: center; gap: 12px; padding: 20px 28px; }
.cs-fill { flex: 1; }
/* status capsule: one quiet glass pill, three thick numbers */
.cs-stats { display: flex; align-items: center; margin: 0; padding: 10px 6px; border-radius: 22px;
  background: rgba(255, 255, 255, 0.045); border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.05) inset, 0 10px 30px rgba(0, 0, 0, 0.18); }
.cs-stat { display: flex; flex-direction: column; align-items: center; gap: 6px; min-width: 92px; padding: 0 18px; }
.cs-stat-sep { width: 1px; height: 38px; background: linear-gradient(transparent, rgba(255, 255, 255, 0.14), transparent); }
.cs-stat dd { margin: 0; height: 34px; overflow: hidden; font-size: 34px; line-height: 34px; font-weight: 900; letter-spacing: -0.04em;
  color: var(--on-canvas, var(--text)); font-variant-numeric: tabular-nums; }
.cs-stat dd span { display: inline-block; }
.cs-stat dt { display: inline-flex; align-items: center; gap: 5px; font-size: 11.5px; font-weight: 700; letter-spacing: 0.02em;
  color: rgba(242, 240, 243, 0.55); }
.cs-stat dt svg { opacity: 0.8; }
.cs-stat--working dd, .cs-stat--waiting dd { color: rgba(242, 240, 243, 0.28); transition: color 0.35s ease; }
.cs-stat--working.is-on dd { color: #E58AC6; text-shadow: 0 0 18px rgba(217, 106, 181, 0.45); }
.cs-stat--working.is-on dt { color: #E58AC6; }
.cs-stat--waiting.is-on dd { color: #C9B8F0; }
.cs-stat--waiting.is-on dt { color: #C9B8F0; }
.cs-spin { animation: none; }
.cs-stat--working.is-on .cs-spin { animation: csSpin 1.1s linear infinite; }
@keyframes csSpin { to { transform: rotate(360deg); } }
/* a changed number rolls in from below */
.cs-num-enter-active { transition: transform 0.32s cubic-bezier(0.32, 0.72, 0, 1), opacity 0.32s ease; }
.cs-num-leave-active { transition: transform 0.18s ease, opacity 0.18s ease; }
.cs-num-enter-from { transform: translateY(70%); opacity: 0; }
.cs-num-leave-to { transform: translateY(-70%); opacity: 0; }
.cs-mark { font-size: 18px; font-weight: 800; letter-spacing: -0.02em; color: var(--on-canvas, var(--text)); }
.cs-mark b { font-weight: 800; color: #D96AB5; }
.cs-icon {
  width: 40px; height: 40px; border-radius: 50%; border: none; display: grid; place-items: center; cursor: pointer; flex: none;
  color: var(--on-canvas, var(--text)); background: color-mix(in srgb, var(--on-canvas, #181818) 8%, transparent);
}
.cs-icon:hover { background: color-mix(in srgb, var(--on-canvas, #181818) 14%, transparent); }
.cs-icon:focus-visible { outline: 2px solid #D96AB5; outline-offset: 2px; }
.cs-icon--sm { width: 34px; height: 34px; }

.cs-stage { flex: 1; min-height: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px; position: relative; }
.cs-orb { position: relative; display: grid; place-items: center; padding: 0; border: none; background: none; border-radius: 50%; cursor: pointer; transition: transform 0.3s ease; }
.cs-orb:hover:not(:disabled), .cs-orb:focus-visible { --hov: 1; }
.cs-orb:active:not(:disabled) { transform: scale(0.985); }
.cs-orb:disabled { cursor: progress; }
.cs-orb:focus-visible { outline: 2px solid #D96AB5; outline-offset: 12px; }
.cs-ripple { position: absolute; inset: 0; border-radius: 50%; border: 2px solid rgba(217, 106, 181, 0.6); pointer-events: none; animation: csRipple 0.9s ease-out forwards; }
@keyframes csRipple { from { transform: scale(0.96); opacity: 0.9; } to { transform: scale(1.3); opacity: 0; } }
.cs-orb--start { animation: csStart 0.75s cubic-bezier(0.34, 1.4, 0.5, 1); }
@keyframes csStart { 0% { transform: scale(1); } 30% { transform: scale(0.94); } 70% { transform: scale(1.035); } 100% { transform: scale(1); } }
.cs-orb--stop { animation: csStop 0.7s cubic-bezier(0.32, 0.72, 0, 1); }
@keyframes csStop { 0% { transform: scale(1); } 40% { transform: scale(0.955); } 100% { transform: scale(1); } }
.cs-glyph-enter-active, .cs-glyph-leave-active { transition: opacity 0.18s ease, transform 0.22s cubic-bezier(0.34, 1.4, 0.5, 1); }
.cs-glyph-enter-from { opacity: 0; transform: scale(0.5) rotate(-45deg); }
.cs-glyph-leave-to { opacity: 0; transform: scale(0.6); }
.cs-status-slot { min-height: 26px; display: grid; place-items: center; }
.cs-status-enter-active { transition: opacity 0.3s ease, transform 0.35s cubic-bezier(0.32, 0.72, 0, 1); }
.cs-status-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.cs-status-enter-from { opacity: 0; transform: translateY(10px); }
.cs-status-leave-to { opacity: 0; transform: translateY(-6px); }
.cs-status--notice { color: var(--on-canvas, var(--text)); }
.cs-fade-enter-active, .cs-fade-leave-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.cs-fade-enter-from, .cs-fade-leave-to { opacity: 0; transform: scale(0.8); }
:deep(.cs-travel), .cs :deep(.cs-travel) { position: fixed; top: 0; left: 0; width: 14px; height: 14px; border-radius: 50%; background: #D96AB5; box-shadow: 0 0 16px rgba(217, 106, 181, 0.8); pointer-events: none; z-index: 5; }
/* the glyph sits in a small tinted disc so it reads on the light orb */
.cs-glyph { position: absolute; width: 68px; height: 68px; border-radius: 50%; color: #fff; display: grid; place-items: center; pointer-events: none;
  background: rgba(120, 28, 92, 0.30); box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.35), 0 6px 18px rgba(110, 30, 85, 0.25);
  backdrop-filter: blur(2px); transition: transform 0.45s cubic-bezier(0.34, 1.45, 0.5, 1), background 0.3s ease; }
.cs-orb:hover:not(:disabled) .cs-glyph, .cs-orb:focus-visible .cs-glyph { transform: scale(1.14); background: rgba(120, 28, 92, 0.48); }
.cs-orb--recording .cs-glyph { background: rgba(120, 28, 92, 0.42); }
.cs-hint { color: rgba(242, 240, 243, 0.7); }
.cs-status {
  margin: 0; min-height: 22px; display: inline-flex; align-items: center; gap: 8px;
  font-size: 15px; font-weight: 600; color: var(--on-canvas-muted, var(--text-secondary)); font-variant-numeric: tabular-nums;
}
.cs-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--red); animation: csBlink 1.2s ease-in-out infinite; }
@keyframes csBlink { 50% { opacity: 0.25; } }
.cs-consent {
  position: absolute; top: calc(50% + 190px); display: flex; flex-direction: column; gap: 10px; padding: 14px 16px;
  border-radius: 14px; background: var(--card-bg); color: var(--text); box-shadow: 0 16px 40px rgba(0, 0, 0, 0.25); font-size: 14px;
}
.cs-consent label { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
.cs-consent input { width: 16px; height: 16px; accent-color: #A63A86; }
.cs-consent-actions { display: flex; gap: 8px; }
.cs-go { flex: 1; border: none; border-radius: 10px; padding: 8px 14px; font: inherit; font-weight: 700; color: #fff; background: #181818; cursor: pointer; }
.cs-go:disabled { opacity: 0.4; cursor: not-allowed; }
.cs-ghost { border: none; background: none; font: inherit; color: var(--text-secondary); padding: 8px 10px; border-radius: 10px; cursor: pointer; }
.cs-ghost:hover { background: var(--bg); }
.cs-pop-enter-active, .cs-pop-leave-active { transition: opacity 0.25s ease, transform 0.25s ease; }
.cs-pop-enter-from, .cs-pop-leave-to { opacity: 0; transform: translateY(6px); }
.cs-err { margin: 0; color: #E8707F; font-size: 14px; }

.cs-band { position: relative; padding: 8px 28px 22px; }
.cs-band-tools { position: absolute; top: 4px; right: 28px; z-index: 2; display: flex; align-items: center; gap: 8px; }
.cs-search {
  width: min(260px, 52vw); height: 34px; padding: 0 14px; border-radius: 999px; border: 1px solid color-mix(in srgb, var(--on-canvas, #181818) 20%, transparent);
  background: var(--app-canvas); color: var(--on-canvas, var(--text)); font: inherit; font-size: 14px; outline: none;
}
.cs-search:focus { border-color: #D96AB5; }
.cs-search::-webkit-search-cancel-button { -webkit-appearance: none; appearance: none; }
.cs-empty { margin: 30px 0; text-align: center; font-size: 15px; color: var(--on-canvas-muted, var(--text-muted)); }

/* the opened call */
.cs-scrim { position: fixed; inset: 0; z-index: 3; background: rgba(12, 10, 14, 0.45); animation: csFade 0.35s ease both; }
@keyframes csFade { from { opacity: 0; } }
.cs-detail {
  position: fixed; inset: 20px max(20px, calc((100vw - 1200px) / 2)); z-index: 4; display: flex; flex-direction: column;
  background: var(--card-bg); color: var(--text); border-radius: 24px; overflow: hidden; box-shadow: 0 30px 90px rgba(0, 0, 0, 0.35);
}
.cs-detail-bar { display: flex; align-items: center; gap: 10px; padding: 12px 16px; border-bottom: 1px solid var(--border-subtle); }
.cs-back { display: inline-flex; align-items: center; gap: 6px; border: none; background: none; color: var(--text); font: inherit; font-size: 14px; font-weight: 600; padding: 8px 10px; border-radius: 10px; cursor: pointer; }
.cs-back:hover { background: var(--bg); }
.cs-del { border: none; background: none; font: inherit; font-size: 13px; color: var(--text-muted); padding: 6px 10px; border-radius: 8px; cursor: pointer; }
.cs-del:hover { color: var(--red); background: rgba(234, 0, 30, 0.06); }
.cs-detail-body { flex: 1; overflow-y: auto; padding: 28px 32px 36px; }

.cs-swap-enter-active, .cs-swap-leave-active { transition: opacity 0.3s ease; }
.cs-swap-enter-from, .cs-swap-leave-to { opacity: 0; }

@media (max-width: 699px) {
  .cs-top { padding: 14px 16px; }
  .cs-stats { padding: 7px 2px; border-radius: 18px; }
  .cs-stat { min-width: 0; padding: 0 10px; gap: 4px; }
  .cs-stat-sep { height: 28px; }
  .cs-stat dd { font-size: 24px; height: 26px; line-height: 26px; }
  .cs-stat dt { font-size: 10.5px; }
  .cs-stat dt svg { display: none; }
  .cs-band { padding: 8px 12px 16px; }
  .cs-band-tools { right: 12px; }
  .cs-consent { top: calc(50% + 130px); }
  .cs-detail { inset: 0; border-radius: 0; }
  .cs-detail-body { padding: 18px 16px 28px; }
}
@media (prefers-reduced-motion: reduce) {
  .cs-dot, .cs-ripple, .cs-orb--start, .cs-orb--stop { animation: none; }
  .cs-orb, .cs-glyph-enter-active, .cs-glyph-leave-active, .cs-status-enter-active, .cs-status-leave-active, .cs-num-enter-active, .cs-num-leave-active { transition: none; }
  .cs-stat--working.is-on .cs-spin { animation: none; }
}
</style>
