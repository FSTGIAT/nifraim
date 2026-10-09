<template>
  <header class="sn" :class="{ 'sn--solid': solid }">
    <!-- The public site's one top bar (home, login, signup, pricing…): a glass pill with
         the wordmark, the product tabs and the two actions. On the home page the tabs
         scroll (the page drives `active`); elsewhere they link to /#chapter. -->
    
    <a v-if="home" href="#top" class="sn-brand" dir="ltr" @click.prevent="$emit('go', 'top')"
       @mouseenter="$emit('brand-hover', true)" @mouseleave="$emit('brand-hover', false)"><NifraimIcon :size="30" /><b>Nifraim<span>.com</span></b></a>
    <router-link v-else to="/" class="sn-brand" dir="ltr"><NifraimIcon :size="30" /><b>Nifraim<span>.com</span></b></router-link>

    <nav class="sn-tabs" ref="tabsEl" aria-label="ניווט">
      <template v-for="t in TABS" :key="t.id">
        <a v-if="home" :href="'#' + t.id" class="sn-tab" :class="{ 'sn-tab--on': active === t.id }" :data-tab="t.id"
           :style="{ '--tc': t.ink }" @click.prevent="$emit('go', t.id)"
        ><span :dir="t.ltr ? 'ltr' : null">{{ t.label }}</span></a>
        <router-link v-else :to="'/#' + t.id" class="sn-tab" :data-tab="t.id" :style="{ '--tc': t.ink }"
        ><span :dir="t.ltr ? 'ltr' : null">{{ t.label }}</span></router-link>
      </template>
      <span class="sn-pill" :style="pillStyle" aria-hidden="true"></span>
    </nav>

    <div class="sn-end">
      <!-- no button for the page you're already on -->
      <router-link v-if="route.name !== 'Login'" to="/login" class="sn-btn sn-btn--ghost">התחברות</router-link>
      <router-link v-if="route.name !== 'Signup' && route.name !== 'Register'" to="/signup" class="sn-btn">התחילו</router-link>
    </div>
  </header>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import NifraimIcon from '../common/NifraimIcon.vue'

const props = defineProps({
  home: { type: Boolean, default: false },   // on the home page: tabs scroll instead of navigate
  active: { type: String, default: '' },     // the chapter in view (home only)
  solid: { type: Boolean, default: false },  // page scrolled → a touch more opaque
})
defineEmits(['go', 'brand-hover'])
const route = useRoute()

// Product colours: the pill takes the accent, hover text takes the ink.
const TABS = [
  { id: 'agent', label: 'Nifra Agent', ltr: true, ink: '#0A6664', color: '#0E8C8A' },
  { id: 'call', label: 'Nifra Calls', ltr: true, ink: '#A63A86', color: '#D96AB5' },
  { id: 'report', label: 'Nifra Report', ltr: true, ink: '#2E2A8C', color: '#2E2A8C' },
]

const tabsEl = ref(null)
const pillStyle = ref({ opacity: 0 })
function placePill() {
  const nav = tabsEl.value
  const on = nav?.querySelector(`[data-tab="${props.active}"]`)
  if (!nav || !on) { pillStyle.value = { ...pillStyle.value, opacity: 0 }; return }
  const nr = nav.getBoundingClientRect()
  const r = on.getBoundingClientRect()
  const tab = TABS.find(t => t.id === props.active)
  pillStyle.value = { opacity: 1, width: r.width + 'px', transform: `translateX(${r.left - nr.left}px)`, background: tab?.color }
}
watch(() => props.active, () => nextTick(placePill))
onMounted(() => { placePill(); window.addEventListener('resize', placePill) })
onBeforeUnmount(() => window.removeEventListener('resize', placePill))
</script>

<style scoped>
.sn {
  --ink: #181818;
  --graphite: #2A2E35;
  --blue: #2F73C4;
  --ease: cubic-bezier(0.22, 1, 0.36, 1);
  position: fixed; top: 14px; inset-inline: 16px; z-index: 110;
  display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 12px;
  padding: 8px 10px 8px 14px; border-radius: 999px; direction: rtl; font-family: 'Heebo', sans-serif;
  background: rgba(255, 255, 255, 0.62); backdrop-filter: blur(18px) saturate(1.4);
  box-shadow: 0 1px 0 rgba(255, 255, 255, 0.5) inset, 0 10px 30px rgba(10, 30, 60, 0.12);
  transition: background 0.4s ease, box-shadow 0.4s ease;
}
.sn--solid {
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 1px 0 rgba(24, 24, 24, 0.06), 0 10px 30px rgba(24, 24, 24, 0.08);
}
.sn-brand {
  justify-self: start; display: inline-flex; align-items: center; gap: 8px;
  font-weight: 800; font-size: 20px; letter-spacing: -0.03em; color: var(--brand-ink); text-decoration: none;
  transition: text-shadow 0.6s ease;
}
.sn-brand b { font-weight: inherit; }
.sn-brand span { color: var(--brand-blue); }
.sn-brand:hover { text-shadow: 0 0 18px rgba(255, 236, 170, 0.9); }
.sn-tabs { position: relative; display: flex; gap: 2px; padding: 4px; border-radius: 999px; background: rgba(24, 24, 24, 0.05); }
.sn-tab {
  position: relative; z-index: 1; padding: 8px 16px; border-radius: 999px;
  font-size: 14px; font-weight: 600; color: var(--ink); text-decoration: none; white-space: nowrap;
  transition: color 0.35s ease;
}
.sn-tab--on { color: #FFFFFF; }
.sn-tab:not(.sn-tab--on):hover { color: var(--tc); }
.sn-pill {
  position: absolute; top: 4px; bottom: 4px; left: 0; border-radius: 999px; z-index: 0;
  transition: transform 0.6s var(--ease), width 0.6s var(--ease), background 0.6s ease, opacity 0.3s ease;
}
.sn-end { justify-self: end; display: flex; gap: 8px; }
.sn-btn {
  display: inline-flex; align-items: center; justify-content: center;
  padding: 9px 18px; border-radius: 10px; border: 1px solid transparent;
  background: var(--ink); color: #FFFFFF; font: 700 14px 'Heebo', sans-serif; text-decoration: none; cursor: pointer;
  box-shadow: 0 6px 18px rgba(24, 24, 24, 0.18); transition: transform 0.25s ease, box-shadow 0.25s ease, background 0.25s ease;
}
.sn-btn:hover { transform: translateY(-1px); background: #000; box-shadow: 0 10px 24px rgba(24, 24, 24, 0.24); }
.sn-btn--ghost { background: transparent; color: var(--ink); border-color: rgba(24, 24, 24, 0.16); box-shadow: none; }
.sn-btn--ghost:hover { background: rgba(24, 24, 24, 0.05); box-shadow: none; }

@media (max-width: 960px) {
  .sn { grid-template-columns: auto 1fr; }
  .sn-tabs { display: none; }
}
@media (max-width: 520px) {
  .sn { padding: 6px 8px 6px 12px; inset-inline: 10px; }
  .sn-end .sn-btn--ghost { display: none; }
}
</style>
