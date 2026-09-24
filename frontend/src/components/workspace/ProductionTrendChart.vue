<template>
  <div class="trend-card">
    <div class="trend-header">
      <div class="trend-title">
        <span class="trend-icon" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        </span>
        <h3>{{ chartTitle }}</h3>
        <span
          v-if="hasTrend"
          class="trend-badge"
          :class="{
            'trend-badge--up': momPct > 0,
            'trend-badge--down': momPct < 0,
            'trend-badge--flat': momPct === 0,
          }"
        >
          <svg v-if="momPct > 0" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"/></svg>
          <svg v-else-if="momPct < 0" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
          <svg v-else width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/></svg>
          <span class="ltr-number">{{ formatPct(momPct) }}</span>
          <span class="trend-badge-sub">לעומת {{ previousLabel }}</span>
        </span>
      </div>
      <div v-if="hasData" class="trend-current">
        <span class="trend-current-label">צפוי {{ latestLabel }}</span>
        <span class="trend-current-value ltr-number">{{ formatCurrency(latestValue) }}</span>
      </div>
      <!-- Actual received — deliberately its own figure. It used to be folded
           into the expected bar for companies with no priceable base, which
           made the headline a mix of money owed and money already paid. -->
      <div v-if="hasData && receivedTotal > 0" class="trend-current trend-current--actual">
        <span class="trend-current-label">התקבל בפועל</span>
        <span class="trend-current-value ltr-number">{{ formatCurrency(receivedTotal) }}</span>
      </div>
      <!-- Which measure the bars show. Expected is computable only where an
           agreement and a priceable base exist, so it covers a fraction of the
           book; actual covers every company that paid. -->
      <div v-if="hasData" class="trend-modes">
        <button class="trend-mode" :class="{ active: mode === 'expected' }"
                @click="mode = 'expected'">צפוי לפי הסכמים</button>
        <button class="trend-mode" :class="{ active: mode === 'actual' }"
                :disabled="!actualPoints.length"
                @click="mode = 'actual'">התקבל בפועל</button>
      </div>
    </div>

    <!-- The expected view covers only companies with an agreement and a
         priceable base. Saying how many, next to the bars, is what stops a
         partial chart reading as a broken one. -->
    <p v-if="hasData && mode === 'expected' && actualCompanyCount > expectedCompanyCount"
       class="trend-coverage">
      <span class="ltr-number">{{ expectedCompanyCount }}</span> מתוך
      <span class="ltr-number">{{ actualCompanyCount }}</span> חברות —
      צפי מחושב רק לחברות שיש להן הסכם ובסיס לחישוב.
      <button class="trend-coverage-btn" @click="mode = 'actual'">
        הצג את מה שהתקבל בפועל מכולן
      </button>
    </p>

    <!-- The intersection is narrower than either side. Naming what IS compared
         first, then what fell out and why, is what keeps a short pair from
         reading as "the insurers underpaid by 80%" — or, as live, as a single
         company that looks like it overpaid by 290%. -->
    <!-- The two bars are NOT the same set of companies, and nothing else on
         the chart says so. Without this line the shorter grey bar reads as
         "the insurers paid us more than we are owed" — the exact opposite of
         what it means. -->
    <div v-if="mode === 'actual' && hasExpectedBar" class="trend-compare-note">
      <p class="tcn-lead">
        עמודת <strong>צפוי לפי ההסכמים</strong> מחושבת ל-<strong>{{ compareCompanies.join(', ') }}</strong>
        — רק חברות שיש להן שיעור מפורש בהסכם. היא נמוכה מהעמודה הצבעונית מפני
        שהיא מכסה פחות חברות, לא מפני ששולם יותר מדי.
      </p>
      <p v-if="compareCoverage" class="tcn-line">
        מתוך <span class="ltr-number">{{ formatCurrency(compareCoverage.total) }}</span>
        שהתקבלו בחודש, <span class="ltr-number">{{ formatCurrency(compareCoverage.checked) }}</span>
        (<span class="ltr-number">{{ compareCoverage.pct }}%</span>) ניתנים להשוואה מול הסכם.
        רחף מעל העמודה לפער לפי חברה.
      </p>
      <ul v-if="compareDropped.length" class="tcn-list">
        <li v-for="d in compareDroppedShown" :key="d.company">
          <span class="tcn-co">{{ d.company }}</span>
          <span class="tcn-why">{{ COMPARE_DROP_REASONS[d.why] }}</span>
        </li>
        <li v-if="compareDroppedMore" class="tcn-more">
          ועוד <span class="ltr-number">{{ compareDroppedMore }}</span>
        </li>
      </ul>
    </div>

    <!-- Insight card: biggest drop + CTA to automation -->
    <div v-if="insight && mode === 'expected'" class="trend-insight" :class="`trend-insight--${insight.severity}`">
      <div class="trend-insight-body">
        <div class="trend-insight-icon" aria-hidden="true">
          <svg v-if="insight.severity === 'warn'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/>
            <line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="16" x2="12" y2="12"/>
            <line x1="12" y1="8" x2="12.01" y2="8"/>
          </svg>
        </div>
        <div class="trend-insight-text">
          <div class="trend-insight-title">{{ insight.title }}</div>
          <div class="trend-insight-detail">{{ insight.detail }}</div>
          <ul v-if="insight.contributors?.length" class="trend-insight-list">
            <li v-for="c in insight.contributors" :key="c.company">
              <span class="trend-insight-list-name">{{ c.company }}</span>
              <span class="trend-insight-list-delta ltr-number">{{ formatSignedCurrency(c.delta) }}</span>
            </li>
          </ul>
        </div>
      </div>
      <button
        v-if="insight.severity === 'warn'"
        class="trend-insight-cta"
        @click="$emit('go-to-automation')"
      >
        הפעל אוטומציה לעדכון
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="15 18 9 12 15 6"/>
        </svg>
      </button>
    </div>

    <template v-if="hasData">
      <ul v-if="legendItems.length" class="trend-legend">
        <li v-for="it in legendItems" :key="it.name"
            :class="{ 'trend-legend--bench': it.benchmark }">
          <i class="tl-dot" :style="{ background: it.color }"></i>{{ it.name }}
        </li>
      </ul>
      <div class="trend-chart-wrap">
        <apexchart
          type="bar"
          height="320"
          width="100%"
          :options="chartOptions"
          :series="series"
        />
      </div>
      <p v-if="isSingleMonth && mode !== 'compare'" class="trend-single-caption">
        חודש ראשון נקלט — המגמה תצטייר אוטומטית עם ההורדה הבאה
      </p>
      <!-- Why companies are missing from the bar. Without this, an agent
           seeing 2 of 7 companies can't tell "no agreement rate for these"
           from "the app lost my data". -->
      <p v-if="uncovered.length && mode !== 'compare'" class="trend-uncovered">
        <span class="tu-lead">לא נכללות בחישוב:</span>
        <span v-for="u in uncovered" :key="u.company" class="tu-item">
          {{ u.company }}
          <span class="tu-why">{{ uncoveredReason(u) }}</span>
        </span>
      </p>
    </template>

    <div v-else-if="loading" class="trend-empty">
      <div class="trend-empty-spinner" aria-hidden="true"></div>
      <p class="trend-empty-sub">טוען נתוני עמלות…</p>
    </div>

    <div v-else class="trend-empty">
      <span class="trend-empty-icon" aria-hidden="true">
        <svg v-if="emptyState.icon === 'production'" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        <svg v-else-if="emptyState.icon === 'rates'" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="5" x2="5" y2="19"/>
          <circle cx="6.5" cy="6.5" r="2.5"/>
          <circle cx="17.5" cy="17.5" r="2.5"/>
        </svg>
        <svg v-else width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
      </span>
      <p class="trend-empty-title">{{ emptyState.title }}</p>
      <p class="trend-empty-sub">{{ emptyState.sub }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import api from '../../api/client.js'
import { useProductionStore } from '../../stores/production.js'
import { CHART_PALETTE, assignCompanyColors, VALIDATED_SLOTS } from '../../utils/chartPalette.js'
import { brandForLabel } from '../../utils/companyBrand.js'

defineEmits(['go-to-automation'])

const productionStore = useProductionStore()
const points = ref([])
const reason = ref(null)
const loading = ref(true)
// ACTUAL commission received (from /comparison/company-summary). Held apart
// from `points` so it can never be summed into the expected figure.
const receivedTotal = ref(0)
const receivedCompanies = ref({})

// Two different questions, so two views rather than two y-scales on one chart.
//   'expected' — what the agreements say is owed, per production month.
//   'actual'   — what actually arrived, per נפרעים month.
// Expected can only be computed where an agreement AND a priceable base exist
// (live: 2 companies of 9), so a chart locked to it looks like most of the
// book is missing. Actual covers every company that paid.
// ACTUAL is the default view.
//
// Expected commission can only be computed where an agreement AND a priceable
// base both exist — live that is 2 companies of 10, so opening on it showed a
// two-bar chart for a ten-company book and read as broken. Twice reported as
// "where are all the companies". Money actually received covers everyone who
// paid, which is what "my commissions this month" means to an agent; the
// expected view is one press away and now states its own coverage.
const mode = ref('actual')
const actualPoints = ref([])

// Companies in the LATEST month's production that contribute no expected
// commission, with the reason the backend gives.
const uncovered = computed(() => {
  const last = points.value[points.value.length - 1]
  return (last?.uncovered || []).slice(0, 6)
})

// Why a company contributes nothing. The backend counts four DISTINCT causes
// and this reports the dominant one; each implies a different fix, which is
// the whole point of splitting them (QA 2026-09-09, item 7):
//
//   no_company      → the agent has no agreement for this insurer at all
//   no_rate         → agreement exists, but nothing covers this product
//   risk_no_premium → the rows carry צבירה, but a risk product is priced off
//                     PREMIUM and the file has none. The old wording said
//                     "אין צבירה או פרמיה בקובץ" about Phoenix rows holding
//                     ₪51.2M of צבירה — false, and it sent the agent hunting
//                     for missing data that was right there.
//   no_base         → genuinely no premium and no accumulation in the file
const UNCOVERED_REASONS = {
  no_company: 'אין הסכם לחברה הזו',
  no_rate: 'יש הסכם, אך אין שיעור עמלה למוצר הזה',
  risk_no_premium: 'מוצר ביטוחי ללא פרמיה בקובץ (הצבירה אינה בסיס לעמלה)',
  no_base: 'אין פרמיה או צבירה בקובץ',
}
const UNCOVERED_ORDER = ['no_company', 'no_rate', 'risk_no_premium', 'no_base']

function uncoveredReason(u) {
  let best = null
  for (const k of UNCOVERED_ORDER) {
    if ((u[k] || 0) > (best ? u[best] : 0)) best = k
  }
  return UNCOVERED_REASONS[best] || 'לא נכלל בחישוב'
}

// Collapse a { rawCompanyName: value } map so a company's legal-entity variants
// (e.g. "הפניקס חברה לביטוח בע\"מ" + "הפניקס אקסלנס פנסיה וגמל בע\"מ") merge into
// ONE branded label — otherwise the two sub-top-5 keys each fall into "אחרות".
// Unknown companies keep their raw name (brandForLabel falls back to label '?').
function collapseByCompany(byCompany) {
  const out = {}
  for (const [name, val] of Object.entries(byCompany || {})) {
    const v = Number(val) || 0
    if (v === 0) continue
    const brand = brandForLabel(name)
    const label = brand && brand.label && brand.label !== '?' ? brand.label : name
    out[label] = (out[label] || 0) + v
  }
  return out
}

// EXPECTED only. This used to top the latest period up with ACTUAL received
// for companies whose production carries no priceable base (Phoenix life:
// premium=0 & accumulation=0), so they'd appear at all — but that silently
// added a different quantity into a chart titled "עמלות צפויות". Live, the
// ₪132,146 headline was mostly נפרעים actuals: הכשרה ₪45,509, מור ₪19,373 and
// הפניקס ₪31,458 were the amounts PAID, not amounts owed. Conflating Actual
// with Expected is the one thing commission_calculation_model.md forbids.
//
// Actual now rides alongside as its OWN series (see `receivedPoint`), so a
// company with no priceable base is still visible — as what it really is.
function mergeTrends(expPoints) {
  const pts = expPoints.map((p) => ({
    ...p,
    by_company: collapseByCompany(p.by_company),
    // The FIRM subset — rates the agreement reached through a named product,
    // not a company-wide default or a median. It is the only expected figure
    // that may be drawn beside what the insurer actually paid.
    by_company_firm: collapseByCompany(p.by_company_firm),
  }))
  for (const p of pts) {
    const total = Object.values(p.by_company).reduce((s, v) => s + (Number(v) || 0), 0)
    p.total_expected = Math.round(total * 100) / 100
  }
  return pts
}

async function load() {
  loading.value = true
  try {
    // EXPECTED commission per production month — updates the moment a
    // production file lands, decoupled from when נפרעים reports arrive.
    // Expected shape is { points, reason } (legacy: a bare array).
    const [expRes, trRes] = await Promise.allSettled([
      api.get('/production/expected-trend'),
      api.get('/production/trend'),
    ])

    let payload = { points: [], reason: null }
    if (expRes.status === 'fulfilled') {
      const d = expRes.value.data
      payload = Array.isArray(d) ? { points: d, reason: null } : (d || { points: [], reason: null })
    } else {
      console.error('Failed to load expected commission trend', expRes.reason)
    }
    const expPoints = Array.isArray(payload.points) ? payload.points : []
    reason.value = payload.reason || null

    points.value = mergeTrends(expPoints)

    // Actual received per month per company — its own endpoint, never blended
    // into the expected series.
    actualPoints.value = trRes.status === 'fulfilled'
      ? (trRes.value.data || []).map(pt => ({
          ...pt,
          by_company: collapseByCompany(pt.by_company),
          // Both sides of the checkable pair get the same brand collapsing as
          // `by_company`, or a legal-entity variant would land in one map and
          // its brand in the other and the pair would silently miss.
          paid_firm_by_company: collapseByCompany(pt.paid_firm_by_company),
          expected_firm_by_company: collapseByCompany(pt.expected_firm_by_company),
          total_expected: pt.total_commission,
        }))
      : []

    // The "התקבל בפועל" headline: each company's LATEST reported month, summed
    // (commission_calculation_model — insurers report on different lags, so
    // one calendar month undercounts and all months summed is a lifetime
    // total). Read from the SAME series the bars draw. It used to come from
    // /comparison/company-summary — the last saved comparison snapshot — which
    // kept counting מגדל ₪3,214 after its rows were gone from every upload:
    // ₪62,327 in the header against ₪59,113 in the bars, with no way to
    // reconcile the two from the screen.
    const latestByCompany = {}
    for (const pt of actualPoints.value) {  // ascending by period — later wins
      for (const [company, v] of Object.entries(pt.by_company || {})) {
        if ((Number(v) || 0) > 0) latestByCompany[company] = Number(v)
      }
    }
    receivedTotal.value = Math.round(
      Object.values(latestByCompany).reduce((s, v) => s + v, 0) * 100) / 100
    receivedCompanies.value = latestByCompany
  } catch (err) {
    console.error('Failed to load commission trend', err)
    points.value = []
    reason.value = null
  } finally {
    loading.value = false
  }
}

onMounted(load)

// Re-fetch in place whenever the store signals fresh production data
// (e.g. after an automation batch). Optional chaining guards builds where
// trendTick isn't on the store yet.
watch(() => productionStore?.trendTick, (tick, prev) => {
  if (tick !== undefined && tick !== prev) load()
})

const hasTrend = computed(() => points.value.length >= 2)
const hasData = computed(() => points.value.length >= 1)
const isSingleMonth = computed(() => points.value.length === 1)

// Honest empty-state copy, keyed by the backend's `reason`. Never tell a
// hands-free automation user to manually upload files.
const emptyState = computed(() => {
  if (reason.value === 'no_production') {
    return {
      icon: 'production',
      title: 'אין עדיין נתוני פרודוקציה',
      sub: 'הפעל את ההורדה האוטומטית או העלה קובץ — והמגמה תתחיל להיבנות',
    }
  }
  if (reason.value === 'no_rates') {
    return {
      icon: 'rates',
      title: 'חסרים שיעורי עמלה לחישוב הצפי',
      sub: 'הגדר שיעורים בלשונית מדף ההסכמים כדי לראות את המגמה',
    }
  }
  return {
    icon: 'default',
    title: 'המגמה עוד לא כאן — אבל היא בדרך',
    sub: 'ככל שיצטברו חודשי פרודוקציה, הגרף יתמלא ויתעדכן אוטומטית',
  }
})

const totals = computed(() => points.value.map(p => Number(p.total_expected) || 0))

const previousLabel = computed(() =>
  points.value.length < 2 ? '' : points.value[points.value.length - 2].period_label || ''
)

const latestLabel = computed(() =>
  points.value.length ? points.value[points.value.length - 1].period_label || '' : ''
)

const latestValue = computed(() =>
  points.value.length ? totals.value[totals.value.length - 1] : 0
)

const momPct = computed(() => {
  const v = totals.value
  if (v.length < 2) return 0
  const prev = v[v.length - 2]
  const curr = v[v.length - 1]
  if (prev === 0) return curr === 0 ? 0 : 100
  return ((curr - prev) / prev) * 100
})

// Every company that contributed in ANY month gets its own segment.
//
// This used to rank on the LATEST period and keep 5. Both halves hid data:
// a month where only one company reported — live, 2026-05 with only הראל —
// pushed every other company into "אחרות", so a chart titled "by month"
// showed one company and a grey blob. Ranking across all periods means a
// company that paid in March is still named in March even if it paid nothing
// in May.
//
// The cap is now the palette's validated slot count, not a readability guess.
// Beyond it the remainder folds into "אחרות" rather than inventing hues.
// What the chart plots. `points` stays the expected series so the headline
// numbers and the drop-insight card keep their meaning.
function countCompanies(pts) {
  const seen = new Set()
  for (const p of pts) {
    for (const [name, v] of Object.entries(p.by_company || {})) {
      if (Number(v) > 0) seen.add(name)
    }
  }
  return seen.size
}
const chartTitle = computed(() => (
  mode.value === 'actual'
    ? (hasExpectedBar.value ? 'עמלות שהתקבלו מול הצפוי לפי חודש' : 'עמלות שהתקבלו לפי חודש')
    : 'עמלות צפויות לפי חודש'
))

const expectedCompanyCount = computed(() => countCompanies(points.value))
const actualCompanyCount = computed(() => countCompanies(actualPoints.value))

const shownPoints = computed(
  () => (mode.value === 'actual' ? actualPoints.value : points.value),
)

// ── בפועל מול צפוי ──────────────────────────────────────────────────────
// "How much should have arrived, and how much did." Both sides come from the
// SAME rows — `/production/trend`'s `paid_firm_by_company` /
// `expected_firm_by_company` — priced only by rates the agreement actually
// names (`:product` / `:residue`). Identical arithmetic to the
// "עמלות בפועל מול ההסכמים" panel, so the two surfaces can never disagree.
//
// ⚠️ Two earlier bases were tried and are wrong, both measured on this book:
//   · production × rates: מנורה's production rows reach a rate only through
//     `exact:median`, giving ₪29,489 expected against ₪8,033 paid — the ₪21K
//     phantom debt the firm gate exists to prevent.
//   · firm production ∩ actual: correct, but on this book it intersects a
//     single company in a single month, so the chart came out empty and the
//     toggle sat disabled. A view that never renders answers nothing.
// The נפרעים row carries the base the insurer actually remitted on, so pricing
// it against the agreement is a real check — and it is non-empty today: live
// 2026-07 shows בפועל ₪30,945 vs צפוי ₪41,414 across 5 companies.
//
// Full `by_company` (all rows) is deliberately NOT the actual side here. מור
// was paid ₪19,373 overall but only ₪1,956 sits on rows with a product-level
// rate; pairing the full figure against a firm expectation invents a surplus.
const compareModel = computed(() => {
  const out = []
  for (const ap of actualPoints.value) {
    const paid = ap.paid_firm_by_company || {}
    const exp = ap.expected_firm_by_company || {}
    const companies = Object.keys(exp).filter(c => (Number(exp[c]) || 0) > 0
      || (Number(paid[c]) || 0) > 0)
    if (!companies.length) continue
    const dropped = []
    for (const [company, v] of Object.entries(ap.by_company || {})) {
      if ((Number(v) || 0) <= 0) continue
      if (companies.includes(company)) continue
      dropped.push({ company, why: 'no_firm_rate' })
    }
    out.push({
      period_label: ap.period_label,
      actual: Math.round(companies.reduce((t, c) => t + (Number(paid[c]) || 0), 0) * 100) / 100,
      expected: Math.round(companies.reduce((t, c) => t + (Number(exp[c]) || 0), 0) * 100) / 100,
      companies,
      paid,
      exp,
      dropped,
      // How much of the month's real income this pair actually covers. Without
      // it the compare bar (₪30,945) silently contradicts the actual bar
      // (₪59,113) two clicks away.
      totalActual: Number(ap.total_expected) || 0,
    })
  }
  return { points: out, skipped: [] }
})

const comparePoints = computed(() => compareModel.value.points)
const compareSkipped = computed(() => [])

// Companies that DID report but carry no agreement line naming their products,
// so nothing can be checked for them. Aggregated across every month.
const compareDropped = computed(() => {
  const seen = new Map()
  for (const m of compareModel.value.points) {
    for (const d of (m.dropped || [])) {
      if (!seen.has(d.company)) seen.set(d.company, d.why)
    }
  }
  return [...seen].map(([company, why]) => ({ company, why }))
})

const COMPARE_DROP_SHOWN = 6
const compareDroppedShown = computed(() => compareDropped.value.slice(0, COMPARE_DROP_SHOWN))
const compareDroppedMore = computed(
  () => Math.max(0, compareDropped.value.length - COMPARE_DROP_SHOWN),
)

const compareCompanies = computed(() => {
  const seen = new Set()
  for (const p of compareModel.value.points) for (const c of p.companies) seen.add(c)
  return [...seen]
})

// What share of the newest month's real income the pair covers — stated, so the
// smaller number here can't read as money that went missing.
const compareCoverage = computed(() => {
  const last = comparePoints.value[comparePoints.value.length - 1]
  if (!last || !last.totalActual) return null
  return {
    checked: last.actual,
    total: last.totalActual,
    pct: Math.round((last.actual / last.totalActual) * 100),
  }
})

const compareSnapshotNote = computed(() => null)

// Only the newest month can be legitimately incomplete: insurers report ~30 days
// late, so its נפרעים set is still filling in.
const compareLatestPartial = computed(() => {
  const n = comparePoints.value.length
  if (n < 2) return false
  return comparePoints.value[n - 1].companies.length < comparePoints.value[n - 2].companies.length
})

const COMPARE_DROP_REASONS = {
  no_report: 'לא התקבל דוח נפרעים בחודש הזה',
  no_firm_rate: 'אין שיעור מפורש בהסכם למוצרים שלה',
}

// The compare view needs BOTH sides; with only one it has nothing to pair.
const canCompare = computed(() => comparePoints.value.some(p => p.expected > 0))

// The 'compare' mode was retired once the expected bar moved into the main
// view; anything that still holds it (a restored session) lands back on
// 'actual', which now shows the pair anyway.
watch(canCompare, () => {
  if (mode.value === 'compare') mode.value = 'actual'
})

const topCompanies = computed(() => {
  if (!shownPoints.value.length) return []
  const totals = {}
  for (const p of shownPoints.value) {
    for (const [name, val] of Object.entries(p.by_company || {})) {
      totals[name] = (totals[name] || 0) + (Number(val) || 0)
    }
  }
  return Object.entries(totals)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, VALIDATED_SLOTS)
    .map(([name]) => name)
})

// Colour follows the COMPANY, not its position in the series array — so a
// month with fewer companies doesn't repaint the ones that remain.
const COMPANY_PALETTE = computed(() => {
  const map = assignCompanyColors(topCompanies.value)
  return [
    ...topCompanies.value.map(c => map.get(c)),
    '#9AA5B1', // "אחרות" — deliberately neutral: a remainder, not a company
  ]
})

// Two plain grouped bars, NOT two stacked-by-company groups. The per-company
// breakdown of the expected side already lives in "עמלות בפועל מול ההסכמים";
// here the comparison itself is the message, and a grouped-stacked chart adds
// a rendering dependency for detail that would be read twice.
const EXPECTED_BAR_COLOR = '#7C8899'

const series = computed(() => {
  if (!shownPoints.value.length) return []
  // Stacked vertical bars per month — the height of each bar IS the total,
  // so we don't add a separate "total" series. Each colored segment is a
  // company.
  const out = []
  topCompanies.value.forEach((company) => {
    out.push({
      name: company,
      data: shownPoints.value.map(p => Number(p.by_company?.[company]) || 0),
    })
  })
  // "אחרות" — the remainder beyond the validated slot count
  const others = shownPoints.value.map((p) => {
    const all = p.by_company || {}
    let sum = 0
    for (const [name, val] of Object.entries(all)) {
      if (!topCompanies.value.includes(name)) sum += Number(val) || 0
    }
    return Math.round(sum * 100) / 100
  })
  if (others.some(v => v > 0)) {
    out.push({ name: 'אחרות', data: others })
  }

  // ── The צפוי bar, standing beside each month's actual bar ──────────────
  // This is the comparison itself, in the window the agent already reads —
  // not behind another toggle. ApexCharts puts two STACKS side by side when
  // each series carries a `group`, so the familiar per-company stack keeps its
  // colours and its total and the expectation lands next to it.
  //
  // One grey series, not a second per-company stack: the legend would
  // otherwise name every insurer twice, and the per-company gap is already in
  // the tooltip where it can be read as a number.
  if (mode.value === 'actual' && hasExpectedBar.value) {
    for (const sr of out) sr.group = 'actual'
    out.push({
      name: 'צפוי לפי ההסכמים',
      group: 'expected',
      data: shownPoints.value.map((p) => {
        const cp = compareByLabel.value.get(p.period_label)
        return cp ? cp.expected : 0
      }),
    })
  }
  return out
})

// Indexed for O(1) lookup from the series/tooltip/dataLabel closures, which run
// per data point per render.
const compareByLabel = computed(
  () => new Map(comparePoints.value.map(p => [p.period_label, p])),
)
const hasExpectedBar = computed(() => comparePoints.value.some(p => p.expected > 0))

// Where the benchmark series sits, or -1. `w.config.series[i].group` comes back
// undefined inside ApexCharts' callbacks — measured: every data label rendered
// empty because the group test never matched — so the index is derived here and
// read from both the label and the tooltip formatters.
const expectedSeriesIndex = computed(
  () => (mode.value === 'actual' && hasExpectedBar.value ? series.value.length - 1 : -1),
)

// Colour comes from the SAME array the chart is given, by index, so the swatch
// can never drift from the bar it names.
const legendItems = computed(() => {
  const colors = mode.value === 'actual' && hasExpectedBar.value
    ? [...COMPANY_PALETTE.value, EXPECTED_BAR_COLOR]
    : COMPANY_PALETTE.value
  return series.value.map((sr, i) => ({
    name: sr.name,
    color: colors[i] || '#9AA5B1',
    benchmark: sr.group === 'expected',
  }))
})

function formatPct(n) {
  const sign = n > 0 ? '+' : ''
  return `${sign}${n.toFixed(1)}%`
}

function formatCurrency(val) {
  return `₪${Number(val || 0).toLocaleString('he-IL', { maximumFractionDigits: 0 })}`
}

function formatSignedCurrency(val) {
  const n = Number(val || 0)
  const sign = n > 0 ? '+' : n < 0 ? '−' : ''
  return `${sign}₪${Math.abs(n).toLocaleString('he-IL', { maximumFractionDigits: 0 })}`
}

// ---- Insight engine ----
// Find the period with the largest negative MoM delta on the total line.
// Attribute it to the 1-3 companies that contributed most to the drop.
// Severity = "warn" when the drop is material (≥ 15% AND ≥ ₪3K), else "info".
const insight = computed(() => {
  const pts = points.value
  if (pts.length < 2) return null

  let worstIdx = -1
  let worstDelta = 0
  for (let i = 1; i < pts.length; i++) {
    const delta = (Number(pts[i].total_expected) || 0) - (Number(pts[i - 1].total_expected) || 0)
    if (delta < worstDelta) {
      worstDelta = delta
      worstIdx = i
    }
  }
  if (worstIdx < 0) return null

  const curr = pts[worstIdx]
  const prev = pts[worstIdx - 1]
  const prevTotal = Number(prev.total_expected) || 0
  const dropPct = prevTotal === 0 ? 0 : (worstDelta / prevTotal) * 100

  // Per-company contribution to the drop
  const allCompanies = new Set([
    ...Object.keys(prev.by_company || {}),
    ...Object.keys(curr.by_company || {}),
  ])
  const contributors = []
  for (const c of allCompanies) {
    const pv = Number(prev.by_company?.[c]) || 0
    const cv = Number(curr.by_company?.[c]) || 0
    const d = cv - pv
    if (d < 0) contributors.push({ company: c, delta: Math.round(d) })
  }
  contributors.sort((a, b) => a.delta - b.delta)
  const topContributors = contributors.slice(0, 3)

  const isMaterial = worstDelta <= -3000 && dropPct <= -15
  const isLatestPeriod = worstIdx === pts.length - 1
  // CTA only makes sense when the drop is on the LATEST period — re-running
  // automation today won't change historical Jan/Feb figures, only fill in
  // missing reports for the current cycle.
  const showCta = isMaterial && isLatestPeriod

  return {
    severity: showCta ? 'warn' : 'info',
    title: isMaterial
      ? `ירידה משמעותית ב-${curr.period_label}`
      : `הירידה הגדולה ביותר: ${curr.period_label}`,
    detail: `${formatSignedCurrency(worstDelta)}${prevTotal > 0 ? ` (${formatPct(dropPct)})` : ''} לעומת ${prev.period_label}${isLatestPeriod && isMaterial ? ' — ייתכן שעדיין לא קיבלנו את כל הדיווחים' : ''}`,
    contributors: topContributors,
  }
})

const chartOptions = computed(() => ({
  chart: {
    type: 'bar',
    // Stacked within each group; the `group` key on each series is what puts
    // the actual stack and the expected bar side by side instead of adding
    // one on top of the other.
    stacked: true,
    fontFamily: 'Heebo, sans-serif',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, easing: 'easeinout', speed: 600 },
  },
  // The expected series is appended last, so its colour goes last. Grey on
  // purpose: it is a benchmark, not another insurer.
  colors: mode.value === 'actual' && hasExpectedBar.value
    ? [...COMPANY_PALETTE.value, EXPECTED_BAR_COLOR]
    : COMPANY_PALETTE.value,
  plotOptions: {
    bar: {
      horizontal: false,
      // A lone month at 55% renders as one massive slab — slim it so the
      // single-point state still reads like the start of a series.
      columnWidth: isSingleMonth.value ? '30%' : '62%',
      borderRadius: 6,
      borderRadiusApplication: 'end',
      borderRadiusWhenStacked: 'last',
    },
  },
  // A 2px surface-coloured gap between stacked segments. Without it adjacent
  // company fills touch, and two hues that pass CVD separation on their own
  // still read as one block where they meet.
  stroke: { show: true, width: 2, colors: ['#fff'] },
  fill: { type: 'solid', opacity: 1 },
  dataLabels: {
    enabled: true,
    formatter: (val, opts) => {
      const arr = series.value
      const expIdx = expectedSeriesIndex.value
      // The benchmark is its own group: its value IS its total. Summing it with
      // the company stack would print the addition of two quantities that exist
      // precisely to be compared.
      if (opts.seriesIndex === expIdx) {
        return Number(val) > 0 ? formatCurrency(val) : ''
      }
      // Company stack: label only the topmost segment, with the stack total.
      const topActual = expIdx >= 0 ? expIdx - 1 : arr.length - 1
      if (opts.seriesIndex !== topActual) return ''
      let sum = 0
      for (let i = 0; i <= topActual; i++) {
        sum += Number(arr[i]?.data?.[opts.dataPointIndex] || 0)
      }
      return sum > 0 ? formatCurrency(sum) : ''
    },
    offsetY: -18,
    style: {
      fontFamily: 'Heebo, sans-serif',
      fontSize: '11px',
      fontWeight: 700,
      colors: ['#181818'],
    },
    background: { enabled: false },
  },
  xaxis: {
    categories: shownPoints.value.map(p => p.period_label || ''),
    labels: {
      style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px', colors: '#706E6B' },
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  yaxis: {
    labels: {
      formatter: formatCurrency,
      style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px', colors: '#706E6B' },
    },
  },
  // A stacked bar with 10 companies produced a 10-row tooltip in which nine
  // rows read ₪0 — the month's actual content (מגדל ₪20) was buried among
  // companies that simply did not report that month. Only series with a value
  // are listed, ordered by size, with the month total on top.
  tooltip: {
    shared: true,
    intersect: false,
    custom: ({ series, dataPointIndex, w }) => {
      const rows = series
        .map((data, i) => ({
          name: w.globals.seriesNames[i],
          value: Number(data[dataPointIndex]) || 0,
          color: w.globals.colors[i],
          // The benchmark is not a company — it must not be listed among the
          // insurers nor summed into the month total.
          isExpected: i === expectedSeriesIndex.value,
        }))
        .filter(r => r.value > 0 && !r.isExpected)
        .sort((a, b) => b.value - a.value)
      const label = w.globals.labels?.[dataPointIndex] ?? ''
      const total = rows.reduce((sum, r) => sum + r.value, 0)
      if (!rows.length) {
        return `<div class="tt"><div class="tt-head">${label}</div>`
          + '<div class="tt-empty">לא התקבלו עמלות בחודש זה</div></div>'
      }
      // The צפוי bar rides in the same tooltip: its own line, the gap on the
      // rows that can actually be checked, and the coverage — because the two
      // bars are NOT the same set of companies and a bare height difference
      // would read as a surplus.
      const pt = compareByLabel.value.get(label)
      let pair = ''
      if (mode.value === 'actual' && pt && pt.expected > 0) {
        const gap = pt.actual - pt.expected
        const gapCls = gap < 0 ? 'tt-neg' : 'tt-pos'
        const per = [...pt.companies]
          .map(c => ({ c, d: (Number(pt.paid[c]) || 0) - (Number(pt.exp[c]) || 0) }))
          .sort((x, y) => x.d - y.d)
          .map(r => '<div class="tt-row tt-sub">'
            + '<span class="tt-dot" style="background:transparent"></span>'
            + `<span class="tt-name">${r.c}</span>`
            + `<span class="tt-val">${formatSignedCurrency(r.d)}</span></div>`)
          .join('')
        pair = '<div class="tt-row tt-sep">'
          + `<span class="tt-dot" style="background:${EXPECTED_BAR_COLOR}"></span>`
          + '<span class="tt-name">צפוי לפי ההסכמים</span>'
          + `<span class="tt-val">${formatCurrency(pt.expected)}</span></div>`
          + '<div class="tt-row tt-sub"><span class="tt-dot" style="background:transparent"></span>'
          + `<span class="tt-name">מתוכו התקבל (${pt.companies.length} חברות בנות-השוואה)</span>`
          + `<span class="tt-val">${formatCurrency(pt.actual)}</span></div>`
          + `<div class="tt-row ${gapCls}"><span class="tt-dot" style="background:transparent"></span>`
          + '<span class="tt-name">פער</span>'
          + `<span class="tt-val">${formatSignedCurrency(gap)}</span></div>`
          + per
      }
      const body = rows.map(r => (
        '<div class="tt-row">'
        + `<span class="tt-dot" style="background:${r.color}"></span>`
        + `<span class="tt-name">${r.name}</span>`
        + `<span class="tt-val">${formatCurrency(r.value)}</span>`
        + '</div>'
      )).join('')
      return `<div class="tt"><div class="tt-head">${label}`
        + `<span class="tt-total">${formatCurrency(total)}</span></div>${body}${pair}</div>`
    },
  },
  // Our own legend, rendered in the template. ApexCharts lays ITS legend out
  // as a COLUMN once series carry a `group` (grouped stacking): ten insurers
  // became a ten-row block 160px tall inside a 320px canvas, squeezing the
  // plot into a strip. Measured — every item sat at the same x, 26px apart.
  legend: { show: false },
  grid: { borderColor: '#E5E5E5', strokeDashArray: 3, padding: { top: 20 } },
}))
</script>

<style>
/* Custom tooltip for the stacked commission chart. Unscoped on purpose:
   ApexCharts injects this markup outside the component's DOM. */
.apexcharts-tooltip .tt { font-family: Heebo, sans-serif; direction: rtl; padding: 4px 0; min-width: 190px; }
.apexcharts-tooltip .tt-head {
  display: flex; justify-content: space-between; gap: 14px; align-items: baseline;
  padding: 6px 12px 7px; border-bottom: 1px solid #E5E5E5;
  font-size: 12px; font-weight: 700; color: #3E3E3C;
}
.apexcharts-tooltip .tt-total { font-size: 12px; font-weight: 700; color: #3E3E3C; direction: ltr; }
.apexcharts-tooltip .tt-row {
  display: flex; align-items: center; gap: 8px; padding: 4px 12px; font-size: 12px;
}
.apexcharts-tooltip .tt-dot { width: 9px; height: 9px; border-radius: 2px; flex-shrink: 0; }
.apexcharts-tooltip .tt-name { color: #3E3E3C; flex: 1; }
.apexcharts-tooltip .tt-val { color: #706E6B; direction: ltr; }
.apexcharts-tooltip .tt-empty { padding: 8px 12px; font-size: 12px; color: #706E6B; }
/* The gap row in the בפועל-מול-צפוי tooltip. Paid-less is the actionable
   direction, so it gets the loss hue; paid-more is worth knowing, not chasing. */
.apexcharts-tooltip .tt-row.tt-neg { border-top: 1px solid #E5E5E5; margin-top: 3px; padding-top: 7px; }
.apexcharts-tooltip .tt-row.tt-pos { border-top: 1px solid #E5E5E5; margin-top: 3px; padding-top: 7px; }
.apexcharts-tooltip .tt-row.tt-neg .tt-name,
.apexcharts-tooltip .tt-row.tt-neg .tt-val { color: #C23934; font-weight: 700; }
.apexcharts-tooltip .tt-row.tt-pos .tt-name,
.apexcharts-tooltip .tt-row.tt-pos .tt-val { color: #2E844A; font-weight: 700; }
</style>

<style scoped>
.trend-modes { display: flex; gap: 6px; margin-right: auto; }
/* The compare-mode coverage block. It used to be one long paragraph with ten
   companies inline; at 11px that is a wall, and the thing it has to communicate
   is exactly what a wall hides. */
.trend-legend {
  display: flex; flex-wrap: wrap; justify-content: flex-end;
  gap: 4px 14px; margin: 0 0 6px; padding: 0; list-style: none;
  font-size: 12px; color: var(--text-muted);
}
.trend-legend li { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.tl-dot { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
/* The benchmark is not one of the insurers — it reads as a label, not a slice. */
.trend-legend--bench { font-weight: 600; color: var(--text-secondary); }

.trend-compare-note {
  margin: 4px 0 10px;
  font-size: 11px;
  line-height: 1.7;
  color: var(--text-muted);
}
.trend-compare-note .tcn-lead { margin: 0 0 4px; color: var(--text-secondary); }
.trend-compare-note .tcn-line { margin: 0 0 4px; }
.tcn-list {
  display: flex; flex-wrap: wrap; gap: 4px 10px;
  margin: 6px 0 0; padding: 0; list-style: none;
}
.tcn-list li {
  display: inline-flex; align-items: baseline; gap: 5px;
  padding: 2px 8px; border-radius: 10px;
  background: var(--bg); white-space: nowrap;
}
.tcn-co { font-weight: 600; color: var(--text-secondary); }
.tcn-why { color: var(--text-muted); }
.tcn-more { color: var(--text-muted); }

.trend-coverage {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  margin: 10px 0 2px; font-size: 12px; color: var(--text-muted);
}
.trend-coverage-btn {
  padding: 3px 10px; border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm); background: none; color: var(--primary);
  font-family: inherit; font-size: 12px; font-weight: 600; cursor: pointer;
}
.trend-coverage-btn:hover { background: var(--primary-light); }
.trend-mode {
  padding: 4px 12px; border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm); background: none; color: var(--text-muted);
  font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.trend-mode.active { background: var(--primary-light); color: var(--primary); border-color: transparent; }
.trend-mode:disabled { opacity: 0.45; cursor: default; }

.trend-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  padding: 20px;
  margin-top: 16px;
}

.trend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.trend-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.trend-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: var(--primary-light);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.trend-title h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin: 0;
}

.trend-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}

.trend-badge--up { background: rgba(46, 132, 74, 0.12); color: #1B5E20; }
.trend-badge--down { background: rgba(194, 57, 52, 0.12); color: #C23934; }
.trend-badge--flat { background: var(--border-subtle); color: var(--text-muted); }
.trend-badge-sub { font-weight: 500; opacity: 0.75; margin-inline-start: 4px; }

.trend-current { display: flex; flex-direction: column; align-items: flex-end; gap: 2px; }
.trend-current-label { font-size: 11px; color: var(--text-muted); font-weight: 500; }
.trend-current-value { font-size: 18px; font-weight: 700; color: var(--primary); }

.trend-insight {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  border: 1px solid;
  margin-bottom: 14px;
}

.trend-insight--warn {
  background: rgba(194, 57, 52, 0.06);
  border-color: rgba(194, 57, 52, 0.25);
  color: #C23934;
}

.trend-insight--info {
  background: rgba(127, 86, 217, 0.05);
  border-color: rgba(127, 86, 217, 0.2);
  color: #7F56D9;
}

.trend-insight-body { display: flex; gap: 10px; flex: 1; min-width: 0; }

.trend-insight-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: currentColor;
  color: #fff;
  opacity: 0.9;
}

.trend-insight--warn .trend-insight-icon { background: #C23934; }
.trend-insight--info .trend-insight-icon { background: #7F56D9; }

.trend-insight-text { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.trend-insight-title { font-size: 13px; font-weight: 700; }
.trend-insight-detail { font-size: 12px; opacity: 0.85; line-height: 1.5; }

.trend-insight-list {
  list-style: none;
  margin: 6px 0 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px 12px;
}

.trend-insight-list li {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.5);
}

.trend-insight-list-name { font-weight: 600; }
.trend-insight-list-delta { font-weight: 700; }

.trend-insight-cta {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border-radius: 10px;
  background: #C23934;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s ease;
  font-family: inherit;
}

.trend-insight-cta:hover { background: #C23934; }

.trend-chart-wrap {
  width: 100%;
  min-height: 300px;
  direction: ltr;
}

.trend-single-caption {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--text-muted);
  text-align: center;
  animation: trend-caption-in 0.25s ease-out;
}

@keyframes trend-caption-in {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .trend-single-caption { animation: none; }
}

.trend-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 40px 20px;
  text-align: center;
  min-height: 200px;
}

.trend-empty-icon {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: var(--primary-light);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 4px;
}

.trend-empty-title { margin: 0; font-size: 14px; font-weight: 700; color: var(--text); }
.trend-empty-sub { margin: 0; font-size: 12px; line-height: 1.5; color: var(--text-muted); max-width: 320px; }

.trend-empty-spinner {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  border: 2.5px solid var(--border-subtle);
  border-top-color: var(--primary);
  animation: trend-spin 0.8s linear infinite;
}

@keyframes trend-spin { to { transform: rotate(360deg); } }
.trend-current--actual .trend-current-value { color: var(--chart-9); }
.trend-current--actual .trend-current-label { color: var(--text-muted); }
.trend-uncovered { margin: 6px 0 0; font-size: 11.5px; color: var(--text-muted); display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline; }
.tu-lead { font-weight: 650; }
.tu-item { white-space: nowrap; }
.tu-why { color: var(--chart-4); }
.tu-why::before { content: '— '; }
</style>
