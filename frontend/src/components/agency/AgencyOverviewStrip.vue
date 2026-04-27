<template>
  <div class="overview-strip">
    <div class="kpi lost" @click="$emit('drill', 'lost')">
      <div class="kpi-label">כסף אבוד — סוכנות</div>
      <div class="kpi-value ltr-number">{{ formatCurrency(d.lost_money_amount) }}</div>
      <div class="kpi-sub">{{ d.lost_money_policy_count.toLocaleString('he-IL') }} פוליסות</div>
    </div>
    <div class="kpi top-company" @click="$emit('drill', 'lost')">
      <div class="kpi-label">חברה משלמת בעיתית</div>
      <div class="kpi-value top-company-name">{{ d.top_lost_company.name || '—' }}</div>
      <div class="kpi-sub ltr-number">{{ formatCurrency(d.top_lost_company.amount) }} אבוד</div>
    </div>
    <div class="kpi premium">
      <div class="kpi-label">סך פרמיה</div>
      <div class="kpi-value ltr-number">{{ formatCurrency(d.total_premium) }}</div>
      <div class="kpi-sub">{{ d.unique_clients.toLocaleString('he-IL') }} לקוחות</div>
    </div>
    <div class="kpi accumulation">
      <div class="kpi-label">סך צבירה</div>
      <div class="kpi-value ltr-number">{{ formatCurrency(d.total_accumulation) }}</div>
      <div class="kpi-sub">בכלל הסוכנים</div>
    </div>
    <div class="kpi agents" @click="$emit('drill', 'agents')">
      <div class="kpi-label">סוכנים</div>
      <div class="kpi-value">{{ d.agent_count }}</div>
      <div class="kpi-sub">{{ d.agents_with_data }} עם פרודוקציה</div>
    </div>
    <div class="kpi bonus" @click="$emit('drill', 'bonus')">
      <div class="kpi-label">בונוסי תפוקה השנה</div>
      <div class="kpi-value">{{ d.bonus_paid_this_year }} / {{ d.bonus_total_this_year }}</div>
      <div class="kpi-sub">שולמו / סה"כ</div>
    </div>
  </div>
</template>

<script setup>
defineProps({ d: { type: Object, required: true } })
defineEmits(['drill'])

function formatCurrency(v) {
  if (v == null) return '—'
  return '₪ ' + Math.round(Number(v)).toLocaleString('he-IL')
}
</script>

<style scoped>
.overview-strip {
  display: grid;
  grid-template-columns: repeat(6, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}
.kpi {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 18px 20px;
  cursor: pointer;
  transition: transform .25s var(--transition), box-shadow .25s var(--transition);
  border-top: 3px solid var(--border-subtle);
  position: relative;
  overflow: hidden;
}
.kpi:hover { transform: translateY(-3px); box-shadow: var(--shadow-lg); }
.kpi-label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
  margin-bottom: 8px;
}
.kpi-value {
  font-size: 26px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.5px;
  line-height: 1.1;
}
.kpi-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 6px;
}
.kpi.lost { border-top-color: var(--red); }
.kpi.lost .kpi-value { color: var(--red-deep); }
.kpi.top-company { border-top-color: var(--accent-violet); }
.kpi.top-company .top-company-name { font-size: 18px; }
.kpi.premium { border-top-color: var(--primary); }
.kpi.accumulation { border-top-color: var(--green); }
.kpi.accumulation .kpi-value { color: var(--green-deep); }
.kpi.agents { border-top-color: var(--accent-cyan); }
.kpi.bonus { border-top-color: var(--amber); }
.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }
@media (max-width: 1100px) { .overview-strip { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 600px)  { .overview-strip { grid-template-columns: repeat(2, 1fr); } }
</style>
