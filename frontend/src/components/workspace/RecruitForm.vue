<template>
  <div class="recruit-form glass-card">
    <div class="form-header">
      <div class="header-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 00-3-3.87"/>
          <path d="M16 3.13a4 4 0 010 7.75"/>
        </svg>
        <h3>רשימת מגויסים</h3>
        <span class="count-badge" v-if="rows.length">{{ rows.length }}</span>
        <span class="page-info" v-if="totalPages > 1">עמוד {{ currentPage }} מתוך {{ totalPages }}</span>
      </div>
      <div class="form-actions-top">
        <div class="search-wrap">
          <svg class="search-ico" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="חפש לפי שם או ת.ז..."
            class="search-input"
          />
          <button v-if="searchQuery" class="search-clear" @click="searchQuery = ''" title="נקה">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          </button>
        </div>
        <button class="btn-add" @click="addRow">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          <span>שורה חדשה</span>
        </button>
        <button
          class="btn-save"
          :disabled="!hasUnsaved || saving"
          @click="saveAll"
        >
          <template v-if="saving">
            <div class="btn-spinner"></div>
            <span>שומר...</span>
          </template>
          <template v-else>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
            <span>שמור</span>
          </template>
        </button>
      </div>
    </div>

    <div class="table-wrapper">
      <table>
        <thead>
          <tr>
            <th>ת.ז</th>
            <th>שם פרטי</th>
            <th>שם משפחה</th>
            <th>חברה</th>
            <th>מוצר</th>
            <th>סכום</th>
            <th class="th-action"></th>
          </tr>
        </thead>
        <TransitionGroup name="row" tag="tbody">
          <tr v-for="(row, idx) in paginatedRows" :key="row._key" :class="{ 'new-row': row._isNew }">
            <td>
              <input
                v-model="row.id_number"
                placeholder="ת.ז"
                class="cell-input ltr-input"
                dir="ltr"
              />
            </td>
            <td>
              <input v-model="row.first_name" placeholder="שם פרטי" class="cell-input" />
            </td>
            <td>
              <input v-model="row.last_name" placeholder="שם משפחה" class="cell-input" />
            </td>
            <td>
              <input v-model="row.company" placeholder="חברה" class="cell-input" />
            </td>
            <td>
              <input v-model="row.product" placeholder="מוצר" class="cell-input" />
            </td>
            <td>
              <input
                v-model.number="row.amount"
                type="number"
                placeholder="—"
                class="cell-input ltr-input"
                dir="ltr"
              />
            </td>
            <td class="td-action">
              <button class="btn-remove" @click="removeRow(row)" title="מחק">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </td>
          </tr>
        </TransitionGroup>
      </table>

      <div v-if="rows.length === 0" class="empty-state">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="color: var(--text-muted)">
          <path d="M16 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
          <circle cx="8.5" cy="7" r="4"/>
          <line x1="20" y1="8" x2="20" y2="14"/>
          <line x1="23" y1="11" x2="17" y2="11"/>
        </svg>
        <p>אין מגויסים עדיין</p>
        <button class="btn-add-first" @click="addRow">הוסף מגויס ראשון</button>
      </div>
    </div>

    <!-- Pagination -->
    <div class="pagination" v-if="totalPages > 1">
      <button class="page-btn" :disabled="currentPage === 1" @click="currentPage--">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
      </button>
      <template v-for="p in visiblePages" :key="p">
        <span v-if="p === '...'" class="page-ellipsis">...</span>
        <button v-else class="page-btn" :class="{ active: p === currentPage }" @click="currentPage = p">{{ p }}</button>
      </template>
      <button class="page-btn" :disabled="currentPage === totalPages" @click="currentPage++">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
      </button>
    </div>

    <Transition name="fade">
      <p class="error-msg" v-if="error">{{ error }}</p>
    </Transition>
    <Transition name="fade">
      <p class="success-msg" v-if="successMsg">{{ successMsg }}</p>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRecruitsStore } from '../../stores/recruits.js'

const recruitsStore = useRecruitsStore()

let keyCounter = 0
const rows = ref([])
const saving = ref(false)
const error = ref('')
const successMsg = ref('')
const currentPage = ref(1)
const pageSize = 50
const searchQuery = ref('')

const hasUnsaved = computed(() => rows.value.some(r => r._isNew && r.id_number && r.first_name && r.last_name))

// Filter rows by name/ID before pagination. New (unsaved) rows always stay visible.
const filteredRows = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return rows.value
  return rows.value.filter(r => {
    if (r._isNew) return true
    const name = `${r.first_name || ''} ${r.last_name || ''}`.toLowerCase()
    const id = String(r.id_number || '').toLowerCase()
    return name.includes(q) || id.includes(q)
  })
})

const totalPages = computed(() => Math.max(1, Math.ceil(filteredRows.value.length / pageSize)))
const pageOffset = computed(() => (currentPage.value - 1) * pageSize)
const paginatedRows = computed(() => filteredRows.value.slice(pageOffset.value, pageOffset.value + pageSize))

// Reset to page 1 whenever the search changes so results are visible
watch(searchQuery, () => { currentPage.value = 1 })

const visiblePages = computed(() => {
  const total = totalPages.value
  const cur = currentPage.value
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages = []
  pages.push(1)
  if (cur > 3) pages.push('...')
  const windowStart = Math.max(2, cur - 1)
  const windowEnd = Math.min(total - 1, Math.max(cur + 1, 4))
  for (let i = windowStart; i <= windowEnd; i++) pages.push(i)
  if (cur < total - 2) pages.push('...')
  pages.push(total)
  return pages
})

onMounted(async () => {
  await recruitsStore.fetchRecruits()
  syncFromStore()
})

watch(() => recruitsStore.recruits, () => {
  syncFromStore()
}, { deep: true })

function syncFromStore() {
  const savedRows = recruitsStore.recruits.map(r => ({
    ...r,
    _key: r.id || `key-${keyCounter++}`,
    _isNew: false,
  }))
  const newRows = rows.value.filter(r => r._isNew)
  rows.value = [...savedRows, ...newRows]
}

function addRow() {
  rows.value.push({
    _key: `new-${keyCounter++}`,
    _isNew: true,
    id_number: '',
    first_name: '',
    last_name: '',
    company: '',
    product: '',
    amount: null,
  })
}

async function removeRow(row) {
  if (!row._isNew && row.id) {
    try {
      await recruitsStore.deleteRecruit(row.id)
    } catch (e) {
      error.value = recruitsStore.error || 'שגיאה במחיקה'
      return
    }
  }
  const idx = rows.value.indexOf(row)
  if (idx !== -1) rows.value.splice(idx, 1)
}

async function saveAll() {
  error.value = ''
  successMsg.value = ''
  saving.value = true

  const newItems = rows.value.filter(r => r._isNew && r.id_number && r.first_name && r.last_name)

  if (newItems.length === 0) {
    saving.value = false
    return
  }

  try {
    const payload = newItems.map(r => ({
      id_number: r.id_number,
      first_name: r.first_name,
      last_name: r.last_name,
      company: r.company || null,
      product: r.product || null,
      amount: r.amount || null,
    }))

    await recruitsStore.createBulk(payload)
    successMsg.value = `נשמרו ${payload.length} מגויסים`
    rows.value = rows.value.filter(r => !r._isNew)
    syncFromStore()
    setTimeout(() => { successMsg.value = '' }, 3000)
  } catch (e) {
    error.value = recruitsStore.error || 'שגיאה בשמירה'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.recruit-form {
  padding: 24px;
}

.form-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--accent-violet);
}

.header-title h3 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.3px;
}

.count-badge {
  background: rgba(127, 86, 217, 0.08);
  color: var(--accent-violet);
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
}

.form-actions-top {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-wrap {
  position: relative;
  display: flex;
  align-items: center;
  width: 260px;
}
.search-ico {
  position: absolute;
  right: 10px;
  color: var(--text-secondary);
  pointer-events: none;
}
.search-input {
  width: 100%;
  padding: 8px 32px 8px 32px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card, #fff);
  color: var(--text-primary);
  font-family: inherit;
  font-size: 12px;
  outline: none;
  transition: border-color 0.2s;
}
.search-input:focus {
  border-color: var(--primary, #F57C00);
}
.search-clear {
  position: absolute;
  left: 8px;
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.search-clear:hover {
  color: var(--primary, #F57C00);
}

.btn-add {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1px dashed var(--border);
  border-radius: 8px;
  font-size: 12px;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-secondary);
  transition: all 0.25s var(--transition);
}

.btn-add:hover {
  background: rgba(127, 86, 217, 0.08);
  border-color: rgba(127, 86, 217, 0.08);
  color: var(--accent-violet);
}

.btn-save {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: linear-gradient(135deg, var(--accent-emerald), var(--green-deep));
  color: white;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  transition: all 0.3s var(--transition);
}

.btn-save:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.btn-save:hover:not(:disabled) {
  box-shadow: 0 8px 20px var(--green-light);
  transform: translateY(-1px);
}

.btn-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* Table */
.table-wrapper {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
}

thead th {
  padding: 10px 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-align: right;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--border-subtle);
}

.th-action { width: 40px; }

tbody tr {
  transition: all 0.2s;
}

tbody tr:hover {
  background: var(--border-subtle);
}

tbody td {
  padding: 3px;
  border-bottom: 1px solid var(--border-subtle);
}

.td-action { width: 40px; text-align: center; }

.new-row {
  background: rgba(127, 86, 217, 0.08);
}

.cell-input {
  width: 100%;
  padding: 9px 10px;
  border: 1px solid transparent;
  border-radius: 8px;
  font-size: 13px;
  font-family: inherit;
  color: var(--text);
  background: transparent;
  transition: all 0.2s var(--transition);
}

.cell-input:focus {
  border-color: var(--primary-light);
  background: var(--bg-surface);
  box-shadow: 0 0 0 3px var(--primary-glow);
}

.cell-input::placeholder {
  color: var(--text-muted);
  opacity: 0.5;
}

.ltr-input { text-align: left; }

.btn-remove {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  color: var(--text-muted);
  opacity: 0;
  transition: all 0.2s;
}

tr:hover .btn-remove { opacity: 1; }

.btn-remove:hover {
  background: var(--red-light);
  color: var(--red);
}

.empty-state {
  text-align: center;
  padding: 40px 24px;
  color: var(--text-muted);
}

.empty-state p {
  font-size: 14px;
  margin: 12px 0;
}

.btn-add-first {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--accent-violet);
  border: 1px dashed rgba(127, 86, 217, 0.08);
  transition: all 0.25s var(--transition);
}

.btn-add-first:hover {
  background: rgba(127, 86, 217, 0.08);
  border-color: rgba(127, 86, 217, 0.08);
}

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-subtle);
}

.page-btn {
  min-width: 34px;
  height: 34px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s var(--transition);
}

.page-btn:hover:not(:disabled) { background: var(--border-subtle); }
.page-btn.active { background: var(--primary-glow); border-color: var(--primary-light); color: var(--primary); }
.page-btn:disabled { opacity: 0.3; cursor: not-allowed; }
.page-ellipsis { color: var(--text-muted); font-size: 13px; padding: 0 4px; }

.page-info {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

/* Row transitions */
.row-enter-active { animation: slideUp 0.3s var(--transition); }
.row-leave-active { animation: fadeOut 0.2s ease-out; position: absolute; width: 100%; }
@keyframes fadeOut { to { opacity: 0; transform: translateX(20px); } }

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }

.error-msg {
  color: var(--red);
  font-size: 13px;
  margin-top: 12px;
  padding: 8px 12px;
  background: var(--red-light);
  border-radius: 8px;
  border: 1px solid var(--red-light);
}

.success-msg {
  color: var(--accent-emerald);
  font-size: 13px;
  margin-top: 12px;
  padding: 8px 12px;
  background: var(--green-light);
  border-radius: 8px;
  border: 1px solid var(--green-light);
}
</style>
