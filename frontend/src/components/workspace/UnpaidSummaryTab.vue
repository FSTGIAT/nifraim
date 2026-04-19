<template>
  <div class="unpaid-tab">
    <!-- Loading -->
    <div v-if="debtsStore.loading && !debtsStore.debts.length" class="loading-state">
      <div class="loader"><div class="loader-ring"></div><div class="loader-ring delay"></div></div>
      <span>טוען סיכום חובות...</span>
    </div>

    <!-- Empty state -->
    <div v-else-if="!debtsStore.summary || debtsStore.summary.total_count === 0" class="empty-state">
      <div class="float-circle fc-1"></div>
      <div class="float-circle fc-2"></div>
      <div class="float-circle fc-3"></div>
      <div class="float-circle fc-4"></div>
      <div class="float-circle fc-5"></div>
      <div class="float-circle fc-6"></div>
      <div class="float-circle fc-7"></div>
      <div class="wave-bg">
        <div class="shimmer"></div>
        <svg class="wave wave-1" viewBox="0 0 1440 200" preserveAspectRatio="none">
          <defs><linearGradient id="utg1" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#F57C00" stop-opacity="0.10"/><stop offset="30%" stop-color="#FF9800" stop-opacity="0.06"/><stop offset="60%" stop-color="#FFB74D" stop-opacity="0.10"/><stop offset="100%" stop-color="#F57C00" stop-opacity="0.05"/></linearGradient></defs>
          <path fill="url(#utg1)" d="M0,100L60,90C120,80,240,60,360,66.7C480,73,600,107,720,113.3C840,120,960,100,1080,86.7C1200,73,1320,67,1380,63.3L1440,60L1440,200L0,200Z"/>
        </svg>
        <svg class="wave wave-2" viewBox="0 0 1440 200" preserveAspectRatio="none">
          <defs><linearGradient id="utg2" x1="100%" y1="0%" x2="0%" y2="0%"><stop offset="0%" stop-color="#FFB74D" stop-opacity="0.08"/><stop offset="40%" stop-color="#F57C00" stop-opacity="0.05"/><stop offset="70%" stop-color="#FF9800" stop-opacity="0.08"/><stop offset="100%" stop-color="#FFB74D" stop-opacity="0.04"/></linearGradient></defs>
          <path fill="url(#utg2)" d="M0,120L60,126.7C120,133,240,147,360,140C480,133,600,107,720,100C840,93,960,107,1080,120C1200,133,1320,147,1380,153.3L1440,160L1440,200L0,200Z"/>
        </svg>
        <svg class="wave wave-3" viewBox="0 0 1440 200" preserveAspectRatio="none">
          <defs><linearGradient id="utg3" x1="0%" y1="0%" x2="100%" y2="0%"><stop offset="0%" stop-color="#FF9800" stop-opacity="0.06"/><stop offset="50%" stop-color="#FFB74D" stop-opacity="0.04"/><stop offset="100%" stop-color="#F57C00" stop-opacity="0.07"/></linearGradient></defs>
          <path fill="url(#utg3)" d="M0,150L60,143.3C120,137,240,123,360,126.7C480,130,600,150,720,153.3C840,157,960,143,1080,133.3C1200,123,1320,117,1380,113.3L1440,110L1440,200L0,200Z"/>
        </svg>
      </div>
      <div class="empty-content">
        <div class="empty-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
          </svg>
        </div>
        <h3>אין חובות פתוחים</h3>
        <p>בצע השוואה בלשונית "השוואת נפרעים" — חובות יתעדכנו אוטומטית</p>
      </div>
    </div>

    <!-- Has data -->
    <template v-else>
      <!-- KPI Strip -->
      <div class="kpi-row">
        <div class="kpi-card kpi-red">
          <div class="kpi-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value ltr-number">{{ formatCurrency(debtsStore.summary.open_amount) }}</span>
            <span class="kpi-label">סה״כ חוב פתוח</span>
          </div>
        </div>
        <div class="kpi-card kpi-amber">
          <div class="kpi-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value ltr-number">{{ debtsStore.summary.open_count.toLocaleString() }}</span>
            <span class="kpi-label">פריטים פתוחים</span>
          </div>
        </div>
        <div class="kpi-card kpi-green">
          <div class="kpi-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value ltr-number">{{ debtsStore.summary.paid_count.toLocaleString() }}</span>
            <span class="kpi-label">שולמו</span>
          </div>
        </div>
        <div class="kpi-card kpi-blue">
          <div class="kpi-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/>
              <path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/>
            </svg>
          </div>
          <div class="kpi-data">
            <span class="kpi-value ltr-number">{{ debtsStore.summary.unique_companies }}</span>
            <span class="kpi-label">חברות</span>
          </div>
        </div>
      </div>

      <!-- Toolbar -->
      <div class="toolbar">
        <div class="toolbar-right">
          <div class="status-toggle">
            <button :class="{ active: debtsStore.statusFilter === 'open' }" @click="setFilter('open')">פתוחים</button>
            <button :class="{ active: debtsStore.statusFilter === 'paid' }" @click="setFilter('paid')">שולמו</button>
            <button :class="{ active: debtsStore.statusFilter === '' }" @click="setFilter('')">הכל</button>
          </div>
          <div class="search-box">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input v-model="debtsStore.searchQuery" type="text" placeholder="חיפוש לפי שם, ת.ז או חברה..." />
          </div>
        </div>
        <div class="toolbar-left">
          <button class="btn-export" @click="debtsStore.exportExcel()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>
            </svg>
            ייצוא Excel
          </button>
        </div>
      </div>

      <!-- Company groups -->
      <div class="company-groups">
        <div
          v-for="group in debtsStore.groupedByCompany"
          :key="group.company"
          class="company-group"
        >
          <div class="group-header" @click="toggleGroup(group.company)">
            <div class="group-info">
              <span class="company-avatar" :style="{ background: getColor(group.company) }">{{ group.company.charAt(0) }}</span>
              <span class="group-name">{{ group.company }}</span>
              <span class="group-category-pill" :class="group.category">{{ group.category === 'insurance' ? 'ביטוח' : 'גמל' }}</span>
            </div>
            <div class="group-meta">
              <span class="group-count ltr-number">{{ group.count }} פריטים</span>
              <span class="group-total ltr-number">{{ formatCurrency(group.total) }}</span>
              <button class="btn-email-company" @click.stop="emailCompany(group.company)" title="שלח אימייל לחברה">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
                </svg>
              </button>
              <svg class="group-chevron" :class="{ open: openGroups.has(group.company) }" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"/></svg>
            </div>
          </div>

          <Transition name="slide-down">
            <div v-if="openGroups.has(group.company)" class="group-body">
              <table class="debt-table">
                <thead>
                  <tr>
                    <th>שם לקוח</th>
                    <th>ת.ז</th>
                    <th>מוצר</th>
                    <th class="th-amount">סכום צפוי</th>
                    <th class="th-status">סטטוס</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="d in group.debts" :key="d.id">
                    <td>{{ d.customer_name }}</td>
                    <td><span class="ltr-number">{{ d.customer_id_number }}</span></td>
                    <td>{{ d.product || '—' }}</td>
                    <td class="td-amount"><span class="ltr-number amount-val">{{ formatCurrency(d.expected_amount) }}</span></td>
                    <td class="td-status">
                      <select
                        :value="d.status"
                        @change="debtsStore.updateStatus(d.id, $event.target.value)"
                        class="status-select"
                        :class="d.status"
                      >
                        <option value="open">פתוח</option>
                        <option value="paid">שולם</option>
                        <option value="disputed">במחלוקת</option>
                        <option value="cancelled">בוטל</option>
                      </select>
                    </td>
                    <td class="td-email-badge">
                      <span v-if="d.email_count > 0" class="email-badge" :title="'נשלח ' + d.email_count + ' פעמים'">
                        <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
                        <span class="ltr-number">{{ d.email_count }}</span>
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Transition>
        </div>
      </div>

      <!-- Email toast -->
      <Transition name="fade">
        <div v-if="emailToast" class="email-toast" :class="emailToast.type">
          {{ emailToast.message }}
        </div>
      </Transition>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useDebtsStore } from '../../stores/debts.js'

const debtsStore = useDebtsStore()
const openGroups = ref(new Set())
const emailToast = ref(null)

const COMPANY_COLORS = {
  'אקסלנס': '#F57C00',
  'הפניקס': '#e53935',
  'מנורה': '#1e88e5',
  'הכשרה': '#43a047',
  'מור': '#8e24aa',
  'אלטשולר': '#00897b',
  'מיטב': '#5c6bc0',
  'מגדל': '#d81b60',
  'ילין': '#fb8c00',
  'כלל': '#3949ab',
  'הראל': '#00acc1',
}

function getColor(name) {
  for (const [key, color] of Object.entries(COMPANY_COLORS)) {
    if (name.includes(key)) return color
  }
  return '#94a3b8'
}

function formatCurrency(val) {
  if (!val) return '₪0'
  return `₪${Math.round(val).toLocaleString()}`
}

function toggleGroup(company) {
  if (openGroups.value.has(company)) {
    openGroups.value.delete(company)
  } else {
    openGroups.value.add(company)
  }
  openGroups.value = new Set(openGroups.value) // trigger reactivity
}

function setFilter(status) {
  debtsStore.statusFilter = status
  debtsStore.fetchDebts()
}

async function emailCompany(companyName) {
  try {
    const result = await debtsStore.sendEmail(companyName)
    emailToast.value = { type: 'success', message: `אימייל נשלח בהצלחה ל-${result.sent_to} (${result.debts_count} פריטים)` }
  } catch (e) {
    emailToast.value = { type: 'error', message: typeof e === 'string' ? e : 'שגיאה בשליחה' }
  }
  setTimeout(() => { emailToast.value = null }, 4000)
}

onMounted(() => {
  debtsStore.fetchDebts()
  debtsStore.fetchSummary()
})
</script>

<style scoped>
.unpaid-tab {
  animation: slideUp 0.4s var(--transition);
}

.loading-state {
  text-align: center;
  padding: 64px;
  color: var(--text-secondary);
  font-size: 14px;
}

.loader { width: 40px; height: 40px; position: relative; margin: 0 auto 16px; }
.loader-ring { position: absolute; inset: 0; border: 2px solid transparent; border-top-color: var(--primary); border-radius: 50%; animation: spin 1s linear infinite; }
.loader-ring.delay { inset: 6px; border-top-color: var(--accent-cyan); animation-duration: 1.5s; animation-direction: reverse; }

/* Empty state */
.empty-state {
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

.empty-state h3 { font-size: 17px; font-weight: 700; color: var(--text); margin-bottom: 8px; }
.empty-state p { font-size: 14px; color: var(--text-secondary); }

/* Circles + waves */
.float-circle { position: fixed; border-radius: 50%; pointer-events: none; z-index: 0; }
.fc-1 { width: 220px; height: 220px; top: 10%; right: -60px; background: rgba(245,124,0,0.045); border: 1px solid rgba(245,124,0,0.06); animation: floatBob 8s ease-in-out infinite; }
.fc-2 { width: 160px; height: 160px; bottom: 25%; left: -40px; background: rgba(245,124,0,0.035); border: 1px solid rgba(245,124,0,0.05); animation: floatBob 6.5s ease-in-out infinite reverse; }
.fc-3 { width: 90px; height: 90px; top: 30%; left: 8%; background: rgba(245,124,0,0.05); animation: floatBob 10s ease-in-out infinite 2s; }
.fc-4 { width: 120px; height: 120px; top: 55%; right: 6%; background: rgba(245,124,0,0.03); border: 1px solid rgba(245,124,0,0.04); animation: floatBob 9s ease-in-out infinite 1s; }
.fc-5 { width: 50px; height: 50px; top: 18%; right: 22%; background: rgba(255,152,0,0.055); animation: floatBob 7s ease-in-out infinite 3s; }
.fc-6 { width: 280px; height: 280px; bottom: 8%; right: -90px; background: rgba(245,124,0,0.025); border: 1px solid rgba(245,124,0,0.035); animation: floatBob 12s ease-in-out infinite 0.5s; }
.fc-7 { width: 65px; height: 65px; bottom: 35%; left: 18%; background: rgba(255,183,77,0.06); border: 1px solid rgba(255,183,77,0.05); animation: floatBob 8.5s ease-in-out infinite reverse 1.5s; }

@keyframes floatBob { 0%, 100% { transform: translateY(0) rotate(0deg); } 33% { transform: translateY(-16px) rotate(2deg); } 66% { transform: translateY(8px) rotate(-1deg); } }

.wave-bg { position: fixed; left: 0; right: 0; bottom: 0; height: 200px; overflow: hidden; pointer-events: none; z-index: 0; }
.shimmer { position: absolute; bottom: 0; left: 0; right: 0; height: 100%; z-index: 1; overflow: hidden; mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%); -webkit-mask-image: linear-gradient(to top, rgba(0,0,0,1) 30%, rgba(0,0,0,0.3) 60%, transparent 100%); }
.shimmer::after { content: ''; position: absolute; top: 0; left: -80%; width: 50%; height: 100%; background: linear-gradient(90deg, transparent 0%, rgba(255,200,100,0.1) 35%, rgba(255,255,255,0.15) 50%, rgba(255,200,100,0.1) 65%, transparent 100%); animation: shimmerSweep 7s ease-in-out infinite; }
@keyframes shimmerSweep { 0% { left: -80%; } 100% { left: 180%; } }
.wave { position: absolute; bottom: 0; left: 0; width: 200%; height: 100%; }
.wave-1 { animation: waveSlide 14s linear infinite; }
.wave-2 { animation: waveSlide 18s linear infinite reverse; }
.wave-3 { animation: waveSlide 22s linear infinite; }
@keyframes waveSlide { 0% { transform: translateX(0); } 100% { transform: translateX(-50%); } }

/* KPI Strip — matches ComparisonDashboard */
.kpi-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}

.kpi-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: box-shadow 0.2s ease;
}

.kpi-card:hover { box-shadow: var(--shadow-md); }

.kpi-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.kpi-blue .kpi-icon { background: rgba(245, 124, 0, 0.1); color: #F57C00; }
.kpi-amber .kpi-icon { background: rgba(232, 114, 10, 0.1); color: #E8720A; }
.kpi-amber .kpi-value { color: #E8720A; }
.kpi-red .kpi-icon { background: rgba(194, 57, 52, 0.1); color: #C23934; }
.kpi-red .kpi-value { color: #C23934; }
.kpi-green .kpi-icon { background: rgba(46, 132, 74, 0.1); color: #2E844A; }
.kpi-green .kpi-value { color: #2E844A; }

.kpi-data { min-width: 0; }
.kpi-value {
  font-size: 18px;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -0.5px;
  line-height: 1.2;
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  margin-top: 2px;
}

/* Toolbar — chart-card style */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  padding: 10px 16px;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  flex-wrap: wrap;
}

.toolbar-right { display: flex; align-items: center; gap: 10px; }
.toolbar-left { display: flex; align-items: center; gap: 8px; }

.status-toggle {
  display: flex;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 2px;
}

.status-toggle button {
  padding: 6px 16px;
  border: none;
  border-radius: 7px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-secondary);
  background: transparent;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;
}

.status-toggle button.active {
  background: var(--bg-surface);
  color: var(--primary-deep);
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  min-width: 220px;
  transition: border-color 0.2s;
}

.search-box:focus-within { border-color: var(--primary); }
.search-box svg { color: var(--text-muted); flex-shrink: 0; }

.search-box input {
  border: none;
  background: transparent;
  font-size: 12px;
  font-family: inherit;
  color: var(--text);
  width: 100%;
  outline: none;
}

.btn-export {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--primary-deep), var(--primary));
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.25s;
}

.btn-export:hover {
  box-shadow: 0 4px 16px var(--primary-light);
  transform: translateY(-1px);
}

/* Company groups */
.company-groups { display: flex; flex-direction: column; gap: 10px; }

.company-group {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  overflow: hidden;
  transition: box-shadow 0.2s ease;
}

.company-group:hover { box-shadow: var(--shadow-md); }

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  cursor: pointer;
  transition: background 0.2s;
}

.group-header:hover { background: var(--bg-surface); }

.group-info { display: flex; align-items: center; gap: 12px; }

.company-avatar {
  width: 36px; height: 36px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.group-name { font-size: 15px; font-weight: 700; color: var(--text); }

.group-category-pill {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 10px;
  border-radius: 6px;
}

.group-category-pill.gemel_hishtalmut { background: rgba(59,130,246,0.08); color: #3b82f6; }
.group-category-pill.insurance { background: rgba(168,85,247,0.08); color: #a855f7; }

.group-meta { display: flex; align-items: center; gap: 14px; }
.group-count { font-size: 12px; color: var(--text-muted); font-weight: 500; }
.group-total { font-size: 16px; font-weight: 800; color: #C23934; letter-spacing: -0.3px; }

.btn-email-company {
  width: 32px; height: 32px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.25s var(--transition);
}

.btn-email-company:hover {
  background: var(--primary-light);
  border-color: var(--primary);
  color: var(--primary);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.15);
}

.group-chevron {
  color: var(--text-muted);
  transition: transform 0.25s ease;
}

.group-chevron.open { transform: rotate(180deg); }

/* Debt table inside group */
.group-body {
  padding: 0 20px 16px;
  border-top: 1px solid var(--border-subtle);
}

.debt-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.debt-table thead { background: var(--bg); }

.debt-table th {
  padding: 10px 10px;
  text-align: right;
  font-weight: 600;
  color: var(--text-muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  border-bottom: 1px solid var(--border-subtle);
}

.debt-table td {
  padding: 10px 10px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
  font-size: 12px;
}

.debt-table tbody tr:hover { background: var(--bg-surface); }
.debt-table tbody tr:last-child td { border-bottom: none; }

.th-amount, .td-amount { text-align: left; }
.th-status { width: 110px; }

.amount-val { font-weight: 700; color: #C23934; }

.status-select {
  padding: 5px 10px;
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  font-size: 11px;
  font-family: inherit;
  font-weight: 600;
  background: var(--bg-surface);
  color: var(--text-secondary);
  cursor: pointer;
  width: 95px;
  transition: border-color 0.2s;
}

.status-select:focus { outline: none; border-color: var(--primary); }
.status-select.open { color: #C23934; border-color: rgba(194,57,52,0.2); background: rgba(194,57,52,0.04); }
.status-select.paid { color: #2E844A; border-color: rgba(46,132,74,0.2); background: rgba(46,132,74,0.04); }
.status-select.disputed { color: #E8720A; border-color: rgba(232,114,10,0.2); background: rgba(232,114,10,0.04); }

.email-badge {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 10px;
  color: var(--accent-emerald);
  background: var(--green-light);
  padding: 2px 6px;
  border-radius: 4px;
}

/* Email toast */
.email-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 24px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
  z-index: 9000;
  box-shadow: 0 8px 32px rgba(0,0,0,0.15);
}

.email-toast.success { background: var(--accent-emerald); color: #fff; }
.email-toast.error { background: #ef4444; color: #fff; }

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

/* Transitions */
.slide-down-enter-active { animation: slideDown 0.3s var(--transition); }
.slide-down-leave-active { animation: slideDown 0.2s var(--transition) reverse; }
@keyframes slideDown { from { opacity: 0; transform: translateY(-8px); } to { opacity: 1; transform: translateY(0); } }

.fade-enter-active { animation: fadeIn 0.3s; }
.fade-leave-active { animation: fadeIn 0.2s reverse; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

@media (max-width: 768px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .toolbar { flex-direction: column; align-items: stretch; }
  .toolbar-right, .toolbar-left { flex-wrap: wrap; }
  .group-header { flex-direction: column; align-items: flex-start; gap: 10px; }
  .group-meta { width: 100%; justify-content: space-between; }
}
</style>
