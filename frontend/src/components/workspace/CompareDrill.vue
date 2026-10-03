<template>
  <!-- The clients behind a file-comparison mark (a KPI, a donut slice, a bar,
       the search button). Same language as ClientCards: summary strip, text
       tabs, search + sort, cards that fold open in place. -->
  <div class="cd">
    <div class="cd-stats">
      <div class="cd-stat">
        <span class="cd-lbl">לקוחות</span>
        <span class="cd-val ltr-number">{{ shown.length.toLocaleString() }}</span>
      </div>
      <template v-if="mode === 'changed'">
        <div v-if="Math.abs(totPremDiff) >= 0.5" class="cd-stat">
          <span class="cd-lbl">שינוי פרמיה</span>
          <span class="cd-val ltr-number">{{ signedMoney(totPremDiff) }}</span>
        </div>
        <div v-if="Math.abs(totAccDiff) >= 0.5" class="cd-stat">
          <span class="cd-lbl">שינוי צבירה</span>
          <span class="cd-val ltr-number">{{ signedMoney(totAccDiff) }}</span>
        </div>
      </template>
      <template v-else>
        <div class="cd-stat">
          <span class="cd-lbl">מוצרים</span>
          <span class="cd-val ltr-number">{{ totProducts.toLocaleString() }}</span>
        </div>
        <div v-if="totPrem >= 0.5" class="cd-stat">
          <span class="cd-lbl">פרמיה</span>
          <span class="cd-val ltr-number">{{ money(totPrem) }}</span>
        </div>
        <div v-if="totAcc >= 0.5" class="cd-stat">
          <span class="cd-lbl">צבירה</span>
          <span class="cd-val ltr-number">{{ money(totAcc) }}</span>
        </div>
      </template>
    </div>

    <div v-if="cuts.length > 1" class="cd-tabs" role="tablist" :aria-label="mode === 'all' ? 'סינון לפי סטטוס' : 'סינון לפי חברה'">
      <button role="tab" class="cd-tab" :class="{ on: !cut }" @click="cut = null">
        הכל <span class="ltr-number">{{ rows.length }}</span>
      </button>
      <button v-for="c in cuts" :key="c.key" role="tab" class="cd-tab"
              :class="{ on: cut === c.key }" @click="cut = cut === c.key ? null : c.key">
        {{ c.label }} <span class="ltr-number">{{ c.count }}</span>
      </button>
    </div>

    <div class="cd-tools">
      <label class="cd-search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input ref="inputEl" v-model.trim="query" type="search" placeholder="שם או ת.ז" />
      </label>
      <div class="cd-sort" role="group" aria-label="מיון">
        <button v-for="s in sorts" :key="s.key" :class="{ on: sortKey === s.key }" @click="sortKey = s.key">
          {{ s.label }}
        </button>
      </div>
    </div>

    <ul class="cd-list">
      <li v-if="!shown.length" class="cd-none">לא נמצאו לקוחות</li>
      <li v-for="c in visible" :key="c._key" class="cd-item" :class="{ open: openKey === c._key }">
        <button class="cd-row" :aria-expanded="openKey === c._key" @click="toggle(c._key)">
          <span class="cd-who">
            <span class="cd-name">{{ c.name || c.id_number }}</span>
            <span class="cd-id ltr-number">{{ c.id_number }}</span>
          </span>
          <span class="cd-ctx">{{ [mode === 'all' ? STATUS[c._status] : '', c.company ? shortCompany(c.company) : ''].filter(Boolean).join(' · ') }}</span>
          <span class="cd-pill ltr-number" title="מוצרים">{{ c.products_count || 0 }}</span>
          <span class="cd-amt">
            <template v-if="lead(c)">
              <span class="ltr-number">{{ lead(c).text }}</span>
              <small>{{ lead(c).label }}</small>
            </template>
          </span>
          <svg class="cd-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        <div class="cd-fold" :class="{ open: openKey === c._key }">
          <div class="cd-fold-inner">
            <div class="cd-detail">
              <!-- What moved: previous → current -->
              <div v-for="ch in (c.changes || [])" :key="ch.field" class="cd-change">
                <span class="cd-c-field">{{ ch.field }}</span>
                <span class="cd-c-vals">
                  <span class="ltr-number cd-c-old">{{ fmt(ch.field, ch.old_val) }}</span>
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"
                       stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 5 5 12 12 19"/></svg>
                  <span class="ltr-number cd-c-new">{{ fmt(ch.field, ch.new_val) }}</span>
                </span>
                <span v-if="typeof ch.old_val === 'number' && typeof ch.new_val === 'number'" class="cd-c-diff ltr-number">
                  {{ ch.new_val >= ch.old_val ? '▲' : '▼' }} {{ fmtDiff(ch.field, ch.new_val - ch.old_val) }}
                </span>
              </div>
              <!-- Book figures for this client -->
              <div class="cd-figs">
                <span v-if="(c.premium || 0) >= 0.5"><small>פרמיה</small><b class="ltr-number">{{ money(c.premium) }}</b></span>
                <span v-if="(c.accumulation || 0) >= 0.5"><small>צבירה</small><b class="ltr-number">{{ money(c.accumulation) }}</b></span>
                <span v-if="c.product_types?.length" class="cd-types"><small>מוצרים</small><b>{{ c.product_types.join(' · ') }}</b></span>
              </div>
            </div>
          </div>
        </div>
      </li>
    </ul>
    <button v-if="shown.length > limit" class="cd-more" @click="limit += 100">
      הצג עוד <span class="ltr-number">{{ Math.min(100, shown.length - limit) }}</span>
    </button>

    <!-- Actions on what is on screen, pinned at the drill's bottom -->
    <div v-if="shown.length" class="cd-actions">
      <button class="cd-btn" type="button" @click="downloadExcel">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
        אקסל
      </button>
      <button v-if="mode !== 'all'" class="cd-btn cd-btn--primary" type="button" :disabled="!mailCompany"
              :title="mailCompany ? '' : 'בחרו חברה'" @click="sendMail">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 6-10 7L2 6"/></svg>
        {{ mailCompany ? 'מייל ל' + mailCompany : 'מייל לחברה' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import * as XLSX from 'xlsx'
import api from '../../api/client.js'
import { money, signedMoney } from '../../utils/chartDefaults'
import { openMailCompose } from '../../utils/mailHelper.js'
import { shortCompany } from '../../utils/companyShort.js'

const props = defineProps({
  rows: { type: Array, default: () => [] },
  // new | removed | changed | all (search over every compared client)
  mode: { type: String, default: 'changed' },
  title: { type: String, default: '' },
  // Client to show unfolded on open (a bar click).
  openId: { type: String, default: null },
  focus: { type: Boolean, default: false },
})

const STATUS = { new: 'חדש', removed: 'הוסר', changed: 'שונה' }
const STATUS_TABS = { new: 'חדשים', removed: 'הוסרו', changed: 'שונו' }

const cut = ref(null)
const query = ref('')
const sortKey = ref(props.mode === 'changed' ? 'diff' : 'value')
const openKey = ref(null)
const limit = ref(100)
const inputEl = ref(null)

const sorts = computed(() => [
  props.mode === 'changed' ? { key: 'diff', label: 'שינוי' } : { key: 'value', label: 'סכום' },
  { key: 'products', label: 'מוצרים' },
  { key: 'name', label: 'שם' },
])

const keyed = computed(() => props.rows.map(c => ({ ...c, _key: (c._status || '') + c.id_number })))

function reset() {
  cut.value = null; query.value = ''; limit.value = 100
  sortKey.value = props.mode === 'changed' ? 'diff' : 'value'
  const hit = props.openId && keyed.value.find(c => c.id_number === props.openId)
  openKey.value = hit ? hit._key : null
}
watch(() => [props.rows, props.openId], reset)
onMounted(() => {
  reset()
  if (props.focus) nextTick(() => setTimeout(() => inputEl.value?.focus(), 350))
})

const cutOf = c => (props.mode === 'all' ? c._status : shortCompany(c.company))
const cuts = computed(() => {
  const m = new Map()
  for (const c of keyed.value) m.set(cutOf(c), (m.get(cutOf(c)) || 0) + 1)
  return [...m].map(([key, count]) => ({ key, count, label: props.mode === 'all' ? STATUS_TABS[key] : key }))
    .sort((a, b) => b.count - a.count)
})

const diffMag = c => Math.abs(c.accumulation_diff || 0) + Math.abs(c.premium_diff || 0) * 12
const shown = computed(() => {
  const q = query.value
  const out = keyed.value.filter(c =>
    (!cut.value || cutOf(c) === cut.value) &&
    (!q || (c.name || '').includes(q) || String(c.id_number).includes(q)))
  const by = {
    diff: (a, b) => diffMag(b) - diffMag(a),
    value: (a, b) => ((b.accumulation || 0) + (b.premium || 0) * 12) - ((a.accumulation || 0) + (a.premium || 0) * 12),
    products: (a, b) => (b.products_count || 0) - (a.products_count || 0),
    name: (a, b) => (a.name || '').localeCompare(b.name || '', 'he'),
  }[sortKey.value]
  return by ? out.sort(by) : out
})
const visible = computed(() => {
  const list = shown.value.slice(0, limit.value)
  // A client opened from a bar may sit past the first page.
  if (openKey.value && !list.some(c => c._key === openKey.value)) {
    const hit = shown.value.find(c => c._key === openKey.value)
    if (hit) list.unshift(hit)
  }
  return list
})
watch([cut, query, sortKey], () => { limit.value = 100 })

const sum = f => shown.value.reduce((s, c) => s + (c[f] || 0), 0)
const totProducts = computed(() => sum('products_count'))
const totPrem = computed(() => sum('premium'))
const totAcc = computed(() => sum('accumulation'))
const totPremDiff = computed(() => sum('premium_diff'))
const totAccDiff = computed(() => sum('accumulation_diff'))

// The one figure a card leads with.
function lead(c) {
  const st = c._status || props.mode
  if (st === 'changed') {
    const acc = c.accumulation_diff || 0
    const prem = c.premium_diff || 0
    if (Math.abs(acc) >= 0.5) return { text: signedMoney(acc), label: 'צבירה' }
    if (Math.abs(prem) >= 0.5) return { text: signedMoney(prem), label: 'פרמיה' }
    const prod = (c.changes || []).find(ch => ch.field === 'מוצרים')
    if (prod && typeof prod.new_val === 'number') {
      const d = prod.new_val - prod.old_val
      return { text: (d > 0 ? '+' : '') + d, label: 'מוצרים' }
    }
    return null
  }
  if ((c.accumulation || 0) >= 0.5) return { text: money(c.accumulation), label: 'צבירה' }
  if ((c.premium || 0) >= 0.5) return { text: money(c.premium), label: 'פרמיה' }
  return null
}

const isCount = field => field === 'מוצרים'
function fmt(field, v) {
  if (typeof v !== 'number') return v ?? ''
  return isCount(field) ? v.toLocaleString() : '₪' + Math.round(v).toLocaleString('en-US')
}
function fmtDiff(field, d) {
  return isCount(field) ? (d > 0 ? '+' : '') + d : signedMoney(d)
}
function toggle(k) { openKey.value = openKey.value === k ? null : k }

// ── actions ──
// Mail goes to ONE insurer: the company tab in view, or the only company.
const mailCompany = computed(() => {
  if (props.mode === 'all') return null
  if (cut.value) return cut.value
  const cos = new Set(shown.value.map(c => shortCompany(c.company)))
  return cos.size === 1 ? [...cos][0] : null
})

let contacts = null
async function companyEmail(name) {
  if (!contacts) {
    try { contacts = (await api.get('/company-contacts')).data || [] } catch { contacts = [] }
  }
  const hit = contacts.find(c => name.includes(c.company_name) || c.company_name.includes(name))
  return hit?.email || ''
}

async function sendMail() {
  const co = mailCompany.value
  if (!co) return
  const list = shown.value.filter(c => shortCompany(c.company) === co)
  const lines = list.map(c => {
    const types = c.product_types?.length ? ` (${c.product_types.join(', ')})` : ''
    const prem = c.premium ? ` פרמיה: ₪${Math.round(c.premium)}` : ''
    return `- ${c.name} ת.ז ${c.id_number}${types}${prem}`
  }).join('\n')
  await openMailCompose({
    to: await companyEmail(co),
    subject: `${props.title} (${list.length}) — ${co}`,
    body: `שלום רב,\n\nלהלן רשימת לקוחות — ${props.title}:\n\n${lines}\n\nבברכה`,
  })
}

function downloadExcel() {
  const rows = shown.value.map(c => ({
    'שם': c.name || '',
    'ת.ז': c.id_number || '',
    'סטטוס': STATUS[c._status || props.mode] || '',
    'חברה': c.company || '',
    'סוג מוצר': c.product_types?.join(', ') || '',
    'מוצרים': c.products_count || 0,
    'פרמיה': c.premium || 0,
    'צבירה': c.accumulation || 0,
    'שינוי פרמיה': c.premium_diff || 0,
    'שינוי צבירה': c.accumulation_diff || 0,
  }))
  const ws = XLSX.utils.json_to_sheet(rows)
  ws['!Dir'] = 'rtl'
  const wb = XLSX.utils.book_new()
  const name = (props.title || 'השוואה').slice(0, 31)
  XLSX.utils.book_append_sheet(wb, ws, name)
  XLSX.writeFile(wb, `${name.replace(/\s+/g, '_')}_${new Date().toLocaleDateString('he-IL')}.xlsx`)
}
</script>

<style scoped>
.cd { display: flex; flex-direction: column; gap: 12px; }
.cd-stats { display: flex; border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; }
.cd-stat { flex: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 13px 16px; min-width: 0; }
.cd-stat + .cd-stat { border-inline-start: 1px solid var(--border-subtle); }
.cd-lbl { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.cd-val { font-size: 20px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; }
.cd-stat:first-child .cd-val { color: var(--tab-production); }

.cd-tabs { display: flex; flex-wrap: wrap; gap: 2px 18px; border-bottom: 1px solid var(--border-subtle); }
.cd-tab {
  position: relative; border: none; background: none; font: inherit; font-size: 13.5px; font-weight: 600;
  color: var(--text-muted); padding: 8px 0 10px; cursor: pointer; transition: color 0.2s ease;
}
.cd-tab .ltr-number { font-weight: 500; margin-inline-start: 3px; }
.cd-tab:hover { color: var(--text); }
.cd-tab.on { color: var(--tab-production); }
.cd-tab.on::after { content: ''; position: absolute; inset-inline: 0; bottom: -1px; height: 2px; border-radius: 2px; background: var(--tab-production); }

.cd-tools { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cd-search {
  flex: 1 1 220px; display: flex; align-items: center; gap: 8px; padding: 0 12px; height: 38px;
  border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--bg); color: var(--text-muted);
}
.cd-search:focus-within { border-color: var(--tab-production); background: var(--card-bg); }
.cd-search input { flex: 1; min-width: 0; border: none; background: none; outline: none; font: inherit; font-size: 13px; color: var(--text); }
.cd-sort { display: flex; padding: 3px; border-radius: 10px; background: var(--bg); gap: 2px; }
.cd-sort button {
  border: none; background: none; font: inherit; font-size: 12px; font-weight: 600; color: var(--text-muted);
  padding: 7px 12px; border-radius: 8px; cursor: pointer;
}
.cd-sort button.on { background: var(--card-bg); color: var(--tab-production); box-shadow: var(--shadow-sm); }

.cd-list { list-style: none; display: flex; flex-direction: column; gap: 6px; margin: 0; padding: 0; }
.cd-none { text-align: center; color: var(--text-muted); font-size: 13px; padding: 20px; }
.cd-item { border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg); transition: border-color 0.2s ease; }
.cd-item:hover { border-color: color-mix(in srgb, var(--tab-production) 40%, var(--border-subtle)); }
.cd-item.open { border-color: var(--tab-production); }
.cd-row {
  width: 100%; display: grid; align-items: center; gap: 12px;
  grid-template-columns: minmax(120px, 1.3fr) minmax(0, 1fr) 34px 130px 16px;
  padding: 10px 14px; border: none; background: none; font: inherit; color: var(--text); text-align: right; cursor: pointer;
}
.cd-row:focus-visible { outline: 2px solid var(--tab-production); outline-offset: -2px; border-radius: 12px; }
.cd-who { display: flex; flex-direction: column; min-width: 0; }
.cd-name { font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cd-id { font-size: 11.5px; color: var(--text-muted); }
.cd-ctx { font-size: 12.5px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cd-pill {
  justify-self: center; min-width: 28px; height: 24px; padding: 0 8px; border-radius: 12px; background: var(--bg);
  font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center;
}
.cd-amt { display: flex; flex-direction: column; align-items: flex-start; font-size: 14px; font-weight: 700; line-height: 1.2; }
.cd-amt small { font-size: 10.5px; font-weight: 500; color: var(--text-muted); }
.cd-chev { color: var(--text-muted); transition: transform 0.25s ease; }
.cd-item.open .cd-chev { transform: rotate(180deg); color: var(--tab-production); }

.cd-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.3s cubic-bezier(0.2, 0, 0.2, 1); }
.cd-fold.open { grid-template-rows: 1fr; }
.cd-fold-inner { overflow: hidden; min-height: 0; }
.cd-detail { margin: 0 14px 12px; padding: 6px; border-radius: 10px; background: var(--bg); display: flex; flex-direction: column; gap: 4px; }
.cd-change {
  display: grid; grid-template-columns: 70px minmax(0, 1fr) 130px; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 8px; background: var(--card-bg); font-size: 13px;
}
.cd-c-field { font-weight: 700; }
.cd-c-vals { display: inline-flex; align-items: center; gap: 8px; color: var(--text-muted); min-width: 0; }
.cd-c-new { color: var(--text); font-weight: 600; }
.cd-c-diff { font-weight: 700; color: var(--tab-production); }
.cd-figs { display: flex; flex-wrap: wrap; gap: 6px 22px; padding: 8px 10px; }
.cd-figs > span { display: flex; flex-direction: column; font-size: 13px; }
.cd-figs small { font-size: 10.5px; color: var(--text-muted); }
.cd-types b { font-weight: 500; }

.cd-more {
  align-self: center; border: 1px solid var(--border-subtle); background: var(--card-bg); border-radius: 10px;
  padding: 9px 16px; font: inherit; font-size: 13px; font-weight: 600; color: var(--tab-production); cursor: pointer;
}
.cd-actions {
  position: sticky; bottom: -16px; margin: 0 -20px -16px; padding: 12px 20px;
  display: flex; gap: 8px; justify-content: flex-end;
  background: var(--card-bg); border-top: 1px solid var(--border-subtle);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg);
}
.cd-btn {
  display: inline-flex; align-items: center; gap: 7px; height: 38px; padding: 0 16px; border-radius: 10px;
  border: 1px solid var(--border-subtle); background: var(--card-bg); color: var(--text);
  font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.cd-btn:hover:not(:disabled) { transform: translateY(-1px); }
.cd-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.cd-btn--primary { background: var(--tab-production); border-color: var(--tab-production); color: #fff; box-shadow: 0 4px 12px color-mix(in srgb, var(--tab-production) 28%, transparent); }

@media (max-width: 640px) {
  .cd-stats { flex-wrap: wrap; }
  .cd-stat { flex: 1 1 45%; padding: 10px 12px; }
  .cd-val { font-size: 17px; }
  .cd-row { grid-template-columns: minmax(0, 1fr) 30px 100px 14px; gap: 8px; padding: 10px; }
  .cd-ctx { display: none; }
  .cd-change { grid-template-columns: 60px minmax(0, 1fr); }
  .cd-c-diff { grid-column: 2; }
}
@media (prefers-reduced-motion: reduce) { .cd-fold, .cd-chev, .cd-item, .cd-tab, .cd-btn { transition: none; } }
</style>
