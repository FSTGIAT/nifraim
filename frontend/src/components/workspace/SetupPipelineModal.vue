<template>
  <Teleport to="body">
    <Transition name="spm">
      <div v-if="setupState.modalOpen" class="spm-overlay" @click.self="close">
        <div
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
              <header class="spm-header">
                <span class="spm-kicker">הפעלת האוטומציה</span>
                <h2 id="spm-title" class="spm-title">ברוכים הבאים ל-Nifraim</h2>
                <p class="spm-sub">עוד כמה צעדים וההורדה תרוץ לבד.</p>
                <div class="spm-progress" aria-hidden="true">
                  <span
                    v-for="s in steps"
                    :key="s.id"
                    class="spm-progress-seg"
                    :class="{ 'spm-progress-seg--on': s.done }"
                    :style="s.done ? { background: ACCENTS[s.id].accent } : {}"
                  ></span>
                  <span class="spm-progress-label ltr-number">{{ completedCount }}/{{ steps.length }}</span>
                </div>
              </header>

              <ol class="spm-steps">
                <li
                  v-for="(s, i) in steps"
                  :key="s.id"
                  class="spm-step"
                  :class="[
                    { 'spm-step--active': s.id === selectedId, 'spm-step--done': s.done },
                    s.id === selectedId && !s.done ? 'spm-step--' + s.id : '',
                  ]"
                >
                  <button class="spm-step-head" type="button" @click="select(s.id)">
                    <span class="spm-step-marker" :style="markerStyle(s)">
                      <Transition name="spm-check" mode="out-in">
                        <svg v-if="s.done" key="check" class="spm-check-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path class="spm-check-path" d="M20 6 9 17l-5-5"/></svg>
                        <span v-else key="num" class="spm-step-num ltr-number">{{ i + 1 }}</span>
                      </Transition>
                    </span>
                    <span class="spm-step-titles">
                      <span class="spm-step-title">{{ s.title }}</span>
                      <span v-if="s.done" class="spm-step-donetag">הושלם</span>
                      <span v-else-if="s.id === firstIncompleteId" class="spm-step-nexttag" :style="{ background: ACCENTS[s.id].soft, color: ACCENTS[s.id].deep }">הצעד הבא</span>
                    </span>
                  </button>

                  <!-- Detail: only for the ACTIVE, NOT-DONE step — the mission card -->
                  <div class="spm-step-detail" :class="{ 'spm-step-detail--open': s.id === selectedId && !s.done }">
                    <div class="spm-step-detail-inner">
                      <p class="spm-step-body">{{ s.body }}</p>

                      <!-- Worker: honest walkthrough + live install telemetry -->
                      <template v-if="s.id === 'worker'">
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
                          <button class="spm-cta" :style="ctaStyle('worker')" :disabled="downloading" @click="onCta(s)">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/></svg>
                            {{ downloading ? 'מוריד…' : downloadedOnce ? 'הורד שוב' : s.cta }}
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
                        <p v-if="s.id === 'phone' && redirectNote" class="spm-hint" :style="{ background: ACCENTS.phone.soft, color: ACCENTS.phone.deep }">{{ redirectNote }}</p>
                        <div class="spm-step-actions">
                        <button class="spm-cta" :style="ctaStyle(s.id)" @click="onCta(s)">
                          <svg v-if="s.id === 'phone'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18h2"/></svg>
                          <svg v-else-if="s.id === 'portal'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
                          <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 4l14 8-14 8z"/></svg>
                          {{ s.cta }}
                        </button>
                        </div>
                      </template>
                    </div>
                  </div>
                </li>
              </ol>
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
                  <img v-if="stepAssets[selectedId]" :src="stepAssets[selectedId]" alt="" class="spm-visual-img" />
                  <component v-else :is="fallbackVisuals[selectedId]" />
                  <div class="spm-visual-scrim" :style="{ background: scrimBg }"></div>
                  <div class="spm-visual-caption">
                    <span class="spm-visual-chip" :style="{ color: activeAccent.deep, borderColor: activeAccent.accent + '55' }">{{ activeStepTitle }}</span>
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
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { setupState, closeSetup } from '../../utils/setupState.js'
import { useSetupPipeline } from '../../composables/useSetupPipeline.js'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import api from '../../api/client.js'
import WorkerVisual from './setup-visuals/WorkerVisual.vue'
import PhoneVisual from './setup-visuals/PhoneVisual.vue'
import PortalVisual from './setup-visuals/PortalVisual.vue'
import RunVisual from './setup-visuals/RunVisual.vue'

const emit = defineEmits(['open-phone-forward', 'open-add-portal', 'run-automation'])

const store = usePortalAutomationStore()
const setup = useSetupPipeline()
const { steps, completedCount, allDone, firstIncompleteId } = setup

// Pastel accent per step — one hue per mission (mirrors SetupProgressCard).
const ACCENTS = {
  worker: { accent: '#E8930C', deep: '#9A5B00', soft: '#FDF1DC', tint: '#FFFAF1' },
  phone:  { accent: '#4E9DD0', deep: '#2C6E9E', soft: '#E7F2FA', tint: '#F5FAFD' },
  portal: { accent: '#8E6FD6', deep: '#5F429F', soft: '#EFEAFA', tint: '#F9F7FD' },
  run:    { accent: '#1FA88C', deep: '#0E7A64', soft: '#E4F5F0', tint: '#F3FBF8' },
}
const DONE = { accent: '#2E844A', soft: '#EAF5EE' }

const fallbackVisuals = { worker: WorkerVisual, phone: PhoneVisual, portal: PortalVisual, run: RunVisual }

// Kling-generated images (optional): any step-<id>.webp dropped into
// assets/welcome/ takes over from the SVG fallback automatically.
const assetModules = import.meta.glob('../../assets/welcome/step-*.webp', { eager: true, import: 'default' })
const stepAssets = Object.fromEntries(
  Object.entries(assetModules).map(([path, url]) => [path.match(/step-([a-z]+)\.webp$/)[1], url]),
)

const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

const selectedId = ref('worker')
const celebrating = ref(false)
const downloading = ref(false)
const downloadedOnce = ref(false)
const downloadedAt = ref(0)
const nowTick = ref(Date.now())
const workerHint = ref('')
const redirectNote = ref('')
const workerOnline = computed(() => !!store.workerStatus?.online)
// The installer embeds the phone-forward token (for OTP relay + install
// telemetry), so it can't be built until the phone step is done. Gate the
// download on it and route the user to the phone step if it's missing.
const phoneStepDone = computed(() => !!steps.value.find((s) => s.id === 'phone')?.done)

const activeAccent = computed(() => ACCENTS[selectedId.value] || ACCENTS.worker)
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
  'done': { label: 'כמעט שם — ממתין לחיבור הראשון…', pct: 97 },
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
const doneSince = ref(0)
watch(rawInstallMsg, (m) => {
  if (m === 'done' && !workerOnline.value) {
    if (!doneSince.value) doneSince.value = Date.now()
  } else {
    doneSince.value = 0
  }
}, { immediate: true })
const installStalled = computed(() =>
  !workerOnline.value && doneSince.value > 0 && nowTick.value - doneSince.value > 45_000,
)

let tickTimer = null
let advanceTimer = null
let celebrateTimer = null
let pollHeld = false // this component's share of the refcounted worker poll

function select(id) {
  selectedId.value = id
  if (id !== 'phone') redirectNote.value = ''
}
function close() { closeSetup() }

function markerStyle(s) {
  if (s.done) return { background: DONE.accent, borderColor: DONE.accent, color: '#fff' }
  if (s.id === selectedId.value) {
    const a = ACCENTS[s.id]
    return { background: a.soft, borderColor: a.accent, color: a.deep }
  }
  return {}
}

function ctaStyle(id) {
  const a = ACCENTS[id]
  return { background: a.accent, boxShadow: `0 4px 12px ${a.accent}55` }
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
  else if (s.id === 'portal') { emit('open-add-portal'); close() }
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
  const colors = ['#E8930C', '#4E9DD0', '#8E6FD6', '#1FA88C', '#2E844A']
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
    setup.bootstrap().catch(() => {})
    if (!pollHeld) { setup.startWorkerPoll(); pollHeld = true }
    if (!tickTimer) tickTimer = setInterval(() => { nowTick.value = Date.now() }, 5000)
    selectedId.value = setupState.requestedStep || firstIncompleteId.value || 'worker'
  } else {
    if (pollHeld) { setup.stopWorkerPoll(); pollHeld = false }
    if (tickTimer) { clearInterval(tickTimer); tickTimer = null }
    if (advanceTimer) { clearTimeout(advanceTimer); advanceTimer = null }
  }
})

// ── Live completion while open: checkmark draws, then move to next mission ──
watch(completedCount, (now, before) => {
  if (!setupState.modalOpen || now <= before) return
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
  min-height: 540px;
}

.spm-main { padding: 30px 34px 26px 26px; }

/* ── Header ── */
.spm-header { margin-bottom: 18px; }
.spm-kicker {
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--primary-deep, #E65100);
  background: var(--primary-light, #FFF3E0);
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
.spm-step--active.spm-step--worker { background: #FFFAF1; border-color: #E8930C; box-shadow: 0 8px 22px rgba(232, 147, 12, 0.14); }
.spm-step--active.spm-step--phone  { background: #F5FAFD; border-color: #4E9DD0; box-shadow: 0 8px 22px rgba(78, 157, 208, 0.14); }
.spm-step--active.spm-step--portal { background: #F9F7FD; border-color: #8E6FD6; box-shadow: 0 8px 22px rgba(142, 111, 214, 0.14); }
.spm-step--active.spm-step--run    { background: #F3FBF8; border-color: #1FA88C; box-shadow: 0 8px 22px rgba(31, 168, 140, 0.14); }

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
  border: 1px solid rgba(232, 147, 12, 0.14);
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
  color: #9A5B00;
  border: 1px solid rgba(232, 147, 12, 0.3);
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
  background: #FDF1DC;
  border: 1px solid rgba(232, 147, 12, 0.25);
  font-size: 12.5px;
  line-height: 1.55;
  color: #6B4A0E;
}
.spm-install-texts { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 6px; }
.spm-install-bar { display: block; height: 6px; border-radius: 3px; background: rgba(232, 147, 12, 0.18); overflow: hidden; }
.spm-install-fill { display: block; height: 100%; border-radius: 3px; background: #E8930C; transition: width 0.6s ease; }
.spm-install-spinner {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2.5px solid rgba(232, 147, 12, 0.25);
  border-top-color: #E8930C;
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
  background: #FFF8E9;
  border-color: rgba(232, 147, 12, 0.35);
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
</style>
