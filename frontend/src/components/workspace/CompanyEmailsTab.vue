<template>
  <div class="emails-card">
    <div class="emails-header">
      <h3>אימיילים לחברות</h3>
      <button v-if="contacts.length === 0 && !loading" class="btn-seed" @click="seedContacts" :disabled="seeding">
        {{ seeding ? 'טוען...' : 'טען ברירת מחדל' }}
      </button>
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>

    <div v-if="contacts.length === 0 && !loading" class="empty">
      <!-- Floating blur circles -->
      <div class="float-circle fc-1"></div>
      <div class="float-circle fc-2"></div>
      <div class="float-circle fc-3"></div>
      <div class="float-circle fc-4"></div>
      <div class="float-circle fc-5"></div>
      <div class="float-circle fc-6"></div>
      <div class="float-circle fc-7"></div>

      <!-- Animated waves at bottom -->
      <div class="wave-bg">
        <div class="shimmer"></div>
        <svg class="wave wave-1" viewBox="0 0 1440 200" preserveAspectRatio="none">
          <defs><linearGradient id="cewg1" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#F57C00" stop-opacity="0.10"/><stop offset="30%" stop-color="#FF9800" stop-opacity="0.06"/><stop offset="60%" stop-color="#FFB74D" stop-opacity="0.10"/><stop offset="100%" stop-color="#F57C00" stop-opacity="0.05"/></linearGradient></defs>
          <path fill="url(#cewg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
        </svg>
        <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
          <defs><linearGradient id="cewg2" x1="100%" y1="0%" x2="0%" y2="0%"><stop offset="0%" stop-color="#FFB74D" stop-opacity="0.08"/><stop offset="40%" stop-color="#F57C00" stop-opacity="0.05"/><stop offset="70%" stop-color="#FF9800" stop-opacity="0.08"/><stop offset="100%" stop-color="#FFB74D" stop-opacity="0.04"/></linearGradient></defs>
          <path fill="url(#cewg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
        </svg>
        <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
          <defs><linearGradient id="cewg3" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#FF9800" stop-opacity="0.06"/><stop offset="50%" stop-color="#FFB74D" stop-opacity="0.04"/><stop offset="100%" stop-color="#F57C00" stop-opacity="0.07"/></linearGradient></defs>
          <path fill="url(#cewg3)" d="M0,150L60,143.3C120,137,240,123,360,126.7C480,130,600,150,720,153.3C840,157,960,143,1080,133.3C1200,123,1320,117,1380,113.3L1440,110L1440,200L0,200Z"/>
        </svg>
      </div>

      <div class="empty-content">
        <div class="empty-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
          </svg>
        </div>
        <h3>לא הוגדרו אימיילים</h3>
        <p>לחץ "טען ברירת מחדל" להוספת רשימה ראשונית</p>
      </div>
    </div>

    <!-- Add form -->
    <div v-if="showAddForm" class="add-form">
      <input v-model="addForm.company_name" placeholder="שם חברה" class="edit-input" />
      <input v-model="addForm.email" placeholder="email@company.co.il" class="edit-input email-input" dir="ltr" />
      <input v-model="addForm.contact_name" placeholder="איש קשר" class="edit-input" />
      <input v-model="addForm.notes" placeholder="הערות" class="edit-input" />
      <div class="add-form-actions">
        <button class="btn-save" @click="createContact">&#10003;</button>
        <button class="btn-cancel" @click="showAddForm = false">&#10005;</button>
      </div>
    </div>

    <table v-if="contacts.length > 0">
      <thead>
        <tr>
          <th>חברה</th>
          <th>אימייל</th>
          <th>איש קשר</th>
          <th>הערות</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="contact in contacts" :key="contact.id">
          <template v-if="editingId === contact.id">
            <td><input v-model="editForm.company_name" class="edit-input" /></td>
            <td><input v-model="editForm.email" class="edit-input email-input" dir="ltr" /></td>
            <td><input v-model="editForm.contact_name" class="edit-input" /></td>
            <td><input v-model="editForm.notes" class="edit-input" /></td>
            <td class="actions">
              <button class="btn-save" @click="saveEdit(contact.id)">&#10003;</button>
              <button class="btn-cancel" @click="editingId = null">&#10005;</button>
            </td>
          </template>
          <template v-else>
            <td>{{ contact.company_name }}</td>
            <td class="ltr-number email-cell">{{ contact.email }}</td>
            <td>{{ contact.contact_name || '—' }}</td>
            <td class="notes-cell">{{ contact.notes || '—' }}</td>
            <td class="actions">
              <button class="btn-edit" @click="startEdit(contact)">&#9998;</button>
              <button class="btn-del" @click="deleteContact(contact.id)">&#10005;</button>
            </td>
          </template>
        </tr>
      </tbody>
    </table>

    <div v-if="contacts.length > 0 || showAddForm" class="footer-actions">
      <button v-if="!showAddForm" class="btn-add" @click="openAddForm">+ הוסף איש קשר</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue'
import api from '../../api/client.js'

const contacts = ref([])
const loading = ref(false)
const seeding = ref(false)
const showAddForm = ref(false)
const editingId = ref(null)

const editForm = reactive({
  company_name: '',
  email: '',
  contact_name: '',
  notes: '',
})

const addForm = reactive({
  company_name: '',
  email: '',
  contact_name: '',
  notes: '',
})

onMounted(() => fetchContacts())

async function fetchContacts() {
  loading.value = true
  try {
    const res = await api.get('/company-contacts')
    contacts.value = res.data
  } finally {
    loading.value = false
  }
}

async function seedContacts() {
  seeding.value = true
  try {
    await api.post('/company-contacts/seed')
    await fetchContacts()
  } finally {
    seeding.value = false
  }
}

function openAddForm() {
  addForm.company_name = ''
  addForm.email = ''
  addForm.contact_name = ''
  addForm.notes = ''
  showAddForm.value = true
}

async function createContact() {
  if (!addForm.company_name || !addForm.email) return
  await api.post('/company-contacts', { ...addForm })
  showAddForm.value = false
  await fetchContacts()
}

function startEdit(contact) {
  editingId.value = contact.id
  editForm.company_name = contact.company_name
  editForm.email = contact.email
  editForm.contact_name = contact.contact_name || ''
  editForm.notes = contact.notes || ''
}

async function saveEdit(id) {
  await api.put(`/company-contacts/${id}`, { ...editForm })
  editingId.value = null
  await fetchContacts()
}

async function deleteContact(id) {
  await api.delete(`/company-contacts/${id}`)
  await fetchContacts()
}
</script>

<style scoped>
.emails-card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg, 16px);
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}

.emails-header {
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

td {
  padding: 8px 6px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
}

.email-cell {
  font-size: 12px;
  color: var(--primary);
}

.notes-cell {
  font-size: 11px;
  color: var(--text-muted);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.email-input {
  width: 180px;
}

.add-form {
  display: flex;
  gap: 8px;
  align-items: center;
  padding: 10px 0;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--border-subtle);
  flex-wrap: wrap;
}

.add-form .edit-input {
  flex: 1;
  min-width: 100px;
}

.add-form-actions {
  display: flex;
  gap: 4px;
}

.add-form-actions button {
  background: none;
  border: none;
  font-size: 15px;
  padding: 4px 8px;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-muted);
}

.footer-actions {
  margin-top: 12px;
}

.btn-add {
  background: none;
  border: 1px dashed var(--glass-border);
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 13px;
  font-family: inherit;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.25s;
  width: 100%;
}

.btn-add:hover {
  border-color: var(--primary);
  color: var(--primary);
  background: var(--primary-light);
}

.empty {
  position: relative;
  text-align: center;
  padding: 80px 24px 100px;
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.empty-content { position: relative; z-index: 1; }

.empty-icon {
  width: 56px; height: 56px;
  margin: 0 auto 16px;
  background: var(--amber-light);
  border-radius: 16px;
  display: flex; align-items: center; justify-content: center;
  color: var(--amber);
}

.empty h3 { font-size: 17px; font-weight: 700; color: var(--text); margin-bottom: 8px; }
.empty p { font-size: 14px; color: var(--text-secondary); }

/* Floating blur circles */
.float-circle { position: fixed; border-radius: 50%; pointer-events: none; z-index: 0; }
.fc-1 { width: 220px; height: 220px; top: 10%; right: -60px; background: rgba(245,124,0,0.045); border: 1px solid rgba(245,124,0,0.06); animation: floatBob 8s ease-in-out infinite; }
.fc-2 { width: 160px; height: 160px; bottom: 25%; left: -40px; background: rgba(245,124,0,0.035); border: 1px solid rgba(245,124,0,0.05); animation: floatBob 6.5s ease-in-out infinite reverse; }
.fc-3 { width: 90px; height: 90px; top: 30%; left: 8%; background: rgba(245,124,0,0.05); animation: floatBob 10s ease-in-out infinite 2s; }
.fc-4 { width: 120px; height: 120px; top: 55%; right: 6%; background: rgba(245,124,0,0.03); border: 1px solid rgba(245,124,0,0.04); animation: floatBob 9s ease-in-out infinite 1s; }
.fc-5 { width: 50px; height: 50px; top: 18%; right: 22%; background: rgba(255,152,0,0.055); animation: floatBob 7s ease-in-out infinite 3s; }
.fc-6 { width: 280px; height: 280px; bottom: 8%; right: -90px; background: rgba(245,124,0,0.025); border: 1px solid rgba(245,124,0,0.035); animation: floatBob 12s ease-in-out infinite 0.5s; }
.fc-7 { width: 65px; height: 65px; bottom: 35%; left: 18%; background: rgba(255,183,77,0.06); border: 1px solid rgba(255,183,77,0.05); animation: floatBob 8.5s ease-in-out infinite reverse 1.5s; }

@keyframes floatBob { 0%, 100% { transform: translateY(0) rotate(0deg); } 33% { transform: translateY(-16px) rotate(2deg); } 66% { transform: translateY(8px) rotate(-1deg); } }

/* Waves */
.wave-bg { position: fixed; left: 0; right: 0; bottom: 0; height: 200px; overflow: hidden; pointer-events: none; z-index: 0; }
.shimmer { position: absolute; bottom: 0; left: 0; right: 0; height: 100%; z-index: 1; overflow: hidden; mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%); -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%); }
.shimmer::after { content: ''; position: absolute; top: 0; left: -80%; width: 50%; height: 100%; background: linear-gradient(90deg, transparent 0%, rgba(255,200,100,0.1) 35%, rgba(255,255,255,0.15) 50%, rgba(255,200,100,0.1) 65%, transparent 100%); animation: shimmerSweep 7s ease-in-out infinite; }
@keyframes shimmerSweep { 0% { left: -80%; } 100% { left: 180%; } }
.wave { position: absolute; bottom: 0; left: 0; width: 200%; height: 100%; }
.wave-1 { animation: waveSlide 14s linear infinite; }
.wave-2 { animation: waveSlide 18s linear infinite reverse; }
.wave-3 { animation: waveSlide 22s linear infinite; }
@keyframes waveSlide { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }

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
