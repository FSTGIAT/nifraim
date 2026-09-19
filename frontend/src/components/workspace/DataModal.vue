<template>
  <Teleport to="body">
    <Transition name="dm">
      <div v-if="open" class="dm-overlay" @click.self="$emit('close')">
        <div class="dm-card" :class="'dm-card--' + size" role="dialog" aria-modal="true">
          <div class="dm-head">
            <h4>{{ title }}</h4>
            <span v-if="subtitle" class="dm-sub ltr-number">{{ subtitle }}</span>
            <button class="dm-close" @click="$emit('close')" aria-label="סגור">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                   stroke-width="2.5" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12" /></svg>
            </button>
          </div>
          <div class="dm-body"><slot /></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { watch, onBeforeUnmount } from 'vue'

// Every chart in the insights tab drills into the same shell, so "click a mark
// → see the rows behind it" behaves identically wherever it is used. It is also
// the table view the charts owe: several palette slots sit under 3:1 contrast
// against the card surface, which obligates a readable text alternative.
const props = defineProps({
  open: { type: Boolean, default: false },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  // A table of many rows and a single-figure card want very different widths;
  // one 900px shell around one row is mostly empty space.
  size: { type: String, default: 'lg' },  // 'sm' | 'lg' | 'xl'
})
const emit = defineEmits(['close'])

function onKey(e) {
  if (e.key === 'Escape') emit('close')
}
watch(() => props.open, (isOpen) => {
  if (isOpen) window.addEventListener('keydown', onKey)
  else window.removeEventListener('keydown', onKey)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.dm-overlay {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.45);
  display: flex; align-items: center; justify-content: center;
  z-index: 1010; padding: 20px;
}
.dm-card {
  background: var(--card-bg); border: 1px solid var(--glass-border);
  border-radius: var(--radius-lg); width: 100%;
  max-height: 84vh; display: flex; flex-direction: column;
}
.dm-card--lg { max-width: 900px; }
/* A bookcase needs room for a row of binders; at 900px it wraps to four rows. */
.dm-card--xl { max-width: 1180px; }
.dm-card--sm { max-width: 440px; }
.dm-head {
  display: flex; align-items: center; gap: 12px;
  padding: 16px 20px; border-bottom: 1px solid var(--border-subtle);
}
.dm-head h4 { font-size: 16px; font-weight: 700; color: var(--text); flex: 1; }
.dm-sub { font-size: 12px; color: var(--text-muted); }
.dm-close {
  background: none; border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm); color: var(--text-muted);
  padding: 5px; cursor: pointer; display: flex;
}
.dm-close:hover { color: var(--text); }
.dm-body { overflow-y: auto; padding: 16px 20px; }

/* One movement, on the thing the click produced — not a page full of drifting
   cards. Respects a reduced-motion preference. */
.dm-enter-active, .dm-leave-active { transition: opacity 0.18s ease; }
.dm-enter-active .dm-card, .dm-leave-active .dm-card {
  transition: transform 0.18s cubic-bezier(0.2, 0, 0.2, 1);
}
.dm-enter-from, .dm-leave-to { opacity: 0; }
.dm-enter-from .dm-card, .dm-leave-to .dm-card { transform: translateY(8px) scale(0.99); }
@media (prefers-reduced-motion: reduce) {
  .dm-enter-active, .dm-leave-active,
  .dm-enter-active .dm-card, .dm-leave-active .dm-card { transition: none; }
}
</style>
