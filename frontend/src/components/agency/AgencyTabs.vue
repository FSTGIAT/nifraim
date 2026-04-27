<template>
  <!-- Always-visible compact pill strip — mirrors WorkspaceTabs in content mode -->
  <div class="ag-strip">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      class="ag-strip-tab"
      :class="{ active: modelValue === tab.id }"
      :style="{ '--accent': tab.accent, '--accent-glow': tab.accentGlow }"
      @click="$emit('update:modelValue', tab.id)"
    >
      <span class="ag-strip-icon">
        <svg v-if="tab.id === 'overview'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
          <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/>
        </svg>
        <svg v-else-if="tab.id === 'production'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
        </svg>
        <svg v-else-if="tab.id === 'comparison'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M9 17v-6a3 3 0 016 0v6m-9 4h12"/><circle cx="12" cy="6" r="2"/>
        </svg>
        <svg v-else-if="tab.id === 'commission-rates'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="5" x2="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>
        </svg>
        <svg v-else-if="tab.id === 'company-emails'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 7L2 7"/>
        </svg>
        <svg v-else-if="tab.id === 'recruits'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
        </svg>
        <svg v-else-if="tab.id === 'ai-library'" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/>
          <path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/>
        </svg>
      </span>
      {{ tab.label }}
    </button>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: String, required: true },
})
defineEmits(['update:modelValue'])

const tabs = [
  { id: 'overview',         label: 'לוח בקרה',         accent: '#F57C00', accentGlow: 'rgba(245, 124, 0, 0.18)' },
  { id: 'comparison',       label: 'השוואת נפרעים',    accent: '#22d3ee', accentGlow: 'rgba(34, 211, 238, 0.15)' },
  { id: 'production',       label: 'פרודוקציה',        accent: '#6366f1', accentGlow: 'rgba(99, 102, 241, 0.15)' },
  { id: 'commission-rates', label: 'טבלת עמלות',       accent: '#f59e0b', accentGlow: 'rgba(245, 158, 11, 0.15)' },
  { id: 'company-emails',   label: 'אימיילים לחברות',  accent: '#3b82f6', accentGlow: 'rgba(59, 130, 246, 0.15)' },
  { id: 'recruits',         label: 'תיקי סוכנים',      accent: '#a78bfa', accentGlow: 'rgba(167, 139, 250, 0.15)' },
  { id: 'ai-library',       label: 'ספריית AI',         accent: '#F57C00', accentGlow: 'rgba(245, 124, 0, 0.18)' },
]
</script>

<style scoped>
/* STRIP: compact horizontal tab bar */
.ag-strip {
  display: flex; align-items: center; gap: 4px;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid var(--border);
  border-radius: 12px;
  margin: 16px 0 18px;
  position: sticky; top: 70px; z-index: 90;
  backdrop-filter: blur(8px);
  box-shadow: var(--shadow-sm);
}
.ag-strip-tab {
  display: inline-flex; align-items: center; gap: 6px;
  background: transparent; border: none; cursor: pointer;
  padding: 7px 14px; border-radius: 999px;
  font-size: 13px; font-weight: 600; color: var(--text-secondary);
  font-family: inherit;
  transition: all .15s var(--transition);
}
.ag-strip-tab:hover { background: var(--accent-glow); color: var(--accent); }
.ag-strip-tab.active {
  background: var(--accent);
  color: #fff;
}
.ag-strip-icon { display: inline-flex; }

@media (max-width: 700px) {
  .ag-strip { overflow-x: auto; flex-wrap: nowrap; }
}
</style>
