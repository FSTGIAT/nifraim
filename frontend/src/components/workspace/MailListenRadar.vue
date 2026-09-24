<template>
  <!-- "The agent is on": the watched senders sit on a ring around the AI core,
       a sweep passes over them, and a sender blinks as the sweep reaches it. -->
  <div class="radar" :class="{ 'radar--fast': scanning }" aria-hidden="true">
    <span class="radar-ring radar-ring--1"></span>
    <span class="radar-ring radar-ring--2"></span>
    <span class="radar-sweep"></span>
    <span class="radar-core">
      <svg viewBox="0 0 24 24" width="28" height="28">
        <path fill="#fff" d="M12 2c.6 4.6 2.4 6.4 7 7-4.6.6-6.4 2.4-7 7-.6-4.6-2.4-6.4-7-7 4.6-.6 6.4-2.4 7-7Z" />
      </svg>
    </span>
    <span
      v-for="(s, i) in dots" :key="s.key" class="radar-dot"
      :style="{ '--a': s.angle + 'deg', '--delay': (s.angle / 360) * 4 + 's' }"
      :title="s.label"
    >{{ s.initial }}</span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  senders: { type: Array, default: () => [] },   // [{ label, address }]
  scanning: { type: Boolean, default: false },
})

const dots = computed(() => {
  const list = props.senders.slice(0, 8)
  const n = Math.max(list.length, 1)
  return list.map((s, i) => {
    const label = s.label || s.address || ''
    return { key: s.address || i, label, initial: (label.trim()[0] || '?').toUpperCase(), angle: Math.round((360 / n) * i - 90) }
  })
})
</script>

<style scoped>
.radar {
  --R: 78px;
  --T: 4s;
  position: relative; width: 200px; height: 200px; flex-shrink: 0;
  display: grid; place-items: center;
}
.radar--fast { --T: 1.2s; }
.radar-ring {
  position: absolute; border-radius: 50%; border: 1.5px dashed color-mix(in srgb, var(--tab-mail) 35%, transparent);
}
.radar-ring--1 { width: calc(var(--R) * 2); height: calc(var(--R) * 2); }
.radar-ring--2 { width: calc(var(--R) * 1.2); height: calc(var(--R) * 1.2); border-style: solid; border-color: var(--tab-mail-wash); }
.radar-sweep {
  position: absolute; width: calc(var(--R) * 2 + 20px); height: calc(var(--R) * 2 + 20px); border-radius: 50%;
  background: conic-gradient(from 0deg, color-mix(in srgb, var(--tab-mail) 28%, transparent), transparent 70deg);
  animation: radar-spin var(--T) linear infinite;
}
.radar-core {
  position: relative; z-index: 2; width: 52px; height: 52px; border-radius: 16px;
  display: grid; place-items: center; background: var(--tab-mail-ink);
  box-shadow: 0 0 0 6px var(--tab-mail-wash), 0 8px 18px color-mix(in srgb, var(--tab-mail) 35%, transparent);
  animation: radar-breathe 2.4s ease-in-out infinite;
}
.radar-dot {
  position: absolute; z-index: 3; width: 30px; height: 30px; border-radius: 50%;
  display: grid; place-items: center; font-size: 12px; font-weight: 800;
  color: var(--tab-mail-ink); background: var(--card-bg); border: 2px solid var(--tab-mail-wash);
  transform: rotate(var(--a)) translate(var(--R)) rotate(calc(-1 * var(--a)));
  animation: radar-ping var(--T) ease-out infinite; animation-delay: var(--delay);
}
@keyframes radar-spin { to { transform: rotate(360deg); } }
@keyframes radar-breathe { 50% { box-shadow: 0 0 0 10px var(--tab-mail-wash), 0 8px 18px color-mix(in srgb, var(--tab-mail) 35%, transparent); } }
@keyframes radar-ping {
  0%, 8% { border-color: var(--tab-mail); box-shadow: 0 0 0 4px var(--tab-mail-wash); }
  30%, 100% { border-color: var(--tab-mail-wash); box-shadow: none; }
}
@media (prefers-reduced-motion: reduce) {
  .radar-sweep, .radar-core, .radar-dot { animation: none; }
}
</style>
