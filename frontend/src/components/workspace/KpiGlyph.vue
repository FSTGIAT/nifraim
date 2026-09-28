<template>
  <!-- Duotone decorative KPI glyphs: a soft currentColor fill under a
       Lucide-weight stroke. Used as the card badge AND as the oversized ghost
       in the card corner, so one drawing per KPI. -->
  <svg :width="size" :height="size" viewBox="0 0 24 24" fill="none" stroke="currentColor"
       :stroke-width="stroke" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <template v-if="name === 'products'">
      <rect x="7" y="2.5" width="12" height="15" rx="2" fill="currentColor" fill-opacity="0.18" />
      <path d="M5 6.5v12.5a2 2 0 0 0 2 2h9" />
      <path d="M10.5 7.5h5M10.5 10.5h5M10.5 13.5h3" />
    </template>
    <template v-else-if="name === 'clients'">
      <circle cx="9" cy="8" r="3.5" fill="currentColor" fill-opacity="0.18" />
      <path d="M2.5 20v-1.2A4.8 4.8 0 0 1 7.3 14h3.4a4.8 4.8 0 0 1 4.8 4.8V20" fill="currentColor" fill-opacity="0.18" />
      <path d="M16 4.6a3.5 3.5 0 0 1 0 6.8" />
      <path d="M18.5 14.3a4.8 4.8 0 0 1 3 4.5V20" />
    </template>
    <template v-else-if="name === 'accumulation'">
      <ellipse cx="9" cy="17" rx="6" ry="2.5" fill="currentColor" fill-opacity="0.18" />
      <path d="M3 17v-3.5c0 1.4 2.7 2.5 6 2.5s6-1.1 6-2.5V17" />
      <ellipse cx="9" cy="13.5" rx="6" ry="2.5" fill="currentColor" fill-opacity="0.18" />
      <path d="M13 5.5l3.2-2.5 2.8 2.2L22 3" />
      <path d="M19 3h3v3" />
    </template>
    <template v-else-if="name === 'companies'">
      <path d="M12 2.5 21 7.5H3z" fill="currentColor" fill-opacity="0.18" />
      <path d="M5 10.5v7M9.7 10.5v7M14.3 10.5v7M19 10.5v7" />
      <path d="M3 20.5h18" />
    </template>
    <template v-else>
      <circle cx="12" cy="12" r="9.5" fill="currentColor" fill-opacity="0.18" />
      <path d="M5.5 12.5h3l1.8-3.5 3 7 1.8-3.5h3.4" />
    </template>
  </svg>
</template>

<script setup>
defineProps({
  name: { type: String, required: true }, // products | clients | accumulation | companies | active
  size: { type: Number, default: 22 },
  stroke: { type: Number, default: 1.8 },
})
</script>
