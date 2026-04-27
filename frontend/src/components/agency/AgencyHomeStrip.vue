<template>
  <section class="ag-home-strip">
    <div class="ag-greet">
      <h1>שלום {{ firstName }}<span class="wave">👋</span></h1>
      <p>{{ agencyName }} · {{ overview?.agent_count || 0 }} סוכנים פעילים בסוכנות</p>
    </div>
    <div class="ag-stats">
      <div class="g-stat">
        <span class="g-label">פרמיה</span>
        <span class="g-val ltr-number">{{ formatShort(overview?.total_premium) }}</span>
      </div>
      <div class="g-divider"></div>
      <div class="g-stat">
        <span class="g-label">לקוחות</span>
        <span class="g-val ltr-number">{{ (overview?.unique_clients || 0).toLocaleString('he-IL') }}</span>
      </div>
      <div class="g-divider"></div>
      <div class="g-stat warn">
        <span class="g-label">לא שולם</span>
        <span class="g-val ltr-number">{{ formatShort(overview?.lost_money_amount) }}</span>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  firstName: { type: String, default: 'חשב' },
  agencyName: { type: String, default: 'הסוכנות' },
  overview: { type: Object, default: null },
})

function formatShort(v) {
  if (v == null || v === 0) return '₪0'
  const n = Number(v)
  if (n >= 1_000_000) return '₪' + (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return '₪' + Math.round(n / 1_000) + 'K'
  return '₪' + Math.round(n).toLocaleString('he-IL')
}
</script>

<style scoped>
.ag-home-strip {
  display: flex; align-items: center; justify-content: space-between; gap: 18px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 18px;
  box-shadow: var(--shadow-sm);
  position: relative; z-index: 2;
}
.ag-greet h1 {
  font-size: 18px; font-weight: 700; color: var(--text);
  letter-spacing: -0.2px; margin-bottom: 2px;
}
.ag-greet .wave {
  display: inline-block; margin-right: 4px;
  animation: wave 2.4s ease-in-out infinite;
  transform-origin: 70% 70%;
}
@keyframes wave {
  0%, 100% { transform: rotate(0); }
  10%, 30% { transform: rotate(14deg); }
  20%      { transform: rotate(-8deg); }
  40%      { transform: rotate(0); }
}
.ag-greet p { font-size: 12.5px; color: var(--text-muted); }

.ag-stats {
  display: flex; align-items: center; gap: 14px;
  background: linear-gradient(180deg, #FFF8F0 0%, #FFFFFF 100%);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 8px 16px;
}
.g-stat { display: flex; flex-direction: column; align-items: flex-start; gap: 1px; }
.g-label { font-size: 10.5px; font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase; color: var(--text-muted); }
.g-val { font-size: 16px; font-weight: 800; color: var(--text); letter-spacing: -0.3px; }
.g-stat.warn .g-val { color: #8C1D2A; }
.g-divider { width: 1px; height: 24px; background: var(--border-subtle); }

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

@media (max-width: 700px) {
  .ag-home-strip { flex-direction: column; align-items: flex-start; gap: 12px; }
  .ag-stats { width: 100%; justify-content: space-between; }
}
</style>
