<template>
  <Teleport to="body">
    <Transition name="dm">
      <div v-if="open" class="dm-overlay" @click.self="$emit('close')">
        <div class="dm-card" role="dialog" aria-modal="true">
          <header class="dm-head">
            <div>
              <h3 class="dm-title">{{ title }}</h3>
              <p class="dm-sub">{{ subtitle }}</p>
            </div>
            <button class="dm-x" @click="$emit('close')" aria-label="סגור">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M18 6 6 18"/><path d="m6 6 12 12"/>
              </svg>
            </button>
          </header>

          <div class="dm-body">
            <div v-if="!items.length" class="dm-empty">אין נתונים להצגה.</div>
            <table v-else class="dm-table">
              <thead>
                <tr>
                  <th>{{ labelHeader }}</th>
                  <th class="num">סכום</th>
                  <th class="num">חיובים</th>
                  <th class="meta">פירוט</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, i) in items" :key="i">
                  <td class="dm-label">
                    <span class="dm-rank">{{ i + 1 }}</span>
                    {{ item.label }}
                  </td>
                  <td class="num bold">
                    <span class="ltr-number">{{ formatShekel(item.amount) }}</span>
                  </td>
                  <td class="num">
                    <span class="ltr-number">{{ (item.count ?? 0).toLocaleString('he-IL') }}</span>
                  </td>
                  <td class="meta">{{ item.meta || '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { shortShekel } from '../../utils/monthDeltas.js'

defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  labelHeader: { type: String, default: 'שם' },
  items: { type: Array, default: () => [] },
})
defineEmits(['close'])

function formatShekel(n) {
  if (n === null || n === undefined || isNaN(n)) return '—'
  return Number(n).toLocaleString('he-IL', { style: 'currency', currency: 'ILS', maximumFractionDigits: 0 })
}
</script>

<style scoped>
.dm-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 12, 6, 0.36);
  backdrop-filter: blur(4px);
  z-index: 1100;
  display: grid;
  place-items: center;
  padding: 24px;
}
.dm-card {
  background: #fff;
  border-radius: 16px;
  width: min(640px, 100%);
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  box-shadow: 0 24px 60px rgba(17, 12, 6, 0.18);
  font-family: 'Heebo', sans-serif;
}
.dm-card::before {
  content: '';
  display: block;
  height: 3px;
  background: linear-gradient(90deg, transparent, #F57C00, transparent);
}
.dm-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--border-subtle);
}
.dm-title { margin: 0; font-size: 16px; font-weight: 800; color: var(--text); }
.dm-sub { margin: 2px 0 0; font-size: 12px; color: var(--text-muted); }
.dm-x {
  width: 28px; height: 28px;
  display: grid; place-items: center;
  border: 1px solid var(--border-subtle);
  background: transparent;
  border-radius: 8px;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.dm-x:hover { background: var(--bg); color: var(--text); }

.dm-body { overflow-y: auto; padding: 4px 20px 20px; }
.dm-empty { padding: 30px; text-align: center; color: var(--text-muted); font-size: 13px; }

.dm-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.dm-table th, .dm-table td {
  padding: 10px 8px;
  text-align: start;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.06);
}
.dm-table th {
  font-weight: 700;
  color: var(--text-muted);
  font-size: 11.5px;
  background: var(--bg);
  position: sticky;
  top: 0;
  z-index: 1;
}
.dm-table td { vertical-align: middle; }
.dm-table .num { text-align: end; font-family: ui-monospace, "SF Mono", Menlo, monospace; }
.dm-table .num.bold { color: #c2410c; font-weight: 700; }
.dm-table .meta { color: var(--text-muted); font-size: 12px; }
.dm-label { display: flex; align-items: center; gap: 8px; font-weight: 600; }
.dm-rank {
  display: inline-grid;
  place-items: center;
  width: 22px; height: 22px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
  font-family: ui-monospace, "SF Mono", Menlo, monospace;
}

.dm-enter-active, .dm-leave-active { transition: opacity 0.18s ease; }
.dm-enter-active .dm-card, .dm-leave-active .dm-card { transition: transform 0.22s ease, opacity 0.22s ease; }
.dm-enter-from, .dm-leave-to { opacity: 0; }
.dm-enter-from .dm-card, .dm-leave-to .dm-card { opacity: 0; transform: translateY(8px) scale(0.98); }
</style>
