<template>
  <div class="agents-card">
    <div class="card-head">
      <h2>סוכנים בסוכנות</h2>
      <span class="hint">לחץ על סוכן כדי להיכנס לתיק שלו</span>
    </div>
    <div v-if="!agents.length" class="empty">
      אין סוכנים בסוכנות עדיין. שלחו הזמנות מהפאנל.
    </div>
    <table v-else class="agents-table">
      <thead>
        <tr>
          <th>סוכן</th>
          <th class="num">לא שולם</th>
          <th class="num">פוליסות חוסר</th>
          <th class="num">סך פרמיה</th>
          <th class="num">לקוחות</th>
          <th>העלאה אחרונה</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="row in agents"
          :key="row.user_id"
          :class="{ 'no-data': !row.has_production, clickable: true }"
          @click="$emit('view', row)"
        >
          <td class="name">
            <span class="avatar">{{ initials(row.full_name) }}</span>
            <div class="name-block">
              <div class="name-line">{{ row.full_name }}</div>
              <div class="email">{{ row.email }}</div>
            </div>
          </td>
          <td class="num lost"><span class="ltr-number">{{ formatCurrency(row.lost_money_amount) }}</span></td>
          <td class="num"><span class="ltr-number">{{ row.lost_money_policy_count.toLocaleString('he-IL') }}</span></td>
          <td class="num"><span class="ltr-number">{{ formatCurrency(row.total_premium) }}</span></td>
          <td class="num"><span class="ltr-number">{{ row.unique_clients.toLocaleString('he-IL') }}</span></td>
          <td class="muted">{{ formatDate(row.last_upload_at) }}</td>
          <td class="actions" @click.stop>
            <button
              class="btn-upload-as"
              :title="`העלה קובץ עבור ${row.full_name}`"
              @click="$emit('uploadAs', row)"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              העלה לסוכן זה
            </button>
            <button class="btn-view" @click="$emit('view', row)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                <circle cx="12" cy="12" r="3"/>
              </svg>
              צפה בפירוט
            </button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  agents: { type: Array, required: true },
})
defineEmits(['view', 'uploadAs'])

function initials(name) {
  if (!name) return '?'
  return name.split(/\s+/).slice(0, 2).map((p) => p[0] || '').join('').toUpperCase()
}
function formatCurrency(v) {
  if (v == null) return '—'
  return '₪ ' + Math.round(Number(v)).toLocaleString('he-IL')
}
function formatDate(iso) {
  if (!iso) return 'לא הועלה'
  const d = new Date(iso)
  return d.toLocaleDateString('he-IL', { day: '2-digit', month: 'short', year: 'numeric' })
}
</script>

<style scoped>
.agents-card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}
.card-head { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 16px; }
.card-head h2 { font-size: 18px; font-weight: 700; color: var(--text); }
.hint { font-size: 12px; color: var(--text-muted); }
.empty { padding: 40px; text-align: center; color: var(--text-muted); }
.agents-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.agents-table th {
  text-align: right;
  font-weight: 600;
  font-size: 12px;
  color: var(--text-muted);
  padding: 10px 8px;
  border-bottom: 1px solid var(--border-subtle);
}
.agents-table td {
  padding: 14px 8px;
  border-bottom: 1px solid var(--border-subtle);
}
.agents-table tr:last-child td { border-bottom: none; }
.agents-table tr.no-data td.lost { color: var(--text-muted); }
.num { text-align: center; }
.name { display: flex; align-items: center; gap: 12px; }
.avatar {
  width: 36px; height: 36px; border-radius: 50%;
  background: var(--primary-light);
  color: var(--primary-deep);
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 700; font-size: 13px;
}
.name-line { font-weight: 600; color: var(--text); }
.email { font-size: 12px; color: var(--text-muted); }
td.lost .ltr-number { color: #8C1D2A; font-weight: 700; }
td.muted { color: var(--text-muted); font-size: 12px; }
tr.clickable { cursor: pointer; transition: background .12s; }
tr.clickable:hover td { background: rgba(245, 124, 0, 0.04); }

.actions { display: flex; gap: 6px; justify-content: flex-end; }
.btn-view {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--primary); color: #fff; border: none; border-radius: 8px;
  padding: 8px 14px; font-size: 13px; font-weight: 700; cursor: pointer;
  transition: background .15s;
}
.btn-view:hover { background: var(--primary-deep); }
.btn-upload-as {
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg);
  color: var(--text-secondary);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 7px 12px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  transition: all .15s;
}
.btn-upload-as:hover {
  background: var(--primary-light);
  color: var(--primary-deep);
  border-color: var(--primary);
}
.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }
</style>
