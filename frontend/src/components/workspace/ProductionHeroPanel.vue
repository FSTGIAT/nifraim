<template>
  <section class="hero" :class="{ 'hero--empty': isEmpty }">
    <div class="hero-bg" aria-hidden="true">
      <span class="glow glow-a"></span>
      <span class="glow glow-b"></span>
    </div>

    <header class="hero-head">
      <div class="hh-titles">
        <h3 class="hh-title">סטטוס פרודוקציה</h3>
        <div class="hh-sub-row">
          <p class="hh-sub">{{ subTitle }}</p>
          <button
            type="button"
            class="hh-upload-btn"
            title="העלאת קובץ פרודוקציה ידנית"
            aria-label="העלאת קובץ פרודוקציה ידנית"
            @click="emit('request-manual-upload')"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>
            </svg>
            <span>העלאה ידנית</span>
          </button>
        </div>
      </div>
      <span v-if="latest?.upload_date" class="hh-pill" :title="absoluteHebrew(latest.upload_date)">
        <span class="hh-pill-dot" aria-hidden="true"></span>
        מאז {{ relativeHebrew(latest.upload_date) }}
      </span>
    </header>

    <div v-if="!isEmpty" class="kpi-row">
      <article class="kpi">
        <span class="kpi-label">קבצים שנטענו</span>
        <span class="kpi-value ltr-number">{{ (landing?.files_loaded || 0).toLocaleString('he-IL') }}</span>
        <span class="kpi-sub">סך הקבצים בחשבון</span>
      </article>
      <article class="kpi">
        <span class="kpi-label">לקוחות</span>
        <span class="kpi-value ltr-number">{{ (latest?.unique_clients || 0).toLocaleString('he-IL') }}</span>
        <span class="kpi-sub">בקובץ האחרון</span>
      </article>
      <article class="kpi">
        <span class="kpi-label">מוצרים</span>
        <span class="kpi-value ltr-number">{{ (latest?.total_records || 0).toLocaleString('he-IL') }}</span>
        <span class="kpi-sub">פוליסות / קופות</span>
      </article>
      <article class="kpi">
        <span class="kpi-label">חברות</span>
        <span class="kpi-value ltr-number">{{ (latest?.companies_count || 0).toLocaleString('he-IL') }}</span>
        <span class="kpi-sub">פעילות בקובץ</span>
      </article>
    </div>

    <div v-if="!isEmpty && topClientNames.length" class="last-clients">
      <span class="lc-label">לקוחות אחרונים</span>
      <ul class="lc-list">
        <li v-for="(name, i) in topClientNames" :key="i">{{ name }}</li>
      </ul>
    </div>

    <div v-if="isEmpty" class="hero-empty">
      <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="12" y1="18" x2="12" y2="12"/>
        <line x1="9" y1="15" x2="15" y2="15"/>
      </svg>
      <p>אין היסטוריית פרודוקציה</p>
      <span>העלה קובץ פרודוקציה ראשון כדי להתחיל</span>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { relativeHebrew } from '../../utils/relativeTime.js'

const props = defineProps({
  landing: { type: Object, default: null }, // { files_loaded, latest }
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['request-manual-upload'])

const latest = computed(() => props.landing?.latest || null)

const isEmpty = computed(
  () => !props.loading && !latest.value && !(props.landing?.files_loaded),
)

const subTitle = computed(() => {
  if (props.loading) return 'טוען נתונים…'
  if (isEmpty.value) return 'אין דוח פרודוקציה עדיין'
  return 'תמונה לפי הקובץ האחרון בחשבון'
})

const topClientNames = computed(() => {
  const list = latest.value?.top_clients || []
  return list
    .map((c) => c?.name || c?.id_number)
    .filter(Boolean)
    .slice(0, 5)
})

function absoluteHebrew(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch { return '' }
}
</script>

<style scoped>
.hero {
  position: relative;
  border-radius: 20px;
  padding: 22px 24px 20px;
  overflow: hidden;
  font-family: 'Heebo', sans-serif;
  color: #F5F0E8;
  background:
    radial-gradient(140% 110% at 0% 0%, rgba(212, 178, 106, 0.18) 0%, transparent 55%),
    linear-gradient(140deg, #1B201D 0%, #232A26 45%, #2D332E 100%);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.04) inset,
    0 18px 42px rgba(11, 18, 13, 0.22);
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
  opacity: 0.5;
}
.glow-a {
  width: 280px;
  height: 280px;
  top: -110px;
  right: -90px;
  background: radial-gradient(circle, rgba(212, 178, 106, 0.45) 0%, transparent 65%);
}
.glow-b {
  width: 220px;
  height: 220px;
  bottom: -90px;
  left: -60px;
  background: radial-gradient(circle, rgba(168, 192, 158, 0.22) 0%, transparent 65%);
}

.hero > :not(.hero-bg) { position: relative; z-index: 1; }

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
  color: rgba(245, 240, 232, 0.62);
}
.hh-sub-row {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.hh-upload-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px 4px 10px;
  font-family: inherit;
  font-size: 12px;
  font-weight: 700;
  color: #E8CFA0;
  background: rgba(212, 178, 106, 0.14);
  border: 1px solid rgba(212, 178, 106, 0.32);
  border-radius: 999px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease, transform 0.15s ease;
}
.hh-upload-btn:hover {
  background: rgba(212, 178, 106, 0.26);
  border-color: rgba(212, 178, 106, 0.6);
  color: #FFE5B8;
  transform: translateY(-1px);
}
.hh-upload-btn:focus-visible {
  outline: 2px solid rgba(212, 178, 106, 0.6);
  outline-offset: 2px;
}
.hh-upload-btn svg { color: #D4B26A; }

.hh-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
  font-size: 11.5px;
  letter-spacing: 0.3px;
  font-weight: 700;
  color: #E8CFA0;
  background: rgba(212, 178, 106, 0.14);
  border: 1px solid rgba(212, 178, 106, 0.32);
  padding: 4px 12px;
  border-radius: 999px;
  white-space: nowrap;
}
.hh-pill-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #D4B26A;
  box-shadow: 0 0 0 3px rgba(212, 178, 106, 0.22);
  animation: pulseDot 2.4s ease-in-out infinite;
}
@keyframes pulseDot {
  0%, 100% { opacity: 0.7; }
  50% { opacity: 1; }
}

/* KPI row */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}
.kpi {
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
}
.kpi-label {
  font-size: 11.5px;
  font-weight: 600;
  color: rgba(245, 240, 232, 0.62);
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
  color: rgba(232, 207, 160, 0.78);
  font-weight: 600;
}

/* Last clients strip */
.last-clients {
  margin-top: 16px;
  padding: 10px 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  display: flex;
  align-items: baseline;
  gap: 10px;
  flex-wrap: wrap;
}
.lc-label {
  font-size: 11.5px;
  font-weight: 700;
  color: rgba(232, 207, 160, 0.86);
  letter-spacing: 0.1px;
  flex-shrink: 0;
}
.lc-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 0 8px;
  font-size: 13px;
  color: rgba(245, 240, 232, 0.92);
  font-weight: 600;
}
.lc-list li + li::before {
  content: '·';
  color: rgba(212, 178, 106, 0.6);
  margin-inline-end: 8px;
  font-weight: 800;
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
  color: rgba(245, 240, 232, 0.72);
}
.hero-empty svg { color: #D4B26A; opacity: 0.78; }
.hero-empty p {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: #fff;
}
.hero-empty span {
  font-size: 12.5px;
  color: rgba(245, 240, 232, 0.55);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

@media (max-width: 720px) {
  .hero { padding: 18px 16px; }
  .kpi-row { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .hh-pill { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .hh-pill-dot { animation: none; }
}
</style>
