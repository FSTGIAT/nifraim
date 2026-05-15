<template>
  <Teleport to="body">
    <Transition name="search-modal">
      <div v-if="open" class="cs-overlay" @click.self="close" @keydown.escape="close">
        <div class="cs-card" role="dialog" aria-labelledby="cs-title">
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
                @click="openDetail(r.id_number)"
              >
                <div class="cs-result-main">
                  <span class="cs-result-name">{{ r.name }}</span>
                  <span class="cs-result-id ltr-number">{{ r.id_number }}</span>
                </div>
                <div class="cs-result-meta">
                  <span class="cs-result-company">{{ r.company }}</span>
                  <span class="cs-result-products ltr-number">{{ r.products }} מוצרים</span>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Client Detail modal — opens on row click; reuses the legacy
         WorkspaceHeader card pattern so the look stays consistent. -->
    <Transition name="search-modal">
      <div v-if="detail" class="cs-detail-overlay" @click.self="detail = null">
        <div class="cs-detail-card">
          <div class="cs-detail-header">
            <div>
              <h4>{{ detail.name }}</h4>
              <span class="cs-detail-id ltr-number">ת.ז {{ detail.id_number }}</span>
            </div>
            <button class="cs-close" @click="detail = null" aria-label="סגור">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div class="cs-kpi-row">
            <div class="cs-kpi">
              <span class="cs-kpi-val ltr-number">{{ formatCurrency(detail.total_premium) }}</span>
              <span class="cs-kpi-label">פרמיה</span>
            </div>
            <div class="cs-kpi">
              <span class="cs-kpi-val ltr-number">{{ formatCurrency(detail.total_accumulation) }}</span>
              <span class="cs-kpi-label">צבירה</span>
            </div>
            <div class="cs-kpi">
              <span class="cs-kpi-val ltr-number">{{ detail.products.length }}</span>
              <span class="cs-kpi-label">מוצרים</span>
            </div>
          </div>
          <div class="cs-detail-table-scroll">
            <table class="cs-detail-table">
              <thead>
                <tr>
                  <th>מוצר</th>
                  <th>חברה</th>
                  <th class="th-num">פרמיה</th>
                  <th class="th-num">צבירה</th>
                  <th>סטטוס</th>
                  <th>פוליסה</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(p, i) in detail.products" :key="i">
                  <td>{{ p.product }}</td>
                  <td>{{ p.company }}</td>
                  <td class="td-num"><span class="ltr-number">{{ formatCurrency(p.premium) }}</span></td>
                  <td class="td-num"><span class="ltr-number">{{ formatCurrency(p.accumulation) }}</span></td>
                  <td>{{ p.status }}</td>
                  <td><span class="ltr-number">{{ p.policy_number }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, nextTick, watch } from 'vue'
import api from '../../api/client.js'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open'])

const inputRef = ref(null)
const query = ref('')
const results = ref([])
const searching = ref(false)
const detail = ref(null)

let timer = null

function close() {
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

async function openDetail(idNumber) {
  try {
    const res = await api.get(`/production/clients/${idNumber}`)
    detail.value = res.data
  } catch {
    /* not found — leave previous detail state */
  }
}

function formatCurrency(val) {
  if (!val) return '₪0'
  return `₪${Math.round(val).toLocaleString()}`
}

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

.cs-search-icon { color: #E8660A; flex-shrink: 0; }

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
.cs-close:hover { background: rgba(232, 102, 10, 0.10); color: #E8660A; }

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
.cs-result:hover { background: rgba(232, 102, 10, 0.06); }

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
.cs-result-company { color: #E8660A; font-weight: 600; }
.cs-result-products { color: rgba(45, 37, 34, 0.5); }

/* ── Detail modal (opens on result click) ── */
.cs-detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 1110;
  background: rgba(45, 37, 34, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  font-family: 'Heebo', sans-serif;
  direction: rtl;
}
.cs-detail-card {
  width: min(880px, 96vw);
  max-height: 88vh;
  background: #FFFFFF;
  border-radius: 14px;
  box-shadow:
    0 28px 60px rgba(45, 37, 34, 0.35),
    0 6px 16px rgba(45, 37, 34, 0.12);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.cs-detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px;
  border-bottom: 1px solid rgba(45, 37, 34, 0.06);
}
.cs-detail-header h4 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: #2D2522;
}
.cs-detail-id {
  font-size: 12px;
  color: rgba(45, 37, 34, 0.55);
  letter-spacing: 0.02em;
}
.cs-kpi-row {
  display: flex;
  gap: 12px;
  padding: 16px 22px;
  background: linear-gradient(135deg, rgba(232, 102, 10, 0.06), rgba(245, 124, 0, 0.02));
}
.cs-kpi {
  flex: 1;
  background: #FFFFFF;
  border: 1px solid rgba(45, 37, 34, 0.06);
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.cs-kpi-val { font-size: 18px; font-weight: 800; color: #2D2522; }
.cs-kpi-label { font-size: 11px; color: rgba(45, 37, 34, 0.55); font-weight: 600; }

.cs-detail-table-scroll {
  flex: 1;
  overflow: auto;
  padding: 0 22px 22px;
}
.cs-detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.cs-detail-table th {
  position: sticky; top: 0;
  background: #FBF4ED;
  color: rgba(45, 37, 34, 0.7);
  font-weight: 700;
  text-align: right;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(45, 37, 34, 0.10);
}
.cs-detail-table th.th-num { text-align: left; }
.cs-detail-table td {
  padding: 10px 12px;
  border-bottom: 1px solid rgba(45, 37, 34, 0.04);
  color: #2D2522;
}
.cs-detail-table td.td-num { text-align: left; }

/* ── Transition ── */
.search-modal-enter-active,
.search-modal-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.search-modal-enter-from,
.search-modal-leave-to { opacity: 0; transform: translateY(-8px); }
</style>
