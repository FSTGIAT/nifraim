<template>
  <div class="rate-card">
    <header class="rate-toolbar">
      <div class="rate-toolbar-titles">
        <h3>טבלת עמלות</h3>
        <p v-if="rates.length" class="rate-subtitle">
          <span class="ltr-number">{{ filteredCount }}</span>
          <template v-if="filteredCount !== rates.length"> / <span class="ltr-number">{{ rates.length }}</span></template>
          שיעורים ב-<span class="ltr-number">{{ visibleCategoryCount }}</span> קטגוריות
          <template v-if="yearFilter !== 'all'">
            · <span class="ltr-number">{{ yearFilterLabel }}</span>
          </template>
        </p>
      </div>
      <div class="rate-toolbar-actions">
        <label v-if="rates.length" class="rate-search">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="7"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input v-model="search" type="search" placeholder="חיפוש חברה או מוצר…" />
        </label>
        <button v-if="rates.length === 0" class="btn-primary" @click="seedRates" :disabled="seeding">
          {{ seeding ? 'טוען…' : 'טען ברירת מחדל' }}
        </button>
        <button v-if="rates.length > 0 && !addingNew" class="btn-primary" @click="startNew">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          הוסף שורה
        </button>
      </div>
    </header>

    <nav v-if="availableYears.length > 1" class="year-chips" aria-label="סינון לפי שנה">
      <button
        v-for="chip in availableYears"
        :key="chip.key"
        type="button"
        class="year-chip"
        :class="{ 'year-chip--active': yearFilter === chip.key }"
        :data-tone="chip.tone"
        @click="yearFilter = chip.key"
      >
        <span class="year-chip-label">{{ chip.label }}</span>
        <span class="year-chip-count ltr-number">{{ chip.count }}</span>
      </button>
    </nav>

    <div v-if="rates.length === 0 && !loading" class="empty">
      לא הוגדרו עמלות. לחץ "טען ברירת מחדל" להוספת טבלת עמלות ראשונית.
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>

    <div v-if="!loading && rates.length > 0" class="rate-groups">
      <section
        v-for="cat in visibleCategories"
        :key="cat.key"
        class="rate-group"
        :class="[`rate-group--${cat.key}`, { 'rate-group--collapsed': !isOpen(cat.key) }]"
      >
        <button
          type="button"
          class="rate-group-header"
          :aria-expanded="isOpen(cat.key)"
          @click="toggle(cat.key)"
        >
          <span class="rate-group-stripe" aria-hidden="true"></span>
          <span class="rate-group-icon" aria-hidden="true" v-html="cat.icon"></span>
          <span class="rate-group-title">{{ cat.label }}</span>
          <span class="rate-group-count">
            <span class="ltr-number">{{ cat.items.length }}</span>
            {{ cat.items.length === 1 ? 'שיעור' : 'שיעורים' }}
          </span>
          <span v-if="cat.range" class="rate-group-range ltr-number">{{ cat.range }}</span>
          <span class="rate-group-chevron" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="6 9 12 15 18 9"/>
            </svg>
          </span>
        </button>

        <Transition name="rate-collapse">
          <div v-show="isOpen(cat.key)" class="rate-group-body">
            <table class="rate-table">
              <colgroup>
                <col class="col-product"/>
                <col class="col-rate"/>
                <col class="col-freq"/>
                <col class="col-paidto"/>
                <col class="col-email"/>
                <col class="col-actions"/>
              </colgroup>
              <thead>
                <tr>
                  <th>מוצר</th>
                  <th class="num">אחוז</th>
                  <th>תדירות</th>
                  <th>נפרעים</th>
                  <th>אימייל</th>
                  <th class="actions-col"></th>
                </tr>
              </thead>
              <tbody v-for="group in cat.companies" :key="cat.key + ':' + group.company">
                <tr class="company-row">
                  <td colspan="6">
                    <div class="company-row-inner">
                      <span class="company-row-dot" aria-hidden="true"></span>
                      <span class="company-row-name">{{ group.company }}</span>
                      <span class="company-row-count">
                        <span class="ltr-number">{{ group.items.length }}</span>
                        {{ group.items.length === 1 ? 'שיעור' : 'שיעורים' }}
                      </span>
                      <span v-if="group.range" class="company-row-range ltr-number">{{ group.range }}</span>
                    </div>
                  </td>
                </tr>
                <tr v-for="rate in group.items" :key="rate.id">
                  <template v-if="editingId === rate.id">
                    <td>
                      <div class="edit-stack">
                        <input v-model="editForm.company_name" class="edit-input" placeholder="חברה" />
                        <input v-model="editForm.product" class="edit-input" placeholder="כל המוצרים" />
                      </div>
                    </td>
                    <td class="num">
                      <input v-model.number="editForm.rate" type="number" step="0.01" class="edit-input num-input" dir="ltr" placeholder="%" />
                    </td>
                    <td>
                      <select v-model="editForm.payment_frequency" class="edit-input">
                        <option value="חודשי">חודשי</option>
                        <option value="רבעוני">רבעוני</option>
                        <option value="שנתי">שנתי</option>
                      </select>
                    </td>
                    <td>
                      <select v-model="editForm.paid_to" class="edit-input">
                        <option value="עיתים">עיתים</option>
                        <option value="סוכן">סוכן</option>
                        <option value="ידנים">ידנים</option>
                      </select>
                    </td>
                    <td>
                      <input v-model="editForm.company_email" class="edit-input email-input" dir="ltr" placeholder="email@company.co.il" />
                    </td>
                    <td class="actions">
                      <button class="icon-btn icon-btn--save" @click="saveEdit(rate.id)" title="שמור">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                      </button>
                      <button class="icon-btn icon-btn--cancel" @click="editingId = null" title="ביטול">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                      </button>
                    </td>
                  </template>
                  <template v-else>
                    <td class="product-cell" :title="rate.product || 'כל המוצרים'">
                      <span class="product-line">
                        <span v-if="rate.product">{{ rate.product }}</span>
                        <span v-else class="product-cell--default">כל המוצרים</span>
                        <span v-if="rateYearLabel(rate)" class="year-pill ltr-number" :class="rateYearClass(rate)" :title="rateYearTitle(rate)">{{ rateYearLabel(rate) }}</span>
                      </span>
                    </td>
                    <td class="num"><span class="rate-pill ltr-number">{{ (rate.rate * 100).toFixed(2) }}%</span></td>
                    <td class="muted-cell">{{ rate.payment_frequency || '—' }}</td>
                    <td class="muted-cell">{{ rate.paid_to || '—' }}</td>
                    <td class="email-cell"><span class="ltr-number">{{ rate.company_email || '—' }}</span></td>
                    <td class="actions">
                      <button class="icon-btn icon-btn--edit" @click="startEdit(rate)" title="ערוך">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                      </button>
                      <button class="icon-btn icon-btn--del" @click="deleteRate(rate.id)" title="מחק">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>
                      </button>
                    </td>
                  </template>
                </tr>
              </tbody>
            </table>
          </div>
        </Transition>
      </section>

      <p v-if="search && !visibleCategoryCount" class="empty empty--filter">
        אין תוצאות עבור "<span class="ltr-number">{{ search }}</span>"
      </p>

      <!-- Add-new row sits at the bottom in its own card so users can pick the
           category by typing the product name; auto-categorization handles the rest. -->
      <section v-if="addingNew" class="rate-group rate-group--new">
        <div class="rate-group-header rate-group-header--static">
          <span class="rate-group-stripe rate-group-stripe--new" aria-hidden="true"></span>
          <span class="rate-group-icon rate-group-icon--new" aria-hidden="true">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          </span>
          <span class="rate-group-title">שורה חדשה</span>
          <span class="rate-group-hint">הקטגוריה תיקבע אוטומטית לפי שם המוצר</span>
        </div>
        <div class="rate-group-body">
          <table class="rate-table">
            <tbody>
              <tr>
                <td>
                  <div class="edit-stack">
                    <input v-model="newForm.company_name" class="edit-input" placeholder="שם חברה" />
                    <input v-model="newForm.product" class="edit-input" placeholder="שם מוצר (אופציונלי)" />
                  </div>
                </td>
                <td class="num"><input v-model.number="newForm.rate" type="number" step="0.01" class="edit-input num-input" dir="ltr" placeholder="%" /></td>
                <td>
                  <select v-model="newForm.payment_frequency" class="edit-input">
                    <option value="חודשי">חודשי</option>
                    <option value="רבעוני">רבעוני</option>
                    <option value="שנתי">שנתי</option>
                  </select>
                </td>
                <td>
                  <select v-model="newForm.paid_to" class="edit-input">
                    <option value="עיתים">עיתים</option>
                    <option value="סוכן">סוכן</option>
                    <option value="ידנים">ידנים</option>
                  </select>
                </td>
                <td><input v-model="newForm.company_email" class="edit-input email-input" dir="ltr" placeholder="email@company.co.il" /></td>
                <td class="actions">
                  <button class="icon-btn icon-btn--save" @click="saveNew" title="שמור">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </button>
                  <button class="icon-btn icon-btn--cancel" @click="cancelNew" title="ביטול">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive, watch } from 'vue'
import api from '../../api/client.js'

const emit = defineEmits(['rates-changed'])

const rates = ref([])
const loading = ref(false)
const seeding = ref(false)
const search = ref('')
const yearFilter = ref('all')  // 'all' | '<year-number>' | 'undated'
const editingId = ref(null)
const editForm = reactive({
  company_name: '', product: '', rate: 0,
  payment_frequency: '', paid_to: '', company_email: '',
})
const addingNew = ref(false)
const newForm = reactive({
  company_name: '', product: '', rate: 0,
  payment_frequency: 'חודשי', paid_to: 'עיתים', company_email: '',
})

// Lucide-style line icons. Picked to read at a glance for each category:
// "savings/pension" = piggy-coin, "life/risk" = shield, "health" = heart-pulse,
// "other" = layers. SVG strings are kept inline so we don't need an icon dep.
const ICONS = {
  savings: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/></svg>',
  risk:    '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>',
  health:  '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 8L9 4l-3 8H2"/></svg>',
  other:   '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
}

const CATEGORIES = [
  {
    key: 'savings',
    label: 'חיסכון ופנסיה',
    icon: ICONS.savings,
    keywords: ['גמל', 'השתלמ', 'פנסיה', 'פיננס', 'השקעה', 'חיסכון', 'צבירה', 'קצבה', 'הון', 'אקסלנס', 'מצנח'],
  },
  {
    key: 'risk',
    label: 'חיים וריסק',
    icon: ICONS.risk,
    keywords: ['ריסק', 'מנהלים', 'חיים', 'מטריה', 'אובדן', 'אכ"ע', 'אכע', 'נכות', 'תאונה', 'אקסטרה', 'רצף', 'משכנת', 'מוות'],
  },
  {
    key: 'health',
    label: 'בריאות',
    icon: ICONS.health,
    keywords: ['בריאות', 'ניתוח', 'השתל', 'תרופ', 'אמבולטור', 'שב"ן', 'שבן', 'סרטן', 'מרפא', 'מחלות', 'פלוס', 'שירותים'],
  },
  {
    key: 'other',
    label: 'אחר',
    icon: ICONS.other,
    keywords: [],
  },
]

function categorize(rate) {
  const text = (rate.product || '').toLowerCase()
  if (text) {
    for (const cat of CATEGORIES) {
      if (cat.keywords.some(k => text.includes(k))) return cat.key
    }
  }
  // No product OR no keyword hit — use rate magnitude as a fallback:
  // sub-percent → savings (gemel-style), > 1% → other (rare unclassified).
  const pct = (rate.rate || 0) * 100
  if (pct > 0 && pct <= 1) return 'savings'
  return 'other'
}

function matchesSearch(rate, q) {
  if (!q) return true
  const needle = q.toLowerCase().trim()
  return (
    (rate.company_name || '').toLowerCase().includes(needle) ||
    (rate.product || '').toLowerCase().includes(needle)
  )
}

function applyFilters(r) {
  return matchesSearch(r, search.value) && rateInYear(r, yearFilter.value)
}

const filteredCount = computed(() =>
  rates.value.filter(applyFilters).length
)

// Year chip set: derive distinct years from all rates' validity spans.
// "כל השנים" is always first; "ללא תאריך" appears only if at least one
// rate is missing dates (avoids a chip the user can't get to otherwise).
const availableYears = computed(() => {
  const yearSet = new Set()
  let undated = 0
  for (const r of rates.value) {
    const span = rateYearSpan(r)
    if (!span) { undated++; continue }
    for (let y = span.from; y <= span.to; y++) yearSet.add(y)
  }
  const nowYear = new Date().getFullYear()
  const sortedYears = [...yearSet].sort((a, b) => b - a)  // newest first
  const chips = [
    { key: 'all', label: 'כל השנים', count: rates.value.length, tone: 'all' },
    ...sortedYears.map(y => ({
      key: String(y),
      label: String(y),
      count: rates.value.filter(r => rateInYear(r, String(y))).length,
      tone: y >= nowYear - 1 ? 'current' : (y >= nowYear - 3 ? 'recent' : 'old'),
    })),
  ]
  if (undated) {
    chips.push({ key: 'undated', label: 'ללא תאריך', count: undated, tone: 'old' })
  }
  return chips
})

const yearFilterLabel = computed(() => {
  const chip = availableYears.value.find(c => c.key === yearFilter.value)
  return chip ? chip.label : ''
})

function _normCompany(name) {
  return (name || '').trim().replace(/^ה/, '')
}

// "Which years does this rate cover?" — used both for the row pill label
// and for membership in the year-filter chip set.
function rateYearSpan(rate) {
  const from = rate.effective_from
  const to = rate.effective_to
  const yf = from ? new Date(from).getFullYear() : null
  const yt = to ? new Date(to).getFullYear() : null
  if (!yf && !yt) return null
  return { from: yf ?? yt, to: yt ?? yf }
}

function rateInYear(rate, year) {
  if (year === 'all') return true
  const span = rateYearSpan(rate)
  if (year === 'undated') return span === null
  const y = parseInt(year, 10)
  if (!span) return false
  return span.from <= y && y <= span.to
}

function rateYearLabel(rate) {
  const from = rate.effective_from
  const to = rate.effective_to
  if (!from && !to) return null
  const yf = from ? new Date(from).getFullYear() : null
  const yt = to ? new Date(to).getFullYear() : null
  if (yf && yt && yf !== yt) return `${yf}–${yt}`
  return String(yf || yt)
}

function rateYearTitle(rate) {
  const from = rate.effective_from
  const to = rate.effective_to
  if (!from && !to) return ''
  if (from && to) return `תוקף: ${from} → ${to}`
  if (from) return `תוקף מ-${from}`
  return `תוקף עד ${to}`
}

// Color the year pill by recency. Current and last year glow in primary;
// older years fade to gray so the eye separates them at a glance.
function rateYearClass(rate) {
  const from = rate.effective_from
  const to = rate.effective_to
  const ref = to || from
  if (!ref) return ''
  const refYear = new Date(ref).getFullYear()
  const nowYear = new Date().getFullYear()
  if (refYear >= nowYear - 1) return 'year-pill--current'
  if (refYear >= nowYear - 3) return 'year-pill--recent'
  return 'year-pill--old'
}

const visibleCategories = computed(() => {
  return CATEGORIES.map(cat => {
    const items = rates.value
      .filter(r => categorize(r) === cat.key && applyFilters(r))
      .sort((a, b) => {
        // Company first, then product. Empty product (= "כל המוצרים") goes last.
        const cmp = _normCompany(a.company_name).localeCompare(_normCompany(b.company_name), 'he')
        if (cmp !== 0) return cmp
        if (!a.product && b.product) return 1
        if (a.product && !b.product) return -1
        return (a.product || '').localeCompare(b.product || '', 'he')
      })

    // Sub-group by company so the user sees insurance-company-level boundaries
    // inside each category. Companies are sorted by row count desc (the
    // "biggest exposure" first) and then alphabetically as a tiebreaker.
    const byCompany = new Map()
    for (const r of items) {
      const key = r.company_name || '—'
      if (!byCompany.has(key)) byCompany.set(key, [])
      byCompany.get(key).push(r)
    }
    const companies = Array.from(byCompany.entries())
      .map(([company, list]) => {
        const pcts = list.map(r => +(r.rate * 100).toFixed(2)).filter(x => x > 0)
        const minPct = pcts.length ? Math.min(...pcts) : null
        const maxPct = pcts.length ? Math.max(...pcts) : null
        const range = pcts.length
          ? (minPct === maxPct ? `${minPct}%` : `${minPct}% – ${maxPct}%`)
          : ''
        return { company, items: list, range }
      })
      .sort((a, b) => {
        if (b.items.length !== a.items.length) return b.items.length - a.items.length
        return _normCompany(a.company).localeCompare(_normCompany(b.company), 'he')
      })

    const pcts = items.map(r => +(r.rate * 100).toFixed(2)).filter(x => x > 0)
    const range = pcts.length
      ? (Math.min(...pcts) === Math.max(...pcts)
          ? `${pcts[0]}%`
          : `${Math.min(...pcts)}% – ${Math.max(...pcts)}%`)
      : ''
    return { ...cat, items, companies, range }
  }).filter(cat => cat.items.length > 0)
})

const visibleCategoryCount = computed(() => visibleCategories.value.length)

// Open/closed state — persisted, with sensible defaults: all open on first
// visit, and a search query auto-expands categories that have matches.
const STORAGE_KEY = 'commission_rate_groups_open'
const openMap = ref(loadOpenState())

function loadOpenState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch { /* ignore */ }
  return { savings: true, risk: true, health: true, other: true }
}
function saveOpenState() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(openMap.value)) } catch { /* ignore */ }
}

function isOpen(key) {
  // Active search overrides the user's collapsed state — they're looking for
  // something, hiding matches would be hostile.
  if (search.value.trim()) return true
  return !!openMap.value[key]
}
function toggle(key) {
  if (search.value.trim()) return
  openMap.value = { ...openMap.value, [key]: !openMap.value[key] }
  saveOpenState()
}

onMounted(() => fetchRates())
watch(openMap, saveOpenState, { deep: true })

async function fetchRates() {
  loading.value = true
  try {
    const res = await api.get('/commission-rates')
    rates.value = res.data
  } finally {
    loading.value = false
  }
}

async function seedRates() {
  seeding.value = true
  try {
    await api.post('/commission-rates/seed')
    await fetchRates()
    emit('rates-changed')
  } finally {
    seeding.value = false
  }
}

function startEdit(rate) {
  addingNew.value = false
  editingId.value = rate.id
  editForm.company_name = rate.company_name
  editForm.product = rate.product || ''
  editForm.rate = +(rate.rate * 100).toFixed(4)
  editForm.payment_frequency = rate.payment_frequency || 'חודשי'
  editForm.paid_to = rate.paid_to || 'עיתים'
  editForm.company_email = rate.company_email || ''
}

async function saveEdit(id) {
  const payload = { ...editForm, rate: editForm.rate / 100, product: editForm.product || null }
  await api.put(`/commission-rates/${id}`, payload)
  editingId.value = null
  await fetchRates()
  emit('rates-changed')
}

async function deleteRate(id) {
  await api.delete(`/commission-rates/${id}`)
  await fetchRates()
  emit('rates-changed')
}

function startNew() {
  editingId.value = null
  addingNew.value = true
  newForm.company_name = ''
  newForm.product = ''
  newForm.rate = 0
  newForm.payment_frequency = 'חודשי'
  newForm.paid_to = 'עיתים'
  newForm.company_email = ''
}

function cancelNew() { addingNew.value = false }

async function saveNew() {
  if (!newForm.company_name) return
  const payload = { ...newForm, rate: newForm.rate / 100, product: newForm.product || null }
  await api.post('/commission-rates', payload)
  addingNew.value = false
  await fetchRates()
  emit('rates-changed')
}
</script>

<style scoped>
.rate-card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 18px 20px 14px;
}

.rate-toolbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.rate-toolbar-titles h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
  letter-spacing: -0.01em;
}

.rate-subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--text-muted);
}

.rate-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rate-search {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  background: var(--bg-surface);
  color: var(--text-muted);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.rate-search:focus-within {
  border-color: var(--primary);
  box-shadow: var(--shadow-glow);
  color: var(--primary);
}
.rate-search input {
  border: none;
  outline: none;
  background: transparent;
  font-family: inherit;
  font-size: 12px;
  width: 160px;
  color: var(--text);
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, var(--primary-deep), var(--primary));
  color: white;
  border: none;
  border-radius: 8px;
  padding: 7px 14px;
  font-size: 13px;
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}
.btn-primary:hover:not(:disabled) {
  box-shadow: 0 4px 14px var(--primary-light);
  transform: translateY(-1px);
}
.btn-primary:disabled { opacity: 0.5; cursor: default; }

/* ── Year filter chips ─────────────────────────────────────────── */

.year-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px dashed var(--border-subtle);
}

.year-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 11px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.18s var(--transition);
}
.year-chip:hover {
  border-color: var(--primary);
  color: var(--text);
}
.year-chip-count {
  font-size: 10.5px;
  font-weight: 700;
  padding: 1px 7px;
  background: var(--bg);
  border-radius: 999px;
  color: var(--text-muted);
}
/* Active state — tinted by recency to maintain consistency with the row pills.
   The "all" chip uses neutral charcoal; current year glows primary;
   older years stay quieter. */
.year-chip--active {
  background: var(--text);
  border-color: var(--text);
  color: #fff;
}
.year-chip--active .year-chip-count {
  background: rgba(255, 255, 255, 0.18);
  color: #fff;
}
.year-chip--active[data-tone="current"] {
  background: var(--primary-deep);
  border-color: var(--primary-deep);
  box-shadow: 0 4px 14px var(--primary-light);
}
.year-chip--active[data-tone="recent"] {
  background: var(--text-secondary);
  border-color: var(--text-secondary);
}
.year-chip--active[data-tone="old"] {
  background: var(--text-muted);
  border-color: var(--text-muted);
}

/* ── Groups (categories) ───────────────────────────────────────── */

.rate-groups {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.rate-group {
  position: relative;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: box-shadow 0.25s var(--transition);
}
.rate-group:hover { box-shadow: var(--shadow-sm); }

/* Each category claims a tint from the existing palette. Backgrounds are
   the *-light tokens so the page stays bright/white-dominant overall. */
.rate-group--savings { --cat: var(--primary); --cat-deep: var(--primary-deep); --cat-tint: var(--primary-light); }
.rate-group--risk    { --cat: var(--accent-violet); --cat-deep: #5a39b8; --cat-tint: #F2EDFB; }
.rate-group--health  { --cat: var(--accent-emerald); --cat-deep: var(--green-deep); --cat-tint: var(--green-light); }
.rate-group--other   { --cat: var(--text-muted); --cat-deep: var(--text-secondary); --cat-tint: #F1F1F1; }
.rate-group--new     { --cat: var(--primary); --cat-deep: var(--primary-deep); --cat-tint: var(--primary-light); }

.rate-group-header {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px 12px 14px;
  background: linear-gradient(95deg, var(--cat-tint) 0%, transparent 70%);
  border: none;
  cursor: pointer;
  font-family: inherit;
  text-align: right;
  color: var(--text);
  transition: background 0.2s;
}
.rate-group-header:hover { background: linear-gradient(95deg, var(--cat-tint) 0%, var(--bg-surface) 80%); }
.rate-group-header--static { cursor: default; }
.rate-group-header--static:hover { background: linear-gradient(95deg, var(--cat-tint) 0%, transparent 70%); }

.rate-group-stripe {
  position: absolute;
  inset-block: 0;
  inset-inline-end: 0;
  width: 4px;
  background: var(--cat);
}

.rate-group-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: var(--bg-surface);
  border: 1px solid var(--cat);
  border-radius: 8px;
  color: var(--cat-deep);
  flex: 0 0 auto;
}
.rate-group-icon--new { border-style: dashed; }

.rate-group-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.005em;
  flex: 0 0 auto;
}

.rate-group-count {
  font-size: 11px;
  color: var(--cat-deep);
  font-weight: 600;
  padding: 3px 9px;
  background: var(--bg-surface);
  border: 1px solid var(--cat);
  border-radius: 999px;
  flex: 0 0 auto;
}

.rate-group-range {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
  padding: 3px 8px;
  background: var(--bg);
  border-radius: 6px;
  flex: 0 0 auto;
}

.rate-group-hint {
  font-size: 11px;
  color: var(--text-muted);
  flex: 0 0 auto;
}

.rate-group-chevron {
  margin-inline-start: auto;
  color: var(--text-muted);
  display: inline-flex;
  align-items: center;
  transition: transform 0.25s var(--transition);
}
.rate-group--collapsed .rate-group-chevron { transform: rotate(-90deg); }

.rate-group-body {
  background: var(--bg-surface);
  border-top: 1px solid var(--border-subtle);
}

/* ── Table ─────────────────────────────────────────────────────── */

.rate-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.rate-table thead {
  background: var(--glass-hover);
}
.rate-table th {
  padding: 8px 10px;
  text-align: right;
  font-weight: 600;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.rate-table th.num, .rate-table td.num { text-align: left; }
.rate-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
  vertical-align: middle;
}
.rate-table tbody tr { transition: background 0.15s; }
.rate-table tbody tr:hover { background: var(--glass-hover); }
.rate-table tbody:last-child tr:last-child td { border-bottom: none; }
.rate-table tbody + tbody tr:first-child td { border-top: 1px solid var(--border-subtle); }

/* Column hints — the table is responsive but these prevent the rate pill
   from stretching past its content and let the product cell soak up the rest. */
.col-product { width: auto; }
.col-rate    { width: 90px; }
.col-freq    { width: 90px; }
.col-paidto  { width: 90px; }
.col-email   { width: 200px; }
.col-actions { width: 60px; }

/* Company-level sub-header inside a category. Quieter than the category
   header but with enough weight that the eye lands on it during scanning. */
.company-row td {
  padding: 8px 12px;
  background: var(--bg);
  border-bottom: 1px solid var(--border-subtle);
}
.company-row:hover td { background: var(--bg); }   /* don't tint on hover */
.company-row-inner {
  display: flex;
  align-items: center;
  gap: 10px;
}
.company-row-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--cat);
  flex: 0 0 auto;
}
.company-row-name {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.005em;
}
.company-row-count {
  font-size: 10.5px;
  font-weight: 600;
  color: var(--text-muted);
  padding: 2px 8px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
}
.company-row-range {
  font-size: 10.5px;
  font-weight: 600;
  color: var(--cat-deep);
  padding: 2px 8px;
  background: var(--cat-tint);
  border-radius: 999px;
  margin-inline-start: auto;
}

.edit-stack {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.product-cell {
  color: var(--text-secondary);
  max-width: 320px;
}
.product-line {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  max-width: 100%;
}
.product-line > span:first-child {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 0 1 auto;
}
.product-cell--default { color: var(--text-muted); font-style: italic; }

.year-pill {
  flex: 0 0 auto;
  font-size: 10px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 999px;
  border: 1px solid transparent;
  letter-spacing: 0.02em;
  line-height: 1.4;
}
.year-pill--current {
  background: var(--primary-light);
  color: var(--primary-deep);
  border-color: var(--primary);
}
.year-pill--recent {
  background: var(--bg);
  color: var(--text-secondary);
  border-color: var(--border-subtle);
}
.year-pill--old {
  background: transparent;
  color: var(--text-muted);
  border-color: var(--border-subtle);
}

.muted-cell { color: var(--text-muted); }

.rate-pill {
  display: inline-block;
  min-width: 56px;
  text-align: center;
  padding: 3px 10px;
  background: var(--cat-tint);
  color: var(--cat-deep);
  border-radius: 999px;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.email-cell {
  font-size: 11px;
  color: var(--text-muted);
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actions {
  display: flex;
  gap: 4px;
  white-space: nowrap;
  justify-content: flex-end;
}
.actions-col { width: 60px; }

.icon-btn {
  width: 26px;
  height: 26px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  color: var(--text-muted);
  transition: all 0.18s var(--transition);
}
.icon-btn--edit:hover  { background: var(--primary-light); color: var(--primary-deep); border-color: var(--primary); }
.icon-btn--del:hover   { background: var(--red-light); color: var(--red); border-color: var(--red); }
.icon-btn--save:hover  { background: var(--green-light); color: var(--green-deep); border-color: var(--green); }
.icon-btn--cancel:hover { background: var(--red-light); color: var(--red); border-color: var(--red); }

.ltr-number { direction: ltr; unicode-bidi: isolate; }

.edit-input {
  width: 100%;
  padding: 5px 8px;
  border: 1px solid var(--glass-border);
  border-radius: 6px;
  font-size: 12px;
  font-family: 'Heebo', sans-serif;
  background: var(--bg-surface);
  color: var(--text);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.edit-input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: var(--shadow-glow);
}
.num-input { width: 86px; }
.email-input { width: 160px; }

.empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 24px 16px;
}
.empty--filter { padding: 16px; }

.loading {
  display: flex;
  justify-content: center;
  padding: 24px 16px;
}
.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Collapse transition ───────────────────────────────────────── */

.rate-collapse-enter-active,
.rate-collapse-leave-active {
  transition: grid-template-rows 0.28s var(--transition), opacity 0.2s;
  display: grid;
  grid-template-rows: 1fr;
}
.rate-collapse-enter-from,
.rate-collapse-leave-to {
  grid-template-rows: 0fr;
  opacity: 0;
}
.rate-collapse-enter-active > *,
.rate-collapse-leave-active > * { overflow: hidden; min-height: 0; }
</style>
