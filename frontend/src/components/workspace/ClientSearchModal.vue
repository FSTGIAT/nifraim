<template>
  <Teleport to="body">
    <!-- Grows out of the sidebar search button and folds back into it — the
         app's iPhone-style open (QA 2026-10-01). Hidden button (phone) → the
         plain fade below. -->
    <Transition name="search-modal" @enter="onEnter">
      <div v-if="open" class="cs-overlay" :class="{ 'cs-overlay--morph': morphing }" @click.self="close" @keydown.escape="close">
        <div ref="cardRef" class="cs-card" role="dialog" aria-labelledby="cs-title">
          <!-- Search bar -->
          <div class="cs-search-bar">
            <svg class="cs-search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="11" cy="11" r="8"/>
              <line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input
              ref="inputRef"
              v-model="query"
              type="text"
              class="cs-input"
              placeholder="חיפוש לפי שם או ת.ז…"
              @input="onInput"
              @keydown.escape="close"
            />
            <button class="cs-close" @click="close" aria-label="סגור">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>

          <!-- Results -->
          <div class="cs-results">
            <div v-if="searching" class="cs-state">מחפש…</div>
            <div v-else-if="query.length < 2" class="cs-state cs-state-hint">
              הקלידו לפחות 2 תווים — שם פרטי, שם משפחה או ת.ז
            </div>
            <div v-else-if="results.length === 0" class="cs-state cs-state-empty">
              לא נמצאו תוצאות עבור "{{ query }}"
            </div>
            <ul v-else class="cs-list">
              <li
                v-for="r in results"
                :key="r.id_number"
                class="cs-result"
                @click="openDetail(r.id_number, $event.currentTarget)"
              >
                <div class="cs-result-main">
                  <span class="cs-result-name">{{ r.name }}</span>
                  <span class="cs-result-id ltr-number">{{ r.id_number }}</span>
                </div>
                <div class="cs-result-meta">
                  <span class="cs-result-company">{{ r.company }}</span>
                  <span v-if="r.source === 'nifraim'" class="cs-result-tag">רק בנפרעים</span>
                  <span v-else class="cs-result-products ltr-number">{{ r.products }} מוצרים</span>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Client card (QA 2026-10-01): the app's shared window — grows from the
         result you clicked — with a summary strip and the products grouped by
         company. No cream header, no ₪0, a soft hover tint on every row. -->
    <DataModal :open="!!detail" :origin="detailOrigin" :title="detail?.name || ''"
               :subtitle="detail ? 'ת.ז ' + detail.id_number : ''" :layer="1120"
               accent="var(--primary)" @close="detail = null">
      <div v-if="detail" class="cc">
        <div class="cc-stats">
          <div v-if="detail.products.length" class="cc-stat">
            <span class="cc-lbl">מוצרים</span>
            <span class="cc-val ltr-number">{{ detail.products.length }}</span>
          </div>
          <div v-if="detail.total_paid >= 0.5" class="cc-stat">
            <span class="cc-lbl">עמלה שהתקבלה</span>
            <span class="cc-val cc-val--paid ltr-number">{{ money(detail.total_paid) }}</span>
          </div>
          <div v-if="detail.total_accumulation >= 0.5" class="cc-stat">
            <span class="cc-lbl">צבירה</span>
            <span class="cc-val ltr-number">{{ money(detail.total_accumulation) }}</span>
          </div>
          <div v-if="detail.total_premium >= 0.5" class="cc-stat">
            <span class="cc-lbl">פרמיה</span>
            <span class="cc-val ltr-number">{{ money(detail.total_premium) }}</span>
          </div>
          <div v-if="groups.length" class="cc-stat">
            <span class="cc-lbl">חברות</span>
            <span class="cc-val ltr-number">{{ groups.length }}</span>
          </div>
        </div>

        <!-- Only in נפרעים: say so plainly, then show what was paid. -->
        <div v-if="!detail.in_production" class="cc-note">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/></svg>
          הלקוח לא מופיע בקובץ הפרודוקציה — רק בנפרעים
        </div>

        <section v-for="(g, gi) in groups" :key="g.company" class="cc-group" :style="{ '--d': gi * 60 + 'ms' }">
          <header class="cc-ghead">
            <span class="cc-logo"><CompanyLogo :company="g.company" :size="20" :frame="false" /></span>
            <span class="cc-gname">{{ g.company }}</span>
            <span class="cc-gcount ltr-number">{{ g.items.length }}</span>
            <span v-if="g.accumulation >= 0.5" class="cc-gsum ltr-number">{{ money(g.accumulation) }}</span>
            <span v-else-if="g.premium >= 0.5" class="cc-gsum ltr-number">{{ money(g.premium) }} פרמיה</span>
          </header>
          <table class="cc-table">
            <thead>
              <tr>
                <th>מוצר</th><th>פוליסה</th>
                <th v-if="g.hasPrem" class="num">פרמיה</th>
                <th v-if="g.hasAcc" class="num">צבירה</th>
                <th v-if="g.hasStatus">סטטוס</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(p, i) in g.items" :key="i">
                <td class="cc-prod">{{ p.product }}</td>
                <td><span class="ltr-number cc-pol">{{ p.policy_number }}</span></td>
                <td v-if="g.hasPrem" class="num"><span v-if="p.premium >= 0.5" class="ltr-number">{{ money(p.premium) }}</span></td>
                <td v-if="g.hasAcc" class="num"><span v-if="p.accumulation >= 0.5" class="ltr-number">{{ money(p.accumulation) }}</span></td>
                <td v-if="g.hasStatus">
                  <span v-if="realStatus(p.status)" class="cc-status" :class="{ 'cc-status--off': p.status !== 'פעיל' }">{{ p.status }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </section>
        <!-- What the current נפרעים paid on this customer, per company. -->
        <section v-if="paidGroups.length" class="cc-group cc-group--paid">
          <header class="cc-ghead">
            <span class="cc-gname">עמלות שהתקבלו</span>
            <span class="cc-gsum ltr-number">{{ money(detail.total_paid) }}</span>
          </header>
          <table class="cc-table">
            <thead><tr><th>מוצר</th><th>חברה</th><th>פוליסה</th><th class="num">עמלה</th></tr></thead>
            <tbody>
              <tr v-for="(p, i) in detail.paid" :key="'p' + i">
                <td class="cc-prod">{{ p.product }}</td>
                <td><span class="cc-co"><CompanyLogo :company="p.company" :size="16" :frame="false" />{{ shortCo(p.company) }}</span></td>
                <td><span class="ltr-number cc-pol">{{ p.policy_number }}</span></td>
                <td class="num"><span v-if="Math.abs(p.commission) >= 0.5" class="ltr-number">{{ money(p.commission) }}</span></td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>
    </DataModal>
  </Teleport>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import api from '../../api/client.js'
import { useOriginMorph } from '../../composables/useOriginMorph'
import DataModal from './DataModal.vue'
import CompanyLogo from './CompanyLogo.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open'])

const inputRef = ref(null)
const query = ref('')
const results = ref([])
const searching = ref(false)
const detail = ref(null)
const detailOrigin = ref(null)

// Products grouped by company, the biggest book first.
const groups = computed(() => {
  const by = new Map()
  for (const p of detail.value?.products || []) {
    const k = p.company || '—'
    if (!by.has(k)) by.set(k, { company: k, items: [], accumulation: 0, premium: 0 })
    const g = by.get(k)
    g.items.push(p)
    g.accumulation += Number(p.accumulation) || 0
    g.premium += Number(p.premium) || 0
  }
  // A column shows only when this company has something to put in it.
  for (const g of by.values()) {
    g.hasPrem = g.items.some(p => Number(p.premium) >= 0.5)
    g.hasAcc = g.items.some(p => Number(p.accumulation) >= 0.5)
    g.hasStatus = g.items.some(p => realStatus(p.status))
  }
  return [...by.values()].sort((a, b) => (b.accumulation + b.premium * 12) - (a.accumulation + a.premium * 12))
})

let timer = null

const cardRef = ref(null)
const morph = useOriginMorph()
const morphing = ref(false)
function onEnter(el) {
  if (morph.hasOrigin()) morph.grow(el.querySelector('.cs-card'))
}
let closing = false

async function close() {
  if (closing) return
  closing = true
  try {
    if (morph.hasOrigin() && cardRef.value) await morph.shrink(cardRef.value)
  } finally { closing = false }
  emit('update:open', false)
  // Reset so next open starts fresh.
  setTimeout(() => {
    query.value = ''
    results.value = []
    detail.value = null
  }, 200)
}

function onInput() {
  clearTimeout(timer)
  const q = query.value.trim()
  if (q.length < 2) {
    results.value = []
    searching.value = false
    return
  }
  searching.value = true
  timer = setTimeout(async () => {
    try {
      const res = await api.get('/production/clients', { params: { search: q } })
      results.value = (res.data || []).slice(0, 10)
    } catch {
      results.value = []
    } finally {
      searching.value = false
    }
  }, 300)
}

async function openDetail(idNumber, el = null) {
  detailOrigin.value = el
  try {
    const res = await api.get(`/production/clients/${idNumber}`)
    detail.value = res.data
  } catch {
    /* not found — leave previous detail state */
  }
}

const paidGroups = computed(() => detail.value?.paid || [])
// Legal entity → brand for the narrow column ("מנורה מבטחים ביטוח בע"מ" → "מנורה").
const shortCo = n => String(n || '').split(/\s+/)[0] || n
// "—" / "-" / blank mean "not reported" — show nothing, never a dash.
const realStatus = s => !!s && !/^[\s\-—–]*$/.test(String(s))
const money = v => `₪${Math.round(Number(v) || 0).toLocaleString()}`

// Measure the search button BEFORE the card exists (flush: 'pre'), so the
// enter hook can grow it from its first frame.
watch(() => props.open, (now) => {
  if (!now) return
  const btn = document.querySelector('[data-rail-key="search"]')
  morph.remember(btn && btn.offsetParent !== null ? btn : null)
  morphing.value = morph.hasOrigin()
})

// Autofocus + key listener when opened
watch(() => props.open, async (now) => {
  if (now) {
    await nextTick()
    inputRef.value?.focus()
  }
})
</script>

<style scoped>
.cs-overlay {
  position: fixed;
  inset: 0;
  z-index: 1100;
  background: rgba(45, 37, 34, 0.45);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 12vh;
  font-family: 'Heebo', sans-serif;
  direction: rtl;
}

.cs-card {
  width: min(640px, 92vw);
  background: #FFFFFF;
  border-radius: 14px;
  box-shadow:
    0 24px 56px rgba(45, 37, 34, 0.30),
    0 4px 12px rgba(45, 37, 34, 0.10);
  overflow: hidden;
}

.cs-search-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  border-bottom: 1px solid rgba(45, 37, 34, 0.06);
}

.cs-search-icon { color: var(--primary); flex-shrink: 0; }

.cs-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font: 500 17px/1.4 'Heebo', sans-serif;
  color: #2D2522;
  direction: rtl;
  text-align: right;
}
.cs-input::placeholder { color: rgba(45, 37, 34, 0.4); }

.cs-close {
  display: flex; align-items: center; justify-content: center;
  width: 32px; height: 32px;
  border: none; outline: none;
  background: rgba(45, 37, 34, 0.05);
  color: rgba(45, 37, 34, 0.6);
  border-radius: 50%;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}
.cs-close:hover { background: rgba(24, 24, 24, 0.10); color: var(--primary); }

.cs-results {
  max-height: 50vh;
  overflow-y: auto;
}

.cs-state {
  padding: 32px 24px;
  text-align: center;
  font-size: 14px;
  color: rgba(45, 37, 34, 0.55);
}
.cs-state-hint { color: rgba(45, 37, 34, 0.45); }
.cs-state-empty { color: rgba(45, 37, 34, 0.55); }

.cs-list {
  list-style: none;
  margin: 0;
  padding: 6px 0;
}

.cs-result {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 18px;
  cursor: pointer;
  transition: background 0.12s ease;
  border-bottom: 1px solid rgba(45, 37, 34, 0.04);
}
.cs-result:last-child { border-bottom: none; }
.cs-result:hover { background: color-mix(in srgb, var(--chart-9, #2F73C4) 8%, transparent); }

.cs-result-main {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
}
.cs-result-name {
  font-weight: 700;
  font-size: 14px;
  color: #2D2522;
}
.cs-result-id {
  font-size: 12px;
  color: rgba(45, 37, 34, 0.55);
  letter-spacing: 0.02em;
}

.cs-result-meta {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 12px;
  font-size: 12px;
}
.cs-result-company { color: var(--primary); font-weight: 600; }
.cs-result-products { color: rgba(45, 37, 34, 0.5); }

/* ── Client card ── */
.cc { display: flex; flex-direction: column; gap: 14px; }
.cc-stats { display: flex; border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; }
.cc-stat { flex: 1; display: flex; flex-direction: column; align-items: flex-start; gap: 4px; padding: 13px 16px; }
.cc-stat + .cc-stat { border-inline-start: 1px solid var(--border-subtle); }
.cc-lbl { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.cc-val { font-size: 20px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; }

.cc-group {
  border: 1px solid var(--border-subtle); border-radius: 14px; overflow: hidden; background: var(--card-bg);
  animation: ccIn 0.4s cubic-bezier(0.2, 0, 0.2, 1) both; animation-delay: var(--d);
}
@keyframes ccIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
.cc-ghead { display: flex; align-items: center; gap: 10px; padding: 11px 14px; border-bottom: 1px solid var(--border-subtle); }
.cc-logo { width: 30px; height: 30px; border-radius: 8px; background: var(--bg); display: inline-flex; align-items: center; justify-content: center; }
.cc-gname { font-size: 14px; font-weight: 700; color: var(--text); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cc-gcount {
  min-width: 22px; height: 22px; padding: 0 7px; border-radius: 11px; background: var(--bg);
  font-size: 12px; font-weight: 700; color: var(--text-muted); display: inline-flex; align-items: center; justify-content: center;
}
.cc-gsum { font-size: 14px; font-weight: 800; color: var(--text); }

.cc-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 13px; }
.cc-table th {
  text-align: right; font-size: 11.5px; font-weight: 600; color: var(--text-muted);
  padding: 8px 14px; background: transparent; border-bottom: 1px solid var(--border-subtle);
}
.cc-table th:nth-child(1) { width: 34%; }
.cc-table th.num, .cc-table td.num { text-align: center; width: 15%; }
.cc-table td { padding: 10px 14px; border-bottom: 1px solid var(--border-subtle); color: var(--text); }
.cc-table tbody tr:last-child td { border-bottom: none; }
.cc-table tbody tr { transition: background 0.15s ease; }
/* Hover: a light wash of the app's blue — no cream (QA 2026-10-01). */
.cc-table tbody tr:hover { background: color-mix(in srgb, var(--chart-9, #2F73C4) 8%, transparent); }
.cc-prod { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cc-pol { color: var(--text-muted); font-size: 12.5px; }
.cc-val--paid { color: var(--green, #2E844A); }
.cc-note {
  display: flex; align-items: center; gap: 8px; padding: 10px 14px; border-radius: 12px;
  background: color-mix(in srgb, var(--tab-portal, #4E9DD0) 10%, var(--card-bg));
  color: var(--tab-portal-ink, #35719A); font-size: 13px; font-weight: 600;
}
.cc-co { display: inline-flex; align-items: center; gap: 6px; font-weight: 600; }
.cs-result-tag {
  font-size: 11.5px; font-weight: 700; padding: 2px 8px; border-radius: 10px;
  background: color-mix(in srgb, var(--tab-portal, #4E9DD0) 14%, transparent); color: var(--tab-portal-ink, #35719A);
}
.cc-status { font-size: 12px; font-weight: 600; color: var(--green, #2E844A); }
.cc-status--off {
  color: var(--text-muted); background: var(--bg); padding: 2px 8px; border-radius: 10px;
}
@media (max-width: 640px) {
  .cc-stats { display: grid; grid-template-columns: 1fr 1fr; }
  .cc-stat { padding: 10px 12px; border-top: 1px solid var(--border-subtle); }
  .cc-stat:nth-child(-n+2) { border-top: none; }
  .cc-stat:nth-child(odd) { border-inline-start: none; }
  .cc-table th:nth-child(2), .cc-table td:nth-child(2) { display: none; }
  .cc-table th:nth-child(1) { width: 40%; }
  .cc-table td, .cc-table th { padding: 9px 10px; }
}
@media (prefers-reduced-motion: reduce) { .cc-group { animation: none; } .cc-table tbody tr { transition: none; } }

/* Growing from the button: the morph owns the card's transform. */
.cs-overlay--morph.search-modal-enter-active .cs-card,
.cs-overlay--morph.search-modal-leave-active .cs-card { transition: none; }
.cs-overlay--morph.search-modal-enter-from,
.cs-overlay--morph.search-modal-leave-to { transform: none; }

/* ── Transition ── */
.search-modal-enter-active,
.search-modal-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.search-modal-enter-from,
.search-modal-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
