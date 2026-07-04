<template>
  <div class="runall">
    <!-- Hero: title + one-click run-all + add, over a cool gradient with Kling art.
         One click downloads every active portal, aggregates into one production +
         one נפרעים file, and runs the compare. -->
    <span class="hero-orb" aria-hidden="true"></span>
    <div class="hero-main">
      <div class="hero-copy">
        <span class="hero-kicker">אוטומציה</span>
        <h2 class="hero-title">פורטלי חברות הביטוח</h2>
        <p class="hero-sub">
          <template v-if="activeCredCount">כל החברות במקום אחד — {{ heroSubText }}, בלחיצה אחת מורידים ומשווים את הכל.</template>
          <template v-else>מחברים פורטל אחד, וקוד האימות מגיע לבד מהטלפון — מכאן ההורדות רצות בשבילכם.</template>
        </p>
        <div class="hero-actions">
          <button
            class="hero-run"
            :disabled="anyRunning || !!store.activeBatchId"
            @click="onRunAll"
          >
            <svg viewBox="0 0 24 24" width="19" height="19" fill="none"
                 stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M12 3v12" /><path d="m7 10 5 5 5-5" /><path d="M5 21h14" />
            </svg>
            <span>הורדה אוטומטית מכל החברות</span>
          </button>
          <button class="hero-add" type="button" @click="$emit('add')">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M5 12h14" /><path d="M12 5v14" />
            </svg>
            <span>הוסף פורטל</span>
          </button>
        </div>
      </div>
      <div class="hero-art" aria-hidden="true">
        <img :src="heroImg" alt="" />
      </div>
    </div>

    <!-- Live batch progress -->
    <div v-if="batchLive && !batchDone" class="batch-progress">
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
import { computed, ref, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import { brandFor, brandForLabel } from '../../utils/companyBrand.js'
import heroImg from '../../assets/automation/hero.webp'

const emit = defineEmits(['view-results', 'add'])
const store = usePortalAutomationStore()

const BATCH_TERMINAL = new Set(['success', 'partial', 'failed'])
const batch = computed(() => store.activeBatch)
// activeBatch keeps its terminal payload until the next batch — only show
// the live-progress strip while the batch is actually running.
const batchLive = computed(() => !!batch.value && !BATCH_TERMINAL.has(batch.value.status))
const batchDone = ref(null)
const anyRunning = computed(() => !!store.activeRunId)
const activeCredCount = computed(
  () => (store.credentials || []).filter((c) => c.is_active).length,
)
// Credentials are report SOURCES (a company can expose several report kinds),
// so the subtitle counts both: "N דוחות מ־M חברות".
const activeCompanyCount = computed(() => {
  const companies = new Set()
  for (const c of (store.credentials || []).filter((c) => c.is_active)) {
    const lbl = portalLabel(c.portal_kind)
    const b = brandForLabel(lbl)
    companies.add(b.label && b.label !== '?' ? b.label : lbl)
  }
  return companies.size
})
const heroSubText = computed(() => {
  const reports = activeCredCount.value
  const companies = activeCompanyCount.value
  const reportsPart = reports === 1 ? 'דוח אוטומטי אחד' : `${reports} דוחות אוטומטיים`
  const companiesPart = companies === 1 ? 'מחברה אחת' : `מ־${companies} חברות`
  return `${reportsPart} ${companiesPart}`
})
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

// The store owns all post-batch side effects (data refresh happens BEFORE
// batchJustFinished is set) — here we only control the local done banner.
// immediate: the flag may have been set while this component was unmounted.
watch(() => store.batchJustFinished, (b) => {
  batchDone.value = b || null
}, { immediate: true })
</script>

<style scoped>
.runall {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 14px;
  font-family: 'Heebo', sans-serif;
  padding: 26px 28px;
  border-radius: 22px;
  border: 1px solid rgba(91, 110, 225, 0.14);
  background:
    radial-gradient(130% 150% at 100% 0%, rgba(142, 111, 214, 0.13) 0%, transparent 52%),
    linear-gradient(135deg, #F6F7FE 0%, #F3F8FD 48%, #F1FBF7 100%);
  box-shadow: 0 10px 30px rgba(46, 60, 130, 0.07);
}
.hero-orb {
  position: absolute;
  top: -55%; inset-inline-end: 8%;
  width: 46%; height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.7), transparent 68%);
  pointer-events: none;
}

/* ───── Hero row ───── */
.hero-main {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 26px;
  flex-wrap: wrap;
}
.hero-copy { flex: 1 1 320px; min-width: 260px; display: flex; flex-direction: column; gap: 7px; }
.hero-kicker {
  align-self: flex-start;
  font-size: 11.5px; font-weight: 800; letter-spacing: 0.04em;
  color: #0E7A64; background: #E4F5F0;
  border-radius: 999px; padding: 4px 12px;
}
.hero-title {
  margin: 2px 0 0;
  font-size: clamp(22px, 2.6vw, 30px);
  font-weight: 800;
  color: #181818;
  letter-spacing: -0.5px;
  line-height: 1.1;
}
.hero-sub { margin: 0; font-size: 14px; line-height: 1.5; color: rgba(24, 24, 24, 0.55); max-width: 46ch; }
.hero-actions { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }

.hero-run {
  display: inline-flex; align-items: center; justify-content: center; gap: 10px;
  height: 50px; padding: 0 26px; border: none; border-radius: 14px;
  background: linear-gradient(135deg, #5B6EE1 0%, #4E9DD0 55%, #1FA88C 100%);
  color: #fff; font-family: inherit; font-size: 15px; font-weight: 800; letter-spacing: 0.1px;
  cursor: pointer;
  box-shadow: 0 8px 22px rgba(78, 157, 208, 0.36);
  transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}
.hero-run:hover:not(:disabled) { transform: translateY(-2px); box-shadow: 0 12px 30px rgba(78, 157, 208, 0.46); filter: brightness(1.04); }
.hero-run:active:not(:disabled) { transform: translateY(0); }
.hero-run:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }
.hero-run:focus-visible { outline: 2px solid #5B6EE1; outline-offset: 3px; }

.hero-add {
  display: inline-flex; align-items: center; gap: 7px;
  height: 50px; padding: 0 20px; border-radius: 14px;
  background: rgba(255, 255, 255, 0.72); border: 1.5px solid rgba(91, 110, 225, 0.28);
  color: #3A4BC0; font-family: inherit; font-size: 14px; font-weight: 700; cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}
.hero-add:hover { background: #fff; border-color: #5B6EE1; transform: translateY(-1px); }
.hero-add:focus-visible { outline: 2px solid #5B6EE1; outline-offset: 2px; }

.hero-art { flex: 0 0 auto; width: min(292px, 38%); line-height: 0; }
.hero-art img { width: 100%; height: auto; display: block; }
@media (max-width: 620px) { .hero-art { display: none; } }

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
