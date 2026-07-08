<template>
  <!-- The ONE close affordance for every portal surface (banner, modal, chat).
       Replaces three hand-rolled X buttons that each had different sizes/radii. -->
  <button type="button" class="portal-close" :aria-label="label" @click="$emit('click')">
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor"
         stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M18 6 6 18" /><path d="m6 6 12 12" />
    </svg>
  </button>
</template>

<script setup>
defineProps({
  label: { type: String, default: 'סגור' },
})
defineEmits(['click'])
</script>

<style scoped>
.portal-close {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--radius-sm, 8px);
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}

.portal-close:hover {
  background: var(--primary-light);
  color: var(--text);
  border-color: var(--border-subtle);
}

.portal-close:focus-visible {
  outline: 2px solid var(--primary);
  outline-offset: 1px;
}
</style>
