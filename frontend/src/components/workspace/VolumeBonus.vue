<template>
  <div class="volume-bonus">
    <div class="bonus-header">
      <div>
        <h5>עמלות היקף</h5>
        <p class="formula-hint">נוסחה: <span class="ltr-number">(תפוקה לאחר ביטולים ÷ 1,000,000) × שיעור למיליון</span></p>
      </div>
      <button v-if="!volumeStore.bonusResult && !volumeStore.bonusLoading" class="btn-calc" @click="calculate">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="4" y="2" width="16" height="20" rx="2"/>
          <line x1="8" y1="6" x2="16" y2="6"/>
          <line x1="16" y1="14" x2="16" y2="18"/>
          <line x1="8" y1="10" x2="8" y2="10.01"/>
          <line x1="12" y1="10" x2="12" y2="10.01"/>
          <line x1="16" y1="10" x2="16" y2="10.01"/>
          <line x1="8" y1="14" x2="8" y2="14.01"/>
          <line x1="12" y1="14" x2="12" y2="14.01"/>
          <line x1="8" y1="18" x2="8" y2="18.01"/>
          <line x1="12" y1="18" x2="12" y2="18.01"/>
        </svg>
        חשב עמלות
      </button>
    </div>

    <!-- Loading -->
    <div v-if="volumeStore.bonusLoading" class="loading-state">
      <div class="spinner"></div>
      <span>מחשב עמלות...</span>
    </div>

    <!-- Results -->
    <template v-if="volumeStore.bonusResult">
      <!-- Table -->
      <div class="bonus-table-scroll">
        <table>
          <thead>
            <tr>
              <th>חברה</th>
              <th class="num">תפוקה לאחר ביטולים</th>
              <th class="num">שיעור למיליון</th>
              <th class="num">עמלה מחושבת</th>
              <th>תדירות תשלום</th>
              <th>סטטוס תשלום</th>
              <th class="num">לקוחות</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in volumeStore.bonusResult.companies" :key="c.company">
              <td>{{ c.company }}</td>
              <td class="num"><span class="ltr-number">{{ c.total_production_after_cancel > 0 ? '₪' + Math.round(c.total_production_after_cancel).toLocaleString() : '—' }}</span></td>
              <td class="num"><span class="ltr-number">{{ c.rate_per_million != null ? '₪' + c.rate_per_million.toLocaleString() : '—' }}</span></td>
              <td class="num"><span class="ltr-number bonus-val" :class="{ 'no-rate': c.calculated_bonus == null }">{{ c.calculated_bonus != null ? '₪' + Math.round(c.calculated_bonus).toLocaleString() : 'חסר שיעור' }}</span></td>
              <td>
                <span v-if="c.payment_frequency" class="freq-badge" :class="'freq-' + freqClass(c.payment_frequency)">{{ c.payment_frequency }}</span>
                <span v-else>—</span>
              </td>
              <td>
                <select
                  class="paid-select"
                  :class="getPaidStatus(c.company) ? 'paid-yes' : 'paid-no'"
                  :value="getPaidStatus(c.company) ? 'paid' : 'unpaid'"
                  @change="onPaidChange(c.company, $event)"
                >
                  <option value="unpaid">לא שולם</option>
                  <option value="paid">שולם</option>
                </select>
              </td>
              <td class="num"><span class="ltr-number">{{ c.client_count }}</span></td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="total-row">
              <td colspan="3"><strong>סה"כ עמלות</strong></td>
              <td class="num"><span class="ltr-number total-val">₪{{ Math.round(volumeStore.bonusResult.grand_total).toLocaleString() }}</span></td>
              <td colspan="3"></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </template>
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useVolumeStore } from '../../stores/volume.js'

const volumeStore = useVolumeStore()

onMounted(() => {
  volumeStore.fetchBonusPayments()
})

function calculate() {
  volumeStore.calculateBonus()
}

function freqClass(freq) {
  if (freq === 'חודשי') return 'monthly'
  if (freq === 'רבעוני') return 'quarterly'
  if (freq === 'שנתי') return 'yearly'
  return 'other'
}

function getPaidStatus(company) {
  const payment = volumeStore.bonusPayments.find(
    p => p.company_name === company && p.year === new Date().getFullYear()
  )
  return payment?.is_paid || false
}

function onPaidChange(company, event) {
  const isPaid = event.target.value === 'paid'
  volumeStore.upsertBonusPayment({
    company_name: company,
    year: new Date().getFullYear(),
    is_paid: isPaid,
    paid_date: isPaid ? new Date().toISOString().split('T')[0] : null,
  })
}
</script>

<style scoped>
.volume-bonus {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg);
  padding: 20px;
}

.bonus-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}

.bonus-header h5 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 2px;
}

.formula-hint {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.btn-calc {
  display: flex;
  align-items: center;
  gap: 6px;
  background: linear-gradient(135deg, var(--primary-deep), var(--primary));
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.25s;
}

.btn-calc:hover {
  box-shadow: 0 4px 16px var(--primary-light);
  transform: translateY(-1px);
}

/* Loading */
.loading-state {
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
  padding: 20px;
  color: var(--text-secondary);
  font-size: 13px;
}

.spinner {
  width: 20px; height: 20px;
  border: 2px solid var(--border-subtle);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

/* Table */
.bonus-table-scroll { overflow-x: auto; }

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

thead { background: var(--bg); }

th {
  padding: 8px 6px;
  text-align: right;
  font-weight: 600;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border-subtle);
  font-size: 11px;
}

th.num, td.num { text-align: left; }

td {
  padding: 8px 6px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
  display: inline-block;
}

.bonus-val {
  font-weight: 700;
  color: var(--accent-emerald);
}

.bonus-val.no-rate {
  color: var(--text-muted);
  font-weight: 400;
  font-size: 11px;
}

/* Frequency badges */
.freq-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
}

.freq-monthly { background: rgba(59, 130, 246, 0.1); color: #3b82f6; }
.freq-quarterly { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; }
.freq-yearly { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }
.freq-other { background: var(--bg-surface); color: var(--text-muted); }

/* Paid status select */
.paid-select {
  padding: 3px 8px;
  border-radius: 8px;
  border: 1px solid var(--border-subtle);
  font-size: 11px;
  font-weight: 600;
  font-family: 'Heebo', sans-serif;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg-surface);
  color: var(--text-secondary);
  appearance: none;
  -webkit-appearance: none;
  text-align: center;
  min-width: 80px;
}

.paid-select:focus { outline: none; border-color: var(--primary); }

.paid-select.paid-yes {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border-color: rgba(16, 185, 129, 0.3);
}

.paid-select.paid-no {
  background: rgba(239, 68, 68, 0.06);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.2);
}

/* Total row */
.total-row td {
  border-top: 2px solid var(--primary);
  border-bottom: none;
  padding-top: 10px;
}

.total-val {
  font-size: 16px;
  font-weight: 800;
  color: var(--primary);
}

@keyframes spin { to { transform: rotate(360deg); } }
</style>
