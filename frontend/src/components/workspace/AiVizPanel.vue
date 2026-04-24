<template>
  <Teleport to="body">
    <Transition name="ai-viz">
      <aside
        v-if="open && viz"
        class="ai-viz"
        role="complementary"
        :aria-label="viz.title || 'תצוגה חזותית'"
      >
        <header class="ai-viz-head">
          <div class="ai-viz-head-left">
            <span class="ai-viz-badge" aria-hidden="true">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
            </span>
            <div class="ai-viz-titles">
              <span class="ai-viz-title">{{ viz.title || 'תצוגה חזותית' }}</span>
              <span class="ai-viz-sub">Remotion · מופעל חי</span>
            </div>
          </div>
          <div class="ai-viz-actions">
            <button
              v-if="!loading"
              class="ai-viz-icon-btn"
              type="button"
              title="הצג שוב"
              @click="replay"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="1 4 1 10 7 10"/>
                <path d="M3.51 15a9 9 0 105.64-11.95L1 10"/>
              </svg>
            </button>
            <button class="ai-viz-icon-btn" type="button" title="סגור" @click="close">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
        </header>

        <div class="ai-viz-body">
          <div v-if="loading" class="ai-viz-loading">
            <div class="ai-viz-loader"></div>
            <span>טוען תצוגה…</span>
          </div>
          <div v-if="error" class="ai-viz-error">{{ error }}</div>
          <div ref="mountEl" class="ai-viz-mount" aria-hidden="true"></div>
        </div>
      </aside>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  viz: { type: Object, default: null },
})
const emit = defineEmits(['update:open'])

const mountEl = ref(null)
const loading = ref(false)
const error = ref(null)

// These three live at module scope so they persist across Vue re-mounts
// within the same SPA session (i.e. the 150 KB chunk is only fetched once).
let reactStack = null // { createRoot, createElement, Player, componentForViz, sizeForViz, VIZ_DURATION_FRAMES, VIZ_FPS }
let reactRoot = null
let replayCounter = 0 // incremented to force re-mount of the Player

async function ensureReactStack() {
  if (reactStack) return reactStack
  loading.value = true
  try {
    const [rdClient, react, player, remotion] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('@remotion/player'),
      import('../../remotion'),
    ])
    reactStack = {
      createRoot: rdClient.createRoot,
      createElement: react.createElement,
      Player: player.Player,
      componentForViz: remotion.componentForViz,
      sizeForViz: remotion.sizeForViz,
      VIZ_DURATION_FRAMES: remotion.VIZ_DURATION_FRAMES,
      VIZ_FPS: remotion.VIZ_FPS,
    }
    return reactStack
  } catch (e) {
    error.value = 'שגיאה בטעינת נגן ה-Remotion'
    throw e
  } finally {
    loading.value = false
  }
}

async function render() {
  if (!props.viz || !mountEl.value) return
  error.value = null
  try {
    const stack = await ensureReactStack()
    if (!mountEl.value) return // unmounted while awaiting
    if (!reactRoot) reactRoot = stack.createRoot(mountEl.value)

    const Comp = stack.componentForViz(props.viz)
    if (!Comp) {
      error.value = 'סוג תצוגה לא נתמך'
      return
    }
    const size = stack.sizeForViz(props.viz)
    const prefersReducedMotion =
      typeof window !== 'undefined' &&
      window.matchMedia &&
      window.matchMedia('(prefers-reduced-motion: reduce)').matches

    // A new `key` forces the Player to fully remount on each replay.
    const element = stack.createElement(stack.Player, {
      key: `${props.viz.type}-${replayCounter}`,
      component: Comp,
      inputProps: props.viz,
      durationInFrames: prefersReducedMotion ? 1 : stack.VIZ_DURATION_FRAMES,
      fps: stack.VIZ_FPS,
      compositionWidth: size.width,
      compositionHeight: size.height,
      autoPlay: true,
      loop: false,
      controls: false,
      clickToPlay: false,
      doubleClickToFullscreen: false,
      style: { width: '100%', borderRadius: 12, overflow: 'hidden' },
    })
    reactRoot.render(element)
  } catch (e) {
    console.error('[AiVizPanel] render failed', e)
    error.value = error.value || 'שגיאה בהצגת התצוגה'
  }
}

function replay() {
  replayCounter += 1
  render()
}

function close() {
  emit('update:open', false)
}

// Render whenever viz changes (new answer from AI)
watch(() => props.viz, () => {
  if (props.open) render()
})

// Render when the panel opens
watch(() => props.open, (isOpen) => {
  if (isOpen) render()
})

onBeforeUnmount(() => {
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
  }
})
</script>

<style scoped>
.ai-viz {
  position: fixed;
  top: 0;
  bottom: 0;
  inset-inline-start: 0;
  width: 500px;
  max-width: 92vw;
  background: #ffffff;
  border-inline-end: 1px solid var(--border-subtle);
  box-shadow: 18px 0 48px rgba(17, 12, 6, 0.12), 2px 0 6px rgba(17, 12, 6, 0.04);
  z-index: 1003;
  display: flex;
  flex-direction: column;
  font-family: inherit;
}

.ai-viz-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-subtle);
  background: linear-gradient(180deg, rgba(245, 124, 0, 0.05) 0%, #ffffff 100%);
}
.ai-viz-head-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.ai-viz-badge {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 10px;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #ffffff;
  box-shadow: 0 4px 12px rgba(245, 124, 0, 0.32);
  flex-shrink: 0;
}
.ai-viz-titles { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ai-viz-title {
  font-size: 14px;
  font-weight: 800;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-viz-sub { font-size: 11px; color: var(--text-muted); font-weight: 600; }

.ai-viz-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.ai-viz-icon-btn {
  width: 30px;
  height: 30px;
  display: grid;
  place-items: center;
  border-radius: 8px;
  background: transparent;
  color: var(--text-muted);
  border: 1px solid transparent;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.ai-viz-icon-btn:hover {
  background: var(--primary-light);
  color: var(--primary-deep);
  border-color: rgba(245, 124, 0, 0.18);
}

.ai-viz-body {
  flex: 1;
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  background:
    radial-gradient(circle at top right, rgba(245,124,0,0.04), transparent 50%),
    #ffffff;
  min-height: 0;
  overflow: auto;
}

.ai-viz-mount {
  width: 100%;
  display: flex;
  justify-content: center;
}

.ai-viz-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-muted);
  font-size: 13px;
}
.ai-viz-loader {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid var(--primary-light);
  border-top-color: var(--primary);
  animation: ai-viz-spin 0.8s linear infinite;
}
@keyframes ai-viz-spin { to { transform: rotate(360deg); } }

.ai-viz-error {
  padding: 14px;
  color: #8A1111;
  background: rgba(234, 0, 30, 0.06);
  border: 1px solid rgba(234, 0, 30, 0.2);
  border-radius: var(--radius-md);
  font-size: 13px;
  text-align: center;
}

/* Transitions */
.ai-viz-enter-active { transition: transform 0.32s var(--transition), opacity 0.32s var(--transition); }
.ai-viz-leave-active { transition: transform 0.22s var(--transition), opacity 0.22s var(--transition); }
.ai-viz-enter-from,
.ai-viz-leave-to {
  opacity: 0;
  transform: translateX(40px); /* RTL body: slides in from the visual left */
}

/* Responsive: below 860px, the panel becomes a bottom sheet instead */
@media (max-width: 860px) {
  .ai-viz {
    top: auto;
    inset-inline-start: 0;
    inset-inline-end: 0;
    left: 12px;
    right: 12px;
    width: auto;
    max-width: none;
    bottom: 0;
    height: 72vh;
    border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    border-inline-end: none;
    border-top: 1px solid var(--border-subtle);
    box-shadow: 0 -18px 44px rgba(17, 12, 6, 0.16);
  }
  .ai-viz-enter-from,
  .ai-viz-leave-to { transform: translateY(30px); }
}

@media (prefers-reduced-motion: reduce) {
  .ai-viz-enter-active,
  .ai-viz-leave-active { transition-duration: 0.12s; }
  .ai-viz-enter-from,
  .ai-viz-leave-to { transform: none; }
  .ai-viz-loader { animation: none; }
}
</style>
