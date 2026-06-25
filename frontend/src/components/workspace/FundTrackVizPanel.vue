<template>
  <Teleport to="body">
    <Transition name="ft-viz">
      <div
        v-if="open"
        class="ft-viz-overlay"
        role="dialog"
        aria-modal="true"
        :aria-label="viz?.title || 'פרטי קופה'"
        @click.self="close"
      >
        <div class="ft-viz-card">
          <header class="ft-viz-head">
            <div class="ft-viz-head-left">
              <span class="ft-viz-badge" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="12" y1="20" x2="12" y2="10"/>
                  <line x1="18" y1="20" x2="18" y2="4"/>
                  <line x1="6" y1="20" x2="6" y2="16"/>
                </svg>
              </span>
              <div class="ft-viz-titles">
                <span class="ft-viz-title">{{ viz?.title || 'פרטי קופה' }}</span>
                <span v-if="viz?.period_label" class="ft-viz-sub">תקופה · {{ viz.period_label }}</span>
              </div>
            </div>
            <div class="ft-viz-actions">
              <button
                v-if="!loading && viz"
                class="ft-viz-icon-btn"
                type="button"
                title="הצג שוב"
                @click="replay"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="1 4 1 10 7 10"/>
                  <path d="M3.51 15a9 9 0 105.64-11.95L1 10"/>
                </svg>
              </button>
              <button class="ft-viz-icon-btn" type="button" title="סגור" @click="close">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/>
                  <line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
          </header>

          <div class="ft-viz-body">
            <div v-if="loading" class="ft-viz-loading">
              <div class="ft-viz-loader"></div>
              <span>טוען תצוגה…</span>
            </div>
            <div v-if="error" class="ft-viz-error">{{ error }}</div>
            <div ref="mountEl" class="ft-viz-mount" aria-hidden="true"></div>
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

// Module-scope caches so the React+Remotion chunk is fetched once per session.
// Same lifecycle pattern as AiVizPanel — see ai_viz_remotion.md.
let reactStack = null
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

    const restFrames = prefersReducedMotion ? 0 : 108000
    const totalFrames = (prefersReducedMotion ? 1 : stack.VIZ_DURATION_FRAMES) + restFrames

    renderCounter += 1
    const element = stack.createElement(stack.Player, {
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
    console.error('[FundTrackVizPanel] render failed', e)
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
.ft-viz-overlay {
  position: fixed;
  inset: 0;
  z-index: 1010;
  background: rgba(17, 12, 6, 0.55);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  direction: rtl;
  font-family: inherit;
}

.ft-viz-card {
  width: 880px;
  max-width: 95vw;
  max-height: 92vh;
  background: #ffffff;
  border-radius: var(--radius-lg);
  box-shadow: 0 24px 64px rgba(17, 12, 6, 0.35), 0 4px 12px rgba(17, 12, 6, 0.08);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ft-viz-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 20px;
  border-bottom: 1px solid var(--border-subtle);
  background: linear-gradient(180deg, rgba(245, 124, 0, 0.05) 0%, #ffffff 100%);
  flex-shrink: 0;
}
.ft-viz-head-left { display: flex; align-items: center; gap: 10px; min-width: 0; }
.ft-viz-badge {
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
.ft-viz-titles { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.ft-viz-title {
  font-size: 15px;
  font-weight: 800;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ft-viz-sub { font-size: 11px; color: var(--text-muted); font-weight: 600; }

.ft-viz-actions { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
.ft-viz-icon-btn {
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
.ft-viz-icon-btn:hover {
  background: var(--primary-light);
  color: var(--primary-deep);
  border-color: rgba(245, 124, 0, 0.18);
}

.ft-viz-body {
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

.ft-viz-mount {
  width: 100%;
  display: flex;
  justify-content: center;
}

.ft-viz-loading {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--text-muted);
  font-size: 13px;
  padding: 40px;
}
.ft-viz-loader {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid var(--primary-light);
  border-top-color: var(--primary);
  animation: ft-viz-spin 0.8s linear infinite;
}
@keyframes ft-viz-spin { to { transform: rotate(360deg); } }

.ft-viz-error {
  padding: 14px;
  color: #C23934;
  background: rgba(234, 0, 30, 0.06);
  border: 1px solid rgba(234, 0, 30, 0.2);
  border-radius: var(--radius-md);
  font-size: 13px;
  text-align: center;
}

.ft-viz-enter-active { transition: opacity 0.28s var(--transition); }
.ft-viz-leave-active { transition: opacity 0.22s var(--transition); }
.ft-viz-enter-active .ft-viz-card,
.ft-viz-leave-active .ft-viz-card {
  transition: transform 0.28s var(--transition), opacity 0.28s var(--transition);
}
.ft-viz-enter-from,
.ft-viz-leave-to { opacity: 0; }
.ft-viz-enter-from .ft-viz-card,
.ft-viz-leave-to .ft-viz-card {
  opacity: 0;
  transform: scale(0.94) translateY(12px);
}

@media (max-width: 860px) {
  .ft-viz-overlay { padding: 12px; }
  .ft-viz-body { padding: 14px; }
}

@media (prefers-reduced-motion: reduce) {
  .ft-viz-enter-active,
  .ft-viz-leave-active,
  .ft-viz-enter-active .ft-viz-card,
  .ft-viz-leave-active .ft-viz-card { transition-duration: 0.1s; }
  .ft-viz-enter-from .ft-viz-card,
  .ft-viz-leave-to .ft-viz-card { transform: none; }
  .ft-viz-loader { animation: none; }
}
</style>
