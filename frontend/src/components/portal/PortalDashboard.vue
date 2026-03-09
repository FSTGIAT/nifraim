<template>
  <div class="portal-dashboard">
    <div class="dashboard-header">
      <div class="customer-info">
        <h2>שלום, {{ data.customer_name }}</h2>
        <p class="id-label">
          ת.ז: <span class="ltr-number">{{ data.id_number }}</span>
          <span v-if="data.period" class="period-badge">{{ data.period }}</span>
        </p>
      </div>
      <button class="logout-btn" @click="$emit('logout')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/>
          <polyline points="16 17 21 12 16 7"/>
          <line x1="21" y1="12" x2="9" y2="12"/>
        </svg>
        יציאה
      </button>
    </div>

    <!-- KPI Strip -->
    <PortalKPIStrip :kpi="data.kpi" />

    <!-- Company Chart -->
    <div class="section-grid">
      <PortalCompanyChart :breakdown="data.company_breakdown" />
      <PortalProductTable :products="data.products" />
    </div>
  </div>
</template>

<script setup>
import PortalKPIStrip from './PortalKPIStrip.vue'
import PortalCompanyChart from './PortalCompanyChart.vue'
import PortalProductTable from './PortalProductTable.vue'

defineProps({
  data: Object,
})

defineEmits(['logout'])
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

@media (max-width: 768px) {
  .section-grid {
    grid-template-columns: 1fr;
  }
}
</style>
