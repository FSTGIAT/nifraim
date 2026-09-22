<template>
  <div class="cockpit">
    <span class="cockpit-orb" aria-hidden="true"></span>

    <!-- Section 1 — health gauge -->
    <div class="gauge">
      <svg viewBox="0 0 84 84" class="gauge-svg" aria-hidden="true">
        <defs>
          <linearGradient id="pg-ring" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stop-color="var(--chart-9, #2F73C4)" />
            <stop offset="0.5" stop-color="var(--chart-2, #4E9DD0)" />
            <stop offset="1" stop-color="var(--chart-12, #0E8C8A)" />
          </linearGradient>
        </defs>
        <circle cx="42" cy="42" r="35" fill="none" stroke="#E9ECF4" stroke-width="7" />
        <circle
          class="gauge-fill"
          cx="42" cy="42" r="35" fill="none"
          stroke="url(#pg-ring)" stroke-width="7" stroke-linecap="round"
          :stroke-dasharray="C" :stroke-dashoffset="ringOffset"
          transform="rotate(-90 42 42)"
        />
      </svg>
      <div class="gauge-center">
        <span class="gauge-num ltr-number">{{ healthyShown }}<span class="gauge-den">/{{ total }}</span></span>
        <span class="gauge-lbl">תקינים</span>
      </div>
    </div>

    <span class="cockpit-sep" aria-hidden="true"></span>

    <!-- Section 2 — stat tiles -->
    <div class="tiles">
      <div v-for="t in tiles" :key="t.key" class="tile">
        <span class="tile-ico" :style="{ background: t.soft, color: t.deep }" v-html="t.icon"></span>
        <div class="tile-body">
          <span class="tile-val ltr-number" :style="t.valueColor ? { color: t.valueColor } : null">{{ t.display }}</span>
          <span class="tile-lbl">{{ t.label }}</span>
        </div>
      </div>
    </div>

    <span class="cockpit-sep" aria-hidden="true"></span>

    <!-- Section 3 — the two workbooks the batch produces.
         These used to be a download icon on EVERY portal card: 18 buttons for
         2 files, and each one served the merged workbook for ALL companies
         regardless of the card it sat on, so the icon on "אלטשולר" promised
         Altshuler and delivered everyone. They belong beside the run stats —
         this band already reports what the batch did; these are what it made. -->
    <div class="files">
      <span class="files-lead">הקבצים המאוחדים</span>
      <div class="files-btns">
        <button v-for="f in MERGED_FILES" :key="f.path" class="file-btn" type="button"
                :disabled="busyFile === f.path" :title="f.hint" @click="download(f)">
          <span v-if="busyFile === f.path" class="file-spin" aria-hidden="true"></span>
          <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
          </svg>
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

const ICONS = {
  active: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2 3 14h8l-1 8 10-12h-8l1-8z"/></svg>',
  total: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3 9 5-9 5-9-5 9-5Z"/><path d="m3 13 9 5 9-5"/><path d="m3 17.5 9 5 9-5"/></svg>',
  last: '<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7.5V12l3 2"/></svg>',
}
// Tile accents ride the shared CHART_PALETTE (--chart-N tokens); status ink
// stays on the semantic brand tokens.
const HUE = {
  indigo: { soft: 'color-mix(in srgb, var(--chart-9, #2F73C4) 10%, white)', deep: 'var(--chart-9, #2F73C4)' },
  blue: { soft: 'color-mix(in srgb, var(--chart-2, #4E9DD0) 12%, white)', deep: 'var(--chart-14, #2C5F6B)' },
  purple: { soft: 'color-mix(in srgb, var(--chart-4, #8E44AD) 10%, white)', deep: 'var(--chart-4, #8E44AD)' },
}
const STATUS_INK = { green: 'var(--green-deep, #1B5E20)', amber: '#9A6B12', red: 'var(--red-deep, #C23934)' }

const total = computed(() => store.credentials.length)
const active = computed(() => store.credentials.filter((c) => c.is_active).length)
const healthy = computed(() => store.credentials.filter((c) => c.last_run_status === 'success').length)

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
const healthyShown = useCountUp(healthy)

// ── Ring draw ──
const C = +(2 * Math.PI * 35).toFixed(2)
const ringOffset = ref(C)
onMounted(() => {
  rafs.push(requestAnimationFrame(() => {
    const pct = total.value ? healthy.value / total.value : 0
    ringOffset.value = +(C * (1 - pct)).toFixed(2)
  }))
})
watch([healthy, total], () => {
  const pct = total.value ? healthy.value / total.value : 0
  ringOffset.value = +(C * (1 - pct)).toFixed(2)
})
onBeforeUnmount(() => rafs.forEach(cancelAnimationFrame))

const tiles = computed(() => [
  { key: 'total', label: 'סה״כ פורטלים', display: totalShown.value, icon: ICONS.total, ...HUE.indigo },
  { key: 'active', label: 'פעילים', display: activeShown.value, icon: ICONS.active, ...HUE.blue },
  { key: 'last', label: 'ריצה אחרונה', display: lastRun.value.value, icon: ICONS.last, ...HUE.purple, valueColor: STATUS_INK[lastRun.value.tone] || null },
])
</script>

<style scoped>
.cockpit {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 22px;
  padding: 18px 22px;
  border-radius: 18px;
  border: 1px solid color-mix(in srgb, var(--chart-9, #2F73C4) 12%, transparent);
  background:
    radial-gradient(120% 160% at 0% 0%, color-mix(in srgb, var(--chart-12, #0E8C8A) 6%, transparent) 0%, transparent 55%),
    linear-gradient(135deg, #FBFBFE 0%, #F5F8FD 100%);
  box-shadow: 0 10px 28px rgba(46, 60, 130, 0.06);
  flex-wrap: wrap;
}
.cockpit-orb {
  position: absolute;
  top: -60%; inset-inline-start: -6%;
  width: 40%; height: 200%;
  background: radial-gradient(circle, color-mix(in srgb, var(--chart-9, #2F73C4) 8%, transparent), transparent 68%);
  pointer-events: none;
}

/* ── Gauge ── */
.gauge { position: relative; flex-shrink: 0; width: 92px; height: 92px; }
.gauge-svg { width: 92px; height: 92px; display: block; }
.gauge-fill { transition: stroke-dashoffset 1s cubic-bezier(0.22, 1, 0.36, 1); }
.gauge-center {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1px;
}
.gauge-num { font-size: 21px; font-weight: 800; color: #181818; letter-spacing: -0.5px; line-height: 1; }
.gauge-den { font-size: 13px; font-weight: 700; color: rgba(24, 24, 24, 0.4); }
.gauge-lbl { font-size: 10.5px; font-weight: 700; color: var(--text-muted); }

.cockpit-sep { width: 1px; align-self: stretch; margin: 6px 0; background: linear-gradient(180deg, transparent, rgba(24,24,24,0.1), transparent); }

/* ── The merged workbooks ──
   Sits at the end of the band (visually far-left in RTL), behind the same
   hairline separator the gauge uses. Tokens come from the band's own blue
   (--chart-9), not the hero's gold: this strip is information, and the two
   downloads are its quietest element. */
.files {
  position: relative;
  flex: 0 0 auto;
  display: flex; flex-direction: column; gap: 7px;
}
.files-lead {
  font-size: 11px; font-weight: 700; letter-spacing: 0.02em;
  color: var(--text-secondary, #6b7280);
}
.files-btns { display: flex; gap: 8px; }
.file-btn {
  display: inline-flex; align-items: center; gap: 6px;
  height: 34px; padding: 0 12px; border-radius: 10px;
  background: #fff;
  border: 1px solid color-mix(in srgb, var(--chart-9, #2F73C4) 22%, transparent);
  color: var(--chart-9, #2F73C4);
  font-family: inherit; font-size: 12.5px; font-weight: 700; cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, transform 0.15s ease;
}
.file-btn:hover:not(:disabled) {
  background: color-mix(in srgb, var(--chart-9, #2F73C4) 8%, #fff);
  border-color: var(--chart-9, #2F73C4);
  transform: translateY(-1px);
}
.file-btn:focus-visible { outline: 2px solid var(--chart-9, #2F73C4); outline-offset: 2px; }
.file-btn:disabled { opacity: 0.6; cursor: progress; }
.file-btn svg { opacity: 0.7; }
.file-spin {
  width: 13px; height: 13px; border-radius: 50%;
  border: 2px solid currentColor; border-top-color: transparent;
  animation: fileSpin 0.7s linear infinite;
}
@keyframes fileSpin { to { transform: rotate(360deg); } }
/* Only rendered on failure, so it never affects the band's resting height. */
.files-err {
  max-width: 230px;
  font-size: 11.5px; font-weight: 600; line-height: 1.5;
  color: var(--red-deep, #C23934);
}
@media (prefers-reduced-motion: reduce) {
  .file-spin { animation-duration: 2s; }
  .file-btn:hover:not(:disabled) { transform: none; }
}

/* ── Stat tiles ── */
.tiles {
  position: relative;
  flex: 1; min-width: 220px;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
}
.tile {
  display: flex; align-items: center; gap: 12px;
  padding: 10px 12px;
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(24, 24, 24, 0.05);
}
.tile-ico { flex-shrink: 0; width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center; }
.tile-body { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
.tile-val { font-size: 21px; font-weight: 800; color: #181818; letter-spacing: -0.5px; line-height: 1.05; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tile-lbl { font-size: 11.5px; font-weight: 700; color: var(--text-muted); }

@media (prefers-reduced-motion: reduce) {
  .gauge-fill { transition: none; }
}
@media (max-width: 560px) {
  .cockpit-sep { display: none; }
  .gauge { margin: 0 auto; }
}
</style>
