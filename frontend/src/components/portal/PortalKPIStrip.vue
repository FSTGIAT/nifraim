<template>
  <div class="kpi-strip">
    <div class="kpi-card">
      <div class="kpi-icon" style="background: var(--primary-light); color: var(--primary);">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 16V8a2 2 0 00-1-1.73l-7-4a2 2 0 00-2 0l-7 4A2 2 0 003 8v8a2 2 0 001 1.73l7 4a2 2 0 002 0l7-4A2 2 0 0021 16z"/>
        </svg>
      </div>
      <div class="kpi-info">
        <span class="kpi-value ltr-number">{{ kpi.product_count }}</span>
        <span class="kpi-label">מוצרים</span>
      </div>
    </div>

    <div class="kpi-card">
      <div class="kpi-icon" style="background: var(--green-light); color: var(--green);">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="1" x2="12" y2="23"/>
          <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
        </svg>
      </div>
      <div class="kpi-info">
        <span class="kpi-value ltr-number">{{ formatCurrency(kpi.total_premium) }}</span>
        <span class="kpi-label">פרמיה חודשית</span>
      </div>
    </div>

    <div class="kpi-card">
      <div class="kpi-icon" style="background: rgba(127,86,217,0.1); color: var(--accent-violet);">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
          <polyline points="17 6 23 6 23 12"/>
        </svg>
      </div>
      <div class="kpi-info">
        <span class="kpi-value ltr-number">{{ formatCurrency(kpi.total_accumulation) }}</span>
        <span class="kpi-label">צבירה כוללת</span>
      </div>
    </div>

    <div class="kpi-card">
      <div class="kpi-icon" style="background: var(--amber-light); color: var(--amber);">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
      </div>
      <div class="kpi-info">
        <span class="kpi-value ltr-number">{{ kpi.company_count }}</span>
        <span class="kpi-label">חברות ביטוח</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  kpi: Object,
})

function formatCurrency(val) {
  if (!val) return '0'
  return new Intl.NumberFormat('he-IL', { style: 'currency', currency: 'ILS', maximumFractionDigits: 0 }).format(val)
}
</script>

<style scoped>
.kpi-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

@media (max-width: 768px) {
  .kpi-strip { grid-template-columns: repeat(2, 1fr); }
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 18px 20px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}

.kpi-icon {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kpi-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kpi-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}

.kpi-label {
  font-size: 12px;
  color: var(--text-muted);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}
</style>
