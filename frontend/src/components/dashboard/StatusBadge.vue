<template>
  <span class="badge" :class="status">{{ label }}</span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: { type: String, required: true },
})

const LABELS = {
  paid_match: 'שולם - תואם',
  paid_mismatch: 'שולם - חריגה',
  unpaid: 'לא שולם',
  cancelled: 'בוטל',
  no_data: 'אין נתונים',
  matched: 'נמצא בשני הקבצים',
  missing_from_report: 'חסר בדוח חברה',
  extra_in_report: 'חסר בקובץ סוכן',
}

const label = computed(() => LABELS[props.status] || props.status)
</script>

<style scoped>
.badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  white-space: nowrap;
  letter-spacing: 0.2px;
}

.paid_match {
  background: var(--green-light);
  color: var(--green);
  border: 1px solid var(--green-light);
}

.paid_mismatch {
  background: var(--amber-light);
  color: var(--amber);
  border: 1px solid var(--amber-light);
}

.unpaid {
  background: var(--red-light);
  color: var(--red);
  border: 1px solid var(--red-light);
}

.cancelled {
  background: var(--border-subtle);
  color: var(--text-muted);
  border: 1px solid var(--border-subtle);
}

.no_data {
  background: rgba(100, 116, 139, 0.08);
  color: var(--text-muted);
  border: 1px solid rgba(100, 116, 139, 0.1);
}

.matched {
  background: var(--primary-light);
  color: var(--primary);
  border: 1px solid var(--primary-light);
}

.missing_from_report {
  background: var(--amber-light);
  color: var(--amber);
  border: 1px solid var(--amber-light);
}

.extra_in_report {
  background: rgba(127, 86, 217, 0.08);
  color: var(--accent-violet);
  border: 1px solid rgba(127, 86, 217, 0.08);
}
</style>
