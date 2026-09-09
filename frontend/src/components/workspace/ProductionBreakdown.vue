<template>
  <div v-if="loaded" class="pb-wrap">
    <!-- ── Companies: both bases side by side ────────────────────────────
         Insurers populate only ONE of premium / accumulation, so a single-bar
         chart silently hides half the book. Showing both is what makes
         "how much do I manage at X, and what do my clients pay there"
         answerable at a glance (QA #8). -->
    <div class="chart-card">
      <div class="chart-header">
        <h3>התפלגות לפי חברה</h3>
        <div class="chart-actions">
          <button class="toggle-btn" :class="{ active: coMetric === 'accumulation' }"
                  @click="coMetric = 'accumulation'">צבירה</button>
          <button class="toggle-btn" :class="{ active: coMetric === 'premium' }"
                  @click="coMetric = 'premium'">פרמיה</button>
        </div>
      </div>
      <p class="pb-hint">בחר חברה כדי לראות את החלוקה הפנימית שלה</p>
      <div class="pb-cos">
        <button v-for="(c, i) in companies" :key="c.company" class="pb-co"
                :class="{ 'pb-co--open': openCompany === c.company }"
                @click="toggleCompany(c.company)">
          <span class="pb-co-bar" :style="{ background: color(i) }"></span>
          <span class="pb-co-name">{{ c.company }}</span>
          <span class="pb-co-val ltr-number">{{ money(c[coMetric]) }}</span>
          <span class="pb-co-meta ltr-number">{{ c.clients }} לקוחות · {{ c.count }} מוצרים</span>
          <svg class="pb-chev" :class="{ 'pb-chev--open': openCompany === c.company }"
               width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      </div>

      <!-- Inside one company: its own products, not every company's.
           The old chart opened a flat all-companies table here. -->
      <Transition name="pb-expand">
        <div v-if="openCompanyRow" class="pb-inner">
          <div class="pb-inner-head">
            <span>{{ openCompanyRow.company }} — לפי מוצר</span>
            <span v-if="openCompanyRow.entities.length > 1" class="pb-entities">
              {{ openCompanyRow.entities.join(' · ') }}
            </span>
          </div>
          <div class="pb-split">
            <section v-for="cat in CATS" :key="cat.key" class="pb-cat">
              <h5>{{ cat.label }}</h5>
              <p v-if="!openCompanyRow.products[cat.key].length" class="pb-none">
                אין מוצרי{{ cat.label === 'ביטוח' ? ' ביטוח' : ' חיסכון' }} בחברה זו
              </p>
              <table v-else class="pb-table">
                <thead>
                  <tr><th>מוצר</th><th>{{ cat.metricLabel }}</th><th>לקוחות</th></tr>
                </thead>
                <tbody>
                  <tr v-for="p in openCompanyRow.products[cat.key]" :key="p.product"
                      class="pb-row" @click="drill(cat.key, p.product, openCompanyRow.company)">
                    <td>{{ p.product }}</td>
                    <td class="pb-num"><span class="ltr-number">{{ money(p[cat.metric]) }}</span></td>
                    <td class="pb-num"><span class="ltr-number">{{ p.clients }}</span></td>
                  </tr>
                </tbody>
              </table>
            </section>
          </div>
        </div>
      </Transition>
    </div>

    <!-- ── Products, split ביטוח / פיננסים ───────────────────────────────
         Insurance is measured by the premium clients pay; savings by the
         balance under management. Charting them on one axis compares
         quantities that have nothing to do with each other (QA #9). -->
    <div class="charts-row">
      <div v-for="cat in CATS" :key="cat.key" class="chart-card">
        <div class="chart-header"><h3>{{ cat.title }}</h3></div>
        <p class="pb-hint">בחר מוצר כדי לראות את הלקוחות שמחזיקים בו</p>
        <p v-if="!products[cat.key].length" class="pb-none">אין נתונים</p>
        <table v-else class="pb-table">
          <thead>
            <tr><th>מוצר</th><th>{{ cat.metricLabel }}</th><th>לקוחות</th><th>מוצרים</th></tr>
          </thead>
          <tbody>
            <tr v-for="p in products[cat.key]" :key="p.product" class="pb-row"
                @click="drill(cat.key, p.product, null)">
              <td>{{ p.product }}</td>
              <td class="pb-num"><span class="ltr-number">{{ money(p[cat.metric]) }}</span></td>
              <td class="pb-num"><span class="ltr-number">{{ p.clients }}</span></td>
              <td class="pb-num"><span class="ltr-number">{{ p.count }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Drill: the clients behind whatever was clicked ──────────────── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="drillOpen" class="dd-overlay" @click.self="closeDrill">
          <div class="dd-card">
            <div class="dd-header">
              <h4>{{ drillTitle }}</h4>
              <span class="dd-count ltr-number" v-if="!drillLoading">{{ drillClients.length }} לקוחות</span>
              <button class="dd-close" @click="closeDrill" aria-label="סגור">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                     stroke-width="2.5" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
              </button>
            </div>
            <div class="dd-body">
              <p v-if="drillLoading" class="pb-none">טוען…</p>
              <p v-else-if="!drillClients.length" class="pb-none">אין לקוחות להצגה</p>
              <table v-else class="pb-table">
                <thead>
                  <tr><th>לקוח</th><th>פרמיה</th><th>צבירה</th><th>מוצרים</th></tr>
                </thead>
                <tbody>
                  <template v-for="c in drillClients" :key="c.id_number">
                    <tr class="pb-row" @click="openClient = openClient === c.id_number ? null : c.id_number">
                      <td>{{ c.name || c.id_number }}</td>
                      <td class="pb-num"><span class="ltr-number">{{ money(c.premium) }}</span></td>
                      <td class="pb-num"><span class="ltr-number">{{ money(c.accumulation) }}</span></td>
                      <td class="pb-num"><span class="ltr-number">{{ c.products.length }}</span></td>
                    </tr>
                    <!-- QA #10: one client's full holdings, insurance and
                         savings together, not one or the other. -->
                    <tr v-if="openClient === c.id_number" class="pb-sub">
                      <td colspan="4">
                        <table class="pb-table pb-table--sub">
                          <thead>
                            <tr><th>מוצר</th><th>חברה</th><th>סוג</th><th>פרמיה</th><th>צבירה</th></tr>
                          </thead>
                          <tbody>
                            <tr v-for="(p, i) in c.products" :key="i">
                              <td>{{ p.raw_product || p.product }}</td>
                              <td>{{ p.company }}</td>
                              <td>{{ p.category === 'insurance' ? 'ביטוח' : 'פיננסים' }}</td>
                              <td class="pb-num"><span class="ltr-number">{{ money(p.premium) }}</span></td>
                              <td class="pb-num"><span class="ltr-number">{{ money(p.accumulation) }}</span></td>
                            </tr>
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  </template>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/client'
import { chartColor } from '../../utils/chartPalette'

const CATS = [
  { key: 'insurance', label: 'ביטוח', title: 'ביטוח — לפי מוצר',
    metric: 'premium', metricLabel: 'פרמיה חודשית' },
  { key: 'financial', label: 'פיננסים', title: 'פיננסים — לפי אפיק',
    metric: 'accumulation', metricLabel: 'צבירה' },
]

const loaded = ref(false)
const companies = ref([])
const products = ref({ insurance: [], financial: [] })
const coMetric = ref('accumulation')
const openCompany = ref(null)

const drillOpen = ref(false)
const drillLoading = ref(false)
const drillClients = ref([])
const drillTitle = ref('')
const openClient = ref(null)

const openCompanyRow = computed(
  () => companies.value.find(c => c.company === openCompany.value) || null,
)

const color = i => chartColor(i)

function money(v) {
  const n = Number(v || 0)
  if (!n) return '—'
  return '₪' + Math.round(n).toLocaleString('en-US')
}

function toggleCompany(name) {
  openCompany.value = openCompany.value === name ? null : name
}

async function drill(category, product, company) {
  drillOpen.value = true
  drillLoading.value = true
  openClient.value = null
  drillClients.value = []
  drillTitle.value = company ? `${company} · ${product}` : product
  try {
    const res = await api.get('/production/breakdown/clients', {
      params: { category, product, company: company || undefined },
    })
    drillClients.value = res.data.clients || []
  } catch (e) {
    drillClients.value = []
  } finally {
    drillLoading.value = false
  }
}

function closeDrill() {
  drillOpen.value = false
  openClient.value = null
}

onMounted(async () => {
  try {
    const res = await api.get('/production/breakdown')
    companies.value = res.data.companies || []
    products.value = res.data.products || { insurance: [], financial: [] }
    loaded.value = (companies.value.length > 0)
  } catch (e) {
    loaded.value = false
  }
})
</script>

<style scoped>
.pb-wrap { display: flex; flex-direction: column; gap: 20px; }

.chart-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 20px;
}
.chart-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 4px;
}
.chart-header h3 { font-size: 15px; font-weight: 700; color: var(--text); }
.chart-actions { display: flex; gap: 6px; }
.toggle-btn {
  padding: 4px 12px; border: none; border-radius: var(--radius-sm);
  background: var(--border-subtle); color: var(--text-muted);
  font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.toggle-btn.active { background: var(--primary-light); color: var(--primary); }

.pb-hint { font-size: 12px; color: var(--text-muted); margin-bottom: 12px; }
.pb-none { font-size: 13px; color: var(--text-muted); padding: 12px 0; }

.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 900px) { .charts-row { grid-template-columns: 1fr; } }

/* Companies as rows, not bars: a bar chart can show one number, and the
   point here is that a company has TWO (accumulation and premium) plus a
   client count. */
.pb-cos { display: flex; flex-direction: column; gap: 2px; }
.pb-co {
  display: grid;
  grid-template-columns: 4px 1fr auto auto 14px;
  align-items: center; gap: 12px;
  padding: 10px 8px; border: none; background: none;
  border-radius: var(--radius-sm); cursor: pointer;
  font-family: inherit; text-align: right; width: 100%;
}
.pb-co:hover { background: var(--border-subtle); }
.pb-co--open { background: var(--primary-light); }
.pb-co-bar { width: 4px; height: 24px; border-radius: 2px; }
.pb-co-name { font-size: 14px; font-weight: 600; color: var(--text); }
.pb-co-val { font-size: 14px; font-weight: 700; color: var(--text); }
.pb-co-meta { font-size: 11px; color: var(--text-muted); }
.pb-chev { color: var(--text-muted); transition: transform 0.2s var(--transition); }
.pb-chev--open { transform: rotate(180deg); }

.pb-inner {
  margin-top: 12px; padding-top: 16px;
  border-top: 1px solid var(--border-subtle);
}
.pb-inner-head {
  display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap;
  font-size: 13px; font-weight: 700; color: var(--text); margin-bottom: 12px;
}
.pb-entities { font-size: 11px; font-weight: 500; color: var(--text-muted); }
.pb-split { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 900px) { .pb-split { grid-template-columns: 1fr; } }
.pb-cat h5 { font-size: 13px; font-weight: 700; color: var(--text); margin-bottom: 8px; }

.pb-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.pb-table th {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-align: right; padding: 6px 8px;
  border-bottom: 1px solid var(--border-subtle);
}
.pb-table td {
  font-size: 13px; color: var(--text); padding: 8px;
  border-bottom: 1px solid var(--border-subtle);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.pb-table th:not(:first-child), .pb-table td.pb-num { text-align: center; width: 100px; }
.pb-row { cursor: pointer; }
.pb-row:hover { background: var(--border-subtle); }
.pb-sub > td { padding: 0 0 8px 0; background: var(--border-subtle); }
.pb-table--sub th, .pb-table--sub td { font-size: 12px; }

.pb-expand-enter-active, .pb-expand-leave-active { transition: opacity 0.2s var(--transition); }
.pb-expand-enter-from, .pb-expand-leave-to { opacity: 0; }

.dd-overlay {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 1010; padding: 20px;
}
.dd-card {
  background: var(--card-bg); border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg); width: 100%; max-width: 860px;
  max-height: 82vh; display: flex; flex-direction: column;
}
.dd-header {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 20px; border-bottom: 1px solid var(--border-subtle);
}
.dd-header h4 { font-size: 16px; font-weight: 700; color: var(--text); flex: 1; }
.dd-count { font-size: 12px; color: var(--text-muted); }
.dd-close {
  background: none; border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm); color: var(--text-muted);
  padding: 5px; cursor: pointer; display: flex;
}
.dd-close:hover { color: var(--text); }
.dd-body { overflow-y: auto; padding: 16px 20px; }

.modal-enter-active, .modal-leave-active { transition: opacity 0.2s var(--transition); }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
