<template>
  <!-- The KPI cards' drill — same language as the rest of the tab's drills
       (QA 2026-09-30: the KPIs still opened the old grey table): a summary
       strip, text tabs, calm rows / cards, one colour. The client lists load
       EVERY client (the old one was capped at 50 while the KPI said 545). -->
  <div class="kd">
    <!-- Summary -->
    <div v-if="stats.length" class="kd-stats">
      <div v-for="s in stats" :key="s.label" class="kd-stat">
        <span class="kd-stat-lbl">{{ s.label }}</span>
        <span class="kd-stat-val ltr-number">{{ s.value }}</span>
      </div>
    </div>

    <!-- ── Clients (לקוחות / סה"כ צבירה) ── -->
    <template v-if="isClients || statusGroup">
      <button v-if="statusGroup" class="ks-back" @click="statusGroup = null">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="9 18 15 12 9 6" /></svg>
        חזרה לסטטוסים · <strong>{{ familyByKey[statusGroup]?.label }}</strong>
      </button>
      <div v-if="companyCuts.length > 1" class="kd-tabs" role="tablist" aria-label="סינון לפי חברה">
        <button role="tab" class="kd-tab" :class="{ on: !company }" @click="company = null">
          הכל <span class="ltr-number">{{ clients.length }}</span>
        </button>
        <button v-for="c in companyCuts" :key="c.key" role="tab" class="kd-tab"
                :class="{ on: company === c.key }" @click="company = company === c.key ? null : c.key">
          {{ c.key }} <span class="ltr-number">{{ c.count }}</span>
        </button>
      </div>
      <div class="kd-tools">
        <label class="kd-search">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input v-model.trim="query" type="search" placeholder="חיפוש לפי שם או ת.ז" />
        </label>
        <div class="kd-sort" role="group" aria-label="מיון">
          <button v-for="s in SORTS" :key="s.key" :class="{ on: sortKey === s.key }" @click="sortKey = s.key">
            {{ s.label }}
          </button>
        </div>
      </div>

      <p v-if="loading" class="kd-none">טוען לקוחות…</p>
      <ul v-else class="kd-list">
        <li v-if="!shownClients.length" class="kd-none">אין לקוחות שתואמים לסינון.</li>
        <li v-for="c in visibleClients" :key="c.id_number" class="kd-item" :class="{ open: openId === c.id_number }">
          <button class="kd-row" :aria-expanded="openId === c.id_number" @click="toggle(c.id_number)">
            <span class="kd-who">
              <span class="kd-name">{{ c.name || c.id_number }}</span>
              <span class="kd-id ltr-number">{{ c.id_number }}</span>
            </span>
            <span class="kd-cos">{{ c.cos.join(' · ') }}</span>
            <span class="kd-pill ltr-number">{{ c.shownProducts.length }}</span>
            <span class="kd-amt">
              <span class="ltr-number">{{ money(primary(c)) }}</span>
              <small>{{ primaryLabel(c) }}</small>
            </span>
            <svg class="kd-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </button>
          <div class="kd-fold" :class="{ open: openId === c.id_number }">
            <div class="kd-fold-inner">
              <div class="kd-products">
                <div v-for="(p, i) in c.shownProducts" :key="i" class="kd-product">
                  <span class="kd-p-name" :title="p.raw_product || p.product">
                    {{ p.raw_product || p.product }}
                    <small>{{ p.company }}{{ p.track ? ' · ' + p.track : '' }}{{ p.status ? ' · ' + p.status : '' }}</small>
                  </span>
                  <span class="kd-p-fig">
                    <template v-if="p.accumulation > 0 || p.premium > 0">
                      <small>{{ p.accumulation > 0 ? 'צבירה' : 'פרמיה' }}</small>
                      <span class="ltr-number">{{ money(p.accumulation > 0 ? p.accumulation : p.premium) }}</span>
                    </template>
                  </span>
                  <span v-if="p.commission > 0" class="kd-p-fig">
                    <small>עמלה צפויה</small>
                    <span class="ltr-number">{{ money(p.commission) }}</span>
                  </span>
                </div>
              </div>
            </div>
          </div>
        </li>
      </ul>
      <button v-if="shownClients.length > limit" class="kd-more" @click="limit += 100">
        הצג עוד <span class="ltr-number">{{ Math.min(100, shownClients.length - limit) }}</span>
        מתוך <span class="ltr-number">{{ shownClients.length - limit }}</span>
      </button>
    </template>

    <!-- ── Status (מוצרים פעילים) ── -->
    <!-- Redesigned (QA 2026-10-01): raw insurer statuses with two bars each
         and percentages that did not add up (543 products, statuses summing
         to 258). Now four groups anyone reads — פעיל / ללא הפקדות / נסגר /
         ללא סטטוס — over ALL products, so the parts make the whole, and each
         group opens the clients in it. -->
    <template v-else-if="kind === 'status' && !statusGroup">
      <div class="ks-head">
        <span class="ks-big">
          <span class="ltr-number">{{ famCount('active').toLocaleString() }}</span>
          <small>מתוך <span class="ltr-number">{{ totalProducts.toLocaleString() }}</span> מוצרים פעילים</small>
        </span>
        <span v-if="famCount('unknown')" class="ks-note">
          ל-<span class="ltr-number">{{ famCount('unknown').toLocaleString() }}</span> מוצרים אין סטטוס בקובץ
        </span>
      </div>
      <div class="ks-bar" role="img" :aria-label="families.map(f => `${f.label} ${f.count}`).join(', ')">
        <span v-for="f in families.filter(f => f.count)" :key="f.key" class="ks-part"
              :class="'ks-part--' + f.key" :style="{ flexGrow: f.count }"></span>
      </div>
      <ul class="ks-fams">
        <li v-for="f in families.filter(f => f.count)" :key="f.key">
          <button class="ks-fam" @click="openGroup(f.key)">
            <i class="ks-dot" :class="'ks-part--' + f.key"></i>
            <span class="ks-fam-txt">
              <strong>{{ f.label }}</strong>
              <small>{{ f.meaning }}</small>
              <small v-if="f.parts.length > 1 || (f.parts[0] && f.parts[0].label !== f.label)" class="ks-parts">
                {{ f.parts.map(x => `${x.label} ${x.count}`).join(' · ') }}
              </small>
            </span>
            <span class="ks-fam-num">
              <span class="ltr-number">{{ f.count.toLocaleString() }}</span>
              <small class="ltr-number">{{ pctOf(f.count) }}%</small>
            </span>
            <svg class="ks-go" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <polyline points="15 18 9 12 15 6" />
            </svg>
          </button>
        </li>
      </ul>
    </template>

    <!-- ── Ranked lists (מוצרים לפי סוג / חברות) ── -->
    <template v-else>
      <label class="kd-search kd-search--solo">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input v-model.trim="query" type="search" :placeholder="kind === 'companies' ? 'חיפוש חברה' : 'חיפוש מוצר'" />
      </label>
      <ul class="kd-rank">
        <li v-for="r in filteredRank" :key="r.label">
          <span class="kd-r-name">
            {{ r.label }}
            <small v-if="r.sub">{{ r.sub }}</small>
          </span>
          <span class="kd-r-bar"><i :style="{ width: r.share + '%' }"></i></span>
          <span class="kd-r-num ltr-number">{{ r.value.toLocaleString() }}</span>
          <span class="kd-r-amt">
            <span v-if="r.accumulation > 0" class="ltr-number">{{ money(r.accumulation) }}</span>
            <span v-if="r.premium > 0" class="ltr-number kd-r-prem">{{ money(r.premium) }} פרמיה</span>
          </span>
        </li>
        <li v-if="!filteredRank.length" class="kd-none">אין תוצאות.</li>
      </ul>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import api from '../../api/client'
import { money } from '../../utils/chartDefaults'
import { brandForLabel } from '../../utils/companyBrand'

const props = defineProps({
  kind: { type: String, required: true },   // products | clients | accumulation | companies | status
  analytics: { type: Object, required: true },
})

const isClients = computed(() => ['clients', 'accumulation', 'premium'].includes(props.kind))
const brand = (name) => {
  const b = brandForLabel(name || '')
  return b && b.label && b.label !== '?' ? b.label : (name || '—')
}

// ── clients ──
const clients = ref([])
const loading = ref(false)
const company = ref(null)
const query = ref('')
const sortKey = ref('accumulation')
const openId = ref(null)
const limit = ref(100)
// Declared up here: the kind-watcher below runs immediately and resets it —
// declared later it was a temporal-dead-zone error and the drill never mounted.
const statusGroup = ref(null)
const SORTS = [
  { key: 'accumulation', label: 'צבירה' },
  { key: 'premium', label: 'פרמיה' },
  { key: 'products', label: 'מוצרים' },
  { key: 'name', label: 'שם' },
]

async function loadClients() {
  loading.value = true
  try {
    const res = await api.get('/production/breakdown/clients')
    clients.value = (res.data.clients || []).map(c => ({
      ...c, cos: [...new Set((c.products || []).map(p => p.company).filter(Boolean))],
    }))
  } catch { clients.value = [] } finally { loading.value = false }
}

watch(() => props.kind, (k) => {
  statusGroup.value = null
  company.value = null; query.value = ''; openId.value = null; limit.value = 100
  sortKey.value = k === 'premium' ? 'premium' : 'accumulation'
  if (isClients.value && !clients.value.length) loadClients()
}, { immediate: true })

const companyCuts = computed(() => {
  const m = new Map()
  for (const c of clients.value) for (const co of c.cos) m.set(co, (m.get(co) || 0) + 1)
  return [...m].map(([key, count]) => ({ key, count })).sort((a, b) => b.count - a.count)
})

const shownClients = computed(() => {
  const q = query.value
  const out = []
  for (const c of clients.value) {
    if (q && !(c.name || '').includes(q) && !String(c.id_number).includes(q)) continue
    const products = c.products.filter(p =>
      (!company.value || p.company === company.value)
      && (!statusGroup.value || familyOf(p.status) === statusGroup.value))
    if (!products.length) continue
    out.push({
      ...c, shownProducts: products,
      sAccum: products.reduce((s, p) => s + (p.accumulation || 0), 0),
      sPrem: products.reduce((s, p) => s + (p.premium || 0), 0),
    })
  }
  const by = {
    accumulation: (a, b) => b.sAccum - a.sAccum || b.sPrem - a.sPrem,
    premium: (a, b) => b.sPrem - a.sPrem || b.sAccum - a.sAccum,
    products: (a, b) => b.shownProducts.length - a.shownProducts.length,
    name: (a, b) => (a.name || '').localeCompare(b.name || '', 'he'),
  }[sortKey.value]
  return out.sort(by)
})
const visibleClients = computed(() => shownClients.value.slice(0, limit.value))
watch([company, query, sortKey], () => { limit.value = 100 })

const primary = c => (sortKey.value === 'premium' ? (c.sPrem || c.sAccum) : (c.sAccum || c.sPrem))
const primaryLabel = c => {
  if (sortKey.value === 'premium') return c.sPrem ? 'פרמיה' : (c.sAccum ? 'צבירה' : '')
  return c.sAccum ? 'צבירה' : (c.sPrem ? 'פרמיה' : '')
}
function toggle(id) { openId.value = openId.value === id ? null : id }

// ── status groups ──
// The insurers' statuses folded into what they mean for the agent.
const FAMILY_OF = {
  'פעיל': 'active',
  'מוקפא': 'paused', 'לא פעיל': 'paused', 'ריסק זמני אוטומטי': 'paused',
  'שמירת כיסוי ביטוחי': 'paused', 'חסום להפקדות': 'paused', 'מסולק זמנית': 'paused',
  'סילוק': 'closed', 'מבוטל': 'closed', 'תום תקופה': 'closed', 'פדיון': 'closed', 'מסולק': 'closed',
}
const FAMILIES = [
  { key: 'active', label: 'פעיל', meaning: 'המוצר פעיל ומפקידים אליו' },
  { key: 'paused', label: 'ללא הפקדות', meaning: 'הכסף נשאר, אבל לא נכנסות הפקדות — שווה לבדוק עם הלקוח' },
  { key: 'closed', label: 'נסגר', meaning: 'המוצר סולק, בוטל או הסתיים' },
  { key: 'unknown', label: 'ללא סטטוס', meaning: 'החברה לא דיווחה סטטוס למוצרים האלה' },
]
const familyOf = st => (st ? (FAMILY_OF[String(st).trim()] || 'paused') : 'unknown')
const totalProducts = computed(() => props.analytics.total_records || 0)
const families = computed(() => {
  const parts = { active: [], paused: [], closed: [], unknown: [] }
  let known = 0
  for (const r of props.analytics.status_breakdown || []) {
    if (!r.status) continue
    parts[familyOf(r.status)].push({ label: r.status, count: r.count || 0 })
    known += r.count || 0
  }
  const unknown = Math.max(0, totalProducts.value - known)
  if (unknown) parts.unknown.push({ label: 'ללא סטטוס', count: unknown })
  return FAMILIES.map(f => ({
    ...f, parts: parts[f.key].sort((a, b) => b.count - a.count),
    count: parts[f.key].reduce((s, x) => s + x.count, 0),
  }))
})
const familyByKey = computed(() => Object.fromEntries(families.value.map(f => [f.key, f])))
const famCount = k => familyByKey.value[k]?.count || 0
const pctOf = n => {
  if (!totalProducts.value || !n) return 0
  const v = (n / totalProducts.value) * 100
  return v < 1 ? '<1' : Math.round(v)   // 2 of 1,931 is not "0%"
}

function openGroup(key) {
  statusGroup.value = key
  company.value = null; query.value = ''; openId.value = null; limit.value = 100
  if (!clients.value.length) loadClients()
}

// ── ranked lists ──
const rankRows = computed(() => {
  const a = props.analytics
  let rows = []
  if (props.kind === 'products') {
    rows = (a.product_type_breakdown || []).map(r => ({
      label: r.product_type || 'ללא סוג', value: r.count || 0, premium: r.premium || 0, accumulation: r.accumulation || 0,
    }))
  } else if (props.kind === 'companies') {
    // One insurer, not its legal entities (מנורה ביטוח + מנורה פנסיה וגמל).
    const m = new Map()
    for (const r of a.company_breakdown || []) {
      const k = brand(r.company)
      const e = m.get(k) || { label: k, value: 0, clients: 0, premium: 0, accumulation: 0 }
      e.value += r.count || 0; e.clients += r.unique_clients || 0
      e.premium += r.premium || 0; e.accumulation += r.accumulation || 0
      m.set(k, e)
    }
    rows = [...m.values()].map(e => ({ ...e, sub: `${e.clients.toLocaleString()} לקוחות` }))
  } else if (props.kind === 'status') {
    rows = (a.status_breakdown || []).map(r => ({ label: r.status || 'ללא סטטוס', value: r.count || 0 }))
  }
  rows.sort((x, y) => y.value - x.value)
  const total = rows.reduce((s, r) => s + r.value, 0) || 1
  const top = rows[0]?.value || 1
  return rows.map(r => ({
    ...r,
    share: props.kind === 'status' ? Math.round((r.value / total) * 100) : Math.max(2, Math.round((r.value / top) * 100)),
  }))
})
const filteredRank = computed(() => {
  const q = query.value
  return q ? rankRows.value.filter(r => r.label.includes(q)) : rankRows.value
})

// ── summary strip ──
const stats = computed(() => {
  const a = props.analytics
  if (isClients.value || statusGroup.value) {
    const list = shownClients.value
    return [
      { label: 'לקוחות', value: list.length.toLocaleString() },
      { label: 'מוצרים', value: list.reduce((s, c) => s + c.shownProducts.length, 0).toLocaleString() },
      { label: 'צבירה', value: money(list.reduce((s, c) => s + c.sAccum, 0)) },
      { label: 'פרמיה חודשית', value: money(list.reduce((s, c) => s + c.sPrem, 0)) },
    ]
  }
  if (props.kind === 'status') return []
  if (props.kind === 'companies') {
    return [
      { label: 'חברות', value: String(rankRows.value.length) },
      { label: 'לקוחות', value: (a.unique_clients || 0).toLocaleString() },
      { label: 'צבירה', value: money(a.total_accumulation || 0) },
    ]
  }
  return [
    { label: 'מוצרים', value: (a.total_records || 0).toLocaleString() },
    { label: 'סוגי מוצר', value: String(rankRows.value.length) },
    { label: 'צבירה', value: money(a.total_accumulation || 0) },
  ]
})
</script>

<style scoped>
.kd { display: flex; flex-direction: column; gap: 16px; }

.kd-stats { display: flex; border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; }
.kd-stat { flex: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 14px 18px; }
.kd-stat + .kd-stat { border-inline-start: 1px solid var(--border-subtle); }
.kd-stat-lbl { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.kd-stat-val { font-size: 22px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; }
.kd-stat:first-child .kd-stat-val { color: var(--tab-production); }

.kd-tabs { display: flex; flex-wrap: wrap; gap: 2px 18px; border-bottom: 1px solid var(--border-subtle); }
.kd-tab {
  position: relative; border: none; background: none; font: inherit; font-size: 13.5px; font-weight: 600;
  color: var(--text-muted); padding: 8px 0 10px; cursor: pointer; transition: color 0.2s ease;
}
.kd-tab .ltr-number { font-weight: 500; margin-inline-start: 3px; }
.kd-tab:hover { color: var(--text); }
.kd-tab.on { color: var(--tab-production); }
.kd-tab.on::after { content: ''; position: absolute; inset-inline: 0; bottom: -1px; height: 2px; border-radius: 2px; background: var(--tab-production); }

.kd-tools { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.kd-search {
  flex: 1 1 220px; display: flex; align-items: center; gap: 8px; padding: 0 12px; height: 38px;
  border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--bg); color: var(--text-muted);
}
.kd-search--solo { flex: 0 0 auto; }
.kd-search:focus-within { border-color: var(--tab-production); background: var(--card-bg); }
.kd-search input { flex: 1; border: none; background: none; outline: none; font: inherit; font-size: 13px; color: var(--text); }
.kd-sort { display: flex; padding: 3px; border-radius: 10px; background: var(--bg); gap: 2px; }
.kd-sort button {
  border: none; background: none; font: inherit; font-size: 12px; font-weight: 600; color: var(--text-muted);
  padding: 7px 12px; border-radius: 8px; cursor: pointer;
}
.kd-sort button.on { background: var(--card-bg); color: var(--tab-production); box-shadow: var(--shadow-sm); }

.kd-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.kd-none { text-align: center; color: var(--text-muted); font-size: 13px; padding: 20px; list-style: none; }
.kd-item { border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg); transition: border-color 0.2s ease; }
.kd-item:hover { border-color: color-mix(in srgb, var(--tab-production) 40%, var(--border-subtle)); }
.kd-item.open { border-color: var(--tab-production); }
.kd-row {
  width: 100%; display: grid; align-items: center; gap: 12px;
  grid-template-columns: minmax(120px, 1.4fr) minmax(0, 1fr) 36px 120px 16px;
  padding: 10px 14px; border: none; background: none; font: inherit; color: var(--text); text-align: right; cursor: pointer;
}
.kd-row:focus-visible { outline: 2px solid var(--tab-production); outline-offset: -2px; border-radius: 12px; }
.kd-who { display: flex; flex-direction: column; min-width: 0; }
.kd-name { font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kd-id { font-size: 11.5px; color: var(--text-muted); }
.kd-cos { font-size: 12.5px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kd-pill {
  justify-self: center; min-width: 28px; height: 24px; padding: 0 8px; border-radius: 12px; background: var(--bg);
  font-size: 12px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center;
}
.kd-amt { display: flex; flex-direction: column; align-items: flex-start; font-size: 14px; font-weight: 700; line-height: 1.2; }
.kd-amt small { font-size: 10.5px; font-weight: 500; color: var(--text-muted); }
.kd-chev { color: var(--text-muted); transition: transform 0.25s ease; }
.kd-item.open .kd-chev { transform: rotate(180deg); color: var(--tab-production); }
.kd-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.3s cubic-bezier(0.2, 0, 0.2, 1); }
.kd-fold.open { grid-template-rows: 1fr; }
.kd-fold-inner { overflow: hidden; min-height: 0; }
.kd-products { margin: 0 14px 12px; padding: 6px; border-radius: 10px; background: var(--bg); display: flex; flex-direction: column; gap: 4px; }
.kd-product {
  display: grid; grid-template-columns: minmax(0, 1fr) 110px 110px; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 8px; background: var(--card-bg);
}
.kd-p-name { display: flex; flex-direction: column; font-size: 13px; font-weight: 600; min-width: 0; }
.kd-p-name small { font-size: 11px; font-weight: 400; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kd-p-fig { display: flex; flex-direction: column; align-items: flex-start; font-size: 13px; font-weight: 700; }
.kd-p-fig small { font-size: 10.5px; font-weight: 500; color: var(--text-muted); }
.kd-more {
  align-self: center; border: 1px solid var(--border-subtle); background: var(--card-bg); border-radius: 10px;
  padding: 9px 16px; font: inherit; font-size: 13px; font-weight: 600; color: var(--tab-production); cursor: pointer;
}

/* ranked lists */
.kd-rank { list-style: none; display: flex; flex-direction: column; }
.kd-rank li {
  display: grid; grid-template-columns: minmax(120px, 1.2fr) minmax(80px, 1fr) 70px 150px; align-items: center; gap: 14px;
  padding: 11px 4px; border-bottom: 1px solid var(--border-subtle);
}
.kd-rank li:last-child { border-bottom: none; }
.kd-r-name { display: flex; flex-direction: column; font-size: 14px; font-weight: 600; color: var(--text); min-width: 0; }
.kd-r-name small { font-size: 11.5px; font-weight: 400; color: var(--text-muted); }
.kd-r-bar { height: 8px; border-radius: 4px; background: var(--bg); overflow: hidden; }
.kd-r-bar i { display: block; height: 100%; border-radius: 4px; background: var(--tab-production); opacity: 0.75; }
.kd-r-num { font-size: 14px; font-weight: 700; color: var(--text); }
.kd-r-pct { font-size: 13px; color: var(--text-muted); }
.kd-r-amt { display: flex; flex-direction: column; align-items: flex-start; font-size: 13.5px; font-weight: 700; color: var(--text); }
.kd-r-prem { font-size: 11.5px; font-weight: 500; color: var(--text-muted); }

.kd-seg { display: flex; gap: 3px; height: 14px; }
.kd-seg-part { flex-basis: 0; min-width: 6px; border-radius: 5px; background: var(--tab-production); }

@media (max-width: 640px) {
  .kd-stats { flex-wrap: wrap; }
  .kd-stat { flex: 1 1 45%; padding: 10px 12px; }
  .kd-stat-val { font-size: 18px; }
  .kd-row { grid-template-columns: minmax(0, 1fr) 30px 96px 14px; gap: 8px; padding: 10px; }
  .kd-cos { display: none; }
  .kd-product { grid-template-columns: minmax(0, 1fr) 90px; }
  .kd-product .kd-p-fig + .kd-p-fig { display: none; }
  .kd-rank li { grid-template-columns: minmax(0, 1fr) 60px 100px; }
  .kd-r-bar { display: none; }
}
@media (prefers-reduced-motion: reduce) { .kd-fold, .kd-chev, .kd-item, .kd-tab { transition: none; } }
/* status groups */
.ks-head { display: flex; flex-direction: column; gap: 4px; }
.ks-big { display: flex; align-items: baseline; gap: 10px; }
.ks-big > .ltr-number { font-size: 40px; font-weight: 800; color: var(--tab-production); letter-spacing: -1px; line-height: 1; }
.ks-big small { font-size: 16px; font-weight: 600; color: var(--text); }
.ks-note { font-size: 13px; color: var(--text-muted); }
.ks-bar { display: flex; gap: 3px; height: 16px; }
.ks-part { flex-basis: 0; min-width: 6px; border-radius: 5px; }
.ks-part--active { background: var(--tab-production); }
.ks-part--paused { background: color-mix(in srgb, var(--tab-production) 50%, var(--card-bg)); }
.ks-part--closed { background: color-mix(in srgb, var(--tab-production) 22%, var(--card-bg)); }
.ks-part--unknown { background: var(--border-subtle); }
.ks-fams { list-style: none; display: flex; flex-direction: column; gap: 8px; }
.ks-fam {
  width: 100%; display: flex; align-items: center; gap: 14px; padding: 12px 14px;
  border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg);
  font: inherit; color: var(--text); text-align: right; cursor: pointer; transition: border-color 0.2s ease;
}
.ks-fam:hover:not(:disabled) { border-color: var(--tab-production); }
.ks-fam:disabled { cursor: default; }
.ks-fam:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }
.ks-dot { flex: 0 0 12px; height: 12px; border-radius: 4px; }
.ks-fam-txt { flex: 1; display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ks-fam-txt strong { font-size: 14.5px; }
.ks-fam-txt small { font-size: 12px; color: var(--text-muted); }
.ks-parts { font-size: 11.5px !important; }
.ks-fam-num { display: flex; flex-direction: column; align-items: flex-start; font-size: 18px; font-weight: 800; }
.ks-fam-num small { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.ks-go { color: var(--text-muted); flex: 0 0 auto; }
.ks-back {
  align-self: flex-start; display: inline-flex; align-items: center; gap: 6px; border: none; background: none;
  font: inherit; font-size: 13px; color: var(--tab-production); cursor: pointer; padding: 0;
}
.ks-back strong { color: var(--text); }
@media (max-width: 640px) { .ks-big > .ltr-number { font-size: 32px; } }
</style>
