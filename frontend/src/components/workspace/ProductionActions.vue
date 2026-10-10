<template>
  <!-- "דורש טיפול" — the first thing under the KPIs. Everything the tab knows
       that needs the agent's hand, one line each, worst first, each opening the
       drill that answers it. Before this the same findings were spread over
       three cards halfway down a 3,500px page and read at the weight of every
       other card (QA 2026-09-30: "users go lost there"). -->
  <section v-if="ready" class="pact" :class="{ 'pact--clear': !items.length }">
    <!-- The whole header is the toggle: the agent can fold the list away and
         keep only the count (QA 2026-09-30). Remembered per viewer. -->
    <button class="pact-head" type="button" :aria-expanded="open" @click="toggle">
      <h3 :class="{ 'pact-flicker': items.length }">{{ items.length ? 'דורש טיפול' : 'הכל תקין החודש' }}</h3>
      <span v-if="items.length" class="pact-count pact-flicker ltr-number">{{ items.length }}</span>
      <span v-if="period" class="pact-period ltr-number">נפרעים {{ period }}</span>
      <svg class="pact-chev" :class="{ 'pact-chev--open': open }" width="16" height="16"
           viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"
           stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <polyline points="6 9 12 15 18 9" />
      </svg>
    </button>

    <div class="pact-fold" :class="{ 'pact-fold--open': open }">
    <div class="pact-fold-inner">
    <p v-if="!items.length" class="pact-clear">
      כל החברות שדיווחו שילמו לפי ההסכם, ואין לקוחות ללא תשלום.
    </p>

    <ul v-else class="pact-list">
      <li v-for="(it, i) in items" :key="it.key" :style="{ '--d': i * 50 + 'ms' }">
        <button class="pact-row" :class="['pact-row--' + it.level, { 'pact-row--hl': it.highlight }]" :disabled="!it.open"
                @click="it.open && $emit('open', { ...it.open, el: $event.currentTarget })">
          <span class="pact-icon" aria-hidden="true">
            <svg v-if="it.level === 'loss'" width="16" height="16" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="5" x2="12" y2="19" /><polyline points="19 12 12 19 5 12" />
            </svg>
            <svg v-else-if="it.level === 'warn'" width="16" height="16" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="16" x2="12" y2="12" />
              <line x1="12" y1="8" x2="12.01" y2="8" />
            </svg>
          </span>
          <span class="pact-body">
            <span class="pact-title">{{ it.title }}</span>
            <span v-if="it.sub" class="pact-sub">{{ it.sub }}</span>
          </span>
          <span v-if="it.amount" class="pact-amt ltr-number">{{ it.amount }}</span>
          <svg v-if="it.open" class="pact-go" width="14" height="14" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"
               aria-hidden="true"><polyline points="15 18 9 12 15 6" /></svg>
        </button>
      </li>
    </ul>
    </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { cachedGet } from '../../utils/cachedGet'
import { signedMoney } from '../../utils/chartDefaults'
import { useCycleStore, judgedMonthsLine, nextNifraimLine, newerProductionLine } from '../../stores/cycle.js'

const cycleStore = useCycleStore()

defineEmits(['open'])

// Same thresholds as the agreement panel — a gap is named only past both.
const GAP_MIN_PCT = 10
const GAP_MIN_SHEKEL = 100

const alerts = ref(null)
const audit = ref(null)
const ready = ref(false)

const period = computed(() => audit.value?.period || null)

// Always starts CLOSED (QA 2026-09-30) — the header keeps the count visible.
// Not remembered: a remembered "open" read as the default being wrong.
const open = ref(false)
function toggle() {
  open.value = !open.value
}

const items = computed(() => {
  const out = []
  const a = alerts.value || {}
  const companies = audit.value?.companies || []

  // Name the months that were compared, and when the next נפרעים run moves
  // the verdict (kiko 2026-10-10: "החודש" in October meant July vs July).
  const months = judgedMonthsLine(a.judged_production_period, a.judged_nifraim_period)
  const next = nextNifraimLine(cycleStore.status)
  // Responses from before the split carry only unpaid_total.
  const full = a.unpaid_full_total ?? a.unpaid_total ?? 0
  const partial = a.unpaid_partial_total ?? 0
  if (full) {
    out.push({
      key: 'unpaid', level: 'loss',
      title: `${full} לקוחות בלי תשלום עמלה`,
      sub: [months, 'לא התקבל תשלום על אף מוצר שלהם'].filter(Boolean).join(' · '),
      open: { kind: 'unpaid', filter: 'full' },
    })
  }
  if (partial) {
    out.push({
      key: 'unpaid-partial', level: 'warn',
      title: `${partial} לקוחות שולמו חלקית`,
      sub: [months, 'התקבלה עמלה על חלק מהמוצרים, על אחרים לא'].filter(Boolean).join(' · '),
      open: { kind: 'unpaid', filter: 'partial' },
    })
  }
  // Newer production with no נפרעים yet → say it; else when the next run is.
  const newer = newerProductionLine(a.newer_production, cycleStore.status, a.judged_nifraim_period)
  if (newer) {
    out.push({ key: 'newer-production', level: 'info', title: newer.title, sub: newer.sub, highlight: true })
  } else if ((full || partial) && next) {
    out.push({ key: 'next-nifraim', level: 'info', title: next })
  }

  // Paid below the agreement, biggest first, each naming its worst product —
  // the product is what the agent quotes to the insurer.
  const losses = companies
    .filter(c => c.comparable && c.gap < 0 && Math.abs(c.gap) >= GAP_MIN_SHEKEL
      && Math.abs(c.gap_pct || 0) >= GAP_MIN_PCT)
    .sort((x, y) => x.gap - y.gap)
  for (const c of losses) {
    const worst = (c.products || [])
      .filter(p => p.firm && p.expected > 0 && /\p{L}/u.test(p.product || ''))
      .sort((x, y) => (x.paid - x.expected) - (y.paid - y.expected))[0]
    out.push({
      key: 'gap-' + c.company, level: 'loss',
      title: `${c.company} שילמה פחות מההסכם`,
      sub: worst ? `בעיקר ב"${worst.product}"` : `${Math.abs(c.gap_pct)}% מתחת להסכם`,
      amount: signedMoney(c.gap),
      open: { kind: 'company', company: c.company },
    })
  }

  const notReported = companies.filter(c => c.no_commission_data).map(c => c.company)
  if (notReported.length) {
    out.push({
      key: 'noreport', level: 'warn',
      title: `${notReported.join(', ')} — לא התקבל דוח נפרעים`,
      sub: 'אי אפשר לבדוק את הלקוחות שלהן עד שהדוח יגיע',
      open: { kind: 'checked' },
    })
  }

  const noValue = (a.no_value_companies || []).map(c => c.company)
  if (noValue.length) {
    out.push({
      key: 'novalue', level: 'warn',
      title: `${noValue.join(', ')} — פרודוקציה בלי סכומים`,
      sub: 'יש שורות אבל אין בהן פרמיה או צבירה; בדוק את ההורדה האוטומטית',
    })
  }

  const noAgreement = companies.filter(c => c.no_agreement && c.paid > 0)
  if (noAgreement.length) {
    out.push({
      key: 'noagr', level: 'info',
      title: `${noAgreement.length} חברות בלי הסכם עמלות`,
      sub: noAgreement.map(c => c.company).join(', ') + ' — אי אפשר לבדוק אם שילמו נכון',
      open: { kind: 'explain' },
    })
  }
  return out
})

onMounted(async () => {
  if (!cycleStore.loaded) cycleStore.fetchStatus()
  const [al, au] = await Promise.allSettled([
    cachedGet('/production/alerts'),
    cachedGet('/production/rate-audit'),
  ])
  alerts.value = al.status === 'fulfilled' ? al.value.data : null
  audit.value = au.status === 'fulfilled' ? au.value.data : null
  // Nothing loaded → say nothing, rather than a false "all clear".
  ready.value = !!(alerts.value || audit.value)
})
</script>

<style scoped>
.pact {
  position: relative; isolation: isolate;
  background: var(--card-bg); border: 1px solid var(--border-subtle);
  border-radius: 14px; padding: 12px 18px; box-shadow: var(--shadow-sm);
}
/* Hovering the header fills the card slowly, right (RTL start) to left, with the tab's light blue */
.pact::before {
  content: ''; position: absolute; inset: 0; z-index: -1; pointer-events: none;
  border-radius: inherit;
  background: var(--tab-production-wash);
  transform: scaleX(0); transform-origin: right center;
  transition: transform 1.4s cubic-bezier(0.25, 0.1, 0.25, 1);
}
.pact:has(.pact-head:hover)::before { transform: scaleX(1); }
.pact-head {
  width: 100%; display: flex; align-items: center; gap: 10px;
  background: none; border: none; padding: 0; font: inherit; color: inherit;
  cursor: pointer; text-align: right;
}
.pact-head:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 4px; border-radius: 6px; }
.pact-chev { color: var(--text-muted); transition: transform 0.25s ease; flex: 0 0 auto; }
.pact-chev--open { transform: rotate(180deg); }
.pact-head:hover .pact-chev { color: var(--tab-production); }
/* Height animates through a 0fr→1fr grid row — no measured max-height. */
.pact-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.3s cubic-bezier(0.2, 0, 0.2, 1); }
.pact-fold--open { grid-template-rows: 1fr; }
.pact-fold-inner { overflow: hidden; min-height: 0; }
.pact-fold--open .pact-fold-inner { padding-top: 12px; }
.pact-head h3 { font-size: 16px; font-weight: 700; color: var(--text); }
/* "דורש טיפול" + its count flicker briefly once a minute (first ~1.2s of each 60s cycle) */
.pact-flicker { animation: pactFlicker 60s ease-in-out infinite; }
@keyframes pactFlicker {
  0%, 2%, 100% { opacity: 1; }
  0.25% { opacity: 0.25; }
  0.5% { opacity: 1; }
  0.75% { opacity: 0.35; }
  1% { opacity: 1; }
}
.pact-count {
  min-width: 22px; height: 22px; padding: 0 7px; border-radius: 11px;
  background: var(--red); color: #fff; font-size: 12px; font-weight: 700;
  display: inline-flex; align-items: center; justify-content: center;
}
.pact-period { margin-inline-start: auto; font-size: 12px; color: var(--text-muted); }
.pact--clear .pact-head h3 { color: var(--green); }
.pact-clear { font-size: 13px; color: var(--text-muted); }

.pact-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.pact-list li { animation: pactIn 0.4s cubic-bezier(0.2, 0, 0.2, 1) both; animation-delay: var(--d); }
@keyframes pactIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }

.pact-row {
  width: 100%; display: flex; align-items: center; gap: 12px;
  padding: 10px 12px; border-radius: 10px; border: 1px solid var(--border-subtle);
  background: var(--card-bg); font: inherit; text-align: right; color: var(--text);
  cursor: pointer; transition: border-color 0.15s ease, background 0.15s ease, transform 0.15s ease;
}
.pact-row:not(:disabled):hover { border-color: var(--tab-production); background: var(--tab-production-wash); }
.pact-row:not(:disabled):active { transform: scale(0.995); }
.pact-row:disabled { cursor: default; }
.pact-row:focus-visible { outline: 2px solid var(--tab-production); outline-offset: 2px; }

.pact-icon {
  flex: 0 0 32px; height: 32px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
}
.pact-row--loss .pact-icon { color: var(--red); background: color-mix(in srgb, var(--red) 12%, transparent); }
.pact-row--warn .pact-icon { color: var(--amber); background: var(--amber-light); }
.pact-row--info .pact-icon { color: var(--text-muted); background: var(--bg); }
/* "No נפרעים yet for the new month" — the line the agent must not miss:
   a tinted card that breathes softly in the tab's colour (like "לא שולם"). */
.pact-row--hl {
  border-color: color-mix(in srgb, var(--tab-production) 45%, transparent);
  background: color-mix(in srgb, var(--tab-production) 7%, var(--card-bg));
  animation: pactBreath 3s ease-in-out infinite;
}
.pact-row--hl .pact-icon { color: var(--tab-production); background: color-mix(in srgb, var(--tab-production) 13%, var(--card-bg)); }
.pact-row--hl .pact-title { color: var(--tab-production); }
@keyframes pactBreath {
  0%, 100% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--tab-production) 0%, transparent); }
  50% { box-shadow: 0 0 0 5px color-mix(in srgb, var(--tab-production) 14%, transparent), 0 8px 20px color-mix(in srgb, var(--tab-production) 16%, transparent); }
}
@media (prefers-reduced-motion: reduce) { .pact-row--hl { animation: none; } }

.pact-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.pact-title { font-size: 14px; font-weight: 600; }
.pact-sub { font-size: 12px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pact-amt { font-size: 15px; font-weight: 700; color: var(--red); white-space: nowrap; }
.pact-go { color: var(--text-muted); flex: 0 0 auto; }

@media (max-width: 640px) {
  .pact { padding: 14px; }
  .pact-sub { white-space: normal; }
}
@media (prefers-reduced-motion: reduce) {
  .pact-list li, .pact-flicker { animation: none; }
  .pact-row, .pact-fold, .pact-chev, .pact::before { transition: none; }
}
</style>
