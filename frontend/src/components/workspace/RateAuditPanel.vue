<template>
  <div v-if="companies.length" class="ra-card">
    <div class="ra-head">
      <h3>עמלות בפועל מול ההסכמים</h3>
      <span v-if="period" class="ra-period ltr-number">{{ period }}</span>
    </div>
    <p class="ra-sub">מה שכל חברה שילמה בפועל, מול מה שאמורה הייתה לשלם לפי אחוזי ההסכם.</p>

    <!-- Anything needing action is stated before the chart. A panel that opens
         with a plot makes the reader hunt for the problem. -->
    <ul v-if="alerts.length" class="ra-alerts">
      <li v-for="a in alerts" :key="a.key" class="ra-alert" :class="'ra-alert--' + a.level">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <span>{{ a.text }}</span>
      </li>
    </ul>

    <!-- One list, not a chart plus a separate list underneath. Companies that
         cannot be compared were rendered in a different visual language from
         the ones that could, so the panel read as two unrelated blocks. -->
    <div class="ra-legend">
      <span><i class="ra-key ra-key--paid"></i>שולם בפועל</span>
      <span><i class="ra-key ra-key--agreed"></i>לפי ההסכם</span>
      <span class="ra-legend-hint">בחר חברה לפירוט לפי מוצר</span>
    </div>
    <AuditRows :rows="companies" @pick="openCompany = $event"
               @explain="explainOpen = true" />

    <button class="ra-all" @click="tableOpen = true">הצג את כל הנתונים</button>

    <DataModal :open="!!openCompany"
               :title="openCompany ? openCompany.company + ' — לפי מוצר' : ''"
               :subtitle="openCompany ? `${openCompany.products.length} מוצרים` : ''"
               @close="openCompany = null">
      <ProductRows v-if="openCompany" :products="openCompany.products" />
    </DataModal>

    <!-- Who cannot be checked, and what would make them checkable. -->
    <DataModal :open="explainOpen" title="חברות שאי אפשר להשוות" @close="explainOpen = false">
      <p class="ra-explain-lead">
        השוואה בין מה ששולם למה שמגיע דורשת שיעור עמלה מפורש בהסכם. לחברות האלה
        התקבלו עמלות, אבל אין מולן שיעור לבדוק אותן — הסכום שהתקבל מוצג, ואי אפשר
        לדעת אם הוא נכון.
      </p>
      <ul class="ra-explain">
        <li v-for="c in notComparable" :key="c.company">
          <span class="ra-ex-co">{{ c.company }}</span>
          <span class="ra-ex-amt ltr-number">{{ money(c.paid) }}</span>
          <span class="ra-ex-why">
            <template v-if="c.no_agreement">אין הסכם עמלות במערכת</template>
            <template v-else>
              יש הסכם, אך אין בו שיעור למוצרים האלה:
              <!-- Naming them is the difference between a status and a task. -->
              <strong class="ra-ex-prods">{{ (c.unrated_products || []).join(' · ') }}</strong>
            </template>
          </span>
        </li>
      </ul>
      <p class="ra-explain-foot">
        להוספת הסכם: לשונית <strong>טבלת עמלות</strong> — העלאת מסמך ההסכם, והמערכת
        תחלץ ממנו את שיעורי העמלה.
      </p>
    </DataModal>

    <DataModal :open="tableOpen" title="עמלות בפועל מול ההסכמים — כל הנתונים" @close="tableOpen = false">
      <table class="ra-table">
        <thead>
          <tr>
            <th>חברה</th><th>סך שולם</th><th>מתוכו להשוואה</th>
            <th>לפי ההסכם</th><th>הפרש</th><th>אחוז בפועל</th><th>אחוז בהסכם</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="c in companies" :key="c.company">
            <td>
              {{ c.company }}
              <span v-if="c.no_agreement" class="ra-tag">אין הסכם</span>
              <span v-else-if="!c.comparable" class="ra-tag">אין שיעור למוצרים</span>
              <span v-else-if="c.rows_estimated" class="ra-tag ltr-number">
                {{ c.rows_estimated }} ללא שיעור מדויק
              </span>
              <span v-if="!c.vat_verified && c.paid > 0" class="ra-tag" :title="c.vat_reason">
                מע"מ לא מאומת
              </span>
            </td>
            <td class="ra-num"><span class="ltr-number">{{ money(c.paid) }}</span></td>
            <!-- Same rows on both sides, or the pair invites a wrong read:
                 מור paid ₪18,738 overall but only ₪2,030 sits on rows with a
                 product-level rate, where the real gap is −0.6%. -->
            <td class="ra-num"><span v-if="c.comparable" class="ltr-number">{{ money(c.paid_firm) }}</span><span v-else class="ra-dash">—</span></td>
            <td class="ra-num"><span v-if="c.comparable" class="ltr-number">{{ money(c.expected_firm) }}</span><span v-else class="ra-dash">—</span></td>
            <td class="ra-num">
              <span v-if="c.comparable" class="ltr-number" :class="gapClass(c)">{{ signedMoney(c.gap) }}</span>
              <span v-else class="ra-dash">—</span>
            </td>
            <td class="ra-num"><span class="ltr-number">{{ pct(c.comparable ? c.implied_rate : c.implied_rate_all) }}</span></td>
            <td class="ra-num"><span v-if="c.comparable" class="ltr-number">{{ pct(c.effective_agreed_rate) }}</span><span v-else class="ra-dash">—</span></td>
          </tr>
        </tbody>
      </table>
      <p class="ra-foot">
        <span class="ra-est">≈</span> מסמן מוצר שחלק משורותיו אינן נושאות שיעור עמלה מפורש
        בהסכם. שיעור שנגזר מברירת מחדל או מחציון אינו טענה על חוב, ולכן אינו נכלל בהפרש
        שבראש המסך.
      </p>
    </DataModal>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../../api/client'
import DataModal from './DataModal.vue'
import AuditRows from './AuditRows.vue'
import ProductRows from './ProductRows.vue'
import { money, signedMoney, pct } from '../../utils/chartDefaults'

// A gap is worth naming only past BOTH thresholds — insurers round, and a
// commission can straddle a month boundary. Mirrors the comparison engine.
const GAP_MIN_PCT = 10
const GAP_MIN_SHEKEL = 100

const ESTIMATE_HINT = 'כל השורות במוצר זה מתומחרות בשיעור ברירת מחדל — אין כאן טענה על חוב'

const companies = ref([])
const period = ref(null)
const openCompany = ref(null)
const tableOpen = ref(false)
const explainOpen = ref(false)

const notComparable = computed(() => companies.value.filter(c => !c.comparable && c.paid > 0))

function gapClass(c) {
  if (!c.comparable || c.gap_pct === null) return ''
  if (Math.abs(c.gap_pct) < GAP_MIN_PCT || Math.abs(c.gap) < GAP_MIN_SHEKEL) return ''
  return c.gap < 0 ? 'ra-neg' : 'ra-pos'
}
function deltaClass(diff, expected) {
  // Same thresholds as the headline gap. Colouring by sign alone painted a ₪1
  // rounding difference in alarm red — and a diff of −₪0.004 rendered as a red
  // "₪0". Insurers round, and a commission can straddle a month boundary.
  const base = Math.abs(Number(expected) || 0)
  if (Math.abs(diff) < GAP_MIN_SHEKEL) return ''
  if (base && (Math.abs(diff) / base) * 100 < GAP_MIN_PCT) return ''
  return diff < 0 ? 'ra-neg' : 'ra-pos'
}

const alerts = computed(() => {
  const out = []
  const noAgreement = companies.value.filter(c => c.no_agreement && c.paid > 0)
  for (const c of companies.value) {
    if (c.no_agreement || !c.comparable) continue
    if (Math.abs(c.gap_pct) >= GAP_MIN_PCT && Math.abs(c.gap) >= GAP_MIN_SHEKEL) {
      const dir = c.gap < 0 ? 'פחות' : 'יותר'
      // Name the product driving it — "Phoenix is 33% off" sends the agent
      // through 750 rows; naming the product does not.
      // Skip products the source file never named. Menora's rows carry a
      // product column holding "0" and ".5", which produced the alert
      // `שולם ₪1,519 יותר … בעיקר ב"0"` — a sentence that points at nothing.
      const worst = (c.products || [])
        .filter(p => p.estimated === 0 && p.expected > 0
          && p.product && /\p{L}/u.test(p.product))
        .sort((a, b) => Math.abs(b.paid - b.expected) - Math.abs(a.paid - a.expected))[0]
      out.push({
        key: 'gap-' + c.company,
        level: c.gap < 0 ? 'warn' : 'info',
        text: `${c.company}: שולם ${money(Math.abs(c.gap))} ${dir} מהצפוי לפי ההסכם `
          + `(${c.gap_pct > 0 ? '+' : ''}${c.gap_pct}%)${worst ? ` בעיקר ב"${worst.product}"` : ''}.`,
      })
    }
  }
  if (noAgreement.length) {
    const total = noAgreement.reduce((s, c) => s + c.paid, 0)
    out.push({
      key: 'noagr', level: 'info',
      text: `${noAgreement.map(c => c.company).join(', ')}: התקבלו ${money(total)} `
        + `ואין הסכם עמלות במערכת — העלה את ההסכמים כדי שנוכל לבדוק אותם.`,
    })
  }
  return out
})

api.get('/production/rate-audit')
  .then((res) => {
    const all = res.data.companies || []
    companies.value = [
      ...all.filter(c => c.comparable),
      ...all.filter(c => !c.comparable),
    ]
    period.value = res.data.period
  })
  .catch(() => { companies.value = [] })
</script>

<style scoped>
.ra-card {
  background: var(--card-bg); border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md); padding: 20px;
}
.ra-head { display: flex; align-items: baseline; gap: 10px; }
.ra-head h3 { font-size: 15px; font-weight: 700; color: var(--text); }
.ra-period { font-size: 12px; color: var(--text-muted); }
.ra-sub { font-size: 12px; color: var(--text-muted); margin: 4px 0 14px; }
.ra-hint { font-size: 12px; color: var(--text-muted); margin-bottom: 4px; }
.ra-none { font-size: 13px; color: var(--text-muted); padding: 10px 0; }

.ra-alerts { list-style: none; display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.ra-alert {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 9px 12px; border-radius: var(--radius-sm); font-size: 13px; line-height: 1.5;
}
.ra-alert svg { flex-shrink: 0; margin-top: 2px; }
.ra-alert--warn { background: var(--amber-light); color: var(--amber); }
.ra-alert--info { background: var(--primary-light); color: var(--primary); }

.ra-excluded { list-style: none; margin-top: 12px; display: flex; flex-direction: column; gap: 2px; }
.ra-excluded li {
  display: grid; grid-template-columns: 1fr auto auto; align-items: center; gap: 10px;
  padding: 7px 8px; border-top: 1px solid var(--border-subtle);
}
.ra-ex-name { font-size: 13px; color: var(--text); }
.ra-ex-paid { font-size: 13px; font-weight: 600; color: var(--text); }

.ra-all {
  margin-top: 14px; padding: 6px 14px; border: 1px solid var(--border-subtle);
  border-radius: var(--radius-sm); background: none; color: var(--text-muted);
  font-size: 12px; font-weight: 600; cursor: pointer; font-family: inherit;
}
.ra-all:hover { color: var(--text); }

.ra-legend {
  display: flex; align-items: center; gap: 16px;
  margin: 2px 0 10px; font-size: 11px; color: var(--text-muted);
}
.ra-legend span { display: flex; align-items: center; gap: 6px; }
.ra-key { width: 10px; height: 10px; border-radius: 3px; display: inline-block; }
.ra-key--paid { background: var(--chart-9); }
.ra-key--agreed { background: var(--text-muted); opacity: 0.38; }
.ra-legend-hint { margin-right: auto; }

.ra-explain-lead { font-size: 13px; color: var(--text); line-height: 1.8; margin-bottom: 14px; }
.ra-explain { list-style: none; display: flex; flex-direction: column; }
.ra-explain li {
  display: grid; grid-template-columns: 1fr auto 1.4fr; align-items: center; gap: 12px;
  padding: 10px 4px; border-bottom: 1px solid var(--border-subtle);
}
.ra-explain li:last-child { border-bottom: none; }
.ra-ex-co { font-size: 13px; font-weight: 600; color: var(--text); }
.ra-ex-amt { font-size: 13px; font-weight: 700; color: var(--text); }
.ra-ex-why { font-size: 12px; color: var(--text-muted); line-height: 1.6; }
.ra-ex-prods { color: var(--text); font-weight: 600; }
.ra-explain-foot {
  font-size: 12px; color: var(--text-muted); line-height: 1.8;
  margin-top: 14px; padding: 10px 12px;
  border-radius: var(--radius-sm); background: var(--border-subtle);
}

.ra-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.ra-table th {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-align: right; padding: 6px 8px; border-bottom: 1px solid var(--border-subtle);
}
.ra-table td {
  font-size: 13px; color: var(--text); padding: 9px 8px;
  border-bottom: 1px solid var(--border-subtle);
}
.ra-table th:not(:first-child), .ra-table td.ra-num { text-align: center; width: 100px; }
.ra-tag {
  display: inline-block; margin-right: 6px; padding: 1px 7px; border-radius: 10px;
  background: var(--border-subtle); color: var(--text-muted); font-size: 10px; font-weight: 600;
}
.ra-neg { color: var(--chart-loss); font-weight: 700; }
.ra-pos { color: var(--chart-gain); font-weight: 700; }
.ra-dash { color: var(--text-muted); }
.ra-est {
  display: inline-block; margin-right: 5px; width: 16px; height: 16px;
  line-height: 15px; text-align: center; border-radius: 50%;
  background: var(--border-subtle); color: var(--text-muted);
  font-size: 11px; font-weight: 700; cursor: help;
}
.ra-foot { font-size: 11px; color: var(--text-muted); margin-top: 12px; line-height: 1.6; }
</style>
