<template>
  <Teleport to="body">
    <Transition name="dm">
      <div v-if="open" class="dm-overlay" @click.self="$emit('close')">
        <div class="dm-card" role="dialog" aria-modal="true">
          <header class="dm-head">
            <div>
              <h3 class="dm-title">{{ title }}</h3>
              <p class="dm-sub">{{ subtitle }}</p>
            </div>
            <button class="dm-x" @click="$emit('close')" aria-label="סגור">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
              </svg>
            </button>
          </header>

          <div class="dm-body">
            <div v-if="!items.length" class="dm-empty">אין נתונים להצגה.</div>
            <table v-else class="dm-table">
              <thead>
                <tr>
                  <th>{{ labelHeader }}</th>
                  <th class="num">סכום</th>
                  <th class="num">חיובים</th>
                  <th class="meta">פירוט</th>
                  <th class="since">מאז</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="(item, i) in items" :key="i">
                  <tr
                    class="dm-row"
                    :class="{ 'dm-row--expandable': canExpand, 'dm-row--open': isExpanded(i) }"
                    @click="canExpand && toggleRow(i, item)"
                  >
                    <td class="dm-label">
                      <span class="dm-rank">{{ i + 1 }}</span>
                      <span class="dm-label-text">{{ item.label }}</span>
                      <svg
                        v-if="canExpand"
                        class="dm-caret"
                        :class="{ 'dm-caret--open': isExpanded(i) }"
                        width="12" height="12" viewBox="0 0 24 24"
                        fill="none" stroke="currentColor" stroke-width="2.4"
                        stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"
                      >
                        <path d="M6 9l6 6 6-6"/>
                      </svg>
                    </td>
                    <td class="num bold">
                      <span class="ltr-number">{{ formatShekel(item.amount) }}</span>
                    </td>
                    <td class="num">
                      <span class="ltr-number">{{ (item.count ?? 0).toLocaleString('he-IL') }}</span>
                    </td>
                    <td class="meta">{{ item.meta || '—' }}</td>
                    <td class="since">
                      <span v-if="item.since" class="since-pill" :title="absoluteHebrew(item.since)">
                        {{ relativeHebrew(item.since) }}
                      </span>
                      <span v-else class="since-empty">—</span>
                    </td>
                  </tr>

                  <tr v-if="canExpand && isExpanded(i)" class="dm-detail-row">
                    <td colspan="5" class="dm-detail-cell">
                      <div v-if="detail[i]?.loading" class="dm-detail-loading">טוען פרטים…</div>
                      <div v-else-if="detail[i]?.error" class="dm-detail-error">{{ detail[i].error }}</div>
                      <div v-else-if="!detail[i]?.rows?.length" class="dm-detail-empty">אין שורות פתוחות.</div>
                      <table v-else class="dm-detail-table">
                        <thead>
                          <tr>
                            <th>{{ kind === 'company' ? 'לקוח' : 'חברה' }}</th>
                            <th>מוצר / פוליסה</th>
                            <th class="num">סכום</th>
                            <th class="since">מאז</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="row in detail[i].rows" :key="row.id">
                            <td>{{ kind === 'company' ? (row.customer_name || row.customer_id_number) : row.company_name }}</td>
                            <td class="policy">
                              <span class="policy-product">{{ row.product || '—' }}</span>
                              <span v-if="row.policy_number" class="policy-num ltr-number">{{ row.policy_number }}</span>
                            </td>
                            <td class="num bold">
                              <span class="ltr-number">{{ formatShekel(row.expected_amount) }}</span>
                            </td>
                            <td class="since">
                              <span class="since-pill" :title="absoluteHebrew(row.created_at)">
                                {{ relativeHebrew(row.created_at) }}
                              </span>
                            </td>
                          </tr>
                        </tbody>
                      </table>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, reactive, watch } from 'vue'
import api from '../../api/client.js'
import { relativeHebrew } from '../../utils/relativeTime.js'

const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  labelHeader: { type: String, default: 'שם' },
  items: { type: Array, default: () => [] },
  // 'company' | 'customer' | null. When null, rows are not expandable.
  kind: { type: String, default: null },
  // gemel_hishtalmut | insurance — needed to scope the per-row /debts fetch.
  category: { type: String, default: null },
})
const emit = defineEmits(['close', 'drill-customer'])

const detail = reactive({})

const canExpand = computed(() => !!props.kind)

function isExpanded(i) {
  return !!detail[i]?.open
}

async function toggleRow(i, item) {
  if (!canExpand.value) return
  // Customer rows drill out to the full CustomerDetailModal — parent handles
  // hydration. Company rows expand inline (the underlying debts table).
  if (props.kind === 'customer') {
    const idNumber = item.raw?.id_number
    if (!idNumber) return
    emit('drill-customer', { idNumber, item })
    return
  }
  if (detail[i]?.open) {
    detail[i].open = false
    return
  }
  // Already fetched? Just re-open.
  if (detail[i]?.rows) {
    detail[i].open = true
    return
  }
  detail[i] = { open: true, loading: true, rows: null, error: null }
  try {
    const params = { status: 'open' }
    if (props.category) params.category = props.category
    if (props.kind === 'company') params.company = item.label
    const res = await api.get('/debts', { params })
    detail[i].rows = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    detail[i].error = 'שגיאה בטעינת הפרטים'
  } finally {
    detail[i].loading = false
  }
}

// Reset expansion state when the modal closes or items change.
watch(() => props.open, (v) => { if (!v) Object.keys(detail).forEach(k => delete detail[k]) })
watch(() => props.items, () => { Object.keys(detail).forEach(k => delete detail[k]) })

function formatShekel(n) {
  if (n === null || n === undefined || isNaN(n)) return '—'
  return Number(n).toLocaleString('he-IL', { style: 'currency', currency: 'ILS', maximumFractionDigits: 0 })
}
function absoluteHebrew(iso) {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleDateString('he-IL', { day: '2-digit', month: '2-digit', year: 'numeric' })
  } catch { return '' }
}
</script>

<style scoped>
.dm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 12, 6, 0.36);
  backdrop-filter: blur(4px);
  z-index: 1100;
  display: grid;
  place-items: center;
  padding: 24px;
}
.dm-card {
  background: #fff;
  border-radius: 16px;
  width: min(820px, 100%);
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 60px rgba(17, 12, 6, 0.18);
  font-family: 'Heebo', sans-serif;
}
.dm-card::before {
  content: '';
  display: block;
  height: 3px;
  background: linear-gradient(90deg, transparent, #F57C00, transparent);
}
.dm-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--border-subtle);
}
.dm-title { margin: 0; font-size: 16px; font-weight: 800; color: var(--text); }
.dm-sub { margin: 2px 0 0; font-size: 12px; color: var(--text-muted); }
.dm-x {
  width: 28px; height: 28px;
  display: grid; place-items: center;
  border: 1px solid var(--border-subtle);
  background: transparent;
  border-radius: 8px;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.dm-x:hover { background: var(--bg); color: var(--text); }

.dm-body { overflow-y: auto; padding: 4px 20px 20px; }
.dm-empty { padding: 30px; text-align: center; color: var(--text-muted); font-size: 13px; }

.dm-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.dm-table th, .dm-table td {
  padding: 10px 8px;
  text-align: start;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.06);
}
.dm-table th {
  font-weight: 700;
  color: var(--text-muted);
  font-size: 11.5px;
  background: var(--bg);
  position: sticky;
  top: 0;
  z-index: 1;
}
.dm-table td { vertical-align: middle; }
.dm-table .num { text-align: end; font-family: ui-monospace, "SF Mono", Menlo, monospace; }
.dm-table .num.bold { color: #c2410c; font-weight: 700; }
.dm-table .meta { color: var(--text-muted); font-size: 12px; }
.dm-table .since { white-space: nowrap; }
.dm-label { display: flex; align-items: center; gap: 8px; font-weight: 600; }
.dm-label-text { flex: 1; min-width: 0; }
.dm-rank {
  display: inline-grid;
  place-items: center;
  width: 22px; height: 22px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
}

.dm-row--expandable { cursor: pointer; }
.dm-row--expandable:hover {
  background: rgba(245, 124, 0, 0.04);
}
.dm-row--open { background: rgba(245, 124, 0, 0.06); }
.dm-caret {
  transition: transform 180ms cubic-bezier(0.16, 1, 0.3, 1);
  color: var(--text-muted);
  flex-shrink: 0;
}
.dm-caret--open { transform: rotate(180deg); color: var(--primary-deep, #c2410c); }

.since-pill {
  display: inline-block;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 700;
  color: var(--primary-deep, #c2410c);
  background: rgba(245, 124, 0, 0.08);
  border: 1px solid rgba(245, 124, 0, 0.22);
  border-radius: 999px;
}
.since-empty { color: var(--text-muted); font-size: 12px; }

/* Inline detail row */
.dm-detail-row { background: rgba(245, 124, 0, 0.025); }
.dm-detail-cell { padding: 10px 14px 16px !important; }
.dm-detail-loading,
.dm-detail-error,
.dm-detail-empty {
  padding: 16px;
  text-align: center;
  font-size: 12.5px;
  color: var(--text-muted);
}
.dm-detail-error { color: var(--red-deep, #C23934); }
.dm-detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  background: #fff;
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  overflow: hidden;
}
.dm-detail-table th,
.dm-detail-table td {
  padding: 8px 10px;
  text-align: start;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
}
.dm-detail-table th {
  font-weight: 700;
  color: var(--text-muted);
  font-size: 11px;
  background: rgba(0, 0, 0, 0.02);
}
.dm-detail-table tr:last-child td { border-bottom: none; }
.dm-detail-table .num { text-align: end; font-family: ui-monospace, "SF Mono", Menlo, monospace; }
.dm-detail-table .num.bold { color: #c2410c; font-weight: 700; }
.policy { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.policy-product { font-weight: 600; color: var(--text); }
.policy-num { font-size: 11px; color: var(--text-muted); font-family: ui-monospace, "SF Mono", Menlo, monospace; }

.dm-enter-active, .dm-leave-active { transition: opacity 0.18s ease; }
.dm-enter-active .dm-card, .dm-leave-active .dm-card { transition: transform 0.22s ease, opacity 0.22s ease; }
.dm-enter-from, .dm-leave-to { opacity: 0; }
.dm-enter-from .dm-card, .dm-leave-to .dm-card { opacity: 0; transform: translateY(8px) scale(0.98); }
</style>
