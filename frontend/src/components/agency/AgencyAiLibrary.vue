<template>
  <div class="lib">
    <div class="lib-header">
      <h2>ספריית AI — מבט סוכנות</h2>
      <p class="muted">כל מה שעוזר ה-AI של הסוכנות "יודע" — מצטבר על-פני כל הסוכנים בסוכנות.</p>
    </div>

    <div v-if="loading" class="state">טוען ידע…</div>
    <div v-else-if="!data" class="state empty">אין נתונים זמינים. לחצו "רענן".</div>
    <div v-else class="lib-grid">
      <!-- Reconciliation gaps -->
      <section class="lib-card">
        <h3>פערי פיוס לפי חברה משלמת</h3>
        <ul class="lib-list">
          <li v-for="r in (data.reconciliation?.by_company || []).slice(0, 8)" :key="r.company">
            <span class="lib-label">{{ r.company }}</span>
            <span class="lib-num lost ltr-number">{{ formatCurrency(r.amount) }}</span>
            <span class="lib-sub">{{ r.policies }} פוליסות</span>
          </li>
          <li v-if="!(data.reconciliation?.by_company || []).length" class="empty">
            (אין כרגע פערים)
          </li>
        </ul>
      </section>

      <!-- Bonus pipeline -->
      <section class="lib-card">
        <h3>צינור בונוסים — {{ data.bonus?.year }}</h3>
        <div class="bonus-summary">
          <strong>{{ data.bonus?.totals?.paid || 0 }}</strong> מתוך
          <strong>{{ data.bonus?.totals?.total || 0 }}</strong> שולמו.
        </div>
        <ul class="lib-list">
          <li v-for="(r, idx) in (data.bonus?.rows || []).filter((x) => !x.is_paid).slice(0, 8)" :key="idx">
            <span class="lib-label">{{ r.agent_name }}</span>
            <span class="lib-sub">{{ r.company }} — ⏳ ממתין</span>
          </li>
          <li v-if="!(data.bonus?.rows || []).some((x) => !x.is_paid)" class="empty">
            כל הבונוסים שולמו 🎉
          </li>
        </ul>
      </section>

      <!-- Top agents (positive performers) -->
      <section class="lib-card">
        <h3>סוכנים מובילים בפרמיה</h3>
        <ul class="lib-list">
          <li v-for="r in topByPremium" :key="r.user_id">
            <span class="lib-label">{{ r.full_name }}</span>
            <span class="lib-num ltr-number">{{ formatCurrency(r.total_premium) }}</span>
            <span class="lib-sub">{{ r.unique_clients }} לקוחות</span>
          </li>
          <li v-if="!topByPremium.length" class="empty">(אין נתונים)</li>
        </ul>
      </section>

      <!-- Stale data -->
      <section class="lib-card">
        <h3>סוכנים ללא העלאה אחרונה</h3>
        <ul class="lib-list">
          <li v-for="r in staleAgents" :key="r.user_id">
            <span class="lib-label">{{ r.full_name }}</span>
            <span class="lib-sub">{{ r.has_production ? lastUploadAgo(r.last_upload_at) : 'לא העלו פרודוקציה' }}</span>
          </li>
          <li v-if="!staleAgents.length" class="empty">כולם עדכניים 👍</li>
        </ul>
      </section>
    </div>

    <div class="lib-actions">
      <button class="btn-refresh" @click="$emit('refresh')" :disabled="loading">
        {{ loading ? 'טוען...' : 'רענן' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})
defineEmits(['refresh'])

const topByPremium = computed(() =>
  [...(props.data?.agent_leaderboard || [])]
    .sort((a, b) => (b.total_premium || 0) - (a.total_premium || 0))
    .slice(0, 8)
)

const staleAgents = computed(() =>
  (props.data?.agent_leaderboard || [])
    .filter((r) => !r.has_production || daysSince(r.last_upload_at) > 30)
    .slice(0, 8)
)

function daysSince(iso) {
  if (!iso) return Infinity
  return Math.floor((Date.now() - new Date(iso).getTime()) / (1000 * 60 * 60 * 24))
}
function lastUploadAgo(iso) {
  if (!iso) return 'לא הועלה'
  const d = daysSince(iso)
  if (d === 0) return 'היום'
  if (d === 1) return 'אתמול'
  return `לפני ${d} ימים`
}
function formatCurrency(v) {
  if (v == null) return '—'
  return '₪ ' + Math.round(Number(v)).toLocaleString('he-IL')
}
</script>

<style scoped>
.lib { padding: 24px 0; }
.lib-header { margin-bottom: 20px; }
.lib-header h2 { font-size: 22px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
.muted { color: var(--text-muted); font-size: 13.5px; }
.state { padding: 60px; text-align: center; color: var(--text-muted); }
.state.empty { color: var(--text-muted); }
.lib-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 18px;
}
.lib-card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}
.lib-card h3 { font-size: 15px; font-weight: 700; color: var(--text); margin-bottom: 12px; }
.bonus-summary { font-size: 14px; color: var(--text-secondary); margin-bottom: 12px; }
.lib-list { list-style: none; padding: 0; margin: 0; }
.lib-list li {
  display: grid;
  grid-template-columns: 1fr auto;
  align-items: baseline;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-subtle);
  font-size: 13.5px;
}
.lib-list li:last-child { border-bottom: none; }
.lib-label { color: var(--text); font-weight: 600; }
.lib-num { color: var(--text); font-weight: 700; font-size: 13px; }
.lib-num.lost { color: var(--red-deep); }
.lib-sub { grid-column: 1 / -1; color: var(--text-muted); font-size: 11.5px; margin-top: -4px; }
.lib-list li.empty { color: var(--text-muted); font-style: italic; grid-template-columns: 1fr; }
.lib-actions { margin-top: 20px; text-align: center; }
.btn-refresh {
  background: var(--primary);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 8px 24px;
  font-size: 13.5px;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s;
}
.btn-refresh:hover:not(:disabled) { background: var(--primary-deep); }
.btn-refresh:disabled { opacity: 0.5; cursor: wait; }
.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }
@media (max-width: 900px) { .lib-grid { grid-template-columns: 1fr; } }
</style>
