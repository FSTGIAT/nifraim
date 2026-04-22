<template>
  <div class="chart-card">
    <h3>התפלגות לפי חברה</h3>
    <div v-if="breakdown.length" class="chart-layout">
      <!-- SVG Donut -->
      <div class="donut-wrap">
        <svg viewBox="0 0 200 200" class="donut-svg">
          <circle cx="100" cy="100" r="80" fill="none" stroke="var(--border-subtle)" stroke-width="32" />
          <circle
            v-for="(seg, i) in segments"
            :key="i"
            cx="100" cy="100" r="80"
            fill="none"
            :stroke="colors[i % colors.length]"
            stroke-width="32"
            :stroke-dasharray="seg.dash"
            :stroke-dashoffset="seg.offset"
            stroke-linecap="butt"
            class="donut-segment"
          />
        </svg>
        <div class="donut-center">
          <span class="donut-label">סה"כ צבירה</span>
          <span class="donut-total ltr-number">{{ formatCurrency(total) }}</span>
        </div>
      </div>

      <!-- Legend -->
      <div class="legend">
        <div v-for="(item, i) in items" :key="i" class="legend-row">
          <span class="legend-dot" :style="{ background: colors[i % colors.length] }"></span>
          <span class="legend-name">{{ item.shortName }}</span>
          <span class="legend-value ltr-number">{{ formatCurrency(item.value) }}</span>
          <span class="legend-pct ltr-number">{{ item.pct }}%</span>
        </div>
      </div>
    </div>
    <p v-else class="empty">אין נתונים</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  breakdown: Array,
})

const colors = ['#E8660A', '#F57C00', '#C85A00', '#A8703A', '#D68B4A', '#8C4A00', '#FFB74D', '#6B3A0A']

const circumference = 2 * Math.PI * 80 // ~502.65

const total = computed(() =>
  (props.breakdown || []).reduce((s, b) => s + (b.accumulation || 0), 0)
)

const items = computed(() => {
  if (!total.value) return []
  return (props.breakdown || []).map(b => {
    const val = b.accumulation || 0
    const pct = Math.round((val / total.value) * 100)
    return {
      company: b.company,
      shortName: shortenCompany(b.company),
      value: val,
      pct,
    }
  }).filter(x => x.pct > 0)
})

const segments = computed(() => {
  const segs = []
  let offset = circumference * 0.25 // start from top (12 o'clock)
  for (const item of items.value) {
    const len = (item.value / total.value) * circumference
    const gap = 2
    segs.push({
      dash: `${Math.max(len - gap, 0)} ${circumference}`,
      offset: -offset,
    })
    offset += len
  }
  return segs
})

function shortenCompany(name) {
  // Remove common suffixes to keep legend compact
  return name
    .replace(/\s*בע"מ\s*/g, '')
    .replace(/\s*חברה לביטוח\s*/g, '')
    .replace(/\s*פנסיה וגמל\s*/g, '')
    .replace(/\s*גמל ופנסיה\s*/g, '')
    .trim()
}

function formatCurrency(val) {
  if (val >= 1_000_000) {
    return `₪${(val / 1_000_000).toFixed(1)}M`
  }
  if (val >= 1_000) {
    return `₪${(val / 1_000).toFixed(0)}K`
  }
  return new Intl.NumberFormat('he-IL', { style: 'currency', currency: 'ILS', maximumFractionDigits: 0 }).format(val)
}
</script>

<style scoped>
.chart-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 20px;
}

h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 16px;
}

.chart-layout {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 20px;
}

/* Donut */
.donut-wrap {
  position: relative;
  width: 180px;
  height: 180px;
}

.donut-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.donut-segment {
  transition: opacity 0.2s;
}

.donut-segment:hover {
  opacity: 0.75;
}

.donut-center {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.donut-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
}

.donut-total {
  font-size: 15px;
  font-weight: 800;
  color: var(--text);
  margin-top: 2px;
}

/* Legend */
.legend {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.legend-row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  line-height: 1;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  flex-shrink: 0;
}

.legend-name {
  color: var(--text-secondary);
  font-weight: 600;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.legend-value {
  color: var(--text);
  font-weight: 700;
  font-size: 12px;
  direction: ltr;
  unicode-bidi: embed;
}

.legend-pct {
  color: var(--text-muted);
  font-weight: 600;
  font-size: 11px;
  min-width: 32px;
  text-align: left;
  direction: ltr;
  unicode-bidi: embed;
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
}

.empty {
  text-align: center;
  color: var(--text-muted);
  padding: 40px 0;
  font-size: 14px;
}
</style>
