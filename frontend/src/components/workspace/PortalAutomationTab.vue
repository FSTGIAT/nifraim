<template>
  <div ref="pageEl" class="auto-page">
    <!-- Remotion: big meshing gears stacked down the page, turning slowly behind the
         dashboard — very faint, decorative only. -->
    <div v-if="store.credentials.length && !gearsReduced" class="auto-gears" aria-hidden="true">
      <div ref="gearsEl" class="auto-gears-mount" :style="{ aspectRatio: `${1600} / ${800 * gearCount}` }"></div>
    </div>
    <div class="auto-inner">
    <!-- Hero: title + one-click run-all + add portal, aggregating to one
         production + one נפרעים file → compare. -->
    <PortalRunAllBar class="runall-block" @view-results="emit('go-to-comparison')" @add="openAdd" />

    <!-- KPI stat band -->
    <PortalStatBand v-if="store.credentials.length" />

    <div v-if="store.error" class="error-banner">{{ store.error }}</div>

    <div v-if="store.loading && !store.credentials.length" class="loading-strip">
      <span class="spinner" aria-hidden="true"></span>
      <span>טוען פורטלים…</span>
    </div>

    <!-- ─── Dashboard: company panels + activity sidebar ────── -->
    <div v-else class="dash" :class="{ 'dash--empty': !store.credentials.length }">
      <!-- No portal yet: one welcome section (realistic photo with a surreal
           touch fading into the card + how it works as a slider). The hero
           above keeps the actions (הוסף פורטל / הורדה אוטומטית). -->
      <section v-if="!store.credentials.length" class="au-welcome">
        <div v-if="auArt.still" class="au-welcome-photo" aria-hidden="true">
          <video v-if="auArt.video && !auReduced" :src="auArt.video" :poster="auArt.still"
                 autoplay muted loop playsinline preload="auto" disablepictureinpicture></video>
          <img v-else :src="auArt.still" alt="" />
        </div>
        <div class="au-welcome-copy">
          <h3 class="au-welcome-title">מחברים פעם אחת<br><span>והדוחות יורדים לבד</span></h3>
          <div v-if="!auReduced" class="au-slider" aria-live="polite"
               @mouseenter="auPaused = true" @mouseleave="auPaused = false">
            <div class="au-slide-track">
              <Transition name="au-slide" mode="out-in">
                <div :key="auStep" class="au-slide">
                  <span class="au-slide-n ltr-number">{{ String(auStep + 1).padStart(2, '0') }}</span>
                  <div><strong>{{ AU_STEPS[auStep].title }}</strong><span>{{ AU_STEPS[auStep].text }}</span></div>
                </div>
              </Transition>
            </div>
            <div class="au-bars">
              <button v-for="(st, n) in AU_STEPS" :key="n" type="button" class="au-bar"
                      :class="{ 'au-bar--done': n < auStep, 'au-bar--on': n === auStep, 'au-bar--paused': auPaused }"
                      :aria-label="st.title" :aria-current="n === auStep ? 'step' : undefined" @click="auGo(n)">
                <span :key="n === auStep ? auCycle : 'x'" class="au-bar-fill"></span>
              </button>
            </div>
          </div>
          <ol v-else class="au-steps-static">
            <li v-for="(st, n) in AU_STEPS" :key="n"><span class="au-slide-n ltr-number">{{ String(n + 1).padStart(2, '0') }}</span><div><strong>{{ st.title }}</strong><span>{{ st.text }}</span></div></li>
          </ol>
        </div>
      </section>
      <PortalAutomationCanvas
        v-if="store.credentials.length"
        class="dash__main"
        :credentials="store.credentials"
        :portal-label="portalLabel"
        :active-run="store.activeRun"
        :active-run-id="store.activeRunId"
        @run="runNow"
        @edit="openEdit"
        @delete="deleteCred"
        @add="openAdd"
        @view-error="onViewError"
      />
      <PortalActivityPanel
        v-if="store.credentials.length"
        class="dash__aside"
        @view-results="emit('go-to-comparison')"
      />
    </div>

    <PortalCredentialModal
      :open="modalOpen"
      :mode="modalMode"
      :credential="modalCred"
      @close="modalOpen = false"
      @saved="onModalSaved"
    />

    <!-- The OTP step no longer pops a modal here — the run continues in the
         background and PortalRunProgressFloat (global widget) owns manual
         entry + cancel. -->

    <!-- ─── Error popup — replaces the inline error block on cards ─── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="errorModalOpen" class="err-overlay" @click="errorModalOpen = false">
          <div class="err-card" role="dialog" aria-modal="true" aria-label="פרטי שגיאה" @click.stop>
            <header class="err-head">
              <span class="err-icon" aria-hidden="true">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
                </svg>
              </span>
              <div class="err-titles">
                <h3 class="err-title">שגיאה בריצת אוטומציה</h3>
                <p v-if="errorContext" class="err-meta">{{ portalLabel(errorContext.portal_kind) }} · <span class="ltr-number">{{ errorContext.username }}</span></p>
              </div>
              <button class="err-x" type="button" aria-label="סגור" @click="errorModalOpen = false">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M18 6 6 18" /><path d="m6 6 12 12" />
                </svg>
              </button>
            </header>
            <div class="err-body">{{ errorMessage }}</div>
            <footer class="err-foot">
              <button class="err-btn err-btn--secondary" type="button" @click="errorModalOpen = false">סגור</button>
              <button v-if="errorContext" class="err-btn err-btn--primary" type="button" @click="rerunFromError">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                  <polygon points="6 4 20 12 6 20" />
                </svg>
                <span>נסה שוב</span>
              </button>
            </footer>
          </div>
        </div>
      </Transition>
    </Teleport>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onBeforeUnmount, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import PortalCredentialModal from './PortalCredentialModal.vue'
import PortalAutomationCanvas from './PortalAutomationCanvas.vue'
import PortalRunAllBar from './PortalRunAllBar.vue'
import PortalStatBand from './PortalStatBand.vue'
import PortalActivityPanel from './PortalActivityPanel.vue'
import { CHART_PALETTE } from '../../utils/chartPalette.js'

const props = defineProps({
  // When the activation checklist routes here, auto-open the add-credential modal.
  autoOpenAdd: { type: Boolean, default: false },
})
const emit = defineEmits(['go-to-comparison', 'opened'])
const store = usePortalAutomationStore()

// ── No-portal welcome: photo + how-it-works slider ──
const auAssets = import.meta.glob('../../assets/welcome/automation-empty.{webp,mp4}', { eager: true, import: 'default' })
const auArt = {
  still: Object.entries(auAssets).find(([k]) => k.endsWith('.webp'))?.[1] || '',
  video: Object.entries(auAssets).find(([k]) => k.endsWith('.mp4'))?.[1] || '',
}
const auReduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
const AU_STEPS = [
  { title: 'מוסיפים פורטל', text: 'שם משתמש וסיסמה — פעם אחת לכל חברה.' },
  { title: 'הטלפון מעביר את הקוד', text: 'קוד האימות מגיע לבד, בלי להקליד.' },
  { title: 'לחיצה אחת', text: 'כל הדוחות יורדים מכל החברות.' },
  { title: 'הכל מושווה', text: 'פרודוקציה ונפרעים מתעדכנים לבד.' },
]
const AU_MS = 2800 // keep in sync with .au-bar--on
const auStep = ref(0)
const auCycle = ref(0)
const auPaused = ref(false)
let auTimer = null
function auArm() {
  clearTimeout(auTimer)
  if (auReduced) return
  auTimer = setTimeout(() => { if (auPaused.value) return auArm(); auGo((auStep.value + 1) % AU_STEPS.length) }, AU_MS)
}
function auGo(n) { auStep.value = n; auCycle.value++; auArm() }
watch(auPaused, (p) => { if (!p) auArm() })
watch(() => store.credentials.length === 0, (empty) => { if (empty) auGo(0); else clearTimeout(auTimer) }, { immediate: true })
onBeforeUnmount(() => clearTimeout(auTimer))

// ─── Modal state ──────────────────────────────────────────
const modalOpen = ref(false)
const modalMode = ref('add')
const modalCred = ref(null)

function openAdd() {
  modalMode.value = 'add'
  modalCred.value = null
  modalOpen.value = true
}
function openEdit(cred) {
  modalMode.value = 'edit'
  modalCred.value = cred
  modalOpen.value = true
}
function onModalSaved() {
  // store.create/update already updates credentials[]; nothing else needed
}

function portalLabel(kind) {
  return store.portalKinds.find((k) => k.id === kind)?.label || kind
}

// ─── Error popup ──────────────────────────────────────────
const errorModalOpen = ref(false)
const errorMessage = ref('')
const errorContext = ref(null)
function onViewError({ cred, message }) {
  errorContext.value = cred
  errorMessage.value = message || 'שגיאה לא ידועה'
  errorModalOpen.value = true
}
async function rerunFromError() {
  const id = errorContext.value?.id
  errorModalOpen.value = false
  if (id) await runNow(id)
}

// ─── Per-credential actions ───────────────────────────────
async function runNow(id) {
  try {
    await store.runNow(id)
  } catch (_) {
    // 409 = a run is already in-flight for this credential. Hydrate the
    // store so the OTP modal / progress UI binds to the live run instead
    // of throwing. Mirrors PortalAutomationDock.onRun.
    await store.hydrateActiveRun()
  }
}
async function deleteCred(id) {
  if (!confirm('למחוק את ההגדרה?')) return
  await store.deleteCredential(id)
}

// ─── OTP modal (shared across all card runs) ──────────────
onMounted(async () => {
  await store.fetchPortalKinds()
  await store.fetchCredentials()
  store.fetchLatestBatch()
  if (props.autoOpenAdd) {
    openAdd()
    emit('opened')
  }
})

// Activation checklist may set this after the tab is already mounted.
watch(() => props.autoOpenAdd, (v) => {
  if (v) {
    openAdd()
    emit('opened')
  }
})
// ── Gear backdrop (Remotion via a React island, like SetupProgressCard) ──
const gearsEl = ref(null)
const pageEl = ref(null)
// One gear per segment of page height — more portals, longer page, more gears.
const gearCount = ref(1)
const gearsReduced =
  typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
let gearsRoot = null
let gearsMods = null
let pageObserver = null
async function mountGears() {
  if (!gearsEl.value || gearsRoot) return
  try {
    const [rdClient, react, player, comp] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('@remotion/player'),
      import('../../remotion/AutomationGearsBackdrop'),
    ])
    if (!gearsEl.value || gearsRoot) return
    gearsMods = { react, player, comp }
    gearsRoot = rdClient.createRoot(gearsEl.value)
    paintGears()
    if (pageEl.value && typeof ResizeObserver !== 'undefined') {
      pageObserver = new ResizeObserver(measureGears)
      pageObserver.observe(pageEl.value)
    }
    measureGears()
  } catch (e) {
    console.error('[PortalAutomationTab] gears failed', e) // decorative — page works without it
  }
}
function measureGears() {
  const el = pageEl.value
  if (!el || !gearsMods) return
  const segPx = el.clientWidth * (gearsMods.comp.AUTOMATION_GEARS_SEGMENT_H / gearsMods.comp.AUTOMATION_GEARS_W)
  // clientHeight, not scrollHeight: the absolute gear layer itself must not
  // count, or each added gear would grow the page and add another.
  const n = Math.max(1, Math.ceil(el.clientHeight / Math.max(1, segPx)))
  if (n !== gearCount.value) {
    gearCount.value = n
    paintGears()
  }
}
function paintGears() {
  if (!gearsRoot || !gearsMods) return
  const { react, player, comp } = gearsMods
  gearsRoot.render(
      react.createElement(player.Player, {
        component: comp.AutomationGearsBackdrop,
        inputProps: { color: CHART_PALETTE[11], count: gearCount.value },
        durationInFrames: comp.AUTOMATION_GEARS_FRAMES,
        fps: 30,
        compositionWidth: comp.AUTOMATION_GEARS_W,
        compositionHeight: comp.automationGearsHeight(gearCount.value),
        autoPlay: true,
        loop: true,
        controls: false,
        clickToPlay: false,
        doubleClickToFullscreen: false,
        showPosterWhenUnplayed: false,
        acknowledgeRemotionLicense: true,
        style: { width: '100%', height: '100%', backgroundColor: 'transparent' },
      }),
  )
}
function unmountGears() {
  if (pageObserver) { pageObserver.disconnect(); pageObserver = null }
  if (gearsRoot) {
    try { gearsRoot.unmount() } catch { /* ignore */ }
    gearsRoot = null
  }
}
// The mount div only exists once there are portals — mount when it appears.
watch(gearsEl, (el) => { if (el) mountGears(); else unmountGears() })
onBeforeUnmount(unmountGears)

onUnmounted(() => {
  // Soft reset — an in-flight run-all batch must keep polling in the
  // background so its completion still refreshes the whole app.
  store.reset({ keepBatch: true })
})
</script>

<style scoped>
.auto-page {
  position: relative;
  min-height: 100%;
  padding: 26px 20px 48px;
  overflow: hidden;
  background: transparent;
}
.auto-gears {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
/* Spans the page's width and scrolls with it; its height (aspect-ratio, set
   inline) grows with the gear count so the stack runs the page's full length. */
.auto-gears-mount {
  position: absolute;
  top: 0;
  inset-inline: 0;
  direction: ltr; /* RTL root would shift the Remotion composition */
}
.auto-inner {
  position: relative;
  z-index: 1;
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ─── Dashboard grid: main panels + activity sidebar ────── */
.dash {
  display: grid;
  grid-template-columns: 1fr;
  gap: 16px;
  align-items: start;
}
@media (min-width: 1024px) {
  .dash:not(.dash--empty) {
    grid-template-columns: minmax(0, 1fr) 320px;
  }
}

/* ── No portal yet: welcome (photo dissolving into the card + slider) ── */
.au-welcome {
  position: relative; overflow: hidden; min-height: 380px; display: flex; align-items: center;
  border-radius: var(--radius-lg, 16px); border: 1px solid var(--border-subtle); background: var(--card-bg); box-shadow: var(--shadow-sm);
}
.au-welcome-photo {
  position: absolute; top: 0; bottom: 0; inset-inline-end: 0; width: 62%; z-index: 0; pointer-events: none;
  -webkit-mask-image: linear-gradient(to right, #000 0%, #000 48%, transparent 95%);
          mask-image: linear-gradient(to right, #000 0%, #000 48%, transparent 95%);
}
.au-welcome-photo video, .au-welcome-photo img { width: 100%; height: 100%; object-fit: cover; object-position: left center; display: block; }
.au-welcome-copy { position: relative; z-index: 1; width: min(440px, 48%); padding: 40px; display: flex; flex-direction: column; gap: 18px; }
.au-welcome-title {
  margin: 0; font-family: 'Heebo', sans-serif; font-weight: 900;
  font-size: clamp(28px, 3.2vw, 40px); line-height: 1.08; letter-spacing: -0.03em; color: var(--text);
}
.au-welcome-title span { color: #0A6664; }
.au-slider { display: flex; flex-direction: column; gap: 10px; width: min(380px, 100%); }
.au-slide-track { min-height: 52px; }
.au-slide, .au-steps-static li { display: flex; align-items: baseline; gap: 14px; }
.au-slide-n { flex-shrink: 0; font-size: 13px; font-weight: 800; letter-spacing: 0.06em; color: #0A6664; }
.au-slide div, .au-steps-static div { display: flex; flex-direction: column; gap: 2px; }
.au-slide strong, .au-steps-static strong { font-size: 18px; font-weight: 700; color: var(--text); }
.au-slide div span, .au-steps-static div span { font-size: 13.5px; color: var(--text-muted); }
.au-slide-enter-active { transition: opacity 0.26s ease-out, transform 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.au-slide-leave-active { transition: opacity 0.16s ease-in, transform 0.18s ease-in; }
.au-slide-enter-from { opacity: 0; transform: translateY(12px); }
.au-slide-leave-to { opacity: 0; transform: translateY(-8px); }
.au-bars { display: flex; gap: 6px; }
.au-bar { position: relative; flex: 1; height: 16px; padding: 0; border: none; background: none; cursor: pointer; }
.au-bar::before, .au-bar-fill { position: absolute; inset-inline: 0; top: 6px; height: 4px; border-radius: 99px; }
.au-bar::before { content: ''; background: var(--tab-automation-wash); }
.au-bar-fill { display: block; width: 0; inset-inline-end: auto; background: #0A6664; }
.au-bar--done .au-bar-fill { width: 100%; }
.au-bar--on .au-bar-fill { animation: au-fill 2.8s linear forwards; }
.au-bar--on.au-bar--paused .au-bar-fill { animation-play-state: paused; }
.au-bar:focus-visible { outline: 2px solid #0A6664; outline-offset: 2px; border-radius: 6px; }
@keyframes au-fill { from { width: 0; } to { width: 100%; } }
.au-steps-static { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }
@media (max-width: 860px) {
  .au-welcome { flex-direction: column; align-items: stretch; min-height: 0; }
  .au-welcome-photo { position: relative; width: 100%; height: 200px;
    -webkit-mask-image: linear-gradient(to bottom, #000 55%, transparent 100%);
            mask-image: linear-gradient(to bottom, #000 55%, transparent 100%); }
  .au-welcome-copy { width: auto; padding: 6px 20px 26px; }
}

.error-banner {
  background: rgba(234, 0, 30, 0.08);
  border: 1px solid rgba(234, 0, 30, 0.3);
  color: var(--red-deep);
  padding: 10px 14px;
  border-radius: var(--radius-sm, 8px);
  font-size: 13px;
}

.loading-strip {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px;
  color: var(--text-muted);
  font-size: 13px;
}
.spinner {
  width: 18px; height: 18px;
  border: 2px solid var(--border-subtle);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ─── Error popup modal ────────────────────────────────── */
.err-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 18, 28, 0.55);
  backdrop-filter: blur(3px);
  z-index: 1010;
  display: grid;
  place-items: center;
  padding: 20px;
}
.err-card {
  background: var(--card-bg, #fff);
  border-radius: 16px;
  width: 100%;
  max-width: 520px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.32);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.err-head {
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 14px;
  padding: 18px 20px 14px;
  background: linear-gradient(135deg, rgba(234, 0, 30, 0.10) 0%, transparent 70%);
  border-bottom: 1px solid var(--border-subtle);
}
.err-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: var(--red);
  color: #fff;
  display: grid;
  place-items: center;
  box-shadow: 0 4px 12px rgba(234, 0, 30, 0.38),
              inset 0 1px 0 rgba(255, 255, 255, 0.25);
  flex-shrink: 0;
}
.err-titles { min-width: 0; }
.err-title { margin: 0; font-size: 17px; font-weight: 800; color: var(--text); letter-spacing: -0.2px; }
.err-meta { margin: 3px 0 0; font-size: 12.5px; color: var(--text-muted); }
.err-x {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  background: var(--card-bg);
  display: grid;
  place-items: center;
  cursor: pointer;
  color: var(--text-muted);
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.err-x:hover { background: var(--bg); color: var(--text); border-color: var(--text-muted); }
.err-body {
  padding: 16px 20px;
  font-size: 13px;
  color: var(--text);
  line-height: 1.55;
  max-height: 50vh;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  background: var(--bg);
  border-bottom: 1px solid var(--border-subtle);
}
.err-foot {
  display: flex;
  gap: 8px;
  padding: 14px 20px;
  justify-content: flex-end;
}
.err-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: none;
  border-radius: 8px;
  padding: 9px 16px;
  font-family: inherit;
  font-weight: 700;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease, box-shadow 0.15s ease;
}
.err-btn--secondary {
  background: var(--bg);
  color: var(--text);
  border: 1px solid var(--border-subtle);
}
.err-btn--secondary:hover { background: var(--card-bg); border-color: var(--text-muted); }
.err-btn--primary {
  background: #0A6664;
  color: #fff;
  box-shadow: 0 4px 12px rgba(14, 140, 138, 0.30);
}
.err-btn--primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(14, 140, 138, 0.42);
}

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-active .err-card, .modal-leave-active .err-card { transition: transform 0.22s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.22s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .err-card, .modal-leave-to .err-card { opacity: 0; transform: translateY(8px) scale(0.96); }

@media (prefers-reduced-motion: reduce) {
  .spinner { animation: none; }
  .err-btn--primary:hover { transform: none; }
}
</style>
