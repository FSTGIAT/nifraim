<template>
  <!-- The clients behind a product / track / company cell — the same cards
       as the KPI client list (QA 2026-10-01: the drill was still the old
       table with a bar per row and dashes). Company tabs, search and sort are
       local, so switching is instant. -->
  <div class="cc">
    <div class="cc-stats">
      <div class="cc-stat">
        <span class="cc-lbl">לקוחות</span>
        <span class="cc-val ltr-number">{{ shown.length.toLocaleString() }}</span>
      </div>
      <div class="cc-stat">
        <span class="cc-lbl">מוצרים</span>
        <span class="cc-val ltr-number">{{ totProducts.toLocaleString() }}</span>
      </div>
      <div v-if="totAccum > 0" class="cc-stat">
        <span class="cc-lbl">צבירה</span>
        <span class="cc-val ltr-number">{{ money(totAccum) }}</span>
      </div>
      <div v-if="totPrem > 0" class="cc-stat">
        <span class="cc-lbl">פרמיה חודשית</span>
        <span class="cc-val ltr-number">{{ money(totPrem) }}</span>
      </div>
      <div v-if="totComm > 0" class="cc-stat">
        <span class="cc-lbl">עמלה צפויה</span>
        <span class="cc-val ltr-number">{{ money(totComm) }}</span>
      </div>
    </div>

    <slot name="note" />

    <div v-if="companyCuts.length > 1" class="cc-tabs" role="tablist" aria-label="סינון לפי חברה">
      <button role="tab" class="cc-tab" :class="{ on: !company }" @click="company = null">
        הכל <span class="ltr-number">{{ clients.length }}</span>
      </button>
      <button v-for="c in companyCuts" :key="c.key" role="tab" class="cc-tab"
              :class="{ on: company === c.key }" @click="company = company === c.key ? null : c.key">
        {{ c.key }} <span class="ltr-number">{{ c.count }}</span>
      </button>
    </div>

    <div class="cc-tools">
      <label class="cc-search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input v-model.trim="query" type="search" placeholder="חיפוש לפי שם או ת.ז" />
      </label>
      <div class="cc-sort" role="group" aria-label="מיון">
        <button v-for="s in SORTS" :key="s.key" :class="{ on: sortKey === s.key }" @click="sortKey = s.key">
          {{ s.label }}
        </button>
      </div>
    </div>

    <p v-if="loading" class="cc-none">טוען לקוחות…</p>
    <ul v-else class="cc-list">
      <li v-if="!shown.length" class="cc-none">אין לקוחות להצגה.</li>
      <li v-for="c in visible" :key="c.id_number" class="cc-item" :class="{ open: openId === c.id_number }">
        <button class="cc-row" :aria-expanded="openId === c.id_number" @click="toggle(c.id_number)">
          <span class="cc-who">
            <span class="cc-name">{{ c.name || c.id_number }}</span>
            <span class="cc-id ltr-number">{{ c.id_number }}</span>
          </span>
          <span class="cc-cos">{{ c.cos.join(' · ') }}</span>
          <span class="cc-pill ltr-number">{{ c.items.length }}</span>
          <span class="cc-amt">
            <template v-if="primary(c) > 0">
              <span class="ltr-number">{{ money(primary(c)) }}</span>
              <small>{{ primaryLabel(c) }}</small>
            </template>
          </span>
          <span class="cc-amt cc-amt--small">
            <template v-if="c.sComm > 0">
              <span class="ltr-number">{{ money(c.sComm) }}</span>
              <small>עמלה</small>
            </template>
          </span>
          <svg class="cc-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        <div class="cc-fold" :class="{ open: openId === c.id_number }">
          <div class="cc-fold-inner">
            <div class="cc-products">
              <div v-for="(p, i) in c.items" :key="i" class="cc-product">
                <span class="cc-p-name" :title="p.raw_product || p.product">
                  {{ p.raw_product || p.product }}
                  <small>{{ [p.company, p.track, p.status].filter(Boolean).join(' · ') }}</small>
                </span>
                <span class="cc-p-fig">
                  <template v-if="p.accumulation > 0 || p.premium > 0">
                    <small>{{ p.accumulation > 0 ? 'צבירה' : 'פרמיה' }}</small>
                    <span class="ltr-number">{{ money(p.accumulation > 0 ? p.accumulation : p.premium) }}</span>
                  </template>
                </span>
                <span class="cc-p-fig">
                  <template v-if="p.commission > 0">
                    <small>עמלה צפויה</small>
                    <span class="ltr-number">{{ money(p.commission) }}</span>
                  </template>
                </span>
              </div>
            </div>
          </div>
        </div>
      </li>
    </ul>
    <button v-if="shown.length > limit" class="cc-more" @click="limit += 100">
      הצג עוד <span class="ltr-number">{{ Math.min(100, shown.length - limit) }}</span>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { money } from '../../utils/chartDefaults'

const props = defineProps({
  rows: { type: Array, default: () => [] },   // /production/breakdown/clients `clients`
  loading: { type: Boolean, default: false },
  initialSort: { type: String, default: 'value' },
})

const company = ref(null)
const query = ref('')
const sortKey = ref(props.initialSort)
const openId = ref(null)
const limit = ref(100)
const SORTS = [
  { key: 'value', label: 'סכום' },
  { key: 'commission', label: 'עמלה' },
  { key: 'products', label: 'מוצרים' },
  { key: 'name', label: 'שם' },
]

const clients = computed(() => props.rows.map(c => ({
  ...c, cos: [...new Set((c.products || []).map(p => p.company).filter(Boolean))],
})))
watch(() => props.rows, () => { company.value = null; query.value = ''; openId.value = null; limit.value = 100 })

const companyCuts = computed(() => {
  const m = new Map()
  for (const c of clients.value) for (const co of c.cos) m.set(co, (m.get(co) || 0) + 1)
  return [...m].map(([key, count]) => ({ key, count })).sort((a, b) => b.count - a.count)
})

const shown = computed(() => {
  const q = query.value
  const out = []
  for (const c of clients.value) {
    if (q && !(c.name || '').includes(q) && !String(c.id_number).includes(q)) continue
    const items = company.value ? (c.products || []).filter(p => p.company === company.value) : (c.products || [])
    if (!items.length) continue
    out.push({
      ...c, items,
      sAccum: items.reduce((s, p) => s + (p.accumulation || 0), 0),
      sPrem: items.reduce((s, p) => s + (p.premium || 0), 0),
      sComm: items.reduce((s, p) => s + (p.commission || 0), 0),
    })
  }
  const by = {
    value: (a, b) => (b.sAccum + b.sPrem * 12) - (a.sAccum + a.sPrem * 12),
    commission: (a, b) => b.sComm - a.sComm,
    products: (a, b) => b.items.length - a.items.length,
    name: (a, b) => (a.name || '').localeCompare(b.name || '', 'he'),
  }[sortKey.value] || (() => 0)
  return out.sort(by)
})
const visible = computed(() => shown.value.slice(0, limit.value))
watch([company, query, sortKey], () => { limit.value = 100 })

const totProducts = computed(() => shown.value.reduce((s, c) => s + c.items.length, 0))
const totAccum = computed(() => shown.value.reduce((s, c) => s + c.sAccum, 0))
const totPrem = computed(() => shown.value.reduce((s, c) => s + c.sPrem, 0))
const totComm = computed(() => shown.value.reduce((s, c) => s + c.sComm, 0))

const primary = c => (c.sAccum > 0 ? c.sAccum : c.sPrem)
const primaryLabel = c => (c.sAccum > 0 ? 'צבירה' : 'פרמיה')
function toggle(id) { openId.value = openId.value === id ? null : id }
</script>

<style scoped>
.cc { display: flex; flex-direction: column; gap: 14px; }
.cc-stats { display: flex; border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; }
.cc-stat { flex: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 13px 16px; }
.cc-stat + .cc-stat { border-inline-start: 1px solid var(--border-subtle); }
.cc-lbl { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.cc-val { font-size: 20px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; }
.cc-stat:first-child .cc-val { color: var(--tab-production); }

.cc-tabs { display: flex; flex-wrap: wrap; gap: 2px 18px; border-bottom: 1px solid var(--border-subtle); }
.cc-tab {
  position: relative; border: none; background: none; font: inherit; font-size: 13.5px; font-weight: 600;
  color: var(--text-muted); padding: 8px 0 10px; cursor: pointer; transition: color 0.2s ease;
}
.cc-tab .ltr-number { font-weight: 500; margin-inline-start: 3px; }
.cc-tab:hover { color: var(--text); }
.cc-tab.on { color: var(--tab-production); }
.cc-tab.on::after { content: ''; position: absolute; inset-inline: 0; bottom: -1px; height: 2px; border-radius: 2px; background: var(--tab-production); }

.cc-tools { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cc-search {
  flex: 1 1 220px; display: flex; align-items: center; gap: 8px; padding: 0 12px; height: 38px;
  border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--bg); color: var(--text-muted);
}
.cc-search:focus-within { border-color: var(--tab-production); background: var(--card-bg); }
.cc-search input { flex: 1; border: none; background: none; outline: none; font: inherit; font-size: 13px; color: var(--text); }
.cc-sort { display: flex; padding: 3px; border-radius: 10px; background: var(--bg); gap: 2px; }
.cc-sort button {
  border: none; background: none; font: inherit; font-size: 12px; font-weight: 600; color: var(--text-muted);
  padding: 7px 12px; border-radius: 8px; cursor: pointer;
}
.cc-sort button.on { background: var(--card-bg); color: var(--tab-production); box-shadow: var(--shadow-sm); }

.cc-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.cc-none { text-align: center; color: var(--text-muted); font-size: 13px; padding: 20px; list-style: none; }
.cc-item { border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg); transition: border-color 0.2s ease; }
.cc-item:hover { border-color: color-mix(in srgb, var(--tab-production) 40%, var(--border-subtle)); }
.cc-item.open { border-color: var(--tab-production); }
.cc-row {
  width: 100%; display: grid; align-items: center; gap: 12px;
  grid-template-columns: minmax(120px, 1.4fr) minmax(0, 1fr) 34px 120px 90px 16px;
  padding: 10px 14px; border: none; background: none; font: inherit; color: var(--text); text-align: right; cursor: pointer;
}
.cc-row:focus-visible { outline: 2px solid var(--tab-production); outline-offset: -2px; border-radius: 12px; }
.cc-who { display: flex; flex-direction: column; min-width: 0; }
.cc-name { font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cc-id { font-size: 11.5px; color: var(--text-muted); }
.cc-cos { font-size: 12.5px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cc-pill {
  justify-self: center; min-width: 28px; height: 24px; padding: 0 8px; border-radius: 12px; background: var(--bg);
  font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center;
}
.cc-amt { display: flex; flex-direction: column; align-items: flex-start; font-size: 14px; font-weight: 700; line-height: 1.2; }
.cc-amt small { font-size: 10.5px; font-weight: 500; color: var(--text-muted); }
.cc-amt--small { font-size: 13px; }
.cc-chev { color: var(--text-muted); transition: transform 0.25s ease; }
.cc-item.open .cc-chev { transform: rotate(180deg); color: var(--tab-production); }
.cc-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.3s cubic-bezier(0.2, 0, 0.2, 1); }
.cc-fold.open { grid-template-rows: 1fr; }
.cc-fold-inner { overflow: hidden; min-height: 0; }
.cc-products { margin: 0 14px 12px; padding: 6px; border-radius: 10px; background: var(--bg); display: flex; flex-direction: column; gap: 4px; }
.cc-product {
  display: grid; grid-template-columns: minmax(0, 1fr) 110px 110px; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 8px; background: var(--card-bg);
}
.cc-p-name { display: flex; flex-direction: column; font-size: 13px; font-weight: 600; min-width: 0; }
.cc-p-name small { font-size: 11px; font-weight: 400; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cc-p-fig { display: flex; flex-direction: column; align-items: flex-start; font-size: 13px; font-weight: 700; }
.cc-p-fig small { font-size: 10.5px; font-weight: 500; color: var(--text-muted); }
.cc-more {
  align-self: center; border: 1px solid var(--border-subtle); background: var(--card-bg); border-radius: 10px;
  padding: 9px 16px; font: inherit; font-size: 13px; font-weight: 600; color: var(--tab-production); cursor: pointer;
}
@media (max-width: 640px) {
  .cc-stats { flex-wrap: wrap; }
  .cc-stat { flex: 1 1 45%; padding: 10px 12px; }
  .cc-val { font-size: 17px; }
  .cc-row { grid-template-columns: minmax(0, 1fr) 30px 96px 14px; gap: 8px; padding: 10px; }
  .cc-cos, .cc-amt--small { display: none; }
  .cc-product { grid-template-columns: minmax(0, 1fr) 90px; }
  .cc-product .cc-p-fig + .cc-p-fig { display: none; }
}
@media (prefers-reduced-motion: reduce) { .cc-fold, .cc-chev, .cc-item, .cc-tab { transition: none; } }
</style>
