<template>
  <ul class="ec-grid" :style="gridStyle" @mouseleave="onLeaveAll">
    <li
      v-for="(item, idx) in items"
      :key="item.id"
      class="ec-card"
      :class="{ active: activeIndex === idx }"
      :data-active="activeIndex === idx"
      :style="{ '--ec-grad-start': item.gradient[0], '--ec-grad-end': item.gradient[1] }"
      tabindex="0"
      @mouseenter="setActive(idx)"
      @focus="setActive(idx)"
      @click="onClick(idx)"
    >
      <div class="ec-bg"></div>
      <div class="ec-veil"></div>

      <article class="ec-content">
        <!-- Vertical title (only when collapsed, on desktop) -->
        <h3 class="ec-spine-title" v-if="isDesktop">{{ item.title }}</h3>

        <div class="ec-icon" v-html="item.icon"></div>

        <h3 class="ec-title">{{ item.title }}</h3>

        <p class="ec-stat" v-if="item.stat">{{ item.stat }}</p>
        <p class="ec-desc">{{ item.description }}</p>

        <span class="ec-cta">
          {{ item.cta || 'פתח' }}
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <path d="M19 12H5M12 19l-7-7 7-7"/>
          </svg>
        </span>
      </article>
    </li>
  </ul>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'

const props = defineProps({
  items: { type: Array, required: true },
  defaultActiveIndex: { type: Number, default: 0 },
})
const emit = defineEmits(['select'])

const activeIndex = ref(props.defaultActiveIndex)
const isDesktop = ref(true)

function onResize() {
  isDesktop.value = window.innerWidth >= 768
}
onMounted(() => {
  onResize()
  window.addEventListener('resize', onResize)
})
onUnmounted(() => window.removeEventListener('resize', onResize))

const gridStyle = computed(() => {
  if (activeIndex.value === null) return {}
  if (isDesktop.value) {
    const cols = props.items.map((_, i) => (i === activeIndex.value ? '5fr' : '1fr')).join(' ')
    return { gridTemplateColumns: cols, gridTemplateRows: '1fr' }
  } else {
    const rows = props.items.map((_, i) => (i === activeIndex.value ? '5fr' : '1fr')).join(' ')
    return { gridTemplateRows: rows, gridTemplateColumns: '1fr' }
  }
})

function setActive(idx) { activeIndex.value = idx }
function onLeaveAll() { /* keep last active — original behavior */ }

function onClick(idx) {
  setActive(idx)
  emit('select', props.items[idx])
}
</script>

<style scoped>
.ec-grid {
  list-style: none; padding: 0; margin: 0;
  display: grid;
  width: 100%;
  height: 460px;
  gap: 10px;
  transition: grid-template-columns .55s cubic-bezier(0.16, 1, 0.3, 1),
              grid-template-rows .55s cubic-bezier(0.16, 1, 0.3, 1);
}
@media (max-width: 767px) {
  .ec-grid { height: 600px; }
}

.ec-card {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  cursor: pointer;
  min-width: 0; min-height: 0;
  outline: none;
  background: var(--ec-grad-start, #2D2522);
  box-shadow: 0 12px 32px -16px rgba(45, 37, 34, 0.4);
  transition: box-shadow .35s var(--transition);
}
.ec-card:focus-visible { box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.6); }
.ec-card.active { box-shadow: 0 24px 48px -16px rgba(232, 102, 10, 0.45); }
@media (min-width: 768px) {
  .ec-card { min-width: 80px; }
}

/* gradient background per card */
.ec-bg {
  position: absolute; inset: 0;
  background: linear-gradient(140deg, var(--ec-grad-start) 0%, var(--ec-grad-end) 100%);
  transition: transform .5s var(--transition), filter .5s var(--transition);
  transform: scale(1.05);
  filter: saturate(0.65) brightness(0.85);
}
.ec-card.active .ec-bg { transform: scale(1); filter: saturate(1) brightness(1); }

/* dot pattern overlay for visual texture */
.ec-bg::after {
  content: ''; position: absolute; inset: 0;
  background-image: radial-gradient(circle at 1px 1px, rgba(255,255,255,0.18) 1px, transparent 0);
  background-size: 22px 22px;
  opacity: 0.35;
  mix-blend-mode: overlay;
}

/* gradient veil for legibility */
.ec-veil {
  position: absolute; inset: 0;
  background: linear-gradient(180deg, transparent 0%, rgba(0,0,0,0.4) 70%, rgba(0,0,0,0.7) 100%);
  pointer-events: none;
}

/* ─── Content ─── */
.ec-content {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; justify-content: flex-end;
  gap: 8px; padding: 18px;
}

/* spine title — visible only when collapsed (desktop) */
.ec-spine-title {
  display: none;
  position: absolute;
  bottom: 18px; right: 22px;
  transform-origin: right bottom;
  transform: rotate(-90deg) translateY(-50%);
  font-size: 12.5px;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: rgba(255,255,255,0.85);
  white-space: nowrap;
  transition: opacity .2s .1s var(--transition);
}
@media (min-width: 768px) {
  .ec-spine-title { display: block; }
  .ec-card.active .ec-spine-title { opacity: 0; pointer-events: none; transition: opacity .15s var(--transition); }
}

.ec-icon {
  color: rgba(255, 255, 255, 0.95);
  opacity: 0; transform: translateY(8px);
  transition: opacity .35s .15s var(--transition), transform .35s .15s var(--transition);
}
.ec-icon :deep(svg) { width: 28px; height: 28px; }
.ec-card.active .ec-icon { opacity: 1; transform: translateY(0); }

.ec-title {
  color: #fff; font-size: 22px; font-weight: 800; letter-spacing: -0.4px;
  opacity: 0; transform: translateY(8px);
  transition: opacity .35s .22s var(--transition), transform .35s .22s var(--transition);
}
.ec-card.active .ec-title { opacity: 1; transform: translateY(0); }

.ec-stat {
  font-family: 'Heebo', sans-serif;
  color: #fff; font-size: 14px; font-weight: 700;
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.22);
  padding: 4px 10px; border-radius: 999px;
  align-self: flex-start;
  direction: ltr; unicode-bidi: embed;
  opacity: 0; transform: translateY(6px);
  transition: opacity .35s .29s var(--transition), transform .35s .29s var(--transition);
}
.ec-card.active .ec-stat { opacity: 1; transform: translateY(0); }

.ec-desc {
  color: rgba(255, 255, 255, 0.88); font-size: 13.5px; line-height: 1.55;
  max-width: 360px;
  opacity: 0; transform: translateY(6px);
  transition: opacity .35s .35s var(--transition), transform .35s .35s var(--transition);
}
.ec-card.active .ec-desc { opacity: 1; transform: translateY(0); }

.ec-cta {
  display: inline-flex; align-items: center; gap: 6px;
  margin-top: 6px; padding: 9px 14px;
  background: rgba(255,255,255,0.16);
  border: 1px solid rgba(255,255,255,0.28);
  color: #fff; font-size: 12.5px; font-weight: 700;
  border-radius: 10px;
  align-self: flex-start;
  backdrop-filter: blur(6px);
  opacity: 0; transform: translateY(6px);
  transition: opacity .35s .42s var(--transition), transform .35s .42s var(--transition), background .15s var(--transition);
}
.ec-card.active .ec-cta { opacity: 1; transform: translateY(0); }
.ec-card.active .ec-cta:hover { background: rgba(255,255,255,0.28); }
</style>
