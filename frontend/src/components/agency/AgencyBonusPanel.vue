<template>
  <div class="bp-wrap">
    <!-- ── Hero strip: 3 KPI tiles + completion ring ── -->
    <div class="bp-hero">
      <div class="bp-stats">
        <div class="bp-stat">
          <div class="bp-stat-eyebrow">סה"כ בונוסים — {{ data.year }}</div>
          <div class="bp-stat-val ltr-number">{{ totals.total }}</div>
          <div class="bp-stat-sub">{{ companyCount }} חברות · {{ agentCount }} סוכנים</div>
        </div>

        <div class="bp-stat paid">
          <div class="bp-stat-eyebrow">שולמו</div>
          <div class="bp-stat-val ltr-number">{{ totals.paid }}</div>
          <div class="bp-stat-sub">
            <span class="delta-up">▲</span>
            {{ paidPct }}% מהשנה
          </div>
        </div>

        <div class="bp-stat pending">
          <div class="bp-stat-eyebrow">ממתינים לטיפול</div>
          <div class="bp-stat-val ltr-number">{{ totals.pending }}</div>
          <div class="bp-stat-sub">דורשים מעקב מול חברות הביטוח</div>
        </div>
      </div>

      <!-- Big completion ring -->
      <div class="bp-ring">
        <svg viewBox="0 0 140 140" width="140" height="140">
          <defs>
            <linearGradient id="bp-ring-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#FFB74D"/>
              <stop offset="100%" stop-color="#E8660A"/>
            </linearGradient>
          </defs>
          <circle cx="70" cy="70" r="58" fill="none" stroke="rgba(45, 37, 34, 0.08)" stroke-width="14"/>
          <circle
            cx="70" cy="70" r="58"
            fill="none"
            stroke="url(#bp-ring-grad)"
            stroke-width="14"
            stroke-linecap="round"
            stroke-dasharray="364.4"
            :stroke-dashoffset="ringOffset"
            transform="rotate(-90 70 70)"
            class="bp-ring-anim"
          />
        </svg>
        <div class="bp-ring-text">
          <div class="bp-ring-num ltr-number">{{ paidPct }}%</div>
          <div class="bp-ring-label">הושלמו</div>
        </div>
      </div>
    </div>

    <!-- ── Per-company breakdown: stacked progress bars ── -->
    <div class="bp-section">
      <div class="bp-section-h">
        <h3>פירוק לפי חברה משלמת</h3>
        <span class="bp-tag">{{ companyCount }} חברות</span>
      </div>
      <div v-if="!byCompany.length" class="bp-empty">אין נתוני בונוס לחברות עדיין.</div>
      <ul v-else class="bp-co-list">
        <li v-for="c in byCompany" :key="c.company">
          <div class="bp-co-head">
            <span class="bp-co-name">{{ shortCompany(c.company) }}</span>
            <span class="bp-co-stats">
              <strong>{{ c.paid }}</strong>/<span>{{ c.total }}</span>
              <span class="bp-co-pct ltr-number">{{ Math.round((c.paid / Math.max(1, c.total)) * 100) }}%</span>
            </span>
          </div>
          <div class="bp-co-bar">
            <div
              class="bp-co-fill"
              :style="{ width: ((c.paid / Math.max(1, c.total)) * 100) + '%' }"
            ></div>
          </div>
        </li>
      </ul>
    </div>

    <!-- ── Per-agent grid: card per agent with chips ── -->
    <div class="bp-section">
      <div class="bp-section-h">
        <h3>סטטוס לפי סוכן</h3>
        <span class="bp-tag">{{ agentCount }} סוכנים</span>
      </div>
      <div v-if="!byAgent.length" class="bp-empty">אין נתוני בונוס לסוכנים עדיין.</div>
      <div v-else class="bp-ag-grid">
        <div v-for="a in byAgent" :key="a.name" class="bp-ag-card">
          <div class="bp-ag-head">
            <span class="bp-ag-avatar">{{ initials(a.name) }}</span>
            <div class="bp-ag-text">
              <div class="bp-ag-name">{{ a.name }}</div>
              <div class="bp-ag-meta">
                <strong>{{ a.paid }}</strong>/{{ a.total }} שולמו
              </div>
            </div>
            <div class="bp-ag-pct ltr-number">{{ Math.round((a.paid / Math.max(1, a.total)) * 100) }}%</div>
          </div>
          <div class="bp-ag-chips">
            <span
              v-for="(item, i) in a.items.slice(0, 6)"
              :key="i"
              class="bp-ag-chip"
              :class="{ paid: item.is_paid }"
              :title="item.company + (item.is_paid ? ' · שולם' : ' · ממתין')"
            >
              {{ shortCompany(item.company) }}
            </span>
            <span v-if="a.items.length > 6" class="bp-ag-more">+{{ a.items.length - 6 }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  data: {
    type: Object,
    required: true,
    default: () => ({ year: new Date().getFullYear(), rows: [], totals: { total: 0, paid: 0 } }),
  },
})

const totals = computed(() => {
  const total = props.data?.totals?.total || 0
  const paid = props.data?.totals?.paid || 0
  return { total, paid, pending: Math.max(0, total - paid) }
})

const paidPct = computed(() => {
  if (!totals.value.total) return 0
  return Math.round((totals.value.paid / totals.value.total) * 100)
})

// SVG ring: full circumference is 2 * π * 58 = 364.4
const ringOffset = computed(() => {
  const fullLen = 364.4
  return fullLen * (1 - paidPct.value / 100)
})

const byCompany = computed(() => {
  const acc = new Map()
  for (const r of props.data?.rows || []) {
    const k = r.company || '—'
    const e = acc.get(k) || { company: k, total: 0, paid: 0 }
    e.total += 1
    if (r.is_paid) e.paid += 1
    acc.set(k, e)
  }
  return [...acc.values()].sort((a, b) => b.total - a.total)
})

const byAgent = computed(() => {
  const acc = new Map()
  for (const r of props.data?.rows || []) {
    const k = r.agent_name || '—'
    const e = acc.get(k) || { name: k, items: [], paid: 0, total: 0 }
    e.items.push({ company: r.company, is_paid: r.is_paid, paid_date: r.paid_date })
    e.total += 1
    if (r.is_paid) e.paid += 1
    acc.set(k, e)
  }
  return [...acc.values()].sort((a, b) => b.total - a.total || (b.paid / Math.max(1, b.total)) - (a.paid / Math.max(1, a.total)))
})

const companyCount = computed(() => byCompany.value.length)
const agentCount = computed(() => byAgent.value.length)

function shortCompany(s) {
  if (!s) return ''
  return s
    .replace(/\s*חברה\s*לביטוח/g, '')
    .replace(/\s*בע"מ/g, '')
    .replace(/\s*בע״מ/g, '')
    .replace(/\s*ופנסיה/g, '')
    .trim()
}
function initials(name) {
  if (!name) return '?'
  return name.split(/\s+/).slice(0, 2).map(p => (p || '')[0] || '').join('').toUpperCase()
}
</script>

<style scoped>
.bp-wrap {
  display: flex; flex-direction: column; gap: 22px;
}

/* ── Hero strip ───────────────────────────────────────────── */
.bp-hero {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 20px;
  align-items: stretch;
  background: linear-gradient(135deg, #FFF8F0 0%, #FFFFFF 60%);
  border: 1px solid rgba(45, 37, 34, 0.08);
  border-radius: 18px;
  padding: 22px 26px;
  box-shadow: 0 12px 30px -16px rgba(232, 102, 10, 0.18);
  position: relative;
  overflow: hidden;
}
.bp-hero::before {
  content: ''; position: absolute; inset: 0 0 auto 0; height: 4px;
  background: linear-gradient(90deg, #FFD54F 0%, #E8660A 50%, #FFD54F 100%);
}

.bp-stats {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px;
}
.bp-stat {
  background: #FFFFFF;
  border: 1px solid rgba(45, 37, 34, 0.06);
  border-radius: 12px;
  padding: 14px 16px;
  position: relative;
  overflow: hidden;
}
.bp-stat::after {
  content: ''; position: absolute; inset: 0 0 auto 0; height: 3px;
  background: var(--primary);
  opacity: 0.85;
}
.bp-stat.paid::after { background: linear-gradient(90deg, #2E844A, #66BB6A); }
.bp-stat.pending::after { background: linear-gradient(90deg, #E8660A, #FFB74D); }

.bp-stat-eyebrow {
  font-size: 10.5px; font-weight: 700; letter-spacing: 1.2px;
  text-transform: uppercase; color: rgba(45, 37, 34, 0.55);
}
.bp-stat-val {
  font-size: 32px; font-weight: 900; letter-spacing: -1px;
  color: #2D2522; line-height: 1; margin: 6px 0 4px;
}
.bp-stat.paid .bp-stat-val { color: #1B5E20; }
.bp-stat.pending .bp-stat-val { color: #C85A00; }
.bp-stat-sub { font-size: 11.5px; color: rgba(45, 37, 34, 0.55); }
.delta-up { color: #2E844A; font-weight: 800; margin-left: 2px; }

/* Ring */
.bp-ring {
  position: relative;
  width: 140px; height: 140px;
  display: flex; align-items: center; justify-content: center;
  margin: auto 0;
}
.bp-ring-anim {
  animation: bp-ring-fill 1.4s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  transition: stroke-dashoffset .8s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes bp-ring-fill {
  from { stroke-dashoffset: 364.4; }
}
.bp-ring-text {
  position: absolute; inset: 0;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.bp-ring-num {
  font-size: 30px; font-weight: 900; color: #2D2522; letter-spacing: -1.2px;
}
.bp-ring-label {
  font-size: 11px; font-weight: 700; color: rgba(45, 37, 34, 0.55);
  letter-spacing: 1px; text-transform: uppercase;
}

/* ── Sections ─────────────────────────────────────────────── */
.bp-section {
  background: #FFFFFF;
  border: 1px solid rgba(45, 37, 34, 0.08);
  border-radius: 16px;
  padding: 18px 22px;
  box-shadow: 0 8px 22px -16px rgba(45, 37, 34, 0.18);
}
.bp-section-h {
  display: flex; justify-content: space-between; align-items: baseline;
  margin-bottom: 14px;
}
.bp-section-h h3 {
  font-size: 16px; font-weight: 800; color: #2D2522; letter-spacing: -0.2px;
}
.bp-tag {
  background: var(--primary-light, #FFF3E0); color: #C85A00;
  padding: 3px 10px; border-radius: 999px;
  font-size: 11px; font-weight: 700;
}
.bp-empty { padding: 30px; text-align: center; color: rgba(45, 37, 34, 0.5); font-size: 13px; }

/* ── By company list ──────────────────────────────────────── */
.bp-co-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 14px; }
.bp-co-list li { display: flex; flex-direction: column; gap: 5px; }
.bp-co-head {
  display: flex; justify-content: space-between; align-items: baseline;
  font-size: 13px;
}
.bp-co-name { color: #2D2522; font-weight: 700; }
.bp-co-stats { color: rgba(45, 37, 34, 0.6); font-weight: 600; display: inline-flex; gap: 10px; align-items: baseline; }
.bp-co-stats strong { color: #1B5E20; font-weight: 800; }
.bp-co-stats span { color: rgba(45, 37, 34, 0.4); }
.bp-co-pct {
  background: rgba(232, 102, 10, 0.10); color: #C85A00;
  padding: 2px 9px; border-radius: 999px; font-size: 11px; font-weight: 800;
  margin-right: 4px;
}
.bp-co-bar {
  height: 10px; border-radius: 6px; overflow: hidden;
  background: rgba(45, 37, 34, 0.06);
}
.bp-co-fill {
  height: 100%;
  background: linear-gradient(90deg, #FFD54F 0%, #E8660A 100%);
  border-radius: 6px;
  transition: width .9s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 2px 6px rgba(232, 102, 10, 0.35);
  animation: bp-fill-grow .9s cubic-bezier(0.16, 1, 0.3, 1) both;
}
@keyframes bp-fill-grow { from { width: 0 !important; } }

/* ── Per-agent grid ───────────────────────────────────────── */
.bp-ag-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}
.bp-ag-card {
  background: #FFF9F0;
  border: 1px solid rgba(232, 102, 10, 0.18);
  border-radius: 12px;
  padding: 12px 14px;
  transition: transform .2s var(--transition), box-shadow .2s var(--transition);
}
.bp-ag-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 22px -14px rgba(232, 102, 10, 0.4);
}
.bp-ag-head { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.bp-ag-avatar {
  width: 36px; height: 36px; border-radius: 50%;
  background: linear-gradient(135deg, #FFD180, #E8660A);
  color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 13px;
  box-shadow: 0 4px 10px rgba(232, 102, 10, 0.4);
}
.bp-ag-text { flex: 1; min-width: 0; }
.bp-ag-name {
  font-size: 13.5px; font-weight: 800; color: #2D2522;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.bp-ag-meta { font-size: 11.5px; color: rgba(45, 37, 34, 0.6); margin-top: 1px; }
.bp-ag-meta strong { color: #1B5E20; font-weight: 800; }
.bp-ag-pct {
  background: #2D2522; color: #FFE0B2;
  padding: 4px 10px; border-radius: 999px;
  font-size: 12px; font-weight: 800;
}
.bp-ag-chips { display: flex; flex-wrap: wrap; gap: 5px; }
.bp-ag-chip {
  font-size: 10.5px; font-weight: 700;
  padding: 3px 8px; border-radius: 6px;
  background: rgba(232, 102, 10, 0.08);
  color: #C85A00;
  border: 1px solid rgba(232, 102, 10, 0.18);
}
.bp-ag-chip.paid {
  background: rgba(46, 132, 74, 0.10);
  color: #1B5E20;
  border-color: rgba(46, 132, 74, 0.22);
  position: relative;
}
.bp-ag-chip.paid::before { content: '✓ '; }
.bp-ag-more {
  font-size: 10.5px; font-weight: 700;
  padding: 3px 8px; border-radius: 6px;
  background: rgba(45, 37, 34, 0.06); color: rgba(45, 37, 34, 0.55);
}

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

@media (max-width: 900px) {
  .bp-hero { grid-template-columns: 1fr; }
  .bp-ring { margin: 0 auto; }
  .bp-stats { grid-template-columns: 1fr; }
}
</style>
