<template>
  <div v-if="companies.length" class="ra-card">
    <div class="ra-head">
      <h3>עמלות בפועל מול ההסכמים</h3>
      <span v-if="period" class="ra-period ltr-number">{{ period }}</span>
    </div>
    <p class="ra-sub">
      מה שכל חברה שילמה בפועל בדוח הנפרעים, מול מה שאמורה הייתה לשלם לפי אחוזי ההסכם.
    </p>

    <!-- Alerts first: a panel that opens with a table makes the agent hunt for
         the problem. Anything needing action is stated before the numbers. -->
    <ul v-if="alerts.length" class="ra-alerts">
      <li v-for="a in alerts" :key="a.key" class="ra-alert" :class="'ra-alert--' + a.level">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
          <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
        </svg>
        <span>{{ a.text }}</span>
      </li>
    </ul>

    <table class="ra-table">
      <thead>
        <tr>
          <th>חברה</th>
          <th>סך שולם</th>
          <th>מתוכו להשוואה</th>
          <th>לפי ההסכם</th>
          <th>הפרש</th>
          <th>אחוז בפועל</th>
          <th>אחוז בהסכם</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="c in companies" :key="c.company">
          <td>
            {{ c.company }}
            <!-- Why a row can't be compared matters as much as the number:
                 each of these has a different fix. -->
            <span v-if="c.no_agreement" class="ra-tag">אין הסכם</span>
            <span v-else-if="!c.comparable" class="ra-tag">אין שיעור למוצרים</span>
            <span v-else-if="c.rows_estimated" class="ra-tag ltr-number">
              {{ c.rows_estimated }} שורות ללא שיעור מדויק
            </span>
            <span v-if="!c.vat_verified && c.paid > 0" class="ra-tag" :title="c.vat_reason">
              מע"מ לא מאומת
            </span>
          </td>
          <td class="ra-num"><span class="ltr-number">{{ money(c.paid) }}</span></td>
          <!-- The comparison columns must describe the SAME rows on both
               sides. Showing the full paid total next to an expected figure
               built from only the firm-rate rows reads as a huge overpayment:
               מור paid ₪18,738 in total but only ₪2,030 of it sits on rows with
               a product-level rate, where the real gap is −0.6%. -->
          <td class="ra-num">
            <span v-if="c.comparable" class="ltr-number">{{ money(c.paid_firm) }}</span>
            <span v-else class="ra-dash">—</span>
          </td>
          <td class="ra-num">
            <span v-if="c.comparable" class="ltr-number">{{ money(c.expected_firm) }}</span>
            <span v-else class="ra-dash">—</span>
          </td>
          <td class="ra-num">
            <span v-if="c.comparable" class="ltr-number" :class="gapClass(c)">{{ money(c.gap, true) }}</span>
            <span v-else class="ra-dash">—</span>
          </td>
          <td class="ra-num">
            <span v-if="c.comparable" class="ltr-number">{{ pct(c.implied_rate) }}</span>
            <span v-else class="ltr-number" :title="'כלל השורות'">{{ pct(c.implied_rate_all) }}</span>
          </td>
          <td class="ra-num">
            <span v-if="c.comparable" class="ltr-number">{{ pct(c.effective_agreed_rate) }}</span>
            <span v-else class="ra-dash">—</span>
          </td>
        </tr>
      </tbody>
    </table>

    <p class="ra-foot">
      "מתוכו להשוואה" הוא החלק מהתשלום שיושב על שורות שיש להן שיעור עמלה מפורש בהסכם —
      רק הן נכנסות להפרש. שיעור שנגזר מברירת מחדל או מחציון אינו טענה על חוב.
    </p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/client'

// A gap is worth naming only past BOTH thresholds — insurers round, and a
// commission can straddle a month boundary. Mirrors the comparison engine.
const GAP_MIN_PCT = 10
const GAP_MIN_SHEKEL = 100

const companies = ref([])
const period = ref(null)

function money(v, signed = false) {
  const n = Math.round(Number(v || 0))
  if (!n) return '₪0'
  const s = '₪' + Math.abs(n).toLocaleString('en-US')
  if (!signed) return s
  return (n > 0 ? '+' : '−') + s
}

function pct(v) {
  if (v === null || v === undefined) return '—'
  const n = Number(v) * 100
  return (n < 1 ? n.toFixed(3) : n.toFixed(2)) + '%'
}

function gapClass(c) {
  if (!c.comparable || c.gap_pct === null) return ''
  if (Math.abs(c.gap_pct) < GAP_MIN_PCT || Math.abs(c.gap) < GAP_MIN_SHEKEL) return ''
  return c.gap < 0 ? 'ra-neg' : 'ra-pos'
}

// One line per PROBLEM, not per company. Listing every company that lacks an
// agreement pushed the single real finding to the bottom of eight rows — the
// panel exists to surface that finding, so the noise is collapsed into one
// line and the diagnostics move into the table as tags.
const alerts = computed(() => {
  const out = []
  const noAgreement = companies.value.filter(c => c.no_agreement && c.paid > 0)
  for (const c of companies.value) {
    if (c.no_agreement || !c.comparable) continue
    if (Math.abs(c.gap_pct) >= GAP_MIN_PCT && Math.abs(c.gap) >= GAP_MIN_SHEKEL) {
      const dir = c.gap < 0 ? 'פחות' : 'יותר'
      // Name the biggest contributing product — "Phoenix is 33% off" sends the
      // agent looking through 750 rows; naming the product does not.
      const worst = (c.products || [])
        .filter(p => p.estimated === 0 && p.expected > 0)
        .sort((a, b) => Math.abs(b.paid - b.expected) - Math.abs(a.paid - a.expected))[0]
      const where = worst ? ` בעיקר ב"${worst.product}"` : ''
      out.push({
        key: 'gap-' + c.company,
        level: c.gap < 0 ? 'warn' : 'info',
        text: `${c.company}: שולם ${money(Math.abs(c.gap))} ${dir} מהצפוי לפי ההסכם `
          + `(${c.gap_pct > 0 ? '+' : ''}${c.gap_pct}%)${where}.`,
      })
    }
  }
  if (noAgreement.length) {
    const total = noAgreement.reduce((s, c) => s + c.paid, 0)
    out.push({
      key: 'noagr',
      level: 'info',
      text: `${noAgreement.map(c => c.company).join(', ')}: התקבלו ${money(total)} `
        + `ואין הסכם עמלות במערכת — העלה את ההסכמים כדי שנוכל לבדוק אותם.`,
    })
  }
  return out
})

onMounted(async () => {
  try {
    const res = await api.get('/production/rate-audit')
    companies.value = res.data.companies || []
    period.value = res.data.period
  } catch (e) {
    companies.value = []
  }
})
</script>

<style scoped>
.ra-card {
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  padding: 20px;
}
.ra-head { display: flex; align-items: baseline; gap: 10px; }
.ra-head h3 { font-size: 15px; font-weight: 700; color: var(--text); }
.ra-period { font-size: 12px; color: var(--text-muted); }
.ra-sub { font-size: 12px; color: var(--text-muted); margin: 4px 0 14px; }

.ra-alerts { list-style: none; display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; }
.ra-alert {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 9px 12px; border-radius: var(--radius-sm);
  font-size: 13px; line-height: 1.5;
}
.ra-alert svg { flex-shrink: 0; margin-top: 2px; }
.ra-alert--warn { background: var(--amber-light); color: var(--amber); }
.ra-alert--info { background: var(--primary-light); color: var(--primary); }

.ra-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.ra-table th {
  font-size: 11px; font-weight: 600; color: var(--text-muted);
  text-align: right; padding: 6px 8px;
  border-bottom: 1px solid var(--border-subtle);
}
.ra-table td {
  font-size: 13px; color: var(--text); padding: 9px 8px;
  border-bottom: 1px solid var(--border-subtle);
}
.ra-table th:not(:first-child), .ra-table td.ra-num { text-align: center; width: 100px; }
.ra-tag {
  display: inline-block; margin-right: 6px; padding: 1px 7px;
  border-radius: 10px; background: var(--border-subtle);
  color: var(--text-muted); font-size: 10px; font-weight: 600;
}
.ra-neg { color: var(--red, #c23934); font-weight: 700; }
.ra-pos { color: var(--accent-emerald); font-weight: 700; }
.ra-dash { color: var(--text-muted); }
.ra-foot { font-size: 11px; color: var(--text-muted); margin-top: 12px; line-height: 1.6; }
</style>
