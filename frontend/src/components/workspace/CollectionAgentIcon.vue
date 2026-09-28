<template>
  <!-- סוכן המשרד (the office agent), in the cycle clock's line-art style:
       an envelope sealed with ₪, a magnifier checking it, a slow dashed halo.
       Badge = insurers that still need the agent's action. Click → the panel,
       which grows out of this icon. Shown only once a comparison exists. -->
  <button
    v-if="store.visible"
    ref="btnEl"
    type="button"
    class="cai"
    :class="'cai--' + size"
    :title="title"
    :aria-label="title"
    @click="$emit('open', btnEl)"
  >
    <svg class="cai-svg" viewBox="0 0 120 112" aria-hidden="true">
      <g fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round">
        <circle class="cai-halo" cx="58" cy="58" r="50" stroke-width="1.2" stroke-dasharray="2 8" opacity="0.5" />
        <g class="cai-float">
          <!-- envelope -->
          <rect x="22" y="34" width="72" height="50" rx="7" stroke-width="2.6" fill="var(--card-bg, #fff)" />
          <path d="M23 37 L58 62 L93 37" stroke-width="2.6" />
          <path d="M24 82 L48 60 M92 82 L68 60" stroke-width="1.4" opacity="0.45" />
          <!-- ₪ seal -->
          <circle cx="58" cy="66" r="10" stroke-width="2" fill="var(--card-bg, #fff)" />
          <text x="58" y="70.5" text-anchor="middle" font-family="Heebo, sans-serif" font-size="12" font-weight="800"
                fill="currentColor" stroke="none">₪</text>
          <!-- magnifier checking the mail -->
          <g class="cai-lens">
            <circle cx="92" cy="28" r="11" stroke-width="2.4" fill="var(--card-bg, #fff)" />
            <path d="M100 36 l8 8" stroke-width="3" />
            <path d="M87 28 l3.5 3.5 l6 -7" stroke-width="2" />
          </g>
        </g>
      </g>
    </svg>
    <b v-if="store.todoCount" class="cai-badge ltr-number">{{ store.todoCount }}</b>
    <span v-if="size === 'big'" class="cai-cap">סוכן המשרד</span>
  </button>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useOfficeAgentStore } from '../../stores/officeAgent.js'

defineProps({ size: { type: String, default: 'big' } }) // big (home, under the clock) | small (corner)
defineEmits(['open'])
const store = useOfficeAgentStore()
const btnEl = ref(null)
const title = computed(() =>
  store.todoCount ? `סוכן המשרד · ${store.todoCount} דברים מחכים לך` : 'סוכן המשרד',
)
onMounted(() => { if (!store.brief) store.load() })
</script>

<style scoped>
.cai {
  position: relative; display: inline-flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 0; border: none; background: none; cursor: pointer; color: var(--tab-comparison, #2E844A);
  font-family: 'Heebo', sans-serif; transition: transform 0.2s ease;
}
.cai:hover { transform: scale(1.05); }
.cai:focus-visible { outline: 2px solid var(--tab-comparison, #2E844A); outline-offset: 4px; border-radius: 16px; }
.cai--big .cai-svg { width: 118px; height: auto; }
.cai--small .cai-svg { width: 52px; height: auto; }
.cai-svg { overflow: visible; filter: drop-shadow(0 3px 6px rgba(24, 24, 24, 0.1)); }
.cai-halo { transform-origin: 58px 58px; animation: caiHalo 40s linear infinite; }
.cai-float { animation: caiFloat 4s ease-in-out infinite; }
.cai-lens { transform-origin: 92px 28px; animation: caiLens 6s ease-in-out infinite; }
@keyframes caiHalo { to { transform: rotate(360deg); } }
@keyframes caiFloat { 50% { transform: translateY(-3px); } }
@keyframes caiLens { 0%, 70%, 100% { transform: none; } 80% { transform: translate(-6px, 4px) rotate(-8deg); } 90% { transform: translate(-2px, 1px); } }
.cai-badge {
  position: absolute; top: 2px; inset-inline-end: 2px; min-width: 22px; height: 22px; padding: 0 6px;
  border-radius: 999px; display: grid; place-items: center;
  font-size: 12px; font-weight: 900; color: #fff; background: #E04B48; box-shadow: 0 0 0 2px #fff;
}
.cai--small .cai-badge { top: -4px; inset-inline-end: -6px; min-width: 18px; height: 18px; font-size: 10.5px; }
.cai-cap {
  padding: 4px 12px; border-radius: 999px; background: var(--card-bg, #fff);
  box-shadow: var(--shadow-sm); font-size: 12.5px; font-weight: 800; color: var(--text-primary, #181818);
}
@media (prefers-reduced-motion: reduce) { .cai-halo, .cai-float, .cai-lens { animation: none; } }
</style>
