<template>
  <section v-if="rows.length" class="crs" aria-labelledby="crs-title">
    <div class="crs-head">
      <div class="crs-head-text">
        <h3 id="crs-title" class="crs-title">סיכום לפי חברה</h3>
        <span class="crs-sub">גמל + ביטוח · נפרעים מול פרודוקציה</span>
      </div>

      <!-- Compact totals strip — the bottom line at a glance -->
      <div v-if="totals" class="crs-totals-strip" aria-hidden="true">
        <div class="crs-pill crs-pill--received">
          <span class="crs-pill-label">התקבל</span>
          <span class="crs-pill-value ltr-number">{{ fmtMoney(totals.received) }}</span>
        </div>
        <div class="crs-pill crs-pill--expected">
          <span class="crs-pill-label">צפי</span>
          <span class="crs-pill-value ltr-number">{{ fmtMoney(totals.expected) }}</span>
        </div>
        <div class="crs-pill crs-pill--gap" :class="{ zero: !(totals.gap > 0) }">
          <span class="crs-pill-label">פער</span>
          <span class="crs-pill-value ltr-number">{{ fmtMoney(totals.gap) }}</span>
        </div>
      </div>
    </div>

    <div class="crs-table-wrap">
      <table class="crs-table">
        <thead>
          <tr>
            <th class="t-name">חברה</th>
            <th>מופקים</th>
            <th>תואמו</th>
            <th>לא־שולמו</th>
            <th>התקבל</th>
            <th>צפי</th>
            <th>פער</th>
            <th class="t-bar">ביצוע גבייה</th>
            <th class="t-go"><span class="sr-only">מעבר לפירוט</span></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.company"
            class="crs-row"
            tabindex="0"
            role="button"
            :aria-label="'פירוט ' + row.company"
            @click="$emit('drill', row.company)"
            @keydown.enter.prevent="$emit('drill', row.company)"
            @keydown.space.prevent="$emit('drill', row.company)"
          >
            <td class="t-name">
              <span
                class="crs-avatar"
                :style="avatarStyle(row.company)"
                aria-hidden="true"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                  <path :d="brandIcon(row.company)" />
                </svg>
              </span>
              <span class="crs-company">{{ row.company }}</span>
            </td>
            <td><span class="ltr-number">{{ fmtInt(row.produced) }}</span></td>
            <td><span class="ltr-number num-matched">{{ fmtInt(row.matched) }}</span></td>
            <td>
              <span v-if="row.unpaid > 0" class="crs-chip crs-chip--warn ltr-number">{{ fmtInt(row.unpaid) }}</span>
              <span v-else class="ltr-number num-muted">0</span>
            </td>
            <td><span class="ltr-number">{{ fmtMoney(row.received) }}</span></td>
            <td><span class="ltr-number num-muted">{{ fmtMoney(row.expected) }}</span></td>
            <td>
              <span class="ltr-number" :class="row.gap > 0 ? 'num-gap' : 'num-muted'">{{ fmtMoney(row.gap) }}</span>
            </td>
            <td class="t-bar">
              <div
                class="crs-progress"
                role="img"
                :aria-label="'נגבו ' + pctLabel(row) + ' מהצפי'"
              >
                <div class="crs-progress-track" :class="{ 'has-gap': row.gap > 0 }">
                  <div
                    class="crs-progress-fill"
                    :style="{ width: pctWidth(row), background: companyColor(row.company) }"
                  ></div>
                </div>
                <span class="crs-progress-pct ltr-number">{{ pctLabel(row) }}</span>
              </div>
            </td>
            <td class="t-go">
              <svg class="crs-chevron" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <path d="m15 18-6-6 6-6" />
              </svg>
            </td>
          </tr>
        </tbody>
        <tfoot v-if="totals">
          <tr class="crs-total">
            <td class="t-name">סה״כ</td>
            <td><span class="ltr-number">{{ fmtInt(totals.produced) }}</span></td>
            <td><span class="ltr-number">{{ fmtInt(totals.matched) }}</span></td>
            <td><span class="ltr-number">{{ fmtInt(totals.unpaid) }}</span></td>
            <td><span class="ltr-number">{{ fmtMoney(totals.received) }}</span></td>
            <td><span class="ltr-number">{{ fmtMoney(totals.expected) }}</span></td>
            <td><span class="ltr-number" :class="totals.gap > 0 ? 'num-gap' : 'num-muted'">{{ fmtMoney(totals.gap) }}</span></td>
            <td class="t-bar">
              <div class="crs-progress">
                <div class="crs-progress-track" :class="{ 'has-gap': totals.gap > 0 }">
                  <div class="crs-progress-fill crs-progress-fill--total" :style="{ width: pctWidth(totals) }"></div>
                </div>
                <span class="crs-progress-pct ltr-number">{{ pctLabel(totals) }}</span>
              </div>
            </td>
            <td class="t-go"></td>
          </tr>
        </tfoot>
      </table>
    </div>

    <!-- Stacked cards below ~720px (table hidden, same data) -->
    <ul class="crs-cards">
      <li v-for="row in rows" :key="'c-' + row.company">
        <button type="button" class="crs-card" @click="$emit('drill', row.company)">
          <div class="crs-card-top">
            <span class="crs-avatar" :style="avatarStyle(row.company)" aria-hidden="true">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path :d="brandIcon(row.company)" />
              </svg>
            </span>
            <span class="crs-company">{{ row.company }}</span>
            <span v-if="row.unpaid > 0" class="crs-chip crs-chip--warn ltr-number">{{ fmtInt(row.unpaid) }} לא שולמו</span>
            <svg class="crs-chevron" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="m15 18-6-6 6-6" />
            </svg>
          </div>
          <div class="crs-card-nums">
            <div class="crs-card-stat">
              <span class="crs-card-label">התקבל</span>
              <span class="ltr-number">{{ fmtMoney(row.received) }}</span>
            </div>
            <div class="crs-card-stat">
              <span class="crs-card-label">צפי</span>
              <span class="ltr-number num-muted">{{ fmtMoney(row.expected) }}</span>
            </div>
            <div class="crs-card-stat">
              <span class="crs-card-label">פער</span>
              <span class="ltr-number" :class="row.gap > 0 ? 'num-gap' : 'num-muted'">{{ fmtMoney(row.gap) }}</span>
            </div>
          </div>
          <div class="crs-progress">
            <div class="crs-progress-track" :class="{ 'has-gap': row.gap > 0 }">
              <div class="crs-progress-fill" :style="{ width: pctWidth(row), background: companyColor(row.company) }"></div>
            </div>
            <span class="crs-progress-pct ltr-number">{{ pctLabel(row) }}</span>
          </div>
        </button>
      </li>
    </ul>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { brandForLabel } from '../../utils/companyBrand.js'
import { assignNearestDistinct } from '../../utils/chartPalette.js'

const props = defineProps({
  summary: { type: Object, default: null }, // { companies: [...], totals: {...} }
})
defineEmits(['drill'])

const rows = computed(() => props.summary?.companies || [])
const totals = computed(() => props.summary?.totals || null)

// One distinct palette color per company, anchored to its brand hue — the
// SAME assignment mechanism the automation canvas uses, so a company keeps
// its color across tabs.
const colorMap = computed(() =>
  assignNearestDistinct(
    rows.value.map((r) => ({ key: r.company, brand: brandForLabel(r.company).color }))
  )
)

function companyColor(company) {
  return colorMap.value.get(company) || 'var(--chart-2, #4E9DD0)'
}

function brandIcon(company) {
  return brandForLabel(company).iconPath
}

function avatarStyle(company) {
  const c = companyColor(company)
  return {
    color: c,
    background: `color-mix(in srgb, ${c} 13%, white)`,
    borderColor: `color-mix(in srgb, ${c} 30%, transparent)`,
  }
}

// Collection rate: received out of expected (expected = received + open gap).
function pct(row) {
  const expected = Number(row?.expected || 0)
  const received = Number(row?.received || 0)
  if (expected <= 0) return received > 0 ? 1 : null
  return Math.min(received / expected, 1)
}

function pctWidth(row) {
  const p = pct(row)
  return p === null ? '0%' : `${Math.round(p * 100)}%`
}

function pctLabel(row) {
  const p = pct(row)
  return p === null ? '—' : `${Math.round(p * 100)}%`
}

function fmtInt(n) {
  return Number(n || 0).toLocaleString('en-US')
}
function fmtMoney(n) {
  const v = Number(n || 0)
  return '₪' + Math.round(v).toLocaleString('en-US')
}
</script>

<style scoped>
.crs {
  background: var(--card-bg, #fff);
  border: 1px solid var(--border-subtle, #e5e7eb);
  border-radius: var(--radius-md, 14px);
  padding: 16px 18px;
  margin-top: 20px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.crs-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}

.crs-head-text {
  display: flex;
  align-items: baseline;
  gap: 10px;
  min-width: 0;
}

.crs-title {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text, #181818);
}

.crs-sub {
  font-size: 12px;
  color: var(--text-muted, #706E6B);
  white-space: nowrap;
}

/* Totals strip */
.crs-totals-strip {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.crs-pill {
  display: flex;
  align-items: baseline;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid transparent;
}

.crs-pill-label { font-weight: 500; opacity: 0.85; }
.crs-pill-value { font-weight: 700; }

.crs-pill--received {
  background: var(--green-light, #EBF7EE);
  color: var(--green-deep, #1B5E20);
  border-color: rgba(46, 132, 74, 0.2);
}

.crs-pill--expected {
  background: var(--bg, #F3F3F3);
  color: var(--text-secondary, #3E3E3C);
  border-color: var(--border-subtle, #E5E5E5);
}

.crs-pill--gap {
  background: var(--red-light, #FEF1EE);
  color: var(--red-deep, #C23934);
  border-color: rgba(194, 57, 52, 0.2);
}

.crs-pill--gap.zero {
  background: var(--bg, #F3F3F3);
  color: var(--text-muted, #706E6B);
  border-color: var(--border-subtle, #E5E5E5);
}

/* Table */
.crs-table-wrap { overflow-x: auto; }

.crs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.crs-table th,
.crs-table td {
  padding: 10px 8px;
  text-align: center;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.crs-table th {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-muted, #706E6B);
  border-bottom: 1px solid var(--border-subtle, #e5e7eb);
}

.crs-table th.t-name,
.crs-table td.t-name {
  text-align: start;
  min-width: 160px;
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.crs-table td.t-name {
  display: flex;
  align-items: center;
  gap: 9px;
  font-weight: 600;
  color: var(--text, #181818);
}

.t-bar { min-width: 130px; }
.t-go { width: 34px; }

.crs-avatar {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: 1px solid transparent;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.crs-company {
  overflow: hidden;
  text-overflow: ellipsis;
}

.crs-row {
  cursor: pointer;
  transition: background 0.15s var(--transition, ease);
}

.crs-row:hover { background: rgba(0, 0, 0, 0.025); }

.crs-row:focus-visible {
  outline: 2px solid var(--primary, #F57C00);
  outline-offset: -2px;
  border-radius: 6px;
}

.crs-row td { border-bottom: 1px solid #f1f1f3; }

.crs-row:hover .crs-chevron { transform: translateX(-2px); color: var(--text, #181818); }

.crs-chevron {
  color: var(--text-muted, #706E6B);
  transition: transform 0.2s var(--transition, ease), color 0.2s;
}

/* Number semantics */
.num-matched { color: var(--green-deep, #1B5E20); font-weight: 600; }
.num-muted { color: var(--text-muted, #706E6B); }
.num-gap { color: var(--red-deep, #C23934); font-weight: 700; }

.crs-chip {
  display: inline-block;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.crs-chip--warn {
  background: var(--amber-light, #FFF3E0);
  color: #9A6B12;
  border: 1px solid rgba(232, 114, 10, 0.25);
}

/* Received-vs-expected progress */
.crs-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.crs-progress-track {
  flex: 1;
  height: 7px;
  border-radius: 999px;
  background: var(--bg, #F0F0F0);
  overflow: hidden;
  min-width: 70px;
}

/* When money is missing, the uncollected remainder reads as a red tint */
.crs-progress-track.has-gap {
  background: color-mix(in srgb, var(--red, #EA001E) 14%, white);
}

.crs-progress-fill {
  height: 100%;
  border-radius: 999px;
  transition: width 0.4s var(--transition, ease);
}

.crs-progress-fill--total {
  background: var(--green, #2E844A);
}

.crs-progress-pct {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted, #706E6B);
  min-width: 34px;
  text-align: start;
}

/* Totals row */
.crs-total td {
  border-top: 2px solid var(--border-subtle, #e5e7eb);
  font-weight: 700;
  color: var(--text, #181818);
  padding-top: 12px;
}

.crs-total td.t-name { display: table-cell; }

/* Stacked cards (mobile) */
.crs-cards {
  display: none;
  list-style: none;
  margin: 0;
  padding: 0;
  flex-direction: column;
  gap: 10px;
}

.crs-card {
  width: 100%;
  text-align: start;
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-subtle, #e5e7eb);
  border-radius: 12px;
  padding: 12px 14px;
  font-family: inherit;
  font-size: 13px;
  color: var(--text, #181818);
  cursor: pointer;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.crs-card:active { background: rgba(0, 0, 0, 0.03); }

.crs-card-top {
  display: flex;
  align-items: center;
  gap: 9px;
}

.crs-card-top .crs-company { font-weight: 700; flex: 1; }
.crs-card-top .crs-chevron { flex-shrink: 0; }

.crs-card-nums {
  display: flex;
  gap: 16px;
}

.crs-card-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.crs-card-label {
  font-size: 11px;
  color: var(--text-muted, #706E6B);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}

@media (max-width: 720px) {
  .crs-table-wrap { display: none; }
  .crs-cards { display: flex; }
  .crs-totals-strip { width: 100%; }
}

@media (prefers-reduced-motion: reduce) {
  .crs-progress-fill, .crs-chevron, .crs-row { transition: none; }
}
</style>
