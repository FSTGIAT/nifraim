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
      לא הוגדרו אימיילים. לחץ "טען ברירת מחדל" להוספת רשימה ראשונית.
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
