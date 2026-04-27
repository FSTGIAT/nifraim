<template>
  <div class="cg-grid">
    <button
      v-for="card in cards"
      :key="card.id"
      class="cg-card"
      :style="{ '--cg-grad-start': card.gradient[0], '--cg-grad-end': card.gradient[1] }"
      @click="$emit('open', card.id)"
    >
      <div class="cg-icon" v-html="card.icon"></div>

      <div class="cg-title-block">
        <h3 class="cg-title">{{ card.title }}</h3>
        <p class="cg-stat ltr-number">{{ card.stat || '—' }}</p>
      </div>

      <!-- Mini chart inside card -->
      <div class="cg-mini">
        <component
          v-if="card.mini"
          :is="card.mini.type"
          :series="card.mini.series"
          :options="card.mini.options"
          :height="card.mini.height || 70"
        />
      </div>

      <div class="cg-cta">
        <span>{{ card.cta || 'פתח' }}</span>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
      </div>
    </button>
  </div>
</template>

<script setup>
defineProps({ cards: { type: Array, required: true } })
defineEmits(['open'])
</script>

<style scoped>
.cg-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
.cg-card {
  position: relative;
  background: linear-gradient(135deg, var(--cg-grad-start) 0%, var(--cg-grad-end) 100%);
  border: 1px solid rgba(255, 255, 255, 0.55);
  border-radius: 18px;
  padding: 18px 20px 14px;
  cursor: pointer;
  text-align: right;
  font-family: 'Heebo', sans-serif;
  color: #2D2522;
  transition: all .2s var(--transition);
  overflow: hidden;
  display: flex; flex-direction: column;
  min-height: 200px;
  box-shadow: 0 12px 28px -16px rgba(232, 102, 10, 0.4);
}
.cg-card::before {
  content: ''; position: absolute; inset: -40% -10% auto auto; width: 70%; aspect-ratio: 1;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.5), transparent 60%);
  filter: blur(28px); opacity: 0.7;
  pointer-events: none;
}
.cg-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 20px 36px -16px rgba(232, 102, 10, 0.55);
  border-color: rgba(255, 255, 255, 0.85);
}
.cg-card:hover .cg-cta { background: rgba(45, 37, 34, 0.95); color: #FFF8F0; }
.cg-card:hover .cg-mini { opacity: 1; }
.cg-card:focus-visible { outline: 3px solid rgba(45, 37, 34, 0.4); outline-offset: 2px; }

.cg-icon {
  width: 36px; height: 36px; border-radius: 10px;
  background: rgba(255, 255, 255, 0.55);
  color: #5C2400;
  display: inline-flex; align-items: center; justify-content: center;
  margin-bottom: 12px; position: relative;
}
.cg-icon :deep(svg) { width: 20px; height: 20px; }

.cg-title-block { position: relative; }
.cg-title {
  font-size: 17px; font-weight: 800; color: #2D2522;
  letter-spacing: -0.3px; line-height: 1.2;
  margin-bottom: 4px;
}
.cg-stat {
  font-size: 12.5px; font-weight: 700; color: rgba(45, 37, 34, 0.78);
  letter-spacing: 0.2px;
}

.cg-mini {
  margin-top: auto; margin-bottom: 4px;
  opacity: 0.85;
  transition: opacity .2s var(--transition);
  position: relative;
}

.cg-cta {
  display: inline-flex; align-items: center; gap: 6px;
  background: rgba(45, 37, 34, 0.85);
  color: #fff;
  padding: 7px 12px;
  border-radius: 9px;
  font-size: 12px; font-weight: 700;
  align-self: flex-start;
  transition: all .15s var(--transition);
  position: relative;
}

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

@media (max-width: 1100px) { .cg-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px)  { .cg-grid { grid-template-columns: 1fr; } }
</style>
