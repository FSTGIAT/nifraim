<template>
  <!-- The rectangular sibling of BigAddButton: same motion language (a dashed
       outline travelling, a solid leading edge riding it, a breathing halo,
       faster on hover) but on a rounded rectangle. The pen never moves — it's
       the target — only the line under it keeps being written. -->
  <button type="button" class="sd" :class="{ 'sd--sm': small, 'sd--nudge': nudge }"
          :title="label" :aria-label="label" @click="$emit('click')">
    <span class="sd-halo" aria-hidden="true"></span>
    <svg class="sd-frame" aria-hidden="true">
      <rect class="sd-dash" pathLength="100" />
      <rect class="sd-lead" pathLength="100" />
    </svg>
    <svg class="sd-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"
         stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path class="sd-ink" d="M12 20h9" pathLength="10" />
      <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
    </svg>
  </button>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  small: { type: Boolean, default: false },
  nudge: { type: Boolean, default: false },   // workshop never finished
})
defineEmits(['click'])
// Icon only on screen; the name lives in the tooltip and for screen readers.
const label = computed(() => (props.nudge ? 'סגנון הכתיבה שלי — עוד לא הוגדר' : 'סגנון הכתיבה שלי'))
</script>

<style scoped>
.sd {
  --sd-acc: var(--tab-mail);
  --sd-ink: var(--tab-mail-ink);
  --sd-r: 22px;
  --sd-speed: 14s;
  position: relative; isolation: isolate;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px;
  width: 210px; height: 128px; padding: 12px; font-family: inherit; cursor: pointer;
  color: var(--sd-ink); background: transparent; border: none; border-radius: var(--sd-r);
}
.sd:hover, .sd:focus-visible { --sd-speed: 7s; }
.sd:focus-visible { outline: 2px solid var(--sd-acc); outline-offset: 4px; }

/* halo — breathes like BigAddButton's */
.sd-halo {
  position: absolute; inset: -14px; z-index: -1; border-radius: calc(var(--sd-r) + 14px); pointer-events: none;
  background: radial-gradient(closest-side, color-mix(in srgb, var(--sd-acc) 55%, transparent), transparent);
  opacity: 0.18; animation: sd-breath 6s ease-in-out infinite;
}
.sd:hover .sd-halo { opacity: 0.32; }

/* the frame: geometry set in CSS so one SVG fits both sizes */
.sd-frame { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; pointer-events: none; }
.sd-frame rect { x: 1px; y: 1px; width: calc(100% - 2px); height: calc(100% - 2px); rx: calc(var(--sd-r) - 1px); fill: none; stroke: var(--sd-acc); stroke-width: 2; }
.sd-dash { stroke-dasharray: 1.6 1.4; opacity: 0.5; animation: sd-march var(--sd-speed) linear infinite; }
.sd-lead { stroke-dasharray: 14 86; stroke-linecap: round; opacity: 0.85; animation: sd-lead var(--sd-speed) linear infinite; }
.sd:hover .sd-dash { opacity: 0.85; }

/* the pen keeps writing its line */
.sd-icon { width: 48px; height: 48px; }
.sd-ink { stroke-dasharray: 10; animation: sd-write 8s ease-in-out infinite; }

.sd--nudge::after {
  content: ''; position: absolute; top: 12px; inset-inline-end: 12px; width: 9px; height: 9px; border-radius: 50%;
  background: var(--sd-acc); box-shadow: 0 0 0 3px var(--card-bg);
}

.sd--sm { --sd-r: 14px; width: 84px; height: 52px; padding: 0; margin-top: 10px; }
.sd--sm .sd-icon { width: 24px; height: 24px; }
.sd--sm .sd-halo { inset: -8px; border-radius: calc(var(--sd-r) + 8px); }

@keyframes sd-march { to { stroke-dashoffset: -100; } }
@keyframes sd-lead { from { stroke-dashoffset: 0; } to { stroke-dashoffset: 100; } }
@keyframes sd-breath { 0%, 100% { transform: scale(0.97); } 50% { transform: scale(1.03); } }
@keyframes sd-write {
  0% { stroke-dashoffset: 10; }
  45%, 75% { stroke-dashoffset: 0; }
  100% { stroke-dashoffset: -10; }
}

@media (prefers-reduced-motion: reduce) {
  .sd-halo, .sd-dash, .sd-lead, .sd-ink { animation: none; }
  .sd-lead { display: none; }
  .sd-ink { stroke-dasharray: none; }
}
</style>
