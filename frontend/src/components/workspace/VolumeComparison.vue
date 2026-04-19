<template>
  <div class="volume-comparison">
    <!-- No production file -->
    <div v-if="!hasProduction" class="empty-state">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
        <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
      </svg>
      <p>יש להעלות קובץ פרודוקציה לפני השוואה מול היקפים</p>
    </div>

    <!-- No result: show uploader -->
    <div v-else-if="!volumeStore.comparisonResult && !volumeStore.loading" class="upload-section">
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
          <defs>
            <linearGradient id="vwg1" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#F57C00" stop-opacity="0.10"/>
              <stop offset="30%" stop-color="#FF9800" stop-opacity="0.06"/>
              <stop offset="60%" stop-color="#FFB74D" stop-opacity="0.10"/>
              <stop offset="100%" stop-color="#F57C00" stop-opacity="0.05"/>
            </linearGradient>
          </defs>
          <path fill="url(#vwg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
        </svg>
        <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
          <defs>
            <linearGradient id="vwg2" x1="100%" y1="0%" x2="0%" y2="0%">
              <stop offset="0%" stop-color="#FFB74D" stop-opacity="0.08"/>
              <stop offset="40%" stop-color="#F57C00" stop-opacity="0.05"/>
              <stop offset="70%" stop-color="#FF9800" stop-opacity="0.08"/>
              <stop offset="100%" stop-color="#FFB74D" stop-opacity="0.04"/>
            </linearGradient>
          </defs>
          <path fill="url(#vwg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
        </svg>
        <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
          <defs>
            <linearGradient id="vwg3" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="#FF9800" stop-opacity="0.06"/>
              <stop offset="50%" stop-color="#FFB74D" stop-opacity="0.04"/>
              <stop offset="100%" stop-color="#F57C00" stop-opacity="0.07"/>
            </linearGradient>
          </defs>
          <path fill="url(#vwg3)" d="M0,150L60,143.3C120,137,240,123,360,126.7C480,130,600,150,720,153.3C840,157,960,143,1080,133.3C1200,123,1320,117,1380,113.3L1440,110L1440,200L0,200Z"/>
        </svg>
      </div>

      <button class="upload-btn" @click="$refs.fileInput.click()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="17 8 12 3 7 8"/>
          <line x1="12" y1="3" x2="12" y2="15"/>
        </svg>
        <span>העלה דוח היקפים להשוואה</span>
      </button>
      <input ref="fileInput" type="file" accept=".xlsx,.xls" @change="onFileSelect" style="display:none" />

      <!-- Encrypted file option -->
      <div class="options-row">
        <label class="toggle-label">
          <div class="toggle" :class="{ on: needPassword }">
            <input type="checkbox" v-model="needPassword" />
            <div class="toggle-track"><div class="toggle-thumb"></div></div>
          </div>
          <span>קובץ מוצפן</span>
        </label>
      </div>

      <Transition name="slide-down">
        <div class="password-field" v-if="needPassword">
          <input type="password" v-model="password" placeholder="סיסמת הקובץ..." dir="ltr" />
        </div>
      </Transition>
    </div>

    <!-- Loading -->
    <div v-else-if="volumeStore.loading" class="loading-state">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring delay"></div>
      </div>
      <span>מנתח דוח היקפים...</span>
    </div>

    <!-- Results -->
    <div v-else-if="volumeStore.comparisonResult" class="results-section">
      <div class="results-header">
        <h4>השוואה מול היקפים</h4>
        <button class="btn-back" @click="volumeStore.reset()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"/>
            <polyline points="12 19 5 12 12 5"/>
          </svg>
          חזרה
        </button>
      </div>

      <!-- Summary KPI strip -->
      <div class="summary-strip">
        <div class="summary-badge badge-green" @click="openModal('matched')">
          <span class="ltr-number">{{ result.summary.matched_count }}</span>
          <span>תואמים</span>
        </div>
        <div class="summary-badge badge-amber" @click="openModal('production_only')">
          <span class="ltr-number">{{ result.summary.in_production_only_count }}</span>
          <span>בפרודוקציה בלבד</span>
        </div>
        <div class="summary-badge badge-blue" @click="openModal('volume_only')">
          <span class="ltr-number">{{ result.summary.in_volume_only_count }}</span>
          <span>בהיקפים בלבד</span>
        </div>
        <div class="summary-badge badge-purple" @click="openModal('recruits')">
          <span class="ltr-number">{{ result.summary.in_recruits_not_volume_count }}</span>
          <span>מגויסים חסרים</span>
        </div>
      </div>

      <!-- Volume totals -->
      <div class="volume-totals">
        <div class="vt-card">
          <span class="vt-label">סה"כ הפקדות</span>
          <span class="vt-value ltr-number">{{ formatCurrency(result.summary.total_volume_deposits) }}</span>
        </div>
        <div class="vt-card">
          <span class="vt-label">תפוקה לאחר ביטולים</span>
          <span class="vt-value ltr-number">{{ formatCurrency(result.summary.total_volume_production_after_cancel) }}</span>
        </div>
        <div class="vt-card">
          <span class="vt-label">לקוחות בהיקפים</span>
          <span class="vt-value ltr-number">{{ result.summary.total_volume_clients }}</span>
        </div>
        <div class="vt-card">
          <span class="vt-label">לקוחות בפרודוקציה</span>
          <span class="vt-value ltr-number">{{ result.summary.total_production_clients }}</span>
        </div>
      </div>

      <!-- Donut chart -->
      <div class="chart-row">
        <div class="chart-card">
          <h5>התפלגות לקוחות</h5>
          <apexchart
            v-if="donutSeries.some(v => v > 0)"
            type="donut"
            :options="donutOptions"
            :series="donutSeries"
            height="260"
            @dataPointSelection="onChartClick"
          />
        </div>
      </div>

      <!-- Volume Bonus section -->
      <VolumeBonus />
    </div>

    <!-- ─── Drill-down Modal ─── -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="modalCategory" class="fm-overlay" @click.self="modalCategory = null">
          <div class="fm-card">
            <div class="fm-header">
              <h4>{{ filterLabel }}</h4>
              <div class="fm-header-right">
                <span class="fm-count ltr-number">{{ filteredClients.length }} לקוחות</span>
                <button class="fm-close" @click="modalCategory = null">&times;</button>
              </div>
            </div>

            <!-- Search -->
            <div class="fm-search">
              <input v-model="searchQuery" type="text" placeholder="חיפוש לפי שם או ת.ז..." class="fm-search-input" />
            </div>

            <!-- Table -->
            <div class="fm-table-scroll">
              <table v-if="searchedClients.length > 0">
                <thead>
                  <tr>
                    <th>ת.ז</th>
                    <th>שם</th>
                    <th v-if="modalCategory !== 'recruits'">חברה</th>
                    <th v-if="modalCategory === 'matched' || modalCategory === 'production_only'" class="num">פרמיה</th>
                    <th v-if="modalCategory === 'matched' || modalCategory === 'production_only'" class="num">צבירה</th>
                    <th v-if="modalCategory === 'matched' || modalCategory === 'volume_only'" class="num">הפקדה</th>
                    <th v-if="modalCategory === 'matched' || modalCategory === 'volume_only'" class="num">תפוקה</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="c in paginatedClients" :key="c.id_number">
                    <td class="ltr-number">{{ c.id_number }}</td>
                    <td>{{ c.name }}</td>
                    <td v-if="modalCategory !== 'recruits'">{{ c.company || '—' }}</td>
                    <td v-if="modalCategory === 'matched' || modalCategory === 'production_only'" class="num">
                      <span class="ltr-number">{{ c.premium > 0 ? c.premium.toLocaleString() : '—' }}</span>
                    </td>
                    <td v-if="modalCategory === 'matched' || modalCategory === 'production_only'" class="num">
                      <span class="ltr-number">{{ c.accumulation > 0 ? c.accumulation.toLocaleString() : '—' }}</span>
                    </td>
                    <td v-if="modalCategory === 'matched' || modalCategory === 'volume_only'" class="num">
                      <span class="ltr-number">{{ (c.volume_deposit || 0) > 0 ? c.volume_deposit.toLocaleString() : '—' }}</span>
                    </td>
                    <td v-if="modalCategory === 'matched' || modalCategory === 'volume_only'" class="num">
                      <span class="ltr-number">{{ (c.volume_production_after_cancel || 0) > 0 ? c.volume_production_after_cancel.toLocaleString() : '—' }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty-table">אין לקוחות בקטגוריה זו</div>
            </div>

            <!-- Pagination -->
            <div v-if="searchedClients.length > pageSize" class="fm-pagination">
              <button :disabled="page === 1" @click="page--">&rarr;</button>
              <span class="ltr-number">{{ page }} / {{ totalPages }}</span>
              <button :disabled="page >= totalPages" @click="page++">&larr;</button>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useVolumeStore } from '../../stores/volume.js'
import { useProductionStore } from '../../stores/production.js'
import VolumeBonus from './VolumeBonus.vue'

const volumeStore = useVolumeStore()
const productionStore = useProductionStore()

const dragging = ref(false)
const showPassword = ref(false)
const needPassword = ref(false)
const password = ref('')
const pendingFile = ref(null)
const modalCategory = ref(null)
const searchQuery = ref('')
const page = ref(1)
const pageSize = 50

const hasProduction = computed(() => !!productionStore.currentFile)
const result = computed(() => volumeStore.comparisonResult)

const filterLabel = computed(() => {
  const labels = {
    matched: 'לקוחות תואמים',
    production_only: 'בפרודוקציה בלבד',
    volume_only: 'בהיקפים בלבד',
    recruits: 'מגויסים חסרים בהיקפים',
  }
  return labels[modalCategory.value] || ''
})

const filteredClients = computed(() => {
  if (!result.value || !modalCategory.value) return []
  const map = {
    matched: result.value.matched,
    production_only: result.value.in_production_only,
    volume_only: result.value.in_volume_only,
    recruits: result.value.in_recruits_not_volume,
  }
  return map[modalCategory.value] || []
})

const searchedClients = computed(() => {
  if (!searchQuery.value) return filteredClients.value
  const q = searchQuery.value.trim().toLowerCase()
  return filteredClients.value.filter(c =>
    (c.id_number && c.id_number.includes(q)) ||
    (c.name && c.name.toLowerCase().includes(q))
  )
})

const totalPages = computed(() => Math.ceil(searchedClients.value.length / pageSize))
const paginatedClients = computed(() => {
  const start = (page.value - 1) * pageSize
  return searchedClients.value.slice(start, start + pageSize)
})

function openModal(category) {
  modalCategory.value = category
  searchQuery.value = ''
  page.value = 1
}

watch(modalCategory, () => { page.value = 1 })
watch(searchQuery, () => { page.value = 1 })

const donutSeries = computed(() => {
  if (!result.value) return [0, 0, 0, 0]
  const s = result.value.summary
  return [s.matched_count, s.in_production_only_count, s.in_volume_only_count, s.in_recruits_not_volume_count]
})

const donutCategories = ['matched', 'production_only', 'volume_only', 'recruits']

function onChartClick(e, chart, opts) {
  const idx = opts.dataPointIndex
  if (idx >= 0 && idx < donutCategories.length) {
    openModal(donutCategories[idx])
  }
}

const donutOptions = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Heebo, sans-serif', events: {} },
  labels: ['תואמים', 'פרודוקציה בלבד', 'היקפים בלבד', 'מגויסים חסרים'],
  colors: ['#10b981', '#f59e0b', '#3b82f6', '#8b5cf6'],
  legend: { position: 'bottom', fontSize: '12px' },
  dataLabels: { enabled: true, formatter: (val) => val.toFixed(0) + '%' },
  plotOptions: { pie: { donut: { size: '55%' }, expandOnClick: false } },
  states: { hover: { filter: { type: 'darken', value: 0.85 } } },
  tooltip: { style: { fontSize: '12px' } },
}))

function formatCurrency(val) {
  if (!val) return '0'
  return '₪' + Math.round(val).toLocaleString()
}

function onDrop(e) {
  dragging.value = false
  const files = e.dataTransfer?.files
  if (files?.[0]) handleFile(files[0])
}

function onFileSelect(e) {
  const files = e.target.files
  if (files?.[0]) handleFile(files[0])
  e.target.value = ''
}

function handleFile(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  if (ext !== 'xlsx' && ext !== 'xls') return
  pendingFile.value = file
  const pw = needPassword.value ? password.value : null
  volumeStore.uploadAndCompare(file, pw).catch((err) => {
    if (err?.response?.status === 400 && err.response.data?.detail?.includes('סיסמה')) {
      showPassword.value = true
    }
  })
}

function submitWithPassword() {
  if (pendingFile.value && password.value) {
    showPassword.value = false
    volumeStore.uploadAndCompare(pendingFile.value, password.value)
    password.value = ''
  }
}
</script>

<style scoped>
.volume-comparison {
  animation: slideUp 0.4s var(--transition);
}

.empty-state {
  text-align: center;
  padding: 48px 20px;
  color: var(--text-muted);
}

.empty-state svg { margin-bottom: 12px; opacity: 0.5; }
.empty-state p { font-size: 14px; }

/* Upload */
.upload-section {
  max-width: 560px;
  margin: 0 auto;
  position: relative;
}

/* Floating blur circles */
.float-circle {
  position: fixed;
  border-radius: 50%;
  pointer-events: none;
  z-index: 0;
}

.fc-1 {
  width: 220px; height: 220px;
  top: 10%; right: -60px;
  background: rgba(245, 124, 0, 0.045);
  border: 1px solid rgba(245, 124, 0, 0.06);
  animation: floatBob 8s ease-in-out infinite;
}

.fc-2 {
  width: 160px; height: 160px;
  bottom: 25%; left: -40px;
  background: rgba(245, 124, 0, 0.035);
  border: 1px solid rgba(245, 124, 0, 0.05);
  animation: floatBob 6.5s ease-in-out infinite reverse;
}

.fc-3 {
  width: 90px; height: 90px;
  top: 30%; left: 8%;
  background: rgba(245, 124, 0, 0.05);
  animation: floatBob 10s ease-in-out infinite 2s;
}

.fc-4 {
  width: 120px; height: 120px;
  top: 55%; right: 6%;
  background: rgba(245, 124, 0, 0.03);
  border: 1px solid rgba(245, 124, 0, 0.04);
  animation: floatBob 9s ease-in-out infinite 1s;
}

.fc-5 {
  width: 50px; height: 50px;
  top: 18%; right: 22%;
  background: rgba(255, 152, 0, 0.055);
  animation: floatBob 7s ease-in-out infinite 3s;
}

.fc-6 {
  width: 280px; height: 280px;
  bottom: 8%; right: -90px;
  background: rgba(245, 124, 0, 0.025);
  border: 1px solid rgba(245, 124, 0, 0.035);
  animation: floatBob 12s ease-in-out infinite 0.5s;
}

.fc-7 {
  width: 65px; height: 65px;
  bottom: 35%; left: 18%;
  background: rgba(255, 183, 77, 0.06);
  border: 1px solid rgba(255, 183, 77, 0.05);
  animation: floatBob 8.5s ease-in-out infinite reverse 1.5s;
}

@keyframes floatBob {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  33% { transform: translateY(-16px) rotate(2deg); }
  66% { transform: translateY(8px) rotate(-1deg); }
}

/* Waves fixed to bottom */
.wave-bg {
  position: fixed;
  left: 0; right: 0; bottom: 0;
  height: 200px;
  overflow: hidden;
  pointer-events: none;
  z-index: 0;
}

.shimmer {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 100%;
  z-index: 1;
  overflow: hidden;
  mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%);
  -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%);
}

.shimmer::after {
  content: '';
  position: absolute;
  top: 0; left: -80%;
  width: 50%; height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 200, 100, 0.1) 35%,
    rgba(255, 255, 255, 0.15) 50%,
    rgba(255, 200, 100, 0.1) 65%,
    transparent 100%
  );
  animation: shimmerSweep 7s ease-in-out infinite;
}

@keyframes shimmerSweep {
  0%   { left: -80%; }
  100% { left: 180%; }
}

.wave {
  position: absolute;
  bottom: 0; left: 0;
  width: 200%; height: 100%;
}

.wave-1 { animation: waveSlide 14s linear infinite; }
.wave-2 { animation: waveSlide 18s linear infinite reverse; }
.wave-3 { animation: waveSlide 22s linear infinite; }

@keyframes waveSlide {
  0%   { transform: translateX(0); }
  100% { transform: translateX(-50%); }
}

.upload-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  width: 100%;
  padding: 16px 24px;
  border: none;
  border-radius: var(--radius-md);
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  font-size: 15px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.3s var(--transition);
}

.upload-btn svg { color: #fff; flex-shrink: 0; }

.upload-btn:hover {
  background: linear-gradient(135deg, #E65100, #F57C00);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(245, 124, 0, 0.25);
}

.upload-btn:active { transform: translateY(0); }

/* Toggle */
.options-row { margin-top: 12px; }

.toggle-label {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-secondary);
}

.toggle { position: relative; }
.toggle input { position: absolute; opacity: 0; pointer-events: none; }

.toggle-track {
  width: 36px; height: 20px;
  background: var(--border-subtle);
  border-radius: 10px;
  transition: all 0.3s var(--transition);
  position: relative;
}

.toggle.on .toggle-track { background: var(--green-light); }

.toggle-thumb {
  width: 16px; height: 16px;
  background: var(--text-secondary);
  border-radius: 50%;
  position: absolute;
  top: 2px; right: 2px;
  transition: all 0.3s var(--transition);
}

.toggle.on .toggle-thumb {
  right: 18px;
  background: var(--accent-emerald);
  box-shadow: 0 0 8px var(--green-light);
}

.password-field { margin-top: 12px; }

.password-field input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: inherit;
  background: var(--bg-surface);
  color: var(--text);
  transition: all 0.25s var(--transition);
}

.password-field input:focus {
  border-color: var(--accent-emerald);
  box-shadow: 0 0 0 3px var(--green-light);
}

.slide-down-enter-active { animation: slideDown 0.3s var(--transition); }
.slide-down-leave-active { animation: slideDown 0.2s var(--transition) reverse; }
@keyframes slideDown {
  from { opacity: 0; transform: translateY(-8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Loading */
.loading-state {
  text-align: center;
  padding: 64px;
  color: var(--text-secondary);
  font-size: 14px;
}

.loader {
  width: 40px; height: 40px;
  position: relative;
  margin: 0 auto 16px;
}

.loader-ring {
  position: absolute; inset: 0;
  border: 2px solid transparent;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loader-ring.delay {
  inset: 6px;
  border-top-color: var(--accent-cyan);
  animation-duration: 1.5s;
  animation-direction: reverse;
}

/* Results */
.results-section { display: flex; flex-direction: column; gap: 20px; }

.results-header {
  display: flex; justify-content: space-between; align-items: center;
}

.results-header h4 { font-size: 17px; font-weight: 700; color: var(--text); }

.btn-back {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 14px; border-radius: 8px;
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  font-size: 13px; font-weight: 600; font-family: inherit;
  color: var(--text-secondary); cursor: pointer;
  transition: all 0.2s;
}

.btn-back:hover { background: var(--bg); color: var(--text); }

/* Summary strip */
.summary-strip {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}

.summary-badge {
  display: flex; flex-direction: column; align-items: center;
  padding: 14px 8px; border-radius: var(--radius-sm);
  cursor: pointer; transition: all 0.25s;
  border: 2px solid transparent;
}

.summary-badge:hover { transform: translateY(-2px); }
.summary-badge .ltr-number { font-size: 22px; font-weight: 800; direction: ltr; unicode-bidi: embed; display: inline-block; }
.summary-badge span:last-child { font-size: 11px; font-weight: 600; margin-top: 2px; }

.badge-green { background: var(--green-light); color: var(--accent-emerald); }
.badge-amber { background: var(--amber-light); color: var(--accent-amber); }
.badge-blue { background: rgba(59, 130, 246, 0.08); color: #3b82f6; }
.badge-purple { background: rgba(139, 92, 246, 0.08); color: #8b5cf6; }

/* Volume totals */
.volume-totals {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px;
}

.vt-card {
  display: flex; flex-direction: column;
  padding: 14px; border-radius: var(--radius-sm);
  background: var(--card-bg); border: 1px solid var(--glass-border);
}

.vt-label { font-size: 11px; color: var(--text-muted); font-weight: 600; margin-bottom: 4px; }
.vt-value { font-size: 16px; font-weight: 700; color: var(--text); }

/* Chart */
.chart-row { display: grid; grid-template-columns: 1fr; }

.chart-card {
  background: var(--card-bg); border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg); padding: 20px;
}

.chart-card h5 { font-size: 14px; font-weight: 700; color: var(--text); margin-bottom: 12px; }
.chart-card :deep(.apexcharts-pie-area) { cursor: pointer; }

/* Table */
.client-table-section {
  background: var(--card-bg); border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg); padding: 20px;
}

.table-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px;
}

.table-header h5 { font-size: 14px; font-weight: 700; color: var(--text); }
.table-count { font-size: 12px; color: var(--text-muted); }

.table-scroll { overflow-x: auto; }

table { width: 100%; border-collapse: collapse; font-size: 12px; }
thead { background: var(--bg); }

th {
  padding: 8px 6px; text-align: right; font-weight: 600;
  color: var(--text-muted); border-bottom: 1px solid var(--border-subtle);
  font-size: 11px;
}

th.num, td.num { text-align: left; }

td {
  padding: 8px 6px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
}

.ltr-number { direction: ltr; unicode-bidi: isolate; display: inline-block; }

.empty-table {
  text-align: center; padding: 24px;
  color: var(--text-muted); font-size: 13px;
}

.pagination {
  display: flex; justify-content: center; align-items: center;
  gap: 12px; margin-top: 12px;
}

.pagination button {
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  border-radius: 6px; padding: 4px 10px; cursor: pointer;
  font-family: inherit; color: var(--text-secondary);
}

.pagination button:disabled { opacity: 0.3; cursor: default; }

/* ── Drill-down Modal ── */
.fm-overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex; align-items: center; justify-content: center;
  z-index: 1010; backdrop-filter: blur(4px);
}

.fm-card {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  width: 90%; max-width: 800px; max-height: 85vh;
  display: flex; flex-direction: column;
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.2);
}

.fm-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 24px 14px;
  border-bottom: 1px solid var(--border-subtle);
}

.fm-header h4 { font-size: 16px; font-weight: 700; color: var(--text); }

.fm-header-right { display: flex; align-items: center; gap: 12px; }
.fm-count { font-size: 12px; color: var(--text-muted); }

.fm-close {
  width: 28px; height: 28px;
  border-radius: 50%; border: none;
  background: var(--bg-surface);
  color: var(--text-muted); font-size: 18px;
  cursor: pointer; display: flex;
  align-items: center; justify-content: center;
  transition: all 0.2s;
}

.fm-close:hover { background: var(--red-light); color: var(--red); }

.fm-search { padding: 12px 24px 0; }

.fm-search-input {
  width: 100%; padding: 9px 14px;
  border: 1px solid var(--glass-border);
  border-radius: 8px; font-size: 13px;
  font-family: 'Heebo', sans-serif;
  background: var(--bg-surface); color: var(--text);
}

.fm-search-input:focus { outline: none; border-color: var(--primary); }

.fm-table-scroll {
  flex: 1; overflow: auto;
  padding: 12px 24px;
}

.fm-pagination {
  display: flex; justify-content: center; align-items: center;
  gap: 12px; padding: 12px 24px 16px;
  border-top: 1px solid var(--border-subtle);
}

.fm-pagination button {
  background: var(--bg-surface); border: 1px solid var(--border-subtle);
  border-radius: 6px; padding: 4px 10px; cursor: pointer;
  font-family: inherit; color: var(--text-secondary);
}

.fm-pagination button:disabled { opacity: 0.3; cursor: default; }

/* Password modal */
.pw-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.45); display: flex;
  align-items: center; justify-content: center;
  z-index: 1010; backdrop-filter: blur(4px);
}

.pw-card {
  background: var(--card-bg); border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg); padding: 28px;
  max-width: 340px; width: 90%; text-align: center;
}

.pw-card h4 { font-size: 15px; font-weight: 700; margin-bottom: 14px; color: var(--text); }

.pw-input {
  width: 100%; padding: 10px; border: 1px solid var(--glass-border);
  border-radius: 8px; font-size: 14px; font-family: inherit;
  background: var(--bg-surface); color: var(--text);
  margin-bottom: 14px; text-align: center;
}

.pw-input:focus { outline: none; border-color: var(--primary); }

.pw-actions { display: flex; gap: 8px; justify-content: center; }

.btn-primary {
  background: var(--primary); color: #fff; border: none;
  border-radius: 8px; padding: 8px 20px; font-size: 13px;
  font-weight: 700; font-family: inherit; cursor: pointer;
}

.btn-ghost {
  background: transparent; color: var(--text-secondary);
  border: 1px solid var(--border-subtle);
  border-radius: 8px; padding: 8px 20px; font-size: 13px;
  font-weight: 600; font-family: inherit; cursor: pointer;
}

/* Modal transition */
.modal-enter-active { animation: modalIn 0.3s var(--transition); }
.modal-leave-active { animation: modalIn 0.2s var(--transition) reverse; }
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes spin { to { transform: rotate(360deg); } }
@keyframes slideUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .summary-strip { grid-template-columns: repeat(2, 1fr); }
  .volume-totals { grid-template-columns: repeat(2, 1fr); }
}
</style>
