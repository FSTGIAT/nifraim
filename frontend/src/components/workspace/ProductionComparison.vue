<template>
  <div ref="rootEl" class="prod-comparison">
    <ProdSectionHero
      v-if="!comparisonResult && !comparing"
      kicker="השוואת קבצים"
      title="חודש מול"
      accent="חודש"
      :line="history.length ? 'בחרו חודש — ונראה מי הצטרף, מי עזב ומה השתנה.' : 'כשיגיע קובץ הפרודוקציה הבא — נראה כאן מי הצטרף, מי עזב ומה השתנה.'"
      scene="prod-compare"
    />

    <!-- No history: what this screen will show, as a preview -->
    <div v-if="!history.length && !comparisonResult" class="pc-preview">
      <article v-for="c in PREVIEW" :key="c.key" class="pc-card" :style="{ '--k': c.color, '--k-ink': c.ink }">
        <span class="pc-ic" aria-hidden="true">
          <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">
            <template v-if="c.key === 'new'"><circle cx="9" cy="8" r="3.5" fill="currentColor" fill-opacity="0.18"/><path d="M2.5 20v-1a5 5 0 0 1 5-5h3a5 5 0 0 1 5 5v1"/><path d="M19 8v6M16 11h6"/></template>
            <template v-else-if="c.key === 'gone'"><circle cx="9" cy="8" r="3.5" fill="currentColor" fill-opacity="0.18"/><path d="M2.5 20v-1a5 5 0 0 1 5-5h3a5 5 0 0 1 5 5v1"/><path d="M16 11h6"/></template>
            <template v-else><path d="M4 7h13l-3-3M20 17H7l3 3" /><circle cx="12" cy="12" r="2.2" fill="currentColor" fill-opacity="0.18"/></template>
          </svg>
        </span>
        <strong>{{ c.title }}</strong>
        <span>{{ c.text }}</span>
        <ul class="pc-sample" aria-hidden="true">
          <li v-for="n in 2" :key="n" :style="{ '--d': (n - 1) * 0.35 + 's' }">
            <i class="pc-av"></i>
            <i class="pc-name" :style="{ width: (70 - n * 12) + '%' }"></i>
            <b class="pc-chip">{{ c.chip }}</b>
          </li>
        </ul>
      </article>
    </div>

    <!-- Pick the earlier file: only full production files that cover the
         same insurers as the current one (a single-insurer .DAT against the
         merged file reported hundreds of fake joiners/leavers). One tap runs
         the comparison — no separate button. -->
    <section v-else-if="!comparisonResult && !comparing" class="pcx-card pcx-pick">
      <div class="pcx-pick-head">
        <h3 class="pcx-title">השוואה לחודש</h3>
        <span v-if="currentFile" class="pcx-pick-cur">
          {{ fileMonth(currentFile) }}
          <small class="ltr-number">{{ (currentFile.record_count || 0).toLocaleString() }} רשומות</small>
        </span>
      </div>
      <p v-if="!comparable.length" class="pcx-pick-none">
        עוד אין קובץ פרודוקציה קודם עם אותן חברות.
      </p>
      <div v-else class="pcx-pick-grid">
        <button v-for="(f, i) in comparable" :key="f.id" type="button" class="pcx-pick-file"
                :class="{ 'is-first': i === 0 }" @click="runCompare(f.id)">
          <span class="pcx-pf-month">{{ fileMonth(f) }}</span>
          <span class="pcx-pf-name" :title="f.filename">{{ f.filename.replace(/\.(xlsx?|dat|zip)$/i, '') }}</span>
          <span class="pcx-pf-meta">
            <span><b class="ltr-number">{{ (f.record_count || 0).toLocaleString() }}</b> רשומות</span>
            <span v-if="f.companies?.length"><b class="ltr-number">{{ coSet(f).size }}</b> חברות</span>
          </span>
          <svg class="pcx-pf-go" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>
          </svg>
        </button>
      </div>
    </section>

    <!-- Comparing -->
    <div v-else-if="comparing" class="loading-state">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring delay"></div>
      </div>
      <span>משווה קבצים...</span>
    </div>

    <!-- Results -->
    <div v-else-if="comparisonResult" class="results-section">
      <!-- Head: which two files + search, joined with the change KPIs -->
      <section class="pcx-card pcx-head">
        <div class="pcx-files">
          <div class="pcx-file pcx-file--cur">
            <b>{{ currentMonthLabel }}</b>
            <small v-if="S.current_date" class="ltr-number">{{ formatDate(S.current_date) }}</small>
          </div>
          <svg class="pcx-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>
          </svg>
          <button type="button" class="pcx-file pcx-file--prev" title="השוואה לקובץ אחר" @click="$emit('reset')">
            <b :title="S.previous_filename">{{ previousMonthLabel }}</b>
            <small v-if="S.previous_date" class="ltr-number">{{ formatDate(S.previous_date) }}</small>
            <svg class="pcx-swap" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="m16 3 4 4-4 4"/><path d="M20 7H4"/><path d="m8 21-4-4 4-4"/><path d="M4 17h16"/>
            </svg>
          </button>
          <button type="button" class="pcx-search" @click="openSearch($event.currentTarget)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <span>חיפוש לקוח</span>
          </button>
        </div>

        <div v-if="changedInsights.totalClients" class="pcx-kpis">
          <button v-for="k in kpis" :key="k.key" type="button" class="pcx-kpi"
                  :disabled="!k.count" @click="openChangedByType(k.field, $event.currentTarget)">
            <span class="pcx-kpi-val ltr-number">{{ k.value }}</span>
            <span class="pcx-kpi-lbl">{{ k.label }}</span>
          </button>
        </div>
      </section>

      <!-- התפלגות שינויים: the donut and its four counts in one card -->
      <section class="pcx-card pcx-dist">
        <h3 class="pcx-title">התפלגות שינויים</h3>
        <div class="pcx-dist-body">
          <div class="pcx-counts">
            <button v-for="(cat, i) in CATEGORIES" :key="cat.key" type="button" class="pcx-count"
                    :disabled="cat.key === 'unchanged' || !chartSeries[i]"
                    @click="openCategory(cat.key, $event.currentTarget)">
              <span class="pcx-count-bar" :style="{ background: cat.color }" aria-hidden="true"></span>
              <span class="pcx-count-lbl">{{ cat.label }}</span>
              <span class="pcx-count-val ltr-number">{{ (chartSeries[i] || 0).toLocaleString() }}</span>
              <span class="pcx-count-pct ltr-number">{{ pctOf(chartSeries[i]) }}</span>
            </button>
          </div>
          <div class="pcx-donut">
            <apexchart type="donut" height="360" :options="chartOptions" :series="chartSeries"
                       @dataPointSelection="onChartClick" />
          </div>
        </div>
      </section>

      <!-- By company -->
      <div v-if="companyCharts.length" class="pcx-grid">
        <section v-for="cc in companyCharts" :key="cc.key" class="pcx-card pcx-co">
          <h3 class="pcx-title">{{ cc.title }} <span class="pcx-badge ltr-number">{{ cc.total }}</span></h3>
          <apexchart type="donut" height="300" :options="cc.options" :series="cc.series"
                     @dataPointSelection="(e, chart, config) => onCompanyChartClick(cc.key, cc.labels, config)" />
        </section>
      </div>

      <!-- Biggest movers -->
      <section v-if="topChangersData.length" class="pcx-card">
        <div class="pcx-title-row">
          <h3 class="pcx-title">גדולי השינויים</h3>
          <div class="pcx-seg" role="group" aria-label="מדד">
            <button :class="{ on: barMode === 'accumulation' }" @click="barMode = 'accumulation'">צבירה</button>
            <button :class="{ on: barMode === 'premium' }" @click="barMode = 'premium'">פרמיה</button>
          </div>
        </div>
        <apexchart type="bar" :height="Math.max(220, topChangersData.length * 38 + 40)"
                   :options="topChangersChartOptions" :series="topChangersChartSeries"
                   @dataPointSelection="onBarChartClick" />
      </section>
    </div>

    <!-- Every drill: the app's shell, grown from what was pressed -->
    <DataModal :open="drill.open" :origin="drillOrigin" :title="drill.title" :badge="drill.rows.length"
               accent="var(--tab-production)" @close="drill.open = false">
      <CompareDrill v-if="drill.open" :rows="drill.rows" :mode="drill.mode" :title="drill.title"
                    :open-id="drill.openId" :focus="drill.mode === 'all'" />
    </DataModal>
  </div>
</template>

<script setup>
import ProdSectionHero from './ProdSectionHero.vue'
// What the file-to-file comparison shows once there are two files.
const PREVIEW = [
  { key: 'new', title: 'לקוחות חדשים', text: 'מי הצטרף מאז הקובץ הקודם', color: 'var(--tab-production)', ink: 'var(--tab-production)', chip: '+' },
  { key: 'gone', title: 'לקוחות שעזבו', text: 'מי כבר לא מופיע', color: 'var(--tab-production)', ink: 'var(--tab-production)', chip: '−' },
  { key: 'changed', title: 'שינויים', text: 'פרמיה, צבירה ומוצרים שזזו', color: 'var(--tab-production)', ink: 'var(--tab-production)', chip: '±' },
]

import { ref, reactive, computed, shallowRef, onMounted, onBeforeUnmount } from 'vue'
import DataModal from './DataModal.vue'
import CompareDrill from './CompareDrill.vue'
import { assignCompanyColors } from '../../utils/chartPalette.js'
import { BASE_CHART, signedMoney } from '../../utils/chartDefaults'
import { useScrollReveal } from '../../composables/useScrollReveal'
import { shortCompany as shortCo } from '../../utils/companyShort.js'

const props = defineProps({
  history: { type: Array, default: () => [] },
  comparisonResult: { type: Object, default: null },
  comparing: { type: Boolean, default: false },
  currentFileId: { type: String, default: null },
  currentFile: { type: Object, default: null },
})

const emit = defineEmits(['compare', 'reset'])

const rootEl = ref(null)
useScrollReveal(rootEl, '.pcx-card')

// ── Picker: like-for-like files only ──
// Insurers a file covers, by brand (legal-name spellings vary between files;
// 'מאוחד' is the merge marker, not an insurer).
function coSet(f) {
  return new Set((f?.companies || []).filter(Boolean).map(shortCo)
    .filter(c => c !== 'לא ידוע' && c !== 'מאוחד'))
}
// Like for like: a merged file (several insurers) against other merged files;
// a one-insurer file against that same insurer only. A single-insurer .DAT
// against the merged month reported hundreds of fake joiners/leavers.
function sameScope(cur, cand) {
  if (cur.size > 1) return cand.size > 1
  return cand.size === 1 && [...cand][0] === [...cur][0]
}
const comparable = computed(() => {
  const cur = coSet(props.currentFile)
  return props.history
    .filter(f => f.id !== props.currentFileId && (f.record_count || 0) > 0)
    .filter(f => !cur.size || sameScope(cur, coSet(f)))
    .sort((a, b) => fileKey(b) - fileKey(a))
    .slice(0, 6)
})
const HE_MONTHS = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
function fileDate(f) {
  if (f?.period_month) return new Date(f.period_month)
  const name = f?.filename || ''
  const mi = HE_MONTHS.findIndex(m => name.includes(m))
  const y = name.match(/(20\d{2})|\b(\d{2})\b/)
  if (mi >= 0 && y) return new Date(y[1] ? +y[1] : 2000 + +y[2], mi, 1)
  return f?.uploaded_at ? new Date(f.uploaded_at) : null
}
function fileKey(f) { return fileDate(f)?.getTime() || 0 }
function fileMonth(f) {
  const d = fileDate(f)
  return d ? HE_MONTHS[d.getMonth()] + ' ' + d.getFullYear() : (f?.filename || '')
}
const S = computed(() => props.comparisonResult?.summary || {})

// ── Drill (one DataModal for every mark on the page) ──
const drill = reactive({ open: false, title: '', rows: [], mode: 'changed', openId: null })
const drillOrigin = shallowRef(null)
// The pressed element, kept in a PLAIN variable: as a ref it re-rendered the
// charts between mousedown and mouseup and ApexCharts swallowed the click.
let lastPress = null
function onPress(e) {
  const t = e.target
  if (!(t instanceof Element)) return
  lastPress = t.closest('.apexcharts-pie-area, .apexcharts-bar-area, button') || t
}
onMounted(() => document.addEventListener('pointerdown', onPress, true))
onBeforeUnmount(() => document.removeEventListener('pointerdown', onPress, true))

function openDrill({ title, rows, mode, openId = null, origin = null }) {
  if (!rows?.length) return
  drillOrigin.value = origin || lastPress
  Object.assign(drill, { title, rows, mode, openId, open: true })
}

// ── Distribution ──
// One colour family: the tab's cobalt in steps, grey for "no change".
const CATEGORIES = [
  { key: 'new', label: 'חדשים', color: '#2F73C4', text: '#fff' },
  { key: 'removed', label: 'הוסרו', color: '#173A63', text: '#fff' },
  { key: 'changed', label: 'שונו', color: '#8DB5E6', text: '#181818' },
  { key: 'unchanged', label: 'ללא שינוי', color: '#DCE3EC', text: '#181818' },
]

const chartSeries = computed(() => {
  const s = S.value
  if (!props.comparisonResult) return []
  return [s.new_count || 0, s.removed_count || 0, s.changed_count || 0, s.unchanged_count || 0]
})
const seriesTotal = computed(() => chartSeries.value.reduce((a, b) => a + b, 0))
function pctOf(n) {
  if (!n || !seriesTotal.value) return ''
  const p = (n / seriesTotal.value) * 100
  return (p < 1 ? '<1' : Math.round(p)) + '%'
}

function donutOptions(labels, colors, textColors, totalLabel) {
  return {
    ...BASE_CHART,
    chart: { ...BASE_CHART.chart, animations: { enabled: true, easing: 'easeout', speed: 700 } },
    labels,
    colors,
    plotOptions: {
      pie: {
        expandOnClick: false,
        donut: {
          size: '52%',
          labels: {
            show: true,
            name: { fontSize: '13px', fontWeight: 600, color: '#706E6B', offsetY: -2 },
            value: { fontSize: '24px', fontWeight: 800, color: '#181818', offsetY: 4, formatter: v => Number(v).toLocaleString() },
            total: {
              show: true, label: totalLabel, fontSize: '12px', fontWeight: 600, color: '#706E6B',
              formatter: w => w.globals.seriesTotals.reduce((a, b) => a + b, 0).toLocaleString(),
            },
          },
        },
      },
    },
    dataLabels: {
      enabled: true,
      // Name + % only where the slice can hold it; a thin slice shows its %.
      formatter: (val, { seriesIndex, w }) => {
        if (val < 5) return ''
        const name = w.globals.labels[seriesIndex] || ''
        return val >= 12 && name.length <= 12 ? name + ' ' + Math.round(val) + '%' : Math.round(val) + '%'
      },
      style: { fontSize: '11.5px', fontWeight: 700, colors: textColors },
      dropShadow: { enabled: false },
    },
    legend: { show: false },
    stroke: { width: 2, colors: ['#fff'] },
    tooltip: { ...BASE_CHART.tooltip, y: { formatter: v => v.toLocaleString() + ' לקוחות' } },
  }
}

const chartOptions = computed(() => donutOptions(
  CATEGORIES.map(c => c.label), CATEGORIES.map(c => c.color), CATEGORIES.map(c => c.text), 'לקוחות'))

function onChartClick(_e, _chart, config) {
  const cat = CATEGORIES[config.dataPointIndex]
  if (cat) openCategory(cat.key)
}

const CAT_INFO = {
  new: { title: 'לקוחות חדשים', list: 'new_clients' },
  removed: { title: 'לקוחות שהוסרו', list: 'removed_clients' },
  changed: { title: 'לקוחות ששונו', list: 'changed_clients' },
}
function openCategory(key, origin) {
  const info = CAT_INFO[key]
  if (!info) return
  openDrill({ title: info.title, rows: props.comparisonResult?.[info.list] || [], mode: key, origin })
}

// ── By company: one colour per insurer, the same in all three charts ──
// Slices carry the brand, not the legal name — long names spilled out of the
// ring (QA 2026-10-03).
function groupByCompany(clients) {
  const map = {}
  for (const c of clients || []) {
    const co = shortCo(c.company)
    map[co] = (map[co] || 0) + 1
  }
  const entries = Object.entries(map).sort((a, b) => b[1] - a[1])
  return { labels: entries.map(e => e[0]), series: entries.map(e => e[1]) }
}
const companyCharts = computed(() => {
  const r = props.comparisonResult
  if (!r) return []
  const groups = [
    { key: 'new', title: 'חדשים לפי חברה', ...groupByCompany(r.new_clients) },
    { key: 'removed', title: 'הוסרו לפי חברה', ...groupByCompany(r.removed_clients) },
    { key: 'changed', title: 'שונו לפי חברה', ...groupByCompany(r.changed_clients) },
  ].filter(g => g.series.length)
  const colors = assignCompanyColors([...new Set(groups.flatMap(g => g.labels))])
  return groups.map(g => ({
    ...g,
    total: g.series.reduce((a, b) => a + b, 0),
    options: donutOptions(g.labels, g.labels.map(l => colors.get(l)), ['#fff'], 'לקוחות'),
  }))
})

function onCompanyChartClick(category, labels, config) {
  const company = labels[config.dataPointIndex]
  const info = CAT_INFO[category]
  if (!company || !info) return
  const rows = (props.comparisonResult?.[info.list] || []).filter(c => shortCo(c.company) === company)
  openDrill({ title: `${info.title} — ${company}`, rows, mode: category })
}

// ── Changed: KPIs + biggest movers ──
const barMode = ref('accumulation')

const changedInsights = computed(() => {
  const clients = props.comparisonResult?.changed_clients || []
  let totalPremiumDiff = 0, totalAccumulationDiff = 0, premiumCount = 0, accumulationCount = 0, productCount = 0
  for (const c of clients) {
    totalPremiumDiff += (c.premium_diff || 0)
    totalAccumulationDiff += (c.accumulation_diff || 0)
    if (c.changes?.some(ch => ch.field === 'פרמיה')) premiumCount++
    if (c.changes?.some(ch => ch.field === 'צבירה')) accumulationCount++
    if (c.changes?.some(ch => ch.field === 'מוצרים')) productCount++
  }
  return { totalClients: clients.length, totalPremiumDiff, totalAccumulationDiff, premiumCount, accumulationCount, productCount }
})

// Direction by arrow, size without a sign (an arrow + "−" read twice).
const moved = v => (Math.abs(v) < 0.5 ? '₪0' : (v > 0 ? '▲ ' : '▼ ') + '₪' + Math.round(Math.abs(v)).toLocaleString('en-US'))
const kpis = computed(() => {
  const ins = changedInsights.value
  return [
    { key: 'prem-sum', field: 'פרמיה', label: 'פרמיה — סה״כ', value: moved(ins.totalPremiumDiff), count: ins.premiumCount },
    { key: 'acc-sum', field: 'צבירה', label: 'צבירה — סה״כ', value: moved(ins.totalAccumulationDiff), count: ins.accumulationCount },
    { key: 'prem', field: 'פרמיה', label: 'שינוי פרמיה', value: ins.premiumCount.toLocaleString(), count: ins.premiumCount },
    { key: 'acc', field: 'צבירה', label: 'שינוי צבירה', value: ins.accumulationCount.toLocaleString(), count: ins.accumulationCount },
    { key: 'prod', field: 'מוצרים', label: 'שינוי מוצרים', value: ins.productCount.toLocaleString(), count: ins.productCount },
  ]
})

function openChangedByType(field, origin) {
  const rows = (props.comparisonResult?.changed_clients || []).filter(c => c.changes?.some(ch => ch.field === field))
  openDrill({ title: `שינוי ${field}`, rows, mode: 'changed', origin })
}

const topChangersData = computed(() => {
  const key = barMode.value === 'premium' ? 'premium_diff' : 'accumulation_diff'
  return [...(props.comparisonResult?.changed_clients || [])]
    .filter(c => Math.abs(c[key] || 0) >= 0.5)
    .sort((a, b) => Math.abs(b[key]) - Math.abs(a[key]))
    .slice(0, 10)
})

const topChangersChartSeries = computed(() => {
  const key = barMode.value === 'premium' ? 'premium_diff' : 'accumulation_diff'
  return [{
    name: barMode.value === 'premium' ? 'שינוי פרמיה' : 'שינוי צבירה',
    data: topChangersData.value.map(c => Math.round(c[key] || 0)),
  }]
})

const topChangersChartOptions = computed(() => ({
  ...BASE_CHART,
  plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '62%' } },
  colors: ['#2F73C4'],
  dataLabels: {
    enabled: true,
    formatter: v => signedMoney(v),
    style: { fontSize: '11.5px', fontWeight: 700, colors: ['#fff'] },
  },
  // RLE…PDF: SVG axis text is LTR, mixed names otherwise reorder.
  labels: topChangersData.value.map(c => '‫' + (c.name || c.id_number || '') + '‬'),
  xaxis: { labels: { formatter: v => signedMoney(v), style: { fontSize: '10.5px', colors: '#706E6B' } } },
  yaxis: { labels: { maxWidth: 140, style: { fontSize: '12px', fontWeight: 600, colors: '#3E3E3C' } } },
  legend: { show: false },
  tooltip: { ...BASE_CHART.tooltip, y: { formatter: v => signedMoney(v) } },
  grid: { ...BASE_CHART.grid, xaxis: { lines: { show: true } }, yaxis: { lines: { show: false } } },
}))

function onBarChartClick(_e, _chart, config) {
  const c = topChangersData.value[config.dataPointIndex]
  if (!c) return
  openDrill({ title: 'לקוחות ששונו', rows: props.comparisonResult?.changed_clients || [], mode: 'changed', openId: c.id_number })
}

// ── Search: every compared client, by status ──
function openSearch(origin) {
  const r = props.comparisonResult
  if (!r) return
  const rows = [
    ...(r.changed_clients || []).map(c => ({ ...c, _status: 'changed' })),
    ...(r.new_clients || []).map(c => ({ ...c, _status: 'new' })),
    ...(r.removed_clients || []).map(c => ({ ...c, _status: 'removed' })),
  ]
  openDrill({ title: 'חיפוש לקוח', rows, mode: 'all', origin })
}

// Always newer → older. The store only swaps on Hebrew month names, so a
// numeric "07_2026" file against "ספטמבר 26" came out inverted.
function runCompare(otherId) {
  if (!otherId || !props.currentFileId) return
  const other = props.history.find(f => f.id === otherId)
  if (other && props.currentFile && fileKey(other) > fileKey(props.currentFile)) {
    emit('compare', otherId, props.currentFileId)
  } else {
    emit('compare', props.currentFileId, otherId)
  }
}

function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('he-IL', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

// "דוח פרודוקציה פברואר 26.xlsx" → "פברואר 26"
function extractMonthLabel(filename) {
  if (!filename) return ''
  const match = filename.replace(/\.(xlsx|xls|dat|zip)$/i, '').replace('דוח פרודוקציה', '').trim()
  return match || filename
}
const currentMonthLabel = computed(() => extractMonthLabel(S.value.current_filename) || 'קובץ נוכחי')
const previousMonthLabel = computed(() => extractMonthLabel(S.value.previous_filename) || 'קובץ קודם')
</script>

<style scoped>
.prod-comparison {
  animation: slideUp 0.4s var(--transition);
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-muted);
}

.empty-state svg { margin-bottom: 12px; opacity: 0.3; }
.empty-state p { font-size: 14px; }

/* Loading */
.loading-state {
  text-align: center;
  padding: 48px;
  color: var(--text-secondary);
  font-size: 14px;
}

.loader {
  width: 36px;
  height: 36px;
  position: relative;
  margin: 0 auto 14px;
}

.loader-ring {
  position: absolute;
  inset: 0;
  border: 2px solid transparent;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loader-ring.delay {
  inset: 5px;
  border-top-color: var(--accent-cyan);
  animation-duration: 1.5s;
  animation-direction: reverse;
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

/* ── empty state: preview of what the comparison shows ── */
.prod-comparison { display: flex; flex-direction: column; gap: 16px; }
.pc-preview { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.pc-card {
  position: relative; overflow: hidden;
  display: flex; flex-direction: column; gap: 4px; padding: 24px 22px 20px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle); border-radius: 16px; box-shadow: var(--shadow-sm);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.pc-card:hover { transform: translateY(-3px); box-shadow: 0 14px 30px color-mix(in srgb, var(--k) 16%, transparent); }
.pc-card strong { font-size: 19px; font-weight: 900; letter-spacing: -0.02em; color: var(--text-primary, #181818); }
.pc-card > span:not(.pc-ic) { font-size: 13.5px; color: var(--text-secondary, #706E6B); }
.pc-ic {
  width: 52px; height: 52px; border-radius: 16px; display: grid; place-items: center; margin-bottom: 8px;
  color: var(--k-ink); background: color-mix(in srgb, var(--k) 13%, var(--card-bg));
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--k) 20%, transparent);
}
.pc-ic svg { width: 26px; height: 26px; }
/* sample rows: what the list will look like */
.pc-sample { list-style: none; margin: 14px 0 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.pc-sample li {
  display: flex; align-items: center; gap: 10px; padding: 9px 10px; border-radius: 12px;
  background: var(--card-bg); border: 1px solid var(--border-subtle);
  animation: pcRow 3.2s ease-in-out infinite; animation-delay: var(--d);
}
.pc-av { width: 26px; height: 26px; border-radius: 50%; flex-shrink: 0; background: color-mix(in srgb, var(--k) 12%, transparent); }
.pc-name { height: 8px; border-radius: 4px; background: color-mix(in srgb, var(--k) 12%, transparent); }
.pc-chip {
  margin-inline-start: auto; min-width: 28px; height: 22px; padding: 0 8px; border-radius: 999px;
  display: grid; place-items: center; font-size: 14px; font-weight: 900; line-height: 1;
  color: var(--k-ink); background: color-mix(in srgb, var(--k) 12%, var(--card-bg));
}
@keyframes pcRow { 0%, 100% { transform: none; opacity: 1; } 50% { transform: translateX(-4px); opacity: 0.8; } }
@media (prefers-reduced-motion: reduce) { .pc-sample li { animation: none; } }
@media (max-width: 720px) { .pc-preview { grid-template-columns: 1fr; } }

/* ── Results (2026-10-03 redesign): white cards, the tab's cobalt, 12px rhythm ── */
.results-section { display: flex; flex-direction: column; gap: 12px; }
.pcx-card {
  background: var(--card-bg); border: 1px solid var(--border-subtle);
  border-radius: 14px; box-shadow: var(--shadow-sm); padding: 16px 18px;
  min-width: 0; overflow: hidden;
}
.pcx-title { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 800; color: var(--text); margin: 0; }
.pcx-title-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 6px; }
.pcx-badge {
  min-width: 24px; height: 22px; padding: 0 8px; border-radius: 11px; display: inline-flex;
  align-items: center; justify-content: center; font-size: 12px; font-weight: 800;
  color: var(--tab-production); background: var(--tab-production-wash);
}

/* head: files + search, then the KPI row under a divider */
.pcx-head { padding: 10px; display: flex; flex-direction: column; gap: 10px; }
.pcx-files { display: flex; align-items: center; gap: 10px; padding: 2px 6px; min-width: 0; }
.pcx-file {
  display: flex; align-items: baseline; gap: 8px; min-width: 0; padding: 6px 12px;
  border-radius: 10px; font: inherit; color: var(--text);
}
.pcx-file b { font-size: 14px; font-weight: 800; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 260px; }
.pcx-file small { font-size: 12px; color: var(--text-muted); flex-shrink: 0; }
.pcx-file--cur { background: var(--tab-production-wash); color: var(--tab-production); }
.pcx-file--cur b { color: var(--tab-production); }
.pcx-file--prev {
  border: 1px solid var(--border-subtle); background: var(--card-bg); cursor: pointer; align-items: center;
  transition: border-color 0.2s ease, color 0.2s ease;
}
.pcx-file--prev b { font-weight: 600; }
.pcx-file--prev:hover { border-color: var(--tab-production); color: var(--tab-production); }
.pcx-swap { flex-shrink: 0; color: var(--text-muted); }
.pcx-file--prev:hover .pcx-swap { color: var(--tab-production); }
.pcx-arrow { flex-shrink: 0; color: var(--text-muted); }
.pcx-search {
  margin-inline-start: auto; flex-shrink: 0; display: inline-flex; align-items: center; gap: 8px;
  height: 38px; padding: 0 16px; border-radius: 10px; border: none; cursor: pointer;
  background: var(--tab-production); color: #fff; font: inherit; font-size: 13.5px; font-weight: 700;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--tab-production) 28%, transparent);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.pcx-search:hover { transform: translateY(-1px); box-shadow: 0 6px 16px color-mix(in srgb, var(--tab-production) 34%, transparent); }
.pcx-search:focus-visible, .pcx-file--prev:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }

.pcx-kpis {
  display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 8px;
  padding-top: 10px; border-top: 1px solid var(--border-subtle);
}
.pcx-kpi {
  display: flex; flex-direction: column; align-items: flex-start; gap: 3px; min-height: 68px; justify-content: center;
  padding: 10px 14px; border-radius: 12px; border: 1px solid var(--border-subtle); background: var(--card-bg);
  font: inherit; color: var(--text); text-align: right; cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}
.pcx-kpi:hover:not(:disabled) { border-color: var(--tab-production); transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.pcx-kpi:disabled { cursor: default; opacity: 0.6; }
.pcx-kpi:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 1px; }
.pcx-kpi-val { font-size: 20px; font-weight: 800; letter-spacing: -0.4px; }
.pcx-kpi:nth-child(-n+2) .pcx-kpi-val { color: var(--tab-production); }
.pcx-kpi-lbl { font-size: 12px; font-weight: 600; color: var(--text-muted); }

/* distribution: counts beside a big donut */
.pcx-dist-body { display: grid; grid-template-columns: minmax(220px, 300px) minmax(0, 1fr); gap: 20px; align-items: center; }
.pcx-counts { display: flex; flex-direction: column; gap: 8px; }
.pcx-count {
  position: relative; display: grid; grid-template-columns: 1fr auto 44px; align-items: center; gap: 10px;
  padding: 12px 16px 12px 14px; border-radius: 12px; border: 1px solid var(--border-subtle); background: var(--card-bg);
  font: inherit; color: var(--text); text-align: right; cursor: pointer; overflow: hidden;
  transition: border-color 0.2s ease, transform 0.2s ease;
}
.pcx-count:hover:not(:disabled) { border-color: var(--tab-production); transform: translateX(-2px); }
.pcx-count:disabled { cursor: default; }
.pcx-count:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 1px; }
.pcx-count-bar { position: absolute; inset-block: 10px; inset-inline-start: 0; width: 4px; border-radius: 0 4px 4px 0; }
.pcx-count-lbl { font-size: 14px; font-weight: 600; }
.pcx-count-val { font-size: 20px; font-weight: 800; }
.pcx-count-pct { font-size: 12px; color: var(--text-muted); text-align: left; }
.pcx-donut { min-width: 0; }

.pcx-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 12px; }
.pcx-co { padding-bottom: 8px; }

.pcx-seg { display: flex; padding: 3px; border-radius: 10px; background: var(--bg); gap: 2px; }
.pcx-seg button {
  border: none; background: none; font: inherit; font-size: 12px; font-weight: 600; color: var(--text-muted);
  padding: 7px 14px; border-radius: 8px; cursor: pointer;
}
.pcx-seg button.on { background: var(--card-bg); color: var(--tab-production); box-shadow: var(--shadow-sm); }

/* ApexCharts: pointer on clickable marks */
.pcx-card :deep(.apexcharts-pie-area),
.pcx-card :deep(.apexcharts-bar-area) { cursor: pointer; }

/* picker */
.pcx-pick { display: flex; flex-direction: column; gap: 14px; }
.pcx-pick-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.pcx-pick-cur {
  display: inline-flex; align-items: baseline; gap: 8px; padding: 6px 12px; border-radius: 10px;
  background: var(--tab-production-wash); color: var(--tab-production); font-size: 13.5px; font-weight: 800;
}
.pcx-pick-cur small { font-size: 12px; font-weight: 500; color: var(--text-muted); }
.pcx-pick-none { margin: 0; font-size: 14px; color: var(--text-muted); }
.pcx-pick-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 10px; }
.pcx-pick-file {
  position: relative; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; min-width: 0;
  padding: 14px 16px 12px; border-radius: 12px; border: 1px solid var(--border-subtle); background: var(--card-bg);
  font: inherit; color: var(--text); text-align: right; cursor: pointer;
  transition: border-color 0.2s ease, transform 0.2s ease, box-shadow 0.2s ease;
}
.pcx-pick-file:hover { border-color: var(--tab-production); transform: translateY(-2px); box-shadow: 0 8px 20px color-mix(in srgb, var(--tab-production) 14%, transparent); }
.pcx-pick-file:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }
.pcx-pick-file.is-first { border-color: color-mix(in srgb, var(--tab-production) 45%, var(--border-subtle)); }
.pcx-pf-month { font-size: 17px; font-weight: 800; color: var(--tab-production); }
.pcx-pf-name { max-width: 100%; font-size: 12px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pcx-pf-meta { display: flex; gap: 12px; margin-top: 4px; font-size: 12px; color: var(--text-muted); }
.pcx-pf-meta b { font-weight: 700; color: var(--text); }
.pcx-pf-go { position: absolute; top: 16px; inset-inline-end: 14px; color: var(--text-muted); transition: transform 0.2s ease, color 0.2s ease; }
.pcx-pick-file:hover .pcx-pf-go { color: var(--tab-production); transform: translateX(-3px); }

@media (max-width: 960px) {
  .pcx-kpis { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .pcx-dist-body { grid-template-columns: 1fr; }
  .pcx-counts { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .pcx-card { padding: 12px; }
  .pcx-files { flex-wrap: wrap; }
  .pcx-file b { max-width: 150px; }
  .pcx-search { margin-inline-start: 0; width: 100%; justify-content: center; }
  .pcx-kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .pcx-kpi-val { font-size: 17px; }
  .pcx-count { grid-template-columns: 1fr auto; padding: 10px 12px; }
  .pcx-count-pct { display: none; }
  .pcx-count-lbl { white-space: nowrap; font-size: 13px; }
  .pcx-grid { grid-template-columns: 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  .pcx-kpi, .pcx-count, .pcx-search, .pcx-file--prev, .pcx-pick-file, .pcx-pf-go { transition: none; }
}
</style>
