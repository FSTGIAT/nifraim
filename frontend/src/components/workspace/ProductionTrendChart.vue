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
      <div v-if="hasTrend" class="trend-current">
        <span class="trend-current-label">סה"כ {{ latestLabel }}</span>
        <span class="trend-current-value ltr-number">{{ formatCurrency(latestValue) }}</span>
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

    <div v-if="hasTrend" class="trend-chart-wrap">
      <apexchart
        type="bar"
        height="320"
        width="100%"
        :options="chartOptions"
        :series="series"
      />
    </div>

    <div v-else-if="loading" class="trend-empty">
      <div class="trend-empty-spinner" aria-hidden="true"></div>
      <p class="trend-empty-sub">טוען נתוני עמלות…</p>
    </div>

    <div v-else class="trend-empty">
      <span class="trend-empty-icon" aria-hidden="true">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
      </span>
      <p class="trend-empty-title">העלה קבצי פרודוקציה מחודשים נוספים כדי לראות מגמה</p>
      <p class="trend-empty-sub">נצטרך לפחות שני חודשים שונים של פרודוקציה כדי לצייר את הקו</p>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../../api/client.js'

defineEmits(['go-to-automation'])

const points = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    // EXPECTED commission per production month — the moment the agent uploads
    // a new production file the chart updates. Decoupled from when נפרעים
    // reports actually arrive. Endpoint returns `total_expected` per period.
    const { data } = await api.get('/production/expected-trend')
    points.value = Array.isArray(data) ? data : []
  } catch (err) {
    console.error('Failed to load expected commission trend', err)
    points.value = []
  } finally {
    loading.value = false
  }
})

const hasTrend = computed(() => points.value.length >= 2)

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

const COMPANY_PALETTE = ['#1E40AF', '#0E7490', '#7C3AED', '#B45309', '#15803D']

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
  colors: [...COMPANY_PALETTE, '#E8660A', '#94a3b8'],
  plotOptions: {
    bar: {
      horizontal: false,
      columnWidth: '55%',
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
      colors: ['#1f2937'],
    },
    background: { enabled: false },
  },
  xaxis: {
    categories: points.value.map(p => p.period_label || ''),
    labels: {
      style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px', colors: '#94a3b8' },
    },
    axisBorder: { show: false },
    axisTicks: { show: false },
  },
  yaxis: {
    labels: {
      formatter: formatCurrency,
      style: { fontFamily: 'Heebo, sans-serif', fontSize: '11px', colors: '#94a3b8' },
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
    labels: { colors: '#64748b' },
  },
  grid: { borderColor: '#e2e8f0', strokeDashArray: 3, padding: { top: 20 } },
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

.trend-badge--up { background: rgba(16, 185, 129, 0.12); color: #047857; }
.trend-badge--down { background: rgba(239, 68, 68, 0.12); color: #b91c1c; }
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
  background: rgba(239, 68, 68, 0.06);
  border-color: rgba(239, 68, 68, 0.25);
  color: #7f1d1d;
}

.trend-insight--info {
  background: rgba(59, 130, 246, 0.05);
  border-color: rgba(59, 130, 246, 0.2);
  color: #1e3a8a;
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

.trend-insight--warn .trend-insight-icon { background: #b91c1c; }
.trend-insight--info .trend-insight-icon { background: #2563eb; }

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
  background: #b91c1c;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  border: none;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s ease;
  font-family: inherit;
}

.trend-insight-cta:hover { background: #991b1b; }

.trend-chart-wrap {
  width: 100%;
  min-height: 300px;
  direction: ltr;
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
</style>
