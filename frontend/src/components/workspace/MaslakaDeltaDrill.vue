<template>
  <!-- What changed in one מסלקה production file: against the file before it, or
       against the agent's production file when it is the first (GET /maslaka/delta,
       services/maslaka/delta.py). nifraim-style drill order: summary strip → text
       tabs with counts → cards that fold open in place. One colour: the tab's teal. -->
  <DataModal
    :open="open" :origin="origin" title="מה השתנה" :badge="total || null"
    :period="periodLabel" accent="var(--tab-maslaka)" size="lg" @close="emit('close')"
  >
    <div class="md">
      <p v-if="loading" class="md-note">טוען…</p>
      <p v-else-if="error" class="md-note" role="alert">{{ error }}</p>
      <p v-else-if="!data?.summary" class="md-note">עוד לא הגיע קובץ פרודוקציה מהמסלקה.</p>

      <template v-else>
        <p class="md-vs">{{ vsLine }}</p>

        <!-- 1. summary strip -->
        <div class="md-strip">
          <div class="md-cell md-cell--key">
            <span>חדשים</span><strong class="ltr-number">{{ num(s.new_count) }}</strong>
          </div>
          <div class="md-cell"><span>הוסרו</span><strong class="ltr-number">{{ num(s.removed_count) }}</strong></div>
          <div class="md-cell"><span>השתנו</span><strong class="ltr-number">{{ num(s.changed_count) }}</strong></div>
          <div class="md-cell"><span>ללא שינוי</span><strong class="ltr-number">{{ num(s.unchanged_count) }}</strong></div>
          <div v-if="Math.abs(s.changed_accumulation_diff) >= 0.5" class="md-cell">
            <span>שינוי בצבירה</span>
            <strong class="ltr-number">{{ arrow(s.changed_accumulation_diff) }} ₪{{ money(Math.abs(s.changed_accumulation_diff)) }}</strong>
          </div>
        </div>

        <!-- 2. filters: what changed, then the company -->
        <div class="md-tabs" role="tablist" aria-label="סוג שינוי">
          <button
            v-for="k in KINDS" :key="k.id" type="button" role="tab" class="md-tab"
            :class="{ 'md-tab--on': kind === k.id }" :aria-selected="kind === k.id"
            @click="setKind(k.id)"
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
          <input v-model="q" placeholder="חיפוש לפי שם או ת.ז" aria-label="חיפוש" @input="limit = PAGE" />
        </label>

        <!-- 3. cards -->
        <p v-if="!shown.length" class="md-note">{{ emptyLine }}</p>
        <ul class="md-list">
          <li v-for="r in shown.slice(0, limit)" :key="r._k" class="md-card" :class="{ 'md-card--open': openKey === r._k }">
            <button type="button" class="md-row" :aria-expanded="openKey === r._k" @click="openKey = openKey === r._k ? null : r._k">
              <span class="md-id">
                <strong>{{ r.name || 'לקוח' }}</strong>
                <small class="ltr-number">{{ r.id_number }}</small>
              </span>
              <span class="md-ctx">{{ shortCo(r.company) }} · {{ productOf(r) }}</span>
              <span v-if="figure(r) >= 0.5" class="md-amt">
                <strong class="ltr-number">{{ kind === 'changed' ? arrow(r.accumulation_diff) + ' ' : '' }}₪{{ money(figure(r)) }}</strong>
                <small>{{ figureLabel }}</small>
              </span>
              <svg class="md-chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
            </button>
            <div class="md-fold">
              <div class="md-fold-in">
                <dl class="md-fields">
                  <div v-if="r.policy"><dt>פוליסה</dt><dd class="ltr-number">{{ r.policy }}</dd></div>
                  <div v-if="r.old_accumulation >= 0.5"><dt>{{ oldLabel }}</dt><dd class="ltr-number">₪{{ money(r.old_accumulation) }}</dd></div>
                  <div v-if="r.new_accumulation >= 0.5"><dt>צבירה במסלקה</dt><dd class="ltr-number">₪{{ money(r.new_accumulation) }}</dd></div>
                  <div v-if="r.new_premium >= 0.5"><dt>הפקדה</dt><dd class="ltr-number">₪{{ money(r.new_premium) }}</dd></div>
                </dl>
              </div>
            </div>
          </li>
        </ul>
        <button v-if="shown.length > limit" type="button" class="md-more" @click="limit += PAGE">
          עוד <span class="ltr-number">{{ num(shown.length - limit) }}</span>
        </button>
      </template>
    </div>
  </DataModal>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import api from '../../api/client.js'
import DataModal from './DataModal.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  origin: { type: null, default: null },
  asOf: { type: String, default: '' },   // the file's valuation date (YYYY-MM-DD)
})
const emit = defineEmits(['close'])

const KINDS = [
  { id: 'new', label: 'חדשים' },
  { id: 'removed', label: 'הוסרו' },
  { id: 'changed', label: 'השתנו' },
]
const PAGE = 20
const HEB_MONTHS = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']

const data = ref(null)
const loading = ref(false)
const error = ref('')
const kind = ref('new')
const company = ref('')
const q = ref('')
const openKey = ref(null)
const limit = ref(PAGE)

const s = computed(() => data.value?.summary || {})
const total = computed(() => (s.value.new_count || 0) + (s.value.removed_count || 0) + (s.value.changed_count || 0))

function monthOf(iso) {
  const [y, m] = String(iso || '').split('-').map(Number)
  return y && m ? `${HEB_MONTHS[m - 1]} ${y}` : ''
}
function dayOf(iso) {
  const [y, m, d] = String(iso || '').split('-').map(Number)
  return y && m && d ? `${d}/${m}/${y}` : ''
}
const periodLabel = computed(() => (data.value?.as_of ? `מסלקה נכון ל-${dayOf(data.value.as_of)}` : ''))
const vsLine = computed(() => {
  const b = data.value?.base || {}
  if (b.kind === 'maslaka') return `לעומת קובץ המסלקה נכון ל-${dayOf(b.as_of)}`
  return `לעומת קובץ הפרודוקציה שלך${b.as_of ? ' של ' + monthOf(b.as_of) : ''} — רק בחברות שענו במסלקה`
})
const oldLabel = computed(() => (data.value?.base?.kind === 'maslaka' ? 'צבירה בחודש הקודם' : 'צבירה בפרודוקציה'))
const figureLabel = computed(() => ({ new: 'צבירה', removed: 'צבירה שהייתה', changed: 'שינוי בצבירה' }[kind.value]))
const emptyLine = computed(() => (q.value ? 'לא נמצא' : {
  new: 'אין מוצרים חדשים.', removed: 'לא הוסר אף מוצר.', changed: 'אף צבירה לא השתנתה.',
}[kind.value]))

const num = (n) => Number(n || 0).toLocaleString('he-IL')
const money = (v) => Math.round(Number(v || 0)).toLocaleString('he-IL')
const arrow = (d) => (Number(d) < 0 ? '▼' : '▲')
// Company names are long legal names; the tabs and cards need the brand.
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

const list = computed(() => (data.value?.[kind.value] || []).map((r, i) => ({ ...r, _k: `${kind.value}-${i}` })))
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

function setKind(k) {
  kind.value = k
  company.value = ''
  openKey.value = null
  limit.value = PAGE
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data: d } = await api.get('/maslaka/delta', { params: props.asOf ? { as_of: props.asOf } : {} })
    data.value = d
    // open on the first kind that has something in it
    setKind(KINDS.find((k) => (d?.[k.id] || []).length)?.id || 'new')
  } catch {
    error.value = 'לא הצלחנו לטעון את השינויים. נסו שוב.'
  } finally {
    loading.value = false
  }
}

watch(() => props.open, (o) => { if (o) { q.value = ''; load() } })
</script>

<style scoped>
.md { display: flex; flex-direction: column; gap: 12px; min-height: 0; }
.md-note { margin: 18px 4px; text-align: center; font-size: 14px; line-height: 1.6; color: var(--text-muted); }
.md-vs { margin: 0; font-size: 13.5px; color: var(--text-secondary); }

.md-strip { display: flex; border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg); overflow: hidden; }
.md-cell { flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: flex-start; gap: 2px; padding: 10px 14px; }
.md-cell + .md-cell { border-inline-start: 1px solid var(--border-subtle); }
.md-cell span { font-size: 12px; color: var(--text-muted); }
.md-cell strong { font-size: 21px; font-weight: 800; color: var(--text); white-space: nowrap; }
.md-cell--key strong { color: var(--tab-maslaka); }

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
.md-amt { flex: none; display: flex; flex-direction: column; align-items: flex-end; gap: 1px; }
.md-amt strong { font-size: 14.5px; font-weight: 800; color: var(--text); }
.md-amt small { font-size: 11.5px; color: var(--text-muted); }
.md-chev { flex: none; color: var(--text-muted); transition: transform 0.35s cubic-bezier(0.32, 0.72, 0, 1); }
.md-card--open .md-chev { transform: rotate(180deg); }
.md-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.4s cubic-bezier(0.32, 0.72, 0, 1); }
.md-card--open .md-fold { grid-template-rows: 1fr; }
.md-fold-in { overflow: hidden; min-height: 0; }
.md-fields { margin: 0 14px 10px; padding: 4px 0 0; border-top: 1px solid var(--border-subtle); }
.md-fields > div { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; padding: 7px 0; }
.md-fields dt { font-size: 12.5px; color: var(--text-muted); }
.md-fields dd { margin: 0; font-size: 14px; color: var(--text); }

.md-more { align-self: center; padding: 8px 20px; border-radius: 10px; border: 1px solid var(--border); background: var(--card-bg);
  cursor: pointer; font-family: inherit; font-size: 13.5px; font-weight: 600; color: var(--text-secondary); }
.md-more:hover { color: var(--tab-maslaka); border-color: var(--tab-maslaka); }

@media (max-width: 640px) {
  .md-strip { flex-wrap: wrap; }
  .md-cell { flex: 1 1 33%; }
  .md-id { flex-basis: 120px; }
  .md-ctx { display: none; }
}
@media (prefers-reduced-motion: reduce) { .md-fold, .md-chev { transition: none; } }
</style>
