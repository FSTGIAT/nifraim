<template>
  <!-- "לקוחות שלא התקבל בגינם תשלום" — redesigned (QA 2026-09-30: two walls of
       chips over a plain table read as noise). The shape now answers the
       agent's questions in order: HOW MUCH is at stake (the strip), WHERE
       (one bar split by insurer — it is also the company filter), and WHO
       (client cards that open into the exact policies to quote to the
       insurer). The product filter is a single select, not 13 chips. -->
  <div class="ud">
    <!-- How much -->
    <div class="ud-stats">
      <div class="ud-stat">
        <span class="ud-stat-val ltr-number">{{ shown.length }}</span>
        <span class="ud-stat-lbl">לקוחות{{ isFiltered ? ` מתוך ${rows.length}` : '' }}</span>
      </div>
      <div class="ud-stat">
        <span class="ud-stat-val ltr-number">{{ totalProducts }}</span>
        <span class="ud-stat-lbl">מוצרים ללא עמלה</span>
      </div>
      <div v-if="totalAccum > 0" class="ud-stat">
        <span class="ud-stat-val ltr-number">{{ compact(totalAccum) }}</span>
        <span class="ud-stat-lbl">צבירה בלי תשלום</span>
      </div>
      <div v-if="totalPremium > 0" class="ud-stat">
        <span class="ud-stat-val ltr-number">{{ money(totalPremium) }}</span>
        <span class="ud-stat-lbl">פרמיה חודשית</span>
      </div>
    </div>

    <!-- Where: every insurer as a text tab with its count — all of them
         readable at any size. A proportional colour bar hid the small ones
         ("מגדל 9" had no room for its name) and added colour for its own sake
         (QA 2026-09-30). -->
    <div class="ud-cos-tabs" role="tablist" aria-label="סינון לפי חברה">
      <button role="tab" class="ud-tab" :class="{ on: !company }" :aria-selected="!company"
              @click="company = null">
        הכל <span class="ltr-number">{{ rows.length }}</span>
      </button>
      <button v-for="c in companyCuts" :key="c.key" role="tab" class="ud-tab"
              :class="{ on: company === c.key }" :aria-selected="company === c.key"
              @click="company = company === c.key ? null : c.key">
        {{ c.key }} <span class="ltr-number">{{ c.count }}</span>
      </button>
    </div>

    <!-- Tools: search · product · sort -->
    <div class="ud-tools">
      <label class="ud-search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input v-model.trim="query" type="search" placeholder="חיפוש לפי שם או ת.ז" />
      </label>
      <div class="ud-select">
        <select v-model="ptype" aria-label="סוג מוצר">
          <option :value="null">כל סוגי המוצרים</option>
          <option v-for="t in typeCuts" :key="t.key" :value="t.key">{{ t.key }} ({{ t.count }})</option>
        </select>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </div>
      <div class="ud-sort" role="group" aria-label="מיון">
        <button v-for="s in SORTS" :key="s.key" :class="{ on: sortKey === s.key }"
                @click="sortKey = s.key">{{ s.label }}</button>
      </div>
    </div>

    <p class="ud-note">
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor"
           stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" /><line x1="12" y1="8" x2="12.01" y2="8" />
      </svg>
      יש להם מוצר בפרודוקציה ואין עליו עמלה בדוחות של {{ covered.join(', ') }}. לחץ על לקוח לרשימת הפוליסות.
    </p>

    <!-- Who -->
    <ul class="ud-list">
      <li v-if="!shown.length" class="ud-none">
        אין לקוחות שתואמים לסינון.
        <button class="ud-clear" @click="resetFilters">נקה סינון</button>
      </li>
      <li v-for="u in shown" :key="u.id_number" class="ud-item" :class="{ 'ud-item--open': openId === u.id_number }">
        <button class="ud-row" :aria-expanded="openId === u.id_number" @click="toggle(u.id_number)">
          <span class="ud-who">
            <span class="ud-name">{{ u.name || u.id_number }}</span>
            <span class="ud-id ltr-number">{{ u.id_number }}</span>
          </span>
          <span class="ud-cos">{{ u.companies.join(' · ') }}</span>
          <span class="ud-pill ltr-number" :title="`${u.shownItems.length || u.products} מוצרים`">
            {{ u.shownItems.length || u.products }}
          </span>
          <span class="ud-amt">
            <span v-if="u.shownAccum > 0" class="ltr-number">{{ money(u.shownAccum) }}</span>
            <span v-else-if="u.shownPremium > 0" class="ltr-number">{{ money(u.shownPremium) }}</span>
            <small>{{ u.shownAccum > 0 ? 'צבירה' : (u.shownPremium > 0 ? 'פרמיה' : '') }}</small>
          </span>
          <svg class="ud-chev" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
        <div class="ud-fold" :class="{ 'ud-fold--open': openId === u.id_number }">
          <div class="ud-fold-inner">
            <div class="ud-policies">
              <div v-for="(it, i) in u.shownItems" :key="i" class="ud-policy">
                <span class="ud-policy-name" :title="it.product || it.product_type">
                  {{ it.product || it.product_type || 'מוצר ללא שם' }}
                  <small>{{ it.company }}{{ it.product_type && it.product ? ' · ' + it.product_type : '' }}</small>
                </span>
                <span class="ud-policy-no">
                  <template v-if="it.policy_number">
                    <small>פוליסה</small>
                    <span class="ltr-number">{{ it.policy_number }}</span>
                  </template>
                </span>
                <span class="ud-policy-amt ltr-number">
                  {{ it.accumulation > 0 ? money(it.accumulation) : (it.premium > 0 ? money(it.premium) : '') }}
                </span>
              </div>
              <p v-if="!u.shownItems.length" class="ud-policy-none">אין פירוט מוצרים לרשומה הזו</p>
            </div>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { money } from '../../utils/chartDefaults'

const props = defineProps({
  rows: { type: Array, default: () => [] },       // /production/alerts `unpaid`
  covered: { type: Array, default: () => [] },    // companies checked
})

const company = ref(null)
const ptype = ref(null)
const query = ref('')
const sortKey = ref('value')
const openId = ref(null)
const SORTS = [
  { key: 'value', label: 'סכום' },
  { key: 'products', label: 'מוצרים' },
  { key: 'name', label: 'שם' },
]

const typeOf = it => (it.product_type || '').trim() || 'ללא סוג'
const isFiltered = computed(() => !!(company.value || ptype.value || query.value))

// Clients per value, counted against the OTHER filter so every number equals
// what pressing it shows.
function countBy(keysOf, otherOk) {
  const m = new Map()
  for (const u of props.rows) {
    for (const k of new Set((u.items || []).filter(otherOk).map(keysOf))) m.set(k, (m.get(k) || 0) + 1)
  }
  return [...m].map(([key, count]) => ({ key, count })).sort((a, b) => b.count - a.count)
}
const companyCuts = computed(() => countBy(it => it.company, it => !ptype.value || typeOf(it) === ptype.value))
const typeCuts = computed(() => countBy(typeOf, it => !company.value || it.company === company.value))
// A product type that no longer exists under the chosen company is cleared,
// so the select never shows a value with zero rows behind it.
watch(typeCuts, cuts => { if (ptype.value && !cuts.some(t => t.key === ptype.value)) ptype.value = null })

const shown = computed(() => {
  const q = query.value
  const cut = company.value || ptype.value
  const out = []
  for (const u of props.rows) {
    if (q && !(u.name || '').includes(q) && !String(u.id_number).includes(q)) continue
    const items = (u.items || []).filter(it =>
      (!company.value || it.company === company.value) && (!ptype.value || typeOf(it) === ptype.value))
    if (cut && !items.length) continue
    out.push({
      ...u,
      shownItems: cut ? items : (u.items || []),
      // Uncut: the client's own totals (items are capped per client); cut:
      // only the policies inside the slice.
      shownPremium: cut ? items.reduce((s, it) => s + (it.premium || 0), 0) : u.premium,
      shownAccum: cut ? items.reduce((s, it) => s + (it.accumulation || 0), 0) : u.accumulation,
    })
  }
  if (sortKey.value === 'name') return out.sort((a, b) => (a.name || '').localeCompare(b.name || '', 'he'))
  if (sortKey.value === 'products') {
    return out.sort((a, b) => (b.shownItems.length || b.products) - (a.shownItems.length || a.products))
  }
  // The value at stake — the same weighting the server ranks by.
  return out.sort((a, b) => (b.shownPremium + b.shownAccum / 12) - (a.shownPremium + a.shownAccum / 12))
})

const totalProducts = computed(() => shown.value.reduce((s, u) => s + (u.shownItems.length || u.products), 0))
const totalAccum = computed(() => shown.value.reduce((s, u) => s + (u.shownAccum || 0), 0))
const totalPremium = computed(() => shown.value.reduce((s, u) => s + (u.shownPremium || 0), 0))

function toggle(id) { openId.value = openId.value === id ? null : id }
function resetFilters() { company.value = null; ptype.value = null; query.value = '' }

function compact(v) {
  const n = Number(v) || 0
  if (n >= 1e6) return '₪' + (n / 1e6).toFixed(n >= 1e7 ? 1 : 2) + 'M'
  if (n >= 1e3) return '₪' + Math.round(n / 1e3) + 'K'
  return money(n)
}
</script>

<style scoped>
.ud { display: flex; flex-direction: column; gap: 16px; }

/* ── How much ── */
.ud-stats {
  display: flex; gap: 0; border: 1px solid var(--border-subtle); border-radius: 14px;
  background: var(--card-bg);
  overflow: hidden;
}
.ud-stat { flex: 1; display: flex; flex-direction: column; gap: 2px; padding: 14px 18px; }
.ud-stat + .ud-stat { border-inline-start: 1px solid var(--border-subtle); }
.ud-stat-val { font-size: 24px; font-weight: 800; color: var(--text); letter-spacing: -0.5px; }
.ud-stat-lbl { font-size: 12px; color: var(--text-muted); }

/* ── Where: company tabs ── */
.ud-cos-tabs {
  display: flex; flex-wrap: wrap; gap: 2px 18px;
  border-bottom: 1px solid var(--border-subtle);
}
.ud-tab {
  position: relative; border: none; background: none; font: inherit; font-size: 13.5px;
  font-weight: 600; color: var(--text-muted); padding: 8px 0 10px; cursor: pointer;
  transition: color 0.2s ease;
}
.ud-tab .ltr-number { font-weight: 500; margin-inline-start: 3px; }
.ud-tab:hover { color: var(--text); }
.ud-tab.on { color: var(--tab-production); }
.ud-tab.on::after {
  content: ''; position: absolute; inset-inline: 0; bottom: -1px; height: 2px;
  border-radius: 2px; background: var(--tab-production);
}
.ud-tab:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; border-radius: 4px; }
.ud-clear {
  border: none; background: none; font: inherit; font-size: 12px; font-weight: 600;
  color: var(--tab-production); cursor: pointer; padding: 0;
}

/* ── Tools ── */
.ud-tools { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ud-search {
  flex: 1 1 220px; display: flex; align-items: center; gap: 8px; padding: 0 12px; height: 38px;
  border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--bg); color: var(--text-muted);
}
.ud-search:focus-within { border-color: var(--tab-production); background: var(--card-bg); }
.ud-search input { flex: 1; border: none; background: none; outline: none; font: inherit; font-size: 13px; color: var(--text); }
.ud-select { position: relative; display: flex; align-items: center; }
.ud-select select {
  appearance: none; height: 38px; padding: 0 12px 0 30px; border-radius: 10px;
  border: 1px solid var(--border-subtle); background: var(--card-bg); font: inherit; font-size: 13px;
  color: var(--text); cursor: pointer; max-width: 240px;
}
.ud-select select:focus { outline: none; border-color: var(--tab-production); }
.ud-select svg { position: absolute; left: 11px; pointer-events: none; color: var(--text-muted); }
.ud-sort { display: flex; padding: 3px; border-radius: 10px; background: var(--bg); gap: 2px; }
.ud-sort button {
  border: none; background: none; font: inherit; font-size: 12px; font-weight: 600; color: var(--text-muted);
  padding: 7px 12px; border-radius: 8px; cursor: pointer; transition: background 0.2s ease, color 0.2s ease;
}
.ud-sort button.on { background: var(--card-bg); color: var(--tab-production); box-shadow: var(--shadow-sm); }

.ud-note { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-muted); margin: -4px 0 0; }

/* ── Who ── */
.ud-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.ud-none { text-align: center; color: var(--text-muted); font-size: 13px; padding: 24px; display: flex; gap: 10px; justify-content: center; }
.ud-item {
  border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg);
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.ud-item:hover { border-color: color-mix(in srgb, var(--tab-production) 40%, var(--border-subtle)); }
.ud-item--open { border-color: var(--tab-production); box-shadow: 0 6px 18px color-mix(in srgb, var(--tab-production) 14%, transparent); }
.ud-row {
  width: 100%; display: grid; align-items: center; gap: 12px;
  grid-template-columns: minmax(120px, 1.4fr) minmax(0, 1fr) 36px 110px 16px;
  padding: 10px 14px; border: none; background: none; font: inherit; color: var(--text);
  text-align: right; cursor: pointer;
}
.ud-row:focus-visible { outline: 2px solid var(--tab-production); outline-offset: -2px; border-radius: 12px; }
.ud-who { display: flex; flex-direction: column; min-width: 0; }
.ud-name { font-size: 14px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ud-id { font-size: 11.5px; color: var(--text-muted); }
.ud-cos { font-size: 12.5px; color: var(--text-muted); min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ud-pill {
  justify-self: center; min-width: 28px; height: 24px; padding: 0 8px; border-radius: 12px;
  background: var(--bg); font-size: 12px; font-weight: 700; color: var(--text);
  display: inline-flex; align-items: center; justify-content: center;
}
.ud-amt { display: flex; flex-direction: column; align-items: flex-end; font-size: 14px; font-weight: 700; line-height: 1.2; }
.ud-amt small { font-size: 10.5px; font-weight: 500; color: var(--text-muted); }
.ud-chev { color: var(--text-muted); transition: transform 0.25s ease; }
.ud-item--open .ud-chev { transform: rotate(180deg); color: var(--tab-production); }

.ud-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.3s cubic-bezier(0.2, 0, 0.2, 1); }
.ud-fold--open { grid-template-rows: 1fr; }
.ud-fold-inner { overflow: hidden; min-height: 0; }
.ud-policies {
  margin: 0 14px 12px; padding: 6px; border-radius: 10px; background: var(--bg);
  display: flex; flex-direction: column; gap: 4px;
}
.ud-policy {
  display: grid; grid-template-columns: minmax(0, 1fr) 130px 110px; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 8px; background: var(--card-bg);
}
.ud-policy-name { display: flex; flex-direction: column; font-size: 13px; font-weight: 600; min-width: 0; }
.ud-policy-name small { font-size: 11px; font-weight: 400; color: var(--text-muted); }
.ud-policy-no { display: flex; flex-direction: column; align-items: flex-start; font-size: 12.5px; }
.ud-policy-no small { font-size: 10.5px; color: var(--text-muted); }
.ud-policy-amt { text-align: left; font-size: 13px; font-weight: 700; }
.ud-policy-none { font-size: 12px; color: var(--text-muted); text-align: center; padding: 8px; margin: 0; }

@media (max-width: 640px) {
  .ud-stats { flex-wrap: wrap; }
  .ud-stat { flex: 1 1 45%; padding: 10px 12px; }
  .ud-stat-val { font-size: 19px; }
  .ud-row { grid-template-columns: minmax(0, 1fr) 30px 92px 14px; gap: 8px; padding: 10px; }
  .ud-cos { display: none; }
  .ud-policy { grid-template-columns: minmax(0, 1fr) 90px; }
  .ud-policy-no { display: none; }
  .ud-select select { max-width: 160px; }
}
@media (prefers-reduced-motion: reduce) {
  .ud-tab, .ud-fold, .ud-chev, .ud-item, .ud-sort button { transition: none; }
}
</style>
