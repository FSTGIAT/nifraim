<template>
  <div class="rate-card">
    <div class="rate-header">
      <h3>טבלת עמלות היקף</h3>
      <div class="header-actions">
        <button v-if="rates.length === 0" class="btn-seed" @click="seedRates" :disabled="seeding">
          {{ seeding ? 'טוען...' : 'טען ברירת מחדל' }}
        </button>
        <button v-if="rates.length > 0 && !addingNew" class="btn-seed" @click="startNew">+ הוסף שורה</button>
        <label class="btn-upload">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          העלה מקובץ
          <input type="file" accept=".xlsx,.xls" @change="onFileUpload" style="display:none" />
        </label>
      </div>
    </div>

    <div v-if="rates.length === 0 && !loading" class="empty">
      לא הוגדרו עמלות היקף. לחץ "טען ברירת מחדל" או "העלה מקובץ".
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>

    <div class="table-scroll" v-if="rates.length > 0">
      <table>
        <thead>
          <tr>
            <th>חברה</th>
            <th class="num">נפרעים (%)</th>
            <th class="num">היקף</th>
            <th class="num">פנסיה צבירות</th>
            <th class="num">משונת %</th>
            <th class="num">המרה לקצבה</th>
            <th>תדירות</th>
            <th>למי</th>
            <th>הערות</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="rate in rates" :key="rate.id">
            <template v-if="editingId === rate.id">
              <td><input v-model="editForm.company_name" class="edit-input" /></td>
              <td class="num"><input v-model.number="editForm.nifraim_rate" type="number" step="0.01" class="edit-input num-input" dir="ltr" /></td>
              <td class="num"><input v-model.number="editForm.volume_rate_per_million" type="number" step="1" class="edit-input num-input" dir="ltr" /></td>
              <td class="num"><input v-model.number="editForm.pension_accumulation" type="number" step="1" class="edit-input num-input" dir="ltr" /></td>
              <td class="num"><input v-model.number="editForm.changed_percent" type="number" step="0.01" class="edit-input num-input" dir="ltr" /></td>
              <td class="num"><input v-model.number="editForm.conversion_to_annuity" type="number" step="1" class="edit-input num-input" dir="ltr" /></td>
              <td>
                <select v-model="editForm.payment_frequency" class="edit-input">
                  <option value="">—</option>
                  <option value="חודשי">חודשי</option>
                  <option value="רבעוני">רבעוני</option>
                  <option value="שנתי">שנתי</option>
                </select>
              </td>
              <td>
                <select v-model="editForm.paid_to" class="edit-input">
                  <option value="">—</option>
                  <option value="עיתים">עיתים</option>
                  <option value="סוכן">סוכן</option>
                  <option value="ידנים">ידנים</option>
                </select>
              </td>
              <td><input v-model="editForm.notes" class="edit-input" /></td>
              <td class="actions">
                <button class="btn-save" @click="saveEdit(rate.id)">&#10003;</button>
                <button class="btn-cancel" @click="editingId = null">&#10005;</button>
              </td>
            </template>
            <template v-else>
              <td>{{ rate.company_name }}</td>
              <td class="num"><span class="ltr-number">{{ rate.nifraim_rate != null ? (rate.nifraim_rate * 100).toFixed(2) + '%' : '—' }}</span></td>
              <td class="num"><span class="ltr-number">{{ rate.volume_rate_per_million != null ? Math.round(rate.volume_rate_per_million).toLocaleString() : '—' }}</span></td>
              <td class="num"><span class="ltr-number">{{ rate.pension_accumulation != null ? Math.round(rate.pension_accumulation).toLocaleString() : '—' }}</span></td>
              <td class="num"><span class="ltr-number">{{ rate.changed_percent != null ? (rate.changed_percent * 100).toFixed(2) + '%' : '—' }}</span></td>
              <td class="num"><span class="ltr-number">{{ rate.conversion_to_annuity != null ? Math.round(rate.conversion_to_annuity).toLocaleString() : '—' }}</span></td>
              <td>{{ rate.payment_frequency || '—' }}</td>
              <td>{{ rate.paid_to || '—' }}</td>
              <td class="notes-cell">{{ rate.notes || '—' }}</td>
              <td class="actions">
                <button class="btn-edit" @click="startEdit(rate)">&#9998;</button>
                <button class="btn-del" @click="deleteRate(rate.id)">&#10005;</button>
              </td>
            </template>
          </tr>
          <tr v-if="addingNew">
            <td><input v-model="newForm.company_name" class="edit-input" placeholder="שם חברה" /></td>
            <td class="num"><input v-model.number="newForm.nifraim_rate" type="number" step="0.01" class="edit-input num-input" dir="ltr" placeholder="%" /></td>
            <td class="num"><input v-model.number="newForm.volume_rate_per_million" type="number" step="1" class="edit-input num-input" dir="ltr" /></td>
            <td class="num"><input v-model.number="newForm.pension_accumulation" type="number" step="1" class="edit-input num-input" dir="ltr" /></td>
            <td class="num"><input v-model.number="newForm.changed_percent" type="number" step="0.01" class="edit-input num-input" dir="ltr" placeholder="%" /></td>
            <td class="num"><input v-model.number="newForm.conversion_to_annuity" type="number" step="1" class="edit-input num-input" dir="ltr" /></td>
            <td>
              <select v-model="newForm.payment_frequency" class="edit-input">
                <option value="">—</option>
                <option value="חודשי">חודשי</option>
                <option value="רבעוני">רבעוני</option>
                <option value="שנתי">שנתי</option>
              </select>
            </td>
            <td>
              <select v-model="newForm.paid_to" class="edit-input">
                <option value="">—</option>
                <option value="עיתים">עיתים</option>
                <option value="סוכן">סוכן</option>
                <option value="ידנים">ידנים</option>
              </select>
            </td>
            <td><input v-model="newForm.notes" class="edit-input" placeholder="הערות" /></td>
            <td class="actions">
              <button class="btn-save" @click="saveNew">&#10003;</button>
              <button class="btn-cancel" @click="cancelNew">&#10005;</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import api from '../../api/client.js'

const rates = ref([])
const loading = ref(false)
const seeding = ref(false)
const editingId = ref(null)
const editForm = reactive({
  company_name: '',
  nifraim_rate: null,
  volume_rate_per_million: null,
  pension_accumulation: null,
  changed_percent: null,
  conversion_to_annuity: null,
  payment_frequency: '',
  paid_to: '',
  notes: '',
})
const addingNew = ref(false)
const newForm = reactive({
  company_name: '',
  nifraim_rate: null,
  volume_rate_per_million: null,
  pension_accumulation: null,
  changed_percent: null,
  conversion_to_annuity: null,
  payment_frequency: '',
  paid_to: '',
  notes: '',
})

onMounted(() => fetchRates())

async function seedRates() {
  seeding.value = true
  try {
    await api.post('/volume-rates/seed')
    await fetchRates()
  } finally {
    seeding.value = false
  }
}

async function fetchRates() {
  loading.value = true
  try {
    const res = await api.get('/volume-rates')
    rates.value = res.data
  } finally {
    loading.value = false
  }
}

function startEdit(rate) {
  editingId.value = rate.id
  editForm.company_name = rate.company_name
  editForm.nifraim_rate = rate.nifraim_rate != null ? +(rate.nifraim_rate * 100).toFixed(4) : null
  editForm.volume_rate_per_million = rate.volume_rate_per_million
  editForm.pension_accumulation = rate.pension_accumulation
  editForm.changed_percent = rate.changed_percent != null ? +(rate.changed_percent * 100).toFixed(4) : null
  editForm.conversion_to_annuity = rate.conversion_to_annuity
  editForm.payment_frequency = rate.payment_frequency || ''
  editForm.paid_to = rate.paid_to || ''
  editForm.notes = rate.notes || ''
}

async function saveEdit(id) {
  const payload = {
    ...editForm,
    nifraim_rate: editForm.nifraim_rate != null ? editForm.nifraim_rate / 100 : null,
    changed_percent: editForm.changed_percent != null ? editForm.changed_percent / 100 : null,
  }
  await api.put(`/volume-rates/${id}`, payload)
  editingId.value = null
  await fetchRates()
}

async function deleteRate(id) {
  await api.delete(`/volume-rates/${id}`)
  await fetchRates()
}

function startNew() {
  editingId.value = null
  addingNew.value = true
  Object.assign(newForm, {
    company_name: '', nifraim_rate: null, volume_rate_per_million: null,
    pension_accumulation: null, changed_percent: null, conversion_to_annuity: null,
    payment_frequency: '', paid_to: '', notes: '',
  })
}

function cancelNew() { addingNew.value = false }

async function saveNew() {
  if (!newForm.company_name) return
  const payload = {
    ...newForm,
    nifraim_rate: newForm.nifraim_rate != null ? newForm.nifraim_rate / 100 : null,
    changed_percent: newForm.changed_percent != null ? newForm.changed_percent / 100 : null,
  }
  await api.post('/volume-rates', payload)
  addingNew.value = false
  await fetchRates()
}

async function onFileUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  e.target.value = ''
  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    await api.post('/volume-rates/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    await fetchRates()
  } catch (err) {
    alert(err.response?.data?.detail || 'שגיאה בהעלאת קובץ')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.rate-card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
}

.rate-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.header-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

h3 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.btn-seed {
  background: linear-gradient(135deg, var(--primary-deep), var(--primary));
  color: white;
  border: none;
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 13px;
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s;
}

.btn-seed:hover:not(:disabled) {
  box-shadow: 0 4px 16px var(--primary-light);
  transform: translateY(-1px);
}

.btn-upload {
  display: flex;
  align-items: center;
  gap: 5px;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 6px 14px;
  font-size: 13px;
  font-family: inherit;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.25s;
}

.btn-upload:hover {
  background: var(--bg);
  color: var(--text);
}

.table-scroll { overflow-x: auto; }

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

thead { background: var(--bg); }

th {
  padding: 8px 6px;
  text-align: right;
  font-weight: 600;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
  font-size: 11px;
  white-space: nowrap;
}

th.num, td.num { text-align: left; }

td {
  padding: 8px 6px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
}

.notes-cell {
  font-size: 11px;
  color: var(--text-muted);
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actions { white-space: nowrap; }

.actions button {
  background: none;
  border: none;
  font-size: 13px;
  padding: 2px 6px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-muted);
}

.btn-edit:hover { background: var(--primary-light); color: var(--primary); }
.btn-del:hover { background: var(--red-light); color: var(--red); }
.btn-save:hover { background: var(--green-light); color: var(--green); }
.btn-cancel:hover { background: var(--red-light); color: var(--red); }

.edit-input {
  width: 100%;
  padding: 4px 6px;
  border: 1px solid var(--glass-border);
  border-radius: 6px;
  font-size: 12px;
  font-family: 'Heebo', sans-serif;
  background: var(--bg-surface);
  color: var(--text);
}

.edit-input:focus { outline: none; border-color: var(--primary); }

.edit-input option { background: var(--bg); color: var(--text-secondary); }

.num-input { width: 80px; }

.empty {
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 16px;
}

.loading {
  display: flex;
  justify-content: center;
  padding: 16px;
}

.spinner {
  width: 24px; height: 24px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
