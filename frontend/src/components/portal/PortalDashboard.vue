<template>
  <div class="portal-dashboard">
    <div class="dashboard-header print-header-hidden">
      <div class="customer-info">
        <h2>שלום, {{ data.customer_name }}</h2>
        <p class="id-label">
          ת.ז: <span class="ltr-number">{{ data.id_number }}</span>
          <span v-if="data.period" class="period-badge">{{ data.period }}</span>
        </p>
      </div>
      <div class="header-actions">
        <button class="print-btn" @click="printReport" title="הדפסת דוח">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 6 2 18 2 18 9"/>
            <path d="M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2"/>
            <rect x="6" y="14" width="12" height="8"/>
          </svg>
          הדפסת דוח
        </button>
        <button class="logout-btn" @click="$emit('logout')">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
            <polyline points="16 17 21 12 16 7"/>
            <line x1="21" y1="12" x2="9" y2="12"/>
          </svg>
          יציאה
        </button>
      </div>
    </div>

    <!-- Print-only header -->
    <div class="print-only-header">
      <h1>דוח תיק ביטוחי — {{ data.customer_name }}</h1>
      <p>ת.ז: {{ data.id_number }} | תקופה: {{ data.period || '—' }} | תאריך הפקה: {{ printDate }}</p>
    </div>

    <!-- Changes Banner -->
    <PortalChangesBanner
      v-if="data.recent_changes"
      :changes="data.recent_changes"
    />

    <!-- KPI Strip -->
    <PortalKPIStrip :kpi="data.kpi" />

    <!-- Trend Chart -->
    <PortalTrendChart :snapshots="portalStore.history" />

    <!-- Company Chart + Products -->
    <div class="section-grid">
      <PortalCompanyChart :breakdown="data.company_breakdown" />
      <PortalProductTable :products="data.products" />
    </div>

    <!-- Print footer -->
    <div class="print-only-footer">
      הופק על ידי Nifraim | {{ printDate }}
    </div>

    <!-- AI Chat -->
    <PortalAIChat v-if="token" :token="token" />
  </div>
</template>

<script setup>
import { onMounted, computed } from 'vue'
import { usePortalStore } from '../../stores/portal.js'
import PortalKPIStrip from './PortalKPIStrip.vue'
import PortalCompanyChart from './PortalCompanyChart.vue'
import PortalProductTable from './PortalProductTable.vue'
import PortalTrendChart from './PortalTrendChart.vue'
import PortalChangesBanner from './PortalChangesBanner.vue'
import PortalAIChat from './PortalAIChat.vue'

const props = defineProps({
  data: Object,
  token: String,
})

defineEmits(['logout'])

const portalStore = usePortalStore()

const printDate = computed(() => {
  return new Date().toLocaleDateString('he-IL', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
})

function printReport() {
  window.print()
}

onMounted(() => {
  if (props.token) {
    portalStore.fetchHistory(props.token)
  }
})
</script>

<style scoped>
.portal-dashboard {
  animation: fadeInUp 0.5s var(--transition);
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}

.dashboard-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.customer-info h2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 4px;
}

.id-label {
  font-size: 13px;
  color: var(--text-muted);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

.period-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  background: var(--primary-light);
  color: var(--primary);
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.print-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  background: var(--card-bg);
  transition: all 0.2s var(--transition);
  cursor: pointer;
}

.print-btn:hover {
  color: var(--primary);
  border-color: var(--primary-light);
  background: var(--primary-light);
}

.logout-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  background: var(--card-bg);
  transition: all 0.2s var(--transition);
  cursor: pointer;
}

.logout-btn:hover {
  color: var(--red);
  border-color: var(--red-light);
  background: var(--red-light);
}

.section-grid {
  display: grid;
  grid-template-columns: 1fr 2fr;
  gap: 20px;
  margin-top: 20px;
}

/* Print-only elements (hidden on screen) */
.print-only-header,
.print-only-footer {
  display: none;
}

@media (max-width: 768px) {
  .section-grid {
    grid-template-columns: 1fr;
  }
}

/* ───── Print Styles ───── */
@media print {
  .portal-dashboard {
    animation: none;
    padding: 0;
  }

  .print-header-hidden,
  .print-btn,
  .logout-btn,
  .header-actions {
    display: none !important;
  }

  .print-only-header {
    display: block;
    text-align: center;
    margin-bottom: 24px;
    border-bottom: 2px solid #333;
    padding-bottom: 12px;
  }

  .print-only-header h1 {
    font-size: 20px;
    font-weight: 700;
    margin: 0 0 6px;
    color: #000;
  }

  .print-only-header p {
    font-size: 12px;
    color: #555;
    margin: 0;
  }

  .print-only-footer {
    display: block;
    text-align: center;
    margin-top: 32px;
    padding-top: 12px;
    border-top: 1px solid #999;
    font-size: 11px;
    color: #777;
  }

  .section-grid {
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  /* Remove shadows and borders for clean print */
  :deep(.trend-chart-card),
  :deep(.kpi-strip),
  :deep(.portal-company-chart),
  :deep(.portal-product-table) {
    box-shadow: none !important;
    border: 1px solid #ddd !important;
    break-inside: avoid;
  }

  /* Hide changes banner in print */
  :deep(.changes-banner) {
    display: none !important;
  }
}
</style>
