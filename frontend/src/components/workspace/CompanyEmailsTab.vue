<template>
  <!-- אנשי קשר — window content (ContactsModal). Built for the window: a
       header strip with the one action, contacts filling the width in two
       columns, and the insurers still missing an address as "+" chips. -->
  <div class="ct">
    <!-- Hero — the Mail Agent's shape: kicker, wordmark with the accent word,
         the counters as the "where do I stand" beat, the one action, and the
         looping scene at the end. -->
    <header class="ct-hero">
      <div class="ct-hero-copy">
        <span class="ct-kicker">ספר כתובות</span>
        <h2 class="ct-hero-title">אנשי <span class="ct-hero-title-acc">קשר</span></h2>
        <div v-if="contacts.length" class="ct-stats">
          <div class="ct-stat">
            <span class="ct-stat-n ltr-number">{{ contacts.length }}</span>
            <span class="ct-stat-l">כתובות</span>
          </div>
          <button v-if="missingCompanies.length" type="button" class="ct-stat ct-stat--btn ct-stat--hot" @click="scrollToMissing">
            <span class="ct-stat-n ltr-number">{{ missingCompanies.length }}</span>
            <span class="ct-stat-l">חסרות כתובת</span>
          </button>
        </div>
        <div v-if="contacts.length" class="ct-meta">
          <button class="ct-add" type="button" @click="openAddForm()">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
            הוספת איש קשר
          </button>
        </div>
      </div>
      <TabHeroLoop scene="company-emails" flow="ltr" class="ct-hero-art" />
    </header>

    <div v-if="loading" class="ct-loading"><span class="ct-spin" aria-hidden="true"></span></div>

    <!-- Empty: one action — load the insurers' default contacts. -->
    <div v-else-if="contacts.length === 0" class="ct-empty">
      <BigAddButton label="טעינת אנשי הקשר של החברות" color="var(--tab-emails)" :size="140"
                    @click="!seeding && seedContacts()">
        <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <rect x="2" y="4" width="20" height="16" rx="2" /><path d="m22 6-10 7L2 6" />
        </svg>
      </BigAddButton>
      <p class="ct-empty-text">{{ seeding ? 'טוען…' : 'טעינת אנשי הקשר של כל החברות בלחיצה אחת' }}</p>
    </div>

    <template v-else>
      <section class="ct-card">
      <ul class="ct-grid">
        <li v-for="contact in contacts" :key="contact.id" class="ct-row">
          <CompanyLogo :company="contact.company_name" :size="36" />
          <div class="ct-id">
            <span class="ct-name">{{ contact.company_name }}<span v-if="contact.contact_name" class="ct-person"> · {{ contact.contact_name }}</span></span>
            <a class="ct-mail ltr-number" :href="'mailto:' + contact.email" :title="contact.email">{{ contact.email }}</a>
          </div>
          <div class="ct-tools">
            <button class="ct-icon" title="עריכה" aria-label="עריכה" @click="startEdit(contact)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/></svg>
            </button>
            <button class="ct-icon ct-icon--del" title="מחיקה" aria-label="מחיקה" @click="deleteContact(contact.id)">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>
            </button>
          </div>
        </li>
      </ul>
      </section>

      <section v-if="missingCompanies.length" ref="missingEl" class="ct-card ct-missing">
        <h3 class="ct-missing-title">חסרה כתובת <span class="ct-missing-n ltr-number">{{ missingCompanies.length }}</span></h3>
        <div class="ct-chips">
          <button v-for="co in missingCompanies" :key="co.label" class="ct-chip" type="button"
                  :title="'הוספת כתובת ל' + co.label" @click="openAddForm(co.label)">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
            {{ co.label }}
          </button>
        </div>
      </section>
    </template>

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
import { brandForLabel, COMPANY_BRAND } from '../../utils/companyBrand.js'
import ContactFormModal from './ContactFormModal.vue'
import CompanyLogo from './CompanyLogo.vue'
import TabHeroLoop from './TabHeroLoop.vue'
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

// Spelling-tolerant company key: Hebrew names are written with and without
// the vowel letters א/ו/י ("אנאליסט" = "אנליסט"), so drop them after the
// first letter, plus spaces and quote marks.
function nameKey(n) {
  const t = String(n || '').trim().replace(/[\s"'׳״-]/g, '')
  return t.slice(0, 1) + t.slice(1).replace(/[אוי]/g, '')
}

/** Insurers with no address on file — the actionable half of this screen. */
const missingCompanies = computed(() => {
  const have = contacts.value.map(c => nameKey(c.company_name)).filter(Boolean)
  return KNOWN_COMPANIES.filter(co => {
    const k = nameKey(co.label)
    return !have.some(h => h.includes(k) || k.includes(h))
  })
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

const missingEl = ref(null)
function scrollToMissing() {
  missingEl.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

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
.ct { display: flex; flex-direction: column; gap: 16px; }

/* ── Hero (Mail Agent's shape, in the contacts' magenta) ── */
.ct-hero {
  position: relative; overflow: hidden; display: flex; align-items: center; min-height: 190px;
  padding: 22px 24px; background: var(--card-bg);
  border: 1px solid var(--border-subtle); border-radius: var(--radius-md); box-shadow: var(--shadow-sm);
}
.ct-hero::before {
  content: ''; position: absolute; inset-inline-end: -6%; top: -60%; width: 44%; height: 220%;
  background: radial-gradient(circle, var(--tab-emails-wash), transparent 70%); pointer-events: none;
}
.ct-hero-copy { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 6px; max-width: 60%; min-width: 0; }
.ct-kicker {
  align-self: flex-start; padding: 4px 11px; border-radius: 999px; font-size: 11.5px; font-weight: 800;
  background: var(--tab-emails-wash); color: var(--tab-emails-ink);
}
.ct-hero-title {
  align-self: flex-start; margin: 4px 0 0;
  font-family: 'Rubik', 'Heebo', sans-serif; font-size: clamp(28px, 3.3vw, 40px); font-weight: 700;
  letter-spacing: -0.035em; line-height: 1.05; color: var(--text);
}
.ct-hero-title-acc { color: var(--tab-emails-ink); }
.ct-hero-art {
  position: absolute; inset-inline-end: 4px; top: 50%; transform: translateY(-50%);
  width: min(270px, 36%); aspect-ratio: 420 / 300; pointer-events: none; z-index: 0;
}
.ct-stats { display: flex; gap: 22px; margin-top: 10px; }
.ct-stat { display: flex; flex-direction: column; align-items: flex-start; padding: 4px 8px; margin: -4px -8px; border-radius: var(--radius-sm); }
.ct-stat--btn { font-family: inherit; text-align: start; background: none; border: none; cursor: pointer; }
.ct-stat--btn:hover { background: var(--tab-emails-wash); }
.ct-stat--btn:hover .ct-stat-l { color: var(--tab-emails-ink); text-decoration: underline; text-underline-offset: 3px; }
.ct-stat--btn:focus-visible { outline: 2px solid var(--tab-emails); outline-offset: 2px; }
.ct-stat-n { font-size: 26px; font-weight: 800; line-height: 1.1; color: var(--text); font-variant-numeric: tabular-nums; }
.ct-stat--hot .ct-stat-n { color: var(--tab-emails-ink); }
.ct-stat-l { font-size: 11.5px; font-weight: 600; color: var(--text-muted); }
.ct-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.ct-add {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 8px 14px; border: none; border-radius: 10px; cursor: pointer;
  background: var(--tab-emails-ink); color: #fff; font-family: inherit; font-size: 13px; font-weight: 700;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--tab-emails) 26%, transparent);
  transition: transform 0.15s, filter 0.15s;
}
.ct-add:hover { transform: translateY(-1px); filter: brightness(0.92); }
.ct-add:focus-visible { outline: 2px solid var(--text); outline-offset: 2px; }

/* Content cards under the hero, like the Mail Agent's. */
.ct-card { padding: 18px; background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); box-shadow: var(--shadow-sm); }

/* Contacts: two columns that fill the window. */
.ct-grid { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
.ct-row {
  display: flex; align-items: center; gap: 12px; min-width: 0;
  padding: 12px 14px; border-radius: 12px;
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  transition: border-color 0.15s, box-shadow 0.15s;
}
.ct-row:hover { border-color: color-mix(in srgb, var(--tab-emails) 35%, white); box-shadow: 0 4px 14px rgba(24, 24, 24, 0.06); }
.ct-id { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.ct-name { font-size: 14px; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ct-person { font-weight: 500; color: var(--text-muted); }
.ct-mail { font-size: 12.5px; color: var(--text-muted); text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: end; }
.ct-mail:hover { color: var(--tab-emails-ink); text-decoration: underline; }
.ct-tools { display: flex; gap: 2px; opacity: 0; transition: opacity 0.15s; }
.ct-row:hover .ct-tools, .ct-row:focus-within .ct-tools { opacity: 1; }
.ct-icon {
  display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px;
  border: none; border-radius: 8px; background: transparent; color: var(--text-muted); cursor: pointer;
}
.ct-icon:hover { background: var(--bg); color: var(--text); }
.ct-icon--del:hover { background: var(--red-light); color: var(--red); }
.ct-icon:focus-visible { outline: 2px solid var(--tab-emails); outline-offset: 1px; }

/* Insurers with no address: a labelled row of "+" chips. */
.ct-missing { display: flex; flex-direction: column; gap: 10px; }
.ct-missing-title { margin: 0; display: flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 700; color: var(--text-secondary); }
.ct-missing-n { font-size: 11px; font-weight: 800; padding: 1px 7px; border-radius: 99px; background: var(--tab-emails-wash); color: var(--tab-emails-ink); }
.ct-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.ct-chip {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 99px; cursor: pointer;
  border: 1px dashed color-mix(in srgb, var(--tab-emails) 38%, white); background: #fff;
  font-family: inherit; font-size: 12.5px; font-weight: 600; color: var(--text-secondary);
  transition: all 0.15s;
}
.ct-chip svg { color: var(--tab-emails); }
.ct-chip:hover { border-style: solid; border-color: var(--tab-emails); color: var(--tab-emails-ink); background: var(--tab-emails-wash); }

.ct-empty { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 30px 0 10px; }
.ct-empty-text { margin: 0; font-size: 13.5px; color: var(--text-muted); }
.ct-loading { display: flex; justify-content: center; padding: 50px 0; }
.ct-spin { width: 26px; height: 26px; border-radius: 50%; border: 3px solid var(--tab-emails-wash); border-top-color: var(--tab-emails); animation: ct-spin 0.8s linear infinite; }
@keyframes ct-spin { to { transform: rotate(360deg); } }

@media (max-width: 720px) {
  .ct-hero { min-height: 0; }
  .ct-hero-copy { max-width: 100%; }
  .ct-hero-art { display: none; }
  .ct-hero::before { display: none; } /* the glow sits behind the art, which is hidden here */
  .ct-grid { grid-template-columns: 1fr; }
  .ct-tools { opacity: 1; }
}
@media (hover: none) { .ct-tools { opacity: 1; } }
</style>
