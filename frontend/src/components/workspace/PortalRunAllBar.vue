<template>
  <div class="runall">
    <!-- Run-all-portals bar: one click downloads every active portal, then
         aggregates into one production + one נפרעים file and runs the compare. -->
    <div class="runall-bar">
      <!-- MetalButton — 3-layer metallic CTA (outer edge / inner sheen / face) -->
      <div class="metal" :class="{ 'metal--disabled': anyRunning || !!store.activeBatchId }">
        <span class="metal__inner" aria-hidden="true"></span>
        <button
          class="metal__btn"
          :disabled="anyRunning || !!store.activeBatchId"
          @click="onRunAll"
        >
          <span class="metal__shine" aria-hidden="true"></span>
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none"
               stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M12 3v12" />
            <path d="m7 10 5 5 5-5" />
            <path d="M5 21h14" />
          </svg>
          <span>הורדה אוטומטית מכל החברות</span>
        </button>
      </div>
      <span v-if="activeCredCount" class="runall-hint">{{ activeCredCount }} חברות מחוברות</span>
      <!-- Local worker liveness: is the agent's computer on & ready to run? -->
      <span class="worker-chip" :class="worker.online ? 'worker-chip--on' : 'worker-chip--off'"
            :title="workerTitle">
        <span class="worker-dot" aria-hidden="true"></span>
        {{ worker.online ? 'המחשב מחובר' : 'המחשב מנותק' }}
      </span>
    </div>

    <!-- Offline warning: clicking download won't do anything until the computer is on -->
    <div v-if="!worker.online" class="worker-warn">
      ההורדה רצה מהמחשב המקומי. ודאו שתוכנת Nifraim פועלת והמחשב דולק כדי להוריד נתונים.
    </div>

    <!-- Live batch progress -->
    <div v-if="batch && !batchDone" class="batch-progress">
      <div class="batch-progress__head">
        <span class="batch-spinner" aria-hidden="true"></span>
        <span>מוריד ומאחד נתונים — {{ batch.succeeded + batch.failed }}/{{ batch.total || '…' }}</span>
      </div>
      <div class="batch-pills">
        <span
          v-for="run in (batch.runs || [])"
          :key="run.id"
          class="batch-pill"
          :class="'batch-pill--' + statusTone(run.status)"
        >
          {{ labelForRun(run) }}
        </span>
      </div>
    </div>

    <!-- Batch finished → results-ready affordance -->
    <div v-if="batchDone" class="batch-done" :class="'batch-done--' + batchDone.status">
      <div class="batch-done__text">
        <strong>{{ batchDoneTitle }}</strong>
        <span>{{ batchDone.succeeded }} הצליחו · {{ batchDone.failed }} נכשלו</span>
      </div>
      <button class="batch-done__cta" @click="onViewResults">צפה בתוצאות</button>
      <button class="batch-done__dismiss" aria-label="סגור" @click="dismissBatchDone">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true">
          <path d="M18 6 6 18M6 6l12 12" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onUnmounted } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import { useComparisonStore } from '../../stores/comparison.js'
import { brandFor } from '../../utils/companyBrand.js'

const emit = defineEmits(['view-results'])
const store = usePortalAutomationStore()
const comparisonStore = useComparisonStore()

// ── Local worker liveness chip ──
const worker = computed(() => store.workerStatus || { online: false })
const workerTitle = computed(() => {
  if (worker.value.online) {
    return worker.value.current_job
      ? `פעיל: ${worker.value.current_job}`
      : `מחובר${worker.value.hostname ? ' (' + worker.value.hostname + ')' : ''}`
  }
  return worker.value.last_seen
    ? `נראה לאחרונה: ${new Date(worker.value.last_seen).toLocaleString('he-IL')}`
    : 'המחשב המקומי לא מחובר'
})
let workerPoll = null
onMounted(() => {
  store.fetchWorkerStatus()
  workerPoll = setInterval(() => store.fetchWorkerStatus(), 20000)
})
onUnmounted(() => { if (workerPoll) clearInterval(workerPoll) })

const batch = computed(() => store.activeBatch)
const batchDone = ref(null)
const anyRunning = computed(() => !!store.activeRunId)
const activeCredCount = computed(
  () => (store.credentials || []).filter((c) => c.is_active).length,
)
const batchDoneTitle = computed(() => {
  const s = batchDone.value?.status
  if (s === 'failed') return 'ההורדה נכשלה'
  if (s === 'partial') return 'ההורדה הסתיימה (חלקית)'
  return 'ההשוואה מוכנה'
})

function portalLabel(kind) {
  return store.portalKinds.find((k) => k.id === kind)?.label || brandFor(kind).label
}
function statusTone(status) {
  if (status === 'success') return 'ok'
  if (['failed', 'timeout'].includes(status)) return 'fail'
  if (['running', 'awaiting_otp', 'downloading', 'parsing', 'pending'].includes(status)) return 'live'
  return 'idle'
}
function labelForRun(run) {
  const cred = store.credentials.find((c) => c.id === run.credential_id)
  return cred ? portalLabel(cred.portal_kind) : 'פורטל'
}

async function onRunAll() {
  batchDone.value = null
  try {
    await store.runAllPortals()
  } catch (_) {
    // store.error already populated; the host page renders it.
  }
}

function onViewResults() {
  dismissBatchDone()
  emit('view-results')
}
function dismissBatchDone() {
  batchDone.value = null
  store.batchJustFinished = null
}

// When the batch finishes, refresh the comparison views so the merged results
// show up without a manual reload, then surface the "results ready" affordance.
watch(() => store.batchJustFinished, async (b) => {
  if (!b) return
  batchDone.value = b
  store.activeBatchId = null
  try {
    await Promise.all([
      comparisonStore.fetchLatest('gemel_hishtalmut'),
      comparisonStore.fetchLatest('insurance'),
      comparisonStore.fetchCompanySummary(),
    ])
  } catch (_) {}
})
</script>

<style scoped>
.runall {
  display: flex;
  flex-direction: column;
  gap: 12px;
  font-family: 'Heebo', sans-serif;
}

/* ───── Run-all bar ───── */
.runall-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
/* ── MetalButton (success/green) — faithful 3-layer metallic CTA ───────── */
.metal {
  position: relative;
  display: inline-flex;
  padding: 1.25px;                /* the outer metallic edge */
  border-radius: 13px;
  background: linear-gradient(to bottom, #005A43, #7CCB9B);
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12);
  transition: transform 250ms cubic-bezier(0.1, 0.4, 0.2, 1),
              box-shadow 250ms cubic-bezier(0.1, 0.4, 0.2, 1);
  transform-origin: center;
}
.metal:hover { box-shadow: 0 6px 16px rgba(0, 0, 0, 0.16); }
/* press physics — whole stack sinks (uses :has so no JS needed) */
.metal:has(.metal__btn:active) {
  transform: translateY(2.5px) scale(0.99);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.18);
}
.metal__inner {
  position: absolute;
  inset: 1px;
  border-radius: 12px;
  background: linear-gradient(to bottom, #E5F8F0, #00352F 55%, #D1F0E6);
  transition: filter 250ms cubic-bezier(0.1, 0.4, 0.2, 1);
  pointer-events: none;
}
.metal:hover .metal__inner { filter: brightness(1.06); }
.metal__btn {
  position: relative;
  z-index: 1;
  margin: 1px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  height: 50px;
  padding: 0 28px;
  border: none;
  border-radius: 11px;
  background: linear-gradient(to bottom, #9ADBC8, #3E8F7C);
  color: #FFF7F0;
  font-family: inherit;
  font-size: 15.5px;
  font-weight: 800;
  letter-spacing: 0.1px;
  line-height: 1;
  cursor: pointer;
  overflow: hidden;
  outline: none;
  text-shadow: 0 -1px 0 rgba(6, 78, 59, 0.9);
  transition: filter 250ms cubic-bezier(0.1, 0.4, 0.2, 1),
              transform 250ms cubic-bezier(0.1, 0.4, 0.2, 1);
  transform-origin: center;
}
.metal__btn:hover { filter: brightness(1.03); }
.metal__btn:active { transform: scale(0.97); }
.metal__btn svg { filter: drop-shadow(0 -1px 0 rgba(6, 78, 59, 0.55)); }
/* shine sweep that flashes on press */
.metal__shine {
  position: absolute;
  inset: 0;
  border-radius: 11px;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.55), transparent);
  opacity: 0;
  transition: opacity 300ms ease;
  pointer-events: none;
}
.metal__btn:active .metal__shine { opacity: 0.25; }
.metal__btn:focus-visible { outline: 2px solid #1FA88C; outline-offset: 4px; }
.metal--disabled { opacity: 0.5; box-shadow: none; }
.metal--disabled .metal__btn { cursor: not-allowed; }
.runall-hint {
  font-size: 12.5px;
  color: var(--text-secondary, #6b7280);
}

/* ───── Local worker liveness chip ───── */
.worker-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 700;
  border: 1px solid transparent;
}
.worker-chip--on  { background: rgba(16, 185, 129, 0.12); color: #047857; border-color: rgba(16,185,129,0.3); }
.worker-chip--off { background: rgba(107,114,128,0.1); color: #6b7280; border-color: rgba(107,114,128,0.24); }
.worker-dot {
  width: 9px; height: 9px; border-radius: 50%;
  background: currentColor;
  flex-shrink: 0;
}
.worker-chip--on .worker-dot {
  background: #10b981;
  box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5);
  animation: worker-pulse 1.8s ease-out infinite;
}
@keyframes worker-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.5); }
  70%  { box-shadow: 0 0 0 7px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}
.worker-warn {
  font-size: 12.5px;
  color: var(--red-deep, #b45309);
  background: rgba(244, 211, 94, 0.14);
  border: 1px solid rgba(216, 168, 0, 0.3);
  border-radius: 10px;
  padding: 9px 13px;
}

/* ───── Batch progress ───── */
.batch-progress {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  background: rgba(31, 168, 140, 0.06);
  border: 1px solid rgba(31, 168, 140, 0.2);
  border-radius: 12px;
}
.batch-progress__head {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-primary, #1a1a1a);
}
.batch-spinner {
  width: 15px;
  height: 15px;
  border: 2.5px solid rgba(31, 168, 140, 0.25);
  border-top-color: #1FA88C;
  border-radius: 50%;
  animation: batch-spin 0.8s linear infinite;
  flex-shrink: 0;
}
@keyframes batch-spin { to { transform: rotate(360deg); } }
.batch-pills {
  display: flex;
  flex-wrap: wrap;
  gap: 7px;
}
.batch-pill {
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid transparent;
}
.batch-pill--ok   { background: rgba(16, 185, 129, 0.12); color: #047857; border-color: rgba(16,185,129,0.3); }
.batch-pill--fail { background: rgba(234, 0, 30, 0.1);   color: var(--red-deep, #b91c1c); border-color: rgba(234,0,30,0.28); }
.batch-pill--live { background: rgba(78, 157, 208, 0.14); color: #1f6f9e; border-color: rgba(78,157,208,0.34); }
.batch-pill--idle { background: rgba(107,114,128,0.1);  color: #6b7280; border-color: rgba(107,114,128,0.24); }

/* ───── Batch done banner ───── */
.batch-done {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 13px 16px;
  border-radius: 12px;
  background: rgba(16, 185, 129, 0.08);
  border: 1px solid rgba(16, 185, 129, 0.28);
}
.batch-done--failed  { background: rgba(234,0,30,0.07); border-color: rgba(234,0,30,0.26); }
.batch-done--partial { background: rgba(244,211,94,0.14); border-color: rgba(216,168,0,0.32); }
.batch-done__text { display: flex; flex-direction: column; gap: 2px; }
.batch-done__text strong { font-size: 14px; color: var(--text-primary, #1a1a1a); }
.batch-done__text span { font-size: 12px; color: var(--text-secondary, #6b7280); }
.batch-done__cta {
  margin-inline-start: auto;
  padding: 8px 16px;
  border: none;
  border-radius: 9px;
  background: #1FA88C;
  color: #fff;
  font-family: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}
.batch-done__cta:hover { background: #178f78; }
.batch-done__dismiss {
  display: inline-flex;
  border: none;
  background: transparent;
  color: var(--text-secondary, #6b7280);
  cursor: pointer;
  padding: 4px 6px;
  line-height: 1;
}
</style>
