<template>
  <span class="badge" :class="status">{{ label }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
})

const LABELS = {
  matched: 'נמצא בשניהם',
  only_production: 'רק בפרודוקציה',
  only_commission: 'רק בנפרעים',
}

const label = computed(() => LABELS[props.status] || props.status)
</script>

<style scoped>
.badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
  letter-spacing: 0.2px;
}

.matched {
  background: var(--primary-light);
  color: var(--primary);
  border: 1px solid var(--primary-light);
}

.only_production {
  background: var(--amber-light);
  color: var(--amber);
  border: 1px solid var(--amber-light);
}

.only_commission {
  background: rgba(127, 86, 217, 0.08);
  color: var(--accent-violet);
  border: 1px solid rgba(127, 86, 217, 0.08);
}
</style>
