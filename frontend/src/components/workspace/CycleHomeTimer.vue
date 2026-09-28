<template>
  <!-- The monthly cycle as a live, animated widget (opened from CycleRailIcon). Locked
       agents count down to the Production tab opening; everyone else to the
       next cycle. Same width as the home cards grid (like SetupProgressCard). -->
  <section v-if="st" class="cw" :class="{ 'cw--wait': st.worker_waiting, 'cw--locked': st.locked, 'cw--embedded': embedded }">
    <header class="cw-head">
      <span class="cw-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/><path d="m9 16 2 2 4-4"/></svg>
      </span>
      <div class="cw-titles">
        <span class="cw-kicker">המחזור החודשי</span>
        <strong class="cw-title">{{ title }}</strong>
      </div>
      <span class="cw-chip" :class="'cw-chip--' + chip.tone" :style="embedded ? { marginInlineEnd: '36px' } : null">
        <span class="cw-chip-dot"></span>{{ chip.text }}
      </span>
    </header>

    <div class="cw-stage" :class="{ 'cw-stage--narrow': narrow }" :style="{ aspectRatio: narrow ? '300 / 230' : '880 / 230' }">
      <div v-if="useStatic" class="cw-static" role="timer">
        <span class="cw-static-num ltr-number">{{ staticDays }}</span>
        <span>ימים עד {{ shortDate(target) }}</span>
      </div>
      <div v-else ref="mountEl" class="cw-mount" aria-hidden="true"></div>
    </div>

    <!-- the agent's own dates: signup + where they stand with the מסלקה -->
    <div class="cw-facts">
      <span v-if="signup" class="cw-fact">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M19 8v6M22 11h-6"/></svg>
        {{ signup }}
      </span>
      <span v-if="mas" class="cw-fact" :class="'cw-fact--' + mas.tone" :title="MASLAKA_RULE">
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18"/><path d="M6 18v-7M10 18v-7M14 18v-7M18 18v-7"/><path d="m12 2 8 5H4Z"/></svg>
        <strong>{{ mas.title }}</strong><span v-if="mas.sub">{{ mas.sub }}</span>
      </span>
    </div>

    <footer class="cw-foot">
      <span class="cw-sub">{{ sub }}</span>
      <button type="button" class="cw-go" @click="onOpen">
        {{ st.locked ? 'מה יקרה ב-21' : 'לאוטומציה' }}
        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
      </button>
    </footer>
  </section>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useCycleStore, monthName, shortDate, signupLine, maslakaLine, MASLAKA_RULE } from '../../stores/cycle.js'

const props = defineProps({ embedded: { type: Boolean, default: false } })
const emit = defineEmits(['select'])
const cycle = useCycleStore()
const st = computed(() => cycle.status)

function monthBefore(iso) {
  const d = new Date(iso)
  return monthName(new Date(d.getFullYear(), d.getMonth() - 1, 1).toISOString())
}
function prevMonthSameDay(iso) {
  const d = new Date(iso)
  return new Date(d.getFullYear(), d.getMonth() - 1, d.getDate(), d.getHours(), d.getMinutes())
}

const signup = computed(() => signupLine(st.value))
const mas = computed(() => maslakaLine(st.value))
const target = computed(() => (st.value?.locked ? st.value.first_cycle_at : st.value?.next_cycle_at))
const periodName = computed(() => (target.value ? monthBefore(target.value) : ''))
const title = computed(() => {
  const s = st.value
  if (!s) return ''
  if (s.locked) return `הפרודוקציה נפתחת ב-${shortDate(s.first_cycle_at)} · 06:00`
  if (s.worker_waiting) return `המחזור של ${s.current_period_label} ממתין למחשב`
  return `המחזור הבא: ${shortDate(s.next_cycle_at)} · 06:00`
})
const sub = computed(() => {
  const s = st.value
  if (!s) return ''
  if (s.locked) return `באותו בוקר נוריד לבד את הנפרעים של ${periodName.value} מכל החברות.`
  if (s.worker_waiting) return 'ההורדה תתחיל לבד ברגע שהמחשב יודלק ויתחבר.'
  return `הנפרעים של ${monthName(s.next_period)} יורדים לבד — רק שהמחשב יהיה דלוק.`
})
const chip = computed(() => {
  const s = st.value
  if (s?.worker_waiting) return { tone: 'wait', text: 'ממתין למחשב' }
  if (['pending', 'running'].includes(s?.cycle_batch_status)) return { tone: 'live', text: 'רץ עכשיו' }
  if (s?.locked) return { tone: 'locked', text: 'המחזור הראשון' }
  return { tone: 'ok', text: 'אוטומטי' }
})

function onOpen() {
  emit('select', st.value?.locked ? 'production' : 'portal-automation')
}

// ── Remotion island ──
const narrow = ref(typeof window !== 'undefined' && window.innerWidth < 640)
function onResize() {
  const n = window.innerWidth < 640
  if (n !== narrow.value) { narrow.value = n; nextTick(draw) }
}
window.addEventListener('resize', onResize)
const mountEl = ref(null)
const useStatic = ref(false)
let reactRoot = null
let mods = null
const staticDays = computed(() => Math.max(0, Math.floor((new Date(target.value).getTime() - Date.now()) / 86400000)))

function draw() {
  if (!reactRoot || !mods || !target.value) return
  const s = st.value
  const { react, player, remotion } = mods
  reactRoot.render(react.createElement(player.Player, {
    component: remotion.CycleWidget,
    inputProps: {
      targetMs: new Date(target.value).getTime(),
      startMs: prevMonthSameDay(target.value).getTime(),
      color: s.locked ? '#2F73C4' : '#0A6664',
      ink: '#181818',
      targetLabel: shortDate(target.value),
      targetCaption: `נפרעים ${periodName.value}`,
      startLabel: shortDate(prevMonthSameDay(target.value).toISOString()),
      maslakaMs: s.maslaka_first_auto ? new Date(s.maslaka_first_auto).getTime() : null,
      maslakaLabel: s.maslaka_first_auto ? shortDate(s.maslaka_first_auto) : '',
      waiting: !!s.worker_waiting,
      narrow: narrow.value,
      signupMs: s.signup_at ? new Date(s.signup_at).getTime() : null,
      signupLabel: s.signup_at ? shortDate(s.signup_at) : '',
    },
    durationInFrames: remotion.CYCLE_WIDGET_FRAMES,
    fps: 30,
    compositionWidth: narrow.value ? 300 : 880,
    compositionHeight: 230,
    autoPlay: true,
    loop: true,
    controls: false,
    clickToPlay: false,
    doubleClickToFullscreen: false,
    acknowledgeRemotionLicense: true,
    style: { width: '100%', height: '100%' },
  }))
}

async function mount() {
  if (reactRoot || !mountEl.value) return
  if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) { useStatic.value = true; return }
  try {
    const [rdClient, react, player, remotion] = await Promise.all([
      import('react-dom/client'), import('react'), import('@remotion/player'), import('../../remotion'),
    ])
    if (!mountEl.value) return
    mods = { react, player, remotion }
    reactRoot = rdClient.createRoot(mountEl.value)
    draw()
  } catch (e) {
    console.error('[CycleHomeTimer] render failed', e)
    useStatic.value = true
  }
}

// The section renders once status arrives — mount the Player then, redraw on change.
watch(st, () => nextTick(() => (reactRoot ? draw() : mount())), { immediate: true })

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
  }
})
</script>

<style scoped>
.cw {
  position: relative;
  box-sizing: border-box;
  width: calc(100% - 48px);
  max-width: 882px;
  margin: 24px auto -12px;
  display: flex; flex-direction: column; gap: 6px;
  padding: 16px 18px 14px;
  background:
    radial-gradient(120% 140% at 0% 0%, rgba(47, 115, 196, 0.07), transparent 55%),
    var(--card-bg, #fff);
  border: 1px solid var(--border-subtle, #E5E5E5);
  border-radius: 14px;
  box-shadow: var(--shadow-sm);
  font-family: 'Heebo', sans-serif;
  overflow: hidden;
  z-index: 2;
  animation: cwIn 0.5s ease both;
}
.cw:not(.cw--locked) {
  background: radial-gradient(120% 140% at 0% 0%, rgba(14, 140, 138, 0.07), transparent 55%), var(--card-bg, #fff);
}
.cw--wait { border-color: color-mix(in srgb, var(--amber, #8A6300) 35%, transparent); }
.cw--embedded { width: 100%; max-width: none; margin: 0; box-shadow: var(--shadow-lg, 0 20px 50px rgba(0, 0, 0, 0.18)); }
@keyframes cwIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }

.cw-head { display: flex; align-items: center; gap: 12px; }
.cw-icon {
  flex-shrink: 0; width: 38px; height: 38px; border-radius: 11px;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--tab-production-wash); color: var(--tab-production);
}
.cw:not(.cw--locked) .cw-icon { background: var(--tab-automation-wash); color: #0A6664; }
.cw-titles { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.cw-kicker { font-size: 11.5px; font-weight: 800; color: var(--text-secondary, #706E6B); }
.cw-title { font-size: 17px; font-weight: 800; color: var(--text-primary, #181818); }
.cw--wait .cw-title { color: var(--amber, #8A6300); }

.cw-chip {
  flex-shrink: 0; display: inline-flex; align-items: center; gap: 7px;
  padding: 5px 12px; border-radius: 999px; font-size: 12px; font-weight: 800;
}
.cw-chip-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; animation: cwDot 2s ease-in-out infinite; }
@keyframes cwDot { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.45; transform: scale(0.7); } }
.cw-chip--locked { background: var(--tab-production-wash); color: var(--tab-production); }
.cw-chip--ok { background: var(--tab-automation-wash); color: #0A6664; }
.cw-chip--live { background: var(--tab-automation-wash); color: #0A6664; }
.cw-chip--wait { background: var(--amber-light, #FBF4DC); color: var(--amber, #8A6300); }

.cw-stage { width: 100%; }
.cw-stage--narrow { width: min(260px, 80%); align-self: center; }
.cw-mount { width: 100%; height: 100%; direction: ltr; } /* Player math assumes LTR */
.cw-static { height: 100%; display: flex; align-items: center; justify-content: center; gap: 10px; color: var(--text-secondary, #706E6B); font-weight: 700; }
.cw-static-num { font-size: 48px; font-weight: 900; color: var(--tab-production); }

.cw-facts { display: flex; flex-wrap: wrap; gap: 8px; }
.cw-fact {
  display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px;
  background: #F4F3F1; color: #3E3E3C; font-size: 12.5px; font-weight: 600;
}
.cw-fact strong { font-weight: 800; }
.cw-fact--ok { background: #EAF5EE; color: #2E844A; }
.cw-fact--wait { background: #FBF4DC; color: #8A6300; }
.cw-fact--todo { background: #E4EDEF; color: #2C5F6B; }
.cw-foot { display: flex; align-items: center; gap: 12px; }
.cw-sub { flex: 1; min-width: 0; font-size: 13.5px; line-height: 1.5; color: var(--text-secondary, #706E6B); }
.cw-go {
  flex-shrink: 0; display: inline-flex; align-items: center; gap: 6px;
  height: 34px; padding: 0 14px; border-radius: 10px; border: none;
  background: var(--primary, #181818); color: #fff;
  font-family: inherit; font-size: 13px; font-weight: 700; cursor: pointer;
  transition: transform 0.15s ease, background 0.15s ease;
}
.cw-go:hover { background: var(--primary-deep, #000); transform: translateY(-1px); }
@media (max-width: 700px) {
  .cw-head { flex-wrap: wrap; }
  .cw-foot { flex-direction: column; align-items: stretch; }
}
@media (prefers-reduced-motion: reduce) { .cw, .cw-chip-dot { animation: none; } }
</style>
