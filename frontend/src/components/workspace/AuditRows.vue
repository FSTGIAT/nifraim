<template>
  <ul class="ar">
    <li v-for="(c, i) in rows" :key="c.company"
        class="ar-row" :class="{ 'ar-row--in': shown, 'ar-row--flat': !c.comparable }"
        :style="{ transitionDelay: (i * 40) + 'ms' }"
        @click="c.comparable && $emit('pick', c)">
      <span class="ar-name" :title="c.company">{{ c.company }}</span>

      <!-- Two bars on ONE scale across ALL companies, so a row can be compared
           with the row above it as well as within itself. Paid sits above
           agreed: the question is "did what arrived match what was owed", and
           stacking them makes that a vertical comparison at a glance. -->
      <span v-if="c.comparable" class="ar-track">
        <span class="ar-bar ar-bar--paid" :style="{ width: pct(c.paid_firm) }"></span>
        <span class="ar-bar ar-bar--agreed" :style="{ width: pct(c.expected_firm) }"></span>
      </span>
      <span v-else class="ar-track ar-track--none">
        <!-- The reason is the actionable part of the row, so it behaves like
             one: it names WHY the company can't be compared and opens the list
             of everyone in the same position, with what it would take to fix. -->
        <button class="ar-reason" :class="{ 'ar-reason--missing': c.no_commission_data }"
                @click.stop="$emit('explain', c)">
          {{ reasonText(c) }}
          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" /><path d="M12 16v-4M12 8h.01" />
          </svg>
        </button>
      </span>

      <span class="ar-amt ltr-number">{{ money(c.comparable ? c.paid_firm : c.paid) }}</span>
      <span class="ar-gap ltr-number" :class="gapTone(c)">
        {{ c.comparable ? signedMoney(c.gap) : '—' }}
      </span>
    </li>
  </ul>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { money, signedMoney } from '../../utils/chartDefaults'

// A gap is worth colouring only past BOTH thresholds — insurers round, and a
// commission can straddle a month boundary. Mirrors the comparison engine.
const GAP_MIN_PCT = 10
const GAP_MIN_SHEKEL = 100

const props = defineProps({ rows: { type: Array, default: () => [] } })
defineEmits(['pick', 'explain'])

// Three distinct reasons a company can't be compared, and the agent acts on
// each differently. They used to render as one sentence:
//
//   no_commission_data → the נפרעים report never arrived this period. This row
//                        exists at all because the panel is built from נפרעים
//                        rows, so such a company used to VANISH — live, הראל
//                        has 1,729 production rows and 53 agreement rows and
//                        was simply absent, indistinguishable from "not mine".
//   no_agreement       → select_rate found no agreement row for this insurer
//                        (route "none") → upload an agreement.
//   no_sane_rate       → the agreement exists but every rate failed the
//                        magnitude guards → the rate is there but unusable.
function reasonText(c) {
  if (c.no_commission_data) return 'לא התקבלו נפרעים החודש'
  if (c.no_rate_reason === 'no_sane_rate') return 'אין שיעור למוצרים שלה'
  if (c.no_agreement) return 'אין הסכם עמלות'
  return 'אין שיעור למוצרים שלה'
}

const shown = ref(false)

const max = computed(() => Math.max(
  1,
  ...props.rows.flatMap(c => [Number(c.paid_firm) || 0, Number(c.expected_firm) || 0]),
))

function pct(v) {
  if (!shown.value) return '0%'
  // 1.5% floor so a small-but-real figure is still a mark, not nothing.
  return Math.max(1.5, (Math.abs(Number(v) || 0) / max.value) * 100) + '%'
}

function gapTone(c) {
  if (!c.comparable || c.gap_pct === null) return 'is-none'
  if (Math.abs(c.gap_pct) < GAP_MIN_PCT || Math.abs(c.gap) < GAP_MIN_SHEKEL) return 'is-none'
  return c.gap < 0 ? 'is-down' : 'is-up'
}

onMounted(() => { requestAnimationFrame(() => { shown.value = true }) })
</script>

<style scoped>
.ar { list-style: none; display: flex; flex-direction: column; }

.ar-row {
  display: grid;
  grid-template-columns: minmax(64px, 110px) 1fr 84px 84px;
  align-items: center; gap: 12px;
  padding: 9px 8px; border-radius: var(--radius-sm);
  border-bottom: 1px solid var(--border-subtle);
  cursor: pointer;
}
.ar-row:last-child { border-bottom: none; }
.ar-row:hover { background: var(--border-subtle); }
.ar-row--flat { cursor: default; }
.ar-row--flat:hover { background: none; }

.ar-name {
  font-size: 13px; font-weight: 600; color: var(--text);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.ar-track { display: flex; flex-direction: column; gap: 3px; direction: ltr; }
.ar-bar {
  display: block; height: 9px; border-radius: 4px;
  transition: width 0.55s cubic-bezier(0.2, 0, 0.2, 1);
}
.ar-bar--paid { background: var(--chart-9); }
/* Agreed is the reference, not a competing series — it recedes. */
.ar-bar--agreed { background: var(--text-muted); opacity: 0.38; }

.ar-track--none { justify-content: center; }
.ar-reason {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 3px 9px; border-radius: 11px;
  border: 1px solid var(--border-subtle); background: none;
  color: var(--text-muted); font-family: inherit; font-size: 11px;
  cursor: pointer; align-self: flex-start;
}
.ar-reason:hover { color: var(--text); border-color: var(--text-muted); }

/* A missing report is not the same class of problem as a missing agreement —
   one is a failed download to retry, the other is paperwork to upload. */
.ar-reason--missing {
  color: var(--amber);
  border-color: currentColor;
  opacity: 0.85;
}
.ar-reason--missing:hover { color: var(--amber); opacity: 1; }

.ar-amt { font-size: 13px; font-weight: 700; color: var(--text); text-align: left; }
.ar-gap { font-size: 13px; font-weight: 700; text-align: left; }
.ar-gap.is-up { color: var(--chart-gain); }
.ar-gap.is-down { color: var(--chart-loss); }
.ar-gap.is-none { color: var(--text-muted); font-weight: 500; }

@media (prefers-reduced-motion: reduce) { .ar-bar { transition: none; } }
</style>
