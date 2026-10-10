<template>
  <!-- The assistant, as one widget on the right rail rather than a card on
       every dashboard. Sits between the bell (top) and the messenger pill
       (bottom) so the rail reads: alerts · assistant · people. -->
  <button
    class="aiw"
    :class="['aiw--' + size, { 'aiw--active': ai.open, 'aiw--ctx': ai.hasContext }]"
    type="button"
    :title="title"
    :aria-label="title"
    @click="ai.openSheet('')"
  >
    <!-- ThinkingOrb (components/ui/thinking-orbs): "working" at rest,
         "listening" while the conversation is open. -->
    <ThinkingOrbIsland class="aiw-orb" :state="ai.open ? 'listening' : 'working'" :size="size === 'small' ? 32 : 64" :color="ORB_COLOR" :dot-size="1.7" :dots="1.2" />
    <!-- Only when the current screen can actually brief the AI. -->
    <span v-if="ai.hasContext" class="aiw-dot" aria-hidden="true"></span>
  </button>
</template>

<script setup>
// small = one 54px circle in the right-hand stack, the same size as its neighbours (user 2026-10-10)
defineProps({ size: { type: String, default: 'big' } })
import { computed } from 'vue'
import { useAiContextStore } from '../../stores/aiContext.js'
import ThinkingOrbIsland from './ThinkingOrbIsland.vue'

const ORB_COLOR = '#6A48C9' // --tab-ai-ink
const ai = useAiContextStore()

const title = computed(() =>
  ai.hasContext
    ? `Nifra AI · ${ai.viewTitle || 'המסך הזה'}`
    : 'Nifra AI',
)
</script>

<style scoped>
.aiw {
  position: relative;
  /* 64px, not 46. At widget size the orb's motion has to be legible from
     across the page, and a 46px circle rendered the core at ~20px where the
     breath and the sparks were invisible. Still under the bell's visual
     weight so the rail does not gain a second focal point. */
  width: 70px; height: 70px; padding: 0; overflow: hidden;
  display: grid; place-items: center;
  border-radius: 50%; cursor: pointer;
  border: 1px solid var(--border-subtle);
  background: var(--card-bg);
  color: #6A48C9;
  background: radial-gradient(circle at 50% 45%, #fff 0%, #F6F2FD 100%);
  box-shadow: 0 6px 18px rgba(106, 72, 201, 0.16);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.aiw:hover { transform: translateY(-2px); box-shadow: 0 10px 24px rgba(46, 60, 130, 0.2); }
.aiw:focus-visible { outline: 2px solid #7C4DBE; outline-offset: 3px; }
.aiw--active { border-color: #7C4DBE; }

.aiw-orb { width: 64px; height: 64px; }
.aiw--small { width: 54px; height: 54px; }
.aiw--small .aiw-orb { width: 32px; height: 32px; }
.aiw--small .aiw-dot { top: 3px; left: 3px; width: 9px; height: 9px; }

/* A screen the AI can actually speak about. Absent = it still opens, just
   without view context — which is a real difference worth showing. */
.aiw-dot {
  position: absolute; top: 5px; left: 5px; z-index: 2;
  width: 10px; height: 10px; border-radius: 50%;
  background: var(--green, #2E844A);
  border: 2px solid var(--card-bg);
}

@media (prefers-reduced-motion: reduce) {
  .aiw:hover { transform: none; }
}
</style>
