<template>
  <!-- One calm capsule: three plain stats, each with its own bespoke line
       drawing (AutoStatArt — the HomeCardDrawing language), and the two merged
       workbooks as quiet pills at the end. Health X/Y lives in the portal wheel. -->
  <div class="cap">
    <div class="stats">
      <div v-for="t in tiles" :key="t.key" class="stat">
        <AutoStatArt :name="t.icon" :size="44" class="stat-ico" />
        <div class="stat-body">
          <span class="stat-val ltr-number">{{ t.display }}<i v-if="t.dot" class="stat-dot" :style="{ background: t.dot }"></i></span>
          <span class="stat-lbl">{{ t.label }}</span>
        </div>
      </div>
    </div>

    <!-- The two workbooks the batch produces (aggregate.py) — one each, not one per portal card. -->
    <div class="files">
      <span class="files-lead">הקבצים המאוחדים</span>
      <div class="files-btns">
        <button v-for="f in MERGED_FILES" :key="f.path" class="file-btn" type="button"
                :disabled="busyFile === f.path" :title="f.hint" @click="download(f)"
                @mouseenter="hoverFile = f.path" @mouseleave="hoverFile = null">
          <span v-if="busyFile === f.path" class="file-spin" aria-hidden="true"></span>
          <AutoStatArt v-else name="doc" :size="22" :hover="hoverFile === f.path" />
          <span>{{ f.label }}</span>
        </button>
      </div>
      <p v-if="fileError" class="files-err">{{ fileError }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import { relativeHebrew } from '../../utils/relativeTime.js'
import { downloadViaApi, XLSX_MIME } from '../../utils/downloadFile.js'
import AutoStatArt from './AutoStatArt.vue'


// The run-all batch folds every company into exactly two workbooks
// (services/portal_automation/aggregate.py), so there are exactly two things
// to download here — not one per portal.
const MERGED_FILES = [
  { path: '/production/commission-export.xlsx', label: 'נפרעים',
    fallback: 'נפרעים מאוחד.xlsx',
    hint: 'כל דוחות הנפרעים מכל החברות בקובץ אחד' },
  { path: '/production/export.xlsx', label: 'פרודוקציה',
    fallback: 'פרודוקציה מאוחדת.xlsx',
    hint: 'כל דוחות הפרודוקציה מכל החברות בקובץ אחד' },
]

const store = usePortalAutomationStore()

const busyFile = ref(null)
const hoverFile = ref(null)
const fileError = ref('')

async function download(f) {
  if (busyFile.value) return
  busyFile.value = f.path
  fileError.value = ''
  try {
    await downloadViaApi(f.path, f.fallback, XLSX_MIME)
  } catch (e) {
    // 404 means the merge has not produced this workbook yet — say so, rather
    // than leaving a button that appears to do nothing.
    fileError.value = e?.response?.status === 404
      ? `אין עדיין קובץ ${f.label} מאוחד — הריצו הורדה אוטומטית תחילה.`
      : `ההורדה של ${f.label} נכשלה.`
  } finally {
    busyFile.value = null
  }
}

// Status of the last run: a small semantic dot beside the plain-ink value
// (the value itself stays ink — no gold/amber numbers).
const TONE_DOT = { green: 'var(--green)', amber: 'var(--amber)', red: 'var(--red)' }

const total = computed(() => store.credentials.length)
const active = computed(() => store.credentials.filter((c) => c.is_active).length)

const lastRun = computed(() => {
  const b = store.latestBatch
  if (!b) return { value: '—', tone: null }
  const when = b.finished_at || b.started_at
  const txt = when ? relativeHebrew(when) : '—'
  const tone = b.status === 'failed' ? 'red' : b.status === 'partial' ? 'amber' : 'green'
  return { value: txt, tone }
})

// ── Count-up (client rAF; small easing entrance) ──
let rafs = []
function useCountUp(source) {
  const shown = ref(0)
  watch(source, (to) => {
    if (typeof to !== 'number') { shown.value = to; return }
    const from = typeof shown.value === 'number' ? shown.value : 0
    if (from === to) { shown.value = to; return }
    const start = performance.now(), dur = 650
    const step = (t) => {
      const p = Math.min(1, (t - start) / dur)
      const e = 1 - Math.pow(1 - p, 3)
      shown.value = Math.round(from + (to - from) * e)
      if (p < 1) rafs.push(requestAnimationFrame(step))
    }
    rafs.push(requestAnimationFrame(step))
  }, { immediate: true })
  return shown
}
const totalShown = useCountUp(total)
const activeShown = useCountUp(active)

onBeforeUnmount(() => rafs.forEach(cancelAnimationFrame))

const tiles = computed(() => [
  { key: 'total', label: 'סה״כ פורטלים', display: totalShown.value, icon: 'portals' },
  { key: 'active', label: 'פעילים', display: activeShown.value, icon: 'pulse' },
  { key: 'last', label: 'ריצה אחרונה', display: lastRun.value.value, icon: 'clock', dot: TONE_DOT[lastRun.value.tone] || null },
])
</script>

<style scoped>
.cap {
  --acc: var(--tab-automation, #0E8C8A);
  display: flex; align-items: center; gap: 24px; flex-wrap: wrap;
  padding: 16px 22px; border-radius: 22px;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-subtle);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.8) inset, 0 10px 30px rgba(24, 24, 24, 0.06);
  backdrop-filter: blur(10px);
}

/* stats: no tiles — icon, a thick number, a muted label */
.stats { flex: 1; min-width: 240px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
.stat { display: flex; align-items: center; gap: 14px; padding: 2px 0; }
.stat + .stat { padding-inline-start: 16px; border-inline-start: 1px solid var(--border-subtle); }
.stat-ico { color: var(--text-secondary); }
.stat-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.stat-val { display: inline-flex; align-items: center; gap: 8px; font-size: 26px; font-weight: 900; letter-spacing: -0.03em; line-height: 1.05; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.stat-dot { width: 7px; height: 7px; border-radius: 50%; flex: none; }
.stat-lbl { font-size: 12px; font-weight: 500; color: var(--text-muted); }

/* the merged workbooks — two quiet pills at the end */
.files { margin-inline-start: auto; display: flex; flex-direction: column; align-items: flex-end; gap: 6px; }
.files-lead { font-size: 11.5px; font-weight: 500; color: var(--text-muted); }
.files-btns { display: flex; gap: 8px; }
.file-btn {
  display: inline-flex; align-items: center; gap: 6px; height: 36px; padding: 0 14px; border-radius: 999px;
  background: transparent; border: 1px solid var(--border-subtle); color: var(--text);
  font-family: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.file-btn :deep(svg) { color: var(--text-secondary); }
.file-btn:hover:not(:disabled) { border-color: var(--acc); background: color-mix(in srgb, var(--acc) 6%, transparent); }
.file-btn:focus-visible { outline: 2px solid var(--acc); outline-offset: 2px; }
.file-btn:disabled { opacity: 0.6; cursor: progress; }
.file-spin { width: 13px; height: 13px; border-radius: 50%; border: 2px solid var(--acc); border-top-color: transparent; animation: fileSpin 0.7s linear infinite; }
@keyframes fileSpin { to { transform: rotate(360deg); } }
.files-err { margin: 0; max-width: 240px; font-size: 11.5px; font-weight: 600; line-height: 1.5; color: var(--red); }

@media (max-width: 760px) {
  .cap { gap: 16px; padding: 16px; }
  .stats { grid-template-columns: repeat(3, minmax(0, 1fr)); min-width: 0; flex-basis: 100%; }
  .stat { flex-direction: column; align-items: flex-start; gap: 6px; }
  .stat + .stat { padding-inline-start: 10px; }
  .stat-val { font-size: 20px; white-space: normal; line-height: 1.15; }
  .files { margin-inline-start: 0; width: 100%; align-items: stretch; }
  .files-btns > * { flex: 1; justify-content: center; }
}
@media (prefers-reduced-motion: reduce) {
  .file-spin { animation-duration: 2s; }
}
</style>
