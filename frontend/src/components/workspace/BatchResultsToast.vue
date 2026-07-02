<template>
  <!-- "Batch results ready" toast — fires when the run-all batch finishes while
       the user is anywhere but the automation tab (which shows its own banner). -->
  <Teleport to="body">
    <Transition name="brt">
      <div
        v-if="visible && batch"
        class="brt"
        role="status"
        aria-live="polite"
        @mouseenter="hovering = true"
        @mouseleave="hovering = false"
        @focusin="hovering = true"
        @focusout="hovering = false"
      >
        <!-- Status icon tile — the only tonal element besides the hairline -->
        <div class="brt-icon" :class="'brt-icon--' + tone" aria-hidden="true">
          <svg v-if="tone === 'ok'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>
          </svg>
          <svg v-else-if="tone === 'warn'" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4"/><path d="M12 17h.01"/>
          </svg>
          <svg v-else width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>
          </svg>
        </div>

        <div class="brt-main">
          <strong class="brt-title">{{ title }}</strong>
          <p class="brt-sub">{{ subtitle }}</p>
          <p v-if="batch.succeeded > 0 || batch.failed > 0" class="brt-counts">
            <template v-if="batch.succeeded === 1">חברה אחת הצליחה</template>
            <template v-else-if="batch.succeeded > 1"><span class="ltr-number">{{ batch.succeeded }}</span> חברות הצליחו</template>
            <template v-if="batch.failed > 0"><template v-if="batch.succeeded > 0"> · </template><span class="ltr-number">{{ batch.failed }}</span> נכשלו</template>
          </p>

          <div class="brt-actions">
            <template v-if="tone !== 'err'">
              <button class="brt-btn brt-btn--primary" type="button" @click="go('comparison')">צפה בהשוואה</button>
              <button class="brt-btn brt-btn--quiet" type="button" @click="go('production')">פרודוקציה</button>
            </template>
            <button v-else class="brt-btn brt-btn--primary" type="button" @click="go('portal-automation')">ליומן הריצות</button>
          </div>
        </div>

        <button class="brt-x" type="button" aria-label="סגור" @click="dismiss">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
          </svg>
        </button>

        <!-- Auto-dismiss hairline — pauses with the timer on hover/focus -->
        <div
          class="brt-hairline"
          :class="'brt-hairline--' + tone"
          :style="{ transform: 'scaleX(' + remainingMs / TOTAL_MS + ')' }"
        ></div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'

const props = defineProps({
  // Current content tab id, or '' when the user is on the home screen.
  activeTab: { type: String, default: '' },
})
const emit = defineEmits(['navigate'])
const store = usePortalAutomationStore()

const TOTAL_MS = 15000
const visible = ref(false)
const batch = ref(null)
const remainingMs = ref(TOTAL_MS)
const hovering = ref(false)
let timerHandle = null

const tone = computed(() => {
  const s = batch.value?.status
  if (s === 'failed') return 'err'
  if (s === 'partial') return 'warn'
  return 'ok'
})
const title = computed(() => {
  const s = batch.value?.status
  if (s === 'failed') return 'ההורדה האוטומטית נכשלה'
  if (s === 'partial') return 'ההורדה הסתיימה חלקית'
  return 'ההורדה האוטומטית הושלמה'
})
const subtitle = computed(() => {
  const s = batch.value?.status
  if (s === 'failed') return 'עבור ליומן הריצות לפרטים'
  if (s === 'partial' && batch.value?.error_message) return batch.value.error_message
  return 'קובץ פרודוקציה ונפרעים נטענו והושוו אוטומטית'
})

function _clearTimer() {
  if (timerHandle) {
    clearInterval(timerHandle)
    timerHandle = null
  }
}

function show(b) {
  batch.value = b
  visible.value = true
  remainingMs.value = TOTAL_MS
  hovering.value = false // the previous toast may have been closed via a click, leaving this stuck true
  _clearTimer()
  timerHandle = setInterval(() => {
    if (hovering.value) return
    remainingMs.value -= 100
    if (remainingMs.value <= 0) hide()
  }, 100)
}

function hide() {
  visible.value = false
  _clearTimer()
}

function dismiss() {
  // Local hide only — the store flag stays so the automation tab's inline
  // banner (PortalRunAllBar) still shows the finished batch.
  hide()
}

function go(tab) {
  hide()
  emit('navigate', tab)
}

// The store refreshes every consumer store BEFORE setting batchJustFinished,
// so by the time this fires the data behind the buttons is already fresh.
// The automation tab renders its own done-banner — no double announcement.
watch(() => store.batchJustFinished, (b) => {
  if (!b) {
    hide()
    return
  }
  if (props.activeTab === 'portal-automation') return
  // batchJustFinished is only cleared by the automation tab's banner — dedupe
  // by batch id (in the store, so it survives WorkspaceView remounts) so the
  // same completion isn't re-announced on every tab/home navigation.
  if (b.id && store.batchToastSeenId === b.id) return
  store.batchToastSeenId = b.id || null
  show(b)
}, { immediate: true })

// Landing on the automation tab means the banner takes over — hide the toast.
watch(() => props.activeTab, (tab) => {
  if (tab === 'portal-automation' && visible.value) hide()
})

onBeforeUnmount(_clearTimer)
</script>

<style scoped>
.brt {
  position: fixed;
  bottom: 24px;
  inset-inline-start: 24px;
  z-index: 1300; /* above CustomerDetailModal (1010), below tour (5000) */
  width: min(400px, calc(100vw - 32px));
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 12px;
  align-items: start;
  direction: rtl;
  font-family: 'Heebo', sans-serif;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow:
    0 18px 44px -10px rgba(24, 24, 24, 0.18),
    0 4px 12px rgba(24, 24, 24, 0.08);
  padding: 16px 16px 18px;
  overflow: hidden;
}

.brt-icon {
  width: 40px;
  height: 40px;
  border-radius: var(--radius-md);
  display: grid;
  place-items: center;
  flex-shrink: 0;
}
.brt-icon--ok   { background: var(--green-light); color: var(--green); }
.brt-icon--warn { background: var(--amber-light); color: var(--amber); }
.brt-icon--err  { background: var(--red-light);   color: var(--red-deep); }

.brt-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.brt-title {
  font-size: 14.5px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.2px;
  line-height: 1.3;
}
.brt-sub {
  margin: 0;
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.45;
  overflow-wrap: anywhere;
}
.brt-counts {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.brt-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 9px;
}
.brt-btn {
  border: none;
  border-radius: var(--radius-sm);
  padding: 8px 15px;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease, border-color 0.15s ease;
}
.brt-btn--primary {
  background: linear-gradient(135deg, var(--primary), var(--accent-cyan));
  color: #fff;
  box-shadow: 0 4px 10px rgba(245, 124, 0, 0.28);
}
.brt-btn--primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 18px rgba(245, 124, 0, 0.38);
}
.brt-btn--quiet {
  background: var(--bg);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
}
.brt-btn--quiet:hover { color: var(--text); border-color: var(--text-muted); }
.brt-btn:focus-visible { outline: 2px solid var(--primary); outline-offset: 2px; }

/* Dismiss — 44px touch target, visually compact via negative margins */
.brt-x {
  width: 44px;
  height: 44px;
  margin: -8px -8px 0 0;
  border: none;
  background: transparent;
  color: var(--text-muted);
  display: grid;
  place-items: center;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: color 0.15s ease, background 0.15s ease;
}
.brt-x:hover { color: var(--text); background: var(--bg); }
.brt-x:focus-visible { outline: 2px solid var(--primary); outline-offset: -2px; }

/* Auto-dismiss hairline — shrinks toward the inline-end (right→left in RTL) */
.brt-hairline {
  position: absolute;
  bottom: 0;
  inset-inline: 0;
  height: 2px;
  transform-origin: right center;
  transition: transform 0.1s linear;
}
.brt-hairline--ok   { background: var(--green); }
.brt-hairline--warn { background: var(--amber); }
.brt-hairline--err  { background: var(--red); }

/* Enter/leave — transform + opacity only */
.brt-enter-active {
  transition:
    transform 0.26s cubic-bezier(0.34, 1.45, 0.64, 1),
    opacity 0.22s ease-out;
}
.brt-leave-active {
  transition:
    transform 0.18s ease-in,
    opacity 0.16s ease-in;
}
.brt-enter-from { opacity: 0; transform: translateY(18px) scale(0.97); }
.brt-leave-to   { opacity: 0; transform: translateY(10px) scale(0.98); }

@media (prefers-reduced-motion: reduce) {
  .brt-enter-active, .brt-leave-active { transition: opacity 0.2s ease; }
  .brt-enter-from, .brt-leave-to { transform: none; }
  .brt-btn--primary:hover { transform: none; }
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}
</style>
