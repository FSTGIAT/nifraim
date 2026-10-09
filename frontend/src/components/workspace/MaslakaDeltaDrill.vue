<template>
  <!-- What changed in one מסלקה production file: against the file before it, or
       against the agent's production file when it is the first (GET /maslaka/delta,
       services/maslaka/delta.py). Modules: counts → by-company chart → biggest
       movements → the list. One colour (the tab's teal, in three shades). Every
       chart and card drills: a company filters the list, a customer opens their
       full מסלקה picture (emit 'open-customer'). -->
  <DataModal
    :open="open" :origin="origin" title="מה השתנה" :badge="total || null"
    :period="periodLabel" accent="var(--tab-maslaka)" size="xl" @close="emit('close')"
  >
    <div ref="rootEl" class="md">
      <p v-if="loading" class="md-note">טוען…</p>
      <p v-else-if="error" class="md-note" role="alert">{{ error }}</p>
      <p v-else-if="!data?.summary" class="md-note">עוד לא הגיע קובץ מהמסלקה.</p>

      <template v-else>
        <!-- 1. the counts -->
        <div class="md-kpis md-mod">
          <button
            v-for="k in KINDS" :key="k.id" type="button" class="md-kpi"
            :class="{ 'md-kpi--on': kind === k.id }" @click="pick(k.id, '')"
          >
            <span class="md-kpi-label">{{ k.label }}</span>
            <strong class="md-kpi-n ltr-number">{{ num(shownCounts[k.id]) }}</strong>
            <span class="md-kpi-bar" :style="{ '--w': share(k.id) }" aria-hidden="true"></span>
          </button>
          <div class="md-kpi md-kpi--quiet">
            <span class="md-kpi-label">ללא שינוי</span>
            <strong class="md-kpi-n ltr-number">{{ num(shownCounts.unchanged) }}</strong>
          </div>
        </div>

        <!-- 2. charts -->
        <div class="md-charts">
          <section class="md-mod md-chart">
            <h4 class="md-h">לפי חברה</h4>
            <apexchart
              type="bar" :height="Math.max(170, coRows.length * 44 + 50)"
              :options="coOptions" :series="coSeries"
            />
          </section>
          <section v-if="movers.length" class="md-mod md-chart">
            <h4 class="md-h">התנועות הגדולות</h4>
            <apexchart
              type="bar" :height="Math.max(170, movers.length * 30 + 40)"
              :options="moverOptions" :series="moverSeries"
            />
          </section>
        </div>

        <!-- 3. the list -->
        <section ref="listEl" class="md-mod md-listmod">
          <div class="md-tabs" role="tablist" aria-label="סוג שינוי">
            <button
              v-for="k in KINDS" :key="k.id" type="button" role="tab" class="md-tab"
              :class="{ 'md-tab--on': kind === k.id }" :aria-selected="kind === k.id"
              @click="pick(k.id, '')"
            >{{ k.label }} <span class="ltr-number">{{ num((data[k.id] || []).length) }}</span></button>
          </div>
          <div v-if="companies.length > 1" class="md-tabs md-tabs--sub" role="tablist" aria-label="חברה">
            <button
              type="button" role="tab" class="md-tab" :class="{ 'md-tab--on': !company }" :aria-selected="!company"
              @click="company = ''; limit = PAGE"
            >הכל <span class="ltr-number">{{ num(list.length) }}</span></button>
            <button
              v-for="c in companies" :key="c.name" type="button" role="tab" class="md-tab"
              :class="{ 'md-tab--on': company === c.name }" :aria-selected="company === c.name"
              @click="company = c.name; limit = PAGE"
            >{{ c.short }} <span class="ltr-number">{{ num(c.n) }}</span></button>
          </div>
          <label v-if="list.length > 8" class="md-search">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
            <input v-model="q" placeholder="שם או ת.ז" aria-label="חיפוש" @input="limit = PAGE" />
          </label>

          <p v-if="!shown.length" class="md-note">{{ q ? 'לא נמצא' : 'אין' }}</p>
          <TransitionGroup tag="ul" name="md-li" class="md-list">
            <li
              v-for="(r, i) in shown.slice(0, limit)" :key="r._k" class="md-card"
              :class="{ 'md-card--open': openKey === r._k }" :style="{ '--i': Math.min(i, 12) }"
            >
              <button type="button" class="md-row" :aria-expanded="openKey === r._k" @click="openKey = openKey === r._k ? null : r._k">
                <span class="md-id">
                  <strong>{{ r.name || 'לקוח' }}</strong>
                  <small class="ltr-number">{{ r.id_number }}</small>
                </span>
                <span class="md-ctx">{{ shortCo(r.company) }} · {{ productOf(r) }}</span>
                <span v-if="figure(r) >= 0.5" class="md-amt ltr-number">
                  <span v-if="kind === 'changed'" class="md-arrow">{{ arrow(r.accumulation_diff) }}</span>₪{{ money(figure(r)) }}
                </span>
                <svg class="md-chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
              </button>
              <div class="md-fold">
                <div class="md-fold-in">
                  <div class="md-fold-body">
                    <dl class="md-fields">
                      <div v-if="r.old_accumulation >= 0.5"><dt>{{ oldLabel }}</dt><dd class="ltr-number">₪{{ money(r.old_accumulation) }}</dd></div>
                      <div v-if="r.new_accumulation >= 0.5"><dt>{{ newLabel }}</dt><dd class="ltr-number">₪{{ money(r.new_accumulation) }}</dd></div>
                      <div v-if="r.policy"><dt>פוליסה</dt><dd class="ltr-number">{{ r.policy }}</dd></div>
                    </dl>
                    <button type="button" class="md-open" @click="emit('open-customer', r.id_number, $event.currentTarget)">
                      תיק הלקוח
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
                    </button>
                  </div>
                </div>
              </div>
            </li>
          </TransitionGroup>
          <button v-if="shown.length > limit" type="button" class="md-more" @click="limit += PAGE">
            עוד <span class="ltr-number">{{ num(shown.length - limit) }}</span>
          </button>
        </section>
      </template>
    </div>
  </DataModal>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import api from '../../api/client.js'
import DataModal from './DataModal.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  origin: { type: null, default: null },
  asOf: { type: String, default: '' },   // the file's valuation date (YYYY-MM-DD)
})
const emit = defineEmits(['close', 'open-customer'])

const KINDS = [
  { id: 'new', label: 'חדשים' },
  { id: 'removed', label: 'הוסרו' },
  { id: 'changed', label: 'השתנו' },
]
const PAGE = 20
const HEB_MONTHS = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
// The tab's teal (--tab-maslaka #2C5F6B) in three shades — charts need literal hexes.
const TEAL = ['#2C5F6B', '#6F98A2', '#B5CDD3']

const data = ref(null)
const loading = ref(false)
const error = ref('')
const kind = ref('new')
const company = ref('')
const q = ref('')
const openKey = ref(null)
const limit = ref(PAGE)
const rootEl = ref(null)
const listEl = ref(null)

const s = computed(() => data.value?.summary || {})
const total = computed(() => (s.value.new_count || 0) + (s.value.removed_count || 0) + (s.value.changed_count || 0))

function monthOf(iso) {
  const [y, m] = String(iso || '').split('-').map(Number)
  return y && m ? `${HEB_MONTHS[m - 1]} ${y}` : ''
}
// "ספטמבר 2026 מול יולי 2026": the file's month against what it is compared with.
const periodLabel = computed(() => {
  const d = data.value
  if (!d?.as_of) return ''
  const vs = d.base?.as_of ? ` מול ${monthOf(d.base.as_of)}` : ''
  return `${monthOf(d.as_of)}${vs}`
})
const fromProduction = computed(() => data.value?.base?.kind !== 'maslaka')
const oldLabel = computed(() => (fromProduction.value ? 'בפרודוקציה' : `ב${monthOf(data.value?.base?.as_of).split(' ')[0]}`))
const newLabel = computed(() => `ב${monthOf(data.value?.as_of).split(' ')[0]}`)

const num = (n) => Number(n || 0).toLocaleString('he-IL')
const money = (v) => Math.round(Number(v || 0)).toLocaleString('he-IL')
const arrow = (d) => (Number(d) < 0 ? '▼' : '▲')
const shortCo = (c) => String(c || '').replace(/\s*(חברה לביטוח|פנסיה וגמל|גמל ופנסיה|פנסיה מקיפה|בע"מ|בעמ)\s*/g, ' ').trim() || c
// "הפניקס - קופת גמל" under הפניקס → "קופת גמל"
function productOf(r) {
  const p = String(r.product || '')
  const brand = shortCo(r.company).split(' ')[0]
  return brand && p.startsWith(brand + ' - ') ? p.slice(brand.length + 3) : p
}
function figure(r) {
  if (kind.value === 'new') return r.new_accumulation || 0
  if (kind.value === 'removed') return r.old_accumulation || 0
  return Math.abs(r.accumulation_diff || 0)
}

// ── counts that count up ────────────────────────────────────────────────
const shownCounts = ref({ new: 0, removed: 0, changed: 0, unchanged: 0 })
let raf = 0
function countUp() {
  cancelAnimationFrame(raf)
  const to = { new: s.value.new_count || 0, removed: s.value.removed_count || 0,
    changed: s.value.changed_count || 0, unchanged: s.value.unchanged_count || 0 }
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { shownCounts.value = to; return }
  const t0 = performance.now(), dur = 900
  const step = (t) => {
    const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3)
    shownCounts.value = Object.fromEntries(Object.entries(to).map(([k, v]) => [k, Math.round(v * e)]))
    if (p < 1) raf = requestAnimationFrame(step)
  }
  raf = requestAnimationFrame(step)
}
onBeforeUnmount(() => cancelAnimationFrame(raf))
const share = (k) => {
  const all = (s.value.new_count || 0) + (s.value.removed_count || 0) + (s.value.changed_count || 0) + (s.value.unchanged_count || 0)
  return all ? `${Math.max(4, Math.round((s.value[k + '_count'] || 0) / all * 100))}%` : '0%'
}

// ── chart: changes by company (stacked, one hue) ────────────────────────
const coRows = computed(() => (data.value?.by_company || []).filter((c) => c.new + c.removed + c.changed > 0))
const coSeries = computed(() => KINDS.map((k) => ({ name: k.label, data: coRows.value.map((c) => c[k.id]) })))
const coOptions = computed(() => ({
  chart: { stacked: true, toolbar: { show: false }, fontFamily: 'Heebo, sans-serif',
    animations: { enabled: true, easing: 'easeout', speed: 700, animateGradually: { enabled: true, delay: 90 } },
    events: { dataPointSelection: (_e, _c, cfg) => pick(KINDS[cfg.seriesIndex].id, coRows.value[cfg.dataPointIndex]?.company) } },
  colors: TEAL,
  plotOptions: { bar: { horizontal: true, barHeight: '58%', borderRadius: 4, borderRadiusApplication: 'end' } },
  labels: coRows.value.map((c) => '‫' + shortCo(c.company) + '‬'),
  xaxis: { labels: { show: false }, axisBorder: { show: false }, axisTicks: { show: false } },
  yaxis: { labels: { style: { fontSize: '13px', fontWeight: 600, colors: '#3B4A4F' } } },
  grid: { show: false, padding: { left: 0, right: 8 } },
  dataLabels: { enabled: false },
  legend: { position: 'top', horizontalAlign: 'right', fontSize: '12.5px', markers: { size: 5 } },
  tooltip: { y: { formatter: (v) => num(v) } },
  states: { hover: { filter: { type: 'darken', value: 0.9 } } },
}))

// ── chart: biggest movements (changed only) ─────────────────────────────
const movers = computed(() => (data.value?.changed || []).slice(0, 8))
const moverSeries = computed(() => [{ name: 'שינוי בצבירה', data: movers.value.map((m) => Math.round(m.accumulation_diff || 0)) }])
const moverOptions = computed(() => ({
  chart: { toolbar: { show: false }, fontFamily: 'Heebo, sans-serif',
    animations: { enabled: true, easing: 'easeout', speed: 800, animateGradually: { enabled: true, delay: 70 } },
    events: { dataPointSelection: (e, _c, cfg) => {
      const m = movers.value[cfg.dataPointIndex]
      if (m) emit('open-customer', m.id_number, e?.target || null)
    } } },
  colors: [TEAL[0]],
  // the amount sits just past the bar's end, so a short bar never clips it
  plotOptions: { bar: { horizontal: true, barHeight: '56%', borderRadius: 3, dataLabels: { position: 'top' } } },
  labels: movers.value.map((m) => '‫' + (m.name || m.id_number) + '‬'),
  xaxis: { labels: { show: false }, axisBorder: { show: false }, axisTicks: { show: false },
    max: Math.max(...movers.value.map((m) => Math.abs(m.accumulation_diff || 0)), 1) * 1.35 },
  yaxis: { labels: { maxWidth: 140, style: { fontSize: '12.5px', colors: '#3B4A4F' } } },
  grid: { show: false, padding: { left: 0, right: 8 } },
  dataLabels: { enabled: true, offsetX: 38, style: { fontSize: '11.5px', fontWeight: 700, colors: ['#3B4A4F'] },
    formatter: (v) => `${v < 0 ? '▼' : '▲'} ₪${money(Math.abs(v))}` },
  tooltip: { y: { formatter: (v) => `${v < 0 ? '▼' : '▲'} ₪${money(Math.abs(v))}` } },
  states: { hover: { filter: { type: 'darken', value: 0.9 } } },
}))

// ── the list ────────────────────────────────────────────────────────────
const list = computed(() => (data.value?.[kind.value] || []).map((r, i) => ({ ...r, _k: `${kind.value}-${r.id_number}-${r.policy}-${i}` })))
const companies = computed(() => {
  const n = {}
  for (const r of list.value) n[r.company] = (n[r.company] || 0) + 1
  return Object.entries(n).sort((a, b) => b[1] - a[1]).map(([name, c]) => ({ name, short: shortCo(name), n: c }))
})
const shown = computed(() => {
  const t = q.value.trim()
  return list.value.filter((r) => (!company.value || r.company === company.value)
    && (!t || `${r.name || ''} ${r.id_number}`.includes(t)))
})

function pick(k, co) {
  kind.value = k
  company.value = co || ''
  openKey.value = null
  limit.value = PAGE
  if (co) nextTick(() => listEl.value?.scrollIntoView({ behavior: 'smooth', block: 'start' }))
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data: d } = await api.get('/maslaka/delta', { params: props.asOf ? { as_of: props.asOf } : {} })
    data.value = d
    pick(KINDS.find((k) => (d?.[k.id] || []).length)?.id || 'new', '')
    nextTick(countUp)
  } catch {
    error.value = 'לא הצלחנו לטעון. נסו שוב.'
  } finally {
    loading.value = false
  }
}

watch(() => props.open, (o) => { if (o) { q.value = ''; load() } })
</script>

<style scoped>
.md { display: flex; flex-direction: column; gap: 12px; min-height: 0; }
.md-note { margin: 18px 4px; text-align: center; font-size: 14px; color: var(--text-muted); }

/* modules rise in one after another */
.md-mod { animation: md-rise 0.7s cubic-bezier(0.22, 1, 0.36, 1) both; }
.md-kpis.md-mod { animation-delay: 0.05s; }
.md-charts .md-mod:nth-child(1) { animation-delay: 0.16s; }
.md-charts .md-mod:nth-child(2) { animation-delay: 0.26s; }
.md-listmod.md-mod { animation-delay: 0.36s; }
@keyframes md-rise { from { opacity: 0; transform: translateY(18px) scale(0.985); } to { opacity: 1; transform: none; } }

/* 1. counts */
.md-kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.md-kpi { position: relative; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 12px 14px 14px;
  border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg); font-family: inherit; text-align: start;
  cursor: pointer; overflow: hidden; transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s; }
.md-kpi:hover { transform: translateY(-1px); box-shadow: var(--shadow-sm); }
.md-kpi--on { border-color: var(--tab-maslaka); box-shadow: 0 0 0 1px var(--tab-maslaka) inset; }
.md-kpi--quiet { cursor: default; background: var(--bg); }
.md-kpi--quiet:hover { transform: none; box-shadow: none; }
.md-kpi-label { font-size: 12.5px; color: var(--text-muted); }
.md-kpi-n { font-size: 26px; font-weight: 800; line-height: 1.1; color: var(--text); }
.md-kpi--on .md-kpi-n { color: var(--tab-maslaka); }
.md-kpi-bar { position: absolute; inset-inline-start: 0; bottom: 0; height: 3px; width: var(--w); background: var(--tab-maslaka);
  opacity: 0.25; transform-origin: right; animation: md-grow 1s 0.3s cubic-bezier(0.22, 1, 0.36, 1) both; }
.md-kpi--on .md-kpi-bar { opacity: 1; }
@keyframes md-grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }

/* 2. charts */
.md-charts { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.md-chart { padding: 12px 14px 4px; border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg); min-width: 0; }
.md-h { margin: 0 0 2px; font-size: 13.5px; font-weight: 700; color: var(--text); }
.md-chart :deep(.apexcharts-bar-area) { cursor: pointer; }

/* 3. list */
.md-listmod { display: flex; flex-direction: column; gap: 10px; }
.md-tabs { display: flex; flex-wrap: wrap; gap: 4px 18px; border-bottom: 1px solid var(--border-subtle); }
.md-tabs--sub { gap: 4px 14px; }
.md-tab { position: relative; padding: 8px 0; border: none; background: none; cursor: pointer; font-family: inherit;
  font-size: 14px; font-weight: 600; color: var(--text-muted); }
.md-tabs--sub .md-tab { font-size: 13px; }
.md-tab span { font-weight: 700; margin-inline-start: 4px; }
.md-tab:hover { color: var(--text); }
.md-tab--on { color: var(--tab-maslaka); }
.md-tab--on::after { content: ''; position: absolute; inset-inline: 0; bottom: -1px; height: 2px; border-radius: 2px; background: var(--tab-maslaka); }
.md-tab:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; border-radius: 4px; }

.md-search { display: flex; align-items: center; gap: 8px; height: 38px; padding: 0 12px; border-radius: 10px;
  background: var(--bg); color: var(--text-muted); }
.md-search:focus-within { background: var(--card-bg); box-shadow: 0 0 0 2px var(--tab-maslaka); }
.md-search input { flex: 1; min-width: 0; border: none; outline: none; background: none; font: inherit; font-size: 14px; color: var(--text); }

.md-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.md-li-enter-active { transition: opacity 0.45s ease, transform 0.45s cubic-bezier(0.22, 1, 0.36, 1); transition-delay: calc(var(--i) * 35ms); }
.md-li-enter-from { opacity: 0; transform: translateY(10px); }
.md-card { border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg); transition: border-color 0.2s, box-shadow 0.2s; }
.md-card--open { border-color: color-mix(in srgb, var(--tab-maslaka) 35%, var(--border-subtle)); box-shadow: var(--shadow-sm); }
.md-row { width: 100%; display: flex; align-items: center; gap: 14px; padding: 11px 14px; border: none; background: none;
  cursor: pointer; font-family: inherit; text-align: start; border-radius: 12px; }
.md-row:hover { background: var(--bg); }
.md-row:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: -2px; }
.md-id { flex: 0 0 170px; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.md-id strong { font-size: 14.5px; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.md-id small { align-self: flex-start; font-size: 12.5px; color: var(--text-muted); }
.md-ctx { flex: 1; min-width: 0; font-size: 13px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.md-amt { flex: none; display: inline-flex; align-items: center; gap: 4px; font-size: 14.5px; font-weight: 800; color: var(--text); }
.md-arrow { font-size: 11px; color: var(--tab-maslaka); }
.md-chev { flex: none; color: var(--text-muted); transition: transform 0.35s cubic-bezier(0.32, 0.72, 0, 1); }
.md-card--open .md-chev { transform: rotate(180deg); }
.md-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.4s cubic-bezier(0.32, 0.72, 0, 1); }
.md-card--open .md-fold { grid-template-rows: 1fr; }
.md-fold-in { overflow: hidden; min-height: 0; }
.md-fold-body { display: flex; align-items: flex-end; gap: 16px; margin: 0 14px 12px; padding-top: 6px; border-top: 1px solid var(--border-subtle); }
.md-fields { flex: 1; margin: 0; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
.md-fields > div { display: flex; flex-direction: column; gap: 2px; padding: 4px 0; }
.md-fields dt { font-size: 12px; color: var(--text-muted); }
.md-fields dd { margin: 0; font-size: 14.5px; font-weight: 700; color: var(--text); }
.md-open { flex: none; display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border: none; border-radius: 10px;
  cursor: pointer; background: var(--tab-maslaka); color: #fff; font-family: inherit; font-size: 13px; font-weight: 700;
  box-shadow: 0 3px 10px color-mix(in srgb, var(--tab-maslaka) 25%, transparent); transition: transform 0.15s, filter 0.15s; }
.md-open:hover { transform: translateY(-1px); filter: brightness(1.1); }

.md-more { align-self: center; padding: 8px 20px; border-radius: 10px; border: 1px solid var(--border); background: var(--card-bg);
  cursor: pointer; font-family: inherit; font-size: 13.5px; font-weight: 600; color: var(--text-secondary); }
.md-more:hover { color: var(--tab-maslaka); border-color: var(--tab-maslaka); }

@media (max-width: 760px) {
  .md-charts { grid-template-columns: 1fr; }
  .md-kpis { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 640px) {
  .md-id { flex-basis: 120px; }
  .md-ctx { display: none; }
  .md-fold-body { flex-direction: column; align-items: stretch; }
  .md-fields { grid-template-columns: 1fr 1fr; }
}
@media (prefers-reduced-motion: reduce) {
  .md-mod, .md-kpi-bar, .md-li-enter-active { animation: none; transition: none; }
  .md-fold, .md-chev { transition: none; }
}
</style>
