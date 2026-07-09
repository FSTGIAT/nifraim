<template>
  <div class="emails-card">
    <div class="emails-header">
      <div class="emails-titles">
        <h3>אימיילים לחברות</h3>
        <span class="emails-sub">אנשי קשר במחלקות העמלות של החברות</span>
      </div>
      <TabHeroLoop scene="company-emails" flow="ltr" class="emails-art" />
    </div>

    <div v-if="loading" class="loading">
      <div class="spinner"></div>
    </div>

    <EmptyStateGuide
      v-if="contacts.length === 0 && !loading"
      variant="full"
      title="לא הוגדרו אימיילים"
      body="שמירת כתובות אימייל של אנשי קשר בחברות הביטוח לשליחת בירורים ישירות מהמערכת. אפשר לטעון רשימה מוכנה או להוסיף ידנית."
      cta-label="טען ברירת מחדל"
      @cta="seedContacts"
    >
      <template #illustration>
        <div class="esg-mail-icon">
          <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
          </svg>
        </div>
      </template>
    </EmptyStateGuide>

    <!-- Add form -->
    <div v-if="showAddForm" class="add-form">
      <input v-model="addForm.company_name" placeholder="שם חברה" class="edit-input" />
      <input v-model="addForm.email" type="email" placeholder="email@company.co.il" class="edit-input email-input" dir="ltr" />
      <input v-model="addForm.contact_name" placeholder="איש קשר" class="edit-input" />
      <input v-model="addForm.notes" placeholder="הערות" class="edit-input" />
      <div class="add-form-actions">
        <button class="icon-btn icon-btn--save" title="שמור" aria-label="שמור" @click="createContact">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
        </button>
        <button class="icon-btn icon-btn--cancel" title="בטל" aria-label="בטל" @click="showAddForm = false">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      </div>
    </div>

    <table v-if="contacts.length > 0">
      <thead>
        <tr>
          <th class="t-company">חברה</th>
          <th>אימייל</th>
          <th>איש קשר</th>
          <th>הערות</th>
          <th class="t-actions"><span class="sr-only">פעולות</span></th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="contact in contacts"
          :key="contact.id"
          class="contact-row"
          :style="{ '--row-accent': companyColor(contact.company_name) }"
        >
          <template v-if="editingId === contact.id">
            <td><input v-model="editForm.company_name" class="edit-input" /></td>
            <td><input v-model="editForm.email" type="email" class="edit-input email-input" dir="ltr" /></td>
            <td><input v-model="editForm.contact_name" class="edit-input" /></td>
            <td><input v-model="editForm.notes" class="edit-input" /></td>
            <td class="actions actions--editing">
              <button class="icon-btn icon-btn--save" title="שמור" aria-label="שמור" @click="saveEdit(contact.id)">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
              </button>
              <button class="icon-btn icon-btn--cancel" title="בטל" aria-label="בטל" @click="editingId = null">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
              </button>
            </td>
          </template>
          <template v-else>
            <td class="t-company">
              <span class="company-avatar" :style="avatarStyle(contact.company_name)" aria-hidden="true">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <path :d="brandIcon(contact.company_name)" />
                </svg>
              </span>
              <span class="company-name">{{ contact.company_name }}</span>
            </td>
            <td>
              <a class="email-link" :href="'mailto:' + contact.email">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>
                </svg>
                <span class="ltr-number">{{ contact.email }}</span>
              </a>
            </td>
            <td class="contact-cell">{{ contact.contact_name || '—' }}</td>
            <td class="notes-cell">{{ contact.notes || '—' }}</td>
            <td class="actions">
              <button class="icon-btn icon-btn--edit" title="ערוך" aria-label="ערוך" @click="startEdit(contact)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/></svg>
              </button>
              <button class="icon-btn icon-btn--del" title="מחק" aria-label="מחק" @click="deleteContact(contact.id)">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
              </button>
            </td>
          </template>
        </tr>
      </tbody>
    </table>

    <div v-if="contacts.length > 0 || showAddForm" class="footer-actions">
      <button v-if="!showAddForm" class="btn-add" @click="openAddForm">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
        הוסף איש קשר
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import api from '../../api/client.js'
import EmptyStateGuide from './EmptyStateGuide.vue'
import TabHeroLoop from './TabHeroLoop.vue'
import { brandForLabel } from '../../utils/companyBrand.js'
import { assignNearestDistinct } from '../../utils/chartPalette.js'

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

// Same palette-color-per-company mechanism as the comparison summary and the
// automation canvas — a company keeps one recognizable hue across all tabs.
const colorMap = computed(() =>
  assignNearestDistinct(
    contacts.value.map((c) => ({ key: c.company_name, brand: brandForLabel(c.company_name).color }))
  )
)

function companyColor(name) {
  return colorMap.value.get(name) || 'var(--chart-2, #4E9DD0)'
}

function brandIcon(name) {
  return brandForLabel(name).iconPath
}

function avatarStyle(name) {
  const c = companyColor(name)
  return {
    color: c,
    background: `color-mix(in srgb, ${c} 13%, white)`,
    borderColor: `color-mix(in srgb, ${c} 30%, transparent)`,
  }
}

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
  position: relative;
  overflow: hidden;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle, #E5E5E5);
  border-radius: var(--radius-md, 14px);
  padding: 18px 20px;
  max-width: 940px;
  margin: 0 auto;
  box-shadow: var(--shadow-sm);
}

.emails-art {
  position: absolute;
  inset-inline-end: 0;
  top: 50%;
  transform: translateY(-50%);
  width: min(230px, 34%);
  aspect-ratio: 420 / 300;
  pointer-events: none;
  z-index: 0;
}
@media (max-width: 640px) { .emails-art { display: none; } }

.emails-header {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 150px;
  margin-bottom: 14px;
}

.emails-titles {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 5px;
  min-width: 0;
  max-width: 62%;
  text-align: start;
}

.emails-titles h3 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.02em;
  color: var(--text);
}

.emails-sub {
  font-size: 13px;
  color: var(--text-muted);
  line-height: 1.4;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

th {
  padding: 9px 8px;
  text-align: right;
  font-weight: 600;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
  font-size: 11.5px;
  letter-spacing: 0.3px;
}

td {
  padding: 9px 8px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
}

/* Per-company accent bar hugging the row's inline-start edge */
.contact-row td:first-child {
  position: relative;
}

.contact-row td:first-child::before {
  content: '';
  position: absolute;
  inset-inline-start: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 999px;
  background: var(--row-accent, transparent);
}

.contact-row { transition: background 0.15s var(--transition, ease); }
.contact-row:hover { background: rgba(0, 0, 0, 0.02); }

.t-company { min-width: 150px; }

td.t-company {
  display: flex;
  align-items: center;
  gap: 9px;
  padding-inline-start: 12px;
  font-weight: 600;
}

.company-avatar {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.company-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.email-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--text-secondary, #3E3E3C);
  text-decoration: none;
  font-size: 12.5px;
  border-radius: 6px;
  padding: 2px 4px;
  transition: color 0.15s, background 0.15s;
}

.email-link svg { color: var(--text-muted); flex-shrink: 0; transition: color 0.15s; }

.email-link:hover {
  color: var(--primary-deep);
  background: var(--primary-light);
}

.email-link:hover svg { color: var(--primary); }

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
}

.contact-cell { font-size: 12.5px; }

.notes-cell {
  font-size: 12px;
  color: var(--text-muted);
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.actions {
  white-space: nowrap;
  text-align: left;
  width: 76px;
}

/* Row actions rest at low emphasis (visible affordance), full on hover/edit/focus */
.actions .icon-btn { opacity: 0.45; }
.contact-row:hover .actions .icon-btn,
.actions--editing .icon-btn,
.actions .icon-btn:focus-visible { opacity: 1; }

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: none;
  border: 1px solid transparent;
  border-radius: 8px;
  cursor: pointer;
  color: var(--text-muted);
  transition: background 0.15s, color 0.15s, border-color 0.15s, opacity 0.15s;
}

.icon-btn:focus-visible {
  outline: 2px solid var(--tab-emails);
  outline-offset: 1px;
}

.icon-btn--edit:hover { background: var(--tab-emails-wash); color: var(--tab-emails-ink); border-color: rgba(232, 74, 127, 0.3); }
.icon-btn--del:hover { background: var(--red-light); color: var(--red-deep); border-color: rgba(194, 57, 52, 0.25); }
.icon-btn--save:hover { background: var(--green-light); color: var(--green-deep); border-color: rgba(46, 132, 74, 0.25); }
.icon-btn--cancel:hover { background: var(--red-light); color: var(--red-deep); border-color: rgba(194, 57, 52, 0.25); }

.edit-input {
  width: 100%;
  padding: 6px 8px;
  border: 1px solid var(--border-subtle, #E5E5E5);
  border-radius: 8px;
  font-size: 12.5px;
  font-family: 'Heebo', sans-serif;
  background: var(--bg-surface);
  color: var(--text);
}

.edit-input:focus {
  outline: none;
  border-color: var(--tab-emails);
  box-shadow: 0 0 0 3px var(--tab-emails-wash);
}

.email-input {
  width: 190px;
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
  min-width: 110px;
}

.add-form-actions {
  display: flex;
  gap: 4px;
}

.add-form-actions .icon-btn { opacity: 1; }

.footer-actions {
  margin-top: 12px;
}

.btn-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  background: none;
  border: 1px dashed var(--border, #DDDBDA);
  border-radius: 8px;
  padding: 9px 16px;
  font-size: 13px;
  font-family: inherit;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.25s;
  width: 100%;
}

.btn-add:hover {
  border-color: var(--tab-emails);
  color: var(--tab-emails-ink);
  background: var(--tab-emails-wash);
}

/* Icon for the empty-state guide (slotted into EmptyStateGuide) */
.esg-mail-icon {
  width: 56px;
  height: 56px;
  margin: 0 auto;
  background: var(--tab-emails-wash);
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--tab-emails-ink);
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

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

@media (max-width: 680px) {
  .actions .icon-btn { opacity: 1; }
  .notes-cell { display: none; }
  th:nth-child(4) { display: none; }
  td:nth-child(4):not(.t-company) { display: none; }
}
</style>
