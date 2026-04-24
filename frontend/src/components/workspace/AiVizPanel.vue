<template>
  <Teleport to="body">
    <Transition name="ai-viz">
      <div
        v-if="open && viz"
        class="ai-viz-overlay"
        role="dialog"
        aria-modal="true"
        :aria-label="viz.title || 'תצוגה חזותית'"
        @click.self="close"
      >
        <div class="ai-viz-card">
          <header class="ai-viz-head">
            <div class="ai-viz-head-left">
              <span class="ai-viz-badge" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polygon points="5 3 19 12 5 21 5 3"/>
                </svg>
              </span>
              <div class="ai-viz-titles">
                <span class="ai-viz-title">{{ viz.title || 'תצוגה חזותית' }}</span>
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
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, watch, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  viz: { type: Object, default: null },
})
const emit = defineEmits(['update:open'])

const mountEl = ref(null)
const loading = ref(false)
const error = ref(null)

// Module-scope caches so the React+Remotion chunk is fetched once per session
let reactStack = null
// reactRoot + currentMountEl track which DOM element the root was bound to so
// we can detect and replace a stale root when the modal is reopened.
let reactRoot = null
let currentMountEl = null
let replayCounter = 0
let renderCounter = 0

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
    if (!mountEl.value) return
    // If the root exists but points to a detached (stale) DOM node — from a
    // previous modal open/close cycle — drop it and create a fresh one bound
    // to the current mount element.
    if (reactRoot && currentMountEl !== mountEl.value) {
      try { reactRoot.unmount() } catch { /* ignore */ }
      reactRoot = null
    }
    if (!reactRoot) {
      reactRoot = stack.createRoot(mountEl.value)
      currentMountEl = mountEl.value
    }

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

    // 3-second animation + ~60-minute still-frame tail. All interpolate()
    // calls in the compositions clamp on both sides, so every frame after the
    // intro renders the final state. No loop — the user sees the animation
    // play once and then the final frame persists.
    const restFrames = prefersReducedMotion ? 0 : 108000 // ~1h at 30fps
    const totalFrames = (prefersReducedMotion ? 1 : stack.VIZ_DURATION_FRAMES) + restFrames

    renderCounter += 1
    const element = stack.createElement(stack.Player, {
      // Fresh key on every render forces the Player to fully remount, which
      // ensures the new viz plays from frame 0 and releases any state held
      // on the previous composition.
      key: `${props.viz.type}-${renderCounter}-${replayCounter}`,
      component: Comp,
      inputProps: props.viz,
      durationInFrames: totalFrames,
      fps: stack.VIZ_FPS,
      compositionWidth: size.width,
      compositionHeight: size.height,
      autoPlay: true,
      loop: false,
      controls: false,
      clickToPlay: false,
      doubleClickToFullscreen: false,
      showPosterWhenUnplayed: false,
      showPosterWhenPaused: false,
      showPosterWhenEnded: false,
      showPosterWhenBuffering: false,
      acknowledgeRemotionLicense: true,
      style: { width: '100%', borderRadius: 12, overflow: 'hidden' },
    })
    reactRoot.render(element)
  } catch (e) {
    console.error('[AiVizPanel] render failed', e)
    if (!error.value) error.value = 'שגיאה בהצגת התצוגה'
  }
}

function replay() {
  replayCounter += 1
  render()
}

function close() {
  emit('update:open', false)
}

function onEscape(e) {
  if (e.key === 'Escape' && props.open) close()
}

watch(() => props.viz, () => {
  if (props.open) nextTick(() => render())
})

watch(() => props.open, (isOpen) => {
  if (isOpen) {
    window.addEventListener('keydown', onEscape)
    nextTick(() => render())
  } else {
    window.removeEventListener('keydown', onEscape)
    // Release the React root now — the <div ref="mountEl"> will be unmounted
    // by Vue's v-if, leaving the root detached. Next open gets a fresh root.
    if (reactRoot) {
      try { reactRoot.unmount() } catch { /* ignore */ }
      reactRoot = null
      currentMountEl = null
    }
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onEscape)
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
  }
})
</script>

<style scoped>
.ai-viz-overlay {
  position: fixed;
  inset: 0;
  z-index: 1010; /* above chat sheet (1005) and its overlay (1004) */
  background: rgba(17, 12, 6, 0.55);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  direction: rtl;
  font-family: inherit;
}

.ai-viz-card {
  width: 820px;
  max-width: 95vw;
  max-height: 92vh;
  background: #ffffff;
  border-radius: var(--radius-lg);
  box-shadow: 0 24px 64px rgba(17, 12, 6, 0.35), 0 4px 12px rgba(17, 12, 6, 0.08);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ai-viz-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-subtle);
  background: linear-gradient(180deg, rgba(245, 124, 0, 0.05) 0%, #ffffff 100%);
  flex-shrink: 0;
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
  font-size: 15px;
  font-weight: 800;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-viz-sub { font-size: 11px; color: var(--text-muted); font-weight: 600; }

.ai-viz-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.ai-viz-icon-btn {
  width: 32px;
  height: 32px;
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
  padding: 20px;
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
  padding: 40px;
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
.ai-viz-enter-active { transition: opacity 0.28s var(--transition); }
.ai-viz-leave-active { transition: opacity 0.22s var(--transition); }
.ai-viz-enter-active .ai-viz-card,
.ai-viz-leave-active .ai-viz-card {
  transition: transform 0.28s var(--transition), opacity 0.28s var(--transition);
}
.ai-viz-enter-from,
.ai-viz-leave-to { opacity: 0; }
.ai-viz-enter-from .ai-viz-card,
.ai-viz-leave-to .ai-viz-card {
  opacity: 0;
  transform: scale(0.94) translateY(12px);
}

@media (max-width: 860px) {
  .ai-viz-overlay { padding: 12px; }
  .ai-viz-body { padding: 14px; }
}

@media (prefers-reduced-motion: reduce) {
  .ai-viz-enter-active,
  .ai-viz-leave-active,
  .ai-viz-enter-active .ai-viz-card,
  .ai-viz-leave-active .ai-viz-card { transition-duration: 0.1s; }
  .ai-viz-enter-from .ai-viz-card,
  .ai-viz-leave-to .ai-viz-card { transform: none; }
  .ai-viz-loader { animation: none; }
}
</style>
