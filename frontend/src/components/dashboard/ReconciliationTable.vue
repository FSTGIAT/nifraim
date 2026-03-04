<template>
  <div class="table-wrapper">
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
    </div>
    <table v-if="records.length > 0">
      <colgroup>
        <col style="width: 12%">
        <col style="width: 12%">
        <col style="width: 10%">
        <col style="width: 18%">
        <col style="width: 14%">
        <col style="width: 12%">
        <col style="width: 12%">
        <col style="width: 10%">
      </colgroup>
      <thead>
        <tr>
          <th @click="$emit('sort', 'first_name')" class="sortable">
            שם פרטי {{ sortIcon('first_name') }}
          </th>
          <th @click="$emit('sort', 'last_name')" class="sortable">
            שם משפחה {{ sortIcon('last_name') }}
          </th>
          <th @click="$emit('sort', 'id_number')" class="sortable">
            ת.ז {{ sortIcon('id_number') }}
          </th>
          <th>מוצר</th>
          <th @click="$emit('sort', 'receiving_company')" class="sortable">
            חברה {{ sortIcon('receiving_company') }}
          </th>
          <th @click="$emit('sort', 'expected_amount')" class="sortable num">
            סכום {{ sortIcon('expected_amount') }}
          </th>
          <th class="num">
            עמלה
          </th>
          <th @click="$emit('sort', 'reconciliation_status')" class="sortable">
            סטטוס {{ sortIcon('reconciliation_status') }}
          </th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="record in records"
          :key="record.id"
          @click="record.id_number && $emit('client-click', record.id_number)"
          :class="{ clickable: record.id_number }"
        >
          <td>{{ record.first_name || '—' }}</td>
          <td>{{ record.last_name || '—' }}</td>
          <td class="ltr-number">{{ record.id_number || '—' }}</td>
          <td class="truncate" :title="record.product">{{ truncate(record.product, 20) }}</td>
          <td>{{ record.receiving_company || '—' }}</td>
          <td class="num ltr-number">{{ formatAmount(mainAmount(record)) }}</td>
          <td class="num ltr-number">{{ formatAmount(commissionAmount(record)) }}</td>
          <td>
            <StatusBadge :status="record.reconciliation_status || 'no_data'" />
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else-if="!loading" class="empty">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
      <p>אין רשומות להצגה</p>
      <p class="hint">העלה קובץ Excel כדי להתחיל</p>
    </div>
  </div>
</template>

<script setup>
import StatusBadge from './StatusBadge.vue'

const props = defineProps({
  records: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  sortBy: { type: String, default: '' },
  sortDir: { type: String, default: 'asc' },
})

defineEmits(['sort', 'client-click'])

function mainAmount(r) {
  return r.expected_amount != null ? r.expected_amount : r.balance
}

function commissionAmount(r) {
  return r.commission_paid != null ? r.commission_paid : r.actual_amount
}

function sortIcon(col) {
  if (props.sortBy !== col) return ''
  return props.sortDir === 'asc' ? '▲' : '▼'
}

function formatAmount(val) {
  if (val == null) return '—'
  return '₪ ' + Number(val).toLocaleString('he-IL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function truncate(str, len) {
  if (!str) return '—'
  return str.length > len ? str.slice(0, len) + '...' : str
}
</script>

<style scoped>
.table-wrapper {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  overflow-x: auto;
  position: relative;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: inherit;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  table-layout: fixed;
}

thead {
  background: var(--bg);
}

th {
  padding: 12px 10px;
  text-align: right;
  font-weight: 600;
  font-size: 12px;
  color: var(--text-muted);
  border-bottom: 1px solid var(--glass-border);
  white-space: nowrap;
  user-select: none;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

th.sortable {
  cursor: pointer;
  transition: color 0.2s;
}

th.sortable:hover {
  color: var(--primary);
}

th.num,
td.num {
  text-align: left;
}

td {
  padding: 12px 10px;
  border-bottom: 1px solid var(--border-subtle);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--text);
}

tbody tr:nth-child(even) {
  background: rgba(255, 255, 255, 0.015);
}

tr.clickable {
  cursor: pointer;
  transition: background 0.2s;
}

tr.clickable:hover {
  background: var(--primary-light) !important;
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
}

.truncate {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty {
  text-align: center;
  padding: 56px 16px;
  color: var(--text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.empty .hint {
  font-size: 13px;
  color: var(--text-muted);
}
</style>
