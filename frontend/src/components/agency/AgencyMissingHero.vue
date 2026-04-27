<template>
  <div class="mh-card" :class="{ rising: deltaPositive, falling: deltaNegative }">
    <div class="mh-blob"></div>

    <div class="mh-grid">
      <!-- Left: hero number -->
      <div class="mh-left">
        <div class="mh-eyebrow">
          <span class="mh-pulse"></span>
          כסף אבוד החודש — {{ thisLabel }}
        </div>
        <div class="mh-number ltr-number">{{ animatedAmount }}</div>
        <div class="mh-meta">
          <span><strong>{{ thisPolicies.toLocaleString('he-IL') }}</strong> פוליסות</span>
          <span class="mh-dot">·</span>
          <span v-if="data?.delta_pct != null">
            <span class="delta" :class="{ up: deltaPositive, down: deltaNegative }">
              <span v-if="deltaPositive">▲</span><span v-else-if="deltaNegative">▼</span>
              {{ Math.abs(data.delta_pct).toFixed(1) }}%
            </span>
            לעומת {{ lastLabel }}
          </span>
          <span v-else>אין השוואה לחודש קודם</span>
        </div>
      </div>

      <!-- Center: trend sparkline -->
      <div class="mh-spark" v-if="trendSeries.length">
        <apexchart type="area" height="120" :options="sparkOptions" :series="[{ name: 'אבוד', data: trendSeries }]" />
      </div>

      <!-- Right: top culprit companies -->
      <div class="mh-culprits">
        <div class="mh-culprits-h">חברות אחראיות</div>
        <ul>
          <li v-for="(c, idx) in topCompanies" :key="idx">
            <span class="mh-rank">{{ idx + 1 }}</span>
            <span class="mh-co">{{ shortName(c.company) }}</span>
            <span class="mh-amt ltr-number">{{ formatShort(c.amount) }}</span>
          </li>
          <li v-if="!topCompanies.length" class="empty">— אין נתונים —</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'

const props = defineProps({
  data: { type: Object, default: null },
})

const animatedAmount = ref('₪ 0')

const thisLabel = computed(() => formatPeriod(props.data?.this_month?.period))
const lastLabel = computed(() => formatPeriod(props.data?.last_month?.period))
const thisAmount = computed(() => Number(props.data?.this_month?.amount || 0))
const thisPolicies = computed(() => Number(props.data?.this_month?.policies || 0))
const topCompanies = computed(() => props.data?.this_month?.top_companies || [])

const deltaPositive = computed(() => (props.data?.delta_pct || 0) > 0)
const deltaNegative = computed(() => (props.data?.delta_pct || 0) < 0)

const trendSeries = computed(() => (props.data?.trend || []).slice(-9).map(t => Math.round(t.amount)))

const sparkOptions = computed(() => ({
  chart: {
    sparkline: { enabled: true },
    animations: { enabled: true, easing: 'easeOutCubic', speed: 800 },
  },
  colors: [deltaPositive.value ? '#8C1D2A' : '#2E844A'],
  stroke: { curve: 'smooth', width: 2.5 },
  fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.45, opacityTo: 0.05 } },
  markers: { size: 4, colors: ['#fff'], strokeColors: deltaPositive.value ? '#8C1D2A' : '#2E844A', strokeWidth: 2 },
  tooltip: { enabled: true, fixed: { enabled: false }, y: { formatter: (v) => '₪ ' + Math.round(v).toLocaleString('he-IL') } },
}))

watch(thisAmount, (v) => animateTo(v), { immediate: false })
onMounted(() => animateTo(thisAmount.value))

function animateTo(target) {
  const start = Number(animatedAmount.value.replace(/[^0-9-]/g, '')) || 0
  const dur = 800
  const t0 = performance.now()
  function tick(now) {
    const t = Math.min(1, (now - t0) / dur)
    const ease = 1 - Math.pow(1 - t, 3)
    const cur = Math.round(start + (target - start) * ease)
    animatedAmount.value = '₪ ' + cur.toLocaleString('he-IL')
    if (t < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

function formatPeriod(p) {
  if (!p) return ''
  const [y, m] = p.split('-')
  const months = ['ינו','פבר','מרץ','אפר','מאי','יונ','יול','אוג','ספט','אוק','נוב','דצמ']
  return `${months[parseInt(m, 10) - 1] || m} ${y}`
}

function formatShort(v) {
  if (v == null || v === 0) return '₪0'
  const n = Number(v)
  if (n >= 1_000_000) return '₪' + (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return '₪' + Math.round(n / 1_000) + 'K'
  return '₪' + Math.round(n).toLocaleString('he-IL')
}

function shortName(s) {
  if (!s) return ''
  return s.replace(/\s*חברה\s*לביטוח/g, '').replace(/\s*בע"מ/g, '').replace(/\s*בע״מ/g, '').trim()
}
</script>

<style scoped>
.mh-card {
  position: relative;
  background: linear-gradient(135deg, #FFE0B2 0%, #FFB74D 100%);
  border-radius: 18px;
  padding: 22px 26px;
  margin-bottom: 22px;
  box-shadow: 0 16px 40px -16px rgba(232, 102, 10, 0.45);
  overflow: hidden;
  border: 1px solid rgba(255, 255, 255, 0.55);
}
.mh-card.rising  { background: linear-gradient(135deg, #FFD8A8 0%, #FF9F66 100%); }
.mh-card.falling { background: linear-gradient(135deg, #DCEFC9 0%, #A5D88E 100%); }

.mh-blob {
  position: absolute; inset: -40% -10% auto auto; width: 60%; aspect-ratio: 1;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.55), transparent 60%);
  filter: blur(40px); pointer-events: none;
}

.mh-grid {
  position: relative;
  display: grid;
  grid-template-columns: 1.4fr 1fr 1fr;
  gap: 24px; align-items: center;
}

.mh-eyebrow {
  font-size: 11.5px; font-weight: 700; letter-spacing: 1.4px;
  text-transform: uppercase; color: #5C2400;
  display: inline-flex; align-items: center; gap: 8px;
}
.mh-pulse {
  width: 8px; height: 8px; border-radius: 50%;
  background: #C23934;
  box-shadow: 0 0 0 4px rgba(194, 57, 52, 0.25);
  animation: pulse 1.6s ease-in-out infinite;
}
@keyframes pulse {
  0%, 100% { box-shadow: 0 0 0 4px rgba(194, 57, 52, 0.25); }
  50%      { box-shadow: 0 0 0 9px rgba(194, 57, 52, 0); }
}
.mh-number {
  font-size: clamp(36px, 5vw, 56px);
  font-weight: 900;
  letter-spacing: -1.5px;
  line-height: 1;
  margin: 12px 0 8px;
  color: #2D2522;
  background: linear-gradient(120deg, #2D2522 0%, #5C2400 50%, #2D2522 100%);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}
.mh-meta {
  font-size: 13.5px; color: rgba(45, 37, 34, 0.78);
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
}
.mh-meta strong { font-weight: 800; color: #2D2522; }
.mh-dot { opacity: 0.45; }
.delta {
  display: inline-flex; align-items: center; gap: 4px;
  font-weight: 800;
  padding: 2px 8px; border-radius: 999px;
  background: rgba(45, 37, 34, 0.08);
}
.delta.up   { color: #8C1D2A; background: rgba(140, 29, 42, 0.10); }
.delta.down { color: #2E844A; background: rgba(46, 132, 74, 0.10); }

.mh-spark { min-width: 0; }

.mh-culprits {
  background: rgba(255, 255, 255, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.7);
  border-radius: 12px;
  padding: 12px 14px;
}
.mh-culprits-h {
  font-size: 11px; font-weight: 800; color: rgba(45, 37, 34, 0.65);
  letter-spacing: 1.2px; text-transform: uppercase;
  margin-bottom: 8px;
}
.mh-culprits ul { list-style: none; padding: 0; margin: 0; }
.mh-culprits li {
  display: grid; grid-template-columns: 22px 1fr auto;
  align-items: center; gap: 10px;
  padding: 6px 0; font-size: 13px;
  border-bottom: 1px dashed rgba(45, 37, 34, 0.12);
}
.mh-culprits li:last-child { border-bottom: none; }
.mh-rank {
  width: 22px; height: 22px; border-radius: 50%;
  background: #2D2522; color: #FFE0B2;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 800;
}
.mh-co { color: #2D2522; font-weight: 600; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mh-amt { color: #5C2400; font-weight: 800; }
.mh-culprits li.empty { display: block; text-align: center; color: rgba(45, 37, 34, 0.4); font-style: italic; }

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

@media (max-width: 1100px) {
  .mh-grid { grid-template-columns: 1fr 1fr; }
  .mh-spark { grid-column: 1 / -1; }
}
@media (max-width: 700px) {
  .mh-grid { grid-template-columns: 1fr; gap: 14px; }
}
</style>
