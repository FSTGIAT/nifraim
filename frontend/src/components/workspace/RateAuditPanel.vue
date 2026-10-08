<template>
  <div v-if="loading" class="ra-card ra-card--skeleton" aria-busy="true">
    <div class="ra-head"><h3>עמלות בפועל מול ההסכמים</h3></div>
    <p class="ra-sub">טוען נתוני עמלות…</p>
    <div class="ra-skel" v-for="n in 5" :key="n">
      <span class="ra-skel-name"></span>
      <span class="ra-skel-bar"></span>
      <span class="ra-skel-amt"></span>
    </div>
  </div>

  <div v-else-if="companies.length" class="ra-card">
    <div class="ra-head">
      <h3>עמלות בפועל מול ההסכמים</h3>
      <span v-if="period" class="ra-period ltr-number">{{ period }}</span>
    </div>
    <p class="ra-sub">מה שכל חברה שילמה בפועל, מול מה שאמורה הייתה לשלם לפי אחוזי ההסכם.</p>

    <!-- Alerts as cards, not a stack of identical amber bars.
         Three of them carried three different meanings — money owed, money
         over-received, and a note that nothing could be checked — in one
         colour, one weight, and one icon, with the figure buried mid-sentence.
         Severity now drives the colour and the amount leads. -->
    <!-- The per-company alert cards that sat here now live once, in the
         "דורש טיפול" band at the top of the tab (ProductionActions), which
         opens this panel's drills through `openCompanyByName` / `openExplain`.
         Showing them in both places listed every finding twice. -->

    <!-- One list, not a chart plus a separate list underneath. Companies that
         cannot be compared were rendered in a different visual language from
         the ones that could, so the panel read as two unrelated blocks. -->
    <div class="ra-legend">
      <span><i class="ra-key ra-key--paid"></i>שולם בפועל</span>
      <span><i class="ra-key ra-key--agreed"></i>לפי ההסכם</span>
      <span class="ra-legend-hint">בחר חברה לפירוט לפי מוצר</span>
    </div>
    <AuditRows :rows="companies" @pick="(c, el) => { drillOrigin = el; openCompany = c }"
               @explain="(c, el) => openExplain(el, c)" />

    <button class="ra-all" @click="drillOrigin = $event.currentTarget; tableOpen = true">הצג את כל הנתונים</button>

    <DataModal :open="!!openCompany" :origin="drillOrigin"
               :title="openCompany ? openCompany.company + ' — לפי מוצר' : ''"
               :subtitle="openCompany ? `${openCompany.products.length} מוצרים` : ''"
               @close="openCompany = null; openProduct = null">
      <ProductRows v-if="openCompany" :products="openCompany.products"
                   @pick="(p, el) => { productOrigin = el; openProduct = p }" />
    </DataModal>

    <!-- A product card's customers — a drill opened from a drill. -->
    <DataModal :open="!!(openCompany && openProduct)" :origin="productOrigin" :layer="1020"
               :title="openProduct ? openProduct.product : ''"
               :subtitle="openCompany ? openCompany.company : ''"
               :period="period ? 'נפרעים ' + period : ''" accent="var(--tab-production)"
               @close="openProduct = null">
      <ProductCustomers v-if="openCompany && openProduct" :company="openCompany.company"
                        :product="openProduct.product" :category="openProduct.category || null"
                        :period="period || ''" />
    </DataModal>

    <!-- Who cannot be checked, and what would make them checkable. -->
    <!-- Who cannot be checked — grouped by WHY, because each reason has a
         different fix, and each group ends in the one action that fixes it
         (QA 2026-09-30: a paragraph, a list and a grey note said the same
         thing three ways and offered nothing to press). -->
    <DataModal :open="explainOpen" :origin="drillOrigin" title="חברות שאי אפשר להשוות" @close="explainOpen = false">
      <!-- Focused, compact (QA 2026-10-01): opens on the group of what was
           clicked, groups switch by tab, companies are tiles (no empty gap
           between a name and its amount), the action stays pinned below. -->
      <div class="nc">
        <div class="nc-stats">
          <div class="nc-stat">
            <span class="nc-stat-lbl">חברות</span>
            <span class="nc-stat-val ltr-number">{{ notComparable.length }}</span>
          </div>
          <div class="nc-stat">
            <span class="nc-stat-lbl">התקבלו בלי אפשרות לבדוק</span>
            <span class="nc-stat-val ltr-number">{{ money(notComparablePaid) }}</span>
          </div>
        </div>

        <div v-if="ncGroups.length > 1" class="nc-tabs" role="tablist">
          <button v-for="g in ncGroups" :key="g.key" role="tab" class="nc-tab"
                  :class="{ on: ncGroup && ncGroup.key === g.key }" :aria-selected="ncGroup && ncGroup.key === g.key"
                  @click="ncTab = g.key">
            {{ g.title }} <span class="ltr-number">{{ g.rows.length }}</span>
          </button>
        </div>

        <template v-if="ncGroup">
          <p class="nc-lead">
            <span class="nc-icon" :class="'nc-icon--' + ncGroup.key" aria-hidden="true">
              <svg v-if="ncGroup.key === 'report'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
            </span>
            {{ ncGroup.sub }}
          </p>
          <ul class="nc-tiles">
            <li v-for="c in ncGroup.rows" :key="c.company" class="nc-tile"
                :class="{ 'nc-tile--focus': ncFocus === c.company }">
              <span class="nc-t-name">{{ c.company }}</span>
              <template v-if="ncGroup.key === 'report'">
                <span class="nc-t-val"><span class="ltr-number">{{ c.records }}</span> רשומות</span>
                <span class="nc-t-cap">ממתינות לדוח</span>
              </template>
              <template v-else>
                <span v-if="c.paid > 0" class="nc-t-val ltr-number">{{ money(c.paid) }}</span>
                <span v-if="c.paid > 0" class="nc-t-cap">התקבל החודש</span>
                <span v-if="ncGroup.key === 'rate' && (c.unrated_products || []).length" class="nc-t-cap nc-t-prods">
                  חסר שיעור ל: {{ c.unrated_products.slice(0, 3).join(' · ') }}{{ c.unrated_products.length > 3 ? ` +${c.unrated_products.length - 3}` : '' }}
                </span>
              </template>
            </li>
          </ul>
          <div class="nc-foot">
            <button class="nc-action" @click="goFix(ncGroup.target)">
              {{ ncGroup.action }}
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="15 18 9 12 15 6"/></svg>
            </button>
          </div>
        </template>
      </div>
    </DataModal>

    <DataModal :open="tableOpen" :origin="drillOrigin" title="עמלות בפועל מול ההסכמים — כל הנתונים" @close="tableOpen = false">
      <table class="ra-table">
        <thead>
          <tr>
            <th>חברה</th><th>סך שולם</th><th>מתוכו להשוואה</th>
            <th>לפי ההסכם</th><th>הפרש</th><th>אחוז בפועל</th><th>אחוז בהסכם</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in companies" :key="c.company">
            <td>
              {{ c.company }}
              <!-- Order matters: a company whose report never arrived is not a
                   missing-rate problem, and it reaches this row with
                   no_agreement=false, so it would fall into the generic
                   "אין שיעור למוצרים" branch below. -->
              <span v-if="c.no_commission_data" class="ra-tag">לא התקבלו נפרעים</span>
              <span v-else-if="c.no_agreement" class="ra-tag">אין הסכם</span>
              <span v-else-if="!c.comparable" class="ra-tag">אין שיעור למוצרים</span>
              <span v-else-if="c.rows_estimated" class="ra-tag ltr-number">
                {{ c.rows_estimated }} ללא שיעור מדויק
              </span>
              <span v-if="!c.vat_verified && c.paid > 0" class="ra-tag" :title="c.vat_reason">
                מע"מ לא מאומת
              </span>
            </td>
            <td class="ra-num"><span class="ltr-number">{{ money(c.paid) }}</span></td>
            <!-- Same rows on both sides, or the pair invites a wrong read:
                 מור paid ₪18,738 overall but only ₪2,030 sits on rows with a
                 product-level rate, where the real gap is −0.6%. -->
            <td class="ra-num"><span v-if="c.comparable" class="ltr-number">{{ money(c.paid_firm) }}</span><span v-else class="ra-dash">—</span></td>
            <td class="ra-num"><span v-if="c.comparable" class="ltr-number">{{ money(c.expected_firm) }}</span><span v-else class="ra-dash">—</span></td>
            <td class="ra-num">
              <span v-if="c.comparable" class="ltr-number" :class="gapClass(c)">{{ signedMoney(c.gap) }}</span>
              <span v-else class="ra-dash">—</span>
            </td>
            <td class="ra-num"><span class="ltr-number">{{ pct(c.comparable ? c.implied_rate : c.implied_rate_all) }}</span></td>
            <td class="ra-num"><span v-if="c.comparable" class="ltr-number">{{ pct(c.effective_agreed_rate) }}</span><span v-else class="ra-dash">—</span></td>
          </tr>
        </tbody>
      </table>
      <p class="ra-foot">
        <span class="ra-est">≈</span> מסמן מוצר שחלק משורותיו אינן נושאות שיעור עמלה מפורש
        בהסכם. שיעור שנגזר מברירת מחדל או מחציון אינו טענה על חוב, ולכן אינו נכלל בהפרש
        שבראש המסך.
      </p>
    </DataModal>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { cachedGet } from '../../utils/cachedGet'
import DataModal from './DataModal.vue'
import AuditRows from './AuditRows.vue'
import ProductRows from './ProductRows.vue'
import ProductCustomers from './ProductCustomers.vue'
import { money, signedMoney, pct } from '../../utils/chartDefaults'

// A gap is worth naming only past BOTH thresholds — insurers round, and a
// commission can straddle a month boundary. Mirrors the comparison engine.
const GAP_MIN_PCT = 10
const GAP_MIN_SHEKEL = 100

const ESTIMATE_HINT = 'כל השורות במוצר זה מתומחרות בשיעור ברירת מחדל — אין כאן טענה על חוב'

const companies = ref([])
const loading = ref(true)
const mounted = ref(false)
const period = ref(null)
const openCompany = ref(null)
const openProduct = ref(null)
const productOrigin = ref(null)
const tableOpen = ref(false)
const explainOpen = ref(false)
const allAlerts = ref(false)
const ALERTS_OPEN = 3

const shownAlerts = computed(
  () => (allAlerts.value ? alerts.value : alerts.value.slice(0, ALERTS_OPEN)),
)
const hiddenAlerts = computed(() => Math.max(0, alerts.value.length - ALERTS_OPEN))

// `paid > 0` kept the list to companies that at least reported. A company whose
// נפרעים never arrived has paid == 0 by definition — the very case that used to
// be invisible — so it has to be admitted explicitly.
const notComparable = computed(() => companies.value.filter(
  c => !c.comparable && (c.paid > 0 || c.no_commission_data),
))

// Grouped by reason, each with the one action that fixes it. A missing
// report is a failed download, not paperwork, so it points at automation.
const ncGroups = computed(() => {
  const nc = notComparable.value
  const groups = [
    { key: 'agreement', rows: nc.filter(c => !c.no_commission_data && c.no_agreement),
      title: 'אין הסכם עמלות', sub: 'התקבלו עמלות, אבל אין במערכת הסכם לבדוק אותן מולו',
      action: 'להעלאת הסכם — מדף ההסכמים', target: 'commission-rates' },
    { key: 'rate', rows: nc.filter(c => !c.no_commission_data && !c.no_agreement),
      title: 'יש הסכם, חסרים שיעורים', sub: 'ההסכם לא מכסה את המוצרים שעליהם שולם',
      action: 'להשלמת השיעורים — מדף ההסכמים', target: 'commission-rates' },
    { key: 'report', rows: nc.filter(c => c.no_commission_data),
      title: 'לא התקבל דוח נפרעים', sub: 'יש פרודוקציה והסכם, אבל הדוח של החודש לא הגיע',
      action: 'לבדיקת ההורדה האוטומטית', target: 'portal-automation' },
  ]
  return groups.filter(g => g.rows.length)
})
const ncTab = ref(null)
const ncFocus = ref(null)
const groupKeyOf = c => (c.no_commission_data ? 'report' : c.no_agreement ? 'agreement' : 'rate')
// The open group: the one clicked, else the first.
const ncGroup = computed(() => ncGroups.value.find(g => g.key === ncTab.value) || ncGroups.value[0] || null)
const notComparablePaid = computed(() => notComparable.value.reduce((s, c) => s + (c.paid || 0), 0))
const emit = defineEmits(['navigate'])
function goFix(tab) {
  explainOpen.value = false
  emit('navigate', tab)
}

function gapClass(c) {
  if (!c.comparable || c.gap_pct === null) return ''
  if (Math.abs(c.gap_pct) < GAP_MIN_PCT || Math.abs(c.gap) < GAP_MIN_SHEKEL) return ''
  return c.gap < 0 ? 'ra-neg' : 'ra-pos'
}
function deltaClass(diff, expected) {
  // Same thresholds as the headline gap. Colouring by sign alone painted a ₪1
  // rounding difference in alarm red — and a diff of −₪0.004 rendered as a red
  // "₪0". Insurers round, and a commission can straddle a month boundary.
  const base = Math.abs(Number(expected) || 0)
  if (Math.abs(diff) < GAP_MIN_SHEKEL) return ''
  if (base && (Math.abs(diff) / base) * 100 < GAP_MIN_PCT) return ''
  return diff < 0 ? 'ra-neg' : 'ra-pos'
}

const alerts = computed(() => {
  const out = []
  const noAgreement = companies.value.filter(c => c.no_agreement && c.paid > 0)

  for (const c of companies.value) {
    if (c.no_agreement || !c.comparable) continue
    if (Math.abs(c.gap_pct) < GAP_MIN_PCT || Math.abs(c.gap) < GAP_MIN_SHEKEL) continue
    const short = c.gap < 0
    // Name the product driving it — "Phoenix is 33% off" sends the agent
    // through 750 rows; naming the product does not. Products the source file
    // never named are skipped: pointing at "0" points at nothing.
    const worst = (c.products || [])
      .filter(p => p.estimated === 0 && p.expected > 0 && p.product && /\p{L}/u.test(p.product))
      .sort((a, b) => Math.abs(b.paid - b.expected) - Math.abs(a.paid - a.expected))[0]
    out.push({
      key: 'gap-' + c.company,
      // Being paid LESS than the agreement is money owed; being paid more is
      // worth knowing but is not a debt. One amber for both said neither.
      level: short ? 'loss' : 'gain',
      company: c.company,
      amount: signedMoney(c.gap),
      text: `${short ? 'שולם פחות' : 'שולם יותר'} מהצפוי לפי ההסכם · `
        + `${Math.abs(c.gap_pct)}%${worst ? ` · בעיקר ב"${worst.product}"` : ''}`,
      target: c,
    })
  }
  out.sort((a, b) => (a.level === 'loss' ? 0 : 1) - (b.level === 'loss' ? 0 : 1))

  if (noAgreement.length) {
    const total = noAgreement.reduce((sum, c) => sum + c.paid, 0)
    out.push({
      key: 'noagr',
      level: 'info',
      company: noAgreement.length === 1
        ? noAgreement[0].company
        : `${noAgreement.length} חברות`,
      amount: money(total),
      text: `התקבלו עמלות ואין הסכם לבדוק אותן — ${noAgreement.map(c => c.company).join(', ')}`,
      explain: true,
    })
  }

  // A company with production and an agreement whose נפרעים simply never
  // arrived. Worth its own line: the fix is a failed download, not paperwork,
  // and until now this company wasn't on the panel at all.
  const noReport = companies.value.filter(c => c.no_commission_data)
  if (noReport.length) {
    out.push({
      key: 'noreport',
      level: 'loss',
      company: noReport.length === 1
        ? noReport[0].company
        : `${noReport.length} חברות`,
      amount: '',
      text: `לא התקבל דוח נפרעים החודש — ${noReport.map(c => c.company).join(', ')}`,
      explain: true,
    })
  }
  return out
})

// The element that opened the current drill — it grows out of it (DataModal).
const drillOrigin = ref(null)

// The "דורש טיפול" band opens this panel's drills from outside the card.
function openCompanyByName(name, el) {
  const c = companies.value.find(x => x.company === name)
  if (!c) return
  drillOrigin.value = el || null
  if (c.comparable) openCompany.value = c
  else explainOpen.value = true
}
function openExplain(el, company = null) {
  drillOrigin.value = el || null
  ncFocus.value = company?.company || null
  ncTab.value = company ? groupKeyOf(company) : null
  explainOpen.value = true
}
defineExpose({ openCompanyByName, openExplain })

function onAlert(a, e) {
  drillOrigin.value = e?.currentTarget || null
  if (a.explain) { ncTab.value = null; ncFocus.value = null; explainOpen.value = true }
  else if (a.target) openCompany.value = a.target
}

cachedGet('/production/rate-audit')
  .finally(() => {
    loading.value = false
    requestAnimationFrame(() => { mounted.value = true })
  })
  .then((res) => {
    const all = res.data.companies || []
    companies.value = [
      ...all.filter(c => c.comparable),
      ...all.filter(c => !c.comparable),
    ]
    period.value = res.data.period
  })
  .catch(() => { companies.value = [] })
</script>

<style scoped>
.ra-card {
  background: var(--card-bg); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); padding: 20px;
}
.ra-card--skeleton { pointer-events: none; }
.ra-skel {
  display: grid; grid-template-columns: minmax(64px, 110px) 1fr 84px;
  align-items: center; gap: 12px; padding: 11px 8px;
}
.ra-skel span { display: block; height: 10px; border-radius: 5px;
  background: linear-gradient(90deg,
    var(--border-subtle) 25%, rgba(0,0,0,0.045) 37%, var(--border-subtle) 63%);
  background-size: 400% 100%;
  animation: ra-shimmer 1.3s ease-in-out infinite;
}
.ra-skel-name { width: 70%; }
.ra-skel-amt { width: 100%; }
@keyframes ra-shimmer {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}
@media (prefers-reduced-motion: reduce) { .ra-skel span { animation: none; } }

.ra-head { display: flex; align-items: baseline; gap: 10px; }
.ra-head h3 { font-size: 15px; font-weight: 700; color: var(--text); }
.ra-period { font-size: 12px; color: var(--text-muted); }
.ra-sub { font-size: 12px; color: var(--text-muted); margin: 4px 0 14px; }
.ra-hint { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.ra-none { font-size: 13px; color: var(--text-muted); padding: 10px 0; }

.ra-alerts {
  list-style: none; display: grid; gap: 10px; margin-bottom: 18px;
  grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
}
@media (max-width: 720px) { .ra-alerts { grid-template-columns: 1fr; } }

.ra-alert {
  border-radius: var(--radius-md);
  border: 1px solid var(--border-subtle);
  background: var(--card-bg);
  /* The accent edge carries severity before any text is read. */
  border-inline-start: 3px solid var(--ra-accent, var(--text-muted));
  opacity: 0; transform: translateY(5px);
  transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.2, 0, 0.2, 1);
}
.ra-alert--in { opacity: 1; transform: none; }
.ra-alert--loss { --ra-accent: var(--chart-loss); }
.ra-alert--gain { --ra-accent: var(--chart-gain); }
.ra-alert--info { --ra-accent: var(--primary); }

.ra-alert-btn {
  display: grid; grid-template-columns: auto 1fr auto;
  align-items: center; gap: 11px; width: 100%;
  padding: 11px 13px; background: none; border: none;
  font-family: inherit; text-align: right; cursor: pointer;
}
.ra-alert-btn:hover { background: var(--border-subtle); border-radius: var(--radius-md); }
.ra-alert-icon {
  display: flex; align-items: center; justify-content: center;
  width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
  background: color-mix(in srgb, var(--ra-accent) 12%, transparent);
  color: var(--ra-accent);
}
.ra-alert-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ra-alert-top { display: flex; align-items: baseline; gap: 8px; }
.ra-alert-co { font-size: 13px; font-weight: 700; color: var(--text); }
/* The amount leads; it used to sit mid-sentence. */
.ra-alert-amt { font-size: 15px; font-weight: 800; color: var(--ra-accent); margin-right: auto; }
.ra-alert-txt {
  font-size: 11.5px; color: var(--text-muted); line-height: 1.5;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.ra-alert-go { color: var(--text-muted); flex-shrink: 0; }
.ra-alert-btn:hover .ra-alert-go { color: var(--text); }

@media (prefers-reduced-motion: reduce) {
  .ra-alert { opacity: 1; transform: none; transition: none; }
}
.ra-alert-more { display: flex; align-items: center; }
.ra-alert-more button {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 12px; border: 1px dashed var(--border-subtle);
  border-radius: var(--radius-sm); background: none; color: var(--text-muted);
  font-family: inherit; font-size: 12px; font-weight: 600; cursor: pointer;
}
.ra-alert-more button:hover { color: var(--text); border-color: var(--text-muted); }
.ra-alert-more svg { transition: transform 0.2s var(--transition); }
.ra-chev--open { transform: rotate(180deg); }

.ra-excluded { list-style: none; margin-top: 12px; display: flex; flex-direction: column; gap: 2px; }
.ra-excluded li {
  display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 10px;
  padding: 7px 8px; border-top: 1px solid var(--border-subtle);
}
.ra-ex-name { font-size: 13px; color: var(--text); }
.ra-ex-paid { font-size: 13px; font-weight: 600; color: var(--text); }

.ra-all {
  margin-top: 14px; padding: 6px 14px; border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm); background: none; color: var(--text-muted);
  font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.ra-all:hover { color: var(--text); }

.ra-legend {
  display: flex; align-items: center; gap: 16px;
  margin: 2px 0 10px; font-size: 11px; color: var(--text-muted);
}
.ra-legend span { display: flex; align-items: center; gap: 6px; }
.ra-key { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
.ra-key--paid { background: var(--chart-9); }
.ra-key--agreed { background: var(--text-muted); opacity: 0.38; }
.ra-legend-hint { margin-right: auto; }

.ra-explain-lead { font-size: 13px; color: var(--text); line-height: 1.8; margin-bottom: 14px; }
.ra-explain { list-style: none; display: flex; flex-direction: column; }
.ra-explain li {
  display: grid; grid-template-columns: 1fr auto 1.4fr; align-items: center; gap: 12px;
  padding: 10px 4px; border-bottom: 1px solid var(--border-subtle);
}
.ra-explain li:last-child { border-bottom: none; }
.ra-ex-co { font-size: 13px; font-weight: 600; color: var(--text); }
.ra-ex-amt { font-size: 13px; font-weight: 700; color: var(--text); }
.ra-ex-why { font-size: 12px; color: var(--text-muted); line-height: 1.6; }
.ra-ex-prods { color: var(--text); font-weight: 600; }
.ra-explain-foot {
  font-size: 12px; color: var(--text-muted); line-height: 1.8;
  margin-top: 14px; padding: 10px 12px;
  border-radius: var(--radius-sm); background: var(--border-subtle);
}

.ra-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.ra-table th {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--border-subtle);
}
.ra-table td {
  font-size: 13px; color: var(--text); padding: 9px 8px;
  border-bottom: 1px solid var(--border-subtle);
}
.ra-table th:not(:first-child), .ra-table td.ra-num { text-align: center; width: 100px; }
.ra-tag {
  display: inline-block; margin-right: 6px; padding: 1px 7px; border-radius: 10px;
  background: var(--border-subtle); color: var(--text-muted); font-size: 10px; font-weight: 600;
}
.ra-neg { color: var(--chart-loss); font-weight: 700; }
.ra-pos { color: var(--chart-gain); font-weight: 700; }
.ra-dash { color: var(--text-muted); }
.ra-est {
  display: inline-block; margin-right: 5px; width: 16px; height: 16px;
  line-height: 15px; text-align: center; border-radius: 50%;
  background: var(--border-subtle); color: var(--text-muted);
  font-size: 11px; font-weight: 700; cursor: help;
}
.ra-foot { font-size: 11px; color: var(--text-muted); margin-top: 12px; line-height: 1.6; }
/* ── "חברות שאי אפשר להשוות" ── */
.nc { display: flex; flex-direction: column; gap: 16px; }
.nc-stats { display: grid; grid-template-columns: 1fr 1.6fr; border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; }
.nc-stat { display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 14px 18px; }
.nc-stat + .nc-stat { border-inline-start: 1px solid var(--border-subtle); }
.nc-stat-lbl { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.nc-stat-val { font-size: 22px; font-weight: 800; color: var(--text); }
.nc-tabs { display: flex; flex-wrap: wrap; gap: 2px 18px; border-bottom: 1px solid var(--border-subtle); }
.nc-tab {
  position: relative; border: none; background: none; font: inherit; font-size: 13.5px; font-weight: 600;
  color: var(--text-muted); padding: 8px 0 10px; cursor: pointer;
}
.nc-tab .ltr-number { font-weight: 500; margin-inline-start: 3px; }
.nc-tab:hover { color: var(--text); }
.nc-tab.on { color: var(--tab-production); }
.nc-tab.on::after { content: ''; position: absolute; inset-inline: 0; bottom: -1px; height: 2px; border-radius: 2px; background: var(--tab-production); }
.nc-lead { display: flex; align-items: center; gap: 10px; font-size: 13px; color: var(--text-muted); margin: 0; }
.nc-icon { flex: 0 0 28px; height: 28px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; background: var(--bg); color: var(--text); }
.nc-icon--report { background: var(--amber-light); color: var(--amber); }
.nc-tiles { list-style: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(170px, 1fr)); gap: 10px; }
.nc-tile {
  display: flex; flex-direction: column; align-items: flex-start; gap: 3px; padding: 14px 16px;
  border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg);
}
.nc-tile--focus { border-color: var(--tab-production); box-shadow: 0 0 0 3px var(--tab-production-wash); }
.nc-t-name { font-size: 14px; font-weight: 700; color: var(--text); }
.nc-t-val { font-size: 20px; font-weight: 800; color: var(--text); letter-spacing: -0.3px; }
.nc-t-cap { font-size: 11.5px; color: var(--text-muted); }
.nc-t-prods { line-height: 1.5; }
/* The action stays in view at the bottom of the scrolling drill. */
.nc-foot {
  position: sticky; bottom: -16px; margin: 4px -20px -16px; padding: 12px 20px 16px;
  background: linear-gradient(to top, var(--card-bg) 75%, transparent);
  border-radius: 0 0 var(--radius-lg) var(--radius-lg); /* keep the drill's rounded corners */
}
.nc-action {
  align-self: flex-start; display: inline-flex; align-items: center; gap: 6px;
  border: none; border-radius: 10px; padding: 9px 14px; font: inherit; font-size: 13px; font-weight: 700;
  background: var(--tab-production); color: #fff; cursor: pointer;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--tab-production) 25%, transparent);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.nc-action:hover { transform: translateY(-1px); box-shadow: 0 6px 16px color-mix(in srgb, var(--tab-production) 32%, transparent); }
.nc-action:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }
@media (max-width: 640px) { .nc-stats { grid-template-columns: 1fr; } .nc-stat + .nc-stat { border-inline-start: none; border-top: 1px solid var(--border-subtle); } }
@media (prefers-reduced-motion: reduce) { .nc-action { transition: none; } }
</style>
