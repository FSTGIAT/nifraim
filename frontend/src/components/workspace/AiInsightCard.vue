<template>
  <div v-if="viewContext" class="ai-insight-card" :class="{ 'ai-insight-card--entered': entered }">
    <div class="ai-orb" aria-hidden="true"></div>

    <div class="ai-card-row ai-card-row--head">
      <span class="ai-eyebrow">
        <svg class="ai-eyebrow-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 2l1.8 5.2L19 9l-5.2 1.8L12 16l-1.8-5.2L5 9l5.2-1.8z"/>
          <path d="M19 3v4"/>
          <path d="M5 17v4"/>
          <path d="M3 19h4"/>
          <path d="M17 19h4"/>
        </svg>
        <span>התמונה הכוללת — מופעל עם AI</span>
      </span>
      <button
        class="ai-copy-btn"
        :class="{ 'ai-copy-btn--done': copied }"
        :title="copied ? 'הועתק!' : 'העתק סיכום'"
        @click="copySummary"
        type="button"
        aria-label="העתק סיכום"
      >
        <svg v-if="!copied" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
          <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
        </svg>
        <svg v-else width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="20 6 9 17 4 12"/>
        </svg>
      </button>
    </div>

    <p class="ai-summary">{{ viewContext.summary }}</p>

    <div class="ai-card-row ai-card-row--actions">
      <div class="ai-chips">
        <button
          v-for="chip in viewContext.suggestions"
          :key="chip"
          class="ai-chip"
          @click="$emit('open-sheet', chip)"
          type="button"
        >
          {{ chip }}
        </button>
      </div>
      <button class="ai-continue" @click="$emit('open-sheet', '')" type="button">
        <span>המשך שיחה</span>
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <line x1="19" y1="12" x2="5" y2="12"/>
          <polyline points="12 19 5 12 12 5"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  viewContext: { type: Object, default: null },
})
defineEmits(['open-sheet'])

const entered = ref(false)
const copied = ref(false)

onMounted(() => {
  requestAnimationFrame(() => { entered.value = true })
})

async function copySummary() {
  if (!props.viewContext?.summary) return
  try {
    await navigator.clipboard.writeText(props.viewContext.summary)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1600)
  } catch {
    /* ignore */
  }
}
</script>

<style scoped>
.ai-insight-card {
  position: relative;
  border-radius: var(--radius-lg);
  padding: 16px 20px 14px;
  background:
    linear-gradient(145deg, rgba(245, 124, 0, 0.05) 0%, #ffffff 55%, rgba(245, 124, 0, 0.02) 100%),
    #ffffff;
  border: 1px solid rgba(245, 124, 0, 0.16);
  box-shadow: 0 6px 22px rgba(245, 124, 0, 0.06), 0 1px 2px rgba(17, 12, 6, 0.04);
  overflow: hidden;
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 0.35s var(--transition), transform 0.35s var(--transition);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.ai-insight-card--entered {
  opacity: 1;
  transform: translateY(0);
}

.ai-orb {
  position: absolute;
  inset-inline-start: -50px;
  top: -60px;
  width: 180px;
  height: 180px;
  background: radial-gradient(circle, rgba(245, 124, 0, 0.22), transparent 70%);
  border-radius: 50%;
  filter: blur(4px);
  pointer-events: none;
}

.ai-card-row {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.ai-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.3px;
  color: var(--primary-deep);
  text-transform: none;
}
.ai-eyebrow-icon {
  color: var(--primary);
  filter: drop-shadow(0 1px 2px rgba(245, 124, 0, 0.3));
}

.ai-copy-btn {
  width: 26px;
  height: 26px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid transparent;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.18s, background 0.15s, color 0.15s, border-color 0.15s;
}
.ai-insight-card:hover .ai-copy-btn,
.ai-copy-btn:focus-visible { opacity: 1; }
.ai-copy-btn:hover {
  background: var(--primary-light);
  color: var(--primary-deep);
  border-color: rgba(245, 124, 0, 0.22);
}
.ai-copy-btn--done {
  opacity: 1 !important;
  background: rgba(46, 132, 74, 0.1);
  color: var(--accent-emerald);
  border-color: rgba(46, 132, 74, 0.28);
}

.ai-summary {
  position: relative;
  z-index: 1;
  margin: 0;
  font-size: 14px;
  line-height: 1.65;
  color: var(--text);
  font-weight: 500;
}

.ai-card-row--actions {
  padding-top: 2px;
  justify-content: space-between;
  align-items: center;
}

.ai-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.ai-chip {
  display: inline-flex;
  align-items: center;
  padding: 7px 12px;
  font-size: 12.5px;
  font-weight: 600;
  line-height: 1.2;
  color: var(--primary-deep);
  background: var(--primary-light);
  border: 1px solid rgba(245, 124, 0, 0.22);
  border-radius: 999px;
  cursor: pointer;
  font-family: inherit;
  transition: transform 0.18s var(--transition), background 0.15s, border-color 0.15s, box-shadow 0.18s;
  white-space: nowrap;
}
.ai-chip:hover {
  transform: translateY(-2px);
  background: #ffe1bd;
  border-color: rgba(245, 124, 0, 0.4);
  box-shadow: 0 6px 14px rgba(245, 124, 0, 0.18);
}
.ai-chip:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.25);
}

.ai-continue {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-family: inherit;
  transition: color 0.15s, background 0.15s, transform 0.15s;
  flex-shrink: 0;
}
.ai-continue svg { opacity: 0.55; transition: transform 0.18s, opacity 0.18s; }
.ai-continue:hover {
  color: var(--primary-deep);
  background: rgba(245, 124, 0, 0.06);
}
.ai-continue:hover svg { opacity: 1; transform: translateX(-3px); }
.ai-continue:focus-visible {
  outline: none;
  color: var(--primary-deep);
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.2);
}

@media (max-width: 640px) {
  .ai-card-row--actions { flex-direction: column; align-items: stretch; gap: 8px; }
  .ai-continue { align-self: flex-end; }
}

@media (prefers-reduced-motion: reduce) {
  .ai-insight-card { transition: none; transform: none; opacity: 1; }
  .ai-chip:hover { transform: none; }
}
</style>
