<template>
  <div class="summary-cards">
    <div class="card blue">
      <div class="card-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      </div>
      <div class="card-body">
        <div class="card-value ltr-number">{{ summary.matched + summary.paid_match + summary.paid_mismatch }}</div>
        <div class="card-label">נמצא בשני הקבצים</div>
      </div>
    </div>
    <div class="card orange">
      <div class="card-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <div class="card-body">
        <div class="card-value ltr-number">{{ summary.missing_from_report }}</div>
        <div class="card-label">חסר בדוח חברה</div>
      </div>
    </div>
    <div class="card purple">
      <div class="card-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/>
          <line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
      </div>
      <div class="card-body">
        <div class="card-value ltr-number">{{ summary.extra_in_report }}</div>
        <div class="card-label">חסר בקובץ סוכן</div>
      </div>
    </div>
    <div class="card gray">
      <div class="card-icon">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4-4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 00-3-3.87"/>
          <path d="M16 3.13a4 4 0 010 7.75"/>
        </svg>
      </div>
      <div class="card-body">
        <div class="card-value ltr-number">{{ summary.total }}</div>
        <div class="card-label">סה"כ רשומות</div>
      </div>
    </div>
  </div>
  <div class="totals-bar" v-if="summary.total > 0">
    <div class="total-item">
      <span class="total-label">סה"כ צפוי:</span>
      <span class="total-value ltr-number">{{ formatCurrency(summary.total_expected) }}</span>
    </div>
    <div class="total-divider"></div>
    <div class="total-item">
      <span class="total-label">סה"כ בפועל:</span>
      <span class="total-value ltr-number">{{ formatCurrency(summary.total_actual) }}</span>
    </div>
    <div class="total-divider"></div>
    <div class="total-item">
      <span class="total-label">הפרש:</span>
      <span class="total-value ltr-number" :class="{ negative: summary.total_difference < 0 }">
        {{ formatCurrency(summary.total_difference) }}
      </span>
    </div>
  </div>
</template>

<script setup>
defineProps({
  summary: { type: Object, required: true },
})

function formatCurrency(val) {
  if (val == null) return '—'
  return '₪ ' + Number(val).toLocaleString('he-IL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<style scoped>
.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border-top: 2px solid transparent;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  animation: fadeInUp 0.4s ease both;
}

.card:nth-child(1) { animation-delay: 0s; }
.card:nth-child(2) { animation-delay: 0.06s; }
.card:nth-child(3) { animation-delay: 0.12s; }
.card:nth-child(4) { animation-delay: 0.18s; }

.blue { border-top-color: var(--primary-light); }
.orange { border-top-color: var(--amber-light); }
.purple { border-top-color: rgba(127, 86, 217, 0.08); }
.gray { border-top-color: var(--border-subtle); }

.card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.card-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.blue .card-icon { background: var(--primary-light); color: var(--primary); }
.orange .card-icon { background: var(--amber-light); color: var(--amber); }
.purple .card-icon { background: rgba(127, 86, 217, 0.08); color: var(--accent-violet); }
.gray .card-icon { background: var(--border-subtle); color: var(--text-muted); }

.card-value {
  font-size: 28px;
  font-weight: 800;
  line-height: 1;
  color: var(--text);
}

.card-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 4px;
}

.totals-bar {
  display: flex;
  gap: 24px;
  align-items: center;
  background: var(--bg-surface);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md, 12px);
  padding: 14px 24px;
  margin-top: 12px;
  animation: fadeInUp 0.4s ease 0.24s both;
}

.total-item {
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.total-label {
  font-size: 13px;
  color: var(--text-muted);
}

.total-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.total-value.negative {
  color: var(--red);
}

.total-divider {
  width: 1px;
  height: 24px;
  background: var(--border-subtle);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
}

@media (max-width: 768px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }
  .totals-bar {
    flex-direction: column;
    gap: 8px;
  }
  .total-divider {
    display: none;
  }
}
</style>
