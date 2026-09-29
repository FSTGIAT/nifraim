<template>
  <Teleport to="body">
    <Transition name="spm">
      <div v-if="setupState.modalOpen" ref="overlayEl" class="spm-overlay" :class="{ 'spm-overlay--morph': morphing }" @click.self="close">
        <div
          ref="cardEl"
          class="spm-card"
          dir="rtl"
          role="dialog"
          aria-modal="true"
          aria-labelledby="spm-title"
          @keydown.escape="close"
        >
          <button class="spm-close" aria-label="סגור" @click="close">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>

          <div class="spm-layout">
            <!-- ── MAIN (right pane in RTL): header + steps ── -->
            <div class="spm-main">
              <header class="spm-top">
                <h2 id="spm-title" class="spm-welcome">ברוכים הבאים ל-<span class="spm-title-brand" dir="ltr">Nifraim</span></h2>
                <!-- compact step bar: jump to any page -->
                <nav class="spm-stepper" aria-label="צעדי ההפעלה">
                  <template v-for="(st, i) in steps" :key="st.id">
                    <span v-if="i" class="spm-stepper-line" :class="{ 'spm-stepper-line--done': steps[i - 1].done }"></span>
                    <button
                      type="button"
                      class="spm-dot"
                      :class="{ 'spm-dot--on': st.id === selectedId, 'spm-dot--done': st.done }"
                      :style="dotStyle(st)"
                      :title="st.title"
                      :aria-label="st.title"
                      :aria-current="st.id === selectedId ? 'step' : undefined"
                      @click="select(st.id)"
                    >
                      <svg v-if="st.done" viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                      <span v-else class="ltr-number">{{ i + 1 }}</span>
                    </button>
                  </template>
                  <span class="spm-stepper-count ltr-number">{{ completedCount }}/{{ steps.length }}</span>
                </nav>
              </header>

              <!-- one PAGE per step -->
              <Transition :name="reducedMotion ? 'spm-fade' : 'spm-page'" mode="out-in">
                <section v-if="current" :key="current.id" class="spm-page">
                  <span class="spm-page-kicker" :style="{ color: activeAccent.deep }">
                    {{ phaseOf(current.id) }} · צעד <span class="ltr-number">{{ pad(stepIndex + 1) }}</span>
                  </span>
                  <h3 class="spm-page-title"><StepTitle :title="current.title" split :accent="activeAccent.deep" /></h3>
                  <p v-if="current.body" class="spm-page-body">{{ current.body }}</p>
                  <div v-if="current.done && !(current.id === 'worker' && justConnected)" class="spm-done">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                    הושלם
                  </div>
                  <div v-else class="spm-page-content">
                      
                      <!-- מדף ההסכמים: email each insurer for the agreement, in place -->
                      <AgreementRequestsPanel
                        v-if="current.id === 'agreements'"
                        @go-mail="select('mail')"
                        @open-shelf="leaveSetupFor('agreements'); emit('open-agreements')"
                        @changed="setup.refreshAgreements()"
                      />
                      <!-- Worker: honest walkthrough + live install telemetry -->
                      <div v-else-if="current.id === 'worker' && justConnected" class="spm-connected" role="status">
                        <span class="spm-connected-icon" aria-hidden="true">
                          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                        </span>
                        <div class="spm-connected-texts">
                          <strong>המחשב מחובר!</strong>
                          <span>ההורדות ירוצו מ-<span class="ltr-number">{{ workerHost || 'המחשב שלך' }}</span>. עוברים לצעד הבא…</span>
                        </div>
                      </div>
                      <template v-else-if="current.id === 'worker'">
                        <div class="spm-mini-steps">
                          <div class="spm-mini-step">
                            <span class="spm-mini-num" :style="{ background: ACCENTS.worker.soft, color: ACCENTS.worker.deep }">1</span>
                            <span>הורידו את קובץ ההתקנה ולחצו עליו פעמיים (בתיקיית ההורדות).</span>
                          </div>
                          <div class="spm-mini-step">
                            <span class="spm-mini-num" :style="{ background: ACCENTS.worker.soft, color: ACCENTS.worker.deep }">2</span>
                            <span>יופיע לרגע חלון שחור קטן, ואחריו <strong>חלון התקנה ירוק</strong>. אם Windows מציג אזהרה — לחצו <code>מידע נוסף</code> ואז <code>הפעל בכל זאת</code>.</span>
                          </div>
                          <div class="spm-mini-step">
                            <span class="spm-mini-num" :style="{ background: ACCENTS.worker.soft, color: ACCENTS.worker.deep }">3</span>
                            <span>ההתקנה אורכת <strong>2–5 דקות</strong>. בסיומה החלון ייסגר לבד והמחוון כאן יהפוך ל"מחובר".</span>
                          </div>
                        </div>

                        <div class="spm-step-actions">
                          <button class="spm-cta" :style="ctaStyle('worker')" :disabled="downloading" @click="onCta(current)">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>
                            {{ downloading ? 'מוריד…' : downloadedOnce ? 'הורד שוב' : current.cta }}
                          </button>
                          <span class="spm-worker-pill" :class="workerOnline ? 'spm-worker-pill--on' : ''">
                            <span class="spm-worker-dot"></span>{{ workerOnline ? 'מחובר' : 'ממתין לחיבור' }}
                          </span>
                        </div>

                        <!-- Live install progress (installer reports to the server) -->
                        <div v-if="installError" class="spm-install spm-install--error">
                          <strong>ההתקנה נעצרה: {{ installError }}</strong>
                          <span v-if="installError.includes('Python')">התקינו Python מ-<a href="https://www.python.org/downloads/" target="_blank" rel="noopener">python.org</a> (סמנו "Add to PATH"), ואז הריצו את הקובץ שוב.</span>
                          <span v-else>הריצו את הקובץ שוב; אם זה חוזר — כתבו לתמיכה ונתחבר לעזור.</span>
                        </div>
                        <div v-else-if="installProgress && !installStalled" class="spm-install">
                          <span class="spm-install-spinner" aria-hidden="true"></span>
                          <div class="spm-install-texts">
                            <strong>{{ installProgress.label }}</strong>
                            <span class="spm-install-bar"><span class="spm-install-fill" :style="{ width: installProgress.pct + '%' }"></span></span>
                          </div>
                        </div>
                        <p v-else-if="workerHint && !stuck && !installStalled" class="spm-hint" :style="{ background: ACCENTS.worker.soft, color: ACCENTS.worker.deep }">{{ workerHint }}</p>

                        <!-- Stuck rescue: no connection despite a download or a finished install -->
                        <div v-if="stuck || installStalled" class="spm-install spm-install--stuck">
                          <strong>{{ installStalled ? 'ההתקנה הסתיימה, אבל המחשב עדיין לא מחובר:' : 'עדיין לא מחובר? ככה פותרים:' }}</strong>
                          <ul>
                            <li>ודאו שלחצתם פעמיים על <code>nifraim-worker-setup.bat</code> בתיקיית ההורדות.</li>
                            <li>הופיע מסך כחול של Windows? לחצו "מידע נוסף" ← "הפעל בכל זאת".</li>
                            <li>לא קרה כלום? לחצו "הורד שוב" ונסו מחדש.</li>
                            <li>עדיין תקוע? כתבו לתמיכה — נתחבר ונתקין ביחד.</li>
                          </ul>
                        </div>
                      </template>

                      <!-- Other steps: single mission CTA -->
                      <template v-else>
                        <p v-if="current.id === 'phone' && redirectNote" class="spm-hint" :style="{ background: ACCENTS.phone.soft, color: ACCENTS.phone.deep }">{{ redirectNote }}</p>
                        <div class="spm-step-actions">
                        <button class="spm-cta" :style="ctaStyle(current.id)" @click="onCta(current)">
                          <svg v-if="current.id === 'phone'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18h2"/></svg>
                          <svg v-else-if="current.id === 'portal'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
                          <svg v-else-if="current.id === 'mail'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/></svg>
                          <svg v-else-if="current.id === 'agreements'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M12 18v-6M9 15l3-3 3 3"/></svg>
                          <svg v-else-if="current.id === 'maslaka'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="m9 15 2 2 4-4"/></svg>
                          <svg v-else-if="current.id === 'run'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>
                          <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 4l14 8-14 8z"/></svg>
                          {{ current.cta }}
                        </button>
                        </div>
                      </template>
                  </div>
                </section>
              </Transition>

              <footer class="spm-nav">
                <button type="button" class="spm-nav-btn" :disabled="stepIndex <= 0" @click="go(-1)">
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M12 5l7 7-7 7"/></svg>
                  הקודם
                </button>
                <button type="button" class="spm-nav-btn spm-nav-btn--next" @click="stepIndex >= steps.length - 1 ? close() : go(1)">
                  {{ stepIndex >= steps.length - 1 ? 'סיום' : 'הבא' }}
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
                </button>
              </footer>
            </div>

            <!-- ── VISUAL (left pane in RTL): full-bleed, own background, divider ── -->
            <div class="spm-visual-col" :style="{ background: visualBg }">
              <Transition :name="reducedMotion ? 'spm-fade' : 'spm-slide'" mode="out-in">
                <div v-if="celebrating" key="celebrate" class="spm-visual-inner spm-celebrate">
                  <span v-for="n in 14" :key="n" class="spm-confetti" :style="confettiStyle(n)"></span>
                  <svg class="spm-celebrate-check" viewBox="0 0 64 64" fill="none">
                    <circle cx="32" cy="32" r="30" fill="#2E844A"/>
                    <path d="M20 33l8 8 16-18" stroke="#fff" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                  <p class="spm-celebrate-text">הכל מוכן! מעכשיו המערכת עובדת בשבילכם.</p>
                </div>
                <div v-else :key="selectedId" class="spm-visual-inner">
                  <!-- Kling loop (first frame = last frame, so it loops without a
                       seam); the still is its poster and the reduced-motion view. -->
                  <video
                    v-if="stepVideos[selectedId] && !reducedMotion"
                    :src="stepVideos[selectedId]" :poster="stepAssets[selectedId]"
                    class="spm-visual-img" autoplay muted loop playsinline preload="auto"
                    aria-hidden="true" disablepictureinpicture
                  ></video>
                  <img v-else-if="stepAssets[selectedId]" :src="stepAssets[selectedId]" alt="" class="spm-visual-img" />
                  <component v-else :is="fallbackVisuals[selectedId]" />
                  <div class="spm-visual-scrim" :style="{ background: scrimBg }"></div>
                  <div class="spm-visual-num" aria-hidden="true">
                    <span class="spm-visual-num-n ltr-number">{{ pad(stepIndex + 1) }}</span>
                    <span class="spm-visual-num-of ltr-number">/{{ pad(steps.length) }}</span>
                  </div>
                </div>
              </Transition>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount, nextTick } from 'vue'
import { useOriginMorph } from '../../composables/useOriginMorph.js'
import { setupState, closeSetup, leaveSetupFor } from '../../utils/setupState.js'
import { useSetupPipeline, SETUP_ACCENTS } from '../../composables/useSetupPipeline.js'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import api from '../../api/client.js'
import WorkerVisual from './setup-visuals/WorkerVisual.vue'
import PhoneVisual from './setup-visuals/PhoneVisual.vue'
import PortalVisual from './setup-visuals/PortalVisual.vue'
import RunVisual from './setup-visuals/RunVisual.vue'
import MaslakaVisual from './setup-visuals/MaslakaVisual.vue'
import MailVisual from './setup-visuals/MailVisual.vue'
import StepTitle from './StepTitle.vue'
import AgreementRequestsPanel from './AgreementRequestsPanel.vue'
import AgreementsVisual from './setup-visuals/AgreementsVisual.vue'

const emit = defineEmits(['open-phone-forward', 'open-add-portal', 'open-mail-agent', 'open-agreements', 'open-maslaka', 'run-automation'])

const store = usePortalAutomationStore()
const setup = useSetupPipeline()
const { steps, completedCount, allDone, firstIncompleteId } = setup

const ACCENTS = SETUP_ACCENTS
const DONE = { accent: '#2E844A', soft: '#EAF5EE' }

// ── page-per-step navigation ──
const PHASE_OF = { phone: 'חיבור', worker: 'חיבור', mail: 'מייל והסכמים', agreements: 'מייל והסכמים', maslaka: 'מסלקה ופורטל', portal: 'מסלקה ופורטל', run: 'המחזור' }
const phaseOf = (id) => PHASE_OF[id] || ''
const pad = (n) => String(n).padStart(2, '0')

const fallbackVisuals = { worker: WorkerVisual, phone: PhoneVisual, portal: PortalVisual, mail: MailVisual, agreements: AgreementsVisual, maslaka: MaslakaVisual, run: RunVisual }

// Kling-generated images (optional): any step-<id>.webp dropped into
// assets/welcome/ takes over from the SVG fallback automatically.
const assetModules = import.meta.glob('../../assets/welcome/step-*.webp', { eager: true, import: 'default' })
const stepAssets = Object.fromEntries(
  Object.entries(assetModules).map(([path, url]) => [path.match(/step-([a-z]+)\.webp$/)[1], url]),
)
const videoModules = import.meta.glob('../../assets/welcome/step-*.mp4', { eager: true, import: 'default' })
const stepVideos = Object.fromEntries(
  Object.entries(videoModules).map(([path, url]) => [path.match(/step-([a-z]+)\.mp4$/)[1], url]),
)

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

const selectedId = ref('phone')
const celebrating = ref(false)
const downloading = ref(false)
const downloadedOnce = ref(false)
const downloadedAt = ref(0)
const nowTick = ref(Date.now())
const workerHint = ref('')
const redirectNote = ref('')
const workerOnline = computed(() => !!store.workerStatus?.online)
const workerHost = computed(() => store.workerStatus?.hostname || '')
// The moment the computer connects, hold the worker step open on a clear
// "connected" confirmation before moving on — a silent collapse-and-jump
// left users unsure whether the install had worked.
const justConnected = ref(false)
let connectedTimer = null
// The installer embeds the phone-forward token (for OTP relay + install
// telemetry), so it can't be built until the phone step is done. Gate the
// download on it and route the user to the phone step if it's missing.
const phoneStepDone = computed(() => !!steps.value.find((s) => s.id === 'phone')?.done)

const activeAccent = computed(() => ACCENTS[selectedId.value] || ACCENTS.worker)
const stepIndex = computed(() => Math.max(0, steps.value.findIndex((x) => x.id === selectedId.value)))
const current = computed(() => steps.value[stepIndex.value] || null)
function go(delta) {
  const i = Math.min(steps.value.length - 1, Math.max(0, stepIndex.value + delta))
  select(steps.value[i].id)
}
function dotStyle(st) {
  if (st.done) return { background: DONE.accent, borderColor: DONE.accent, color: '#fff' }
  if (st.id === selectedId.value) {
    const a = ACCENTS[st.id]
    return { background: a.deep, borderColor: a.deep, color: '#fff' }
  }
  return {}
}
const activeStepTitle = computed(() => steps.value.find((s) => s.id === selectedId.value)?.title || '')
const visualBg = computed(() => {
  const a = activeAccent.value
  return `linear-gradient(165deg, ${a.tint} 0%, ${a.soft} 100%)`
})
const scrimBg = computed(() => {
  const a = activeAccent.value
  return `linear-gradient(to top, ${a.soft} 0%, transparent 42%)`
})

// ── Live installer telemetry ──────────────────────────────────────────────
// The installer window POSTs its progress to the server; /worker/status echoes
// it back via current_job ("install: <msg>"). Map raw messages to friendly UI.
const INSTALL_STAGES = {
  'מתקין Python (חד-פעמי)': { label: 'מתקין Python (פעם אחת)…', pct: 12 },
  'מוריד רכיבים': { label: 'מוריד רכיבים למחשב…', pct: 22 },
  'מכינים סביבה': { label: 'מכין סביבה…', pct: 38 },
  'מתקינים ספריות (2-4 דקות — אל תסגרו)': { label: 'מתקין ספריות — החלק הארוך (2-4 דקות)…', pct: 55 },
  'מורידים דפדפן (כ-150MB — אל תסגרו)': { label: 'מוריד דפדפן (כ-150MB)…', pct: 72 },
  'מגדיר': { label: 'מגדיר את החיבור…', pct: 82 },
  'מפעיל': { label: 'מפעיל את החיבור…', pct: 92 },
  'done': { label: 'כמעט שם — ממתין לחיבור הראשון…', pct: 96 },
  // The worker process itself is up and importing (first run on a fresh PC can
  // take a couple of minutes); its first heartbeat flips the pill to מחובר.
  'booting': { label: 'המחשב עולה — החיבור הראשון לוקח עד 2-3 דקות…', pct: 98 },
  // Legacy label from pre-2026-07 installers still in the field:
  'מתקין רכיבים (כמה דקות)': { label: 'מתקין רכיבים (כמה דקות)…', pct: 55 },
}
const rawInstallMsg = computed(() => {
  const job = store.workerStatus?.current_job || ''
  if (workerOnline.value || !job.startsWith('install: ')) return null
  return job.slice('install: '.length)
})
const installError = computed(() => {
  const m = rawInstallMsg.value
  return m && m.startsWith('FATAL: ') ? m.slice(7) : null
})
const installProgress = computed(() => {
  const m = rawInstallMsg.value
  if (!m || installError.value) return null
  return INSTALL_STAGES[m] || { label: 'ההתקנה רצה…', pct: 35 }
})

// Stuck rescue: the user downloaded 75s+ ago, and neither the installer nor
// the worker gave any sign of life. Tell them exactly what to do next.
const stuck = computed(() => {
  if (!downloadedAt.value || workerOnline.value || rawInstallMsg.value) return false
  return nowTick.value - downloadedAt.value > 75_000
})

// The installer can report it finished ('done') yet the worker never comes
// online — then we'd sit at 97% "כמעט שם…" forever. Record when we first see
// 'done' and, after a grace period without a connection, switch to the rescue.
// The server keeps no timestamp for 'done', so a 'done' we did NOT watch happen
// (no download and no live install stage this session) is stale — e.g. from an
// earlier install whose worker then crashed. Start that one already expired.
const doneSince = ref(0)
const sawLiveInstall = ref(false)
// Grace before the rescue: 'done' should be followed by 'booting' within
// seconds; 'booting' may legitimately take minutes (first import on a new PC).
const STALL_GRACE = { done: 45_000, booting: 240_000 }
const waitingOn = ref(null)
watch(rawInstallMsg, (m) => {
  if (m && !(m in STALL_GRACE)) sawLiveInstall.value = true
  if (m in STALL_GRACE && !workerOnline.value) {
    if (m !== waitingOn.value) {
      if (waitingOn.value) sawLiveInstall.value = true // a transition we saw live
      waitingOn.value = m
      doneSince.value = 0
    }
    if (!doneSince.value) {
      const watched = sawLiveInstall.value || downloadedAt.value > 0
      doneSince.value = watched ? Date.now() : Date.now() - 3_600_000
    }
  } else {
    doneSince.value = 0
  }
}, { immediate: true })
const installStalled = computed(() =>
  !workerOnline.value && doneSince.value > 0
    && nowTick.value - doneSince.value > (STALL_GRACE[waitingOn.value] || 45_000),
)

let tickTimer = null
let advanceTimer = null
let celebrateTimer = null
let pollHeld = false // this component's share of the refcounted worker poll

function select(id) {
  selectedId.value = id
  if (id !== 'phone') redirectNote.value = ''
}
// iPhone-style: the wizard grows out of the home "הפעלת האוטומציה" card and folds
// back into it on X. Opened from elsewhere (bell, another tab) → the card isn't
// on screen, both calls no-op, and the plain fade plays.
const morph = useOriginMorph()
const overlayEl = ref(null)
const cardEl = ref(null)
const morphing = ref(false)
const homeCard = () => {
  const el = document.querySelector('.spc')
  const r = el?.getBoundingClientRect()
  return r && r.width && r.bottom > 0 && r.top < window.innerHeight ? el : null
}
function fadeScrim(dir) {
  const o = overlayEl.value
  if (!o) return
  const bg = getComputedStyle(o).backgroundColor
  o.animate(dir === 'in' ? [{ backgroundColor: 'rgba(24,24,24,0)' }, { backgroundColor: bg }]
                         : [{ backgroundColor: bg }, { backgroundColor: 'rgba(24,24,24,0)' }],
            { duration: dir === 'in' ? 560 : 380, easing: 'ease', fill: dir === 'in' ? 'none' : 'forwards' })
}
watch(() => setupState.modalOpen, async (open) => {
  if (!open) return
  const origin = homeCard()
  if (!origin) return
  morphing.value = true
  morph.remember(origin)
  await nextTick()
  fadeScrim('in')
  morph.grow(cardEl.value)
  setTimeout(() => { morphing.value = false }, 600)
})
async function close() {
  const origin = homeCard()
  if (origin && cardEl.value) {
    morph.remember(origin)
    fadeScrim('out')
    await morph.shrink(cardEl.value)
  }
  closeSetup()
}

function ctaStyle(id) {
  const a = ACCENTS[id]
  return { background: a.deep, boxShadow: `0 4px 12px ${a.accent}55` } // deep: white text on sky/teal accents fails 4.5:1
}

// Once the phone connects (token now exists), bounce the user back to the
// worker step so they can finish the download that sent them here.
watch(phoneStepDone, (done, prev) => {
  if (done && !prev && redirectNote.value) {
    redirectNote.value = ''
    select('worker')
    workerHint.value = 'הטלפון חובר ✓ עכשיו לחצו "הורד מתקין".'
  }
})

function onCta(s) {
  if (s.id === 'worker') downloadInstaller()
  else if (s.id === 'phone') emit('open-phone-forward')
  else if (s.id === 'portal') { leaveSetupFor('portal'); emit('open-add-portal') }
  else if (s.id === 'mail') { leaveSetupFor('mail'); emit('open-mail-agent') }
  else if (s.id === 'maslaka') { leaveSetupFor('maslaka'); emit('open-maslaka') }
  else if (s.id === 'run') { emit('run-automation'); close() }
}

async function downloadInstaller() {
  // Phone step must be done first — it provisions the token the installer needs.
  // Instead of a dead-end "download failed", take the user to the phone step.
  if (!phoneStepDone.value) {
    workerHint.value = ''
    select('phone')
    redirectNote.value = 'רגע לפני ההורדה — קודם נחבר את הטלפון (שנייה אחת). כך המחשב ידע לאן לשלוח את קודי האימות, ואז נוריד את המתקין.'
    return
  }
  downloading.value = true
  workerHint.value = ''
  try {
    const res = await api.get('/portal-automation/worker/installer', { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/octet-stream' }))
    const a = document.createElement('a')
    a.href = url
    a.download = 'nifraim-worker-setup.bat'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    downloadedOnce.value = true
    downloadedAt.value = Date.now()
    workerHint.value = 'הקובץ ירד ✓ לחצו עליו פעמיים — ייפתח חלון התקנה ירוק, וההתקדמות תופיע גם כאן.'
  } catch (e) {
    workerHint.value = 'ההורדה נכשלה. נסו שוב או פנו לתמיכה.'
  } finally {
    downloading.value = false
  }
}

function confettiStyle(n) {
  const colors = [...Object.values(ACCENTS).map((a) => a.accent), DONE.accent]
  return {
    left: `${(n * 61) % 100}%`,
    background: colors[n % colors.length],
    animationDelay: `${(n % 7) * 0.12}s`,
    animationDuration: `${1.6 + (n % 5) * 0.25}s`,
  }
}

// ── Open / close lifecycle — always land on the mission (first incomplete) ──
watch(() => setupState.modalOpen, (open) => {
  if (open) {
    celebrating.value = false
    workerHint.value = ''
    const requested = setupState.requestedStep
    setup.bootstrap().then(() => {
      // Back from a step done elsewhere (e.g. a portal was just added): land on
      // the step that is ACTUALLY next, now that the fresh state is in.
      if (!requested && setupState.modalOpen) selectedId.value = firstIncompleteId.value || selectedId.value
    }).catch(() => {})
    if (!pollHeld) { setup.startWorkerPoll(); pollHeld = true }
    if (!tickTimer) tickTimer = setInterval(() => { nowTick.value = Date.now() }, 5000)
    selectedId.value = setupState.requestedStep || firstIncompleteId.value || 'phone'
  } else {
    if (pollHeld) { setup.stopWorkerPoll(); pollHeld = false }
    if (tickTimer) { clearInterval(tickTimer); tickTimer = null }
    if (advanceTimer) { clearTimeout(advanceTimer); advanceTimer = null }
  }
// immediate: the modal can MOUNT already open (remount / hot reload while the
// wizard is up) — without it the status poll never starts and the pill stays
// on "ממתין לחיבור" even after the worker connects.
}, { immediate: true })

watch(workerOnline, (on, was) => {
  if (!on || was || !setupState.modalOpen) return
  justConnected.value = true
  selectedId.value = 'worker'
  if (connectedTimer) clearTimeout(connectedTimer)
  connectedTimer = setTimeout(() => {
    justConnected.value = false
    if (firstIncompleteId.value) selectedId.value = firstIncompleteId.value
  }, 2600)
})

// ── Live completion while open: checkmark draws, then move to next mission ──
watch(completedCount, (now, before) => {
  if (!setupState.modalOpen || now <= before || justConnected.value) return
  if (advanceTimer) clearTimeout(advanceTimer)
  advanceTimer = setTimeout(() => {
    if (firstIncompleteId.value) selectedId.value = firstIncompleteId.value
  }, 900)
})

watch(allDone, (done) => {
  if (!done) return
  setup.markCompleted()
  if (setupState.modalOpen) {
    celebrating.value = true
    celebrateTimer = setTimeout(close, 2600)
  }
})

onBeforeUnmount(() => {
  if (connectedTimer) clearTimeout(connectedTimer)
  if (advanceTimer) clearTimeout(advanceTimer)
  if (celebrateTimer) clearTimeout(celebrateTimer)
  if (tickTimer) clearInterval(tickTimer)
  if (pollHeld) { setup.stopWorkerPoll(); pollHeld = false }
})
</script>

<style scoped>
.spm-overlay {
  position: fixed;
  inset: 0;
  z-index: 1050; /* below PhoneForwardModal (1300) so the phone step stacks on top */
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(24, 24, 24, 0.45);
  backdrop-filter: blur(4px);
}

.spm-card {
  position: relative;
  width: 100%;
  max-width: 980px;
  max-height: calc(100vh - 40px);
  overflow: hidden auto;
  background: #fff;
  border-radius: var(--radius-xl, 24px);
  box-shadow: 0 24px 64px rgba(24, 24, 24, 0.22);
  padding: 0;
  font-family: 'Heebo', sans-serif;
}

.spm-close {
  position: absolute;
  top: 16px;
  left: 16px;
  z-index: 3;
  display: inline-flex;
  padding: 7px;
  border: none;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.85);
  box-shadow: 0 1px 4px rgba(24, 24, 24, 0.12);
  color: var(--text-secondary, #3E3E3C);
  cursor: pointer;
  transition: background 0.15s;
}
.spm-close:hover { background: #fff; }

/* ── Two full-height panes with a hard seam ── */
.spm-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(0, 0.9fr);
  /* Tall enough for the biggest step, so opening/closing steps never resizes
     and re-centres the card under the user's cursor. */
  min-height: min(720px, calc(100vh - 40px));
}
/* Desktop: the card is a fixed frame and only the steps column scrolls. When
   the whole card scrolled, the longest step (worker) stretched the picture
   pane to ~970px, so the image zoomed in and its bottom scrolled away. */
@media (min-width: 761px) {
  .spm-card { overflow: hidden; }
  .spm-layout { height: min(760px, calc(100vh - 40px)); }
  .spm-main { overflow-y: auto; overscroll-behavior: contain; }
}

.spm-main { padding: 30px 34px 26px 26px; }

/* ── Header ── */
.spm-header { margin-bottom: 18px; }
.spm-kicker {
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: #0A6664; /* automation ink — orange is the CTA colour, not a label */
  background: var(--tab-automation-wash);
  border-radius: 999px;
  padding: 4px 12px;
  margin-bottom: 10px;
}
.spm-title { margin: 0 0 4px; font-size: 25px; font-weight: 800; color: var(--text, #181818); }
.spm-sub { margin: 0; font-size: 14.5px; color: var(--text-tertiary, #706E6B); }

.spm-progress { display: flex; align-items: center; gap: 6px; margin-top: 14px; }
.spm-progress-seg {
  height: 7px;
  width: 46px;
  border-radius: 4px;
  background: #F0EDE8;
  transition: background 0.4s ease;
}
.spm-progress-label { font-size: 12.5px; font-weight: 700; color: var(--text-tertiary, #706E6B); margin-right: 4px; }

/* ── Steps list ── */
.spm-steps { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }

.spm-step {
  border-radius: var(--radius-lg, 16px);
  border: 1.5px solid transparent;
  background: #FAFAF9;
  transition: background 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease;
}
.spm-step--done {
  background: #EAF5EE;
  border-color: rgba(46, 132, 74, 0.16);
}
.spm-step--active.spm-step--worker { background: #FAF8FC; border-color: #8E44AD; box-shadow: 0 8px 22px rgba(142, 68, 173, 0.14); }
.spm-step--active.spm-step--phone  { background: #F8FBFD; border-color: #4E9DD0; box-shadow: 0 8px 22px rgba(78, 157, 208, 0.14); }
.spm-step--active.spm-step--portal { background: #FDF7F9; border-color: #D6336C; box-shadow: 0 8px 22px rgba(214, 51, 108, 0.14); }
.spm-step--active.spm-step--run    { background: #F5FAFA; border-color: #0E8C8A; box-shadow: 0 8px 22px rgba(14, 140, 138, 0.14); }

.spm-step-head {
  display: flex;
  align-items: center;
  gap: 14px;
  width: 100%;
  padding: 13px 14px;
  border: none;
  background: none;
  cursor: pointer;
  text-align: right;
  font-family: inherit;
  border-radius: inherit;
}

.spm-step-marker {
  flex-shrink: 0;
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 2px solid var(--border, #DDDBDA);
  color: var(--text-secondary, #3E3E3C);
  transition: border-color 0.25s, background 0.25s, color 0.25s, transform 0.25s;
}
.spm-step--active .spm-step-marker { transform: scale(1.06); }
.spm-step-num { font-size: 15px; font-weight: 800; }
.spm-check-icon { width: 18px; height: 18px; }
.spm-check-path { stroke-dasharray: 24; stroke-dashoffset: 0; }
.spm-check-enter-active .spm-check-path { animation: spm-draw 0.45s ease 0.05s backwards; }
@keyframes spm-draw { from { stroke-dashoffset: 24; } to { stroke-dashoffset: 0; } }
.spm-check-enter-active, .spm-check-leave-active { transition: transform 0.25s ease, opacity 0.2s ease; }
.spm-check-enter-from { transform: scale(0.4); opacity: 0; }
.spm-check-leave-to { opacity: 0; }

.spm-step-titles { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }
.spm-step-title { font-size: 15.5px; font-weight: 700; color: var(--text, #181818); }
.spm-step--done .spm-step-title { color: #2F5E41; }
.spm-step-donetag {
  flex-shrink: 0;
  margin-right: auto;
  font-size: 11px;
  font-weight: 700;
  color: var(--accent-emerald, #2E844A);
  background: #fff;
  border: 1px solid rgba(46, 132, 74, 0.25);
  border-radius: 999px;
  padding: 2px 9px;
}
.spm-step-meta {
  flex-shrink: 0;
  margin-right: auto;
  font-size: 11.5px;
  color: #2F5E41;
  opacity: 0.8;
}
.spm-step-meta + .spm-step-donetag { margin-right: 0; }
.spm-connected {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 4px;
  padding: 14px 16px;
  border-radius: 14px;
  background: #EAF5EE;
  border: 1px solid rgba(46, 132, 74, 0.28);
  animation: spmConnectedIn 0.35s ease both;
}
.spm-connected-icon {
  flex-shrink: 0;
  display: grid;
  place-items: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--accent-emerald, #2E844A);
  color: #fff;
}
.spm-connected-texts { display: flex; flex-direction: column; gap: 2px; }
.spm-connected-texts strong { font-size: 15px; color: #1F5A35; }
.spm-connected-texts span { font-size: 13px; color: #2F5E41; }
@keyframes spmConnectedIn {
  from { opacity: 0; transform: scale(0.97); }
  to { opacity: 1; transform: scale(1); }
}
@media (prefers-reduced-motion: reduce) { .spm-connected { animation: none; } }
.spm-step-nexttag {
  flex-shrink: 0;
  margin-right: auto;
  font-size: 11px;
  font-weight: 700;
  border-radius: 999px;
  padding: 2px 9px;
}

/* Expanding detail — only the active mission renders content */
.spm-step-detail {
  display: grid;
  grid-template-rows: 0fr;
  transition: grid-template-rows 0.35s ease;
}
.spm-step-detail--open { grid-template-rows: 1fr; }
.spm-step-detail-inner { overflow: hidden; padding: 0 66px 0 14px; }
.spm-step-detail--open .spm-step-detail-inner { padding-bottom: 16px; }

.spm-step-body { margin: 0 0 12px; font-size: 13.5px; line-height: 1.6; color: var(--text-secondary, #3E3E3C); }

/* Worker mini-walkthrough */
.spm-mini-steps { display: flex; flex-direction: column; gap: 7px; margin-bottom: 12px; }
.spm-mini-step {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  font-size: 12.5px;
  line-height: 1.55;
  color: var(--text-secondary, #3E3E3C);
  background: #fff;
  border: 1px solid rgba(142, 68, 173, 0.14);
  border-radius: 10px;
  padding: 8px 10px;
}
.spm-mini-num {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 800;
}
.spm-mini-step code {
  background: #F4F0EA;
  padding: 0 6px;
  border-radius: 5px;
  font-size: 11.5px;
  direction: ltr;
  display: inline-block;
}

.spm-step-actions { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.spm-cta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border: none;
  border-radius: 11px;
  color: #fff;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.15s, filter 0.15s;
}
.spm-cta:hover { transform: translateY(-1px); filter: brightness(1.06); }
.spm-cta:active { transform: translateY(0); }
.spm-cta:disabled { opacity: 0.65; cursor: default; }
.spm-cta:focus-visible { outline: 2px solid var(--text, #181818); outline-offset: 2px; }

.spm-worker-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 7px 13px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: #fff;
  color: #6C2E87;
  border: 1px solid rgba(142, 68, 173, 0.3);
}
.spm-worker-pill--on { background: #EAF5EE; color: var(--accent-emerald, #2E844A); border-color: rgba(46, 132, 74, 0.3); }
.spm-worker-dot { width: 8px; height: 8px; border-radius: 50%; background: #F0B429; animation: spm-blink 1.4s ease-in-out infinite; }
.spm-worker-pill--on .spm-worker-dot { background: var(--accent-emerald, #2E844A); animation: none; }
@keyframes spm-blink { 50% { opacity: 0.3; } }

.spm-hint {
  margin: 12px 0 0;
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1.55;
  border-radius: 10px;
  padding: 9px 12px;
}

/* Live install progress / error / stuck rescue */
.spm-install {
  display: flex;
  align-items: center;
  gap: 11px;
  margin-top: 12px;
  padding: 11px 13px;
  border-radius: 11px;
  background: #F1E9F5;
  border: 1px solid rgba(142, 68, 173, 0.25);
  font-size: 12.5px;
  line-height: 1.55;
  color: #6C2E87;
}
.spm-install-texts { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.spm-install-bar { display: block; height: 6px; border-radius: 3px; background: rgba(142, 68, 173, 0.18); overflow: hidden; }
.spm-install-fill { display: block; height: 100%; border-radius: 3px; background: #8E44AD; transition: width 0.6s ease; }
.spm-install-spinner {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2.5px solid rgba(142, 68, 173, 0.25);
  border-top-color: #8E44AD;
  animation: spm-spin 0.9s linear infinite;
}
@keyframes spm-spin { to { transform: rotate(360deg); } }

.spm-install--error {
  flex-direction: column;
  align-items: flex-start;
  gap: 5px;
  background: #FCEDEA;
  border-color: rgba(194, 57, 52, 0.3);
  color: #8E2A26;
}
.spm-install--error a { color: inherit; font-weight: 700; }

.spm-install--stuck {
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  background: var(--amber-light);
  border-color: rgba(201, 162, 39, 0.35);
}
.spm-install--stuck ul { margin: 0; padding-inline-start: 18px; display: flex; flex-direction: column; gap: 4px; }
.spm-install--stuck code { background: #F4F0EA; padding: 0 5px; border-radius: 4px; font-size: 11px; direction: ltr; display: inline-block; }

/* ── Visual pane: full-bleed, own background, seam line ── */
.spm-visual-col {
  position: relative;
  border-right: 1px solid rgba(24, 24, 24, 0.08); /* the seam (visual col sits physically LEFT in RTL) */
  overflow: hidden;
  transition: background 0.5s ease;
}
.spm-visual-inner { position: absolute; inset: 0; }
.spm-visual-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.spm-visual-inner > .sv,
.spm-visual-inner > div[class^='sv'] { position: absolute; inset: 24px; }
.spm-visual-scrim { position: absolute; inset: 0; pointer-events: none; }
.spm-visual-caption { position: absolute; bottom: 16px; right: 16px; left: 16px; display: flex; justify-content: flex-start; }
.spm-visual-chip {
  font-size: 12.5px;
  font-weight: 800;
  background: rgba(255, 255, 255, 0.92);
  border: 1.5px solid;
  border-radius: 999px;
  padding: 6px 14px;
  box-shadow: 0 2px 8px rgba(24, 24, 24, 0.08);
}

.spm-slide-enter-active, .spm-slide-leave-active { transition: opacity 0.32s ease, transform 0.32s ease; }
.spm-slide-enter-from { opacity: 0; transform: translateY(26px); }
.spm-slide-leave-to { opacity: 0; transform: translateY(-26px); }
.spm-fade-enter-active, .spm-fade-leave-active { transition: opacity 0.25s ease; }
.spm-fade-enter-from, .spm-fade-leave-to { opacity: 0; }

/* Celebration */
.spm-celebrate { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 16px; }
.spm-celebrate-check { width: 74px; height: 74px; animation: spm-pop-in 0.5s cubic-bezier(0.34, 1.56, 0.64, 1); }
@keyframes spm-pop-in { from { transform: scale(0); } to { transform: scale(1); } }
.spm-celebrate-text { margin: 0; font-size: 16px; font-weight: 700; color: var(--text, #181818); text-align: center; padding: 0 18px; }
.spm-confetti {
  position: absolute;
  top: -10px;
  width: 8px;
  height: 12px;
  border-radius: 2px;
  animation: spm-confetti-fall linear infinite;
}
@keyframes spm-confetti-fall {
  from { transform: translateY(-20px) rotate(0deg); opacity: 1; }
  to { transform: translateY(460px) rotate(340deg); opacity: 0.2; }
}

/* enter/leave */
.spm-enter-active { transition: opacity 0.3s ease; }
.spm-leave-active { transition: opacity 0.22s ease; }
.spm-enter-from, .spm-leave-to { opacity: 0; }
.spm-enter-active .spm-card { animation: spm-card-in 0.38s cubic-bezier(0.22, 1, 0.36, 1); }
/* growing out of the home card: the morph owns the motion (no fade, no slide-in) */
.spm-enter-active.spm-overlay--morph { transition: none; }
.spm-enter-active.spm-overlay--morph .spm-card { animation: none; }
@keyframes spm-card-in { from { transform: translateY(18px) scale(0.98); opacity: 0; } }

/* responsive: visual pane stacks on top */
@media (max-width: 760px) {
  .spm-layout { grid-template-columns: 1fr; min-height: 0; }
  .spm-visual-col {
    order: -1;
    min-height: 220px;
    border-right: none;
    border-bottom: 1px solid rgba(24, 24, 24, 0.08);
  }
  .spm-main { padding: 22px 20px 18px; }
  .spm-step-detail-inner { padding: 0 54px 0 8px; }
}

@media (prefers-reduced-motion: reduce) {
  .spm-enter-active .spm-card,
  .spm-celebrate-check,
  .spm-confetti,
  .spm-worker-dot,
  .spm-install-spinner { animation: none; }
  .spm-step-detail { transition: none; }
}

.spm-title-brand { color: #0A6664; unicode-bidi: isolate; }   /* two-colour welcome: ink + automation teal */

/* ═══════════ Full-screen welcome: one page per step ═══════════ */
.spm-overlay { padding: 0; backdrop-filter: none; background: #fff; }
.spm-card { max-width: none; width: 100vw; height: 100vh; max-height: none; border-radius: 0; box-shadow: none; }
.spm-layout { height: 100vh; min-height: 0; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
.spm-main {
  display: flex; flex-direction: column; min-height: 0;
  padding: clamp(28px, 4vh, 48px) clamp(28px, 5vw, 72px) clamp(20px, 3vh, 32px);
  overflow-y: auto;
}
.spm-close { top: 20px; left: 20px; }

/* top: kicker + welcome + step bar */
.spm-top { display: flex; flex-direction: column; gap: 8px; }
.spm-top .spm-kicker { align-self: flex-start; }
.spm-welcome { margin: 0; font-size: 20px; font-weight: 800; color: var(--text, #181818); }
.spm-stepper { display: flex; align-items: center; gap: 0; margin-top: 10px; }
.spm-dot {
  flex: none; width: 30px; height: 30px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  border: 2px solid #E4E1DD; background: #fff; color: #8A8784;
  font-family: inherit; font-size: 12.5px; font-weight: 800; cursor: pointer;
  transition: transform 0.2s ease, background 0.2s ease, border-color 0.2s ease;
}
.spm-dot:hover { transform: scale(1.08); }
.spm-dot--on { transform: scale(1.12); box-shadow: 0 4px 12px rgba(24, 24, 24, 0.14); }
.spm-stepper-line { flex: 1; min-width: 10px; max-width: 46px; height: 2px; background: #ECEAE7; }
.spm-stepper-line--done { background: rgba(46, 132, 74, 0.45); }
.spm-stepper-count { margin-inline-start: 12px; font-size: 12.5px; font-weight: 700; color: var(--text-tertiary, #706E6B); }

/* the page */
.spm-page { flex: 1; display: flex; flex-direction: column; justify-content: center; gap: 12px; padding: 28px 0; min-height: 0; }
.spm-page-kicker { font-size: 13px; font-weight: 800; letter-spacing: 0.02em; }
.spm-page-title { margin: 0; font-size: clamp(32px, 3.4vw, 50px); font-weight: 900; line-height: 1.12; letter-spacing: -0.02em; color: var(--text, #181818); }
.spm-page-title :deep(.st-brand) { font-size: 1em; }
.spm-page-body { margin: 0; max-width: 46ch; font-size: 16.5px; line-height: 1.65; color: var(--text-secondary, #3E3E3C); }
.spm-page-content { display: flex; flex-direction: column; gap: 14px; max-width: 560px; margin-top: 6px; }
.spm-page-content .spm-cta { height: 48px; padding: 0 24px; font-size: 15px; border-radius: 12px; }
.spm-done {
  align-self: flex-start; display: inline-flex; align-items: center; gap: 8px; margin-top: 6px;
  padding: 8px 16px; border-radius: 999px; background: #EAF5EE; color: #2E844A; font-size: 14px; font-weight: 800;
}

/* bottom nav */
.spm-nav { display: flex; justify-content: space-between; align-items: center; gap: 12px; padding-top: 12px; border-top: 1px solid #F0EEEB; }
.spm-nav-btn {
  display: inline-flex; align-items: center; gap: 8px; height: 42px; padding: 0 18px; border-radius: 10px;
  border: 1px solid var(--border-subtle, #E5E5E5); background: #fff; color: var(--text, #181818);
  font-family: inherit; font-size: 14px; font-weight: 700; cursor: pointer;
}
.spm-nav-btn:disabled { opacity: 0.4; cursor: default; }
.spm-nav-btn--next { background: var(--primary, #181818); color: #fff; border-color: transparent; }
.spm-nav-btn--next:hover { background: var(--primary-deep, #000); }

/* page transition */
.spm-page-enter-active, .spm-page-leave-active { transition: opacity 0.28s ease, transform 0.28s cubic-bezier(0.32, 0.72, 0, 1); }
.spm-page-enter-from { opacity: 0; transform: translateX(-24px); }
.spm-page-leave-to { opacity: 0; transform: translateX(24px); }

/* picture: landing-style step number in its top-right corner */
.spm-visual-num {
  position: absolute; top: clamp(20px, 4vh, 44px); right: clamp(20px, 3vw, 44px); z-index: 2;
  display: flex; align-items: baseline; gap: 6px; direction: ltr; pointer-events: none;
}
.spm-visual-num-n {
  font-family: 'Heebo', sans-serif; font-size: clamp(90px, 11vw, 168px); font-weight: 900; line-height: 0.9;
  color: rgba(255, 255, 255, 0.14); -webkit-text-stroke: 2px rgba(255, 255, 255, 0.92);
  text-shadow: 0 6px 30px rgba(24, 24, 24, 0.12); letter-spacing: -0.04em;
}
.spm-visual-num-of { font-size: clamp(18px, 1.6vw, 24px); font-weight: 800; color: rgba(255, 255, 255, 0.92); text-shadow: 0 2px 10px rgba(24, 24, 24, 0.18); }

/* ROBOT install instructions — a clean numbered list, not cramped boxes */
.spm-mini-steps { gap: 0; margin-bottom: 4px; counter-reset: none; }
.spm-mini-step {
  position: relative; display: flex; align-items: flex-start; gap: 14px;
  padding: 0 0 16px; border: none; background: none; box-shadow: none;
  font-size: 15px; line-height: 1.6; color: var(--text, #181818);
}
.spm-mini-step:not(:last-child)::before {
  content: ''; position: absolute; right: 13px; top: 30px; bottom: 2px; width: 2px;
  background: linear-gradient(#E9DDF0, #F4EEF7);
}
.spm-mini-num {
  flex: none; width: 28px; height: 28px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 800;
}
.spm-mini-step code {
  display: inline-block; margin: 0 2px; padding: 1px 9px; border-radius: 6px;
  background: #F3EAF7; color: #6B2F86; border: 1px solid #E4D3EC;
  font-family: 'Heebo', sans-serif; font-size: 13px; font-weight: 700; direction: rtl;
}

/* phones: picture becomes a banner on top */
@media (max-width: 760px) {
  .spm-layout { grid-template-columns: 1fr; grid-template-rows: 34vh minmax(0, 1fr); height: 100vh; }
  .spm-visual-col { order: -1; }
  .spm-main { overflow-y: auto; padding: 20px; }
  .spm-page { padding: 18px 0; justify-content: flex-start; }
  .spm-page-title { font-size: 30px; }
}
</style>
