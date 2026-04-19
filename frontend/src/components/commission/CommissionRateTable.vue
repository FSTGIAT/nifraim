<template>
  <div class="rate-card">
    <div class="rate-header">
      <h3>טבלת עמלות</h3>
      <button v-if="rates.length === 0" class="btn-seed" @click="seedRates" :disabled="seeding">
        {{ seeding ? 'טוען...' : 'טען ברירת מחדל' }}
      </button>
      <button v-if="rates.length > 0 && !addingNew" class="btn-seed" @click="startNew">+ הוסף שורה</button>
    </div>

    <div v-if="rates.length === 0 && !loading" class="empty">
      לא הוגדרו עמלות. לחץ "טען ברירת מחדל" להוספת טבלת עמלות ראשונית.
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>

    <table v-if="rates.length > 0">
      <thead>
        <tr>
          <th>חברה</th>
          <th class="num">אחוז</th>
          <th>תדירות</th>
          <th>נפרעים</th>
          <th>אימייל</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="rate in rates" :key="rate.id">
          <template v-if="editingId === rate.id">
            <td><input v-model="editForm.company_name" class="edit-input" /></td>
            <td class="num">
              <input v-model.number="editForm.rate" type="number" step="0.01" class="edit-input num-input" dir="ltr" placeholder="%" />
            </td>
            <td>
              <select v-model="editForm.payment_frequency" class="edit-input">
                <option value="חודשי">חודשי</option>
                <option value="רבעוני">רבעוני</option>
                <option value="שנתי">שנתי</option>
              </select>
            </td>
            <td>
              <select v-model="editForm.paid_to" class="edit-input">
                <option value="עיתים">עיתים</option>
                <option value="סוכן">סוכן</option>
                <option value="ידנים">ידנים</option>
              </select>
            </td>
            <td>
              <input v-model="editForm.company_email" class="edit-input email-input" dir="ltr" placeholder="email@company.co.il" />
            </td>
            <td class="actions">
              <button class="btn-save" @click="saveEdit(rate.id)">&#10003;</button>
              <button class="btn-cancel" @click="editingId = null">&#10005;</button>
            </td>
          </template>
          <template v-else>
            <td>{{ rate.company_name }}</td>
            <td class="num"><span class="ltr-number">{{ (rate.rate * 100).toFixed(2) }}%</span></td>
            <td>{{ rate.payment_frequency || '—' }}</td>
            <td>{{ rate.paid_to || '—' }}</td>
            <td class="email-cell"><span class="ltr-number">{{ rate.company_email || '—' }}</span></td>
            <td class="actions">
              <button class="btn-edit" @click="startEdit(rate)">&#9998;</button>
              <button class="btn-del" @click="deleteRate(rate.id)">&#10005;</button>
            </td>
          </template>
        </tr>
        <tr v-if="addingNew">
          <td><input v-model="newForm.company_name" class="edit-input" placeholder="שם חברה" /></td>
          <td class="num">
            <input v-model.number="newForm.rate" type="number" step="0.01" class="edit-input num-input" dir="ltr" placeholder="%" />
          </td>
          <td>
            <select v-model="newForm.payment_frequency" class="edit-input">
              <option value="חודשי">חודשי</option>
              <option value="רבעוני">רבעוני</option>
              <option value="שנתי">שנתי</option>
            </select>
          </td>
          <td>
            <select v-model="newForm.paid_to" class="edit-input">
              <option value="עיתים">עיתים</option>
              <option value="סוכן">סוכן</option>
              <option value="ידנים">ידנים</option>
            </select>
          </td>
          <td>
            <input v-model="newForm.company_email" class="edit-input email-input" dir="ltr" placeholder="email@company.co.il" />
          </td>
          <td class="actions">
            <button class="btn-save" @click="saveNew">&#10003;</button>
            <button class="btn-cancel" @click="cancelNew">&#10005;</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import api from '../../api/client.js'

const emit = defineEmits(['rates-changed'])

const rates = ref([])
const loading = ref(false)
const seeding = ref(false)
const editingId = ref(null)
const editForm = reactive({
  company_name: '',
  rate: 0,
  payment_frequency: '',
  paid_to: '',
  company_email: '',
})
const addingNew = ref(false)
const newForm = reactive({
  company_name: '',
  rate: 0,
  payment_frequency: 'חודשי',
  paid_to: 'עיתים',
  company_email: '',
})

onMounted(() => fetchRates())

async function fetchRates() {
  loading.value = true
  try {
    const res = await api.get('/commission-rates')
    rates.value = res.data
  } finally {
    loading.value = false
  }
}

async function seedRates() {
  seeding.value = true
  try {
    await api.post('/commission-rates/seed')
    await fetchRates()
    emit('rates-changed')
  } finally {
    seeding.value = false
  }
}

function startEdit(rate) {
  editingId.value = rate.id
  editForm.company_name = rate.company_name
  editForm.rate = +(rate.rate * 100).toFixed(4)
  editForm.payment_frequency = rate.payment_frequency || 'חודשי'
  editForm.paid_to = rate.paid_to || 'עיתים'
  editForm.company_email = rate.company_email || ''
}

async function saveEdit(id) {
  const payload = { ...editForm, rate: editForm.rate / 100 }
  await api.put(`/commission-rates/${id}`, payload)
  editingId.value = null
  await fetchRates()
  emit('rates-changed')
}

async function deleteRate(id) {
  await api.delete(`/commission-rates/${id}`)
  await fetchRates()
  emit('rates-changed')
}

function startNew() {
  editingId.value = null
  addingNew.value = true
  newForm.company_name = ''
  newForm.rate = 0
  newForm.payment_frequency = 'חודשי'
  newForm.paid_to = 'עיתים'
  newForm.company_email = ''
}

function cancelNew() {
  addingNew.value = false
}

async function saveNew() {
  if (!newForm.company_name) return
  const payload = { ...newForm, rate: newForm.rate / 100 }
  await api.post('/commission-rates', payload)
  addingNew.value = false
  await fetchRates()
  emit('rates-changed')
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

.btn-seed:disabled {
  opacity: 0.5;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

thead {
  background: var(--bg);
}

th {
  padding: 8px 6px;
  text-align: right;
  font-weight: 600;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

th.num, td.num {
  text-align: left;
}

td {
  padding: 8px 6px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
}

.actions {
  white-space: nowrap;
}

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

.edit-input:focus {
  outline: none;
  border-color: var(--primary);
}

.edit-input option {
  background: var(--bg);
  color: var(--text-secondary);
}

.num-input {
  width: 80px;
}

.email-input {
  width: 140px;
}

.email-cell {
  font-size: 11px;
  color: var(--text-muted);
}

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
  width: 24px;
  height: 24px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
