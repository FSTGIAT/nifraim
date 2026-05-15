<template>
  <div v-if="ready" class="stock-ticker" aria-label="ביצועי קופות גמל" aria-live="off">
    <div class="ticker-track" :style="{ animationDuration: durationSec + 's' }">
      <button
        v-for="(t, i) in repeated"
        :key="`${t.id}-${i}`"
        type="button"
        class="ticker-chip"
        :class="directionClass(t.month)"
        :title="`${t.label} — לחץ לפרטים`"
        @click="onChipClick(t)"
      >
        <span class="ticker-bar" aria-hidden="true"></span>
        <span class="ticker-label">{{ t.label }}</span>
        <span class="ticker-pct ltr-number">{{ formatPct(t.month) }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useFundTickerStore } from '../../stores/fundTicker.js'

const emit = defineEmits(['track-click'])
const store = useFundTickerStore()

function onChipClick(track) {
  if (!track?.id) return
  emit('track-click', track.id)
}

onMounted(() => {
  if (!store.loaded) store.fetch()
})

// Only render after the first fetch resolves AND we have at least one track
// with a numeric value — otherwise the strip is a 32px empty band.
const ready = computed(() =>
  store.loaded && store.tracks.some((t) => t.month !== null && t.month !== undefined),
)

// Duplicate the list so the linear `0 → -50%` keyframe loops seamlessly:
// when the first copy scrolls off-screen, the second copy is already filling in.
const repeated = computed(() => {
  const real = store.tracks.filter((t) => t.month !== null && t.month !== undefined)
  return [...real, ...real]
})

// Scroll speed: ~5s per chip feels right for reading (Nasdaq is similar).
// We tie the duration to the number of chips so adding tracks doesn't speed up the strip.
const durationSec = computed(() => Math.max(20, repeated.value.length * 2.5))

function formatPct(v) {
  if (v === null || v === undefined) return '—'
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}%`
}
function directionClass(v) {
  if (v === null || v === undefined) return 'ticker-chip--flat'
  if (v < 0) return 'ticker-chip--down'
  if (v > 0) return 'ticker-chip--up'
  return 'ticker-chip--flat'
}
</script>

<style scoped>
.stock-ticker {
  position: sticky;
  top: 0;
  z-index: 101; /* above WorkspaceHeader's 100 */
  height: 32px;
  overflow: hidden;
  background: #1e293b; /* slate-800 — keeps the Nasdaq dark-strip feel */
  border-bottom: 1px solid rgba(245, 240, 235, 0.08);
  /* Lock direction LTR so the keyframe translate behaves the same regardless
     of the parent's RTL flow; chip content itself stays RTL (see .ticker-chip). */
  direction: ltr;
}

.ticker-track {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 100%;
  padding-inline-start: 24px;
  width: max-content;
  animation: ticker-scroll linear infinite;
  will-change: transform;
}
.ticker-track:hover {
  animation-play-state: paused;
}

@keyframes ticker-scroll {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}

.ticker-chip {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 4px 12px 4px 10px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 600;
  color: inherit;
  text-decoration: none;
  white-space: nowrap;
  flex-shrink: 0;
  direction: rtl;
  cursor: pointer;
  transition: background 0.15s ease, transform 0.15s ease, border-color 0.15s ease;
}
.ticker-chip:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.14);
}
.ticker-chip:focus-visible {
  outline: none;
  border-color: rgba(245, 124, 0, 0.6);
  background: rgba(255, 255, 255, 0.10);
}
.ticker-chip:active {
  transform: scale(0.98);
}

.ticker-bar {
  width: 3px;
  height: 16px;
  border-radius: 2px;
  flex-shrink: 0;
}
.ticker-chip--down .ticker-bar { background: #ef4444; }
.ticker-chip--up   .ticker-bar { background: #22c55e; }
.ticker-chip--flat .ticker-bar { background: #64748b; }

.ticker-label {
  color: #e2e8f0;
}

.ticker-pct {
  font-weight: 700;
}
.ticker-chip--down .ticker-pct { color: #f87171; }
.ticker-chip--up   .ticker-pct { color: #4ade80; }
.ticker-chip--flat .ticker-pct { color: #94a3b8; }

@media (max-width: 720px) {
  .stock-ticker { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .ticker-track { animation: none; }
}
</style>
