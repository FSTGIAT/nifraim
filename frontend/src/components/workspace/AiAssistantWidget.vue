<template>
  <!-- The assistant, as one widget on the right rail rather than a card on
       every dashboard. Sits between the bell (top) and the messenger pill
       (bottom) so the rail reads: alerts · assistant · people. -->
  <button
    class="aiw"
    :class="{ 'aiw--active': ai.open, 'aiw--ctx': ai.hasContext }"
    type="button"
    :title="title"
    :aria-label="title"
    @click="ai.openSheet('')"
  >
    <AiOrbIsland :color="ORB_COLOR" :active="ai.open" />
    <!-- The glyph stays legible over the orb: motion alone should not be the
         only thing telling you what the control does (ux color-not-only). -->
    <svg class="aiw-glyph" width="24" height="24" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"
         aria-hidden="true">
      <path d="M12 3l1.7 4.8L18.5 9.5 13.7 11.2 12 16l-1.7-4.8L5.5 9.5l4.8-1.7z" />
      <path d="M18.5 16.5v3M20 18h-3" />
    </svg>
    <!-- Only when the current screen can actually brief the AI. -->
    <span v-if="ai.hasContext" class="aiw-dot" aria-hidden="true"></span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import { useAiContextStore } from '../../stores/aiContext.js'
import AiOrbIsland from './AiOrbIsland.vue'

const ORB_COLOR = '#7C4DBE'
const ai = useAiContextStore()

const title = computed(() =>
  ai.hasContext
    ? `שאל את ה-AI על ${ai.viewTitle || 'המסך הזה'}`
    : 'שאל את ה-AI',
)
</script>

<style scoped>
.aiw {
  position: relative;
  /* 64px, not 46. At widget size the orb's motion has to be legible from
     across the page, and a 46px circle rendered the core at ~20px where the
     breath and the sparks were invisible. Still under the bell's visual
     weight so the rail does not gain a second focal point. */
  width: 64px; height: 64px; padding: 0;
  display: grid; place-items: center;
  border-radius: 50%; cursor: pointer;
  border: 1px solid var(--border-subtle);
  background: var(--card-bg);
  color: #7C4DBE;
  box-shadow: 0 6px 18px rgba(46, 60, 130, 0.14);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.aiw:hover { transform: translateY(-2px); box-shadow: 0 10px 24px rgba(46, 60, 130, 0.2); }
.aiw:focus-visible { outline: 2px solid #7C4DBE; outline-offset: 3px; }
.aiw--active { border-color: #7C4DBE; }

/* White on the orb's core. It inherited the widget colour, which is the same
   purple as the core it sits on — the glyph was invisible, and the glyph is
   what tells you the control is the AI (ux color-not-only). */
.aiw-glyph {
  position: relative; z-index: 1;
  color: #fff;
  filter: drop-shadow(0 1px 2px rgba(40, 20, 70, 0.35));
}

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
