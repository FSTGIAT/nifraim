<template>
  <div class="agents-tab">
    <div v-if="loading" class="state">
      <div class="spinner"></div>
      <span>טוען נתוני סוכנות…</span>
    </div>

    <template v-else-if="comparison && agents">
      <!-- ═══════════════════════════════════════════════════════════
           MONITOR — sticky always-on dashboard (KPI strip + mini gauges + podium)
           ═══════════════════════════════════════════════════════════ -->
      <div class="monitor">
        <!-- KPI strip -->
        <div class="kpi-row">
          <div class="kpi kpi-blue">
            <div class="kpi-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4-4v2"/><circle cx="9" cy="7" r="4"/>
              </svg>
            </div>
            <div class="kpi-data">
              <div class="kpi-value ltr-number">{{ agentCount }}</div>
              <div class="kpi-label">סוכנים</div>
            </div>
          </div>
          <div class="kpi kpi-cyan">
            <div class="kpi-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M9 17v-6a3 3 0 016 0v6m-9 4h12"/><circle cx="12" cy="6" r="2"/>
              </svg>
            </div>
            <div class="kpi-data">
              <div class="kpi-value ltr-number">{{ comparison.summary.total_customers.toLocaleString('he-IL') }}</div>
              <div class="kpi-label">לקוחות בנפרעים</div>
            </div>
          </div>
          <div class="kpi kpi-amber">
            <div class="kpi-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
              </svg>
            </div>
            <div class="kpi-data">
              <div class="kpi-value ltr-number">{{ comparison.summary.unpaid_count.toLocaleString('he-IL') }}</div>
              <div class="kpi-label">לא שולם</div>
            </div>
          </div>
          <div class="kpi kpi-emerald">
            <div class="kpi-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            </div>
            <div class="kpi-data">
              <div class="kpi-value ltr-number">{{ comparison.summary.matched_count.toLocaleString('he-IL') }}</div>
              <div class="kpi-label">נמצא בשניהם</div>
            </div>
          </div>
          <div class="kpi kpi-red">
            <div class="kpi-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 000 7h5a3.5 3.5 0 010 7H6"/>
              </svg>
            </div>
            <div class="kpi-data">
              <div class="kpi-value ltr-number">{{ formatShort(comparison.summary.total_unpaid_amount) }}</div>
              <div class="kpi-label">סך עמלות לא שולמו</div>
            </div>
          </div>
        </div>

        <!-- Mini gauges + podium chips, single row -->
        <div class="monitor-row">
          <div class="mini-gauges-strip">
            <div class="mg-eyebrow">
              <span>מגמה לפי חברה</span>
              <span class="mg-period ltr-number" v-if="targets?.current_period">
                {{ targets.current_period }} ▸ {{ targets.previous_period || '—' }}
              </span>
            </div>
            <div class="mg-grid" v-if="topGauges.length">
              <div v-for="(g, i) in topGauges.slice(0, 5)" :key="i" class="mini-gauge" :title="g.company">
                <apexchart
                  type="radialBar" height="90"
                  :options="miniGaugeOptions(g.achievement_pct, gaugeColor(g.achievement_pct), g.is_new)"
                  :series="[Math.min(200, g.achievement_pct || 0)]"
                />
                <div class="mini-gauge-label">{{ shortCo(g.company) }}</div>
                <div class="mini-gauge-delta" :class="deltaClass(g)">
                  <span v-if="g.is_new">חדש</span>
                  <span v-else-if="g.change_pct > 0" class="ltr-number">▲ {{ g.change_pct }}%</span>
                  <span v-else-if="g.change_pct < 0" class="ltr-number">▼ {{ Math.abs(g.change_pct) }}%</span>
                  <span v-else>—</span>
                </div>
              </div>
            </div>
            <div v-else class="mg-empty">אין מגמה זמינה — צריך 2 חודשי פרודוקציה</div>
          </div>

          <div class="mini-podium" v-if="topPerformers.length">
            <div class="mp-eyebrow">3 המובילים</div>
            <div
              v-for="(p, i) in topPerformers.slice(0, 3)"
              :key="p.user_id"
              class="mp-chip"
              :class="`rank-${i + 1}`"
              @click="$emit('view-agent', p.user_id)"
            >
              <span class="mp-rank" :class="`mp-rank-${i + 1}`">{{ i + 1 }}</span>
              <span class="mp-name">{{ p.name }}</span>
              <span class="mp-prem ltr-number">{{ formatShort(p.premium) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- ═══════════════════════════════════════════════════════════
           SUB-TAB STRIP — 4 work areas (פיוס / חישוב / תכנון / סוכנים)
           ═══════════════════════════════════════════════════════════ -->
      <div class="sub-tabs" role="tablist">
        <button
          v-for="t in subTabs"
          :key="t.id"
          class="sub-pill"
          :class="{ active: activeSubTab === t.id }"
          :style="{ '--accent': t.accent, '--accent-glow': t.accentGlow }"
          :title="t.tooltip"
          role="tab"
          :aria-selected="activeSubTab === t.id"
          @click="setSubTab(t.id)"
        >
          <span class="sub-icon" v-html="t.icon"></span>
          {{ t.label }}
        </button>
      </div>

      <!-- ═══════════════════════════════════════════════════════════
           SUB-TAB CONTENT — only one rendered at a time
           ═══════════════════════════════════════════════════════════ -->
      <Transition name="sub-fade" mode="out-in">
        <div :key="activeSubTab" class="sub-content">

          <!-- 🩹 פיוס (default) — aging exceptions + storno -->
          <template v-if="activeSubTab === 'reconcile'">
            <div class="card section-card">
              <div class="card-h">
                <div>
                  <span class="section-eyebrow">חריגים · 11:00 - 13:30</span>
                  <h3>טיפול בחריגים וערעורים — חוב פתוח מול חברות הביטוח</h3>
                </div>
              </div>
              <div v-if="aging" class="row-2 aging-grid">
                <div>
                  <h4 class="sub-h">תורי טיפול לפי גיל</h4>
                  <apexchart
                    v-if="aging.buckets.length"
                    type="bar" height="240"
                    :options="agingBucketsOptions"
                    :series="agingBucketsSeries"
                  />
                </div>
                <div>
                  <h4 class="sub-h">חוב פתוח לפי חברה — Top 10</h4>
                  <apexchart
                    v-if="aging.by_company.length"
                    type="bar" height="240"
                    :options="agingCoOptions"
                    :series="agingCoSeries"
                  />
                </div>
              </div>

              <h4 class="oldest-h">פעולות שצריך לטפל קודם — 10 הוותיקות ביותר</h4>
              <table v-if="aging?.oldest?.length" class="ov-table">
                <thead>
                  <tr><th>גיל (ימים)</th><th>סוכן</th><th>חברה</th><th>לקוח</th><th class="num">חוסר</th><th>מייל פנייה</th></tr>
                </thead>
                <tbody>
                  <tr v-for="o in aging.oldest.slice(0, 10)" :key="o.record_id" class="clickable" @click="$emit('view-agent', o.agent_user_id)">
                    <td><span class="age-pill" :class="ageClass(o.age_days)">{{ o.age_days }}</span></td>
                    <td>{{ o.agent_name }}</td>
                    <td>{{ shortCo(o.company) }}</td>
                    <td class="muted">{{ o.client_name || o.client_id_number }}</td>
                    <td class="num warn"><span class="ltr-number">{{ formatShort(o.expected_amount) }}</span></td>
                    <td>
                      <a class="follow-up-btn" :href="emailDraft(o)" @click.stop>
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
                          <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                          <polyline points="22,6 12,13 2,6"/>
                        </svg>
                        שלח פנייה
                      </a>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty">אין כרגע חריגים פתוחים 🎉</div>
            </div>

            <div class="card section-card">
              <div class="card-h">
                <div>
                  <span class="section-eyebrow">סטורנו · 14:30</span>
                  <h3>טיפול בביטולים — קיזוז עמלות שנמשכו חזרה</h3>
                </div>
                <div class="storno-tag" v-if="storno">
                  <span class="storno-count ltr-number">{{ storno.totals.count.toLocaleString('he-IL') }}</span>
                  ביטולים · <span class="storno-amount ltr-number">{{ formatShort(storno.totals.amount) }}</span>
                </div>
              </div>
              <div v-if="storno" class="storno-grid">
                <div class="storno-chart">
                  <h4 class="sub-h">מגמה חודשית</h4>
                  <apexchart v-if="storno.by_month.length" type="line" height="220" :options="stornoTrendOptions" :series="stornoTrendSeries"/>
                  <div v-else class="empty">אין נתוני זמן.</div>
                </div>
                <div class="storno-chart">
                  <h4 class="sub-h">טופ סוכנים בביטולים</h4>
                  <apexchart v-if="topStorno.length" type="bar" height="220" :options="topStornoOptions" :series="topStornoSeries"/>
                  <div v-else class="empty">אין סטורנו לסוכנים.</div>
                </div>
              </div>
              <div v-else class="empty">טוען נתוני ביטולים…</div>
            </div>
          </template>

          <!-- 💰 חישוב — sub-agent splits + payslip -->
          <template v-else-if="activeSubTab === 'calculate'">
            <div class="card section-card">
              <div class="card-h">
                <div>
                  <span class="section-eyebrow">פיצול עמלות · 13:30 - 15:30</span>
                  <h3>חישוב עמלות סוכני משנה — ברוטו · Override · נטו</h3>
                </div>
                <div class="override-control">
                  <label>Override %</label>
                  <input type="range" min="0" max="50" :value="overridePctUi" @input="onOverrideInput" @change="reloadSplits" />
                  <span class="override-val ltr-number">{{ overridePctUi }}%</span>
                </div>
              </div>
              <div v-if="splits" class="splits-summary">
                <div class="split-stat">
                  <span class="lbl">סך ברוטו (שולם בפועל)</span>
                  <span class="val ltr-number">{{ formatShort(splits.totals.gross) }}</span>
                </div>
                <div class="split-stat split-override">
                  <span class="lbl">Override לסוכנות</span>
                  <span class="val ltr-number">{{ formatShort(splits.totals.override) }}</span>
                </div>
                <div class="split-stat split-net">
                  <span class="lbl">נטו לסוכני המשנה</span>
                  <span class="val ltr-number">{{ formatShort(splits.totals.net) }}</span>
                </div>
              </div>
              <apexchart
                v-if="topSplits.length"
                type="bar"
                :height="Math.max(260, topSplits.length * 36)"
                :options="splitsOptions"
                :series="splitsSeries"
              />
              <div v-else class="empty">אין נתוני עמלות עדיין — אין שולם בפועל לחישוב.</div>
            </div>

            <div class="card section-card">
              <div class="card-h">
                <div>
                  <span class="section-eyebrow">תלוש לסוכן · אישי</span>
                  <h3>תלוש עמלות לסוכן — בחר סוכן לפירוט</h3>
                </div>
                <select class="agent-picker" v-model="selectedPayslipAgent" @change="loadPayslip">
                  <option :value="''">— בחר סוכן —</option>
                  <option v-for="a in agents" :key="a.user_id" :value="a.user_id">{{ a.full_name }}</option>
                </select>
              </div>

              <div v-if="payslip" class="payslip">
                <div class="payslip-head">
                  <div class="payslip-title">
                    <span class="payslip-avatar">{{ initials(payslip.user.name) }}</span>
                    <div>
                      <h4>{{ payslip.user.name }}</h4>
                      <span class="payslip-email">{{ payslip.user.email }}</span>
                    </div>
                  </div>
                  <div class="payslip-net">
                    <span class="lbl">נטו לתשלום</span>
                    <span class="val ltr-number">{{ formatShort(payslip.totals.net) }}</span>
                  </div>
                </div>
                <div class="payslip-grid">
                  <div class="ps-stat ps-gross">
                    <span class="lbl">ברוטו (התקבל)</span>
                    <span class="val ltr-number">{{ formatShort(payslip.totals.gross) }}</span>
                  </div>
                  <div class="ps-stat ps-override">
                    <span class="lbl">Override</span>
                    <span class="val ltr-number">−{{ formatShort(payslip.totals.override) }}</span>
                  </div>
                  <div class="ps-stat ps-storno">
                    <span class="lbl">סטורנו</span>
                    <span class="val ltr-number">−{{ formatShort(payslip.totals.storno) }}</span>
                  </div>
                </div>
                <table v-if="payslip.lines.length" class="ps-table">
                  <thead>
                    <tr><th>תיאור</th><th class="num">פוליסות</th><th class="num">סכום</th></tr>
                  </thead>
                  <tbody>
                    <tr v-for="(l, i) in payslip.lines" :key="i" :class="l.kind">
                      <td>{{ l.label }}</td>
                      <td class="num">{{ l.policies }}</td>
                      <td class="num"><span class="ltr-number">{{ l.amount < 0 ? '−' : '' }}{{ formatShort(Math.abs(l.amount)) }}</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="empty">בחרו סוכן מהרשימה כדי לראות את התלוש שלו.</div>
            </div>
          </template>

          <!-- 📈 תכנון — forecast + reference distribution charts -->
          <template v-else-if="activeSubTab === 'plan'">
            <div class="card section-card">
              <div class="card-h">
                <div>
                  <span class="section-eyebrow">תחזית · 15:30 - 17:30</span>
                  <h3>תחזית עמלות renewals — 6 חודשים קדימה</h3>
                </div>
                <div v-if="forecast" class="forecast-tag">
                  <span :class="{ up: forecast.growth_rate > 0, down: forecast.growth_rate < 0 }">
                    <span v-if="forecast.growth_rate > 0">▲</span>
                    <span v-else-if="forecast.growth_rate < 0">▼</span>
                    <span class="ltr-number">{{ Math.abs(forecast.growth_rate) }}%</span>
                  </span>
                  קצב צמיחה
                </div>
              </div>
              <div v-if="forecast && (forecast.history.length || forecast.forecast.length)">
                <apexchart type="area" height="320" :options="forecastOptions" :series="forecastSeries"/>
                <p class="forecast-note">תחזית מבוססת ממוצע 3 החודשים האחרונים × קצב צמיחה. רצועת ביטחון ±15%.</p>
              </div>
              <div v-else class="empty">צריך לפחות חודש אחד של פרודוקציה כדי לחשב תחזית.</div>
            </div>

            <div class="charts-row">
              <div class="card chart-card">
                <h3>חלוקת נפרעים בסוכנות</h3>
                <apexchart v-if="donutSeries.length" type="donut" height="300" :options="donutOptions" :series="donutSeries"/>
                <div v-else class="empty">אין נתוני נפרעים עדיין</div>
              </div>
              <div class="card chart-card">
                <h3>טופ חברות — לא שולם</h3>
                <apexchart v-if="topUnpaidCo.length" type="bar" height="300" :options="topUnpaidCoOptions" :series="topUnpaidCoSeries"/>
                <div v-else class="empty">🎉 אין כרגע פערי נפרעים</div>
              </div>
            </div>
          </template>

          <!-- 👥 סוכנים — full leaderboard with drill-in -->
          <template v-else>
            <div class="card">
              <div class="card-h">
                <div>
                  <span class="section-eyebrow">תיק הסוכנים</span>
                  <h3>הסוכנים בסוכנות — לחץ על שורה לפירוט מלא</h3>
                </div>
                <span class="card-tag">{{ agents.length }} סוכנים</span>
              </div>
              <table v-if="agents.length" class="agents-table">
                <thead>
                  <tr>
                    <th>סוכן</th>
                    <th class="num">לקוחות</th>
                    <th class="num">פרמיה</th>
                    <th class="num">לא שולם</th>
                    <th class="num">חוסר ₪</th>
                    <th>העלאה אחרונה</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in agents" :key="row.user_id" class="clickable" @click="$emit('view-agent', row.user_id)">
                    <td class="name">
                      <span class="avatar">{{ initials(row.full_name) }}</span>
                      <div class="name-block">
                        <div class="name-line">{{ row.full_name }}</div>
                        <div class="email">{{ row.email }}</div>
                      </div>
                    </td>
                    <td class="num"><span class="ltr-number">{{ row.unique_clients.toLocaleString('he-IL') }}</span></td>
                    <td class="num"><span class="ltr-number">{{ formatShort(row.total_premium) }}</span></td>
                    <td class="num"><span class="ltr-number">{{ unpaidCountFor(row.user_id).toLocaleString('he-IL') }}</span></td>
                    <td class="num warn"><span class="ltr-number">{{ formatShort(row.lost_money_amount) }}</span></td>
                    <td class="muted">{{ formatDate(row.last_upload_at) }}</td>
                  </tr>
                </tbody>
              </table>
              <div v-else class="empty">אין סוכנים בסוכנות עדיין.</div>
            </div>
          </template>

        </div>
      </Transition>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAgencyStore } from '../../stores/agency.js'
import api from '../../api/client.js'

const agencyStore = useAgencyStore()
defineEmits(['view-agent'])

const loading = ref(true)
const comparison = computed(() => agencyStore.comparison)
const agents = computed(() => agencyStore.agents)

// Daily-workflow data
const splits = ref(null)
const storno = ref(null)
const forecast = ref(null)
const aging = ref(null)
const targets = ref(null)
const payslip = ref(null)
const selectedPayslipAgent = ref('')
const overridePctUi = ref(20)

// ── Sub-tabs (in-page navigation under the sticky monitor) ──
const SUB_TABS = [
  {
    id: 'reconcile',
    label: 'פיוס',
    accent: '#E8720A',
    accentGlow: 'rgba(232, 114, 10, 0.14)',
    tooltip: 'בוקר 11:00 - 13:30  ·  טיפול בחריגים, ערעורים וסטורנו',
    icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 01-2 2H5a2 2 0 01-2-2V5a2 2 0 012-2h11"/></svg>',
  },
  {
    id: 'calculate',
    label: 'חישוב',
    accent: '#6366f1',
    accentGlow: 'rgba(99, 102, 241, 0.14)',
    tooltip: 'צהריים 13:30 - 15:30  ·  פיצול עמלות סוכני משנה ותלוש',
    icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2"/><line x1="8" y1="6" x2="16" y2="6"/><line x1="16" y1="14" x2="16" y2="18"/><line x1="8" y1="10" x2="16" y2="10"/><line x1="8" y1="14" x2="12" y2="14"/><line x1="8" y1="18" x2="12" y2="18"/></svg>',
  },
  {
    id: 'plan',
    label: 'תכנון',
    accent: '#2E844A',
    accentGlow: 'rgba(46, 132, 74, 0.14)',
    tooltip: 'אחה"צ 15:30 - 17:30  ·  תחזית renewals וחלוקות',
    icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 17 9 11 13 15 21 7"/><polyline points="14 7 21 7 21 14"/></svg>',
  },
  {
    id: 'agents',
    label: 'סוכנים',
    accent: '#7F56D9',
    accentGlow: 'rgba(127, 86, 217, 0.14)',
    tooltip: 'תמיד נגיש  ·  כל הסוכנים בסוכנות עם דריל-אין',
    icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>',
  },
]
const subTabs = SUB_TABS
const STORAGE_KEY = 'agents_subtab'
const activeSubTab = ref(
  (typeof localStorage !== 'undefined' && localStorage.getItem(STORAGE_KEY)) || 'reconcile'
)
function setSubTab(id) {
  activeSubTab.value = id
  try { localStorage.setItem(STORAGE_KEY, id) } catch { /* ignore quota errors */ }
}

let overrideTimer = null
function onOverrideInput(e) { overridePctUi.value = parseInt(e.target.value, 10) || 0 }
async function reloadSplits() {
  clearTimeout(overrideTimer)
  overrideTimer = setTimeout(async () => {
    const pct = overridePctUi.value / 100
    splits.value = (await api.get('/agency/sub-agent-splits', { params: { override_pct: pct } })).data
    if (selectedPayslipAgent.value) await loadPayslip()
  }, 200)
}

async function loadPayslip() {
  if (!selectedPayslipAgent.value) { payslip.value = null; return }
  const pct = overridePctUi.value / 100
  payslip.value = (await api.get(`/agency/agent-payslip/${selectedPayslipAgent.value}`, { params: { override_pct: pct } })).data
}

onMounted(async () => {
  loading.value = true
  await Promise.all([
    agencyStore.comparison ? Promise.resolve() : agencyStore.fetchComparison(),
    agencyStore.agents?.length ? Promise.resolve() : agencyStore.fetchAgents(),
    api.get('/agency/sub-agent-splits').then(r => splits.value = r.data),
    api.get('/agency/storno').then(r => storno.value = r.data),
    api.get('/agency/renewal-forecast').then(r => forecast.value = r.data),
    api.get('/agency/exceptions-aging').then(r => aging.value = r.data),
    api.get('/agency/target-achievement').then(r => targets.value = r.data),
  ])
  loading.value = false
})

const agentCount = computed(() => agents.value?.length || 0)

// ── Donut: matched vs unpaid ──
const donutSeries = computed(() => {
  if (!comparison.value) return []
  const s = comparison.value.summary
  const arr = []
  if (s.matched_count) arr.push(s.matched_count)
  if (s.unpaid_count) arr.push(s.unpaid_count)
  return arr
})
const donutLabels = computed(() => {
  if (!comparison.value) return []
  const s = comparison.value.summary
  const labels = []
  if (s.matched_count) labels.push('נמצא בשניהם')
  if (s.unpaid_count) labels.push('לא שולם')
  return labels
})
const donutOptions = computed(() => ({
  chart: { type: 'donut', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  labels: donutLabels.value,
  colors: ['#2E844A', '#E8720A'],
  legend: { position: 'bottom', fontSize: '12.5px', markers: { width: 10, height: 10 } },
  dataLabels: { enabled: true, formatter: (v) => `${Math.round(v)}%` },
  stroke: { width: 2, colors: ['#fff'] },
  plotOptions: { pie: { donut: { size: '60%' } } },
  tooltip: { y: { formatter: (v) => v.toLocaleString('he-IL') + ' רשומות' } },
}))

// ── Top companies by unpaid count ──
const topUnpaidCo = computed(() => (comparison.value?.by_company || []).filter(c => c.unpaid > 0).slice(0, 8))
const topUnpaidCoSeries = computed(() => [{ name: 'לא שולם', data: topUnpaidCo.value.map(c => c.unpaid) }])
const topUnpaidCoOptions = computed(() => ({
  chart: { type: 'bar', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  plotOptions: { bar: { horizontal: true, distributed: true, borderRadius: 4, barHeight: '70%' } },
  colors: ['#E8720A', '#FF9800', '#FFB74D', '#FFCC80', '#C68A2E', '#7F56D9', '#0891b2', '#22d3ee'],
  legend: { show: false },
  xaxis: { categories: topUnpaidCo.value.map(c => shortCo(c.company)), labels: { style: { fontSize: '10.5px' } } },
  yaxis: { labels: { style: { fontSize: '11px', fontWeight: 600 } } },
  dataLabels: { enabled: true, formatter: (v) => v.toLocaleString('he-IL'), style: { fontSize: '10px', fontWeight: 700, colors: ['#fff'] } },
  grid: { strokeDashArray: 3 },
}))

// ── Sub-agent splits chart ──
const topSplits = computed(() => (splits.value?.rows || []).filter(r => r.gross > 0).slice(0, 10))
const splitsSeries = computed(() => [
  { name: 'נטו לסוכן', data: topSplits.value.map(r => Math.round(r.net)) },
  { name: 'Override לסוכנות', data: topSplits.value.map(r => Math.round(r.override)) },
])
const splitsOptions = computed(() => ({
  chart: { type: 'bar', stacked: true, fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: '70%' } },
  colors: ['#2E844A', '#F57C00'],
  legend: { position: 'bottom', fontSize: '12px' },
  xaxis: {
    categories: topSplits.value.map(r => r.name),
    labels: { formatter: (v) => '₪' + Math.round(Number(v)).toLocaleString('he-IL'), style: { fontSize: '10.5px' } },
  },
  yaxis: { labels: { style: { fontSize: '11.5px', fontWeight: 600 } } },
  dataLabels: { enabled: false },
  tooltip: { y: { formatter: (v) => '₪ ' + Math.round(v).toLocaleString('he-IL') }, shared: true },
  grid: { strokeDashArray: 3 },
}))

// ── Storno charts ──
const stornoTrendSeries = computed(() => [{ name: 'מספר ביטולים', data: (storno.value?.by_month || []).map(m => m.count) }])
const stornoTrendOptions = computed(() => ({
  chart: { type: 'line', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  colors: ['#8C1D2A'],
  stroke: { curve: 'smooth', width: 3 },
  markers: { size: 5, colors: ['#fff'], strokeColors: '#8C1D2A', strokeWidth: 2.5 },
  xaxis: { categories: (storno.value?.by_month || []).map(m => m.period), labels: { style: { fontSize: '10.5px' } } },
  yaxis: { labels: { style: { fontSize: '10.5px' } } },
  grid: { strokeDashArray: 3 },
  tooltip: { y: { formatter: (v) => v.toLocaleString('he-IL') + ' ביטולים' } },
}))

const topStorno = computed(() => (storno.value?.by_agent || []).slice(0, 8))
const topStornoSeries = computed(() => [{ name: 'ביטולים', data: topStorno.value.map(r => r.count) }])
const topStornoOptions = computed(() => ({
  chart: { type: 'bar', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  plotOptions: { bar: { horizontal: true, distributed: true, borderRadius: 4, barHeight: '70%' } },
  colors: ['#8C1D2A', '#A1313F', '#B6485C', '#C66072', '#D67890', '#E8720A', '#C68A2E', '#FFA726'],
  legend: { show: false },
  xaxis: { categories: topStorno.value.map(r => r.name), labels: { style: { fontSize: '10.5px' } } },
  yaxis: { labels: { style: { fontSize: '10.5px', fontWeight: 600 } } },
  dataLabels: { enabled: true, formatter: (v) => v.toLocaleString('he-IL'), style: { fontSize: '10px', fontWeight: 700, colors: ['#fff'] } },
  grid: { strokeDashArray: 3 },
}))

// ── Renewal forecast ──
const forecastSeries = computed(() => {
  if (!forecast.value) return []
  const hist = forecast.value.history.map(h => h.amount)
  const proj = forecast.value.forecast.map(f => f.amount)
  const low  = forecast.value.forecast.map(f => f.low)
  const high = forecast.value.forecast.map(f => f.high)
  return [
    { name: 'היסטוריה', data: [...hist, ...new Array(proj.length).fill(null)] },
    { name: 'תחזית',     data: [...new Array(hist.length).fill(null), ...proj] },
    { name: 'גבול עליון', data: [...new Array(hist.length).fill(null), ...high] },
    { name: 'גבול תחתון', data: [...new Array(hist.length).fill(null), ...low] },
  ]
})
const forecastOptions = computed(() => ({
  chart: { type: 'area', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  colors: ['#6366f1', '#F57C00', 'rgba(245, 124, 0, 0.25)', 'rgba(245, 124, 0, 0.25)'],
  stroke: { curve: 'smooth', width: [3, 3, 1, 1], dashArray: [0, 6, 0, 0] },
  fill: { type: 'gradient', gradient: { shadeIntensity: 1, opacityFrom: 0.4, opacityTo: 0.04 } },
  markers: { size: [5, 5, 0, 0], colors: ['#fff'], strokeColors: ['#6366f1', '#F57C00'], strokeWidth: 2.5 },
  legend: { position: 'bottom', fontSize: '12px' },
  xaxis: {
    categories: [
      ...(forecast.value?.history || []).map(h => h.period),
      ...(forecast.value?.forecast || []).map(f => f.period),
    ],
    labels: { style: { fontSize: '10.5px' } },
  },
  yaxis: { labels: { formatter: (v) => '₪' + Math.round(Number(v) / 1000) + 'K', style: { fontSize: '10.5px' } } },
  tooltip: { y: { formatter: (v) => v == null ? '—' : '₪ ' + Math.round(v).toLocaleString('he-IL') } },
  grid: { strokeDashArray: 3 },
}))

// ── Aging buckets ──
const agingBucketsSeries = computed(() => [
  { name: 'מספר רשומות', data: (aging.value?.buckets || []).map(b => b.count) },
])
const agingBucketsOptions = computed(() => ({
  chart: { type: 'bar', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  plotOptions: { bar: { horizontal: false, distributed: true, borderRadius: 8, columnWidth: '55%' } },
  colors: ['#FFB74D', '#E8720A', '#8C1D2A'],
  legend: { show: false },
  xaxis: { categories: (aging.value?.buckets || []).map(b => `${b.bucket} ימים`), labels: { style: { fontSize: '11.5px', fontWeight: 600 } } },
  yaxis: { labels: { style: { fontSize: '10.5px' } } },
  dataLabels: { enabled: true, formatter: (v) => v.toLocaleString('he-IL'), style: { fontSize: '12px', fontWeight: 800, colors: ['#fff'] } },
  tooltip: { y: { formatter: (v) => v.toLocaleString('he-IL') + ' רשומות' } },
  grid: { strokeDashArray: 3 },
}))

const agingCoSeries = computed(() => [
  { name: 'גיל מקסימלי (ימים)', data: (aging.value?.by_company || []).map(c => c.oldest_age) },
])
const agingCoOptions = computed(() => ({
  chart: { type: 'bar', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
  plotOptions: { bar: { horizontal: true, distributed: true, borderRadius: 4, barHeight: '70%' } },
  colors: ['#8C1D2A', '#A1313F', '#B6485C', '#C66072', '#D67890', '#E8720A', '#C68A2E', '#FFA726', '#FFB74D', '#FFCC80'],
  legend: { show: false },
  xaxis: { categories: (aging.value?.by_company || []).map(c => shortCo(c.company)), labels: { style: { fontSize: '10.5px' } } },
  yaxis: { labels: { style: { fontSize: '10.5px', fontWeight: 600 } } },
  dataLabels: { enabled: true, formatter: (v) => v + 'ה', style: { fontSize: '10px', fontWeight: 700, colors: ['#fff'] } },
  tooltip: { y: { formatter: (v) => v + ' ימים' } },
  grid: { strokeDashArray: 3 },
}))

// ── Target achievement ──
const topGauges = computed(() => (targets.value?.by_company || []).slice(0, 5))
const topPerformers = computed(() => targets.value?.top_performers || [])

function gaugeColor(pct) {
  // pct = % of last month's premium. 100% = unchanged, >100 = grew, <100 = shrank.
  if (pct >= 100) return '#2E844A'  // green — grew or stable
  if (pct >= 80) return '#F57C00'   // orange — slight decline
  return '#C23934'                  // Nifraim --red-deep — significant decline
}
// Compact monitor variant — small dial, no padding, used in the sticky monitor row
function miniGaugeOptions(pct, color, isNew = false) {
  return {
    chart: { type: 'radialBar', fontFamily: 'Heebo, sans-serif', toolbar: { show: false }, sparkline: { enabled: true } },
    colors: [color],
    plotOptions: {
      radialBar: {
        startAngle: -135, endAngle: 135, hollow: { size: '50%' },
        track: { background: '#F0EBE7', strokeWidth: '100%', margin: 0 },
        dataLabels: {
          name: { show: false },
          value: {
            fontSize: '13px', fontWeight: 900, color: '#2D2522', offsetY: 4,
            formatter: () => isNew ? 'חדש' : Math.round(pct) + '%',
          },
        },
      },
    },
    stroke: { lineCap: 'round' },
    fill: { type: 'gradient', gradient: { shade: 'light', type: 'horizontal', shadeIntensity: 0.5, gradientToColors: [color], opacityFrom: 0.85, opacityTo: 1, stops: [0, 100] } },
  }
}

function gaugeOptions(pct, color, isNew = false) {
  return {
    chart: { type: 'radialBar', fontFamily: 'Heebo, sans-serif', toolbar: { show: false } },
    colors: [color],
    plotOptions: {
      radialBar: {
        startAngle: -135, endAngle: 135, hollow: { size: '60%' },
        track: { background: '#F0EBE7', strokeWidth: '100%', margin: 0 },
        dataLabels: {
          name: { show: false },
          value: {
            fontSize: '24px', fontWeight: 900, color: '#2D2522', offsetY: 8,
            formatter: () => isNew ? 'חדש' : Math.round(pct) + '%',
          },
        },
      },
    },
    stroke: { lineCap: 'round' },
    fill: { type: 'gradient', gradient: { shade: 'light', type: 'horizontal', shadeIntensity: 0.5, gradientToColors: [color], opacityFrom: 0.85, opacityTo: 1, stops: [0, 100] } },
  }
}
function deltaClass(g) {
  if (g.is_new) return 'delta-new'
  if (g.change_pct > 0) return 'delta-up'
  if (g.change_pct < 0) return 'delta-down'
  return 'delta-flat'
}

// ── Per-agent unpaid map ──
const unpaidByAgent = computed(() => {
  const m = new Map()
  for (const a of comparison.value?.by_agent || []) m.set(a.user_id, a.unpaid)
  return m
})
function unpaidCountFor(uid) { return unpaidByAgent.value.get(uid) || 0 }

// ── helpers ──
function initials(name) {
  if (!name) return '?'
  return name.split(/\s+/).slice(0, 2).map(p => (p || '')[0] || '').join('').toUpperCase()
}
function shortCo(s) {
  if (!s) return ''
  return s.replace(/\s*חברה\s*לביטוח/g, '').replace(/\s*בע"מ/g, '').replace(/\s*בע״מ/g, '').replace(/\s*ופנסיה/g, '').trim()
}
function formatShort(v) {
  if (v == null || v === 0) return '₪0'
  const n = Number(v)
  if (n >= 1_000_000) return '₪' + (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000) return '₪' + Math.round(n / 1_000) + 'K'
  return '₪' + Math.round(n).toLocaleString('he-IL')
}
function formatDate(iso) {
  if (!iso) return 'לא הועלה'
  return new Date(iso).toLocaleDateString('he-IL', { day: '2-digit', month: 'short', year: 'numeric' })
}
function ageClass(age) {
  if (age <= 30) return 'age-fresh'
  if (age <= 60) return 'age-mid'
  return 'age-old'
}
function emailDraft(o) {
  const subject = encodeURIComponent(`בירור עמלה לא משולמת — ${o.company} — לקוח ${o.client_id_number || ''}`)
  const body = encodeURIComponent(
    `שלום,\n\nאני מבקש בירור לגבי עמלה שלא התקבלה:\n\n` +
    `חברה: ${o.company}\n` +
    `סוכן: ${o.agent_name}\n` +
    `לקוח: ${o.client_name || ''}  ת.ז: ${o.client_id_number || ''}\n` +
    `סכום צפוי: ₪${Math.round(o.expected_amount).toLocaleString('he-IL')}\n` +
    `סטטוס: ${o.status}\n` +
    `גיל: ${o.age_days} ימים\n\n` +
    `אבקש בדיקה ועדכון.\nתודה,\nחשב עמלות`
  )
  return `mailto:?subject=${subject}&body=${body}`
}
</script>

<style scoped>
.agents-tab {
  display: flex; flex-direction: column; gap: 16px;
  padding: 0 4px;
}
.state { padding: 80px; text-align: center; color: var(--text-muted); }
.spinner {
  width: 36px; height: 36px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin .8s linear infinite;
  margin: 0 auto 16px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.empty { padding: 50px 20px; text-align: center; color: var(--text-muted); font-size: 13.5px; }

/* ─── Sticky monitor (always-on dashboard at top) ─── */
.monitor {
  position: sticky;
  /* Sticks below: page header (~58px) + workspace tab strip (~70px) + small breathing */
  top: 132px;
  z-index: 90;
  background: var(--bg);
  display: flex; flex-direction: column; gap: 10px;
  padding: 10px 0 14px;
  margin-top: -4px;  /* hug the workspace tab strip above */
  border-bottom: 1px solid var(--border-subtle);
}
.monitor-row {
  display: grid;
  grid-template-columns: 1fr minmax(220px, 280px);
  gap: 12px;
  align-items: stretch;
}

/* Mini gauges strip */
.mini-gauges-strip {
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px 14px 12px;
  box-shadow: var(--shadow-sm);
  display: flex; flex-direction: column; gap: 6px;
}
.mg-eyebrow {
  display: flex; justify-content: space-between; align-items: center;
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.6px; text-transform: uppercase;
  color: var(--text-muted);
  padding: 0 2px;
}
.mg-period {
  background: var(--bg);
  padding: 2px 9px; border-radius: 999px;
  font-size: 10px; font-weight: 700; color: var(--text-secondary);
  text-transform: none; letter-spacing: 0;
}
/* Horizontal flex strip — fixed-width gauges. Scrolls if narrower than 5×116. */
.mg-grid {
  display: flex;
  gap: 6px;
  overflow-x: auto;
  overflow-y: hidden;
  scrollbar-width: thin;
  scrollbar-color: var(--border) transparent;
  padding-bottom: 2px;
}
.mg-grid::-webkit-scrollbar { height: 4px; }
.mg-grid::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
.mini-gauge {
  flex: 0 0 116px;       /* fixed — never shrinks below readable size */
  text-align: center;
  min-width: 0;
}
.mini-gauge-label {
  font-size: 11px; font-weight: 700; color: var(--text);
  margin-top: -4px; line-height: 1.2;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  max-width: 110px; margin-inline: auto;
}
.mini-gauge-delta {
  font-size: 10px; font-weight: 800; margin-top: 3px;
  padding: 2px 7px; border-radius: 999px;
  display: inline-block;
}
.mini-gauge-delta.delta-up   { background: var(--green-light); color: var(--green); }
.mini-gauge-delta.delta-down { background: var(--red-light); color: var(--red-deep); }
.mini-gauge-delta.delta-flat { background: var(--bg); color: var(--text-muted); }
.mini-gauge-delta.delta-new  { background: rgba(127, 86, 217, 0.10); color: var(--accent-violet); }
.mg-empty { padding: 30px 10px; text-align: center; color: var(--text-muted); font-size: 12px; }

/* Mini podium */
.mini-podium {
  background: #FFFFFF;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px 14px;
  box-shadow: var(--shadow-sm);
  display: flex; flex-direction: column; gap: 4px;
}
.mp-eyebrow {
  font-size: 10.5px; font-weight: 700; letter-spacing: 0.6px; text-transform: uppercase;
  color: var(--text-muted); margin-bottom: 4px;
}
.mp-chip {
  display: grid;
  grid-template-columns: auto 1fr auto;
  gap: 8px; align-items: center;
  padding: 6px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: background .12s var(--transition), transform .12s var(--transition);
  border: 1px solid transparent;
}
.mp-chip:hover { background: var(--bg); transform: translateX(-2px); }
.mp-chip.rank-1 {
  background: linear-gradient(90deg, rgba(255, 224, 130, 0.25) 0%, transparent 70%);
  border-color: rgba(255, 215, 0, 0.35);
}
.mp-chip.rank-2 {
  background: linear-gradient(90deg, rgba(207, 216, 220, 0.35) 0%, transparent 70%);
  border-color: rgba(176, 190, 197, 0.5);
}
.mp-chip.rank-3 {
  background: linear-gradient(90deg, rgba(255, 204, 128, 0.30) 0%, transparent 70%);
  border-color: rgba(255, 152, 0, 0.3);
}
/* Numbered rank chip — metallic gradient pills, no emoji */
.mp-rank {
  flex-shrink: 0;
  width: 22px; height: 22px;
  border-radius: 6px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: 11.5px; font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.3px;
}
.mp-rank-1 {
  background: linear-gradient(135deg, #F5C77E 0%, #C99843 100%);
  color: #5A3D11;
  box-shadow: 0 1px 2px rgba(201, 152, 67, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.4);
}
.mp-rank-2 {
  background: linear-gradient(135deg, #D9DDE2 0%, #9BA3AC 100%);
  color: #2E353C;
  box-shadow: 0 1px 2px rgba(155, 163, 172, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.4);
}
.mp-rank-3 {
  background: linear-gradient(135deg, #DDA571 0%, #B27340 100%);
  color: #4A2A0F;
  box-shadow: 0 1px 2px rgba(178, 115, 64, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.3);
}
.mp-name {
  font-size: 12.5px; font-weight: 700; color: var(--text);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.mp-prem {
  font-size: 11.5px; font-weight: 800; color: var(--primary-deep);
  background: var(--primary-light);
  padding: 2px 8px; border-radius: 999px;
}

/* ─── Sub-tab strip (in-page navigation) ─── */
.sub-tabs {
  display: flex; gap: 4px;
  padding: 5px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  margin-top: 8px;
  align-self: flex-start;
  flex-wrap: wrap;
}
.sub-pill {
  display: inline-flex; align-items: center; gap: 6px;
  background: transparent;
  border: none;
  padding: 8px 14px;
  border-radius: 8px;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  transition: all .15s var(--transition);
  position: relative;
}
.sub-pill:hover { color: var(--text); background: rgba(255, 255, 255, 0.5); }
.sub-pill.active {
  background: #FFFFFF;
  color: var(--accent);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.06);
  font-weight: 800;
}
.sub-pill.active::after {
  content: ''; position: absolute;
  bottom: -2px; right: 12px; left: 12px;
  height: 3px; background: var(--accent); border-radius: 2px;
}
.sub-pill .sub-icon { display: inline-flex; }
.sub-pill .sub-icon svg { display: block; }

/* Sub-content fade transition */
.sub-content {
  display: flex; flex-direction: column; gap: 14px;
  margin-top: 8px;
}
.sub-fade-enter-active, .sub-fade-leave-active {
  transition: opacity .18s var(--transition), transform .18s var(--transition);
}
.sub-fade-enter-from { opacity: 0; transform: translateY(6px); }
.sub-fade-leave-to   { opacity: 0; transform: translateY(-6px); }

/* KPI strip */
.kpi-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; }
.kpi {
  background: #FFFFFF; border: 1px solid var(--border);
  border-radius: 12px; padding: 14px 16px;
  display: flex; align-items: center; gap: 12px;
  box-shadow: var(--shadow-sm);
  position: relative; overflow: hidden;
}
.kpi::before { content: ''; position: absolute; inset: 0 0 auto 0; height: 3px; }
.kpi-blue::before    { background: #6366f1; }
.kpi-cyan::before    { background: #22d3ee; }
.kpi-amber::before   { background: #E8720A; }
.kpi-emerald::before { background: #2E844A; }
.kpi-red::before     { background: var(--red-deep); }
.kpi-icon {
  width: 38px; height: 38px; border-radius: 10px;
  display: inline-flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.kpi-blue    .kpi-icon { background: rgba(99, 102, 241, 0.10); color: #4f46e5; }
.kpi-cyan    .kpi-icon { background: rgba(34, 211, 238, 0.10); color: #0891b2; }
.kpi-amber   .kpi-icon { background: rgba(232, 114, 10, 0.10); color: #E8720A; }
.kpi-emerald .kpi-icon { background: var(--green-light); color: var(--green); }
.kpi-red     .kpi-icon { background: var(--red-light); color: var(--red-deep); }
.kpi-data { min-width: 0; }
.kpi-value { font-size: 22px; font-weight: 800; color: var(--text); letter-spacing: -0.4px; line-height: 1; }
.kpi-label { font-size: 12px; color: var(--text-muted); margin-top: 4px; }

/* Generic cards */
.card { background: #FFFFFF; border: 1px solid var(--border); border-radius: 14px; padding: 16px 18px; box-shadow: var(--shadow-sm); }
.section-card { padding: 18px 20px; }
.section-eyebrow {
  display: inline-block;
  font-size: 10.5px; font-weight: 700; letter-spacing: 1.2px;
  text-transform: uppercase;
  color: var(--primary-deep);
  background: var(--primary-light);
  padding: 3px 10px; border-radius: 999px;
  margin-bottom: 6px;
}
.card-h { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 10px; gap: 14px; }
.card-h h3 { font-size: 14.5px; font-weight: 700; color: var(--text); }
.card-tag { font-size: 11px; color: var(--text-muted); }
.sub-h { font-size: 12px; font-weight: 700; color: var(--text-muted); letter-spacing: 0.4px; text-transform: uppercase; margin-bottom: 6px; }

.row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

/* ─── MoM gauges (full-width, breathing room) ─── */
.section-sub { font-size: 12px; color: var(--text-muted); margin-top: 4px; line-height: 1.5; max-width: 720px; }
.gauges-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
  gap: 16px;
  padding: 14px 4px 4px;
}
.gauge-card {
  text-align: center;
  background: linear-gradient(180deg, #FFFFFF 0%, #FAF6F2 100%);
  border: 1px solid var(--border-subtle);
  border-radius: 14px;
  padding: 14px 10px 16px;
  transition: transform .2s var(--transition), box-shadow .2s var(--transition);
}
.gauge-card:hover { transform: translateY(-2px); box-shadow: 0 12px 24px -14px rgba(0, 0, 0, 0.18); }
.gauge-label {
  font-size: 13px; font-weight: 800; color: var(--text);
  margin-top: -10px; line-height: 1.2;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  padding: 0 6px;
}
.gauge-meta {
  font-size: 11.5px; color: var(--text-muted); margin-top: 6px;
  display: inline-flex; align-items: center; gap: 6px;
  background: var(--bg);
  padding: 4px 10px; border-radius: 999px;
  font-variant-numeric: tabular-nums;
}
.g-actual { color: var(--text); font-weight: 800; }
.g-vs { color: var(--text-muted); font-size: 10px; opacity: 0.6; }
.g-prev { color: var(--text-muted); font-weight: 600; }
.gauge-delta {
  font-size: 11.5px; font-weight: 800; margin-top: 8px;
  padding: 4px 10px; border-radius: 999px;
  display: inline-block;
}
.gauge-delta.delta-up   { background: var(--green-light); color: var(--green); }
.gauge-delta.delta-down { background: var(--red-light); color: var(--red-deep); }
.gauge-delta.delta-flat { background: var(--bg); color: var(--text-muted); }
.gauge-delta.delta-new  { background: rgba(127, 86, 217, 0.12); color: var(--accent-violet); }

/* ─── Top performers podium ─── */
.podium { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
.podium-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 14px;
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  cursor: pointer;
  transition: all .15s var(--transition);
}
.podium-item:hover { background: rgba(245, 124, 0, 0.05); transform: translateX(-2px); border-color: var(--primary); }
.podium-item.rank-1 { background: linear-gradient(135deg, #FFF8E1 0%, #FFE082 100%); border-color: rgba(255, 215, 0, 0.4); }
.podium-item.rank-2 { background: linear-gradient(135deg, #ECEFF1 0%, #CFD8DC 100%); border-color: #B0BEC5; }
.podium-item.rank-3 { background: linear-gradient(135deg, #FFF3E0 0%, #FFCC80 100%); border-color: rgba(255, 152, 0, 0.3); }
.podium-rank {
  flex: 0 0 28px; width: 28px; height: 28px; border-radius: 50%;
  background: #2D2522; color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 13px;
}
.podium-avatar {
  flex: 0 0 36px; width: 36px; height: 36px; border-radius: 50%;
  background: linear-gradient(135deg, #FFD180, #E8660A);
  color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 13px;
  box-shadow: 0 4px 8px rgba(232, 102, 10, 0.32);
}
.podium-text { flex: 1; min-width: 0; }
.podium-name { font-weight: 700; color: var(--text); font-size: 13.5px; }
.podium-meta { font-size: 11.5px; color: var(--text-muted); margin-top: 2px; }
.podium-medal { font-size: 22px; }

/* ─── Aging exceptions ─── */
.aging-grid { margin-bottom: 14px; }
.oldest-h { font-size: 13px; font-weight: 700; color: var(--text); margin: 18px 0 8px; padding-right: 4px; }
.age-pill { font-size: 11px; font-weight: 800; padding: 3px 9px; border-radius: 999px; }
.age-fresh { background: rgba(255, 183, 77, 0.18); color: var(--primary-deep); }
.age-mid   { background: rgba(232, 114, 10, 0.18); color: #C85A00; }
.age-old   { background: var(--red-light); color: var(--red-deep); }
.follow-up-btn {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 7px;
  padding: 5px 10px;
  font-size: 11.5px; font-weight: 600;
  color: var(--text-secondary);
  text-decoration: none;
  transition: all .12s;
}
.follow-up-btn:hover { background: var(--primary); color: #fff; border-color: var(--primary); }

/* ─── Sub-agent splits ─── */
.override-control {
  display: inline-flex; align-items: center; gap: 8px;
  background: var(--bg);
  padding: 6px 12px; border-radius: 999px;
  border: 1px solid var(--border-subtle);
  font-size: 12px; color: var(--text-secondary);
}
.override-control input[type="range"] { width: 110px; accent-color: var(--primary); }
.override-val {
  background: var(--primary); color: #fff;
  padding: 2px 9px; border-radius: 999px;
  font-size: 11.5px; font-weight: 800;
  min-width: 38px; text-align: center;
}
.splits-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 10px 0 14px; }
.split-stat {
  background: var(--bg);
  border: 1px solid var(--border-subtle);
  border-radius: 10px; padding: 10px 14px;
}
.split-stat .lbl { font-size: 11px; color: var(--text-muted); font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase; display: block; }
.split-stat .val { font-size: 18px; font-weight: 800; color: var(--text); display: block; margin-top: 2px; letter-spacing: -0.3px; }
.split-stat.split-override { border-top: 3px solid #F57C00; }
.split-stat.split-override .val { color: var(--primary-deep); }
.split-stat.split-net { border-top: 3px solid var(--green); }
.split-stat.split-net .val { color: var(--green); }

/* ─── Agent payslip ─── */
.agent-picker {
  padding: 7px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-family: inherit;
  font-size: 13px;
  background: #fff;
  color: var(--text);
  cursor: pointer;
  min-width: 220px;
}
.agent-picker:focus { border-color: var(--primary); outline: none; box-shadow: var(--shadow-glow); }
.payslip { display: flex; flex-direction: column; gap: 14px; margin-top: 10px; }
.payslip-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 14px 16px;
  background: linear-gradient(135deg, #FFF8F0 0%, #FFFFFF 100%);
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
}
.payslip-title { display: flex; align-items: center; gap: 12px; }
.payslip-avatar {
  width: 42px; height: 42px; border-radius: 50%;
  background: linear-gradient(135deg, #FFD180, #E8660A);
  color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 15px;
  box-shadow: 0 6px 12px rgba(232, 102, 10, 0.4);
}
.payslip-title h4 { font-size: 16px; font-weight: 800; color: var(--text); }
.payslip-email { font-size: 12px; color: var(--text-muted); }
.payslip-net { text-align: left; }
.payslip-net .lbl { font-size: 11px; font-weight: 700; color: var(--text-muted); letter-spacing: 0.4px; text-transform: uppercase; display: block; }
.payslip-net .val { font-size: 28px; font-weight: 900; color: var(--green); display: block; letter-spacing: -1px; }

.payslip-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
.ps-stat { background: var(--bg); border: 1px solid var(--border-subtle); border-radius: 10px; padding: 10px 14px; }
.ps-stat .lbl { font-size: 10.5px; font-weight: 700; color: var(--text-muted); letter-spacing: 0.4px; text-transform: uppercase; display: block; }
.ps-stat .val { font-size: 18px; font-weight: 800; color: var(--text); display: block; margin-top: 2px; }
.ps-gross    { border-top: 3px solid #6366f1; }
.ps-override { border-top: 3px solid #F57C00; }
.ps-override .val { color: var(--primary-deep); }
.ps-storno   { border-top: 3px solid var(--red-deep); }
.ps-storno .val { color: var(--red-deep); }

.ps-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ps-table th { text-align: right; font-size: 11px; color: var(--text-muted); font-weight: 700; padding: 8px 6px; border-bottom: 1px solid var(--border-subtle); }
.ps-table td { padding: 9px 6px; border-bottom: 1px solid var(--border-subtle); }
.ps-table tr:last-child td { border-bottom: none; }
.ps-table .num { text-align: center; }
.ps-table tr.deduction { background: rgba(140, 29, 42, 0.04); }
.ps-table tr.deduction td { color: var(--red-deep); font-weight: 600; }

/* ─── Storno ─── */
.storno-tag {
  font-size: 12.5px; color: var(--text-muted);
  background: rgba(140, 29, 42, 0.08);
  padding: 5px 12px; border-radius: 999px;
  border: 1px solid rgba(140, 29, 42, 0.18);
}
.storno-count, .storno-amount { color: var(--red-deep); font-weight: 800; margin: 0 4px; }
.storno-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }

/* ─── Forecast ─── */
.forecast-tag {
  font-size: 12.5px; color: var(--text-muted);
  background: var(--bg);
  padding: 5px 12px; border-radius: 999px;
  border: 1px solid var(--border-subtle);
  display: inline-flex; align-items: center; gap: 6px;
}
.forecast-tag .up { color: var(--green); font-weight: 800; }
.forecast-tag .down { color: var(--red-deep); font-weight: 800; }
.forecast-note {
  font-size: 11.5px; color: var(--text-muted);
  margin-top: 8px; line-height: 1.5; padding: 8px 12px;
  background: var(--bg); border-radius: 8px;
}

/* ─── Reference charts row ─── */
.charts-row { display: grid; grid-template-columns: 1fr 1.3fr; gap: 14px; }
.chart-card h3 { font-size: 14.5px; font-weight: 700; color: var(--text); margin-bottom: 8px; }

/* ─── Generic table (oldest list) ─── */
.ov-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.ov-table th { text-align: right; font-size: 11px; color: var(--text-muted); font-weight: 700; padding: 8px 6px; border-bottom: 1px solid var(--border-subtle); }
.ov-table td { padding: 9px 6px; border-bottom: 1px solid var(--border-subtle); }
.ov-table tr:last-child td { border-bottom: none; }
.ov-table tr.clickable { cursor: pointer; transition: background .12s; }
.ov-table tr.clickable:hover td { background: rgba(245, 124, 0, 0.05); }
.ov-table .num { text-align: center; }
.ov-table .num.warn .ltr-number { color: var(--red-deep); font-weight: 700; }
.ov-table .muted { color: var(--text-muted); font-size: 12px; }

/* ─── Agents leaderboard table ─── */
.agents-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.agents-table th { text-align: right; font-size: 11px; color: var(--text-muted); font-weight: 700; padding: 8px 6px; border-bottom: 1px solid var(--border-subtle); }
.agents-table td { padding: 11px 6px; border-bottom: 1px solid var(--border-subtle); }
.agents-table tr:last-child td { border-bottom: none; }
.agents-table tr.clickable { cursor: pointer; transition: background .12s; }
.agents-table tr.clickable:hover td { background: rgba(245, 124, 0, 0.05); }
.agents-table .num { text-align: center; }
.agents-table .num.warn .ltr-number { color: var(--red-deep); font-weight: 700; }
.agents-table .name { display: flex; align-items: center; gap: 10px; }
.agents-table .avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: linear-gradient(135deg, #FFD180, #E8660A);
  color: #fff;
  display: inline-flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 12px;
  box-shadow: 0 4px 8px rgba(232, 102, 10, 0.32);
}
.agents-table .name-line { font-weight: 700; color: var(--text); font-size: 13px; }
.agents-table .email { font-size: 11px; color: var(--text-muted); }
.agents-table .muted { color: var(--text-muted); font-size: 12px; }

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }

@media (max-width: 1100px) {
  .kpi-row { grid-template-columns: repeat(3, 1fr); }
  .charts-row, .row-2, .storno-grid, .splits-summary, .payslip-grid { grid-template-columns: 1fr; }
  .gauges-row { grid-template-columns: repeat(3, 1fr); }
  .monitor-row { grid-template-columns: 1fr; }
}
@media (max-width: 700px) {
  .kpi-row { grid-template-columns: repeat(2, 1fr); }
  .gauges-row { grid-template-columns: repeat(2, 1fr); }
  /* Stop stickying on mobile so the monitor doesn't eat half the screen */
  .monitor { position: static; }
  .sub-tabs { width: 100%; }
}
</style>
