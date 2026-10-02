<template>
  <!-- Why the comparison's customer count differs from the production tab
       (QA 2026-10-01: "683 in production, 737 here — duplicates?"). A visual
       bridge, not a paragraph: each step is a row with a bar to scale, its
       signed count and the companies behind it. Numbers come from the
       backend's `summary.population`, never re-derived here.
       mode="total" — the whole bridge (סה״כ לקוחות KPI)
       mode="only"  — the header of the "רק בנפרעים" list -->
  <div class="cb" :class="'cb--' + mode">
    <template v-if="mode === 'total'">
      <!-- An equation of tiles — production, minus what isn't checked, plus
           the נפרעים-only, equals this tab's total. No bars (QA 2026-10-01). -->
      <div class="cq">
        <template v-for="(t, i) in tiles" :key="t.key">
          <span v-if="i" class="cq-op" :class="'cq-op--' + t.op" aria-hidden="true">{{ OPS[t.op] }}</span>
          <div class="cq-tile" :class="'cq-tile--' + t.kind" :style="{ '--d': i * 90 + 'ms' }">
            <span class="cq-lbl">{{ t.label }}</span>
            <span class="cq-num ltr-number">{{ t.value.toLocaleString() }}</span>
            <span v-if="t.sub" class="cq-sub">{{ t.sub }}</span>
          </div>
        </template>
      </div>
      <!-- Company breakdowns BELOW the equation, full width — inside the tiles
           they stretched every tile and left empty space (QA 2026-10-01). -->
      <section v-for="t in tiles.filter(x => x.companies && Object.keys(x.companies).length)"
               :key="'co-' + t.key" class="cq-sec" :class="'cq-sec--' + t.kind">
        <h4><span class="ltr-number">{{ t.value.toLocaleString() }}</span> {{ t.label }} — לפי חברה</h4>
        <ul class="cq-cos">
          <li v-for="[co, n] in byCount(t.companies)" :key="co">
            <span class="cq-co"><CompanyLogo :company="co" :size="16" :frame="false" />{{ co }}</span>
            <b class="ltr-number">{{ n.toLocaleString() }}</b>
          </li>
        </ul>
      </section>
    </template>

    <template v-else>
      <div class="cb-hero">
        <span class="cb-hero-num ltr-number">{{ pop.commission_only.toLocaleString() }}</span>
        <span class="cb-hero-txt">
          <b>החברה משלמת עליהם עמלה</b>
          <span>אבל הם לא מופיעים בקובץ הפרודוקציה</span>
        </span>
      </div>
      <div v-if="cos.length" class="cb-split" role="img" :aria-label="'לפי חברה'">
        <span v-for="(c, i) in cos" :key="c.name" class="cb-seg"
              :style="{ flex: c.n, '--c': palette[i % palette.length], '--d': i * 70 + 'ms' }"
              :title="c.name + ' ' + c.n"></span>
      </div>
      <span class="cb-cos">
        <span v-for="(c, i) in cos" :key="c.name" class="cb-co">
          <i :style="{ background: palette[i % palette.length] }"></i>{{ c.name }}
          <b class="ltr-number">{{ c.n }}</b>
        </span>
      </span>
      <div class="cb-why">
        <span class="cb-why-lbl">למה זה קורה</span>
        <span class="cb-pill">קובץ הפרודוקציה של החברה חסר או חלקי</span>
        <span class="cb-pill">לקוח ותיק שעדיין מניב עמלה</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import CompanyLogo from '../workspace/CompanyLogo.vue'
import { CHART_PALETTE } from '../../utils/chartPalette'

const props = defineProps({
  population: { type: Object, required: true },
  mode: { type: String, default: 'total' },
  // matched / unpaid split of the judged customers — the KPIs' own counts
  paid: { type: Number, default: 0 },
  unpaid: { type: Number, default: 0 },
})

const pop = computed(() => props.population || {})
const palette = CHART_PALETTE

// Largest first — stored JSONB does not keep the backend's key order.
const byCount = o => Object.entries(o || {}).sort((a, b) => b[1] - a[1])
const OPS = { minus: '−', plus: '+', eq: '=' }
const tiles = computed(() => {
  const p = pop.value
  const out = [{ key: 'prod', kind: 'base', label: 'בקובץ הפרודוקציה', value: p.production || 0 }]
  if (p.empty_funds) {
    out.push({ key: 'empty', kind: 'minus', op: 'minus', label: 'קופות ריקות או לא פעילות',
      value: p.empty_funds, companies: p.empty_funds_by_company })
  }
  if (p.not_judged) {
    out.push({ key: 'nj', kind: 'minus', op: 'minus', label: 'בלי דוח נפרעים מהחברה',
      value: p.not_judged, companies: p.not_judged_by_company })
  }
  const extra = (p.commission_only || 0) + (p.production_but_commission_only || 0)
  if (extra) {
    out.push({ key: 'only', kind: 'plus', op: 'plus', label: 'רק בנפרעים',
      value: extra, companies: p.commission_only_by_company })
  }
  out.push({ key: 'total', kind: 'total', op: 'eq', label: 'בהשוואה', value: p.total || 0,
    sub: props.paid || props.unpaid
      ? `${props.paid.toLocaleString()} שולמו · ${props.unpaid.toLocaleString()} לא שולמו` : '' })
  return out
})

const cos = computed(() => byCount(pop.value.commission_only_by_company)
  .map(([name, n]) => ({ name, n })))
</script>

<style scoped>
.cb { --acc: var(--tab-comparison); display: flex; flex-direction: column; gap: 12px; }

/* ── equation ── */
/* An equation reads left → right (QA 2026-10-01): the ROW is LTR, the
   Hebrew inside each tile stays RTL. */
.cq { display: flex; align-items: stretch; gap: 10px; direction: ltr; }
.cq-tile { direction: rtl; }
.cq-tile {
  flex: 1 1 0; min-width: 0; display: flex; flex-direction: column; gap: 6px;
  padding: 18px 16px; border-radius: 16px; background: var(--card-bg); border: 1px solid var(--border-subtle);
  animation: cbIn 0.45s cubic-bezier(0.2, 0, 0.2, 1) both; animation-delay: var(--d);
  --tone: var(--text);
}
.cq-tile--base { --tone: var(--tab-production); }
.cq-tile--minus { --tone: var(--text-muted); }
.cq-tile--plus { --tone: var(--tab-portal-ink, #35719A); }
.cq-tile--total { --tone: var(--acc); background: color-mix(in srgb, var(--acc) 8%, var(--card-bg)); border-color: transparent; }
.cq-tile { align-items: center; text-align: center; }
.cq-lbl { font-size: 13.5px; font-weight: 700; color: var(--text-muted); }
.cq-num { font-size: 46px; font-weight: 900; color: var(--tone); letter-spacing: -1.5px; line-height: 1.05; }
.cq-sub { font-size: 12.5px; color: var(--text-muted); }
.cq { align-items: center; }
.cq-tile { padding: 16px 14px; align-self: stretch; justify-content: center; }
.cq-sec { display: flex; flex-direction: column; gap: 8px; }
.cq-sec h4 { margin: 0; font-size: 13px; font-weight: 700; color: var(--text-muted); }
.cq-sec h4 span { color: var(--tone, var(--text)); font-weight: 800; }
.cq-sec--plus { --tone: var(--tab-portal-ink, #35719A); }
.cq-sec--minus { --tone: var(--text-muted); }
.cq-cos {
  list-style: none; margin: 0; padding: 0; text-align: right;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 6px;
}
.cq-cos li {
  display: flex; align-items: center; justify-content: space-between; gap: 8px;
  padding: 8px 12px; border-radius: 10px; background: var(--bg); font-size: 13px;
}
.cq-co { display: inline-flex; align-items: center; gap: 7px; font-weight: 600; color: var(--text); }
.cq-cos b { font-weight: 800; color: var(--text-muted); }
.cq-op {
  flex: 0 0 auto; align-self: center; width: 30px; height: 30px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--bg); color: var(--text-muted); font-size: 18px; font-weight: 800;
}
.cq-op--eq { background: color-mix(in srgb, var(--acc) 14%, transparent); color: var(--acc); }
@media (max-width: 760px) {
  .cq { flex-direction: column; }
  .cq-op { align-self: center; }
}

.cb-cos { display: flex; flex-wrap: wrap; gap: 6px; }
.cb-co {
  display: inline-flex; align-items: center; gap: 5px; height: 26px; padding: 0 9px; border-radius: 13px;
  background: var(--bg); font-size: 12px; font-weight: 600; color: var(--text);
}
.cb-co b { font-weight: 800; color: var(--text-muted); }
.cb-co i { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }

/* ── "only in נפרעים" header ── */
.cb--only { padding: 14px 16px; border-radius: 14px; background: color-mix(in srgb, var(--tab-portal, #4E9DD0) 8%, var(--card-bg)); }
.cb-hero { display: flex; align-items: center; gap: 14px; }
.cb-hero-num { font-size: 34px; font-weight: 900; color: var(--tab-portal-ink, #35719A); letter-spacing: -1px; line-height: 1; }
.cb-hero-txt { display: flex; flex-direction: column; gap: 2px; }
.cb-hero-txt b { font-size: 15px; font-weight: 700; color: var(--text); }
.cb-hero-txt span { font-size: 13px; color: var(--text-muted); }
.cb-split { display: flex; gap: 3px; height: 10px; }
.cb-seg {
  border-radius: 5px; background: var(--c); transform-origin: right center;
  animation: cbGrow 0.8s cubic-bezier(0.22, 1, 0.36, 1) both; animation-delay: var(--d);
}
.cb-why { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.cb-why-lbl { font-size: 12px; font-weight: 700; color: var(--text-muted); }
.cb-pill {
  font-size: 12px; padding: 4px 10px; border-radius: 12px; background: var(--card-bg);
  border: 1px solid var(--border-subtle); color: var(--text);
}

@keyframes cbIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@keyframes cbGrow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
@media (prefers-reduced-motion: reduce) {
  .cq-tile, .cb-seg { animation: none; }
}
</style>
