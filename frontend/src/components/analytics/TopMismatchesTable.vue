<template>
  <div class="chart-card">
    <h3>לקוחות מובילים</h3>
    <div v-if="data.length === 0" class="empty">אין נתונים להצגה</div>
    <div v-else class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>שם</th>
            <th>ת.ז</th>
            <th class="num">סכום / יתרה</th>
            <th class="num">בפועל / עמלה</th>
            <th class="num">הפרש</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, i) in data" :key="i">
            <td>{{ item.first_name || '' }} {{ item.last_name || '' }}</td>
            <td class="ltr-number">{{ item.id_number || '—' }}</td>
            <td class="num ltr-number">{{ formatAmount(item.expected) }}</td>
            <td class="num ltr-number">{{ formatAmount(item.actual) }}</td>
            <td class="num ltr-number" :class="diffClass(item.difference)">
              {{ formatAmount(item.difference) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
defineProps({
  data: { type: Array, default: () => [] },
})

function formatAmount(val) {
  if (val == null) return '—'
  return '₪ ' + Number(val).toLocaleString('he-IL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function diffClass(val) {
  if (val == null) return ''
  return val > 0 ? 'positive' : val < 0 ? 'negative' : ''
}
</script>

<style scoped>
.chart-card {
  background: white;
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

h3 {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
  color: var(--text);
}

.table-wrap {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

thead {
  background: #F9FAFB;
}

th {
  padding: 10px 8px;
  text-align: right;
  font-weight: 600;
  font-size: 12px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}

th.num, td.num {
  text-align: left;
}

td {
  padding: 10px 8px;
  border-bottom: 1px solid #F3F4F6;
}

tr:nth-child(even) {
  background: #FAFBFC;
}

tr:hover {
  background: #EFF6FF;
}

.positive { color: var(--green); font-weight: 600; }
.negative { color: var(--red); font-weight: 600; }

.empty {
  text-align: center;
  color: var(--text-secondary);
  padding: 48px 16px;
  font-size: 14px;
}
</style>
