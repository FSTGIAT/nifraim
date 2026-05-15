<template>
  <div class="boxes-stage" aria-hidden="true">
    <div class="boxes-grid">
      <div v-for="r in ROWS" :key="`row-${r}`" class="boxes-row">
        <div
          v-for="c in COLS"
          :key="`cell-${r}-${c}`"
          class="boxes-cell"
          @pointerenter="onPointerEnter"
        >
          <svg
            v-if="(r - 1) % 2 === 0 && (c - 1) % 2 === 0"
            class="boxes-plus"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="1.5"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="M12 6v12m6-6H6"/>
          </svg>
        </div>
      </div>
    </div>
    <!-- Radial mask: fades the grid into the bg at edges (mirrors the React reference's slate-900 overlay with mask-image radial-gradient) -->
    <div class="boxes-mask" aria-hidden="true"></div>
  </div>
</template>

<script setup>
const ROWS = 200
const COLS = 160

// Tailwind *-400 swatches — bolder than *-300 so the cell flashes pop
// against the dark slate background.
const HOVER_COLORS = [
  'rgb(56 189 248)',   // sky-400
  'rgb(244 114 182)',  // pink-400
  'rgb(74 222 128)',   // green-400
  'rgb(250 204 21)',   // yellow-400
  'rgb(248 113 113)',  // red-400
  'rgb(192 132 252)',  // purple-400
  'rgb(96 165 250)',   // blue-400
  'rgb(129 140 248)',  // indigo-400
  'rgb(167 139 250)',  // violet-400
]
const pickColor = () => HOVER_COLORS[Math.floor(Math.random() * HOVER_COLORS.length)]

const reduced = typeof window !== 'undefined'
  && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// Web Animations API: instant pop in the picked color, then a 1.5 s
// ease-out fade to transparent. No CSS transition fight, no reactive
// state per cell. Each call creates a fresh animation that supersedes
// any previous one on the same element (replace mode is the default).
function onPointerEnter(e) {
  if (reduced) return
  const el = e.currentTarget
  el.animate(
    [
      { backgroundColor: pickColor(), offset: 0 },
      { backgroundColor: pickColor(), offset: 0.001 },     // hold the pop
      { backgroundColor: 'rgba(0,0,0,0)', offset: 1 },     // fade to transparent
    ],
    { duration: 1500, easing: 'ease-out', fill: 'none' },
  )
}
</script>

<style scoped>
/* Stage = full section overlay. */
.boxes-stage {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  pointer-events: auto;
}

/* Grid positioning mirrors the React reference 1:1:
   - parent: absolute, left:25% / top:-25%, w-full h-full
   - transform: translate(-40%,-60%) skewX(-48deg) skewY(14deg) scale(0.675)
   - transform-origin: default 50% 50% (center). 0 0 origin pushes the whole
     skewed grid off-screen — must stay centered. */
.boxes-grid {
  position: absolute;
  top: -25%;
  left: 25%;
  width: 100%;
  height: 100%;
  display: flex;
  transform:
    translate(-40%, -60%)
    skewX(-48deg)
    skewY(14deg)
    scale(1.3);
}

.boxes-row {
  display: flex;
  flex-direction: column;
  width: 64px;
  flex-shrink: 0; /* required — 100 rows × 64px overflow the section; without this they compress to invisibly thin */
  border-left: 1px solid rgb(51 65 85);
}

.boxes-cell {
  width: 64px;
  height: 32px;
  flex-shrink: 0;
  border-right: 1px solid rgb(51 65 85);
  border-top:   1px solid rgb(51 65 85);
  position: relative;
  background-color: transparent;
  /* No CSS transition — Web Animations API drives the entire flash. */
}

.boxes-plus {
  position: absolute;
  width: 40px;
  height: 24px;
  top: -14px;
  left: -22px;
  color: rgb(51 65 85);
  pointer-events: none;
  stroke-width: 1px;
}

/* Edge fade: slate-900 overlay that's transparent in the center and opaque at edges.
   Pointer events disabled so the cells underneath still receive hover. */
.boxes-mask {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: rgb(15 23 42);
  -webkit-mask-image: radial-gradient(transparent, white);
          mask-image: radial-gradient(transparent, white);
  pointer-events: none;
}

@media (max-width: 720px) {
  .boxes-stage { display: none; }
}
</style>
