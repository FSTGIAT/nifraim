<template>
  <!-- אנשי קשר — window content (ContactsModal). Built for the window: a
       header strip with the one action, contacts filling the width in two
       columns, and the insurers still missing an address as "+" chips. -->
  <div class="ct">
    <!-- Hero — the tabs' shape: kicker, two-colour title, the counters, the
         actions, and the contacts' own loop (TabHeroLoop 'contacts'). -->
    <header class="ct-hero">
      <div class="ct-hero-copy">
        <span class="ct-kicker">ספר כתובות</span>
        <h2 class="ct-hero-title">אנשי <span class="ct-hero-title-acc">קשר</span></h2>
        <div class="ct-stats">
          <button type="button" class="ct-app" aria-label="לקוחות חדשים — פתיחת אנשי הקשר" @click="openApp">
            <span ref="appIconEl" class="ct-app-ico">
              <svg viewBox="0 0 60 60" width="100%" height="100%" aria-hidden="true">
                <rect x="13" y="10" width="34" height="42" rx="5" fill="#fff" opacity="0.96" />
                <circle cx="30" cy="25" r="6.5" fill="var(--tab-emails-ink)" />
                <path d="M19.5 42 a10.5 8.5 0 0 1 21 0 z" fill="var(--tab-emails-ink)" />
                <rect x="47" y="15" width="4" height="7" rx="1.5" fill="#fff" opacity="0.85" />
                <rect x="47" y="25" width="4" height="7" rx="1.5" fill="#fff" opacity="0.6" />
                <rect x="47" y="35" width="4" height="7" rx="1.5" fill="#fff" opacity="0.4" />
              </svg>
              <span v-if="walkins.length" class="ct-app-badge ltr-number">{{ walkins.length }}</span>
            </span>
            <span class="ct-stat-l">לקוחות חדשים</span>
          </button>
          <button type="button" class="ct-app" aria-label="חברות — פתיחת אנשי הקשר של החברות" @click="coOpen = true">
            <span ref="coIconEl" class="ct-app-ico ct-app-ico--co">
              <svg viewBox="0 0 60 60" width="100%" height="100%" aria-hidden="true">
                <path d="M14 46 V22 l16 -9 16 9 v24 z" fill="#fff" opacity="0.96" />
                <rect x="20" y="27" width="5" height="5" rx="1" fill="var(--tab-emails-ink)" />
                <rect x="27.5" y="27" width="5" height="5" rx="1" fill="var(--tab-emails-ink)" />
                <rect x="35" y="27" width="5" height="5" rx="1" fill="var(--tab-emails-ink)" />
                <rect x="26" y="36" width="8" height="10" rx="1.5" fill="var(--tab-emails-ink)" />
              </svg>
              <span v-if="contacts.length && missingCompanies.length" class="ct-app-badge ltr-number">{{ missingCompanies.length }}</span>
            </span>
            <span class="ct-stat-l">חברות<template v-if="contacts.length"> · <span class="ltr-number">{{ contacts.length }}</span></template></span>
          </button>
        </div>
        <div class="ct-meta">
          <button class="ct-add" type="button" @click="openWalkin()">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/></svg>
            לקוח חדש
          </button>
          <button class="ct-add ct-add--ghost" type="button" @click="openAddForm()">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>
            חברה
          </button>
        </div>
      </div>
      <TabHeroLoop scene="contacts" class="ct-hero-art" />
    </header>

    <ContactsAppSheet :open="coOpen" :origin="coIconEl" kind="companies" title="חברות" :walkins="companyRows"
                      :missing="missingCompanies.map((m) => m.label)" @close="coOpen = false"
                      @add="(m) => openAddForm(typeof m === 'string' ? m : '')" @edit="(r) => startEdit(r.raw)"
                      @delete="deleteContact" @seed="seedContacts" />
    <ContactsAppSheet :open="appOpen" :origin="appIconEl" :walkins="walkins" @close="appOpen = false"
                      @add="openWalkin()" @edit="openWalkin" @delete="deleteWalkin" />
    <WalkinFormModal :show="walkinOpen" :editing="editingWalkin" @close="walkinOpen = false" @saved="onWalkinSaved" />

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
import WalkinFormModal from './WalkinFormModal.vue'
import ContactsAppSheet from './ContactsAppSheet.vue'
import TabHeroLoop from './TabHeroLoop.vue'
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

onMounted(() => { fetchContacts(); fetchWalkins() })

// ── לקוחות חדשים (walk-in customers) ──
const phoneFmt = (p) => { const d = String(p || '').replace(/\D/g, ''); return d.length === 10 ? `${d.slice(0, 3)}-${d.slice(3)}` : d.length === 9 ? `${d.slice(0, 2)}-${d.slice(2)}` : p }
const walkins = ref([])
const walkinOpen = ref(false)
const appOpen = ref(false)
const appIconEl = ref(null)
function openApp() { appOpen.value = true }
// the insurers as the second app: rows shaped like the walk-in rows
const coOpen = ref(false)
const coIconEl = ref(null)
const companyRows = computed(() => contacts.value.map((c) => ({
  id: c.id, name: c.company_name, email: c.email, contact_name: c.contact_name, notes: c.notes, raw: c,
})))
const editingWalkin = ref(null)
async function fetchWalkins() {
  try { walkins.value = (await api.get('/walkin-customers')).data || [] } catch { walkins.value = [] }
}
function openWalkin(w = null) {
  editingWalkin.value = w
  walkinOpen.value = true
}
async function onWalkinSaved() {
  walkinOpen.value = false
  editingWalkin.value = null
  await fetchWalkins()
}
async function deleteWalkin(id) {
  await api.delete(`/walkin-customers/${id}`)
  await fetchWalkins()
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

/* ── Hero: centred, it fills the round window (RailWindow round) ── */
.ct-hero {
  position: relative; display: flex; flex-direction: column; align-items: center; text-align: center;
  padding: 0; background: none;
}
.ct-hero::before {
  content: ''; position: absolute; left: 50%; top: 18%; width: 120%; aspect-ratio: 1; transform: translate(-50%, -50%);
  background: radial-gradient(circle, var(--tab-emails-wash), transparent 62%); pointer-events: none;
}
.ct-hero-art { position: relative; order: -1; width: min(250px, 70%); aspect-ratio: 420 / 300; margin-bottom: -6px; pointer-events: none; }
.ct-hero-copy { position: relative; z-index: 2; display: flex; flex-direction: column; align-items: center; gap: 6px; min-width: 0; }
.ct-kicker {
  align-self: center; padding: 4px 11px; border-radius: 999px; font-size: 11.5px; font-weight: 800;
  background: var(--tab-emails-wash); color: var(--tab-emails-ink);
}
.ct-hero-title {
  align-self: center; margin: 4px 0 0; font-family: 'Heebo', sans-serif;
  font-size: clamp(30px, 3.6vw, 44px); font-weight: 900; letter-spacing: -0.03em; line-height: 1.05; color: var(--text);
}
.ct-hero-title-acc { color: var(--tab-emails-ink); }
.ct-stats { display: flex; align-items: flex-end; justify-content: center; gap: 36px; margin-top: 10px; flex-wrap: wrap; }
.ct-stat { display: flex; flex-direction: column; align-items: flex-start; padding: 4px 8px; margin: -4px -8px; border-radius: var(--radius-sm); }
.ct-stat--btn { font-family: inherit; text-align: start; background: none; border: none; cursor: pointer; }
.ct-stat--btn:hover { background: var(--tab-emails-wash); }
.ct-stat--btn:focus-visible { outline: 2px solid var(--tab-emails); outline-offset: 2px; }
/* the walk-in customers as an iPhone app icon — opens the Contacts app (ContactsAppSheet) */
.ct-app { display: flex; flex-direction: column; align-items: center; gap: 5px; padding: 0; margin: -2px 0 0;
  border: none; background: none; cursor: pointer; font-family: inherit; }
.ct-app-ico { position: relative; width: 56px; height: 56px; border-radius: 50%; display: block;
  background: linear-gradient(160deg, var(--tab-emails), var(--tab-emails-ink));
  box-shadow: 0 6px 16px color-mix(in srgb, var(--tab-emails) 35%, transparent), inset 0 1px 0 rgba(255, 255, 255, 0.35);
  transition: transform 0.2s cubic-bezier(0.32, 0.72, 0, 1); }
.ct-app-ico svg { position: relative; z-index: 1; padding: 3px; }
/* the ring waves of the hero's ringing phone, around each app */
.ct-app-ico::before, .ct-app-ico::after {
  content: ''; position: absolute; inset: 0; border-radius: 50%; pointer-events: none;
  border: 2px solid color-mix(in srgb, var(--tab-emails) 45%, transparent);
  animation: ctRing 3.2s cubic-bezier(0.22, 1, 0.36, 1) infinite;
}
.ct-app-ico::after { animation-delay: 0.5s; }
.ct-app:nth-child(2) .ct-app-ico::before, .ct-app:nth-child(2) .ct-app-ico::after { animation-delay: 1.6s, 2.1s; }
@keyframes ctRing { 0% { transform: scale(1); opacity: 0.8; } 60%, 100% { transform: scale(1.55); opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .ct-app-ico::before, .ct-app-ico::after { animation: none; opacity: 0; } }
.ct-app:hover .ct-app-ico { transform: translateY(-2px) scale(1.04); }
.ct-app:active .ct-app-ico { transform: scale(0.94); }
.ct-app:focus-visible { outline: none; }
.ct-app:focus-visible .ct-app-ico { outline: 2px solid var(--text); outline-offset: 3px; }
/* the companies app: white icon, magenta building — the walk-ins app is the filled one */
.ct-app-ico--co { background: #fff; box-shadow: 0 6px 16px rgba(24, 24, 24, 0.08), inset 0 0 0 1px var(--border-subtle); }
.ct-app-ico--co svg path { fill: var(--tab-emails); opacity: 1; }
.ct-app-ico--co svg rect { fill: #fff; }
.ct-app-badge { position: absolute; z-index: 2; top: -4px; inset-inline-end: -4px; min-width: 20px; height: 20px; padding: 0 5px;
  border-radius: 99px; display: grid; place-items: center; font-size: 11.5px; font-weight: 800; color: #fff;
  background: var(--red, #D93025); box-shadow: 0 0 0 2px var(--card-bg); }
.ct-stat-n { font-size: 26px; font-weight: 800; line-height: 1.1; color: var(--text); font-variant-numeric: tabular-nums; }
.ct-stat--hot .ct-stat-n { color: var(--tab-emails-ink); }
.ct-stat-l { font-size: 11.5px; font-weight: 600; color: var(--text-muted); }
.ct-meta { display: flex; align-items: center; justify-content: center; gap: 8px; flex-wrap: wrap; margin-top: 18px; }
.ct-add {
  display: inline-flex; align-items: center; gap: 7px; padding: 9px 16px; border: none; border-radius: 10px; cursor: pointer;
  background: var(--tab-emails-ink); color: #fff; font-family: inherit; font-size: 13.5px; font-weight: 700;
  box-shadow: 0 4px 12px color-mix(in srgb, var(--tab-emails) 26%, transparent); transition: transform 0.15s, filter 0.15s;
}
.ct-add:hover { transform: translateY(-1px); filter: brightness(0.92); }
.ct-add:focus-visible { outline: 2px solid var(--text); outline-offset: 2px; }
.ct-add--ghost { background: var(--card-bg); color: var(--text); border: 1px solid var(--border); box-shadow: none; }
.ct-add--ghost:hover { filter: none; border-color: var(--text-muted); }

/* Sections: one white card each; rows are flat lines inside it, not boxes in a box. */
.ct-card { padding: 16px 18px; background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); box-shadow: var(--shadow-sm); }
.ct-sec-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 6px; }
.ct-sec-title { margin: 0; display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 800; color: var(--text); }
.ct-sec-n { font-size: 11px; font-weight: 800; padding: 1px 7px; border-radius: 99px; background: var(--tab-emails-wash); color: var(--tab-emails-ink); }
.ct-sec-note { font-size: 12.5px; color: var(--text-muted); }
.ct-list { list-style: none; margin: 0; padding: 0; display: grid; grid-template-columns: minmax(0, 1fr); column-gap: 28px; }
.ct-list--two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
.ct-row {
  display: flex; align-items: center; gap: 12px; min-width: 0; padding: 11px 2px;
  border-bottom: 1px solid var(--border-subtle);
}
.ct-id { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.ct-name { font-size: 14px; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ct-person { font-weight: 500; color: var(--text-muted); }
.ct-sub { font-size: 12.5px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ct-mail { align-self: flex-start; max-width: 100%; font-size: 12.5px; color: var(--text-muted); text-decoration: none; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.ct-mail:hover { color: var(--tab-emails-ink); text-decoration: underline; }
.ct-tools { display: flex; gap: 2px; opacity: 0.45; transition: opacity 0.15s; }
.ct-row:hover .ct-tools, .ct-row:focus-within .ct-tools { opacity: 1; }
.ct-icon {
  display: inline-flex; align-items: center; justify-content: center; width: 30px; height: 30px;
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
  .ct-hero-art { width: min(220px, 70%); }
  .ct-list--two { grid-template-columns: 1fr; }
  .ct-tools { opacity: 1; }
}
@media (hover: none) { .ct-tools { opacity: 1; } }
</style>
