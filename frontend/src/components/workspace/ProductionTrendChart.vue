<template>
  <div class="trend-card">
    <div class="trend-header">
      <div class="trend-title">
        <span class="trend-icon" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
        </span>
        <h3>עמלות צפויות לפי חודש</h3>
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
    </div>

    <!-- Insight card: biggest drop + CTA to automation -->
    <div v-if="insight" class="trend-insight" :class="`trend-insight--${insight.severity}`">
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
      <div class="trend-chart-wrap">
        <apexchart
          type="bar"
          height="320"
          width="100%"
          :options="chartOptions"
          :series="series"
        />
      </div>
      <p v-if="isSingleMonth" class="trend-single-caption">
        חודש ראשון נקלט — המגמה תצטייר אוטומטית עם ההורדה הבאה
      </p>
      <!-- Why companies are missing from the bar. Without this, an agent
           seeing 2 of 7 companies can't tell "no agreement rate for these"
           from "the app lost my data". -->
      <p v-if="uncovered.length" class="trend-uncovered">
        <span class="tu-lead">לא נכללות בחישוב:</span>
        <span v-for="u in uncovered" :key="u.company" class="tu-item">
          {{ u.company }}
          <span class="tu-why">{{ u.no_rate >= u.no_base ? 'אין שיעור בהסכם' : 'אין צבירה או פרמיה בקובץ' }}</span>
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
import { CHART_PALETTE } from '../../utils/chartPalette.js'
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

// Companies in the LATEST month's production that contribute no expected
// commission, with the reason the backend gives.
const uncovered = computed(() => {
  const last = points.value[points.value.length - 1]
  return (last?.uncovered || []).slice(0, 6)
})

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
  const pts = expPoints.map((p) => ({ ...p, by_company: collapseByCompany(p.by_company) }))
  for (const p of pts) {
    const total = Object.values(p.by_company).reduce((s, v) => s + (Number(v) || 0), 0)
    p.total_expected = Math.round(total * 100) / 100
  }
  return pts
}

async function load() {
  loading.value = true
  try {
    // EXPECTED commission per production month (primary) — updates the moment a
    // production file lands. Decoupled from when נפרעים reports arrive. The latest
    // period is topped up with ACTUAL received per company (/comparison/company-summary)
    // so companies whose production has no priceable base (Phoenix life) still
    // surface. Expected shape is { points, reason } (legacy: a bare array).
    const [expRes, csRes] = await Promise.allSettled([
      api.get('/production/expected-trend'),
      api.get('/comparison/company-summary'),
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

    // Per-company actual received (₪) — { companyName: received }.
    const receivedByCompany = {}
    if (csRes.status === 'fulfilled') {
      for (const c of (csRes.value.data?.companies || [])) {
        const v = Number(c.received) || 0
        if (v > 0) receivedByCompany[c.company] = v
      }
    }

    points.value = mergeTrends(expPoints)
    // Kept separate on purpose — this is what ARRIVED, not what is owed.
    receivedTotal.value = Object.values(receivedByCompany)
      .reduce((s, v) => s + (Number(v) || 0), 0)
    receivedCompanies.value = collapseByCompany(receivedByCompany)
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
      sub: 'הגדר שיעורים בלשונית טבלת עמלות כדי לראות את המגמה',
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

// Top companies by latest period contribution → become individual lines.
// Limit to 5 so the chart stays readable; remaining companies are rolled
// into "אחרות" (still shown as a thin line so totals reconcile visually).
const topCompanies = computed(() => {
  if (!points.value.length) return []
  const latest = points.value[points.value.length - 1].by_company || {}
  return Object.entries(latest)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name]) => name)
})

// Bright-bold categorical palette (shared) for the stacked company segments.
const COMPANY_PALETTE = CHART_PALETTE

const series = computed(() => {
  if (!points.value.length) return []
  // Stacked vertical bars per month — the height of each bar IS the total,
  // so we don't add a separate "total" series. Each colored segment is a
  // company.
  const out = []
  topCompanies.value.forEach((company) => {
    out.push({
      name: company,
      data: points.value.map(p => Number(p.by_company?.[company]) || 0),
    })
  })
  // "אחרות" — every company not in top 5
  const others = points.value.map((p) => {
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
  return out
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
    stacked: true,
    fontFamily: 'Heebo, sans-serif',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, easing: 'easeinout', speed: 600 },
  },
  colors: COMPANY_PALETTE,
  plotOptions: {
    bar: {
      horizontal: false,
      // A lone month at 55% renders as one massive slab — slim it so the
      // single-point state still reads like the start of a series.
      columnWidth: isSingleMonth.value ? '18%' : '55%',
      borderRadius: 6,
      borderRadiusApplication: 'end',
      borderRadiusWhenStacked: 'last',
    },
  },
  stroke: { show: false },
  fill: { type: 'solid', opacity: 1 },
  dataLabels: {
    enabled: true,
    formatter: (val, opts) => {
      // Only show the cumulative total on the TOP of each stack
      const seriesArr = opts.w.config.series
      const isTopVisible = opts.seriesIndex === seriesArr.length - 1
      if (!isTopVisible) return ''
      let sum = 0
      for (let i = 0; i < seriesArr.length; i++) {
        sum += Number(seriesArr[i].data[opts.dataPointIndex] || 0)
      }
      return formatCurrency(sum)
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
    categories: points.value.map(p => p.period_label || ''),
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
  tooltip: {
    shared: true,
    intersect: false,
    y: { formatter: formatCurrency },
  },
  legend: {
    show: true,
    position: 'top',
    horizontalAlign: 'right',
    fontFamily: 'Heebo, sans-serif',
    fontSize: '12px',
    itemMargin: { horizontal: 8, vertical: 4 },
    markers: { width: 10, height: 10, radius: 3 },
    labels: { colors: '#706E6B' },
  },
  grid: { borderColor: '#E5E5E5', strokeDashArray: 3, padding: { top: 20 } },
}))
</script>

<style scoped>
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
