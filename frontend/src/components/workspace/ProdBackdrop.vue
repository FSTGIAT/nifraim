<template>
  <!-- Big faint animated backdrop behind a Production sub-screen (like the
       automation tab's gears). Decorative; skipped for reduced motion. -->
  <Teleport to="body">
  <div class="pbd" aria-hidden="true">
    <RemotionLoopIsland
      :key="variant"
      class="pbd-scene"
      component="ProductionBackdrop"
      frames-key="PRODUCTION_BACKDROP_FRAMES"
      :width="1600"
      :height="1000"
      :input-props="{ variant, color: '#2F73C4' }"
    />
  </div>
  </Teleport>
</template>

<script setup>
import RemotionLoopIsland from './RemotionLoopIsland.vue'

defineProps({ variant: { type: String, required: true } }) // compare | volume | history
</script>

<style scoped>
/* Full-screen layer behind the whole page (sides included), under all content. */
.pbd {
  position: fixed; inset: 0; z-index: -1; overflow: hidden; pointer-events: none;
}
/* "cover": at least the viewport's width and height, anchored to the bottom. */
.pbd-scene {
  position: absolute; bottom: 0; left: 50%; transform: translateX(-50%);
  width: max(100vw, 160vh);
}
</style>
