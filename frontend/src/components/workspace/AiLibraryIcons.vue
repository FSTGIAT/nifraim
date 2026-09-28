<template>
  <!-- What Nifra AI can read, as small library icons (not a chip per file):
       agreements shelf · production · נפרעים · personal file, each with a
       count badge; the tooltip names them. Only libraries that have content. -->
  <div v-if="libs.length" class="ail" role="list" aria-label="הספריות ש-Nifra AI קורא">
    <component
      :is="clickable ? 'button' : 'span'"
      v-for="l in libs" :key="l.id"
      :type="clickable ? 'button' : undefined"
      class="ail-ic" role="listitem"
      :style="{ '--c': l.color }"
      :title="l.title" :aria-label="l.title"
      @click="clickable && $emit('open', l.tab)"
    >
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <template v-if="l.id === 'agreements'"><path d="M4 20h16"/><rect x="5" y="5" width="3.2" height="12" rx="0.8"/><rect x="10.4" y="3.5" width="3.2" height="13.5" rx="0.8"/><path d="m16 6.5 3 -0.8 2.6 10.4 -3 0.8z"/></template>
        <template v-else-if="l.id === 'production'"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/></template>
        <template v-else-if="l.id === 'commission'"><path d="M12 3v18M5 21h14"/><path d="M5 7h14"/><path d="m5 7-3 7a3 3 0 0 0 6 0z"/><path d="m19 7-3 7a3 3 0 0 0 6 0z"/></template>
        <template v-else><rect x="3" y="7" width="18" height="13" rx="2"/><path d="M8 7V5a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></template>
      </svg>
      <b v-if="l.count > 1" class="ail-n ltr-number">{{ l.count }}</b>
    </component>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  documents: { type: Array, default: () => [] }, // uploaded agreement docs
  sources: { type: Array, default: () => [] }, // /api/ai/sources [{type,label}]
  clickable: { type: Boolean, default: false },
})
defineEmits(['open'])

const libs = computed(() => {
  const n = (t) => props.sources.filter((s) => s.type === t).length
  const docs = props.documents.filter((d) => d.status !== 'error').length
  const commissionNames = props.sources.filter((s) => s.type === 'commission').map((s) => s.label).join(', ')
  return [
    { id: 'agreements', count: docs, tab: 'commission-rates', color: 'var(--tab-commission, #8E44AD)',
      title: `מדף ההסכמים · ${docs} הסכמים` },
    { id: 'production', count: n('production'), tab: 'production', color: 'var(--tab-production, #2F73C4)',
      title: 'פרודוקציה' },
    { id: 'commission', count: n('commission'), tab: 'comparison', color: 'var(--tab-comparison, #2E844A)',
      title: `נפרעים${commissionNames ? ' · ' + commissionNames : ''}` },
    { id: 'myfile', count: n('myfile'), tab: 'recruits', color: 'var(--tab-recruits-ink, #1E7D78)',
      title: 'תיק אישי' },
  ].filter((l) => l.count > 0)
})
</script>

<style scoped>
.ail { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.ail-ic {
  position: relative; width: 30px; height: 30px; border-radius: 10px; padding: 0;
  display: grid; place-items: center; font-family: inherit;
  color: var(--c);
  background: color-mix(in srgb, var(--c) 11%, #fff);
  border: 1px solid color-mix(in srgb, var(--c) 22%, transparent);
  transition: transform 0.15s ease, background 0.15s ease;
}
button.ail-ic { cursor: pointer; }
button.ail-ic:hover { transform: translateY(-1px); background: color-mix(in srgb, var(--c) 18%, #fff); }
button.ail-ic:focus-visible { outline: 2px solid var(--c); outline-offset: 2px; }
.ail-n {
  position: absolute; top: -6px; inset-inline-start: -6px; min-width: 16px; height: 16px; padding: 0 4px;
  border-radius: 999px; display: grid; place-items: center;
  font-size: 10px; font-weight: 800; line-height: 1; color: #fff; background: var(--c);
  box-shadow: 0 0 0 2px #fff;
}
</style>
