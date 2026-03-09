<template>
  <div class="product-table-card">
    <h3>המוצרים שלך</h3>
    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th @click="sortBy('product')">
              מוצר
              <span v-if="sortKey === 'product'" class="sort-arrow">{{ sortAsc ? '▲' : '▼' }}</span>
            </th>
            <th>סוג</th>
            <th @click="sortBy('receiving_company')">
              חברה
              <span v-if="sortKey === 'receiving_company'" class="sort-arrow">{{ sortAsc ? '▲' : '▼' }}</span>
            </th>
            <th @click="sortBy('track')">
              אפיק השקעה
              <span v-if="sortKey === 'track'" class="sort-arrow">{{ sortAsc ? '▲' : '▼' }}</span>
            </th>
            <th @click="sortBy('total_premium')">
              פרמיה
              <span v-if="sortKey === 'total_premium'" class="sort-arrow">{{ sortAsc ? '▲' : '▼' }}</span>
            </th>
            <th @click="sortBy('accumulation')">
              צבירה
              <span v-if="sortKey === 'accumulation'" class="sort-arrow">{{ sortAsc ? '▲' : '▼' }}</span>
            </th>
            <th>סטטוס</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(p, i) in sortedProducts" :key="i">
            <td>{{ p.product || '—' }}</td>
            <td>{{ p.product_type || '—' }}</td>
            <td>{{ p.receiving_company || '—' }}</td>
            <td>{{ p.track || '—' }}</td>
            <td class="ltr-number">{{ p.total_premium ? formatNum(p.total_premium) : '—' }}</td>
            <td class="ltr-number">{{ p.accumulation ? formatNum(p.accumulation) : '—' }}</td>
            <td>
              <span class="status-badge" :class="statusClass(p.product_status)">
                {{ p.product_status || '—' }}
              </span>
            </td>
          </tr>
          <tr v-if="!products.length">
            <td colspan="7" class="empty">אין מוצרים להצגה</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  products: Array,
})

const sortKey = ref('receiving_company')
const sortAsc = ref(true)

function sortBy(key) {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value
  } else {
    sortKey.value = key
    sortAsc.value = true
  }
}

const sortedProducts = computed(() => {
  const arr = [...(props.products || [])]
  arr.sort((a, b) => {
    const va = a[sortKey.value] ?? ''
    const vb = b[sortKey.value] ?? ''
    const cmp = typeof va === 'number' ? va - vb : String(va).localeCompare(String(vb), 'he')
    return sortAsc.value ? cmp : -cmp
  })
  return arr
})

function formatNum(val) {
  return new Intl.NumberFormat('he-IL', { maximumFractionDigits: 0 }).format(val)
}

function statusClass(status) {
  if (!status) return ''
  if (status === 'פעיל') return 'active'
  if (status === 'מבוטל') return 'cancelled'
  return ''
}
</script>

<style scoped>
.product-table-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
}

h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  padding: 16px 20px 12px;
  margin: 0;
}

.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

thead th {
  padding: 10px 14px;
  text-align: right;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--bg);
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
  white-space: nowrap;
  user-select: none;
}

thead th:hover { color: var(--text-secondary); }

.sort-arrow { font-size: 10px; margin-right: 4px; }

tbody td {
  padding: 12px 14px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

tbody tr:last-child td { border-bottom: none; }

tbody tr:hover { background: var(--glass-hover); }

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  text-align: left;
}

.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.status-badge.active {
  background: var(--green-light);
  color: var(--green);
}

.status-badge.cancelled {
  background: var(--red-light);
  color: var(--red);
}

.empty {
  text-align: center;
  color: var(--text-muted);
  padding: 32px !important;
}
</style>
