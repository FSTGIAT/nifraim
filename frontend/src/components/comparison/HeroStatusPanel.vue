<template>
  <section class="hero" :class="{ 'hero--empty': isEmpty }">
    <div class="hero-bg" aria-hidden="true">
      <span class="glow glow-a"></span>
      <span class="glow glow-b"></span>
    </div>

    <header class="hero-head">
      <div class="hh-titles">
        <h3 class="hh-title">סטטוס נפרעים</h3>
        <p class="hh-sub">{{ subTitle }}</p>
      </div>
      <span v-if="lastComputedAt" class="hh-pill">
        <span class="hh-pill-dot" aria-hidden="true"></span>
        עודכן {{ relativeHebrew(lastComputedAt) }}
      </span>
    </header>

    <div v-if="!isEmpty" class="kpi-row">
      <button
        type="button"
        class="kpi kpi--btn"
        :disabled="!openAmount"
        :aria-disabled="!openAmount ? 'true' : null"
        @click="onTile('open-amount')"
      >
        <span class="kpi-label">סך חיוב פתוח</span>
        <span class="kpi-value ltr-number">{{ shortShekel(openAmount) }}</span>
        <span class="kpi-sub ltr-number">{{ openCount.toLocaleString('he-IL') }} חיובים</span>
        <span class="kpi-chev" aria-hidden="true">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 12H5M12 5l-7 7 7 7"/>
          </svg>
        </span>
      </button>

      <button
        type="button"
        class="kpi kpi--btn"
        :disabled="!debtCustomers"
        :aria-disabled="!debtCustomers ? 'true' : null"
        @click="onTile('debt-customers')"
      >
        <span class="kpi-label">לקוחות עם חוב</span>
        <span class="kpi-value ltr-number">{{ debtCustomers.toLocaleString('he-IL') }}</span>
        <span class="kpi-sub">דרושה התייחסות</span>
        <span class="kpi-chev" aria-hidden="true">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 12H5M12 5l-7 7 7 7"/>
          </svg>
        </span>
      </button>

      <button
        type="button"
        class="kpi kpi--btn"
        :disabled="!debtCompanies"
        :aria-disabled="!debtCompanies ? 'true' : null"
        @click="onTile('debt-companies')"
      >
        <span class="kpi-label">חברות פעילות</span>
        <span class="kpi-value ltr-number">{{ debtCompanies.toLocaleString('he-IL') }}</span>
        <span class="kpi-sub ltr-number">{{ paidCount.toLocaleString('he-IL') }} שולמו</span>
        <span class="kpi-chev" aria-hidden="true">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 12H5M12 5l-7 7 7 7"/>
          </svg>
        </span>
      </button>
    </div>

    <div v-else class="hero-empty">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <circle cx="12" cy="12" r="9"/>
        <path d="M12 7v5l3 2"/>
      </svg>
      <p>אין נתוני נפרעים עדיין</p>
      <span>הפעל אוטומציה מעל או העלה דוח ידנית מההגדרות למטה</span>
    </div>

    <ul v-if="insightLines.length" class="hero-insights" role="note">
      <li v-for="(line, i) in insightLines" :key="i">
        <span class="hi-spark" aria-hidden="true">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 2l1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8z"/>
          </svg>
        </span>
        <span>{{ line }}</span>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { shortShekel } from '../../utils/monthDeltas.js'
import { relativeHebrew } from '../../utils/relativeTime.js'

const props = defineProps({
  openCount: { type: Number, default: 0 },
  openAmount: { type: Number, default: 0 },
  paidCount: { type: Number, default: 0 },
  debtCustomers: { type: Number, default: 0 },
  debtCompanies: { type: Number, default: 0 },
  lastComputedAt: { type: [String, Number, Date], default: null },
  insightLines: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['tile-click'])

const isEmpty = computed(
  () => !props.loading && !props.openCount && !props.paidCount,
)

const subTitle = computed(() => {
  if (props.loading) return 'טוען נתונים…'
  if (isEmpty.value) return 'אין דוח נפרעים פעיל בקטגוריה זו'
  return 'תמונת מצב לפי הקבצים שעובדו לאחרונה'
})

function onTile(id) {
  emit('tile-click', id)
}
</script>

<style scoped>
.hero {
  position: relative;
  border-radius: 20px;
  padding: 22px 24px 20px;
  overflow: hidden;
  font-family: 'Heebo', sans-serif;
  color: #F5F1EC;
  background:
    radial-gradient(140% 110% at 0% 0%, rgba(245, 124, 0, 0.22) 0%, transparent 55%),
    linear-gradient(140deg, #0B1220 0%, #161F2E 45%, #1B2536 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.04) inset,
    0 18px 42px rgba(11, 18, 32, 0.18);
  isolation: isolate;
}

.hero-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}
.glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(60px);
  opacity: 0.55;
}
.glow-a {
  width: 280px;
  height: 280px;
  top: -110px;
  right: -90px;
  background: radial-gradient(circle, rgba(245, 124, 0, 0.55) 0%, transparent 65%);
}
.glow-b {
  width: 220px;
  height: 220px;
  bottom: -90px;
  left: -60px;
  background: radial-gradient(circle, rgba(255, 152, 0, 0.32) 0%, transparent 65%);
}

.hero > :not(.hero-bg) { position: relative; z-index: 1; }

/* Head */
.hero-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
  margin-bottom: 18px;
}
.hh-titles { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.hh-title {
  margin: 0;
  font-size: 19px;
  font-weight: 800;
  letter-spacing: -0.2px;
  color: #fff;
}
.hh-sub {
  margin: 0;
  font-size: 12.5px;
  color: rgba(245, 241, 236, 0.62);
}
.hh-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11.5px;
  letter-spacing: 0.3px;
  font-weight: 700;
  color: #FFD2A6;
  background: rgba(245, 124, 0, 0.16);
  border: 1px solid rgba(245, 124, 0, 0.32);
  padding: 4px 12px;
  border-radius: 999px;
  white-space: nowrap;
}
.hh-pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #F57C00;
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.22);
  animation: pulseDot 2.4s ease-in-out infinite;
}
@keyframes pulseDot {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

/* KPI row */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.kpi {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 14px;
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  min-width: 0;
  text-align: start;
  font-family: inherit;
  color: inherit;
  cursor: pointer;
  transition: background 180ms ease-out, box-shadow 180ms ease-out, transform 180ms ease-out;
}
.kpi--btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.08);
  box-shadow: inset 0 0 0 1px rgba(245, 124, 0, 0.32);
  transform: translateY(-1px);
}
.kpi--btn:focus-visible {
  outline: none;
  box-shadow:
    inset 0 0 0 1px rgba(245, 124, 0, 0.32),
    0 0 0 3px rgba(245, 124, 0, 0.45);
}
.kpi--btn:disabled {
  cursor: default;
  opacity: 0.55;
}
.kpi--btn:disabled .kpi-chev { display: none; }

.kpi-label {
  font-size: 11.5px;
  font-weight: 600;
  color: rgba(245, 241, 236, 0.62);
  letter-spacing: 0.1px;
}
.kpi-value {
  font-size: 24px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.4px;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}
.kpi-sub {
  font-size: 11.5px;
  color: rgba(255, 210, 166, 0.78);
  font-weight: 600;
}
.kpi-chev {
  position: absolute;
  top: 10px;
  inset-inline-start: 12px;
  display: inline-grid;
  place-items: center;
  width: 18px;
  height: 18px;
  border-radius: 6px;
  color: #FFD2A6;
  background: rgba(245, 124, 0, 0.14);
  opacity: 0.5;
  transition: opacity 180ms ease-out, background 180ms ease-out;
}
.kpi--btn:hover:not(:disabled) .kpi-chev,
.kpi--btn:focus-visible .kpi-chev {
  opacity: 1;
  background: rgba(245, 124, 0, 0.26);
}

/* Empty */
.hero--empty .hero-bg { opacity: 0.6; }
.hero-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 18px 8px 8px;
  text-align: center;
  color: rgba(245, 241, 236, 0.72);
}
.hero-empty svg { color: #F57C00; opacity: 0.78; }
.hero-empty p {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}
.hero-empty span {
  font-size: 12.5px;
  color: rgba(245, 241, 236, 0.55);
}

/* Insight pills */
.hero-insights {
  list-style: none;
  margin: 16px 0 0;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
}
.hero-insights li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: rgba(245, 241, 236, 0.88);
  font-weight: 600;
  line-height: 1.4;
}
.hi-spark {
  display: inline-grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border-radius: 6px;
  color: #fff;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  flex-shrink: 0;
  box-shadow: 0 3px 8px rgba(245, 124, 0, 0.32);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

@media (max-width: 720px) {
  .hero { padding: 18px 16px; }
  .kpi-row { grid-template-columns: 1fr; }
  .hh-pill { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .hh-pill-dot { animation: none; }
  .kpi { transition: none; }
}
</style>
