<template>
  <div
    class="circle-menu"
    :class="{ 'is-open': isOpen }"
    :style="{ width: containerSize + 'px', height: containerSize + 'px' }"
  >
    <!-- Bloom — soft warm halo that fades in when menu opens -->
    <div class="cm-bloom" aria-hidden="true" />

    <!-- Trigger -->
    <button
      class="cm-trigger"
      :class="{ 'cm-trigger--open': isOpen }"
      :style="{ width: itemSize + 'px', height: itemSize + 'px' }"
      :aria-expanded="isOpen"
      aria-label="תפריט"
      @click="toggle"
    >
      <span class="cm-trigger-inner-highlight" aria-hidden="true" />
      <Transition name="cm-icon" mode="out-in">
        <svg
          v-if="isOpen"
          key="x"
          class="cm-svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.4"
          stroke-linecap="round"
          stroke-linejoin="round"
          v-html="ICONS.x"
        />
        <svg
          v-else
          key="menu"
          class="cm-svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2.4"
          stroke-linecap="round"
          stroke-linejoin="round"
          v-html="ICONS.menu"
        />
      </Transition>
    </button>

    <!-- Orbital items — half-circle arc to the LEFT (so the menu doesn't
         shoot off the right edge of the viewport when anchored in the corner). -->
    <div class="cm-orbit" :class="{ 'cm-orbit--open': isOpen }">
      <button
        v-for="(item, i) in items"
        :key="item.key"
        type="button"
        class="cm-item"
        :class="{ open: isOpen }"
        :style="itemStyle(i)"
        :data-tooltip="item.label"
        @click="onSelect(item)"
      >
        <svg
          class="cm-svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          v-html="ICONS[item.icon] || ICONS.menu"
        />
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  items: { type: Array, required: true }, // [{ key, label, icon }]
  itemSize: { type: Number, default: 42 },
  containerSize: { type: Number, default: 200 },
  triggerSize: { type: Number, default: 52 },
})

const emit = defineEmits(['select'])

const isOpen = ref(false)
function toggle() { isOpen.value = !isOpen.value }
function onSelect(item) {
  emit('select', item.key)
  // Tiny delay so the click visual lands before the menu collapses.
  setTimeout(() => { isOpen.value = false }, 90)
}

// Half-circle arc opening to the LEFT — items sweep from bottom → left → top.
// This keeps every item inside the viewport when the menu lives in the top-right corner.
function pointOnLeftArc(i, n, r) {
  const start = Math.PI / 2     // bottom
  const span = Math.PI          // sweep 180° → ends at top
  const theta = n > 1 ? start + (i / (n - 1)) * span : start
  return { x: r * Math.cos(theta), y: r * Math.sin(theta) }
}

function itemStyle(i) {
  const open = isOpen.value
  const r = props.containerSize / 2 - props.itemSize / 2 - 6
  const { x, y } = pointOnLeftArc(i, props.items.length, r)
  return {
    transform: open
      ? `translate(calc(-50% + ${x}px), calc(-50% + ${y}px)) scale(1)`
      : 'translate(-50%, -50%) scale(0.5)',
    transitionDelay: (i * (open ? 0.025 : 0.04)) + 's',
    opacity: open ? 1 : 0,
    pointerEvents: open ? 'auto' : 'none',
    width: props.itemSize + 'px',
    height: props.itemSize + 'px',
  }
}

// Inline-SVG path content — Lucide-style strokes, currentColor for theme switching.
const ICONS = {
  menu:     '<line x1="3" y1="6"  x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>',
  x:        '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
  logout:   '<path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/>',
  search:   '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
  user:     '<path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  home:     '<path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
  help:     '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 015.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
}
</script>

<style scoped>
/* ───── Container ───── */
.circle-menu {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Heebo', sans-serif;
  /* Container itself stays invisible; the trigger sits at its center,
     items orbit out from there. */
}

/* ───── Bloom — warm glow that fades in when the menu opens ───── */
.cm-bloom {
  position: absolute;
  inset: -10%;
  border-radius: 50%;
  background:
    radial-gradient(circle at center,
      rgba(232, 114, 10, 0.18) 0%,
      rgba(232, 114, 10, 0.06) 40%,
      transparent 70%);
  opacity: 0;
  transform: scale(0.7);
  transition: opacity 0.45s ease, transform 0.45s cubic-bezier(0.16, 1, 0.3, 1);
  pointer-events: none;
  z-index: 0;
}
.circle-menu.is-open .cm-bloom { opacity: 1; transform: scale(1); }

/* ───── Trigger ───── */
.cm-trigger {
  position: relative;
  z-index: 3;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.18);
  border-radius: 50%;
  cursor: pointer;
  color: #FFFFFF;
  background:
    radial-gradient(circle at 30% 25%, rgba(255, 255, 255, 0.25), transparent 55%),
    linear-gradient(140deg, #FF9800 0%, #F57C00 38%, #E8720A 65%, #E65100 100%);
  box-shadow:
    0 8px 24px rgba(232, 114, 10, 0.38),
    0 2px 6px rgba(45, 37, 34, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.35),
    inset 0 -8px 12px rgba(120, 50, 0, 0.25);
  transition:
    transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1),
    background 0.3s ease,
    box-shadow 0.3s ease;
  isolation: isolate;
}
.cm-trigger:hover { transform: scale(1.06) rotate(-5deg); }
.cm-trigger:active { transform: scale(0.94); }

/* Inner glossy highlight — gives the orb a jewel-like sheen */
.cm-trigger-inner-highlight {
  position: absolute;
  top: 8%;
  left: 18%;
  width: 38%;
  height: 28%;
  border-radius: 50%;
  background: radial-gradient(ellipse, rgba(255, 255, 255, 0.55), transparent 70%);
  pointer-events: none;
  z-index: 1;
  filter: blur(0.5px);
}

/* Soft idle attention pulse — only when closed */
.cm-trigger:not(.cm-trigger--open)::before {
  content: '';
  position: absolute;
  inset: -8px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(232, 114, 10, 0.5) 0%, transparent 65%);
  z-index: -1;
  animation: cm-pulse 2.6s ease-in-out infinite;
  pointer-events: none;
}
@keyframes cm-pulse {
  0%, 100% { transform: scale(0.95); opacity: 0.55; }
  50%      { transform: scale(1.18); opacity: 0.85; }
}

/* Open state — orb cools to slate, gains an amber ring */
.cm-trigger--open {
  background:
    radial-gradient(circle at 30% 25%, rgba(255, 255, 255, 0.06), transparent 55%),
    linear-gradient(140deg, #3A3330 0%, #2D2522 100%);
  color: #FFE2C2;
  box-shadow:
    0 0 0 3px rgba(232, 114, 10, 0.18),
    0 0 0 1px rgba(232, 114, 10, 0.6),
    0 10px 28px rgba(45, 37, 34, 0.42),
    inset 0 1px 0 rgba(255, 255, 255, 0.06);
  border-color: rgba(232, 114, 10, 0.4);
}

/* Icon swap transition — fade + slight blur */
.cm-svg { width: 60%; height: 60%; }
.cm-icon-enter-active,
.cm-icon-leave-active { transition: opacity 0.2s ease, filter 0.2s ease, transform 0.2s ease; }
.cm-icon-enter-from   { opacity: 0; filter: blur(6px); transform: rotate(-45deg); }
.cm-icon-leave-to     { opacity: 0; filter: blur(6px); transform: rotate(45deg); }

/* ───── Orbit ───── */
.cm-orbit {
  position: absolute;
  inset: 0;
  z-index: 2;
  pointer-events: none;
}
.cm-orbit--open { pointer-events: auto; }

/* ───── Item ───── */
.cm-item {
  position: absolute;
  top: 50%;
  left: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(232, 114, 10, 0.18);
  border-radius: 50%;
  color: #2D2522;
  background: linear-gradient(155deg, #FFFFFF 0%, #FBF4ED 100%);
  cursor: pointer;
  box-shadow:
    0 6px 18px rgba(45, 37, 34, 0.10),
    0 1px 2px rgba(45, 37, 34, 0.06),
    inset 0 1px 0 rgba(255, 255, 255, 0.9);
  transition:
    transform 0.55s cubic-bezier(0.22, 1.4, 0.36, 1),
    opacity 0.35s ease,
    color 0.18s ease,
    background 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
  will-change: transform, opacity;
}
.cm-item:hover {
  background: linear-gradient(140deg, #FF9800 0%, #E8720A 100%);
  border-color: rgba(232, 114, 10, 0.65);
  color: #FFFFFF;
  /* Layer hover transform AFTER the orbit translate by stacking transforms in JS */
  box-shadow:
    0 12px 28px rgba(232, 114, 10, 0.40),
    0 2px 6px rgba(232, 114, 10, 0.20),
    inset 0 1px 0 rgba(255, 255, 255, 0.25);
}
.cm-item:active { filter: brightness(0.96); }

/* Tooltip — sits BELOW the item with a small caret. Heebo type, slate slab. */
.cm-item::after {
  content: attr(data-tooltip);
  position: absolute;
  top: calc(100% + 10px);
  left: 50%;
  padding: 5px 10px;
  background: #2D2522;
  color: #F5F0EB;
  font: 600 11px/1.4 'Heebo', sans-serif;
  letter-spacing: 0.02em;
  border-radius: 6px;
  white-space: nowrap;
  pointer-events: none;
  opacity: 0;
  transform: translate(-50%, -4px);
  transition: opacity 0.2s ease, transform 0.2s ease;
  box-shadow: 0 6px 16px rgba(45, 37, 34, 0.25);
}
.cm-item::before {
  content: '';
  position: absolute;
  top: calc(100% + 4px);
  left: 50%;
  width: 0; height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-bottom: 6px solid #2D2522;
  transform: translateX(-50%);
  opacity: 0;
  transition: opacity 0.2s ease;
  pointer-events: none;
}
.cm-item:hover::after  { opacity: 1; transform: translate(-50%, 0); }
.cm-item:hover::before { opacity: 1; }

@media (max-width: 720px) {
  /* On phones the orbit gets cramped — hide the items, keep just the trigger. */
  .cm-orbit { display: none; }
  .cm-bloom { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .cm-trigger:not(.cm-trigger--open)::before { animation: none; }
  .cm-item, .cm-trigger, .cm-bloom { transition-duration: 0.15s; }
}
</style>
