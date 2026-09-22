<template>
  <span class="clogo" :style="{ width: size + 'px', height: size + 'px' }">
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
  // Find the brand key whose label this contact's company name contains.
  for (const [key, b] of Object.entries(COMPANY_BRAND)) {
    const base = String(b.label || '').split('—')[0].trim()
    if (!base) continue
    if (label.includes(base) || base.includes(label)) {
      const file = byKey[key] || byKey[key.split('_')[0]]
      if (file) return file
    }
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
</style>
