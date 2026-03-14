<template>
  <button
    class="nav-arrow"
    :class="[direction, { disabled }]"
    :disabled="disabled"
    @click="$emit('navigate')"
  >
    <span class="nav-arrow-label" v-if="label">{{ label }}</span>
    <svg class="nav-arrow-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polyline v-if="direction === 'next'" points="15 18 9 12 15 6"/>
      <polyline v-else points="9 18 15 12 9 6"/>
    </svg>
  </button>
</template>

<script setup>
defineProps({
  direction: { type: String, required: true },
  label: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})
defineEmits(['navigate'])
</script>

<style scoped>
.nav-arrow {
  position: fixed;
  top: 50%;
  transform: translateY(-50%);
  z-index: 50;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 10px;
  box-shadow: var(--shadow-sm);
  color: var(--text-muted);
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
  font-size: 12px;
  font-weight: 500;
}

.nav-arrow.next {
  left: 16px;
  flex-direction: row-reverse;
}

.nav-arrow.prev {
  right: 16px;
  flex-direction: row;
}

.nav-arrow:hover:not(.disabled) {
  color: var(--text);
  border-color: var(--border);
  box-shadow: var(--shadow-md);
}

.nav-arrow.next:hover:not(.disabled) {
  transform: translateY(-50%) translateX(-3px);
}

.nav-arrow.prev:hover:not(.disabled) {
  transform: translateY(-50%) translateX(3px);
}

.nav-arrow.disabled {
  opacity: 0.25;
  cursor: default;
}

.nav-arrow-icon {
  flex-shrink: 0;
}

@media (max-width: 860px) {
  .nav-arrow-label {
    display: none;
  }
  .nav-arrow {
    padding: 8px;
  }
}

@media (max-width: 768px) {
  .nav-arrow {
    display: none;
  }
}
</style>
