<template>
  <div class="products-section">
    <h3>המוצרים שלך <span class="count-badge">{{ products.length }}</span></h3>

    <!-- Company cards grid -->
    <div class="company-grid">
      <div
        v-for="group in companyGroups"
        :key="group.company"
        class="company-card"
        @click="openModal(group)"
      >
        <div class="card-top">
          <span class="company-name">{{ group.shortName }}</span>
          <span class="product-count">{{ group.products.length }} מוצרים</span>
        </div>
        <div class="card-metrics">
          <div class="metric">
            <span class="metric-label">צבירה</span>
            <span class="metric-value ltr-number">{{ formatCompact(group.totalAccumulation) }}</span>
          </div>
          <div class="metric" v-if="group.totalPremium">
            <span class="metric-label">פרמיה</span>
            <span class="metric-value ltr-number">{{ formatCompact(group.totalPremium) }}</span>
          </div>
        </div>
        <div class="card-statuses">
          <span v-if="group.activeCount" class="mini-badge active">{{ group.activeCount }} פעיל</span>
          <span v-if="group.inactiveCount" class="mini-badge inactive">{{ group.inactiveCount }} לא פעיל</span>
        </div>
        <div class="card-arrow">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
        </div>
      </div>
    </div>

    <!-- Product detail modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="selectedGroup" class="modal-overlay" @click.self="closeModal">
          <div class="modal-card">
            <div class="modal-header">
              <div>
                <h4>{{ selectedGroup.company }}</h4>
                <p class="modal-subtitle">
                  {{ selectedGroup.products.length }} מוצרים
                  <span class="sep">&middot;</span>
                  צבירה: <span class="ltr-number">{{ formatNum(selectedGroup.totalAccumulation) }}</span> &#8362;
                </p>
              </div>
              <button class="close-btn" @click="closeModal">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            <div class="modal-body">
              <div
                v-for="(p, i) in selectedGroup.products"
                :key="i"
                class="product-row"
              >
                <div class="product-main">
                  <span class="product-name">{{ p.product || '—' }}</span>
                  <span class="product-type">{{ p.product_type || '' }}</span>
                </div>
                <div class="product-details">
                  <div class="detail-item" v-if="p.track">
                    <span class="detail-label">מסלול</span>
                    <span class="detail-value">{{ p.track }}</span>
                  </div>
                  <div class="detail-item" v-if="p.accumulation">
                    <span class="detail-label">צבירה</span>
                    <span class="detail-value ltr-number">{{ formatNum(p.accumulation) }} &#8362;</span>
                  </div>
                  <div class="detail-item" v-if="p.total_premium">
                    <span class="detail-label">פרמיה</span>
                    <span class="detail-value ltr-number">{{ formatNum(p.total_premium) }} &#8362;</span>
                  </div>
                  <div class="detail-item" v-if="p.fund_policy_number">
                    <span class="detail-label">מספר חשבון</span>
                    <span class="detail-value ltr-number">{{ p.fund_policy_number }}</span>
                  </div>
                </div>
                <div class="product-footer">
                  <span class="status-badge" :class="statusClass(p.product_status)">
                    {{ p.product_status || '—' }}
                  </span>
                  <span v-if="p.sign_date" class="sign-date ltr-number">{{ formatDate(p.sign_date) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  products: Array,
})

const selectedGroup = ref(null)

const companyGroups = computed(() => {
  const map = {}
  for (const p of (props.products || [])) {
    const co = p.receiving_company || 'אחר'
    if (!map[co]) {
      map[co] = {
        company: co,
        shortName: shortenCompany(co),
        products: [],
        totalAccumulation: 0,
        totalPremium: 0,
        activeCount: 0,
        inactiveCount: 0,
      }
    }
    map[co].products.push(p)
    map[co].totalAccumulation += p.accumulation || 0
    map[co].totalPremium += p.total_premium || 0
    if (p.product_status === 'פעיל') map[co].activeCount++
    else map[co].inactiveCount++
  }
  return Object.values(map).sort((a, b) => b.totalAccumulation - a.totalAccumulation)
})

function openModal(group) {
  selectedGroup.value = group
  document.body.style.overflow = 'hidden'
}

function closeModal() {
  selectedGroup.value = null
  document.body.style.overflow = ''
}

function shortenCompany(name) {
  return name
    .replace(/\s*בע"מ\s*/g, '')
    .replace(/\s*חברה לביטוח\s*/g, '')
    .replace(/\s*פנסיה וגמל\s*/g, '')
    .replace(/\s*גמל ופנסיה\s*/g, '')
    .trim()
}

function formatCompact(val) {
  if (val >= 1_000_000) return `₪${(val / 1_000_000).toFixed(1)}M`
  if (val >= 1_000) return `₪${Math.round(val / 1_000)}K`
  return `₪${Math.round(val)}`
}

function formatNum(val) {
  return new Intl.NumberFormat('he-IL', { maximumFractionDigits: 0 }).format(val)
}

function formatDate(d) {
  if (!d) return ''
  return d.substring(0, 10)
}

function statusClass(status) {
  if (!status) return ''
  if (status === 'פעיל') return 'active'
  return 'inactive'
}
</script>

<style scoped>
.products-section {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
  padding: 20px;
}

h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  background: var(--primary-light);
  color: var(--primary);
  border-radius: 11px;
  font-size: 12px;
  font-weight: 700;
}

/* Company Cards Grid */
.company-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.company-card {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s var(--transition);
}

.company-card:hover {
  border-color: var(--primary);
  box-shadow: var(--shadow-glow);
  background: var(--card-bg);
}

.card-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.company-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.product-count {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
}

.card-metrics {
  display: flex;
  gap: 20px;
}

.metric {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.metric-label {
  font-size: 10px;
  color: var(--text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.metric-value {
  font-size: 14px;
  font-weight: 800;
  color: var(--text);
}

.card-statuses {
  display: flex;
  gap: 6px;
}

.mini-badge {
  font-size: 10px;
  font-weight: 700;
  padding: 1px 8px;
  border-radius: 8px;
}

.mini-badge.active {
  background: var(--green-light);
  color: var(--green);
}

.mini-badge.inactive {
  background: #f0f0f0;
  color: var(--text-muted);
}

.card-arrow {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted);
  opacity: 0;
  transition: opacity 0.2s;
}

.company-card:hover .card-arrow {
  opacity: 1;
}

/* Modal */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 1010;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.modal-card {
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 100%;
  max-width: 560px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid var(--border-subtle);
}

.modal-header h4 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 4px;
}

.modal-subtitle {
  font-size: 12px;
  color: var(--text-muted);
  margin: 0;
  font-weight: 600;
}

.modal-subtitle .sep {
  margin: 0 4px;
  opacity: 0.4;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.15s;
  flex-shrink: 0;
}

.close-btn:hover {
  background: var(--bg);
  color: var(--text);
}

.modal-body {
  overflow-y: auto;
  padding: 8px 24px 20px;
}

/* Product rows in modal */
.product-row {
  padding: 14px 0;
  border-bottom: 1px solid var(--border-subtle);
}

.product-row:last-child {
  border-bottom: none;
}

.product-main {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 8px;
}

.product-name {
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}

.product-type {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 500;
}

.product-details {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 16px;
  margin-bottom: 8px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 4px;
}

.detail-label {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
}

.detail-value {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 700;
}

.product-footer {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 10px;
  font-weight: 700;
}

.status-badge.active {
  background: var(--green-light);
  color: var(--green);
}

.status-badge.inactive {
  background: #f0f0f0;
  color: var(--text-muted);
}

.sign-date {
  font-size: 11px;
  color: var(--text-muted);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
}

/* Transitions */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.25s var(--transition);
}

.modal-enter-active .modal-card,
.modal-leave-active .modal-card {
  transition: transform 0.25s var(--transition);
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-from .modal-card {
  transform: translateY(20px) scale(0.97);
}

.modal-leave-to .modal-card {
  transform: translateY(10px) scale(0.98);
}

@media (max-width: 768px) {
  .modal-card {
    max-height: 90vh;
  }
}
</style>
