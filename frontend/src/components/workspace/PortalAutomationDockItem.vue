<template>
  <Motion
    :ref="(el) => (itemEl = el?.$el ?? el)"
    as="button"
    type="button"
    class="dock-item"
    :class="[
      {
        running: isRunning,
        pending: anyRunning && !isRunning,
        unconfigured: !hasCredential,
      },
    ]"
    :disabled="anyRunning && !isRunning && hasCredential"
    :style="{ width: width, height: width }"
    @click="$emit('click')"
    :title="tooltip"
  >
    <Motion
      as="span"
      class="di-inner"
      :style="{ scale: iconSpring, background: brand.color }"
    >
      <span v-if="isRunning" class="di-spinner" aria-hidden="true"></span>
      <svg
        v-else
        width="22" height="22" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round"
        aria-hidden="true"
      >
        <path :d="brand.iconPath"/>
      </svg>
    </Motion>
    <span v-if="!hasCredential" class="di-add" aria-hidden="true">
      <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
        <path d="M5 12h14"/><path d="M12 5v14"/>
      </svg>
    </span>
    <span class="di-label">{{ portalLabel }}</span>
  </Motion>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Motion, useSpring, useTransform } from 'motion-v'

const props = defineProps({
  cred: { type: Object, default: null },          // null when no credential exists
  mouseX: { type: Object, required: true },
  portalLabel: { type: String, required: true },
  isImplemented: { type: Boolean, default: true },
  isRunning: { type: Boolean, default: false },
  anyRunning: { type: Boolean, default: false },
  brand: { type: Object, required: true },
  hasCredential: { type: Boolean, default: false },
})
defineEmits(['click'])

const itemEl = ref(null)

const tooltip = computed(() => {
  if (!props.hasCredential) return `${props.portalLabel} · הוסף פורטל`
  if (props.cred?.username) return `${props.portalLabel} · ${props.cred.username}`
  return props.portalLabel
})

// Distance from cursor → width (40 → 80 → 40), exactly per the reference
const distance = useTransform(props.mouseX, (val) => {
  const bounds = itemEl.value?.getBoundingClientRect?.() ?? { x: 0, width: 0 }
  return val - bounds.x - bounds.width / 2
})

const widthSync = useTransform(distance, [-150, 0, 150], [40, 80, 40])
const width = useSpring(widthSync, { mass: 0.1, stiffness: 150, damping: 12 })

const iconScale = useTransform(width, [40, 80], [1, 1.5])
const iconSpring = useSpring(iconScale, { mass: 0.1, stiffness: 150, damping: 12 })
</script>

<style scoped>
.dock-item {
  position: relative;
  border-radius: 9999px;
  border: none;
  padding: 0;
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-family: inherit;
  transform-origin: bottom center;
  overflow: visible;
}
.dock-item:disabled { cursor: not-allowed; }
.dock-item.disabled .di-inner { opacity: 0.4; filter: grayscale(0.7); }
.dock-item.pending .di-inner { opacity: 0.55; filter: grayscale(0.4); }
.dock-item.unconfigured .di-inner {
  opacity: 0.55;
  filter: saturate(0.85);
}
.dock-item.unconfigured:hover:not(:disabled) .di-inner {
  opacity: 1;
  filter: none;
}

.di-add {
  position: absolute;
  top: -3px;
  inset-inline-end: -3px;
  width: 16px;
  height: 16px;
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  border: 2px solid #fff;
  border-radius: 999px;
  display: grid;
  place-items: center;
  box-shadow: 0 2px 6px rgba(245, 124, 0, 0.4);
}

.di-inner {
  width: 100%;
  height: 100%;
  border-radius: 9999px;
  display: grid;
  place-items: center;
  color: #fff;
  box-shadow:
    0 6px 12px rgba(17, 12, 6, 0.20),
    inset 0 -2px 0 rgba(0, 0, 0, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.22);
  transform-origin: center;
}
.dock-item:hover:not(:disabled) .di-inner {
  box-shadow:
    0 14px 28px rgba(17, 12, 6, 0.26),
    inset 0 -2px 0 rgba(0, 0, 0, 0.18),
    inset 0 1px 0 rgba(255, 255, 255, 0.30);
}

.dock-item.running .di-inner {
  animation: dockPulse 1.4s ease-in-out infinite;
}
@keyframes dockPulse {
  0%, 100% { box-shadow: 0 6px 12px rgba(17,12,6,0.20), inset 0 -2px 0 rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.22), 0 0 0 0 rgba(245, 124, 0, 0.50); }
  50%      { box-shadow: 0 6px 12px rgba(17,12,6,0.20), inset 0 -2px 0 rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.22), 0 0 0 16px rgba(245, 124, 0, 0); }
}

.di-spinner {
  width: 22px;
  height: 22px;
  border: 2.5px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spinDock 0.9s linear infinite;
}
@keyframes spinDock { to { transform: rotate(360deg); } }

.di-label {
  position: absolute;
  bottom: -22px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  font-weight: 700;
  color: var(--text);
  letter-spacing: 0.1px;
  white-space: nowrap;
  opacity: 0;
  transition: opacity 200ms ease, bottom 200ms ease;
  pointer-events: none;
}
.dock-item:hover:not(:disabled) .di-label {
  opacity: 1;
  bottom: -26px;
}

.di-soon {
  position: absolute;
  top: -2px;
  inset-inline-end: -2px;
  background: var(--text-muted);
  color: #fff;
  font-size: 9px;
  font-weight: 800;
  padding: 2px 6px;
  border-radius: 999px;
  letter-spacing: 0.2px;
}
</style>
