<template>
  <!-- Nifra Agent — alive, not an icon: the ThinkingOrb in its "connecting"
       state (a constellation wiring itself — the agent connecting the book),
       in a breathing glass ring with a soft teal glow. Badge = what waits.
       Click → the agent's panel grows out of it. -->
  <button
    v-if="store.visible"
    ref="btnEl"
    type="button"
    class="nai"
    :class="['nai--' + size, { 'nai--attn': attn }]"
    :title="title"
    :aria-label="title"
    @click="$emit('open', btnEl)"
  >
    <span class="nai-ring">
      <span class="nai-glow" aria-hidden="true"></span>
      <!-- Drawn at its real size in the corner (the 32px preset in a 54px ring), not a 64px orb scaled down —
           the scale didn't always take and the orb spilled over the next circle (user 2026-10-10). -->
      <span class="nai-orb-clip">
        <ThinkingOrbIsland class="nai-orb" :state="state" :size="size === 'big' ? 64 : 32" color="#0E8C8A"
                           :dot-size="size === 'big' ? 1.25 : 1.6" :dots="1.1" />
      </span>
      <b v-if="store.todoCount" class="nai-badge ltr-number">{{ store.todoCount }}</b>
    </span>
    <span v-if="size === 'big'" class="nai-cap" dir="ltr">Nifra <b>Agent</b></span>
  </button>
</template>

<script setup>
import { computed, ref, watch, onMounted } from 'vue'
import { useOfficeAgentStore } from '../../stores/officeAgent.js'
import ThinkingOrbIsland from './ThinkingOrbIsland.vue'

defineProps({ size: { type: String, default: 'big' } }) // big (home, under the clock) | small (corner)
defineEmits(['open'])
const store = useOfficeAgentStore()
const btnEl = ref(null)
const state = computed(() => (store.busy ? 'composing' : 'connecting'))
const title = computed(() => (store.todoCount ? `Nifra Agent · ${store.todoCount} דברים מחכים לך` : 'Nifra Agent'))
// a call summary is ready → a short attention pulse (ring + badge bump)
const attn = ref(false)
watch(() => store.attention, () => {
  attn.value = false
  requestAnimationFrame(() => { attn.value = true; setTimeout(() => { attn.value = false }, 1600) })
})
// prefetch the written brief so opening the panel starts writing instantly
onMounted(() => { if (!store.narration) store.narrate() })
</script>

<style scoped>
.nai {
  display: inline-flex; flex-direction: column; align-items: center; gap: 8px;
  padding: 0; border: none; background: none; cursor: pointer; font-family: 'Heebo', sans-serif;
}
.nai:focus-visible { outline: 2px solid #0E8C8A; outline-offset: 6px; border-radius: 50%; }
.nai-ring {
  position: relative; display: grid; place-items: center; border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #FFFFFF 0%, #EEF8F6 55%, #DDF1EE 100%);
  box-shadow: inset 0 0 0 1px rgba(14, 140, 138, 0.18), 0 10px 30px rgba(14, 140, 138, 0.18), 0 2px 6px rgba(24, 24, 24, 0.06);
  animation: naiBreathe 4.8s ease-in-out infinite;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.nai--big .nai-ring { width: 118px; height: 118px; }
.nai--small .nai-ring { width: 54px; height: 54px; }
/* the orb never draws outside its ring */
.nai-orb-clip { display: grid; place-items: center; width: 100%; height: 100%; border-radius: 50%; overflow: hidden; }
.nai--big .nai-orb { transform: scale(1.35); }
.nai:hover .nai-ring { transform: scale(1.06); box-shadow: inset 0 0 0 1px rgba(14, 140, 138, 0.3), 0 14px 38px rgba(14, 140, 138, 0.28); }
.nai-glow {
  position: absolute; inset: -14px; border-radius: 50%; pointer-events: none;
  background: conic-gradient(from 0deg, rgba(14, 140, 138, 0), rgba(14, 140, 138, 0.28), rgba(143, 217, 198, 0.35), rgba(14, 140, 138, 0));
  filter: blur(14px); opacity: 0.7; animation: naiSpin 9s linear infinite;
}
.nai--small .nai-glow { inset: -6px; filter: blur(7px); }
/* phones: the icon sits near the screen edge — keep the glow inside it (no sideways scroll) */
@media (max-width: 700px) { .nai-glow { inset: -4px; filter: blur(8px); } }
.nai-badge {
  position: absolute; top: 4px; inset-inline-end: 4px; min-width: 22px; height: 22px; padding: 0 6px;
  border-radius: 999px; display: grid; place-items: center; font-size: 12px; font-weight: 900;
  color: #fff; background: #181818; box-shadow: 0 0 0 2px #fff;
}
.nai--small .nai-badge { top: -4px; inset-inline-end: -4px; min-width: 18px; height: 18px; font-size: 10.5px; }
.nai-cap {
  padding: 5px 13px; border-radius: 999px; background: rgba(255, 255, 255, 0.8);
  backdrop-filter: blur(8px); box-shadow: 0 2px 10px rgba(24, 24, 24, 0.08);
  font-size: 13px; font-weight: 800; letter-spacing: -0.01em; color: #181818;
}
.nai-cap b { color: #0E8C8A; font-weight: 900; }
@keyframes naiBreathe { 50% { transform: scale(1.035); } }
@keyframes naiSpin { to { transform: rotate(360deg); } }
/* attention: the orb swells twice and the badge bumps */
.nai--attn .nai-ring { animation: naiAttn 1.5s cubic-bezier(0.34, 1.4, 0.5, 1); }
.nai--attn .nai-ring::after {
  content: ''; position: absolute; inset: -6px; border-radius: 50%; border: 2px solid rgba(14, 140, 138, 0.55);
  animation: naiRing 1.5s ease-out; pointer-events: none;
}
.nai--attn .nai-badge { animation: naiBump 0.6s cubic-bezier(0.34, 1.8, 0.5, 1) 0.2s; }
@keyframes naiAttn { 0%, 100% { transform: scale(1); } 20% { transform: scale(1.12); } 40% { transform: scale(0.98); } 60% { transform: scale(1.08); } }
@keyframes naiRing { from { transform: scale(0.95); opacity: 1; } to { transform: scale(1.45); opacity: 0; } }
@keyframes naiBump { 50% { transform: scale(1.45); } }
@media (prefers-reduced-motion: reduce) { .nai-ring, .nai-glow, .nai--attn .nai-ring, .nai--attn .nai-ring::after, .nai--attn .nai-badge { animation: none; } }
</style>
