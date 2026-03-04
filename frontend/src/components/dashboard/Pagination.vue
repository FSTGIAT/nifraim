<template>
  <div class="pagination" v-if="pages > 1">
    <div class="page-info">
      <span class="ltr-number">{{ total }}</span> רשומות · עמוד <span class="ltr-number">{{ page }}</span> מתוך <span class="ltr-number">{{ pages }}</span>
    </div>
    <div class="page-buttons">
      <button :disabled="page <= 1" @click="$emit('change', page - 1)">&#8594;</button>
      <template v-for="p in visiblePages" :key="p">
        <button
          v-if="p !== '...'"
          :class="{ active: p === page }"
          @click="$emit('change', p)"
        >
          <span class="ltr-number">{{ p }}</span>
        </button>
        <span v-else class="dots">...</span>
      </template>
      <button :disabled="page >= pages" @click="$emit('change', page + 1)">&#8592;</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Number, required: true },
  pages: { type: Number, required: true },
  total: { type: Number, required: true },
})

defineEmits(['change'])

const visiblePages = computed(() => {
  const p = props.page
  const total = props.pages
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages = []
  pages.push(1)
  if (p > 3) pages.push('...')
  for (let i = Math.max(2, p - 1); i <= Math.min(total - 1, p + 1); i++) {
    pages.push(i)
  }
  if (p < total - 2) pages.push('...')
  pages.push(total)
  return pages
})
</script>

<style scoped>
.pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding: 12px 0;
}

.page-info {
  font-size: 13px;
  color: var(--text-muted);
}

.ltr-number {
  direction: ltr;
  unicode-bidi: isolate;
}

.page-buttons {
  display: flex;
  gap: 4px;
  align-items: center;
}

.page-buttons button {
  background: var(--bg-surface);
  border: 1px solid var(--glass-border);
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  color: var(--text);
  cursor: pointer;
  transition: all 0.2s;
}

.page-buttons button:hover:not(:disabled) {
  background: var(--primary-light);
  border-color: var(--primary-light);
}

.page-buttons button.active {
  background: linear-gradient(135deg, var(--primary-deep), var(--primary));
  color: white;
  border-color: transparent;
  box-shadow: 0 2px 8px var(--primary-light);
}

.page-buttons button:disabled {
  opacity: 0.3;
  cursor: default;
}

.dots {
  padding: 0 4px;
  color: var(--text-muted);
}
</style>
