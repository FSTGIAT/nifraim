<template>
  <!-- Production tab before the agent's FIRST monthly cycle. Only this tab is
       locked (the rest of the app is open): nothing to upload yet — the first
       cycle's נפרעים decide which month the first production must describe.
       Truth lives on the server (GET /api/cycle/status). -->
  <section class="cl">
    <div class="cl-circles" aria-hidden="true">
      <span class="cl-c cl-c-1"></span><span class="cl-c cl-c-2"></span>
      <span class="cl-c cl-c-3"></span><span class="cl-c cl-c-4"></span>
      <span class="cl-c cl-c-5"></span>
    </div>

    <header class="cl-hero">
      <!-- Integrated photo: blurred, dissolving into the card under the text
           (subject on the left, the empty wall carries the copy). -->
      <div v-if="heroPhoto" class="cl-hero-photo" aria-hidden="true">
        <img :src="heroPhoto" alt="" />
      </div>
      <span class="cl-kicker">פרודוקציה</span>
      <h2 class="cl-title">הכל מתחיל ב-<span class="ltr-number">{{ firstShort }}</span><br><span class="cl-title-acc">המחזור הראשון שלך</span></h2>
      <p class="cl-sub">
        Nifraim עובד במחזור חודשי. ב-<span class="ltr-number">{{ firstShort }}</span> בשעה 06:00 נוריד לבד את
        הנפרעים של {{ firstPeriodName }} מכל החברות — ומאותו רגע לשונית הפרודוקציה נפתחת.
      </p>

      <!-- Remotion: live countdown + hand-drawn "how the month works" strip -->
      <CycleCountdownIsland
        v-if="cycle.status?.first_cycle_at"
        class="cl-remotion"
        :target-iso="cycle.status.first_cycle_at"
        :period-name="firstPeriodName"
        heading="לשונית הפרודוקציה נפתחת בעוד"
        :compact="narrow"
      />
    </header>

    <div class="cl-grid">
      <!-- what will happen -->
      <div class="cl-card">
        <h3 class="cl-card-title">מה יקרה עכשיו</h3>
        <ol class="cl-timeline">
          <li v-if="signup" class="cl-tl cl-tl--done">
            <span class="cl-tl-dot"></span>
            <div class="cl-tl-body">
              <strong>{{ signup }}</strong>
              <span>ההרשמה נשמרה — ממנה נקבע המחזור הראשון שלכם.</span>
            </div>
          </li>
          <li class="cl-tl" :class="{ 'cl-tl--done': setup.allDone.value }">
            <span class="cl-tl-dot"></span>
            <div class="cl-tl-body">
              <strong>עד אז — מתכוננים</strong>
              <span>טלפון, מחשב, פורטלים ושיוך למסלקה. פעם אחת, וזהו.</span>
            </div>
          </li>
          <li class="cl-tl" :class="{ 'cl-tl--done': maslakaSigned }">
            <span class="cl-tl-dot"></span>
            <div class="cl-tl-body">
              <strong>{{ mas ? mas.title : 'טופס שיוך למסלקה' }}</strong>
              <span v-if="mas && mas.sub">{{ mas.sub }}</span>
              <span class="cl-rule">{{ MASLAKA_RULE }}</span>
            </div>
          </li>
          <li class="cl-tl">
            <span class="cl-tl-dot"></span>
            <div class="cl-tl-body">
              <strong><span class="ltr-number">{{ firstShort }}</span> · 06:00 — הנפרעים יורדים</strong>
              <span>הנפרעים של {{ firstPeriodName }} מכל החברות, בלי ללחוץ על כלום.</span>
            </div>
          </li>
          <li class="cl-tl">
            <span class="cl-tl-dot"></span>
            <div class="cl-tl-body">
              <strong>ההשוואה מוכנה</strong>
              <span v-if="firstIsAuto">פרודוקציה מול נפרעים — אוטומטית, כל חודש.</span>
              <span v-else>מעלים את הפרודוקציה של {{ firstPeriodName }} (מאתר המסלקה), וההשוואה רצה. מהחודש שאחרי — הכל אוטומטי.</span>
            </div>
          </li>
        </ol>
      </div>

      <!-- readiness checklist (same steps as the setup wizard) -->
      <div class="cl-card">
        <h3 class="cl-card-title">
          מוכנות למחזור
          <span class="cl-progress ltr-number">{{ setup.completedCount.value }}/{{ setup.steps.value.length }}</span>
        </h3>
        <ul class="cl-check">
          <li v-for="s in setup.steps.value" :key="s.id">
            <button type="button" class="cl-step" :class="{ 'cl-step--done': s.done }" @click="onStep(s)">
              <span class="cl-step-mark" aria-hidden="true">
                <svg v-if="s.done" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
              </span>
              <span class="cl-step-title"><StepTitle :title="s.title" /></span>
              <span v-if="!s.done && s.id !== 'run'" class="cl-step-go">
                השלמה
                <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 18l-6-6 6-6"/></svg>
              </span>
              <span v-else-if="s.id === 'run' && !s.done" class="cl-step-when ltr-number">{{ firstShort }}</span>
            </button>
          </li>
        </ul>
        <p class="cl-note">
          המחשב צריך להיות דלוק ב-<span class="ltr-number">{{ firstShort }}</span>. אם הוא כבוי — ההורדה תחכה ותתחיל
          לבד ברגע שיחזור, ונעדכן אותך במייל.
        </p>
      </div>
    </div>

    <div class="cl-waves" aria-hidden="true">
      <svg class="cl-wave cl-wave-1" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs><linearGradient id="clwg1" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="#2F73C4" stop-opacity="0.10"/><stop offset="100%" stop-color="#2F73C4" stop-opacity="0.02"/>
        </linearGradient></defs>
        <path fill="url(#clwg1)" d="M0,120 C240,80 480,160 720,120 C960,80 1200,150 1440,110 L1440,200 L0,200 Z"/>
      </svg>
      <svg class="cl-wave cl-wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs><linearGradient id="clwg2" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="#2F73C4" stop-opacity="0.08"/><stop offset="100%" stop-color="#2F73C4" stop-opacity="0.02"/>
        </linearGradient></defs>
        <path fill="url(#clwg2)" d="M0,140 C300,110 540,180 840,140 C1100,105 1300,165 1440,140 L1440,200 L0,200 Z"/>
      </svg>
      <svg class="cl-wave cl-wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
        <defs><linearGradient id="clwg3" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="#2F73C4" stop-opacity="0.12"/><stop offset="100%" stop-color="#2F73C4" stop-opacity="0.04"/>
        </linearGradient></defs>
        <path fill="url(#clwg3)" d="M0,165 C260,145 520,190 780,165 C1040,140 1260,185 1440,160 L1440,200 L0,200 Z"/>
      </svg>
      <div class="cl-shimmer"></div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useCycleStore, monthName, shortDate, signupLine, maslakaLine, MASLAKA_RULE } from '../../stores/cycle.js'
import { useSetupPipeline } from '../../composables/useSetupPipeline.js'
import { openSetup } from '../../utils/setupState.js'
import CycleCountdownIsland from './CycleCountdownIsland.vue'
import StepTitle from './StepTitle.vue'

const emit = defineEmits(['go-to-portal-automation', 'go-to-maslaka'])
const heroPhoto = Object.values(
  import.meta.glob('../../assets/welcome/production-cycle.webp', { eager: true, import: 'default' }),
)[0] || ''
const cycle = useCycleStore()
const setup = useSetupPipeline()

const now = ref(Date.now())
let timer = null
// Phones: the hand-drawn strip is unreadable at that scale — digits only
// (the timeline card below tells the same story in text).
const narrow = ref(typeof window !== 'undefined' && window.innerWidth < 640)
const onResize = () => { narrow.value = window.innerWidth < 640 }
onMounted(() => {
  window.addEventListener('resize', onResize)
  setup.bootstrap()
  timer = setInterval(() => {
    now.value = Date.now()
    // The moment the first cycle fires, ask the server — it unlocks the tab.
    if (firstAt.value && now.value >= firstAt.value.getTime()) cycle.fetchStatus()
  }, 30000)
})
onBeforeUnmount(() => {
  clearInterval(timer)
  window.removeEventListener('resize', onResize)
})

const firstAt = computed(() => (cycle.status?.first_cycle_at ? new Date(cycle.status.first_cycle_at) : null))
const firstShort = computed(() => shortDate(cycle.status?.first_cycle_at))

function monthBefore(iso) {
  const d = new Date(iso)
  return monthName(new Date(d.getFullYear(), d.getMonth() - 1, 1).toISOString())
}
const firstPeriodName = computed(() => (cycle.status?.first_cycle_at ? monthBefore(cycle.status.first_cycle_at) : ''))

const signup = computed(() => signupLine(cycle.status))
const mas = computed(() => maslakaLine(cycle.status))
const maslakaFirst = computed(() => cycle.status?.maslaka_first_auto || null)
const maslakaSigned = computed(() => ['submitted', 'approved'].includes(cycle.status?.maslaka_status))
// The מסלקה production for the first cycle's period lands by the 15th of the
// first cycle's month → no manual upload even in cycle 1.
const firstIsAuto = computed(() => {
  // Plain YYYY-MM-DD comparison: Date objects here would mix UTC and the
  // browser's zone and flip the verdict around midnight.
  const first = cycle.status?.first_cycle_at
  if (!maslakaFirst.value || !first) return false
  return maslakaFirst.value <= `${first.slice(0, 7)}-15`
})


function onStep(s) {
  if (s.done) return
  if (s.id === 'maslaka') emit('go-to-maslaka')
  else if (s.id === 'run') emit('go-to-portal-automation')
  else openSetup(s.id)
}
</script>

<style scoped>
.cl { position: relative; display: flex; flex-direction: column; gap: 18px; padding-bottom: 120px; }

/* floating circles — production cobalt */
.cl-circles { position: fixed; inset: 0; pointer-events: none; z-index: 0; overflow: hidden; }
.cl-c { position: absolute; border-radius: 50%; background: rgba(47, 115, 196, 0.05); border: 1px solid rgba(47, 115, 196, 0.06); }
.cl-c-1 { width: 220px; height: 220px; top: 14%; left: -60px; animation: clFloat 9s ease-in-out infinite; }
.cl-c-2 { width: 90px; height: 90px; top: 30%; left: 22%; animation: clFloat 7s ease-in-out infinite reverse; }
.cl-c-3 { width: 140px; height: 140px; top: 60%; right: 5%; animation: clFloat 10s ease-in-out infinite 1s; }
.cl-c-4 { width: 50px; height: 50px; top: 20%; right: 24%; background: rgba(47, 115, 196, 0.08); animation: clFloat 6.5s ease-in-out infinite 2s; }
.cl-c-5 { width: 300px; height: 300px; bottom: 6%; right: -110px; background: rgba(47, 115, 196, 0.03); animation: clFloat 12s ease-in-out infinite 0.5s; }
@keyframes clFloat {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  33% { transform: translateY(-16px) rotate(2deg); }
  66% { transform: translateY(8px) rotate(-1deg); }
}

.cl-hero, .cl-grid { position: relative; z-index: 1; }
.cl-hero {
  position: relative; overflow: hidden;
  display: flex; flex-direction: column; gap: 10px; padding: 26px 28px;
  background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-md, 14px);
  box-shadow: var(--shadow-sm);
}
.cl-hero > :not(.cl-hero-photo) { position: relative; z-index: 1; }
.cl-hero-photo { position: absolute; top: 0; bottom: 0; left: 0; width: 58%; z-index: 0; pointer-events: none; }
.cl-hero-photo img {
  width: 100%; height: 100%; object-fit: cover; object-position: 8% 40%;
  filter: blur(10px) saturate(0.9);
  transform: scale(1.08);            /* hide the blur's soft edge */
  opacity: 0.5;
  /* visible on the left (the clock + calendar), dissolving under the copy */
  -webkit-mask-image: linear-gradient(to right, #000 0%, rgba(0, 0, 0, 0.7) 40%, transparent 100%);
  mask-image: linear-gradient(to right, #000 0%, rgba(0, 0, 0, 0.7) 40%, transparent 100%);
}
/* soft white wash so the digits and the drawn strip stay crisp */
.cl-hero-photo::after {
  content: ''; position: absolute; inset: 0;
  background: radial-gradient(70% 60% at 90% 55%, rgba(255, 255, 255, 0.6), rgba(255, 255, 255, 0) 70%);
}
@media (max-width: 640px) { .cl-hero-photo { width: 100%; } .cl-hero-photo img { opacity: 0.35; } }
.cl-kicker {
  align-self: flex-start; padding: 4px 11px; border-radius: 999px; font-size: 11.5px; font-weight: 800;
  background: var(--tab-production-wash); color: var(--tab-production);
}
.cl-title { margin: 0; font-size: clamp(28px, 3.4vw, 42px); font-weight: 900; letter-spacing: -0.03em; line-height: 1.12; color: var(--text-primary, #181818); }
.cl-title-acc { color: var(--tab-production); }
.cl-sub { margin: 0; max-width: 62ch; font-size: 15px; line-height: 1.7; color: var(--text-secondary, #3E3E3C); }

.cl-remotion { width: 100%; max-width: 860px; align-self: center; margin-top: 4px; }

.cl-grid { position: relative; z-index: 1; }
.cl-hero {
  display: flex; flex-direction: column; gap: 10px; padding: 26px 28px;
  background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-md, 14px);
  box-shadow: var(--shadow-sm);
}
.cl-kicker {
  align-self: flex-start; padding: 4px 11px; border-radius: 999px; font-size: 11.5px; font-weight: 800;
  background: var(--tab-production-wash); color: var(--tab-production);
}
.cl-title { margin: 0; font-size: clamp(28px, 3.4vw, 42px); font-weight: 900; letter-spacing: -0.03em; line-height: 1.12; color: var(--text-primary, #181818); }
.cl-title-acc { color: var(--tab-production); }
.cl-sub { margin: 0; max-width: 62ch; font-size: 15px; line-height: 1.7; color: var(--text-secondary, #3E3E3C); }

.cl-count { display: flex; align-items: flex-end; gap: 10px; margin-top: 8px; direction: ltr; align-self: flex-start; }
.cl-unit { display: flex; flex-direction: column; align-items: center; gap: 2px; min-width: 64px; }
.cl-num { font-size: clamp(34px, 4vw, 48px); font-weight: 900; line-height: 1; color: var(--tab-production); font-variant-numeric: tabular-nums; }
.cl-lbl { font-size: 12px; font-weight: 700; color: var(--text-secondary, #706E6B); }
.cl-sep { font-size: 32px; font-weight: 800; color: rgba(47, 115, 196, 0.35); padding-bottom: 18px; }

.cl-grid { display: grid; grid-template-columns: 1.15fr 1fr; gap: 18px; }
@media (max-width: 860px) { .cl-grid { grid-template-columns: 1fr; } }
.cl-card {
  display: flex; flex-direction: column; gap: 14px; padding: 22px 24px;
  background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-md, 14px);
  box-shadow: var(--shadow-sm);
}
.cl-card-title { margin: 0; display: flex; align-items: center; gap: 10px; font-size: 16px; font-weight: 800; color: var(--text-primary, #181818); }
.cl-progress { font-size: 12px; font-weight: 800; padding: 2px 9px; border-radius: 999px; background: var(--tab-production-wash); color: var(--tab-production); }

.cl-timeline { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
.cl-tl { position: relative; display: flex; gap: 14px; padding-bottom: 18px; }
.cl-tl:last-child { padding-bottom: 0; }
.cl-tl::before {
  content: ''; position: absolute; inset-inline-start: 7px; top: 18px; bottom: 0; width: 2px;
  background: rgba(47, 115, 196, 0.18);
}
.cl-tl:last-child::before { display: none; }
.cl-tl-dot {
  flex-shrink: 0; width: 16px; height: 16px; margin-top: 3px; border-radius: 50%;
  background: #fff; border: 2.5px solid var(--tab-production);
}
.cl-tl--done .cl-tl-dot { background: var(--green, #2E844A); border-color: var(--green, #2E844A); }
.cl-tl-body { display: flex; flex-direction: column; gap: 3px; min-width: 0; }
.cl-tl-body strong { font-size: 14.5px; font-weight: 800; color: var(--text-primary, #181818); }
.cl-tl-body span { font-size: 13.5px; line-height: 1.6; color: var(--text-secondary, #706E6B); }

.cl-check { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.cl-step {
  width: 100%; display: flex; align-items: center; gap: 12px; padding: 11px 14px;
  border: 1px solid var(--border-subtle); border-radius: 10px; background: #fff;
  font-family: inherit; font-size: 14px; color: var(--text-primary, #181818); cursor: pointer; text-align: start;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.cl-step:hover:not(.cl-step--done) { border-color: var(--tab-production); background: var(--tab-production-wash); }
.cl-step--done { cursor: default; color: var(--text-secondary, #706E6B); }
.cl-step-mark {
  flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  border: 2px solid rgba(47, 115, 196, 0.35); color: #fff;
}
.cl-step--done .cl-step-mark { background: var(--green, #2E844A); border-color: var(--green, #2E844A); }
.cl-step-title { flex: 1; font-weight: 700; }
.cl-rule { display: block; margin-top: 3px; font-size: 12px !important; color: var(--text-secondary, #8A8784) !important; }
.cl-step-go { display: inline-flex; align-items: center; gap: 4px; font-size: 12.5px; font-weight: 800; color: var(--tab-production); }
.cl-step-when { font-size: 12.5px; font-weight: 800; color: var(--tab-production); }
.cl-note { margin: 0; font-size: 13px; line-height: 1.6; color: var(--text-secondary, #706E6B); }

/* waves */
.cl-waves { position: fixed; left: 0; right: 0; bottom: 0; height: 180px; pointer-events: none; z-index: 0; overflow: hidden; }
.cl-wave { position: absolute; bottom: -12px; left: 0; width: 100%; height: 100%; }
.cl-wave-1 { animation: clWave 9s ease-in-out infinite; }
.cl-wave-2 { animation: clWave 7s ease-in-out infinite reverse; }
.cl-wave-3 { animation: clWave 11s ease-in-out infinite 1s; }
@keyframes clWave { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(10px); } }
.cl-shimmer {
  position: absolute; inset: 0;
  background: linear-gradient(100deg, transparent 30%, rgba(255, 255, 255, 0.35) 50%, transparent 70%);
  background-size: 200% 100%;
  animation: clShimmer 7s ease-in-out infinite;
  -webkit-mask-image: linear-gradient(to top, #000 55%, transparent);
  mask-image: linear-gradient(to top, #000 55%, transparent);
}
@keyframes clShimmer { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

@media (prefers-reduced-motion: reduce) {
  .cl-c, .cl-wave, .cl-shimmer { animation: none; }
}
</style>
