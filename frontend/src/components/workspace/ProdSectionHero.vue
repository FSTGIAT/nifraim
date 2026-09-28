<template>
  <!-- One hero for every Production sub-screen (השוואת קבצים / היקפים /
       היסטוריה): kicker chip, two-colour Heebo title, one short line, optional
       actions, and the section's own Remotion loop on the far side. Same look
       as the Production empty-state hero. -->
  <header class="psh">
    <div class="psh-copy">
      <span class="psh-kicker">{{ kicker }}</span>
      <h2 class="psh-title">{{ title }} <span class="psh-acc">{{ accent }}</span></h2>
      <p v-if="line" class="psh-line">{{ line }}</p>
      <div v-if="$slots.default" class="psh-actions"><slot /></div>
    </div>
    <TabHeroLoop :scene="scene" flow="ltr" class="psh-art" />
  </header>
</template>

<script setup>
import TabHeroLoop from './TabHeroLoop.vue'

defineProps({
  kicker: { type: String, required: true },
  title: { type: String, required: true },
  accent: { type: String, required: true },
  line: { type: String, default: '' },
  scene: { type: String, required: true },
})
</script>

<style scoped>
.psh {
  position: relative; overflow: hidden;
  display: flex; align-items: center; min-height: 190px;
  padding: 24px 28px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
}
.psh::before {
  content: ''; position: absolute; inset-inline-end: -6%; top: -60%; width: 46%; height: 220%;
  background: radial-gradient(circle, var(--tab-production-wash), transparent 70%);
  pointer-events: none;
}
.psh-copy { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 8px; max-width: 58%; }
.psh-kicker {
  align-self: flex-start; padding: 4px 11px; border-radius: 999px;
  font-size: 11.5px; font-weight: 800;
  background: var(--tab-production-wash); color: var(--tab-production);
}
.psh-title {
  margin: 2px 0 0;
  font-size: clamp(26px, 3vw, 38px); font-weight: 900; letter-spacing: -0.03em; line-height: 1.08;
  color: var(--text-primary, #181818);
}
.psh-acc { color: var(--tab-production); }
.psh-line { margin: 0; font-size: 15px; line-height: 1.6; color: var(--text-secondary, #5C5A58); }
.psh-actions { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-top: 6px; }
.psh-art {
  position: absolute; inset-inline-end: 6px; top: 50%; transform: translateY(-50%);
  width: min(320px, 40%); aspect-ratio: 420 / 300; pointer-events: none;
}
@media (max-width: 640px) {
  .psh { min-height: 0; padding: 20px; }
  .psh-copy { max-width: none; }
  .psh-art { display: none; }
}
</style>
