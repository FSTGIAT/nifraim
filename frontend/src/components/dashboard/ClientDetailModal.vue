<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h2>פרטי לקוח — {{ idNumber }}</h2>
        <button class="close-btn" @click="$emit('close')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"/>
            <line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
      <div class="modal-body">
        <div v-if="loading" class="loading">
          <div class="spinner"></div>
        </div>
        <div v-else-if="records.length === 0" class="empty">לא נמצאו רשומות</div>
        <div v-else>
          <div class="client-info" v-if="records[0]">
            <h3>{{ records[0].first_name }} {{ records[0].last_name }}</h3>
          </div>

          <!-- Record cards — one per product -->
          <div class="record-cards">
            <div class="record-card" v-for="r in records" :key="r.id">
              <div class="record-card-header">
                <span class="product-name">{{ r.product || 'לא צוין' }}</span>
                <StatusBadge :status="r.reconciliation_status || 'no_data'" />
              </div>

              <div class="detail-grid">
                <div class="detail-item" v-if="r.receiving_company">
                  <span class="detail-label">חברה</span>
                  <span class="detail-value">{{ r.receiving_company }}</span>
                </div>
                <div class="detail-item" v-if="r.sign_date">
                  <span class="detail-label">תאריך חתימה</span>
                  <span class="detail-value ltr-number">{{ r.sign_date }}</span>
                </div>

                <!-- Agent tracking: transfer amounts -->
                <div class="detail-item" v-if="r.expected_amount != null">
                  <span class="detail-label">סכום העברה צפוי</span>
                  <span class="detail-value ltr-number">{{ formatAmount(r.expected_amount) }}</span>
                </div>
                <div class="detail-item" v-if="r.actual_amount != null">
                  <span class="detail-label">סכום העברה בפועל</span>
                  <span class="detail-value ltr-number">{{ formatAmount(r.actual_amount) }}</span>
                </div>
                <div class="detail-item" v-if="r.amount_difference != null">
                  <span class="detail-label">הפרש העברה</span>
                  <span class="detail-value ltr-number" :class="diffClass(r.amount_difference)">
                    {{ formatAmount(r.amount_difference) }}
                  </span>
                </div>

                <!-- Company report: balance & commission -->
                <div class="detail-item" v-if="r.balance != null">
                  <span class="detail-label">יתרה</span>
                  <span class="detail-value ltr-number">{{ formatAmount(r.balance) }}</span>
                </div>
                <div class="detail-item" v-if="r.commission_expected != null">
                  <span class="detail-label">עמלה צפויה</span>
                  <span class="detail-value ltr-number">{{ formatAmount(r.commission_expected) }}</span>
                </div>
                <div class="detail-item" v-if="r.commission_paid != null">
                  <span class="detail-label">עמלה ששולמה</span>
                  <span class="detail-value ltr-number">{{ formatAmount(r.commission_paid) }}</span>
                </div>
                <div class="detail-item" v-if="r.management_fee != null">
                  <span class="detail-label">דמי ניהול</span>
                  <span class="detail-value ltr-number">{{ formatPercent(r.management_fee) }}</span>
                </div>

                <!-- Extra info -->
                <div class="detail-item" v-if="r.fund_policy_number">
                  <span class="detail-label">מספר קופה/פוליסה</span>
                  <span class="detail-value ltr-number">{{ r.fund_policy_number }}</span>
                </div>
                <div class="detail-item" v-if="r.agent_number">
                  <span class="detail-label">מספר סוכן</span>
                  <span class="detail-value ltr-number">{{ r.agent_number }}</span>
                </div>
              </div>

              <div class="general-notes" v-if="r.general_notes">
                <span class="detail-label">הערות:</span> {{ r.general_notes }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRecordsStore } from '../../stores/records.js'
import StatusBadge from './StatusBadge.vue'

const props = defineProps({
  idNumber: { type: String, required: true },
})
defineEmits(['close'])

const recordsStore = useRecordsStore()
const records = ref([])
const loading = ref(true)

onMounted(async () => {
  try {
    records.value = await recordsStore.fetchClientRecords(props.idNumber)
  } finally {
    loading.value = false
  }
})

function formatAmount(val) {
  if (val == null) return '—'
  return '₪ ' + Number(val).toLocaleString('he-IL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function formatPercent(val) {
  if (val == null) return '—'
  return Number(val * 100).toFixed(4) + '%'
}

function diffClass(val) {
  if (val == null) return ''
  if (val > 0) return 'positive'
  if (val < 0) return 'negative'
  return ''
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  animation: fadeIn 0.2s;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal {
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-xl, 20px);
  width: 90%;
  max-width: 900px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4), 0 0 0 1px var(--border-subtle);
  animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.97);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--glass-border);
}

.modal-header h2 {
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}

.close-btn {
  background: none;
  border: none;
  color: var(--text-muted);
  padding: 6px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
}

.close-btn:hover {
  background: var(--red-light);
  color: var(--red);
}

.modal-body {
  padding: 24px;
  overflow-y: auto;
}

.client-info h3 {
  font-size: 20px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 16px;
}

.record-cards {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.record-card {
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md, 12px);
  padding: 16px 20px;
  background: var(--bg);
}

.record-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--border-subtle);
}

.product-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text);
}

.detail-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px 24px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  padding: 4px 0;
}

.detail-label {
  font-size: 13px;
  color: var(--text-muted);
}

.detail-value {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
}

.general-notes {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border-subtle);
  font-size: 13px;
  color: var(--text-muted);
}

.positive { color: var(--green); font-weight: 600; }
.negative { color: var(--red); font-weight: 600; }

.loading {
  display: flex;
  justify-content: center;
  padding: 32px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--border-subtle);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty {
  text-align: center;
  padding: 32px;
  color: var(--text-muted);
}
</style>
