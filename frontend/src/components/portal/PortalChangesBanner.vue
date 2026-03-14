<template>
  <div v-if="visible" class="changes-banner" :class="{ expanded }">
    <div class="banner-header" @click="expanded = !expanded">
      <div class="banner-icon">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/>
          <line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
      </div>
      <span class="banner-summary">
        שינויים בתיק:
        <strong v-if="changes.added?.length">{{ changes.added.length }} מוצרים חדשים</strong>
        <strong v-if="changes.removed?.length">{{ changes.removed.length }} הוסרו</strong>
        <strong v-if="changes.changed?.length">{{ changes.changed.length }} שונו</strong>
      </span>
      <button class="expand-btn">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline :points="expanded ? '18 15 12 9 6 15' : '6 9 12 15 18 9'"/>
        </svg>
      </button>
      <button class="dismiss-btn" @click.stop="dismiss" title="סגור">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    </div>

    <Transition name="slide">
      <div v-if="expanded" class="banner-details">
        <!-- Added -->
        <div v-if="changes.added?.length" class="change-group added">
          <h4>מוצרים חדשים</h4>
          <div v-for="(p, i) in changes.added" :key="'a' + i" class="change-card">
            <span class="change-product">{{ p.product || 'ללא שם' }}</span>
            <span class="change-company">{{ p.receiving_company }}</span>
            <span v-if="p.total_premium" class="ltr-number">₪{{ p.total_premium.toLocaleString() }}</span>
          </div>
        </div>

        <!-- Removed -->
        <div v-if="changes.removed?.length" class="change-group removed">
          <h4>מוצרים שהוסרו</h4>
          <div v-for="(p, i) in changes.removed" :key="'r' + i" class="change-card">
            <span class="change-product">{{ p.product || 'ללא שם' }}</span>
            <span class="change-company">{{ p.receiving_company }}</span>
            <span v-if="p.total_premium" class="ltr-number">₪{{ p.total_premium.toLocaleString() }}</span>
          </div>
        </div>

        <!-- Changed -->
        <div v-if="changes.changed?.length" class="change-group changed">
          <h4>מוצרים שהשתנו</h4>
          <div v-for="(p, i) in changes.changed" :key="'c' + i" class="change-card">
            <span class="change-product">{{ p.product || 'ללא שם' }}</span>
            <span class="change-company">{{ p.receiving_company }}</span>
            <div v-for="(d, j) in p.changes" :key="j" class="change-diff">
              <span class="diff-field">{{ fieldLabel(d.field) }}:</span>
              <span class="diff-old ltr-number">{{ formatVal(d.old_val) }}</span>
              <span class="diff-arrow">←</span>
              <span class="diff-new ltr-number">{{ formatVal(d.new_val) }}</span>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  changes: { type: Object, required: true },
})

const DISMISS_KEY = 'portal_changes_dismissed'
const expanded = ref(false)
const visible = ref(!sessionStorage.getItem(DISMISS_KEY))

function dismiss() {
  visible.value = false
  sessionStorage.setItem(DISMISS_KEY, 'true')
}

function fieldLabel(field) {
  const map = {
    total_premium: 'פרמיה',
    accumulation: 'צבירה',
    product_status: 'סטטוס',
  }
  return map[field] || field
}

function formatVal(val) {
  if (typeof val === 'number') return `₪${val.toLocaleString()}`
  return val || '—'
}
</script>

<style scoped>
.changes-banner {
  background: var(--card-bg);
  border: 1px solid #f59e0b;
  border-radius: var(--radius-lg);
  margin-bottom: 20px;
  overflow: hidden;
  animation: fadeInUp 0.4s var(--transition);
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.banner-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  cursor: pointer;
  background: rgba(245, 158, 11, 0.06);
  transition: background 0.2s ease;
}

.banner-header:hover {
  background: rgba(245, 158, 11, 0.1);
}

.banner-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  background: rgba(245, 158, 11, 0.15);
  color: #f59e0b;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.banner-summary {
  flex: 1;
  font-size: 13.5px;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.banner-summary strong {
  font-weight: 700;
  color: #d97706;
}

.expand-btn,
.dismiss-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: none;
  background: transparent;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
}

.expand-btn:hover,
.dismiss-btn:hover {
  background: var(--border-subtle);
  color: var(--text);
}

/* Details */
.banner-details {
  padding: 0 16px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.slide-enter-active,
.slide-leave-active {
  transition: all 0.25s ease;
  overflow: hidden;
}

.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  max-height: 0;
  padding-top: 0;
  padding-bottom: 0;
}

.change-group h4 {
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  margin: 0 0 8px;
}

.change-group.added h4 { color: #16a34a; }
.change-group.removed h4 { color: #dc2626; }
.change-group.changed h4 { color: #d97706; }

.change-card {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 8px 12px;
  border-radius: var(--radius-sm);
  font-size: 13px;
  margin-bottom: 4px;
}

.added .change-card { background: rgba(22, 163, 74, 0.06); border-right: 3px solid #16a34a; }
.removed .change-card { background: rgba(220, 38, 38, 0.06); border-right: 3px solid #dc2626; }
.changed .change-card { background: rgba(217, 119, 6, 0.06); border-right: 3px solid #d97706; }

.change-product {
  font-weight: 600;
  color: var(--text);
}

.change-company {
  font-size: 12px;
  color: var(--text-muted);
}

.change-diff {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  width: 100%;
  margin-top: 4px;
}

.diff-field {
  color: var(--text-muted);
  font-weight: 600;
}

.diff-old {
  color: #dc2626;
  text-decoration: line-through;
}

.diff-arrow {
  color: var(--text-muted);
  font-size: 10px;
}

.diff-new {
  color: #16a34a;
  font-weight: 600;
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}
</style>
