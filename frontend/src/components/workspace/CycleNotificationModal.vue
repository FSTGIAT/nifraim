<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="current" class="cn-overlay" @click.self="dismiss">
        <!-- The month's נפרעים are in and production is the agent's part: the
             machine scene (Remotion gears). The agent's FIRST cycle gets the
             assembly intro — the celebration is the machine coming together. -->
        <div
          v-if="isUpload"
          :key="current.id"
          class="cn-card cn-card--gears"
          :class="{ 'cn-card--celebrate': celebrate }"
          role="dialog" aria-modal="true" :aria-label="current.title"
        >
          <header class="cg-head">
            <span class="cg-kicker">
              <span class="cg-kicker-dot" aria-hidden="true"></span>
              {{ celebrate ? 'המחזור הראשון שלך' : 'המחזור החודשי' }} · {{ current.period_label }}
            </span>
            <button class="cn-x" type="button" aria-label="סגור" @click="dismiss">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
            </button>
          </header>
          <div class="cg-stage" @pointerenter="hoverStart" @pointerleave="hoverEnd">
            <RemotionLoopIsland
              component="CycleGears"
              :frames-key="celebrate ? 'CYCLE_GEARS_FRAMES' : 'CYCLE_GEARS_FRAMES_PLAIN'"
              :width="560" :height="320"
              :input-props="gearProps"
            >
              <div class="cg-static" aria-hidden="true">
                <span class="cg-static-g cg-static-g--done">
                  <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
                </span>
                <span class="cg-static-g cg-static-g--now">
                  <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 17V5M6 11l6-6 6 6"/></svg>
                </span>
                <span class="cg-static-g"></span>
              </div>
            </RemotionLoopIsland>
          </div>
          <h3 class="cg-title">הורדת דוחות נפרעים <span class="cg-acc">הסתיימה</span></h3>
          <p class="cg-body">
            הנפרעים של {{ current.period_label }} ירדו אוטומטית מכל החברות.
            העלה פרודוקציה באופן ידני<template v-if="autoCycle.date"> — ב-<span class="ltr-number">{{ autoCycle.date }}</span> המערכת תעבור לאוטומציה<template v-if="autoCycle.deadline"> (בתנאי שטופס השיוך יוגש עד <span class="ltr-number">{{ autoCycle.deadline }}</span>)</template></template>.
          </p>
          <footer class="cn-foot">
            <span v-if="queue.length > 1" class="cn-count ltr-number">1/{{ queue.length }}</span>
            <button v-if="queue.length > 1" class="cn-btn cn-btn--ghost" type="button" @click="dismiss">הבא</button>
            <button class="cn-btn cn-btn--primary" type="button" @click="act">
              {{ meta.cta }}
              <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            </button>
          </footer>
        </div>

        <div v-else class="cn-card" role="dialog" aria-modal="true" :aria-label="current.title">
          <header class="cn-head">
            <span class="cn-icon" :class="'cn-icon--' + meta.tone" aria-hidden="true">
              <!-- worker waiting: monitor -->
              <svg v-if="current.kind === 'worker_waiting'" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2"/><path d="M8 21h8M12 17v4"/><path d="M12 7v4l2 1"/></svg>
              <!-- upload production -->
              <svg v-else-if="current.kind === 'upload_production'" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5"/><path d="M12 3v12"/></svg>
              <!-- partial / failed -->
              <svg v-else-if="current.kind === 'cycle_failed'" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3"/><path d="M12 9v4M12 17h.01"/></svg>
              <!-- comparison ready -->
              <svg v-else viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/></svg>
            </span>
            <div class="cn-titles">
              <span class="cn-kicker">המחזור החודשי · {{ current.period_label }}</span>
              <h3 class="cn-title">{{ current.title }}</h3>
            </div>
            <button class="cn-x" type="button" aria-label="סגור" @click="dismiss">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
            </button>
          </header>

          <p class="cn-body">{{ current.body }}</p>

          <footer class="cn-foot">
            <span v-if="queue.length > 1" class="cn-count ltr-number">1/{{ queue.length }}</span>
            <button class="cn-btn cn-btn--ghost" type="button" @click="dismiss">
              {{ queue.length > 1 ? 'הבא' : 'סגור' }}
            </button>
            <button v-if="meta.tab" class="cn-btn cn-btn--primary" type="button" @click="act">
              {{ meta.cta }}
              <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
            </button>
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useCycleStore } from '../../stores/cycle.js'
import RemotionLoopIsland from './RemotionLoopIsland.vue'

const emit = defineEmits(['navigate'])
const cycle = useCycleStore()

const queue = computed(() => cycle.notifications)
const current = computed(() => queue.value[0] || null)

const META = {
  worker_waiting: { tone: 'warn', tab: 'portal-automation', cta: 'למצב המחשב' },
  upload_production: { tone: 'info', tab: 'production', cta: 'להעלאת הפרודוקציה' },
  cycle_failed: { tone: 'warn', tab: 'portal-automation', cta: 'לפרטי ההורדה' },
  comparison_ready: { tone: 'ok', tab: 'comparison', cta: 'להשוואה' },
}
const meta = computed(() => META[current.value?.kind] || { tone: 'info' })

const isUpload = computed(() => current.value?.kind === 'upload_production')
// The agent's FIRST cycle: its period is the month before the first cycle's
// month (string math on the ISO dates — no time-zone drift).
const firstPeriod = computed(() => {
  const iso = cycle.status?.first_cycle_at
  if (!iso) return null
  let [y, m] = iso.slice(0, 7).split('-').map(Number)
  m -= 1
  if (m === 0) { m = 12; y -= 1 }
  return `${y}-${String(m).padStart(2, '0')}-01`
})
const celebrate = computed(() => isUpload.value && !!firstPeriod.value && current.value.period === firstPeriod.value)
const hoverAt = ref({ start: null, end: null })
function hoverStart() { hoverAt.value = { start: Date.now(), end: null } }
function hoverEnd() { if (hoverAt.value.start) hoverAt.value = { ...hoverAt.value, end: Date.now() } }
const gearProps = computed(() => ({
  hoverStartMs: hoverAt.value.start,
  hoverEndMs: hoverAt.value.end,
  celebrate: celebrate.value,
  accent: '#2F73C4', done: '#2E844A', faint: '#A9A6A2', ink: '#181818',
  labelDone: `נפרעים ${(current.value?.period_label || '').split(' ')[0]}`,
  labelNext: 'השוואה',
}))
// When production stops being manual: the cycle (21st) of the month the first
// מסלקה production lands — already scheduled (שיוך submitted), or what a
// submission by the deadline would give. String math, no time-zone drift.
const autoCycle = computed(() => {
  const st = cycle.status || {}
  const iso = st.maslaka_first_auto || st.maslaka_if_submitted_now
  const m = iso ? Number(iso.slice(5, 7)) : null
  const dm = (d) => (d ? `${Number(d.slice(8, 10))}.${Number(d.slice(5, 7))}` : '')
  return {
    date: m ? `21.${m}` : '',
    deadline: st.maslaka_first_auto ? '' : dm(st.maslaka_deadline),
  }
})

function dismiss() {
  if (current.value) cycle.markSeen(current.value.id)
}
function act() {
  const tab = meta.value.tab
  dismiss()
  if (tab) emit('navigate', tab)
}
</script>

<style scoped>
.cn-overlay {
  position: fixed; inset: 0; z-index: 1010;
  display: flex; align-items: center; justify-content: center; padding: 16px;
  background: rgba(24, 24, 24, 0.42);
}
.cn-card {
  width: min(460px, 100%);
  display: flex; flex-direction: column; gap: 16px;
  padding: 22px 22px 18px;
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  box-shadow: var(--shadow-lg, 0 20px 50px rgba(0, 0, 0, 0.18));
  font-family: 'Heebo', sans-serif;
}
/* ── gears variant (upload production) ── */
.cn-card--gears {
  width: min(600px, 100%); gap: 12px; padding: 18px 24px 20px;
  background:
    radial-gradient(120% 70% at 50% 0%, var(--tab-production-wash, rgba(47, 115, 196, 0.1)) 0%, transparent 70%),
    var(--card-bg, #fff);
}
.cn-card--celebrate { animation: cgRise 0.7s cubic-bezier(0.2, 0.9, 0.25, 1.15) both; }
@keyframes cgRise { from { opacity: 0; transform: translateY(18px) scale(0.96); } to { opacity: 1; transform: none; } }
.cg-head { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.cg-kicker {
  display: inline-flex; align-items: center; gap: 8px; padding: 5px 12px; border-radius: 999px;
  background: var(--card-bg, #fff); border: 1px solid var(--border-subtle);
  font-size: 12.5px; font-weight: 700; color: var(--tab-production, #2F73C4);
}
.cg-kicker-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--green, #2E844A); }
.cg-stage { margin: -6px -8px 6px; }
.cg-static { display: flex; align-items: center; justify-content: center; gap: 28px; height: 100%; }
.cg-static-g {
  width: 58px; height: 58px; border-radius: 50%; display: grid; place-items: center;
  border: 2px dashed var(--border-subtle); color: var(--text-muted, #939393);
}
.cg-static-g--done { background: var(--green, #2E844A); border: none; color: #fff; }
.cg-static-g--now { background: var(--tab-production, #2F73C4); border: none; color: #fff; }
.cg-title {
  margin: 0; text-align: center; text-wrap: balance;
  font-size: clamp(22px, 3vw, 28px); font-weight: 900; letter-spacing: -0.03em; line-height: 1.25;
  color: var(--text-primary, #181818);
}
.cg-acc { color: var(--tab-production, #2F73C4); }
.cg-body { margin: 0; text-align: center; font-size: 15px; line-height: 1.7; color: var(--text-secondary, #5C5A58); text-wrap: pretty; }
.cn-card--gears .cn-foot { justify-content: center; margin-top: 4px; }
@media (prefers-reduced-motion: reduce) { .cn-card--celebrate { animation: none; } }

.cn-head { display: flex; align-items: flex-start; gap: 12px; }
.cn-icon {
  flex-shrink: 0; width: 46px; height: 46px; border-radius: 12px;
  display: inline-flex; align-items: center; justify-content: center;
}
.cn-icon--info { background: var(--primary-light, #F3F3F3); color: var(--primary, #181818); }
.cn-icon--warn { background: var(--amber-light, #FBF4DC); color: var(--amber, #8A6300); }
.cn-icon--ok { background: rgba(46, 132, 74, 0.1); color: var(--green, #2E844A); }
.cn-titles { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.cn-kicker { font-size: 12px; font-weight: 700; color: var(--text-secondary, #706E6B); }
.cn-title { margin: 0; font-size: 18px; font-weight: 800; line-height: 1.3; color: var(--text-primary, #181818); }
.cn-x {
  flex-shrink: 0; width: 32px; height: 32px; border: none; border-radius: 8px;
  display: inline-flex; align-items: center; justify-content: center;
  background: transparent; color: var(--text-secondary, #706E6B); cursor: pointer;
}
.cn-x:hover { background: var(--bg, #F3F3F3); color: var(--text-primary, #181818); }
.cn-body { margin: 0; font-size: 15px; line-height: 1.75; color: var(--text-primary, #3E3E3C); }
.cn-foot { display: flex; align-items: center; justify-content: flex-end; gap: 10px; }
.cn-count { margin-inline-end: auto; font-size: 12px; color: var(--text-secondary, #706E6B); }
.cn-btn {
  display: inline-flex; align-items: center; gap: 8px;
  height: 40px; padding: 0 18px; border-radius: 10px;
  font-family: inherit; font-size: 14px; font-weight: 700; cursor: pointer;
  transition: transform 0.15s ease, background 0.15s ease;
}
.cn-btn--ghost { background: transparent; border: 1px solid var(--border-subtle); color: var(--text-primary, #181818); }
.cn-btn--ghost:hover { background: var(--bg, #F3F3F3); }
.cn-btn--primary { border: none; background: var(--primary, #181818); color: #fff; box-shadow: 0 4px 12px rgba(24, 24, 24, 0.18); }
.cn-btn--primary:hover { background: var(--primary-deep, #000); transform: translateY(-1px); }
</style>
