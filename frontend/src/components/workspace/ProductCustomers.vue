<template>
  <!-- The customers behind ONE product card of "עמלות בפועל מול ההסכמים"
       (QA 2026-10-08: "שאוכל ללחוץ על כל סעיף ולהבין עבור איזה לקוחות אני מקבל
       פחות מהצפוי"). Same rows and arithmetic as the card
       (`/production/rate-audit/customers`), so the customers sum to it. -->
  <div class="pc">
    <p v-if="loading" class="pc-note">טוען לקוחות…</p>
    <p v-else-if="error" class="pc-note">{{ error }}</p>
    <template v-else>
      <div v-if="summary.expected_firm >= 0.5" class="pc-stats">
        <div class="pc-stat pc-stat--lead">
          <span class="pc-lbl">מגיע לפי ההסכם</span>
          <span class="pc-val ltr-number">{{ money(summary.expected_firm) }}</span>
        </div>
        <div class="pc-stat">
          <span class="pc-lbl">התקבל</span>
          <span class="pc-val ltr-number">{{ money(summary.paid_firm) }}</span>
        </div>
        <div v-if="summary.shortfall >= 0.5" class="pc-stat">
          <span class="pc-lbl">חסר</span>
          <span class="pc-val ltr-number is-down">{{ money(summary.shortfall) }}</span>
        </div>
        <div class="pc-stat">
          <span class="pc-lbl">לקוחות</span>
          <span class="pc-val ltr-number">{{ customers.length }}</span>
        </div>
      </div>
      <p v-else class="pc-why">
        לאף לקוח במוצר הזה אין שיעור מפורש בהסכם — לכן הסכום שהתקבל מוצג, אבל אין מול מה לבדוק (נתון חסר).
      </p>

      <!-- Status as text tabs with counts — the drill's filter pattern. -->
      <div v-if="tabs.length > 1" class="pc-tabs" role="tablist" aria-label="סינון לפי מצב">
        <button type="button" role="tab" :aria-selected="!status" :class="{ on: !status }" @click="status = null">
          הכל <span class="ltr-number">{{ customers.length }}</span>
        </button>
        <button v-for="t in tabs" :key="t.key" type="button" role="tab"
                :aria-selected="status === t.key" :class="{ on: status === t.key }" @click="status = t.key">
          {{ STATUS[t.key].tab }} <span class="ltr-number">{{ t.count }}</span>
        </button>
      </div>

      <label v-if="customers.length > 8" class="pc-search">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input v-model.trim="query" type="search" placeholder="חיפוש לפי שם או ת.ז" />
      </label>

      <ul class="pc-list">
        <li v-for="c in shown" :key="c.id_number" class="pc-card">
          <div class="pc-row">
            <span class="pc-who">
              <strong>{{ c.name || 'ללא שם' }}</strong>
              <small class="ltr-number">{{ c.id_number }}</small>
              <small class="pc-status" :class="'pc-status--' + c.status">{{ STATUS[c.status].label }}</small>
            </span>
            <span v-if="c.expected_firm >= 0.5" class="pc-fig pc-fig--lead">
              <small>מגיע</small><span class="ltr-number">{{ money(c.expected_firm) }}</span>
            </span>
            <span v-if="c.paid >= 0.5" class="pc-fig">
              <small>התקבל</small><span class="ltr-number">{{ money(c.paid) }}</span>
            </span>
            <span v-if="c.gap !== null && Math.abs(c.gap) >= 0.5" class="pc-fig">
              <small>הפרש</small>
              <span class="ltr-number" :class="{ 'is-down': c.status === 'underpaid' || c.status === 'unpaid' }">{{ signedMoney(c.gap) }}</span>
            </span>
          </div>
          <div class="pc-meta">
            <span v-if="c.base >= 0.5">
              {{ c.basis === 'accumulation' ? 'צבירה' : 'פרמיה' }} <span class="ltr-number">{{ money(c.base) }}</span>
            </span>
            <span v-if="c.rate && c.status !== 'estimate'">שיעור בהסכם <span class="ltr-number">{{ rateText(c.rate) }}</span></span>
            <span v-if="c.paid_rate">שיעור בפועל <span class="ltr-number">{{ rateText(c.paid_rate) }}</span></span>
            <span v-if="c.policies.length" class="pc-pol">
              פוליסה <span class="ltr-number">{{ c.policies.slice(0, 3).join(', ') }}</span><template v-if="c.policies.length > 3"> +{{ c.policies.length - 3 }}</template>
            </span>
          </div>
        </li>
      </ul>
      <button v-if="filtered.length > shown.length" class="pc-more" type="button" @click="limit += 100">
        הצג עוד <span class="ltr-number">{{ filtered.length - shown.length }}</span>
      </button>

      <!-- The one action: ask the insurer for what is short, pinned below. -->
      <div v-if="claim.length" class="pc-actions">
        <button class="pc-btn pc-btn--primary" type="button" @click="sendMail">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <rect x="2" y="4" width="20" height="16" rx="2" /><path d="M22 7l-10 7L2 7" />
          </svg>
          מייל ל{{ company }} על <span class="ltr-number">{{ claim.length }}</span> לקוחות
        </button>
        <button class="pc-btn" type="button" @click="downloadExcel">Excel</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import * as XLSX from 'xlsx'
import api from '../../api/client.js'
import { openMailCompose } from '../../utils/mailHelper.js'
import { money, signedMoney } from '../../utils/chartDefaults'
import { useAuthStore } from '../../stores/auth'

const props = defineProps({
  company: { type: String, required: true },
  product: { type: String, required: true },
  category: { type: String, default: null },
  period: { type: String, default: '' },
})

const STATUS = {
  unpaid: { label: 'מגיע לפי ההסכם ולא שולם', tab: 'לא שולם' },
  underpaid: { label: 'שולם פחות מההסכם', tab: 'תשלום חסר' },
  missing: { label: 'נתון חסר — אין שיעור בהסכם', tab: 'נתון חסר' },
  estimate: { label: 'אין שיעור מפורש בהסכם — לא נבדק', tab: 'לא נבדק' },
  overpaid: { label: 'שולם יותר מההסכם', tab: 'שולם יותר' },
  ok: { label: 'שולם לפי ההסכם', tab: 'תקין' },
}
const ORDER = Object.keys(STATUS)

const loading = ref(true)
const error = ref('')
const customers = ref([])
const summary = ref({})
const status = ref(null)
const query = ref('')
const limit = ref(100)

async function load() {
  loading.value = true
  error.value = ''
  status.value = null
  query.value = ''
  try {
    const { data } = await api.get('/production/rate-audit/customers', {
      params: { company: props.company, product: props.product, category: props.category || undefined },
    })
    customers.value = data.customers || []
    summary.value = data.summary || {}
    // Open on what needs action: the first problem status present.
    const first = ['unpaid', 'underpaid', 'missing'].find(k => customers.value.some(c => c.status === k))
    if (first && tabs.value.length > 1) status.value = first
  } catch (e) {
    error.value = 'לא הצלחנו לטעון את הלקוחות. נסו שוב.'
  } finally {
    loading.value = false
  }
}
watch(() => [props.company, props.product, props.category], load, { immediate: true })
watch([status, query], () => { limit.value = 100 })

const tabs = computed(() => ORDER
  .map(key => ({ key, count: customers.value.filter(c => c.status === key).length }))
  .filter(t => t.count))
const filtered = computed(() => {
  const q = query.value
  return customers.value.filter(c => (!status.value || c.status === status.value)
    && (!q || (c.name || '').includes(q) || (c.id_number || '').includes(q)))
})
const shown = computed(() => filtered.value.slice(0, limit.value))
// What the insurer is asked for: customers the agreement prices and who got
// less (or nothing). Estimates and נתון חסר are no claim.
const claim = computed(() => customers.value.filter(c => c.status === 'unpaid' || c.status === 'underpaid'))

function rateText(rate) {
  const n = Number(rate) * 100
  return (n < 1 ? n.toFixed(3) : n.toFixed(2)) + '%'
}

let contacts = null
async function companyEmail(name) {
  if (!contacts) {
    try { contacts = (await api.get('/company-contacts')).data || [] } catch { contacts = [] }
  }
  const hit = contacts.find(c => c.company_name && (name.includes(c.company_name) || c.company_name.includes(name)))
  return hit?.email || ''
}

const authStore = useAuthStore()
async function sendMail() {
  const list = claim.value
  const lines = list.map(c => {
    const pol = c.policies.length ? ` | פוליסה/חשבון ${c.policies.join(', ')}` : ''
    // money(0) prints "—"; the insurer must read that nothing arrived.
    const got = c.paid_firm >= 0.5 ? `התקבל ${money(c.paid_firm)}` : 'לא התקבל תשלום'
    return `- ${c.name || ''} ת.ז ${c.id_number}${pol}: לפי ההסכם ${money(c.expected_firm)}, ${got} (חסר ${money(-c.gap)})`
  }).join('\n')
  const total = list.reduce((s, c) => s + (-c.gap || 0), 0)
  const rate = list.find(c => c.rate)?.rate
  const subject = `בקשה להשלמת עמלות נפרעים — ${props.product}${props.period ? ' ' + props.period : ''} (${list.length} לקוחות)`
  const body = `שלום רב,

בבדיקת דוח הנפרעים${props.period ? ' לחודש ' + props.period : ''} מול הסכם העמלות, במוצר ${props.product}${rate ? ` (שיעור בהסכם ${rateText(rate)})` : ''} שולם פחות מהמגיע עבור הלקוחות הבאים — סה"כ חסר ${money(total)}:

${lines}

קובץ אקסל עם הפירוט הורד למחשבי — מצורף.

אודה לבדיקתכם ולהשלמת התשלום.

בברכה,
${authStore.user?.full_name || ''}`
  downloadExcel()
  await openMailCompose({ to: await companyEmail(props.company), subject, body })
}

function downloadExcel() {
  const rows = (claim.value.length ? claim.value : customers.value).map(c => ({
    'שם': c.name || '',
    'ת.ז': c.id_number,
    'פוליסה/חשבון': c.policies.join(', '),
    'מוצר': props.product,
    'מצב': STATUS[c.status].label,
    [c.basis === 'accumulation' ? 'צבירה' : 'פרמיה']: c.base,
    'שיעור בהסכם': c.rate ? rateText(c.rate) : '',
    'מגיע לפי ההסכם': c.expected_firm,
    'התקבל': c.paid,
    'הפרש': c.gap ?? '',
  }))
  const ws = XLSX.utils.json_to_sheet(rows)
  ws['!Dir'] = 'rtl'
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, 'מול ההסכם')
  XLSX.writeFile(wb, `${props.company}_${props.product}_מול_ההסכם.xlsx`.replace(/[\\/:*?"<>|\s]+/g, '_'))
}
</script>

<style scoped>
.pc { display: flex; flex-direction: column; gap: 12px; }
.pc-note, .pc-why { font-size: 13px; color: var(--text-muted); }

.pc-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; }
.pc-stat { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 12px 16px; }
.pc-stat + .pc-stat { border-inline-start: 1px solid var(--border-subtle); }
.pc-lbl { font-size: 12px; color: var(--text-muted); font-weight: 600; }
.pc-val { font-size: 21px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; }
.pc-stat--lead .pc-val { color: var(--tab-production); }
.is-down { color: var(--red); }

.pc-tabs { display: flex; flex-wrap: wrap; gap: 4px 16px; border-bottom: 1px solid var(--border-subtle); }
.pc-tabs button {
  background: none; border: none; font: inherit; font-size: 13px; font-weight: 600; color: var(--text-muted);
  padding: 8px 0; border-bottom: 2px solid transparent; margin-bottom: -1px; cursor: pointer;
}
.pc-tabs button.on { color: var(--tab-production); border-bottom-color: var(--tab-production); }
.pc-tabs .ltr-number { font-weight: 500; opacity: 0.8; }

.pc-search { display: flex; align-items: center; gap: 8px; height: 38px; padding: 0 12px; border: 1px solid var(--border-subtle); border-radius: 10px; color: var(--text-muted); }
.pc-search input { border: none; outline: none; background: transparent; font: inherit; font-size: 13px; flex: 1; color: var(--text); }

.pc-list { list-style: none; display: flex; flex-direction: column; gap: 8px; padding: 0; margin: 0; }
.pc-card { border: 1px solid var(--border-subtle); border-radius: 12px; padding: 12px 14px; display: flex; flex-direction: column; gap: 6px; background: var(--card-bg); }
.pc-row { display: grid; grid-template-columns: minmax(0, 1.6fr) repeat(3, minmax(0, 1fr)); gap: 12px; align-items: center; }
.pc-who { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.pc-who strong { font-size: 14px; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pc-who small { font-size: 12px; color: var(--text-muted); align-self: flex-start; }
.pc-status--unpaid, .pc-status--underpaid { color: var(--red) !important; font-weight: 600; }
.pc-fig { display: flex; flex-direction: column; align-items: flex-start; gap: 2px; font-size: 15px; font-weight: 700; color: var(--text); }
.pc-fig small { font-size: 11px; font-weight: 600; color: var(--text-muted); }
.pc-fig--lead { color: var(--tab-production); }
.pc-meta { display: flex; flex-wrap: wrap; gap: 4px 14px; font-size: 12px; color: var(--text-muted); }

.pc-more { align-self: center; background: none; border: 1px solid var(--border-subtle); border-radius: 10px; padding: 6px 14px; font: inherit; font-size: 12.5px; cursor: pointer; color: var(--text); }

.pc-actions {
  position: sticky; bottom: -1px; display: flex; gap: 8px; padding: 12px 0 4px;
  background: linear-gradient(to top, var(--card-bg) 75%, transparent);
}
.pc-btn {
  display: inline-flex; align-items: center; gap: 6px; height: 40px; padding: 0 16px; border-radius: 10px;
  border: 1px solid var(--border-subtle); background: var(--card-bg); color: var(--text);
  font: inherit; font-size: 13px; font-weight: 600; cursor: pointer; transition: transform 0.15s ease;
}
.pc-btn--primary { background: var(--tab-production); border-color: var(--tab-production); color: #fff; box-shadow: 0 4px 12px rgba(47, 115, 196, 0.25); }
.pc-btn--primary:hover { transform: translateY(-1px); }

@media (max-width: 640px) {
  .pc-row { grid-template-columns: 1fr 1fr; }
  .pc-who { grid-column: 1 / -1; }
}
</style>
