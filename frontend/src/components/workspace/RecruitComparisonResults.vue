<template>
  <div class="rr">
    <!-- Head: what this is, and the one way to start over -->
    <div class="rr-head">
      <h3>תוצאות הבדיקה <small>מול {{ sourceLabel }}</small></h3>
      <button class="rr-ghost" type="button" @click="isCommission ? recruitsStore.resetCommissionComparison() : recruitsStore.resetComparison()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 12a9 9 0 11-3-6.7L21 8"/><path d="M21 3v5h-5"/></svg>
        בדיקה חדשה
      </button>
    </div>

    <!-- KPIs: one white panel. Each card opens the drill behind it. -->
    <div class="rr-kpis">
      <button class="rr-kpi rr-kpi--lead" type="button" @click="openList('found', $event)">
        <svg class="rr-ico" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path pathLength="1" d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle pathLength="1" cx="9" cy="7" r="4"/><path pathLength="1" d="M16 11l2 2 4-4"/>
        </svg>
        <span class="rr-kpi-val ltr-number">{{ result.found }}</span>
        <span class="rr-kpi-lbl">נמצאו · <span class="ltr-number">{{ foundPct }}%</span></span>
      </button>
      <button class="rr-kpi" type="button" @click="openList('missing', $event)">
        <svg class="rr-ico" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path pathLength="1" d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle pathLength="1" cx="9" cy="7" r="4"/><path pathLength="1" d="M17 8l5 5M22 8l-5 5"/>
        </svg>
        <span class="rr-kpi-val ltr-number">{{ result.not_found }}</span>
        <span class="rr-kpi-lbl">לא נמצאו · <span class="ltr-number">{{ missingPct }}%</span></span>
      </button>
      <button v-if="result.total_premium_found >= 0.5" class="rr-kpi" type="button" @click="openList('found', $event)">
        <svg class="rr-ico" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path pathLength="1" d="M20 7H5a2 2 0 010-4h13v4"/><path pathLength="1" d="M3 5v14a2 2 0 002 2h15V7"/><path pathLength="1" d="M17 14h.01"/>
        </svg>
        <span class="rr-kpi-val ltr-number">{{ money(result.total_premium_found) }}</span>
        <span class="rr-kpi-lbl">פרמיה שנמצאה<template v-if="result.active_product_rate"> · <span class="ltr-number">{{ Math.round(result.active_product_rate) }}%</span> פעילים</template></span>
      </button>
      <!-- The recruit file's transfer amounts of the recruits NOT found — money that
           was meant to move, not premium (it was labelled "פרמיה חסרה (הערכה)"). -->
      <button v-if="result.estimated_missing_premium >= 0.5" class="rr-kpi" type="button" @click="openList('missing', $event)">
        <svg class="rr-ico" width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path pathLength="1" d="M17 3l4 4-4 4"/><path pathLength="1" d="M21 7H9"/><path pathLength="1" d="M7 21l-4-4 4-4"/><path pathLength="1" d="M3 17h12"/>
        </svg>
        <span class="rr-kpi-val ltr-number">{{ money(result.estimated_missing_premium) }}</span>
        <span class="rr-kpi-lbl">העברות שלא נמצאו</span>
      </button>
    </div>

    <!-- Charts: found in the tab colour, not found in grey. Bars open the drill. -->
    <div v-if="hasCompanyData || hasStatusData" class="rr-charts">
      <div v-if="hasCompanyData" class="rr-chart rr-chart--click">
        <h4>לפי חברה</h4>
        <apexchart v-if="chartReady" type="bar" :options="companyChartOptions" :series="companyChartSeries"
                   :height="Math.max(160, (result.company_breakdown || []).length * 38)" />
      </div>
      <div v-if="hasStatusData" class="rr-chart">
        <h4>סטטוס מוצרים</h4>
        <apexchart v-if="chartReady" type="donut" :options="statusChartOptions" :series="statusChartSeries" height="240" />
      </div>
    </div>
    <div v-if="hasProductData" class="rr-chart rr-chart--click">
      <h4>לפי מוצר</h4>
      <apexchart v-if="chartReady" type="bar" :options="productChartOptions" :series="productChartSeries"
                 :height="Math.max(180, productBreakdown.length * 36)" />
    </div>

    <!-- Every recruit -->
    <div class="rr-list">
      <div class="rr-tabs" role="tablist" aria-label="סינון">
        <button v-for="t in FILTERS" :key="t.id" type="button" role="tab"
                :aria-selected="activeFilter === t.id" :class="{ on: activeFilter === t.id }" @click="activeFilter = t.id">
          {{ t.label }} <span class="ltr-number">{{ t.count() }}</span>
        </button>
      </div>
      <div class="rr-controls">
        <label class="rr-search">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input v-model="nameSearch" type="search" placeholder="שם או ת.ז" />
        </label>
        <select v-model="companyFilter" class="rr-select" aria-label="חברה">
          <option value="">כל החברות</option>
          <option v-for="c in uniqueCompanies" :key="c" :value="c">{{ c }}</option>
        </select>
        <select v-model="productFilter" class="rr-select" aria-label="מוצר">
          <option value="">כל המוצרים</option>
          <option v-for="p in uniqueProducts" :key="p" :value="p">{{ p }}</option>
        </select>
      </div>

      <table class="rr-tbl">
        <thead>
          <tr>
            <th>לקוח</th>
            <th>חברה</th>
            <th>מוצר</th>
            <th class="rr-num">ב{{ sourceLabel }}</th>
            <th class="rr-num">פרמיה</th>
            <th>מה קרה</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in paginatedResults" :key="item.recruit_id" class="rr-row" @click="openDetail(item, $event.currentTarget)">
            <td>
              <span class="rr-who"><strong>{{ fullName(item) }}</strong><small class="ltr-number">{{ item.id_number }}</small></span>
            </td>
            <td>{{ item.company }}</td>
            <td>{{ item.product }}</td>
            <td class="rr-num">
              <span v-if="item.found_in_production" class="rr-pill"><span class="ltr-number">{{ item.production_products.length }}</span> מוצרים</span>
              <span v-else class="rr-pill rr-pill--miss">לא נמצא</span>
            </td>
            <td class="rr-num"><span v-if="item.production_premium >= 0.5" class="ltr-number">{{ money(item.production_premium) }}</span></td>
            <td @click.stop>
              <div v-if="!item.found_in_production" class="status-select-wrap">
                <select class="status-select" :class="customerStatusClass(customerStatuses[item.recruit_id])"
                        :value="customerStatuses[item.recruit_id] || ''" @change="onStatusChange(item.recruit_id, $event)">
                  <option value="">בחרו…</option>
                  <option value="עבר סוכן">עבר סוכן</option>
                  <option value="משך את הכסף">משך את הכסף</option>
                  <option v-if="isCustom(customerStatuses[item.recruit_id])" :value="customerStatuses[item.recruit_id]">{{ customerStatuses[item.recruit_id] }}</option>
                  <option value="__custom__">אחר…</option>
                </select>
                <input v-if="customInputId === item.recruit_id" v-model="customInputVal" class="status-custom-input" placeholder="מה קרה?"
                       @keydown.enter="confirmCustomStatus(item.recruit_id)" @blur="confirmCustomStatus(item.recruit_id)" />
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!filteredResults.length" class="rr-none">אין מגויסים שמתאימים לסינון.</p>

      <div v-if="totalPages > 1" class="rr-pages">
        <button class="rr-pg" :disabled="currentPage === 1" @click="currentPage--" aria-label="הקודם">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
        <template v-for="p in visiblePages" :key="p">
          <span v-if="p === '...'" class="rr-pg-dots">…</span>
          <button v-else class="rr-pg" :class="{ on: p === currentPage }" @click="currentPage = p">{{ p }}</button>
        </template>
        <button class="rr-pg" :disabled="currentPage === totalPages" @click="currentPage++" aria-label="הבא">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
      </div>
    </div>

    <!-- ── Drill: a list of recruits (found / not found / one company / one product) ── -->
    <DataModal :open="list.open" :title="listTitle" :badge="listItems.length" :origin="list.origin"
               accent="var(--tab-recruits-ink)" @close="list.open = false">
      <div class="rd">
        <div class="rd-strip">
          <div v-if="list.kind !== 'missing'" class="rd-cell rd-cell--lead">
            <span class="rd-lbl">נמצאו</span><span class="rd-val ltr-number">{{ listFound.length }}</span>
          </div>
          <div v-if="list.kind !== 'found'" class="rd-cell" :class="{ 'rd-cell--lead': list.kind === 'missing' }">
            <span class="rd-lbl">לא נמצאו</span><span class="rd-val ltr-number">{{ listMissing.length }}</span>
          </div>
          <div v-if="listPremium >= 0.5" class="rd-cell">
            <span class="rd-lbl">פרמיה שנמצאה</span><span class="rd-val ltr-number">{{ money(listPremium) }}</span>
          </div>
          <div v-if="listTransfers >= 0.5" class="rd-cell">
            <span class="rd-lbl">העברות שלא נמצאו</span><span class="rd-val ltr-number">{{ money(listTransfers) }}</span>
          </div>
        </div>

        <div class="rd-controls">
          <label class="rr-search">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <input v-model="list.search" type="search" placeholder="שם או ת.ז" />
          </label>
          <select v-if="list.kind !== 'company' && listCompanies.length > 1" v-model="list.company" class="rr-select" aria-label="חברה">
            <option value="">כל החברות</option>
            <option v-for="c in listCompanies" :key="c" :value="c">{{ c }}</option>
          </select>
          <select v-if="list.kind !== 'product' && listProducts.length > 1" v-model="list.product" class="rr-select" aria-label="מוצר">
            <option value="">כל המוצרים</option>
            <option v-for="p in listProducts" :key="p" :value="p">{{ p }}</option>
          </select>
          <button v-if="list.kind === 'missing' && listFiltered.length" class="rd-link" type="button" @click="toggleMissingSelectAll(listFiltered)">
            {{ listFiltered.every(r => missingSelected.has(r.recruit_id)) ? 'ניקוי סימון' : 'סימון הכל' }}
          </button>
        </div>

        <RecruitCards :items="listShown" :selectable="list.kind === 'missing'" :selected="missingSelected"
                      @pick="openDetail" @toggle="toggleMissingSelect">
          <template #status="{ item }">
            <select class="status-select status-select-sm" :class="customerStatusClass(customerStatuses[item.recruit_id])"
                    :value="customerStatuses[item.recruit_id] || ''" @change="onStatusChange(item.recruit_id, $event)" aria-label="מה קרה">
              <option value="">מה קרה?</option>
              <option value="עבר סוכן">עבר סוכן</option>
              <option value="משך את הכסף">משך את הכסף</option>
              <option v-if="isCustom(customerStatuses[item.recruit_id])" :value="customerStatuses[item.recruit_id]">{{ customerStatuses[item.recruit_id] }}</option>
              <option value="__custom__">אחר…</option>
            </select>
            <input v-if="customInputId === item.recruit_id" v-model="customInputVal" class="status-custom-input status-custom-input-sm"
                   placeholder="מה קרה?" @keydown.enter="confirmCustomStatus(item.recruit_id)" @blur="confirmCustomStatus(item.recruit_id)" />
          </template>
        </RecruitCards>
        <p v-if="!listFiltered.length" class="rr-none">אין מגויסים שמתאימים לסינון.</p>
        <button v-if="listFiltered.length > listShown.length" class="rd-more" type="button" @click="list.limit += 100">
          הצג עוד <span class="ltr-number">{{ listFiltered.length - listShown.length }}</span>
        </button>

        <!-- The drill's actions, pinned at the bottom -->
        <div v-if="list.kind !== 'product' && (list.kind !== 'company' || listMissing.length)" class="rd-actions">
          <template v-if="list.kind === 'missing'">
            <button class="rd-btn rd-btn--primary" type="button" :disabled="!missingSelected.size" @click="sendSelectedMissingMails">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 7L2 7"/></svg>
              מייל לחברות על <span class="ltr-number">{{ missingSelected.size }}</span> מסומנים
            </button>
            <button class="rd-btn" type="button" @click="downloadMissingExcel">Excel</button>
          </template>
          <button v-else-if="list.kind === 'company'" class="rd-btn rd-btn--primary" type="button" @click="sendMissingMail(list.value, listMissing)">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 7L2 7"/></svg>
            מייל ל{{ list.value }} על <span class="ltr-number">{{ listMissing.length }}</span> שלא נמצאו
          </button>
          <button v-else class="rd-btn" type="button" @click="downloadFoundExcel">Excel</button>
        </div>
      </div>
    </DataModal>

    <!-- ── Drill: one recruit ── -->
    <DataModal :open="!!detailItem" :title="detailItem ? fullName(detailItem) : ''"
               :subtitle="detailItem ? 'ת.ז ' + detailItem.id_number : ''"
               :origin="detailOrigin" size="sm" :layer="list.open ? 1020 : null"
               accent="var(--tab-recruits-ink)" @close="closeDetail">
      <div v-if="detailItem" class="rd">
        <div v-if="detailItem.company || detailItem.product || detailItem.amount >= 0.5" class="rd-strip">
          <div v-if="detailItem.company" class="rd-cell"><span class="rd-lbl">חברה</span><span class="rd-val rd-val--sm">{{ detailItem.company }}</span></div>
          <div v-if="detailItem.product" class="rd-cell"><span class="rd-lbl">מוצר</span><span class="rd-val rd-val--sm">{{ detailItem.product }}</span></div>
          <div v-if="detailItem.amount >= 0.5" class="rd-cell"><span class="rd-lbl">העברה</span><span class="rd-val rd-val--sm ltr-number">{{ money(detailItem.amount) }}</span></div>
        </div>

        <template v-if="detailItem.found_in_production">
          <h5 class="rd-sec">ב{{ sourceLabel }} <span class="ltr-number">{{ detailItem.production_products.length }}</span></h5>
          <ul class="rd-prods">
            <li v-for="(p, i) in detailItem.production_products" :key="i">
              <span class="rd-prod-name">{{ p.product || p.product_type }}<small v-if="p.company">{{ shortCompany(p.company) }}</small></span>
              <span v-if="statusLabel(p.status)" class="rd-st" :class="statusClass(p.status)">{{ statusLabel(p.status) }}</span>
              <span class="rd-prod-amt"><span v-if="p.premium >= 0.5" class="ltr-number">{{ money(p.premium) }}</span></span>
            </li>
          </ul>
          <p v-if="detailItem.production_premium >= 0.5" class="rd-total">
            פרמיה חודשית <strong class="ltr-number">{{ money(detailItem.production_premium) }}</strong>
          </p>
        </template>

        <div v-else class="rd-missing">
          <p>לא נמצא ב{{ sourceLabel }}.</p>
          <label class="rd-status">
            <span>מה קרה?</span>
            <select class="status-select" :class="customerStatusClass(customerStatuses[detailItem.recruit_id])"
                    :value="customerStatuses[detailItem.recruit_id] || ''" @change="onStatusChange(detailItem.recruit_id, $event)">
              <option value="">בחרו…</option>
              <option value="עבר סוכן">עבר סוכן</option>
              <option value="משך את הכסף">משך את הכסף</option>
              <option v-if="isCustom(customerStatuses[detailItem.recruit_id])" :value="customerStatuses[detailItem.recruit_id]">{{ customerStatuses[detailItem.recruit_id] }}</option>
              <option value="__custom__">אחר…</option>
            </select>
          </label>
          <input v-if="customInputId === detailItem.recruit_id" v-model="customInputVal" class="status-custom-input" placeholder="מה קרה?"
                 @keydown.enter="confirmCustomStatus(detailItem.recruit_id)" @blur="confirmCustomStatus(detailItem.recruit_id)" />
        </div>
      </div>
    </DataModal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import * as XLSX from 'xlsx'
import { useRecruitsStore } from '../../stores/recruits.js'
import { openMailCompose } from '../../utils/mailHelper.js'
import api from '../../api/client.js'
import DataModal from './DataModal.vue'
import RecruitCards from './RecruitCards.vue'
import { CHART_PALETTE } from '../../utils/chartPalette.js'

// One colour: found in the tab's turquoise, not found in neutral grey.
const C_FOUND = CHART_PALETTE[6]
const C_MISS = '#C9C7C5'

const props = defineProps({
  result: { type: Object, required: true },
  // Which check this view shows. Both views are mounted from the same store, so
  // the store's "last run" mode would relabel (and reset) the wrong one.
  mode: { type: String, default: 'production' },  // 'production' | 'commission'
})

const recruitsStore = useRecruitsStore()
const isCommission = computed(() => props.mode === 'commission')
const sourceLabel = computed(() => isCommission.value ? 'נפרעים' : 'פרודוקציה')
const activeFilter = ref('all')
const currentPage = ref(1)
const pageSize = 20
const chartReady = ref(false)
const detailItem = ref(null)
const detailOrigin = ref(null)
const customerStatuses = ref({})
const customInputId = ref(null)
const customInputVal = ref('')
const customInputRef = ref(null)
const missingSelected = ref(new Set())

function toggleMissingSelect(id) {
  const s = new Set(missingSelected.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  missingSelected.value = s
}
function toggleMissingSelectAll(filtered) {
  const allIds = filtered.map(r => r.recruit_id)
  const allSelected = allIds.every(id => missingSelected.value.has(id))
  const s = new Set(missingSelected.value)
  if (allSelected) {
    allIds.forEach(id => s.delete(id))
  } else {
    allIds.forEach(id => s.add(id))
  }
  missingSelected.value = s
}
const companyFilter = ref('')
const productFilter = ref('')
const nameSearch = ref('')
// The list drill: found / missing / one company / one product. A row opens the
// recruit ABOVE it (layer 1020) — the list stays where it was.
const list = reactive({ open: false, kind: 'found', value: '', origin: null, search: '', company: '', product: '', limit: 100 })

// Chart clicks: the pressed bar, captured at pointerdown in a PLAIN variable —
// a reactive ref re-renders the chart between down and up and eats the click.
let lastPointerEl = null
function capturePointer(e) { lastPointerEl = e.target instanceof Element ? e.target : null }
onMounted(() => document.addEventListener('pointerdown', capturePointer, true))
onBeforeUnmount(() => document.removeEventListener('pointerdown', capturePointer, true))

// Initialize customer statuses from saved data
function initStatuses() {
  const statuses = {}
  for (const r of props.result.results) {
    if (r.customer_status) {
      statuses[r.recruit_id] = r.customer_status
    }
  }
  customerStatuses.value = statuses
}

onMounted(() => {
  nextTick(() => { chartReady.value = true })
  initStatuses()
})

watch(() => props.result, () => { initStatuses() })

const foundPct = computed(() => props.result.total > 0 ? Math.round((props.result.found / props.result.total) * 100) : 0)
const missingPct = computed(() => props.result.total > 0 ? Math.round((props.result.not_found / props.result.total) * 100) : 0)

const notFoundList = computed(() => props.result.results.filter(r => !r.found_in_production))
const foundList = computed(() => props.result.results.filter(r => r.found_in_production))



// ── Insights computeds ──
const avgProductsPerClient = computed(() => {
  if (!props.result.found) return '0'
  const totalProds = props.result.results
    .filter(r => r.found_in_production)
    .reduce((sum, r) => sum + r.production_products.length, 0)
  return (totalProds / props.result.found).toFixed(1)
})

const hasCompanyData = computed(() => (props.result.company_breakdown || []).length > 0)
const hasStatusData = computed(() => {
  const sb = props.result.status_breakdown || {}
  return Object.keys(sb).length > 1  // one slice at 100% says nothing
})
const hasProductData = computed(() => uniqueProducts.value.length > 1)

// Product breakdown data
const productBreakdown = computed(() => {
  const map = {}
  for (const r of props.result.results) {
    const prod = r.product || 'לא ידוע'
    if (!map[prod]) map[prod] = { product: prod, found: 0, not_found: 0, total: 0 }
    map[prod].total++
    if (r.found_in_production) map[prod].found++
    else map[prod].not_found++
  }
  return Object.values(map).sort((a, b) => b.total - a.total)
})



const LIST_TITLES = { found: () => `נמצאו ב${sourceLabel.value}`, missing: () => `לא נמצאו ב${sourceLabel.value}` }
const listTitle = computed(() => (LIST_TITLES[list.kind] ? LIST_TITLES[list.kind]() : list.value))
const listItems = computed(() => {
  const rs = props.result.results
  if (list.kind === 'found') return rs.filter(r => r.found_in_production)
  if (list.kind === 'missing') return rs.filter(r => !r.found_in_production).sort((a, b) => (b.amount || 0) - (a.amount || 0))
  if (list.kind === 'company') return rs.filter(r => (r.company || 'לא ידוע') === list.value)
  if (list.kind === 'product') return rs.filter(r => (r.product || 'לא ידוע') === list.value)
  return []
})
const listCompanies = computed(() => [...new Set(listItems.value.map(r => r.company).filter(Boolean))].sort())
const listProducts = computed(() => [...new Set(listItems.value.map(r => r.product).filter(Boolean))].sort())
const listFiltered = computed(() => {
  let rs = listItems.value
  if (list.company) rs = rs.filter(r => r.company === list.company)
  if (list.product) rs = rs.filter(r => r.product === list.product)
  const q = list.search.trim().toLowerCase()
  if (q) rs = rs.filter(r => fullName(r).toLowerCase().includes(q) || String(r.id_number || '').includes(q))
  return rs
})
const listShown = computed(() => listFiltered.value.slice(0, list.limit))
const listFound = computed(() => listFiltered.value.filter(r => r.found_in_production))
const listMissing = computed(() => listFiltered.value.filter(r => !r.found_in_production))
const listPremium = computed(() => listFound.value.reduce((s, r) => s + (r.production_premium || 0), 0))
const listTransfers = computed(() => listMissing.value.reduce((s, r) => s + (r.amount || 0), 0))

function openList(kind, ev, value = '') {
  const origin = ev instanceof Element ? ev : (ev?.currentTarget || null)
  Object.assign(list, { kind, value, origin, search: '', company: '', product: '', limit: 100, open: true })
}

const FILTERS = [
  { id: 'all', label: 'הכל', count: () => props.result.total },
  { id: 'found', label: 'נמצאו', count: () => props.result.found },
  { id: 'not_found', label: 'לא נמצאו', count: () => props.result.not_found },
]

// Company bar chart
const companyChartSeries = computed(() => {
  const bd = props.result.company_breakdown || []
  return [
    { name: 'נמצאו', data: bd.map(c => c.found) },
    { name: 'לא נמצאו', data: bd.map(c => c.not_found) },
  ]
})

const companyChartOptions = computed(() => ({
  chart: {
    type: 'bar', stacked: true, fontFamily: 'Heebo, sans-serif', toolbar: { show: false },
    events: {
      dataPointSelection: (_e, _chart, config) => {
        const bd = props.result.company_breakdown || []
        const company = bd[config.dataPointIndex]
        if (company) openList('company', lastPointerEl, company.company)
      },
    },
  },
  plotOptions: { bar: { horizontal: true, barHeight: '60%', borderRadius: 4 } },
  colors: [C_FOUND, C_MISS],
  xaxis: {
    categories: (props.result.company_breakdown || []).map(c => c.company),
    labels: { style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px' } },
  },
  yaxis: {
    labels: {
      style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px', cursor: 'pointer' },
    },
  },
  legend: { position: 'top', fontFamily: 'Heebo, sans-serif', fontSize: '11px' },
  dataLabels: { enabled: false },
  grid: { borderColor: 'var(--border-subtle)', strokeDashArray: 3 },
  tooltip: { style: { fontFamily: 'Heebo, sans-serif' } },
  states: { active: { filter: { type: 'darken', value: 0.75 } } },
}))

// Status donut chart
const statusChartSeries = computed(() => {
  const sb = props.result.status_breakdown || {}
  return Object.values(sb)
})

const statusChartOptions = computed(() => {
  const sb = props.result.status_breakdown || {}
  const labels = Object.keys(sb)
  // Active in the tab colour; cancelled is a real state (red); the rest stay grey.
  const colorMap = { 'פעיל': C_FOUND, 'מוקפא': '#8FA3AD', 'מבוטל': '#C23934' }
  const colors = labels.map(l => colorMap[l] || C_MISS)
  return {
    chart: { type: 'donut', fontFamily: 'Heebo, sans-serif' },
    labels,
    colors,
    legend: { position: 'bottom', fontFamily: 'Heebo, sans-serif', fontSize: '11px' },
    dataLabels: {
      enabled: true,
      formatter: (val) => val.toFixed(0) + '%',
      style: { fontFamily: 'Heebo, sans-serif', fontWeight: 700, fontSize: '12px' },
      dropShadow: { enabled: false },
    },
    plotOptions: { pie: { donut: { size: '60%' } } },
    stroke: { width: 2, colors: ['var(--card-bg)'] },
    tooltip: { style: { fontFamily: 'Heebo, sans-serif' }, y: { formatter: (val) => val + ' מוצרים' } },
  }
})

// Product horizontal bar chart (stacked found/not_found)
const productChartSeries = computed(() => [
  { name: 'נמצאו', data: productBreakdown.value.map(p => p.found) },
  { name: 'לא נמצאו', data: productBreakdown.value.map(p => p.not_found) },
])

const productChartOptions = computed(() => ({
  chart: {
    type: 'bar', stacked: true, fontFamily: 'Heebo, sans-serif', toolbar: { show: false },
    events: {
      dataPointSelection: (_e, _chart, config) => {
        const prod = productBreakdown.value[config.dataPointIndex]
        if (prod) openList('product', lastPointerEl, prod.product)
      },
    },
  },
  plotOptions: { bar: { horizontal: true, barHeight: '55%', borderRadius: 4 } },
  colors: [C_FOUND, C_MISS],
  xaxis: {
    categories: productBreakdown.value.map(p => p.product),
    labels: { style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px' } },
  },
  yaxis: { labels: { style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px' }, maxWidth: 180 } },
  legend: { position: 'top', fontFamily: 'Heebo, sans-serif', fontSize: '11px' },
  dataLabels: { enabled: false },
  grid: { borderColor: 'var(--border-subtle)', strokeDashArray: 3 },
  tooltip: { style: { fontFamily: 'Heebo, sans-serif' } },
  states: { active: { filter: { type: 'darken', value: 0.75 } } },
}))

const uniqueCompanies = computed(() => {
  const set = new Set()
  for (const r of props.result.results) {
    if (r.company) set.add(r.company)
  }
  return [...set].sort()
})

const uniqueProducts = computed(() => {
  const set = new Set()
  for (const r of props.result.results) {
    if (r.product) set.add(r.product)
  }
  return [...set].sort()
})

const filteredResults = computed(() => {
  let list = props.result.results
  if (activeFilter.value === 'found') list = list.filter(r => r.found_in_production)
  if (activeFilter.value === 'not_found') list = list.filter(r => !r.found_in_production)
  if (companyFilter.value) list = list.filter(r => r.company === companyFilter.value)
  if (productFilter.value) list = list.filter(r => r.product === productFilter.value)
  const q = nameSearch.value.trim().toLowerCase()
  if (q) {
    list = list.filter(r => {
      const name = `${r.first_name || ''} ${r.last_name || ''}`.toLowerCase()
      const id = String(r.id_number || '').toLowerCase()
      return name.includes(q) || id.includes(q)
    })
  }
  return list
})

const totalPages = computed(() => Math.ceil(filteredResults.value.length / pageSize))

const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  return filteredResults.value.slice(start, start + pageSize)
})

const visiblePages = computed(() => {
  const total = totalPages.value
  const cur = currentPage.value
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages = []
  pages.push(1)
  if (cur > 3) pages.push('...')
  const windowStart = Math.max(2, cur - 1)
  const windowEnd = Math.min(total - 1, Math.max(cur + 1, 4))
  for (let i = windowStart; i <= windowEnd; i++) pages.push(i)
  if (cur < total - 2) pages.push('...')
  pages.push(total)
  return pages
})

watch([activeFilter, companyFilter, productFilter, nameSearch], () => { currentPage.value = 1 })

function openDetail(item, el) {
  detailOrigin.value = el || null
  detailItem.value = item
}

function closeDetail() { detailItem.value = null }


function downloadFoundExcel() {
  const found = listFiltered.value.filter(r => r.found_in_production)
  if (!found.length) return

  const rows = []
  for (const r of found) {
    const name = `${r.first_name || ''} ${r.last_name || ''}`.trim()
    if (r.production_products?.length) {
      for (const p of r.production_products) {
        rows.push({
          'שם': name,
          'ת.ז': r.id_number,
          'חברה': r.company || '',
          'מוצר': p.product || p.product_type || '',
          'חברה (נפרעים)': p.company || '',
          'פרמיה': p.premium || 0,
          'עמלה': p.commission || 0,
        })
      }
    } else {
      rows.push({ 'שם': name, 'ת.ז': r.id_number, 'חברה': r.company || '', 'פרמיה': r.production_premium || 0 })
    }
  }

  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'נמצאו')
  const label = isCommission.value ? 'בנפרעים' : 'בפרודוקציה'
  XLSX.writeFile(wb, `לקוחות_שנמצאו_${label}_${new Date().toLocaleDateString('he-IL')}.xlsx`)
}

function downloadMissingExcel() {
  const missing = props.result.results.filter(r => !r.found_in_production)
  if (!missing.length) return

  const rows = missing.map(m => ({
    'שם': `${m.first_name || ''} ${m.last_name || ''}`.trim(),
    'ת.ז': m.id_number,
    'חברה': m.company || '',
    'מוצר': m.product || '',
    'סכום': m.amount || 0,
    'סטטוס': customerStatuses.value[m.recruit_id] || '',
  }))

  const ws = XLSX.utils.json_to_sheet(rows)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'חסרים')
  XLSX.writeFile(wb, `מגויסים_חסרים_${new Date().toLocaleDateString('he-IL')}.xlsx`)
}

async function sendSelectedMissingMails() {
  const selected = notFoundList.value.filter(r => missingSelected.value.has(r.recruit_id))
  if (!selected.length) return

  // Group by company
  const byCompany = {}
  for (const m of selected) {
    const co = m.company || 'לא ידוע'
    if (!byCompany[co]) byCompany[co] = []
    byCompany[co].push(m)
  }

  // Load contacts once
  let contacts = []
  try {
    const res = await api.get('/company-contacts')
    contacts = res.data || []
  } catch { /* ignore */ }

  const missingContacts = []
  const label = isCommission.value ? 'בנפרעים' : 'בפרודוקציה'
  let sentCount = 0

  for (const [companyName, clients] of Object.entries(byCompany)) {
    const match = contacts.find(c => companyName.includes(c.company_name) || c.company_name.includes(companyName))
    if (!match || !match.email) {
      missingContacts.push(companyName)
      continue
    }

    try {
      const rows = clients.map(m => ({
        'שם': `${m.first_name || ''} ${m.last_name || ''}`.trim(),
        'ת.ז': m.id_number,
        'חברה': m.company || '',
        'מוצר': m.product || '',
        'סכום': m.amount || 0,
      }))
      const ws = XLSX.utils.json_to_sheet(rows)
      const wb = XLSX.utils.book_new()
      XLSX.utils.book_append_sheet(wb, ws, 'חסרים')
      XLSX.writeFile(wb, `חסרים_${companyName}_${new Date().toLocaleDateString('he-IL')}.xlsx`)
    } catch { /* ignore */ }

    const lines = clients.map(m => {
      const name = `${m.first_name || ''} ${m.last_name || ''}`.trim()
      const product = m.product ? ` (${m.product})` : ''
      return `הלקוח ${name} ת.ז ${m.id_number}${product} אינו מופיע אצלי ${label}.\nאשמח להבין מהי הסיבה לכך, ולבדוק האם יש צורך בפעולה כלשהי מצדי.`
    }).join('\n\n')

    const subject = `בקשת בדיקה — לקוחות חסרים ${label} (${clients.length}) — ${companyName}`
    const body = `שלום רב,\n\nמצורף קובץ Excel עם פירוט הלקוחות.\n\n${lines}\n\nבברכה`

    await openMailCompose({ to: match.email, subject, body })
    sentCount++
  }

  if (missingContacts.length) {
    alert(`לא נמצא אימייל עבור: ${missingContacts.join(', ')}.\nיש להוסיף אימייל בלשונית "אימיילים לחברות".\nנשלחו ${sentCount} מיילים לחברות האחרות.`)
  }
}

async function sendMissingMail(companyName, clients) {
  if (!clients?.length) return

  // Look up company email from contacts
  let companyEmail = ''
  try {
    const res = await api.get('/company-contacts')
    const match = res.data.find(c => companyName.includes(c.company_name) || c.company_name.includes(companyName))
    if (match) companyEmail = match.email
  } catch { /* ignore */ }

  if (!companyEmail) {
    alert(`לא נמצא אימייל עבור "${companyName}".\nיש להוסיף אימייל בלשונית "אימיילים לחברות".`)
    return
  }

  // Download Excel with the filtered clients
  try {
    const rows = clients.map(m => ({
      'שם': `${m.first_name || ''} ${m.last_name || ''}`.trim(),
      'ת.ז': m.id_number,
      'חברה': m.company || '',
      'מוצר': m.product || '',
      'סכום': m.amount || 0,
    }))
    const ws = XLSX.utils.json_to_sheet(rows)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'חסרים')
    XLSX.writeFile(wb, `חסרים_${companyName}_${new Date().toLocaleDateString('he-IL')}.xlsx`)
  } catch { /* ignore */ }

  const label = isCommission.value ? 'בנפרעים' : 'בפרודוקציה'
  const lines = clients.map(m => {
    const name = `${m.first_name || ''} ${m.last_name || ''}`.trim()
    const product = m.product ? ` (${m.product})` : ''
    return `הלקוח ${name} ת.ז ${m.id_number}${product} אינו מופיע אצלי ${label}.\nאשמח להבין מהי הסיבה לכך, ולבדוק האם יש צורך בפעולה כלשהי מצדי.`
  }).join('\n\n')

  const subject = `בקשת בדיקה — לקוחות חסרים ${label} (${clients.length}) — ${companyName}`
  const body = `שלום רב,\n\nמצורף קובץ Excel עם פירוט הלקוחות.\n\n${lines}\n\nבברכה`

  await openMailCompose({ to: companyEmail, subject, body })
}

function persistStatus(recruitId, status) {
  api.patch(`/recruits/${recruitId}/status`, { status }).catch(() => {})
}

function onStatusChange(recruitId, event) {
  const val = event.target.value
  if (val === '__custom__') {
    customInputId.value = recruitId
    customInputVal.value = ''
    nextTick(() => {
      const inputs = document.querySelectorAll('.status-custom-input')
      const last = inputs[inputs.length - 1]
      if (last) last.focus()
    })
  } else {
    customerStatuses.value[recruitId] = val
    customInputId.value = null
    persistStatus(recruitId, val)
  }
}

function confirmCustomStatus(recruitId) {
  const status = customInputVal.value.trim() || 'אחר'
  customerStatuses.value[recruitId] = status
  persistStatus(recruitId, status)
  customInputId.value = null
  customInputVal.value = ''
}

function customerStatusClass(status) {
  if (!status) return ''
  if (status === 'עבר סוכן') return 'cs-moved'
  if (status === 'משך את הכסף') return 'cs-withdrew'
  return 'cs-custom'
}

const fullName = (r) => `${r.first_name || ''} ${r.last_name || ''}`.trim()
const money = (v) => '₪' + Math.round(Number(v) || 0).toLocaleString('he-IL')
const isCustom = (s) => !!s && s !== 'עבר סוכן' && s !== 'משך את הכסף'

function fmtNum(val) {
  if (val == null || val === 0) return '0'
  return Number(val).toLocaleString('he-IL', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function shortCompany(name) {
  if (!name) return ''
  const words = name.split(/\s+/)
  return words.length <= 2 ? name : words.slice(0, 2).join(' ')
}

function statusLabel(s) {
  if (!s) return ''
  if (s === 'פעיל' || s.includes('active') || s.includes('פעיל')) return 'פעיל'
  if (s === 'מוקפא' || s.includes('frozen')) return 'מוקפא'
  if (s.includes('מבוטל') || s.includes('cancel')) return 'מבוטל'
  return s
}

function statusClass(s) {
  const label = statusLabel(s)
  if (label === 'פעיל') return 'st-active'
  if (label === 'מוקפא') return 'st-frozen'
  if (label === 'מבוטל') return 'st-cancelled'
  return ''
}

</script>

<style scoped>
.rr { display: flex; flex-direction: column; gap: 12px; }

/* Head */
.rr-head { display: flex; align-items: center; gap: 10px; }
.rr-head h3 { margin: 0; font-size: 17px; font-weight: 800; color: var(--text); display: flex; align-items: baseline; gap: 8px; }
.rr-head h3 small { font-size: 13px; font-weight: 500; color: var(--text-muted); }
.rr-ghost {
  margin-inline-start: auto; display: inline-flex; align-items: center; gap: 6px;
  padding: 8px 14px; border: 1px solid var(--border-subtle); border-radius: 10px;
  background: var(--card-bg); font: inherit; font-size: 13px; font-weight: 600; color: var(--text-secondary); cursor: pointer;
  transition: border-color 0.15s ease, color 0.15s ease, transform 0.15s ease;
}
.rr-ghost:hover { border-color: var(--tab-recruits); color: var(--tab-recruits-ink); transform: translateY(-1px); }

/* KPI panel — one white panel, cards inside */
.rr-kpis {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 8px;
  padding: 10px; background: var(--card-bg); border: 1px solid var(--border-subtle);
  border-radius: 14px; box-shadow: var(--shadow-sm);
}
.rr-kpi {
  display: flex; flex-direction: column; align-items: flex-start; gap: 4px;
  padding: 12px 14px; min-height: 68px; border: 1px solid transparent; border-radius: 12px;
  background: var(--bg); font: inherit; text-align: right; cursor: pointer;
  transition: border-color 0.2s ease, background 0.2s ease, transform 0.2s ease;
}
.rr-kpi:hover { background: var(--tab-recruits-wash); border-color: var(--tab-recruits); transform: translateY(-1px); }
.rr-kpi:focus-visible { outline: 2px solid var(--tab-recruits-ink); outline-offset: 2px; }
.rr-kpi-val { font-size: 22px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; }
.rr-kpi--lead .rr-kpi-val { color: var(--tab-recruits-ink); }
.rr-kpi-lbl { font-size: 12.5px; font-weight: 600; color: var(--text-muted); }

/* Motion line icons: the strokes draw in once, and draw again on hover */
.rr-ico { color: var(--tab-recruits-ink); margin-bottom: 2px; }
.rr-ico > * { stroke-dasharray: 1; stroke-dashoffset: 1; animation: rrDraw 1.1s cubic-bezier(0.65, 0, 0.35, 1) 0.15s forwards; }
.rr-ico > *:nth-child(2) { animation-delay: 0.35s; }
.rr-ico > *:nth-child(3) { animation-delay: 0.55s; }
.rr-ico > *:nth-child(4) { animation-delay: 0.7s; }
.rr-kpi:hover .rr-ico > * { animation-name: rrDraw2; animation-delay: 0s; }
.rr-kpi:hover .rr-ico > *:nth-child(2) { animation-delay: 0.12s; }
.rr-kpi:hover .rr-ico > *:nth-child(3) { animation-delay: 0.24s; }
.rr-kpi:hover .rr-ico > *:nth-child(4) { animation-delay: 0.32s; }
@keyframes rrDraw { to { stroke-dashoffset: 0; } }
@keyframes rrDraw2 { from { stroke-dashoffset: 1; } to { stroke-dashoffset: 0; } }

/* Charts */
.rr-charts { display: grid; grid-template-columns: 1.4fr 1fr; gap: 12px; }
.rr-charts:has(> .rr-chart:only-child) { grid-template-columns: 1fr; }
.rr-chart {
  background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: 14px;
  box-shadow: var(--shadow-sm); padding: 14px 16px 6px; min-width: 0;
}
.rr-chart h4 { margin: 0 0 4px; font-size: 14px; font-weight: 700; color: var(--text); }
.rr-chart--click :deep(.apexcharts-bar-area) { cursor: pointer; }

/* The list */
.rr-list {
  display: flex; flex-direction: column; gap: 10px;
  background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: 14px;
  box-shadow: var(--shadow-sm); padding: 14px 16px;
}
.rr-tabs { display: flex; gap: 18px; border-bottom: 1px solid var(--border-subtle); }
.rr-tabs button {
  position: relative; padding: 8px 2px 10px; border: none; background: none; font: inherit;
  font-size: 14px; font-weight: 600; color: var(--text-muted); cursor: pointer;
}
.rr-tabs button .ltr-number { font-weight: 500; margin-inline-start: 4px; }
.rr-tabs button.on { color: var(--tab-recruits-ink); }
.rr-tabs button::after {
  content: ''; position: absolute; inset-inline: 0; bottom: -1px; height: 2px; border-radius: 2px;
  background: var(--tab-recruits-ink); transform: scaleX(0); transition: transform 0.3s ease;
}
.rr-tabs button.on::after { transform: scaleX(1); }
.rr-controls, .rd-controls { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; }
.rr-search {
  flex: 1 1 200px; display: flex; align-items: center; gap: 8px; padding: 0 12px; height: 38px;
  border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--card-bg); color: var(--text-muted);
}
.rr-search:focus-within { border-color: var(--tab-recruits); }
.rr-search input { flex: 1; min-width: 0; border: none; outline: none; background: none; font: inherit; font-size: 13.5px; color: var(--text); }
.rr-select {
  height: 38px; padding: 0 12px; border: 1px solid var(--border-subtle); border-radius: 10px;
  background: var(--card-bg); font: inherit; font-size: 13.5px; color: var(--text); cursor: pointer; max-width: 220px;
}
.rr-select:focus { outline: none; border-color: var(--tab-recruits); }

.rr-tbl { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.rr-tbl th {
  text-align: right; font-size: 12px; font-weight: 600; color: var(--text-muted);
  padding: 8px 10px; border-bottom: 1px solid var(--border-subtle);
}
.rr-tbl td { padding: 9px 10px; border-bottom: 1px solid var(--border-subtle); color: var(--text-secondary); vertical-align: middle; }
.rr-num { text-align: center !important; }
.rr-row { cursor: pointer; transition: background 0.15s ease; }
.rr-row:hover { background: var(--tab-recruits-wash); }
.rr-who { display: flex; flex-direction: column; }
.rr-who strong { font-size: 14px; font-weight: 700; color: var(--text); }
.rr-who small { font-size: 12px; color: var(--text-muted); align-self: flex-start; }
.rr-pill {
  display: inline-block; font-size: 12px; font-weight: 700; padding: 3px 10px; border-radius: 999px;
  background: var(--tab-recruits-wash); color: var(--tab-recruits-ink); white-space: nowrap;
}
.rr-pill--miss { background: var(--bg); color: var(--text-secondary); }
.rr-none { margin: 6px 0; font-size: 13px; color: var(--text-muted); text-align: center; }

.rr-pages { display: flex; justify-content: center; align-items: center; gap: 4px; padding-top: 4px; }
.rr-pg {
  min-width: 32px; height: 32px; padding: 0 8px; border: 1px solid var(--border-subtle); border-radius: 8px;
  background: var(--card-bg); font: inherit; font-size: 13px; color: var(--text-secondary); cursor: pointer;
  display: inline-flex; align-items: center; justify-content: center;
}
.rr-pg:disabled { opacity: 0.4; cursor: default; }
.rr-pg.on { background: var(--tab-recruits-ink); border-color: var(--tab-recruits-ink); color: #fff; font-weight: 700; }
.rr-pg-dots { color: var(--text-muted); padding: 0 4px; }

/* Status select ("מה קרה") */
.status-select-wrap { display: flex; flex-direction: column; gap: 6px; }
.status-select {
  height: 32px; padding: 0 10px; border: 1px solid var(--border-subtle); border-radius: 8px;
  background: var(--card-bg); font: inherit; font-size: 12.5px; color: var(--text-secondary); cursor: pointer;
}
.status-select:focus { outline: none; border-color: var(--tab-recruits); }
.status-select.cs-moved, .status-select.cs-custom { background: var(--tab-recruits-wash); border-color: transparent; color: var(--tab-recruits-ink); font-weight: 600; }
.status-select.cs-withdrew { background: var(--red-light); border-color: transparent; color: var(--red); font-weight: 600; }
.status-select-sm { height: 30px; font-size: 12px; }
.status-custom-input {
  height: 32px; padding: 0 10px; border: 1px solid var(--tab-recruits); border-radius: 8px;
  background: var(--card-bg); font: inherit; font-size: 12.5px; color: var(--text); outline: none;
}
.status-custom-input-sm { height: 30px; font-size: 12px; margin-top: 6px; width: 100%; }

/* ── Drills ── */
.rd { display: flex; flex-direction: column; gap: 12px; }
.rd-strip { display: grid; grid-auto-flow: column; grid-auto-columns: 1fr; border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; }
.rd-cell { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 12px 16px; min-width: 0; }
.rd-cell + .rd-cell { border-inline-start: 1px solid var(--border-subtle); }
.rd-lbl { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.rd-val { font-size: 21px; font-weight: 800; color: var(--text); letter-spacing: -0.3px; }
.rd-val--sm { font-size: 15px; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 100%; }
.rd-cell--lead .rd-val { color: var(--tab-recruits-ink); }
.rd-link { border: none; background: none; font: inherit; font-size: 13px; font-weight: 600; color: var(--tab-recruits-ink); cursor: pointer; padding: 6px 2px; }
.rd-link:hover { text-decoration: underline; }
.rd-more {
  align-self: center; padding: 8px 16px; border: 1px solid var(--border-subtle); border-radius: 10px;
  background: var(--card-bg); font: inherit; font-size: 13px; color: var(--text-secondary); cursor: pointer;
}
.rd-actions {
  position: sticky; bottom: -1px; display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
  margin: 4px -20px -16px; padding: 12px 20px; background: var(--card-bg);
  border-top: 1px solid var(--border-subtle); border-radius: 0 0 16px 16px;
}
.rd-btn {
  display: inline-flex; align-items: center; gap: 7px; padding: 9px 16px; border-radius: 10px;
  border: 1px solid var(--border-subtle); background: var(--card-bg); font: inherit; font-size: 13.5px; font-weight: 600;
  color: var(--text-secondary); cursor: pointer; transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.rd-btn:hover:not(:disabled) { transform: translateY(-1px); }
.rd-btn:disabled { opacity: 0.5; cursor: default; }
.rd-btn--primary {
  background: var(--tab-recruits-ink); border-color: var(--tab-recruits-ink); color: #fff;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--tab-recruits-ink) 30%, transparent);
}

/* One recruit */
.rd-sec { margin: 4px 0 0; font-size: 13px; font-weight: 700; color: var(--text); display: flex; gap: 6px; align-items: baseline; }
.rd-sec .ltr-number { color: var(--text-muted); font-weight: 500; }
.rd-prods { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.rd-prods li {
  display: grid; grid-template-columns: minmax(0, 1fr) auto 90px; align-items: center; gap: 10px;
  padding: 10px 12px; border: 1px solid var(--border-subtle); border-radius: 12px;
}
.rd-prod-name { display: flex; flex-direction: column; font-size: 13.5px; font-weight: 600; color: var(--text); min-width: 0; }
.rd-prod-name small { font-size: 12px; font-weight: 400; color: var(--text-muted); }
.rd-prod-amt { font-size: 14px; font-weight: 700; color: var(--text); text-align: left; }
.rd-st { font-size: 12px; font-weight: 600; padding: 2px 9px; border-radius: 999px; background: var(--bg); color: var(--text-secondary); }
.rd-st.st-active { background: var(--tab-recruits-wash); color: var(--tab-recruits-ink); }
.rd-st.st-cancelled { background: var(--red-light); color: var(--red); }
.rd-total { margin: 0; display: flex; justify-content: space-between; font-size: 13px; color: var(--text-muted); padding: 0 4px; }
.rd-total strong { font-size: 15px; color: var(--text); }
.rd-missing { display: flex; flex-direction: column; gap: 10px; }
.rd-missing p { margin: 0; font-size: 14px; font-weight: 600; color: var(--text); }
.rd-status { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--text-muted); }
.rd-status .status-select { flex: 1; }

@media (max-width: 900px) {
  .rr-charts { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .rr-tbl th:nth-child(2), .rr-tbl td:nth-child(2), .rr-tbl th:nth-child(3), .rr-tbl td:nth-child(3) { display: none; }
  .rr-list { padding: 12px; }
  .rd-strip { grid-auto-flow: row; }
  .rd-cell + .rd-cell { border-inline-start: none; border-top: 1px solid var(--border-subtle); }
  .rr-select { max-width: none; flex: 1 1 140px; }
}
@media (prefers-reduced-motion: reduce) {
  .rr-ico > * { animation: none !important; stroke-dashoffset: 0; }
  .rr-kpi, .rr-ghost { transition: none; }
}
</style>
