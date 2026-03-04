<template>
  <div class="tabs-container">
    <div class="tabs" ref="tabsRef">
      <div class="tab-indicator" :style="indicatorStyle"></div>
      <button
        v-for="(tab, idx) in tabs"
        :key="tab.id"
        :ref="el => tabEls[idx] = el"
        :data-tour="'tab-' + tab.id"
        class="tab-btn"
        :class="{ active: modelValue === tab.id }"
        @click="$emit('update:modelValue', tab.id)"
      >
        <span class="tab-icon-wrap" :style="{ background: modelValue === tab.id ? tab.gradient : 'transparent' }">
          <svg v-if="tab.id === 'production'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="16" y1="13" x2="8" y2="13"/>
            <line x1="16" y1="17" x2="8" y2="17"/>
          </svg>
          <svg v-else-if="tab.id === 'comparison'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
          </svg>
          <svg v-else-if="tab.id === 'recruits'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/>
            <circle cx="9" cy="7" r="4"/>
            <path d="M23 21v-2a4 4 0 00-3-3.87"/>
            <path d="M16 3.13a4 4 0 010 7.75"/>
          </svg>
          <svg v-else-if="tab.id === 'commission-rates'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
            <line x1="3" y1="9" x2="21" y2="9"/>
            <line x1="3" y1="15" x2="21" y2="15"/>
            <line x1="9" y1="3" x2="9" y2="21"/>
            <line x1="15" y1="3" x2="15" y2="21"/>
          </svg>
          <svg v-else-if="tab.id === 'unpaid-summary'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="1" x2="12" y2="23"/>
            <path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
          </svg>
          <svg v-else-if="tab.id === 'company-emails'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
            <polyline points="22,6 12,13 2,6"/>
          </svg>
        </span>
        <span class="tab-label">{{ tab.label }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: String, required: true },
})
defineEmits(['update:modelValue'])

const tabs = [
  { id: 'production', label: 'פרודוקציה', gradient: 'linear-gradient(135deg, rgba(99,102,241,0.2), rgba(34,211,238,0.2))' },
  { id: 'comparison', label: 'השוואת נפרעים', gradient: 'linear-gradient(135deg, rgba(52,211,153,0.2), rgba(34,211,238,0.2))' },
  { id: 'recruits', label: 'גיוס חדש', gradient: 'linear-gradient(135deg, rgba(167,139,250,0.2), rgba(251,113,133,0.2))' },
  { id: 'unpaid-summary', label: 'סיכום חובות', gradient: 'linear-gradient(135deg, rgba(234,0,30,0.2), rgba(232,114,10,0.2))' },
  { id: 'commission-rates', label: 'טבלת עמלות', gradient: 'linear-gradient(135deg, rgba(251,191,36,0.2), rgba(245,158,11,0.2))' },
  { id: 'company-emails', label: 'אימיילים לחברות', gradient: 'linear-gradient(135deg, rgba(56,189,248,0.2), rgba(99,102,241,0.2))' },
]

const tabsRef = ref(null)
const tabEls = ref([])
const indicatorStyle = ref({})

function updateIndicator() {
  const activeIdx = tabs.findIndex(t => t.id === props.modelValue)
  const el = tabEls.value[activeIdx]
  if (el && tabsRef.value) {
    const container = tabsRef.value.getBoundingClientRect()
    const rect = el.getBoundingClientRect()
    // RTL: anchor is right, so calculate offset from the right edge
    const offsetRight = container.right - rect.right
    indicatorStyle.value = {
      width: `${rect.width}px`,
      transform: `translateX(${-offsetRight}px)`,
    }
  }
}

onMounted(() => {
  nextTick(updateIndicator)
})

watch(() => props.modelValue, () => {
  nextTick(updateIndicator)
})
</script>

<style scoped>
.tabs-container {
  display: flex;
  justify-content: center;
  padding: 16px 0 0;
  margin-bottom: 16px;
  position: sticky;
  top: 56px;
  z-index: 90;
  background: var(--bg);
}

.tabs {
  display: inline-flex;
  position: relative;
  gap: 2px;
  background: var(--card-bg);
  border: 1px solid var(--glass-border);
  border-radius: 16px;
  padding: 4px;
  box-shadow: var(--shadow-md), var(--shadow-glow);
}

.tab-indicator {
  position: absolute;
  top: 4px;
  right: 0;
  height: calc(100% - 8px);
  background: var(--primary-light);
  border: 1px solid var(--primary-light);
  border-radius: 12px;
  transition: all 0.4s var(--transition);
  pointer-events: none;
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 28px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 500;
  font-family: inherit;
  color: var(--text-muted);
  background: transparent;
  cursor: pointer;
  transition: all 0.3s var(--transition);
  white-space: nowrap;
  position: relative;
  z-index: 1;
}

.tab-btn:hover:not(.active) {
  color: var(--text-secondary);
}

.tab-btn.active {
  color: var(--text);
  font-weight: 600;
}

.tab-icon-wrap {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s var(--transition);
  flex-shrink: 0;
}

.tab-btn.active .tab-icon-wrap {
  color: var(--primary);
}

@media (max-width: 860px) {
  .tab-btn {
    padding: 10px 14px;
    gap: 6px;
  }
  .tab-label {
    font-size: 12px;
  }
}

@media (max-width: 640px) {
  .tab-btn {
    padding: 10px 12px;
  }
  .tab-label {
    display: none;
  }
  .tab-icon-wrap {
    width: 32px;
    height: 32px;
  }
}
</style>
