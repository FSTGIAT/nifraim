<template>
  <div class="rate-shelf">
    <!-- ── Hero (reference's left text + CTA) ── -->
    <header class="shelf-hero">
      <div class="hero-copy">
        <span class="hero-eyebrow">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="4" rx="1"/><rect x="3" y="10" width="18" height="4" rx="1"/><rect x="3" y="16" width="18" height="4" rx="1"/></svg>
          טבלת עמלות
        </span>
        <h2 class="hero-title">מדף ההסכמים שלך</h2>
        <p v-if="!rates.length" class="hero-sub">העלו הסכם עמלות והשיעורים יופיעו כאן על המדף.</p>
        <div class="hero-actions">
          <button class="btn-accent" @click="triggerUpload" :disabled="uploadingDoc">
            <svg v-if="!uploadingDoc" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
            <span v-if="uploadingDoc" class="btn-spin" aria-hidden="true"></span>
            {{ uploadingDoc ? 'מעבד הסכם…' : 'העלאת הסכם עמלות' }}
          </button>
          <button v-if="rates.length > 0 && !addingNew" class="btn-ghost" @click="startNew">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            הוסף שורה ידנית
          </button>
          <button v-if="rates.length === 0" class="btn-ghost" @click="seedRates" :disabled="seeding">{{ seeding ? 'טוען…' : 'טען ברירת מחדל' }}</button>
          <input ref="fileInput" type="file" accept="application/pdf" class="hidden-file" @change="onAgreementFile" />
        </div>
        <Transition name="fade">
          <div v-if="uploadingDoc" class="hero-upload">
            <div class="hu-bar"><div class="hu-fill" :style="{ width: uploadProgress + '%' }"></div></div>
            <span class="hu-label">{{ uploadStage === 'uploading' ? 'מעלה קובץ…' : uploadStage === 'complete' ? 'הושלם — מרענן' : 'מחלץ שיעורי עמלה…' }}</span>
          </div>
        </Transition>
        <Transition name="fade"><p v-if="uploadError" class="hero-upload-error">שגיאה בהעלאה: {{ uploadError }}</p></Transition>
      </div>
      <TabHeroLoop scene="commission-shelf" class="shelf-art" />
    </header>

    <div v-if="rates.length" class="shelf-toolbar">
      <label class="rate-search">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
        <input v-model="search" type="search" placeholder="חיפוש חברה או מוצר…" />
      </label>
      <nav v-if="availableYears.length > 1" class="year-chips" aria-label="סינון לפי שנה">
        <button v-for="chip in availableYears" :key="chip.key" type="button" class="year-chip" :class="{ 'year-chip--active': yearFilter === chip.key }" :data-tone="chip.tone" @click="yearFilter = chip.key">
          <span>{{ chip.label }}</span><span class="year-chip-count ltr-number">{{ chip.count }}</span>
        </button>
      </nav>
    </div>

    <div v-if="rates.length === 0 && !loading" class="empty">עדיין אין הסכמי עמלות. לחצו <strong>"העלאת הסכם עמלות"</strong> — נחלץ את השיעורים אוטומטית, או טענו ברירת מחדל.</div>
    <div v-if="loading" class="loading"><div class="spinner"></div></div>

    <!-- ── The shelf: a row of tall picture panels (your reference).
         Thin panels stand vertical like book spines; hover/click a panel to
         widen it and reveal its big picture. ── -->
    <div v-if="!loading && rates.length > 0 && visibleCategories.length" class="shelf-rack" :class="{ 'shelf-rack--open': !!activeShelf }">
      <button
        v-for="cat in visibleCategories"
        :key="cat.key"
        type="button"
        class="shelf-panel"
        :class="[`tint-${cat.key}`, { 'shelf-panel--active': activeShelf === cat.key }]"
        :aria-expanded="activeShelf === cat.key"
        @click="toggleShelf(cat.key)"
      >
        <span class="shelf-media" :class="{ 'shelf-media--fallback': !artFor(cat.key) }" :style="artFor(cat.key) ? { backgroundImage: `url(${artFor(cat.key)})` } : null"></span>
        <span class="shelf-veil"></span>
        <span class="shelf-caption">
          <span class="shelf-badge" v-html="cat.icon"></span>
          <span class="shelf-name">{{ cat.label }}</span>
          <span class="shelf-meta"><span class="ltr-number">{{ cat.items.length }}</span> שיעורים · <span class="ltr-number">{{ cat.companies.length }}</span> חברות</span>
          <span class="shelf-hint">
            <svg v-if="activeShelf !== cat.key" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M12 5v14M5 12h14"/></svg>
            <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/></svg>
            {{ activeShelf === cat.key ? 'לחצו לסגירה' : 'לחצו לפתיחה' }}
          </span>
        </span>
      </button>
    </div>

    <!-- ── The opened shelf's agreements (companies + rates) ── -->
    <section v-if="!loading && activeCategory" class="shelf-open" :class="`tint-${activeCategory.key}`">
      <div class="shelf-open-head">
        <span class="soh-dot"></span>
        <h3 class="soh-title">{{ activeCategory.label }}</h3>
        <span class="soh-meta"><span class="ltr-number">{{ activeCategory.items.length }}</span> שיעורים · <span class="ltr-number">{{ activeCategory.companies.length }}</span> חברות<template v-if="activeCategory.range"> · <span class="ltr-number">{{ activeCategory.range }}</span></template></span>
      </div>
      <div class="shelf-open-body">
        <table class="rate-table">
          <colgroup><col class="col-product"/><col class="col-rate"/><col class="col-freq"/><col class="col-paidto"/><col class="col-email"/><col class="col-actions"/></colgroup>
          <thead><tr><th>מוצר</th><th class="num">אחוז</th><th>תדירות</th><th>נפרעים</th><th>אימייל</th><th class="actions-col"></th></tr></thead>
          <tbody v-for="(group, gi) in activeCategory.companies" :key="group.company" class="company-binder" :style="{ '--company-color': companyColor(group.company), animationDelay: (gi * 35) + 'ms' }">
            <tr class="company-row">
              <td colspan="6">
                <div class="company-row-inner">
                  <span class="company-tab" aria-hidden="true"></span>
                  <span class="company-row-name">{{ group.company }}</span>
                  <span class="company-row-count"><span class="ltr-number">{{ group.items.length }}</span> {{ group.items.length === 1 ? 'שיעור' : 'שיעורים' }}</span>
                  <span v-if="group.range" class="company-row-range ltr-number">{{ group.range }}</span>
                </div>
              </td>
            </tr>
            <tr v-for="rate in group.items" :key="rate.id">
              <template v-if="editingId === rate.id">
                <td><div class="edit-stack"><input v-model="editForm.company_name" class="edit-input" placeholder="חברה" /><input v-model="editForm.product" class="edit-input" placeholder="כל המוצרים" /></div></td>
                <td class="num"><input v-model.number="editForm.rate" type="number" step="0.01" class="edit-input num-input" dir="ltr" placeholder="%" /></td>
                <td><select v-model="editForm.payment_frequency" class="edit-input"><option value="חודשי">חודשי</option><option value="רבעוני">רבעוני</option><option value="שנתי">שנתי</option></select></td>
                <td><select v-model="editForm.paid_to" class="edit-input"><option value="עיתים">עיתים</option><option value="סוכן">סוכן</option><option value="ידנים">ידנים</option></select></td>
                <td><input v-model="editForm.company_email" class="edit-input email-input" dir="ltr" placeholder="email@company.co.il" /></td>
                <td class="actions">
                  <button class="icon-btn icon-btn--save" @click="saveEdit(rate.id)" title="שמור"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></button>
                  <button class="icon-btn icon-btn--cancel" @click="editingId = null" title="ביטול"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
                </td>
              </template>
              <template v-else>
                <td class="product-cell" :title="rate.product || 'כל המוצרים'"><span class="product-line"><span v-if="rate.product">{{ rate.product }}</span><span v-else class="product-cell--default">כל המוצרים</span><span v-if="rateYearLabel(rate)" class="year-pill ltr-number" :class="rateYearClass(rate)" :title="rateYearTitle(rate)">{{ rateYearLabel(rate) }}</span></span></td>
                <td class="num"><span class="rate-pill ltr-number">{{ (rate.rate * 100).toFixed(2) }}%</span></td>
                <td class="muted-cell">{{ rate.payment_frequency || '—' }}</td>
                <td class="muted-cell">{{ rate.paid_to || '—' }}</td>
                <td class="email-cell"><span class="ltr-number">{{ rate.company_email || '—' }}</span></td>
                <td class="actions">
                  <button class="icon-btn icon-btn--edit" @click="startEdit(rate)" title="ערוך"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
                  <button class="icon-btn icon-btn--del" @click="deleteRate(rate.id)" title="מחק"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg></button>
                </td>
              </template>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <p v-if="rates.length > 0 && search && !visibleCategoryCount" class="empty empty--filter">אין תוצאות עבור "<span class="ltr-number">{{ search }}</span>"</p>

    <section v-if="addingNew" class="add-card">
      <div class="add-card-head">
        <span class="add-card-icon"><svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg></span>
        <span class="add-card-title">שורה חדשה</span><span class="add-card-hint">הקטגוריה תיקבע אוטומטית לפי שם המוצר</span>
      </div>
      <table class="rate-table"><tbody><tr>
        <td><div class="edit-stack"><input v-model="newForm.company_name" class="edit-input" placeholder="שם חברה" /><input v-model="newForm.product" class="edit-input" placeholder="שם מוצר (אופציונלי)" /></div></td>
        <td class="num"><input v-model.number="newForm.rate" type="number" step="0.01" class="edit-input num-input" dir="ltr" placeholder="%" /></td>
        <td><select v-model="newForm.payment_frequency" class="edit-input"><option value="חודשי">חודשי</option><option value="רבעוני">רבעוני</option><option value="שנתי">שנתי</option></select></td>
        <td><select v-model="newForm.paid_to" class="edit-input"><option value="עיתים">עיתים</option><option value="סוכן">סוכן</option><option value="ידנים">ידנים</option></select></td>
        <td><input v-model="newForm.company_email" class="edit-input email-input" dir="ltr" placeholder="email@company.co.il" /></td>
        <td class="actions">
          <button class="icon-btn icon-btn--save" @click="saveNew" title="שמור"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></button>
          <button class="icon-btn icon-btn--cancel" @click="cancelNew" title="ביטול"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
        </td>
      </tr></tbody></table>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive, watch } from 'vue'
import { storeToRefs } from 'pinia'
import api from '../../api/client.js'
import { chartColor } from '../../utils/chartPalette.js'
import { useChatStore } from '../../stores/chat.js'
import TabHeroLoop from '../workspace/TabHeroLoop.vue'

const emit = defineEmits(['rates-changed'])

const rates = ref([])
const loading = ref(false)
const seeding = ref(false)
const search = ref('')
const yearFilter = ref('all')
const editingId = ref(null)
const editForm = reactive({ company_name: '', product: '', rate: 0, payment_frequency: '', paid_to: '', company_email: '' })
const addingNew = ref(false)
const newForm = reactive({ company_name: '', product: '', rate: 0, payment_frequency: 'חודשי', paid_to: 'עיתים', company_email: '' })

// Which shelf (category) is open/active.
const activeShelf = ref(null)

const chat = useChatStore()
const { uploadingDoc, uploadProgress, uploadStage, uploadError } = storeToRefs(chat)
const fileInput = ref(null)

const ART = import.meta.glob('../../assets/commission-shelf/*.webp', { eager: true, import: 'default' })
function artFor(key) { return ART[`../../assets/commission-shelf/${key}.webp`] || null }
const heroArt = computed(() => artFor('hero'))

const ICONS = {
  savings: '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/></svg>',
  risk:    '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><polyline points="9 12 11 14 15 10"/></svg>',
  health:  '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 8L9 4l-3 8H2"/></svg>',
  other:   '<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>',
}
const CATEGORIES = [
  { key: 'savings', label: 'חיסכון ופנסיה', icon: ICONS.savings, keywords: ['גמל', 'השתלמ', 'פנסיה', 'פיננס', 'השקעה', 'חיסכון', 'צבירה', 'קצבה', 'הון', 'אקסלנס', 'מצנח'] },
  { key: 'risk', label: 'חיים וריסק', icon: ICONS.risk, keywords: ['ריסק', 'מנהלים', 'חיים', 'מטריה', 'אובדן', 'אכ"ע', 'אכע', 'נכות', 'תאונה', 'אקסטרה', 'רצף', 'משכנת', 'מוות'] },
  { key: 'health', label: 'בריאות', icon: ICONS.health, keywords: ['בריאות', 'ניתוח', 'השתל', 'תרופ', 'אמבולטור', 'שב"ן', 'שבן', 'סרטן', 'מרפא', 'מחלות', 'פלוס', 'שירותים'] },
  { key: 'other', label: 'אחר', icon: ICONS.other, keywords: [] },
]

function categorize(rate) {
  const text = (rate.product || '').toLowerCase()
  if (text) for (const cat of CATEGORIES) if (cat.keywords.some(k => text.includes(k))) return cat.key
  const pct = (rate.rate || 0) * 100
  return (pct > 0 && pct <= 1) ? 'savings' : 'other'
}
function matchesSearch(rate, q) {
  if (!q) return true
  const n = q.toLowerCase().trim()
  return (rate.company_name || '').toLowerCase().includes(n) || (rate.product || '').toLowerCase().includes(n)
}
function applyFilters(r) { return matchesSearch(r, search.value) && rateInYear(r, yearFilter.value) }

const companyOrder = computed(() => [...new Set(rates.value.map(r => r.company_name || '—'))].sort((a, b) => _normCompany(a).localeCompare(_normCompany(b), 'he')))
const companyColors = computed(() => { const m = new Map(); companyOrder.value.forEach((n, i) => m.set(n, chartColor(i))); return m })
function companyColor(name) { return companyColors.value.get(name) || 'var(--text-muted)' }

const availableYears = computed(() => {
  const yearSet = new Set(); let undated = 0
  for (const r of rates.value) { const s = rateYearSpan(r); if (!s) { undated++; continue } for (let y = s.from; y <= s.to; y++) yearSet.add(y) }
  const nowYear = new Date().getFullYear()
  const chips = [{ key: 'all', label: 'כל השנים', count: rates.value.length, tone: 'all' },
    ...[...yearSet].sort((a, b) => b - a).map(y => ({ key: String(y), label: String(y), count: rates.value.filter(r => rateInYear(r, String(y))).length, tone: y >= nowYear - 1 ? 'current' : (y >= nowYear - 3 ? 'recent' : 'old') }))]
  if (undated) chips.push({ key: 'undated', label: 'ללא תאריך', count: undated, tone: 'old' })
  return chips
})

function _normCompany(name) { return (name || '').trim().replace(/^ה/, '') }
function rateYearSpan(rate) {
  const yf = rate.effective_from ? new Date(rate.effective_from).getFullYear() : null
  const yt = rate.effective_to ? new Date(rate.effective_to).getFullYear() : null
  if (!yf && !yt) return null
  return { from: yf ?? yt, to: yt ?? yf }
}
function rateInYear(rate, year) {
  if (year === 'all') return true
  const s = rateYearSpan(rate)
  if (year === 'undated') return s === null
  const y = parseInt(year, 10)
  return s ? (s.from <= y && y <= s.to) : false
}
function rateYearLabel(rate) {
  const yf = rate.effective_from ? new Date(rate.effective_from).getFullYear() : null
  const yt = rate.effective_to ? new Date(rate.effective_to).getFullYear() : null
  if (!yf && !yt) return null
  return (yf && yt && yf !== yt) ? `${yf}–${yt}` : String(yf || yt)
}
function rateYearTitle(rate) {
  const f = rate.effective_from, t = rate.effective_to
  if (!f && !t) return ''
  return f && t ? `תוקף: ${f} → ${t}` : (f ? `תוקף מ-${f}` : `תוקף עד ${t}`)
}
function rateYearClass(rate) {
  const ref = rate.effective_to || rate.effective_from
  if (!ref) return ''
  const r = new Date(ref).getFullYear(), n = new Date().getFullYear()
  return r >= n - 1 ? 'year-pill--current' : (r >= n - 3 ? 'year-pill--recent' : 'year-pill--old')
}

function _companiesOf(items) {
  const byCompany = new Map()
  for (const r of items) { const k = r.company_name || '—'; if (!byCompany.has(k)) byCompany.set(k, []); byCompany.get(k).push(r) }
  return Array.from(byCompany.entries()).map(([company, list]) => {
    const pcts = list.map(r => +(r.rate * 100).toFixed(2)).filter(x => x > 0)
    const range = pcts.length ? (Math.min(...pcts) === Math.max(...pcts) ? `${pcts[0]}%` : `${Math.min(...pcts)}% – ${Math.max(...pcts)}%`) : ''
    return { company, items: list, range }
  }).sort((a, b) => b.items.length - a.items.length || _normCompany(a.company).localeCompare(_normCompany(b.company), 'he'))
}

const visibleCategories = computed(() => CATEGORIES.map(cat => {
  const items = rates.value.filter(r => categorize(r) === cat.key && applyFilters(r)).sort((a, b) => {
    const cmp = _normCompany(a.company_name).localeCompare(_normCompany(b.company_name), 'he')
    if (cmp !== 0) return cmp
    if (!a.product && b.product) return 1
    if (a.product && !b.product) return -1
    return (a.product || '').localeCompare(b.product || '', 'he')
  })
  const companies = _companiesOf(items)
  const pcts = items.map(r => +(r.rate * 100).toFixed(2)).filter(x => x > 0)
  const range = pcts.length ? (Math.min(...pcts) === Math.max(...pcts) ? `${pcts[0]}%` : `${Math.min(...pcts)}% – ${Math.max(...pcts)}%`) : ''
  return { ...cat, items, companies, range }
}).filter(cat => cat.items.length > 0))
const visibleCategoryCount = computed(() => visibleCategories.value.length)

// All shelves start FOLDED (activeShelf = null). A click opens one book and
// drills into it; clicking it again folds it back.
const activeCategory = computed(() => activeShelf.value ? (visibleCategories.value.find(c => c.key === activeShelf.value) || null) : null)
function toggleShelf(key) { activeShelf.value = activeShelf.value === key ? null : key }

// First shelf (חיסכון ופנסיה) opens by default so the row is filled, not empty.
watch(visibleCategories, (cats) => {
  if (!cats.length) { activeShelf.value = null; return }
  if (!cats.find(c => c.key === activeShelf.value)) activeShelf.value = cats[0].key
}, { immediate: true })

onMounted(() => fetchRates())
async function fetchRates() { loading.value = true; try { const res = await api.get('/commission-rates'); rates.value = res.data } finally { loading.value = false } }

function triggerUpload() { if (!uploadingDoc.value) fileInput.value?.click() }
async function onAgreementFile(e) {
  const file = e.target.files && e.target.files[0]
  if (e.target) e.target.value = ''
  if (!file) return
  const before = new Set(rates.value.map(r => r.id))
  await chat.uploadDocument(file)
  await fetchRates(); emit('rates-changed')
  const fresh = rates.value.filter(r => !before.has(r.id))
  if (fresh.length) activeShelf.value = categorize(fresh[0])
}
async function seedRates() { seeding.value = true; try { await api.post('/commission-rates/seed'); await fetchRates(); emit('rates-changed') } finally { seeding.value = false } }

function startEdit(rate) {
  addingNew.value = false; editingId.value = rate.id
  editForm.company_name = rate.company_name; editForm.product = rate.product || ''
  editForm.rate = +(rate.rate * 100).toFixed(4)
  editForm.payment_frequency = rate.payment_frequency || 'חודשי'; editForm.paid_to = rate.paid_to || 'עיתים'; editForm.company_email = rate.company_email || ''
}
async function saveEdit(id) { await api.put(`/commission-rates/${id}`, { ...editForm, rate: editForm.rate / 100, product: editForm.product || null }); editingId.value = null; await fetchRates(); emit('rates-changed') }
async function deleteRate(id) { await api.delete(`/commission-rates/${id}`); await fetchRates(); emit('rates-changed') }
function startNew() { editingId.value = null; addingNew.value = true; newForm.company_name = ''; newForm.product = ''; newForm.rate = 0; newForm.payment_frequency = 'חודשי'; newForm.paid_to = 'עיתים'; newForm.company_email = '' }
function cancelNew() { addingNew.value = false }
async function saveNew() { if (!newForm.company_name) return; await api.post('/commission-rates', { ...newForm, rate: newForm.rate / 100, product: newForm.product || null }); addingNew.value = false; await fetchRates(); emit('rates-changed') }
</script>

<style scoped>
/* ══ מדף ההסכמים — horizontal picture accordion (your reference), RTL, pastel. ══ */
.rate-shelf { position: relative; }

.shelf-hero { position: relative; overflow: hidden; background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-xl, 24px); padding: 22px 26px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.shelf-hero .hero-copy { position: relative; z-index: 1; max-width: 62%; }
.shelf-art { position: absolute; inset-inline-end: 8px; top: 50%; transform: translateY(-50%); width: min(300px, 34%); aspect-ratio: 420 / 300; pointer-events: none; z-index: 0; }
@media (max-width: 720px) { .shelf-hero .hero-copy { max-width: 100%; } .shelf-art { display: none; } }
.hero-copy { display: flex; flex-direction: column; gap: 7px; }
.hero-eyebrow { display: inline-flex; align-items: center; gap: 7px; align-self: flex-start; font-size: 11px; font-weight: 700; letter-spacing: 0.04em; color: var(--chart-9); background: color-mix(in srgb, var(--chart-2) 12%, white); border: 1px solid color-mix(in srgb, var(--chart-2) 28%, white); padding: 4px 11px; border-radius: 999px; }
.hero-title { margin: 2px 0 0; font-size: 25px; font-weight: 800; letter-spacing: -0.02em; color: var(--text); }
.hero-sub { margin: 0; font-size: 13px; color: var(--text-secondary); line-height: 1.6; }
.hero-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 10px; }
.btn-accent { display: inline-flex; align-items: center; gap: 8px; background: var(--chart-4); color: #fff; border: none; border-radius: 12px; padding: 11px 18px; font-size: 14px; font-family: inherit; font-weight: 700; cursor: pointer; box-shadow: 0 5px 14px color-mix(in srgb, var(--chart-4) 26%, transparent); transition: transform 0.2s var(--transition), background 0.2s var(--transition); }
.btn-accent:hover:not(:disabled) { transform: translateY(-1px); background: color-mix(in srgb, var(--chart-4) 88%, black); }
.btn-accent:disabled { opacity: 0.7; cursor: default; }
.btn-spin { width: 15px; height: 15px; border-radius: 50%; border: 2px solid rgba(255,255,255,0.4); border-top-color: #fff; animation: spin 0.7s linear infinite; }
.btn-ghost { display: inline-flex; align-items: center; gap: 6px; background: var(--bg-surface); color: var(--text-secondary); border: 1px solid var(--border-subtle); border-radius: 12px; padding: 10px 15px; font-size: 13px; font-family: inherit; font-weight: 600; cursor: pointer; transition: all 0.18s var(--transition); }
.btn-ghost:hover:not(:disabled) { border-color: var(--chart-4); color: var(--chart-4); }
.btn-ghost:disabled { opacity: 0.5; cursor: default; }
.hidden-file { display: none; }
.hero-upload { display: flex; align-items: center; gap: 10px; margin-top: 12px; max-width: 420px; }
.hu-bar { flex: 1 1 auto; height: 7px; border-radius: 999px; background: color-mix(in srgb, var(--chart-2) 14%, white); overflow: hidden; }
.hu-fill { height: 100%; border-radius: 999px; background: var(--chart-4); transition: width 0.3s var(--transition); }
.hu-label { font-size: 11.5px; font-weight: 600; color: var(--text-muted); white-space: nowrap; }
.hero-upload-error { margin: 8px 0 0; font-size: 12px; color: var(--red); font-weight: 600; }

.shelf-toolbar { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 14px; }
.rate-search { display: inline-flex; align-items: center; gap: 6px; padding: 8px 12px; border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--bg-surface); color: var(--text-muted); transition: border-color 0.2s, box-shadow 0.2s; }
.rate-search:focus-within { border-color: var(--chart-2); box-shadow: 0 0 0 3px color-mix(in srgb, var(--chart-2) 18%, transparent); color: var(--chart-9); }
.rate-search input { border: none; outline: none; background: transparent; font-family: inherit; font-size: 12.5px; width: 180px; color: var(--text); }
.year-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.year-chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 999px; font-family: inherit; font-size: 12px; font-weight: 600; color: var(--text-secondary); cursor: pointer; transition: all 0.18s var(--transition); }
.year-chip:hover { border-color: var(--chart-2); color: var(--text); }
.year-chip-count { font-size: 10.5px; font-weight: 700; padding: 1px 7px; background: var(--bg); border-radius: 999px; color: var(--text-muted); }
.year-chip--active { background: var(--text); border-color: var(--text); color: #fff; }
.year-chip--active .year-chip-count { background: rgba(255,255,255,0.18); color: #fff; }
.year-chip--active[data-tone="current"] { background: var(--chart-4); border-color: transparent; }

/* Category hue tokens — the app's VIVID "subjects" palette (chart colors). */
.tint-savings { --cat: var(--chart-2);  --cat-deep: var(--chart-9);   --cat-tint: color-mix(in srgb, var(--chart-2) 16%, white); }
.tint-risk    { --cat: var(--chart-4);  --cat-deep: #5A39B8;          --cat-tint: color-mix(in srgb, var(--chart-4) 16%, white); }
.tint-health  { --cat: var(--chart-5);  --cat-deep: var(--chart-10);  --cat-tint: color-mix(in srgb, var(--chart-5) 20%, white); }
.tint-other   { --cat: var(--chart-3);  --cat-deep: #C9791A;          --cat-tint: color-mix(in srgb, var(--chart-3) 20%, white); }

/* ── The picture accordion (your reference: tall panels, widen on hover) ── */
.shelf-rack { display: flex; flex-direction: row; gap: 14px; height: 300px; margin-bottom: 16px; }
.shelf-panel {
  position: relative; flex: 1 1 0; min-width: 132px;    /* closed books: narrow, clearly "closed" */
  border: none; padding: 0; cursor: pointer; border-radius: 18px; overflow: hidden;
  box-shadow: 0 4px 16px rgba(0,0,0,0.10);
  transition: flex 0.6s var(--transition), box-shadow 0.4s var(--transition), transform 0.35s var(--transition);
  outline: none;
}
/* The open book is much wider (~4.5×) so closed books read as closed. */
.shelf-panel--active { flex: 4.5 1 0; box-shadow: 0 18px 44px rgba(0,0,0,0.22); }
/* A closed book lifts on hover to signal it's clickable (opens on click). */
.shelf-panel:not(.shelf-panel--active):hover { transform: translateY(-6px); box-shadow: 0 14px 30px rgba(0,0,0,0.20); }
.shelf-panel:focus-visible { outline: 3px solid color-mix(in srgb, var(--cat) 55%, white); outline-offset: 2px; }

.shelf-media { position: absolute; inset: 0; z-index: 0; background-size: cover; background-position: center; transition: transform 0.6s var(--transition); }
/* Slow ken-burns drift while a shelf is open — feels alive. */
.shelf-panel--active .shelf-media { animation: shelfKen 14s ease-in-out infinite alternate; }
@keyframes shelfKen { from { transform: scale(1.03); } to { transform: scale(1.1) translate(-1.5%, 1%); } }
/* One-time light sheen sweeping across the picture when it opens. */
.shelf-panel::after { content: ''; position: absolute; inset: 0; z-index: 1; pointer-events: none; background: linear-gradient(115deg, transparent 34%, rgba(255,255,255,0.18) 50%, transparent 66%); transform: translateX(-130%); }
.shelf-panel--active::after { animation: shelfSheen 3.4s var(--transition) 0.25s; }
@keyframes shelfSheen { 0% { transform: translateX(-130%); } 55%, 100% { transform: translateX(130%); } }
.shelf-media--fallback { background: radial-gradient(120% 100% at 50% 0%, color-mix(in srgb, var(--cat) 46%, white), transparent 62%), linear-gradient(160deg, color-mix(in srgb, var(--cat) 34%, #2b2f3a), color-mix(in srgb, var(--cat-deep) 30%, #1c2029)); }

/* Constant, LIGHT veil (like the reference's bg-opacity-40) — picture stays visible. */
.shelf-veil { position: absolute; inset: 0; z-index: 0; background: linear-gradient(to top, rgba(12,16,26,0.62) 0%, rgba(12,16,26,0.18) 42%, rgba(12,16,26,0.05) 100%); }

.shelf-caption { position: absolute; z-index: 2; inset-inline: 0; bottom: 0; display: flex; flex-direction: column; align-items: flex-start; gap: 6px; padding: 16px 18px; color: #fff; text-align: start; }
.shelf-badge { display: inline-flex; align-items: center; justify-content: center; width: 36px; height: 36px; border-radius: 11px; background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.3); backdrop-filter: blur(5px); color: #fff; margin-bottom: 2px; }
.shelf-name { font-size: 16px; font-weight: 800; letter-spacing: -0.01em; line-height: 1.2; text-shadow: 0 2px 10px rgba(0,0,0,0.55); }
.shelf-meta { font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.9); white-space: nowrap; opacity: 1; transition: opacity 0.35s var(--transition); text-shadow: 0 1px 6px rgba(0,0,0,0.5); }
/* A CLOSED book keeps its name HORIZONTAL at the bottom (just hides the meta line). */
.shelf-panel:not(.shelf-panel--active) .shelf-meta { display: none; }
/* "click to open / close" hint chip — only on the open book. */
.shelf-hint { display: inline-flex; align-items: center; gap: 5px; margin-top: 4px; padding: 4px 10px; font-size: 11px; font-weight: 700; color: #fff; background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.3); border-radius: 999px; backdrop-filter: blur(4px); white-space: nowrap; }
.shelf-panel:not(.shelf-panel--active) .shelf-hint { display: none; }

/* ── The opened shelf's agreements ── */
.shelf-open { background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); overflow: hidden; }
.shelf-open-head { display: flex; align-items: center; gap: 10px; padding: 13px 18px; background: linear-gradient(95deg, var(--cat-tint) 0%, transparent 62%); border-bottom: 1px solid var(--border-subtle); }
.soh-dot { width: 10px; height: 10px; border-radius: 50%; background: var(--cat); flex: 0 0 auto; }
.soh-title { margin: 0; font-size: 16px; font-weight: 800; color: var(--text); letter-spacing: -0.01em; }
.soh-meta { font-size: 12px; font-weight: 600; color: var(--text-muted); margin-inline-start: auto; }
.shelf-open-body { overflow-x: auto; }

.rate-table { width: 100%; border-collapse: collapse; font-size: 12.5px; }
.rate-table thead { background: var(--glass-hover); }
.rate-table th { padding: 9px 12px; text-align: right; font-weight: 700; color: var(--text-muted); border-bottom: 1px solid var(--border-subtle); font-size: 10px; text-transform: uppercase; letter-spacing: 0.06em; }
.rate-table th.num, .rate-table td.num { text-align: left; }
.rate-table td { padding: 9px 12px; border-bottom: 1px solid var(--border-subtle); color: var(--text); vertical-align: middle; }
.rate-table tbody tr { transition: background 0.15s; }
.rate-table tbody tr:hover { background: var(--glass-hover); }
.rate-table tbody:last-child tr:last-child td { border-bottom: none; }
.col-product { width: auto; } .col-rate { width: 92px; } .col-freq { width: 90px; } .col-paidto { width: 90px; } .col-email { width: 200px; } .col-actions { width: 60px; }

.company-binder { animation: binderIn 0.35s var(--transition) both; }
@keyframes binderIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: none; } }
.company-row td { padding: 9px 12px; background: var(--bg); border-bottom: 1px solid var(--border-subtle); border-inline-start: 3px solid var(--company-color); }
.company-binder + .company-binder .company-row td { border-top: 1px solid var(--border-subtle); }
.company-row-inner { display: flex; align-items: center; gap: 10px; }
.company-tab { width: 10px; height: 10px; border-radius: 3px; background: var(--company-color); flex: 0 0 auto; box-shadow: 0 0 0 3px color-mix(in srgb, var(--company-color) 18%, white); }
.company-row-name { font-size: 13px; font-weight: 800; color: var(--text); }
.company-row-count { font-size: 10.5px; font-weight: 600; color: var(--text-muted); padding: 2px 8px; background: var(--bg-surface); border: 1px solid var(--border-subtle); border-radius: 999px; }
.company-row-range { font-size: 10.5px; font-weight: 700; color: color-mix(in srgb, var(--company-color) 66%, black); padding: 2px 9px; background: color-mix(in srgb, var(--company-color) 13%, white); border-radius: 999px; margin-inline-start: auto; }
.edit-stack { display: flex; flex-direction: column; gap: 4px; }
.product-cell { color: var(--text-secondary); max-width: 380px; }
.product-line { display: inline-flex; align-items: center; gap: 8px; max-width: 100%; }
.product-line > span:first-child { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 0 1 auto; }
.product-cell--default { color: var(--text-muted); font-style: italic; }
.year-pill { flex: 0 0 auto; font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 999px; border: 1px solid transparent; }
.year-pill--current { background: color-mix(in srgb, var(--chart-2) 16%, white); color: var(--chart-9); border-color: color-mix(in srgb, var(--chart-2) 40%, white); }
.year-pill--recent { background: var(--bg); color: var(--text-secondary); border-color: var(--border-subtle); }
.year-pill--old { background: transparent; color: var(--text-muted); border-color: var(--border-subtle); }
.muted-cell { color: var(--text-muted); }
.rate-pill { display: inline-block; min-width: 58px; text-align: center; padding: 3px 10px; background: var(--cat-tint); color: var(--cat-deep); border-radius: 999px; font-weight: 800; }
.email-cell { font-size: 11px; color: var(--text-muted); max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.actions { display: flex; gap: 4px; white-space: nowrap; justify-content: flex-end; }
.actions-col { width: 60px; }
.icon-btn { width: 27px; height: 27px; display: inline-flex; align-items: center; justify-content: center; padding: 0; background: transparent; border: 1px solid transparent; border-radius: 7px; cursor: pointer; color: var(--text-muted); transition: all 0.18s var(--transition); }
.icon-btn--edit:hover  { background: color-mix(in srgb, var(--chart-2) 14%, white); color: var(--chart-9); border-color: color-mix(in srgb, var(--chart-2) 40%, white); }
.icon-btn--del:hover   { background: var(--red-light); color: var(--red); border-color: var(--red); }
.icon-btn--save:hover  { background: var(--green-light); color: var(--green-deep); border-color: var(--green); }
.icon-btn--cancel:hover { background: var(--red-light); color: var(--red); border-color: var(--red); }
.ltr-number { direction: ltr; unicode-bidi: isolate; }
.edit-input { width: 100%; padding: 6px 9px; border: 1px solid var(--border-subtle); border-radius: 7px; font-size: 12px; font-family: 'Heebo', sans-serif; background: var(--bg-surface); color: var(--text); transition: border-color 0.2s, box-shadow 0.2s; }
.edit-input:focus { outline: none; border-color: var(--chart-2); box-shadow: 0 0 0 3px color-mix(in srgb, var(--chart-2) 18%, transparent); }
.num-input { width: 86px; } .email-input { width: 160px; }
.add-card { margin-top: 14px; background: var(--card-bg); border: 1px dashed color-mix(in srgb, var(--chart-4) 40%, var(--border-subtle)); border-radius: var(--radius-lg); overflow: hidden; }
.add-card-head { display: flex; align-items: center; gap: 10px; padding: 12px 16px; background: color-mix(in srgb, var(--chart-4) 7%, white); }
.add-card-icon { display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px; border-radius: 8px; border: 1px dashed var(--chart-4); color: var(--chart-4); }
.add-card-title { font-size: 14px; font-weight: 800; color: var(--text); }
.add-card-hint { font-size: 11px; color: var(--text-muted); }
.empty { text-align: center; color: var(--text-muted); font-size: 13.5px; padding: 30px 16px; line-height: 1.7; }
.empty strong { color: var(--chart-9); }
.empty--filter { padding: 16px; }
.loading { display: flex; justify-content: center; padding: 30px 16px; }
.spinner { width: 26px; height: 26px; border: 3px solid var(--border-subtle); border-top-color: var(--chart-4); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
.fade-enter-active, .fade-leave-active { transition: opacity 0.25s var(--transition); }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 760px) {
  .shelf-rack { height: 360px; }
  .shelf-panel { flex-basis: 60px; min-width: 60px; }
  .col-email, .col-freq, .col-paidto { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .shelf-panel, .shelf-media, .company-binder, .hu-fill { transition: none !important; animation: none !important; }
}
</style>
