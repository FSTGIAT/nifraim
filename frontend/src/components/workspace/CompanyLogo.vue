<template>
  <span class="clogo" :class="{ 'clogo--bare': !frame }" :style="{ width: size + 'px', height: size + 'px' }">
    <!-- The real mark when we have one. Vendored at build time rather than
         hotlinked, so no third-party request tells an outside service which
         insurers this agent works with. -->
    <img v-if="src && !failed" :src="src" :alt="company" loading="lazy" @error="failed = true" />
    <!-- Otherwise the drawn brand glyph — every company has one, so a missing
         logo degrades to a recognisable mark, never to a blank square. -->
    <svg v-else viewBox="0 0 24 24" fill="none" :stroke="brand.color" stroke-width="1.8"
         stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path :d="brand.iconPath" />
    </svg>
  </span>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { brandForLabel, COMPANY_BRAND } from '../../utils/companyBrand.js'

const props = defineProps({
  company: { type: String, default: '' },
  size: { type: Number, default: 34 },
  /* Draw the rounded tile. Off where the CALLER already supplies one — the
     automation rows and the comparison table both wrap their mark in a
     brand-tinted square, and a framed logo inside that is a tile in a tile. */
  frame: { type: Boolean, default: true },
})

const LOGOS = import.meta.glob('../../assets/logos/*.png', { eager: true, import: 'default' })

// Brand-map key → vendored file. The map is keyed by portal kind, so several
// keys share one company (clal, clal_nifraim, clal_health) and therefore one
// logo; matching on the key's leading segment covers them all.
const byKey = {}
for (const path in LOGOS) {
  const name = path.split('/').pop().replace('.png', '')
  byKey[name] = LOGOS[path]
}

const brand = computed(() => brandForLabel(props.company))

const src = computed(() => {
  const label = String(props.company || '').trim()
  if (!label) return null
  // Resolve through `brandForLabel` rather than matching here. This used to run
  // its own `includes` loop, which had no head-word rule: a production row
  // saying `מיטב גמל ופנסיה בע"מ` does not contain `מיטב דש`, so it found no
  // logo and fell back to the drawn glyph while the same company showed its
  // real mark two panels over. One matcher, one answer.
  const b = brandForLabel(label)
  for (const [key, entry] of Object.entries(COMPANY_BRAND)) {
    if (entry !== b) continue
    const file = byKey[key] || byKey[key.split('_')[0]]
    if (file) return file
  }
  return null
})

const failed = ref(false)
watch(src, () => { failed.value = false })
</script>

<style scoped>
.clogo {
  flex-shrink: 0;
  display: grid; place-items: center;
  border-radius: 9px; overflow: hidden;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
}
/* The mark fills more of its tile at large sizes — at 88px a 72% inset left
   the logo looking lost inside its own frame. */
.clogo img { width: 78%; height: 78%; object-fit: contain; display: block; }
.clogo svg { width: 62%; height: 62%; }

.clogo--bare {
  background: none;
  border: none;
  border-radius: 0;
}
/* Without a frame of its own the mark should fill the caller's. */
.clogo--bare img { width: 100%; height: 100%; }
.clogo--bare svg { width: 100%; height: 100%; }
</style>
