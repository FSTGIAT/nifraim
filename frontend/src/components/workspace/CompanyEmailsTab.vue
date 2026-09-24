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

    <!-- Empty: the same ring the other Nifraim tabs use when there is no data —
         one action (load the default insurer contacts), in the tab's colour. -->
    <div v-if="contacts.length === 0 && !loading" class="emails-empty">
      <BigAddButton
        label="טעינת אנשי הקשר של החברות"
        color="var(--tab-emails)"
        :size="156"
        @click="!seeding && seedContacts()"
      >
        <svg width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="2" y="4" width="20" height="16" rx="2" /><path d="m22 6-10 7L2 6" />
        </svg>
      </BigAddButton>
    </div>

    <!-- One compact card, list-shaped: avatar · name/email · action.
         The previous pass put every insurer on its own tile and filled the
         page with 17 cards to say what a list says in a third of the space. -->
    <div v-if="!loading && contacts.length" class="share">
      <ul class="share-list">
        <li v-for="contact in contacts" :key="contact.id" class="share-row">
          <CompanyLogo :company="contact.company_name" :size="34" />
          <div class="share-id">
            <span class="share-name">{{ contact.company_name }}</span>
            <a class="share-mail ltr-number" :href="'mailto:' + contact.email">{{ contact.email }}</a>
          </div>
          <span v-if="contact.contact_name" class="share-person">{{ contact.contact_name }}</span>
          <div class="share-tools">
            <button class="icon-btn" title="ערוך" aria-label="ערוך" @click="startEdit(contact)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/></svg>
            </button>
            <button class="icon-btn icon-btn--del" title="מחק" aria-label="מחק" @click="deleteContact(contact.id)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
            </button>
          </div>
        </li>
      </ul>

      <!-- Who you still cannot reach, as one quiet line rather than a wall of
           tiles. Each name opens the form already knowing the company. -->
      <p v-if="missingCompanies.length" class="share-missing">
        <span class="share-missing-lead">ללא כתובת:</span>
        <button v-for="co in missingCompanies" :key="co.label" class="share-chip"
                @click="openAddForm(co.label)">{{ co.label }}</button>
      </p>

      <div class="share-foot">
        <BigAddButton label="הוסף איש קשר" color="#D6336C" @click="openAddForm()" />
      </div>
    </div>

    <ContactFormModal
      :show="formOpen"
      :editing="editingContact"
      :preset-company="presetCompany"
      :companies="KNOWN_COMPANIES"
      :taken="contacts.map(c => c.company_name)"
      @close="closeForm"
      @saved="onSaved"
    />

  </div>
</template>

<script setup>
import { ref, onMounted, reactive, computed } from 'vue'
import api from '../../api/client.js'
import TabHeroLoop from './TabHeroLoop.vue'
import { brandForLabel, COMPANY_BRAND } from '../../utils/companyBrand.js'
import ContactFormModal from './ContactFormModal.vue'
import CompanyLogo from './CompanyLogo.vue'
import BigAddButton from './BigAddButton.vue'
import { assignNearestDistinct } from '../../utils/chartPalette.js'

const contacts = ref([])
const loading = ref(false)
const seeding = ref(false)
// The inline row-of-inputs became a modal, so the tab keeps only WHICH
// contact is being edited and which company the form should start on.
const formOpen = ref(false)
const editingContact = ref(null)
const presetCompany = ref('')

// Every insurer the app knows, deduplicated by display label — the brand map
// carries one entry per PORTAL kind, so כלל appears three times (portal,
// נפרעים, בריאות) for one company.
const KNOWN_COMPANIES = (() => {
  const seen = new Map()
  for (const b of Object.values(COMPANY_BRAND)) {
    // A label with an em-dash is a report variant ("כלל — עמלות"), not a company.
    const label = String(b.label || '').split('—')[0].trim()
    // Not an insurer this book needs an address for.
    if (label.startsWith('אי.בי')) continue
    if (label && !seen.has(label)) seen.set(label, { ...b, label })
  }
  return [...seen.values()]
})()

const knownTotal = computed(() => KNOWN_COMPANIES.length)

/** Insurers with no address on file — the actionable half of this screen. */
const missingCompanies = computed(() => {
  const have = new Set(contacts.value.map(c => String(c.company_name || '').trim()))
  return KNOWN_COMPANIES.filter(co =>
    ![...have].some(h => h.includes(co.label) || co.label.includes(h)),
  )
})

const coveragePct = computed(() => {
  const total = knownTotal.value
  if (!total) return 0
  return Math.min(100, Math.round((contacts.value.length / total) * 100))
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

function openAddForm(company = '') {
  editingContact.value = null
  presetCompany.value = typeof company === 'string' ? company : ''
  formOpen.value = true
}

function startEdit(contact) {
  presetCompany.value = ''
  editingContact.value = contact
  formOpen.value = true
}

function closeForm() {
  formOpen.value = false
  editingContact.value = null
  presetCompany.value = ''
}

// The modal owns the write; the tab only has to catch up afterwards.
async function onSaved() {
  closeForm()
  await fetchContacts()
}

async function deleteContact(id) {
  await api.delete(`/company-contacts/${id}`)
  await fetchContacts()
}
</script>

<style scoped>
/* ── Share-style list ──────────────────────────────────────────────────
   One card, rows of avatar · identity · action. The previous pass gave each
   insurer its own tile, which spent a full screen saying what a list says in
   a third of the height. */
.share {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md, 14px);
  background: var(--card-bg);
  padding: 16px;
}
.share-sep { height: 1px; background: var(--border-subtle); margin: 14px 0; }

.share-list { list-style: none; display: flex; flex-direction: column; }
.share-row {
  display: flex; align-items: center; gap: 11px;
  padding: 9px 4px; border-radius: 8px;
}
.share-row:hover { background: var(--bg); }
.share-id { display: flex; flex-direction: column; min-width: 0; flex: 1; gap: 1px; }
.share-name {
  font-size: 13.5px; font-weight: 600; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.share-mail {
  /* `.ltr-number` flips direction to ltr, which in this RTL column pushed the
     address to the far edge — visually divorced from the company it belongs
     to. Pin it to the column's start so name and address read as one block. */
  align-self: flex-start;
  font-size: 12px; color: var(--text-muted); text-decoration: none;
  max-width: 100%;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.share-mail:hover { color: var(--tab-company-emails, #D6336C); }
.share-person { font-size: 12px; color: var(--text-muted); flex-shrink: 0; }
.share-tools { display: flex; gap: 2px; flex-shrink: 0; opacity: 0; transition: opacity 0.15s ease; }
.share-row:hover .share-tools, .share-row:focus-within .share-tools { opacity: 1; }

/* Who you cannot reach — one line, not a wall of tiles. */
.share-missing {
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
  margin-top: 14px; padding-top: 13px; border-top: 1px solid var(--border-subtle);
}
.share-missing-lead { font-size: 11.5px; color: var(--text-muted); }
.share-chip {
  padding: 3px 10px; border-radius: 11px; cursor: pointer;
  border: 1px dashed color-mix(in srgb, var(--tab-company-emails, #D6336C) 32%, transparent);
  background: none; color: var(--text-secondary, #6b7280);
  font-family: inherit; font-size: 11.5px; font-weight: 600;
}
.share-chip:hover {
  border-style: solid;
  border-color: var(--tab-company-emails, #D6336C);
  color: var(--tab-company-emails, #D6336C);
}
.share-foot { margin-top: 14px; }

@media (prefers-reduced-motion: reduce) {
  .share-tools { opacity: 1; }
}

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

.emails-empty {
  display: flex;
  justify-content: center;
  padding: 48px 0 32px;
  color: var(--tab-emails);
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
