<template>
  <Teleport to="body">
    <!-- The grow starts in the transition's `enter` hook — i.e. before the
         card's first paint. Started a tick later (as it was), the card was
         drawn once at full size and THEN jumped to the tapped element and
         grew: "looks like something ran before" (QA 2026-09-30). -->
    <Transition name="dm" @enter="onEnter">
      <div v-if="open" class="dm-overlay" :class="{ 'dm-overlay--morph': morphing }"
           :style="layer ? { zIndex: layer } : null"
           @click.self="requestClose">
        <div ref="cardEl" class="dm-card" :class="'dm-card--' + size" role="dialog" aria-modal="true"
             :style="accent ? { '--dm-accent': accent } : null">
          <div class="dm-head" :style="accent ? { '--dm-accent': accent } : null">
            <h4>{{ title }}</h4>
            <!-- "דורש טיפול" header style: a count badge and the period beside
                 the title. Optional — windows that pass neither look as before. -->
            <span v-if="badge !== null && badge !== ''" class="dm-badge ltr-number">{{ badge }}</span>
            <span v-if="period" class="dm-period ltr-number">{{ period }}</span>
            <span v-if="subtitle" class="dm-sub ltr-number">{{ subtitle }}</span>
            <!-- optional header action beside the title (e.g. "+ לקוח חדש") -->
            <slot name="head-action" />
            <button class="dm-close" @click="requestClose" aria-label="סגור">
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

<script>
// Shared by every DataModal instance: which drills are open, in order.
const openStack = []
</script>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import { useOriginMorph } from '../../composables/useOriginMorph'

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
  // The element that was tapped to open this drill. Given one, the card grows
  // out of it and folds back into it on close — the app's iPhone-style open
  // (composables/useOriginMorph). Without one: the plain fade below.
  origin: { type: null, default: null },
  badge: { type: [Number, String], default: null },
  period: { type: String, default: '' },
  // The owning tab's colour for the badge (e.g. var(--tab-comparison)).
  accent: { type: String, default: '' },
  // Stacking override for a drill opened FROM another drill (default 1010).
  layer: { type: Number, default: 0 },
})
const emit = defineEmits(['close'])

const cardEl = ref(null)
const morph = useOriginMorph()
// True while this open grows from a tapped element — the CSS nudge-in below is
// then switched off so two animations never fight over the card's transform.
const morphing = ref(false)

function onEnter(el) {
  if (!morph.hasOrigin()) return
  morph.grow(el.querySelector('.dm-card'))
}
let closing = false

async function requestClose() {
  if (closing) return
  closing = true
  try {
    if (morph.hasOrigin()) await morph.shrink(cardEl.value)
  } finally {
    closing = false
    emit('close')
  }
}

// Esc closes only the TOP drill. With a customer window open over the list
// it came from, each window heard the key and both closed (QA 2026-10-01).
const token = Symbol('dm')
function onKey(e) {
  if (e.key === 'Escape' && openStack[openStack.length - 1] === token) requestClose()
}
watch(() => props.open, (isOpen) => {
  if (isOpen) {
    openStack.push(token)
    window.addEventListener('keydown', onKey)
    // Runs before the DOM update (flush: 'pre'), so the origin is measured
    // before the card exists and `onEnter` can grow it on its first frame.
    morph.remember(props.origin instanceof Element ? props.origin : null)
    morphing.value = morph.hasOrigin()
  } else {
    dropFromStack()
    window.removeEventListener('keydown', onKey)
  }
})
function dropFromStack() {
  const i = openStack.lastIndexOf(token)
  if (i >= 0) openStack.splice(i, 1)
}
onBeforeUnmount(() => { dropFromStack(); window.removeEventListener('keydown', onKey) })
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
.dm-head h4 { font-size: 16px; font-weight: 700; color: var(--text); }
.dm-head .dm-close { margin-inline-start: auto; }
.dm-badge {
  min-width: 24px; height: 24px; padding: 0 8px; border-radius: 12px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 12.5px; font-weight: 800; color: #fff; background: var(--dm-accent, var(--text));
}
.dm-period { font-size: 12.5px; color: var(--text-muted); }
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
/* Growing from an origin: the morph owns the card's transform and opacity. */
.dm-overlay--morph.dm-enter-active .dm-card,
.dm-overlay--morph.dm-leave-active .dm-card { transition: none; }
.dm-overlay--morph.dm-enter-from .dm-card,
.dm-overlay--morph.dm-leave-to .dm-card { transform: none; }

/* Every row in a drill fills on hover, in the drill's colour (user 2026-10-10):
   the expandable row buttons, the customer-list rows and table rows. */
.dm-body :deep(button[aria-expanded]),
.dm-body :deep(.ccl-row), .dm-body :deep(.cd-row), .dm-body :deep(.rr-row),
.dm-body :deep(.cp-row), .dm-body :deep(.cr-row), .dm-body :deep(.dv-row),
.dm-body :deep(tbody tr) { transition: background-color 0.18s ease; }
.dm-body :deep(button[aria-expanded]:hover),
.dm-body :deep(.ccl-row:hover), .dm-body :deep(.cd-row:hover), .dm-body :deep(.rr-row:hover),
.dm-body :deep(.cp-row:hover), .dm-body :deep(.cr-row:hover), .dm-body :deep(.dv-row:hover),
.dm-body :deep(tbody tr:hover) {
  background-color: color-mix(in srgb, var(--dm-accent, var(--tab-production)) 8%, var(--card-bg));
}
</style>
