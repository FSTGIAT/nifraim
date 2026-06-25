<template>
  <div v-if="rows.length" class="crs">
    <div class="crs-head">
      <h3 class="crs-title">סיכום לפי חברה</h3>
      <span class="crs-sub">גמל + ביטוח · נפרעים מול פרודוקציה</span>
    </div>

    <div class="crs-table-wrap">
      <table class="crs-table">
        <thead>
          <tr>
            <th class="t-name">חברה</th>
            <th>מופקים</th>
            <th>תואמו</th>
            <th>לא־שולמו</th>
            <th>התקבל</th>
            <th>צפי</th>
            <th>פער</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.company" class="crs-row" @click="$emit('drill', row.company)">
            <td class="t-name">{{ row.company }}</td>
            <td><span class="ltr-number">{{ fmtInt(row.produced) }}</span></td>
            <td><span class="ltr-number">{{ fmtInt(row.matched) }}</span></td>
            <td><span class="ltr-number" :class="{ warn: row.unpaid > 0 }">{{ fmtInt(row.unpaid) }}</span></td>
            <td><span class="ltr-number">{{ fmtMoney(row.received) }}</span></td>
            <td><span class="ltr-number">{{ fmtMoney(row.expected) }}</span></td>
            <td><span class="ltr-number" :class="{ gap: row.gap > 0 }">{{ fmtMoney(row.gap) }}</span></td>
          </tr>
        </tbody>
        <tfoot v-if="totals">
          <tr class="crs-total">
            <td class="t-name">סה״כ</td>
            <td><span class="ltr-number">{{ fmtInt(totals.produced) }}</span></td>
            <td><span class="ltr-number">{{ fmtInt(totals.matched) }}</span></td>
            <td><span class="ltr-number">{{ fmtInt(totals.unpaid) }}</span></td>
            <td><span class="ltr-number">{{ fmtMoney(totals.received) }}</span></td>
            <td><span class="ltr-number">{{ fmtMoney(totals.expected) }}</span></td>
            <td><span class="ltr-number gap">{{ fmtMoney(totals.gap) }}</span></td>
          </tr>
        </tfoot>
      </table>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  summary: { type: Object, default: null }, // { companies: [...], totals: {...} }
})
defineEmits(['drill'])

const rows = computed(() => props.summary?.companies || [])
const totals = computed(() => props.summary?.totals || null)

function fmtInt(n) {
  return Number(n || 0).toLocaleString('en-US')
}
function fmtMoney(n) {
  const v = Number(n || 0)
  return '₪' + Math.round(v).toLocaleString('en-US')
}
</script>

<style scoped>
.crs {
  background: #fff;
  border: 1px solid var(--border-light, #e5e7eb);
  border-radius: 14px;
  padding: 16px 18px;
  margin-bottom: 18px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.crs-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 12px;
}
.crs-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary, #1a1a1a);
}
.crs-sub {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
}
.crs-table-wrap { overflow-x: auto; }
.crs-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: 13px;
}
.crs-table th,
.crs-table td {
  padding: 9px 8px;
  text-align: center;
  width: 92px;
  white-space: nowrap;
}
.crs-table th {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-secondary, #6b7280);
  border-bottom: 1px solid var(--border-light, #e5e7eb);
}
.crs-table th.t-name,
.crs-table td.t-name {
  text-align: start;
  width: 150px;
  font-weight: 600;
  color: var(--text-primary, #1a1a1a);
  overflow: hidden;
  text-overflow: ellipsis;
}
.crs-row { cursor: pointer; transition: background 0.12s ease; }
.crs-row:hover { background: rgba(245, 124, 0, 0.05); }
.crs-row td { border-bottom: 1px solid var(--border-faint, #f1f1f3); }
.ltr-number.warn { color: #b45309; font-weight: 600; }
.ltr-number.gap { color: var(--red-deep, #b91c1c); font-weight: 700; }
.crs-total td {
  border-top: 2px solid var(--border-light, #e5e7eb);
  font-weight: 700;
  color: var(--text-primary, #1a1a1a);
  padding-top: 11px;
}
</style>
