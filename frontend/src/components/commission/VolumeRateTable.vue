<template>
  <div class="rate-card">
    <!-- ── Compact hero (shelf-language, purple tab identity) ── -->
    <header class="rate-hero">
      <div class="hero-copy">
        <span class="hero-eyebrow">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>
          עמלות היקף
        </span>
        <h2 class="hero-title">טבלת עמלות היקף</h2>
        <p class="hero-sub">שיעורי ההיקף, הצבירות וההמרה לקצבה לפי חברה — הבסיס לחישוב הבונוס.</p>
      </div>
      <div class="hero-actions">
        <button v-if="rates.length === 0" class="btn-accent" @click="seedRates" :disabled="seeding">
          <span v-if="seeding" class="btn-spin" aria-hidden="true"></span>
          {{ seeding ? 'טוען...' : 'טען ברירת מחדל' }}
        </button>
        <button v-if="rates.length > 0 && !addingNew" class="btn-ghost" @click="startNew">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
          הוסף שורה
        </button>
        <label class="btn-ghost">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          העלה מקובץ
          <input type="file" accept=".xlsx,.xls" @change="onFileUpload" class="hidden-file" />
        </label>
      </div>
    </header>

    <Transition name="fade">
      <div v-if="uploadError" class="hero-upload-error" role="alert">
        <span>{{ uploadError }}</span>
        <button class="error-dismiss" @click="uploadError = null" title="סגור" aria-label="סגור">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>
    </Transition>

    <div v-if="rates.length === 0 && !loading" class="empty">
      <span class="empty-icon" aria-hidden="true">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>
      </span>
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
                <button class="icon-btn icon-btn--save" @click="saveEdit(rate.id)" title="שמור"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></button>
                <button class="icon-btn icon-btn--cancel" @click="editingId = null" title="ביטול"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
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
                <button class="icon-btn icon-btn--edit" @click="startEdit(rate)" title="ערוך"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
                <button class="icon-btn icon-btn--del" @click="deleteRate(rate.id)" title="מחק"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg></button>
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
              <button class="icon-btn icon-btn--save" @click="saveNew" title="שמור"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></button>
              <button class="icon-btn icon-btn--cancel" @click="cancelNew" title="ביטול"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>
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
const uploadError = ref(null)
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
  uploadError.value = null
  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file)
    await api.post('/volume-rates/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    await fetchRates()
  } catch (err) {
    uploadError.value = err.response?.data?.detail || 'שגיאה בהעלאת קובץ'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.rate-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
  box-shadow: var(--shadow-sm);
}

/* ── Compact hero (shelf language, purple identity) ── */
.rate-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.04em;
  color: var(--tab-commission);
  background: var(--tab-commission-wash);
  border: 1px solid color-mix(in srgb, var(--tab-commission) 28%, transparent);
  padding: 3px 10px;
  border-radius: 999px;
}

.hero-title {
  margin: 0;
  font-size: 20px;
  font-weight: 750;
  letter-spacing: -0.01em;
  color: var(--text);
}

.hero-sub {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-inline-start: auto;
}

.btn-accent {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: var(--tab-commission);
  color: white;
  border: none;
  border-radius: 10px;
  padding: 9px 16px;
  font-size: 13px;
  font-family: inherit;
  font-weight: 700;
  cursor: pointer;
  box-shadow: var(--shadow-md);
  transition: transform 0.2s var(--transition), background 0.2s var(--transition);
}

.btn-accent:hover:not(:disabled) {
  transform: translateY(-1px);
  background: color-mix(in srgb, var(--tab-commission) 88%, black);
}

.btn-accent:disabled { opacity: 0.7; cursor: default; }

.btn-spin {
  width: 14px;
  height: 14px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: white;
  animation: spin 0.7s linear infinite;
}

.btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--bg-surface);
  color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 13px;
  font-family: inherit;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.18s var(--transition);
}

.btn-ghost:hover:not(:disabled) {
  border-color: var(--tab-commission);
  color: var(--tab-commission);
}

.btn-ghost:disabled { opacity: 0.5; cursor: default; }

.hidden-file { display: none; }

/* ── Inline upload error (dismissible strip) ── */
.hero-upload-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin: 0 0 14px;
  padding: 8px 12px;
  font-size: 12px;
  color: var(--red);
  font-weight: 600;
  background: var(--red-light);
  border: 1px solid color-mix(in srgb, var(--red) 30%, transparent);
  border-radius: 10px;
}

.error-dismiss {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  flex: 0 0 auto;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 6px;
  color: var(--red);
  cursor: pointer;
  transition: background 0.18s var(--transition);
}

.error-dismiss:hover { background: color-mix(in srgb, var(--red) 14%, transparent); }

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

tbody tr { transition: background 0.15s; }
tbody tr:hover { background: rgba(0, 0, 0, 0.02); }

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

.actions {
  display: flex;
  gap: 4px;
  white-space: nowrap;
  justify-content: flex-end;
}

.icon-btn {
  width: 27px;
  height: 27px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 7px;
  cursor: pointer;
  color: var(--text-muted);
  transition: all 0.18s var(--transition);
}

.icon-btn--edit:hover {
  background: var(--tab-commission-wash);
  color: var(--tab-commission);
  border-color: color-mix(in srgb, var(--tab-commission) 40%, transparent);
}
.icon-btn--del:hover { background: var(--red-light); color: var(--red); border-color: var(--red); }
.icon-btn--save:hover { background: var(--green-light); color: var(--green-deep, var(--green)); border-color: var(--green); }
.icon-btn--cancel:hover { background: var(--red-light); color: var(--red); border-color: var(--red); }

.edit-input {
  width: 100%;
  padding: 4px 6px;
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  font-size: 12px;
  font-family: 'Heebo', sans-serif;
  background: var(--bg-surface);
  color: var(--text);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.edit-input:focus {
  outline: none;
  border-color: var(--tab-commission);
  box-shadow: 0 0 0 3px var(--tab-commission-wash);
}

.edit-input option { background: var(--bg); color: var(--text-secondary); }

.num-input { width: 80px; }

.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  text-align: center;
  color: var(--text-muted);
  font-size: 13px;
  padding: 24px 16px;
  line-height: 1.7;
}

.empty-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: var(--tab-commission-wash);
  color: var(--tab-commission);
}

.loading {
  display: flex;
  justify-content: center;
  padding: 16px;
}

.spinner {
  width: 24px; height: 24px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--tab-commission);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.fade-enter-active, .fade-leave-active { transition: opacity 0.25s var(--transition); }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (prefers-reduced-motion: reduce) {
  .btn-accent, .btn-ghost, .icon-btn, .btn-spin, .spinner { transition: none !important; animation: none !important; }
}
</style>
