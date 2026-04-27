<template>
  <ul class="bk-grid" :style="gridStyle">
    <!-- eslint-disable-next-line vue/require-v-for-key -->
    <li
      v-for="(book, idx) in books"
      :key="book.id"
      class="bk-card"
      :class="{ active: activeIndex === idx }"
      :style="{ '--bk-grad-start': book.gradient[0], '--bk-grad-end': book.gradient[1] }"
      tabindex="0"
      @mouseenter="setActive(idx)"
      @focus="setActive(idx)"
      @click="onClick(idx)"
    >
      <div class="bk-bg"></div>

      <!-- Spine title visible only when collapsed -->
      <h3 class="bk-spine" v-if="isDesktop">{{ book.title }}</h3>

      <!-- Active book — 2-column stage: reel takes the spotlight, text on the side -->
      <div class="bk-content" v-if="activeIndex === idx">
        <div class="bk-text">
          <div class="bk-icon" v-html="book.icon"></div>
          <h3 class="bk-title">{{ book.title }}</h3>
          <p class="bk-stat ltr-number">{{ book.stat || '—' }}</p>
          <p class="bk-blurb" v-if="book.blurb">{{ book.blurb }}</p>
          <button class="bk-cta" @click.stop="onClick(idx)">
            {{ book.cta || 'פתח' }}
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
              <path d="M19 12H5M12 19l-7-7 7-7"/>
            </svg>
          </button>
        </div>

        <div class="bk-stage">
          <AgencyShelfReel :type="book.id" :width="560" :height="320" />
        </div>
      </div>
    </li>
  </ul>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import AgencyShelfReel from './AgencyShelfReel.vue'

const props = defineProps({
  books: { type: Array, required: true },
  defaultActiveIndex: { type: Number, default: 0 },
})
const emit = defineEmits(['open'])

// Need the loop var inside template (Vue strict mode) — `idx` shadows from v-for
defineOptions({ inheritAttrs: false })

const activeIndex = ref(props.defaultActiveIndex)
const isDesktop = ref(true)

function onResize() { isDesktop.value = window.innerWidth >= 768 }
onMounted(() => { onResize(); window.addEventListener('resize', onResize) })
onUnmounted(() => window.removeEventListener('resize', onResize))

const gridStyle = computed(() => {
  if (activeIndex.value === null) return {}
  if (isDesktop.value) {
    const cols = props.books.map((_, i) => (i === activeIndex.value ? '4fr' : '1fr')).join(' ')
    return { gridTemplateColumns: cols, gridTemplateRows: '1fr' }
  } else {
    const rows = props.books.map((_, i) => (i === activeIndex.value ? '4fr' : '1fr')).join(' ')
    return { gridTemplateRows: rows, gridTemplateColumns: '1fr' }
  }
})

function setActive(idx) { activeIndex.value = idx }
function onClick(idx) {
  setActive(idx)
  emit('open', props.books[idx].id)
}
</script>

<style scoped>
.bk-grid {
  list-style: none; padding: 0; margin: 0;
  display: grid;
  width: 100%;
  height: 460px;
  gap: 10px;
  transition:
    grid-template-columns .55s cubic-bezier(0.16, 1, 0.3, 1),
    grid-template-rows .55s cubic-bezier(0.16, 1, 0.3, 1);
}
@media (max-width: 767px) { .bk-grid { height: 720px; } }

.bk-card {
  position: relative;
  overflow: hidden;
  border-radius: 16px;
  cursor: pointer;
  min-width: 0; min-height: 0;
  outline: none;
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: 0 10px 24px -14px rgba(232, 102, 10, 0.45);
  transition: box-shadow .35s var(--transition);
}
@media (min-width: 768px) { .bk-card { min-width: 64px; } }
.bk-card:focus-visible { box-shadow: 0 0 0 3px rgba(45, 37, 34, 0.4); }
.bk-card.active { box-shadow: 0 22px 44px -16px rgba(232, 102, 10, 0.6); }

.bk-bg {
  position: absolute; inset: 0;
  background: linear-gradient(135deg, var(--bk-grad-start) 0%, var(--bk-grad-end) 100%);
  transition: filter .4s var(--transition);
  filter: saturate(0.85) brightness(0.95);
}
.bk-bg::after {
  content: ''; position: absolute; inset: -50% -10% auto auto; width: 70%; aspect-ratio: 1;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.6), transparent 60%);
  filter: blur(30px); opacity: 0.6;
}
.bk-card.active .bk-bg { filter: saturate(1) brightness(1); }

/* Spine title (collapsed) — DARK on warm orange so it's always readable */
.bk-spine {
  display: none;
  position: absolute;
  bottom: 16px; right: 22px;
  transform-origin: right bottom;
  transform: rotate(-90deg) translateY(-50%);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 1.4px;
  color: #2D2522;
  white-space: nowrap;
  transition: opacity .2s var(--transition);
  text-shadow: 0 1px 0 rgba(255, 255, 255, 0.5);
}
@media (min-width: 768px) {
  .bk-spine { display: block; }
  .bk-card.active .bk-spine { opacity: 0; pointer-events: none; }
}

/* Expanded content — two-column stage layout */
.bk-content {
  position: absolute; inset: 0;
  display: grid;
  grid-template-columns: minmax(180px, 38%) 1fr;
  gap: 16px;
  padding: 22px 24px;
  color: #2D2522;
  align-items: stretch;
}
.bk-text {
  display: flex; flex-direction: column;
  gap: 10px;
  justify-content: flex-start;
}
.bk-icon {
  width: 42px; height: 42px;
  border-radius: 11px;
  background: rgba(255, 255, 255, 0.6);
  color: #5C2400;
  display: inline-flex; align-items: center; justify-content: center;
  opacity: 0; transform: translateY(8px);
  transition: opacity .35s .15s var(--transition), transform .35s .15s var(--transition);
  align-self: flex-start;
}
.bk-icon :deep(svg) { width: 22px; height: 22px; }
.bk-card.active .bk-icon { opacity: 1; transform: translateY(0); }

.bk-title {
  font-size: 22px; font-weight: 800; letter-spacing: -0.4px; line-height: 1.15;
  color: #2D2522;
  opacity: 0; transform: translateY(8px);
  transition: opacity .35s .22s var(--transition), transform .35s .22s var(--transition);
}
.bk-card.active .bk-title { opacity: 1; transform: translateY(0); }

.bk-stat {
  font-size: 13px; font-weight: 700; color: rgba(45, 37, 34, 0.78);
  letter-spacing: 0.2px; line-height: 1.4;
  opacity: 0; transform: translateY(6px);
  transition: opacity .35s .29s var(--transition), transform .35s .29s var(--transition);
}
.bk-card.active .bk-stat { opacity: 1; transform: translateY(0); }

.bk-blurb {
  font-size: 12.5px; color: rgba(45, 37, 34, 0.6); line-height: 1.6;
  opacity: 0; transform: translateY(6px);
  transition: opacity .35s .32s var(--transition), transform .35s .32s var(--transition);
}
.bk-card.active .bk-blurb { opacity: 1; transform: translateY(0); }

.bk-stage {
  position: relative;
  display: block;
  min-width: 0;
  min-height: 220px;
  height: 100%;
  border-radius: 14px;
  background:
    radial-gradient(ellipse at center, rgba(255,255,255,0.5) 0%, transparent 70%),
    rgba(255, 255, 255, 0.24);
  border: 1px solid rgba(255, 255, 255, 0.55);
  overflow: hidden;
  opacity: 0; transform: translateY(6px) scale(0.98);
  transition: opacity .4s .35s var(--transition), transform .4s .35s var(--transition);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.25);
}
.bk-card.active .bk-stage { opacity: 1; transform: translateY(0) scale(1); }
.bk-stage :deep(.shelf-reel-mount) {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}

.bk-cta {
  display: inline-flex; align-items: center; gap: 6px;
  background: rgba(45, 37, 34, 0.92);
  color: #FFF8F0;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px; font-weight: 700;
  align-self: flex-start;
  border: none;
  cursor: pointer;
  margin-top: auto;
  font-family: inherit;
  opacity: 0; transform: translateY(6px);
  transition:
    opacity .35s .42s var(--transition),
    transform .35s .42s var(--transition),
    background .15s var(--transition);
}
.bk-card.active .bk-cta { opacity: 1; transform: translateY(0); }
.bk-card.active .bk-cta:hover { background: #1a1513; }

@media (max-width: 1100px) {
  .bk-content { grid-template-columns: 1fr; grid-template-rows: auto 1fr; }
  .bk-stage { min-height: 180px; }
}
</style>
