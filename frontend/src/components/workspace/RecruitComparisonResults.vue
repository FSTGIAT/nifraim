<template>
  <div class="comparison-results glass-card">
    <div class="results-header">
      <div class="header-title">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <h3>תוצאות בדיקה</h3>
      </div>
      <button class="btn-close" @click="recruitsStore.resetComparison()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"/>
          <line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>

    <div class="summary-bar">
      <div class="summary-item found">
        <span class="summary-value">{{ result.found }}</span>
        <span class="summary-label">נמצאו</span>
      </div>
      <div class="summary-item not-found">
        <span class="summary-value">{{ result.not_found }}</span>
        <span class="summary-label">לא נמצאו</span>
      </div>
      <div class="summary-item total">
        <span class="summary-value">{{ result.total }}</span>
        <span class="summary-label">סה"כ</span>
      </div>
    </div>

    <div class="results-list">
      <TransitionGroup name="result-item">
        <div
          v-for="(item, idx) in result.results"
          :key="item.recruit_id"
          class="result-item"
          :class="{ found: item.found_in_production, 'not-found': !item.found_in_production }"
          :style="{ animationDelay: `${idx * 50}ms` }"
        >
          <div class="result-main">
            <div class="result-status">
              <div v-if="item.found_in_production" class="status-dot found-dot">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </div>
              <div v-else class="status-dot not-found-dot">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </div>
            </div>
            <div class="result-info">
              <span class="result-name">{{ item.first_name }} {{ item.last_name }}</span>
              <span class="result-id ltr-number">{{ item.id_number }}</span>
            </div>
            <div class="result-meta" v-if="item.company || item.product">
              <span class="meta-tag" v-if="item.company">{{ item.company }}</span>
              <span class="meta-tag" v-if="item.product">{{ item.product }}</span>
            </div>
          </div>

          <div v-if="item.found_in_production && item.production_products.length" class="result-details">
            <span class="detail-label">מוצרים בפרודוקציה</span>
            <div class="product-list">
              <div v-for="(p, i) in item.production_products" :key="i" class="product-item">
                <span class="product-name">{{ p.product || p.product_type || 'מוצר' }}</span>
                <span class="product-company" v-if="p.company">{{ p.company }}</span>
                <span class="product-premium ltr-number" v-if="p.premium">₪{{ Number(p.premium).toLocaleString() }}</span>
              </div>
            </div>
            <div class="total-premium">
              סה"כ פרמיה: <strong class="ltr-number">₪{{ Number(item.production_premium).toLocaleString() }}</strong>
            </div>
          </div>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<script setup>
import { useRecruitsStore } from '../../stores/recruits.js'

defineProps({
  result: { type: Object, required: true },
})

const recruitsStore = useRecruitsStore()
</script>

<style scoped>
.comparison-results {
  padding: 24px;
  animation: slideUp 0.5s var(--transition);
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--primary);
}

.header-title h3 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: -0.3px;
}

.btn-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--text-muted);
  transition: all 0.25s var(--transition);
}

.btn-close:hover {
  background: var(--bg-surface);
  color: var(--text);
}

.summary-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 24px;
}

.summary-item {
  flex: 1;
  text-align: center;
  padding: 16px 12px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border-subtle);
}

.summary-item.found {
  background: var(--green-light);
  border-color: var(--green-light);
}

.summary-item.not-found {
  background: var(--red-light);
  border-color: var(--red-light);
}

.summary-item.total {
  background: var(--border-subtle);
}

.summary-value {
  display: block;
  font-size: 28px;
  font-weight: 800;
  letter-spacing: -1px;
}

.found .summary-value { color: var(--accent-emerald); }
.not-found .summary-value { color: var(--red); }
.total .summary-value { color: var(--text); }

.summary-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-top: 4px;
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-item {
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm);
  overflow: hidden;
  transition: all 0.25s var(--transition);
  animation: slideUp 0.4s var(--transition) both;
}

.result-item:hover {
  border-color: var(--border);
  background: var(--border-subtle);
}

.result-item.found {
  border-right: 3px solid var(--accent-emerald);
}

.result-item.not-found {
  border-right: 3px solid var(--red);
}

.result-main {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
}

.status-dot {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.found-dot {
  background: var(--green-light);
  color: var(--accent-emerald);
}

.not-found-dot {
  background: var(--red-light);
  color: var(--red);
}

.result-info {
  display: flex;
  gap: 12px;
  align-items: center;
}

.result-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text);
}

.result-id {
  font-size: 12px;
  color: var(--text-muted);
  font-family: monospace;
}

.result-meta {
  margin-right: auto;
  display: flex;
  gap: 6px;
}

.meta-tag {
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-surface);
  padding: 3px 8px;
  border-radius: 4px;
}

.result-details {
  padding: 12px 16px 16px;
  background: var(--border-subtle);
  border-top: 1px solid var(--border-subtle);
}

.detail-label {
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}

.product-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.product-item {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: var(--text-secondary);
  padding: 5px 0;
}

.product-company {
  color: var(--text-muted);
}

.product-premium {
  margin-right: auto;
  font-weight: 700;
  color: var(--primary);
}

.total-premium {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--border-subtle);
  font-size: 13px;
  color: var(--text-secondary);
}

.total-premium strong {
  color: var(--text);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

.result-item-enter-active { animation: slideUp 0.4s var(--transition); }
</style>
