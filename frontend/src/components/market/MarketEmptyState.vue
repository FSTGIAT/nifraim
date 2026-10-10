<template>
  <div class="mes">
    <!-- An empty view says what's going on, with calm motion art (remotion/market/MarketEmpty) and a way on —
         never a blank area or a "₪0". -->
    <span class="mes-blob mes-blob--a" aria-hidden="true"></span>
    <span class="mes-blob mes-blob--b" aria-hidden="true"></span>
    <div class="mes-art" aria-hidden="true">
      <RemotionLoopIsland component="MarketEmpty" frames-key="MARKET_EMPTY_FRAMES" :width="520" :height="220"
                          :input-props="{ color: '#5B8DD6', tone }">
        <svg viewBox="0 0 520 220" class="mes-static"><rect v-for="(h, i) in [70, 110, 92, 140, 120, 96, 128]" :key="i"
             :x="76 + i * 56" :y="186 - h" width="28" :height="h" rx="14" fill="none" stroke="#5B8DD6" stroke-opacity="0.5" stroke-width="2" /></svg>
      </RemotionLoopIsland>
    </div>
    <h3>{{ title }}</h3>
    <p>{{ text }}</p>
    <div v-if="actions.length" class="mes-actions">
      <button v-for="a in actions" :key="a.view" type="button" @click="$emit('go', a.view)">{{ a.label }}</button>
    </div>
  </div>
</template>

<script setup>
import RemotionLoopIsland from '../workspace/RemotionLoopIsland.vue'

defineProps({
  title: { type: String, required: true },
  text: { type: String, default: '' },
  tone: { type: String, default: 'empty' },   // 'empty' (scan) | 'ok' (check)
  actions: { type: Array, default: () => [] }, // [{ view, label }]
})
defineEmits(['go'])
</script>

<style scoped>
.mes {
  position: relative; overflow: hidden; display: flex; flex-direction: column; align-items: center; gap: 8px; text-align: center;
  padding: 18px 24px 28px; border-radius: 18px; background: #fff; border: 1px solid var(--border-subtle, #E5E5E5);
}
.mes-blob { position: absolute; border-radius: 50%; filter: blur(46px); opacity: 0.5; pointer-events: none; animation: mesBob 12s ease-in-out infinite; }
.mes-blob--a { width: 260px; height: 260px; top: -120px; right: -60px; background: rgba(91, 141, 214, 0.22); }
.mes-blob--b { width: 220px; height: 220px; bottom: -110px; left: -40px; background: rgba(186, 209, 240, 0.35); animation-delay: -6s; }
.mes-art { position: relative; width: min(420px, 100%); }
.mes-art :deep(.rli-mount) { direction: ltr; }
.mes-static { width: 100%; height: auto; }
.mes h3 { position: relative; margin: 0; font-size: 19px; font-weight: 900; letter-spacing: -0.01em; }
.mes p { position: relative; margin: 0; max-width: 560px; font-size: 14px; line-height: 1.6; color: var(--text-secondary, #5C5C5C); }
.mes-actions { position: relative; display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-top: 6px; }
.mes-actions button {
  padding: 8px 16px; border-radius: 10px; border: none; cursor: pointer; font: inherit; font-size: 13.5px; font-weight: 700;
  background: var(--tab-market-ink); color: #fff; box-shadow: 0 6px 14px rgba(94, 99, 32, 0.22); transition: transform 0.2s;
}
.mes-actions button:hover { transform: translateY(-1px); }
.mes-actions button + button { background: var(--tab-market-wash); color: var(--tab-market-ink); box-shadow: none; }
@keyframes mesBob { 50% { transform: translate(-20px, 14px) scale(1.06); } }
@media (prefers-reduced-motion: reduce) { .mes-blob { animation: none; } }
</style>
