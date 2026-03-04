<template>
  <div class="summary-cards">
    <div class="card matched">
      <div class="card-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4-4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M22 21v-2a4 4 0 00-3-3.87"/>
          <path d="M16 3.13a4 4 0 010 7.75"/>
        </svg>
      </div>
      <div class="card-label">לקוחות משותפים</div>
      <div class="card-value">{{ summary.matched }}</div>
    </div>
    <div class="card production">
      <div class="card-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
      </div>
      <div class="card-label">רק בפרודוקציה</div>
      <div class="card-value">{{ summary.only_in_production }}</div>
    </div>
    <div class="card commission">
      <div class="card-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="1" x2="12" y2="23"/>
          <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
        </svg>
      </div>
      <div class="card-label">רק בנפרעים</div>
      <div class="card-value">{{ summary.only_in_commission }}</div>
    </div>
    <div class="card total">
      <div class="card-icon">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4-4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 00-3-3.87"/>
          <path d="M16 3.13a4 4 0 010 7.75"/>
        </svg>
      </div>
      <div class="card-label">סה"כ לקוחות</div>
      <div class="card-value">{{ summary.total_customers }}</div>
    </div>
  </div>
  <div class="totals-bar">
    <div class="total-item">
      <span class="total-label">סה"כ פרמיה</span>
      <strong class="ltr-number total-value">{{ formatAmount(summary.total_premium) }}</strong>
    </div>
    <div class="total-divider"></div>
    <div class="total-item">
      <span class="total-label">סה"כ עמלה</span>
      <strong class="ltr-number total-value emerald">{{ formatAmount(summary.total_commission) }}</strong>
    </div>
  </div>
</template>

<script setup>
defineProps({
  summary: { type: Object, required: true },
})

function formatAmount(val) {
  if (val == null) return '—'
  return '₪ ' + Number(val).toLocaleString('he-IL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}
</script>

<style scoped>
.summary-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
  text-align: center;
  transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  position: relative;
  overflow: hidden;
}

.card::before {
  content: '';
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 0.3s;
}

.card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
}

.card:hover::before {
  opacity: 1;
}

.card-icon {
  width: 36px;
  height: 36px;
  margin: 0 auto 10px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.matched .card-icon { background: var(--primary-light); color: var(--primary); }
.production .card-icon { background: var(--amber-light); color: var(--amber); }
.commission .card-icon { background: rgba(127, 86, 217, 0.08); color: var(--accent-violet); }
.total .card-icon { background: var(--border-subtle); color: var(--text-muted); }

.card-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 6px;
  font-weight: 500;
}

.card-value {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -1px;
}

.matched { border-top: 2px solid var(--primary-light); }
.matched .card-value { color: var(--primary); }
.matched::before { background: radial-gradient(ellipse at 50% 0%, var(--primary-light), transparent 70%); }

.production { border-top: 2px solid var(--amber-light); }
.production .card-value { color: var(--amber); }
.production::before { background: radial-gradient(ellipse at 50% 0%, var(--amber-light), transparent 70%); }

.commission { border-top: 2px solid rgba(127, 86, 217, 0.08); }
.commission .card-value { color: var(--accent-violet); }
.commission::before { background: radial-gradient(ellipse at 50% 0%, rgba(127, 86, 217, 0.08), transparent 70%); }

.total { border-top: 2px solid var(--border-subtle); }
.total .card-value { color: var(--text); }
.total::before { background: radial-gradient(ellipse at 50% 0%, var(--border-subtle), transparent 70%); }

.totals-bar {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 14px 20px;
  background: var(--bg-surface);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md, 12px);
  margin-bottom: 20px;
}

.total-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.total-label {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 500;
}

.total-value {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.total-value.emerald {
  color: var(--green);
}

.total-divider {
  width: 1px;
  height: 24px;
  background: var(--border-subtle);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

@media (max-width: 768px) {
  .summary-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
