<template>
  <Teleport to="body">
    <Transition name="yr-modal">
      <div
        v-if="open"
        class="yr-overlay"
        role="dialog"
        aria-modal="true"
        aria-label="המלצות לניוד תשואות"
        @click.self="close"
      >
        <div class="yr-card">
          <header class="yr-head">
            <div class="yr-head-left">
              <span class="yr-badge" aria-hidden="true">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
                  <polyline points="17 6 23 6 23 12"/>
                </svg>
              </span>
              <div class="yr-titles">
                <span class="yr-title">השוואת תשואות והמלצות ניוד</span>
                <span class="yr-sub">פרודוקציה × גמל-נט • דירוג לפי פוטנציאל שנתי</span>
              </div>
            </div>
            <button class="yr-icon-btn" type="button" title="סגור" @click="close">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"/>
                <line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </header>

          <div class="yr-body">
            <div v-if="loading && !recommendations.length" class="yr-state">
              <div class="yr-loader"></div>
              <span>טוען המלצות…</span>
            </div>

            <div v-else-if="error" class="yr-state yr-state--error">{{ error }}</div>

            <template v-else>
              <!-- Top summary strip -->
              <div class="yr-summary">
                <div class="yr-summary-block">
                  <span class="yr-summary-label">סה״כ המלצות</span>
                  <span class="yr-summary-value ltr-number">{{ filtered.length }}<span v-if="filtered.length !== recommendations.length" class="yr-summary-of">/ {{ recommendations.length }}</span></span>
                </div>
                <div class="yr-summary-block">
                  <span class="yr-summary-label">פוטנציאל שנתי מצרפי</span>
                  <span class="yr-summary-value yr-gain ltr-number">{{ fmt(filteredGain) }}</span>
                </div>
                <div class="yr-summary-block">
                  <span class="yr-summary-label">לקוחות ייחודיים</span>
                  <span class="yr-summary-value ltr-number">{{ uniqueClients }}</span>
                </div>
                <div class="yr-summary-block yr-summary-block--actions">
                  <button class="yr-btn yr-btn--ghost" type="button" :disabled="generating" @click="onGenerate">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="23 4 23 10 17 10"/>
                      <polyline points="1 20 1 14 7 14"/>
                      <path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
                    </svg>
                    <span>{{ generating ? 'מחשב…' : (recommendations.length ? 'רענן' : 'צור המלצות') }}</span>
                  </button>
                  <button
                    class="yr-btn yr-btn--primary"
                    type="button"
                    :disabled="!recommendations.length || downloading"
                    @click="onDownload"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                      <polyline points="7 10 12 15 17 10"/>
                      <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    <span>{{ downloading ? 'מייצא…' : 'הורד Excel' }}</span>
                  </button>
                </div>
              </div>

              <!-- Toolbar: view toggle + filters + search + sort -->
              <div v-if="recommendations.length" class="yr-toolbar">
                <div class="yr-view-toggle" role="tablist">
                  <button
                    role="tab"
                    type="button"
                    class="yr-view-btn"
                    :class="{ 'yr-view-btn--active': viewMode === 'groups' }"
                    :aria-selected="viewMode === 'groups'"
                    @click="viewMode = 'groups'"
                  >סיכום לפי מסלול יעד</button>
                  <button
                    role="tab"
                    type="button"
                    class="yr-view-btn"
                    :class="{ 'yr-view-btn--active': viewMode === 'flat' }"
                    :aria-selected="viewMode === 'flat'"
                    @click="viewMode = 'flat'"
                  >פירוט לפי לקוח</button>
                </div>

                <div class="yr-filters">
                  <input
                    v-model="searchQuery"
                    type="search"
                    class="yr-search"
                    placeholder="חפש לקוח / חברה / מוצר…"
                    aria-label="חיפוש"
                  />
                  <select v-model="filterMoveType" class="yr-select" aria-label="סוג מהלך">
                    <option value="all">כל המהלכים</option>
                    <option value="same">באותה רמת סיכון</option>
                    <option value="aggressive">אגרסיבי</option>
                  </select>
                  <select v-model="filterRisk" class="yr-select" aria-label="רמת סיכון">
                    <option value="all">כל הסיכונים</option>
                    <option value="general">כללי</option>
                    <option value="stocks">מניות</option>
                  </select>
                  <select v-if="viewMode === 'flat'" v-model="sortBy" class="yr-select" aria-label="מיון">
                    <option value="gain">מיין: פוטנציאל</option>
                    <option value="accum">מיין: צבירה</option>
                    <option value="client">מיין: לקוח</option>
                  </select>
                </div>
              </div>

              <!-- ── Group-by-destination view ─────────────────────────── -->
              <div v-if="viewMode === 'groups' && filtered.length" class="yr-groups">
                <article
                  v-for="g in grouped"
                  :key="g.track_id + g.risk"
                  class="yr-group-card"
                  :class="{ 'yr-group-card--aggressive': g.move_type === 'aggressive' }"
                >
                  <header class="yr-group-head">
                    <div class="yr-group-titles">
                      <div class="yr-group-title">
                        <span class="yr-group-name">{{ g.track_name }}</span>
                        <span v-if="g.fund_name" class="yr-group-fund">קרן מובילה: {{ g.fund_name }}</span>
                      </div>
                      <div class="yr-group-pills">
                        <span class="yr-pill" :class="`yr-pill--${g.risk}`">
                          {{ g.risk === 'stocks' ? 'מניות' : 'כללי' }}
                        </span>
                        <span class="yr-pill" :class="g.move_type === 'aggressive' ? 'yr-pill--aggressive' : 'yr-pill--same'">
                          {{ g.move_type === 'aggressive' ? 'אגרסיבי' : 'אותו סיכון' }}
                        </span>
                      </div>
                    </div>
                    <div class="yr-group-metrics">
                      <div class="yr-group-metric">
                        <span class="yr-group-metric-label">לקוחות</span>
                        <span class="yr-group-metric-value ltr-number">{{ g.clients }}</span>
                      </div>
                      <div class="yr-group-metric">
                        <span class="yr-group-metric-label">צבירה</span>
                        <span class="yr-group-metric-value ltr-number">{{ fmt(g.accum) }}</span>
                      </div>
                      <div class="yr-group-metric yr-group-metric--gain">
                        <span class="yr-group-metric-label">פוטנציאל</span>
                        <span class="yr-group-metric-value ltr-number">{{ fmt(g.gain) }}</span>
                      </div>
                    </div>
                  </header>
                  <div class="yr-group-yields">
                    <span>תשואה 3Y: <strong class="ltr-number">{{ fmtPct(g.y3) }}</strong></span>
                    <span>תשואה 5Y: <strong class="ltr-number">{{ fmtPct(g.y5) }}</strong></span>
                  </div>
                  <button class="yr-group-expand" type="button" @click="drilldownGroup = g">
                    הצג {{ g.items.length }} המלצות
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="15 18 9 12 15 6"/>
                    </svg>
                  </button>
                </article>
              </div>

              <!-- ── Flat view (cinematic ticker cards) ──────────────────────── -->
              <div v-else-if="viewMode === 'flat' && filtered.length" class="yr-list">
                <article
                  v-for="(r, i) in pagedFlat"
                  :key="r.id"
                  class="yr-row"
                  :class="`yr-row--${r.confidence}`"
                  :style="{ '--yr-stagger': i + 'ms' }"
                >
                  <div class="yr-row-head">
                    <div class="yr-row-client">
                      <span class="yr-row-name">{{ r.client_name || '—' }}</span>
                      <span class="yr-row-id">ת.ז <span class="ltr-number">{{ r.id_number || '—' }}</span></span>
                    </div>
                    <div class="yr-row-pills">
                      <span class="yr-pill" :class="`yr-pill--${r.risk_class}`">
                        {{ r.risk_class === 'stocks' ? 'מניות' : 'כללי' }}
                      </span>
                      <span class="yr-pill" :class="r.move_type === 'aggressive' ? 'yr-pill--aggressive' : 'yr-pill--same'">
                        {{ r.move_type === 'aggressive' ? 'אגרסיבי' : 'אותו סיכון' }}
                      </span>
                      <span class="yr-pill" :class="`yr-pill--conf-${r.confidence}`">
                        {{ confidenceHe(r.confidence) }}
                      </span>
                    </div>
                  </div>

                  <!-- Ticker: text columns on top, then a yield row aligned across the arrow -->
                  <div class="yr-ticker">
                    <div class="yr-ticker-info">
                      <div class="yr-ticker-slot yr-ticker-slot--from">
                        <span class="yr-ticker-label">מצב נוכחי</span>
                        <span class="yr-ticker-company">{{ r.current_company || '—' }}</span>
                        <span class="yr-ticker-name">{{ r.current_track || '—' }}</span>
                        <span class="yr-ticker-product">{{ r.product_type || '—' }}</span>
                      </div>
                      <div class="yr-ticker-slot yr-ticker-slot--to">
                        <span class="yr-ticker-label">המלצה</span>
                        <span class="yr-ticker-name yr-ticker-name--em">{{ r.recommended_track_name || '—' }}</span>
                        <span class="yr-ticker-product">{{ r.recommended_fund_name || '—' }}</span>
                      </div>
                    </div>
                    <div class="yr-ticker-yields">
                      <span class="yr-ticker-yield ltr-number">
                        <span class="yr-yld">3Y · {{ fmtPct(r.current_yield_3y) }}</span>
                        <span v-if="r.current_yield_5y != null" class="yr-yld yr-yld--5y">5Y · {{ fmtPct(r.current_yield_5y) }}</span>
                      </span>
                      <span class="yr-ticker-rule" aria-hidden="true">
                        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                          <line x1="20" y1="12" x2="4" y2="12"/>
                          <polyline points="10 6 4 12 10 18"/>
                        </svg>
                      </span>
                      <span class="yr-ticker-yield yr-ticker-yield--em ltr-number">
                        <span class="yr-yld">3Y · {{ fmtPct(r.recommended_yield_3y) }}</span>
                        <span v-if="r.recommended_yield_5y != null" class="yr-yld yr-yld--5y">5Y · {{ fmtPct(r.recommended_yield_5y) }}</span>
                      </span>
                    </div>
                  </div>

                  <!-- Hero: annual potential gain + delta chip -->
                  <div class="yr-hero">
                    <div class="yr-hero-main">
                      <span class="yr-hero-label">פוטנציאל שנתי</span>
                      <span class="yr-hero-value ltr-number">{{ fmt(r.potential_annual_gain) }}</span>
                    </div>
                    <span v-if="deltaPp(r) != null" class="yr-hero-delta ltr-number">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                        <polygon points="12,4 22,20 2,20"/>
                      </svg>
                      <span>{{ deltaPp(r) }}pp</span>
                    </span>
                  </div>
                  <div class="yr-foot">על צבירה של <span class="ltr-number">{{ fmt(r.accumulation) }}</span></div>
                  <!-- Magnitude bar — every card has a different width, so even
                       a list of identical-looking pills visibly differentiates
                       by gain size. The biggest gain fills the rail. -->
                  <div class="yr-magnitude" :title="`${Math.round(gainPct(r))}% מהמומלץ הגדול ביותר ברשימה`">
                    <div class="yr-magnitude-fill" :style="{ width: gainPct(r) + '%' }"></div>
                  </div>
                </article>
                <div v-if="pagedFlat.length < filtered.length" class="yr-load-more">
                  <button class="yr-btn yr-btn--ghost" type="button" @click="flatLimit += 30">
                    טען עוד ({{ filtered.length - pagedFlat.length }} נוספים)
                  </button>
                </div>
              </div>

              <div v-else class="yr-state yr-state--empty">
                <strong>אין המלצות תואמות למסננים.</strong>
                <span>נסה לנקות את שדה החיפוש או לשנות את הסינון.</span>
              </div>
            </template>
          </div>
        </div>

        <!-- Drilldown sub-modal — flat list of all recs in the selected group -->
        <Transition name="yr-modal">
          <div v-if="drilldownGroup" class="yr-drill-overlay" @click.self="drilldownGroup = null">
            <div class="yr-drill-card">
              <header class="yr-head">
                <div class="yr-head-left">
                  <span class="yr-badge"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="22 6 12 16 2 6"/></svg></span>
                  <div class="yr-titles">
                    <span class="yr-title">{{ drilldownGroup.track_name }}</span>
                    <span class="yr-sub">{{ drilldownGroup.clients }} לקוחות · פוטנציאל {{ fmt(drilldownGroup.gain) }}</span>
                  </div>
                </div>
                <button class="yr-icon-btn" type="button" title="סגור" @click="drilldownGroup = null">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
              </header>
              <div class="yr-body">
                <table class="yr-mini-table">
                  <thead>
                    <tr>
                      <th>לקוח</th>
                      <th>חברה נוכחית</th>
                      <th>3Y נוכחי</th>
                      <th>3Y מומלץ</th>
                      <th>צבירה</th>
                      <th>פוטנציאל</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="r in drilldownGroup.items" :key="r.id">
                      <td>{{ r.client_name || '—' }}</td>
                      <td>{{ r.current_company || '—' }}</td>
                      <td><span class="ltr-number">{{ fmtPct(r.current_yield_3y) }}</span></td>
                      <td><span class="ltr-number yr-gain">{{ fmtPct(r.recommended_yield_3y) }}</span></td>
                      <td><span class="ltr-number">{{ fmt(r.accumulation) }}</span></td>
                      <td><span class="ltr-number yr-gain">{{ fmt(r.potential_annual_gain) }}</span></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useInsightsStore } from '../../stores/insights.js'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open'])

const insightsStore = useInsightsStore()

const recommendations = computed(() => insightsStore.recommendations)
const loading = computed(() => insightsStore.recommendationsLoading)
const error = computed(() => insightsStore.recommendationsError)
const generating = computed(() => insightsStore.generating)
const downloading = ref(false)

// UI state — view toggle, filters, search, sort, pagination.
const viewMode = ref('groups')           // 'groups' (default summary) | 'flat'
const filterMoveType = ref('all')        // 'all' | 'same' | 'aggressive'
const filterRisk = ref('all')            // 'all' | 'general' | 'stocks'
const searchQuery = ref('')
const sortBy = ref('gain')               // 'gain' | 'accum' | 'client'
const flatLimit = ref(30)                // flat-view pagination
const drilldownGroup = ref(null)         // current open group drilldown

const filtered = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  return recommendations.value.filter((r) => {
    if (filterMoveType.value !== 'all' && r.move_type !== filterMoveType.value) return false
    if (filterRisk.value !== 'all' && r.risk_class !== filterRisk.value) return false
    if (q) {
      const hay = `${r.client_name || ''} ${r.current_company || ''} ${r.product_type || ''} ${r.recommended_track_name || ''} ${r.recommended_fund_name || ''}`.toLowerCase()
      if (!hay.includes(q)) return false
    }
    return true
  })
})

// A client realistically makes ONE move per product. Each general product now
// carries two options (same-risk fund switch + aggressive stocks jump), so for
// the headline aggregate we sum the BEST option per product rather than
// double-counting both. With a single-move-type filter active each product
// appears once anyway, so this is a no-op there.
const filteredGain = computed(() => {
  const best = new Map()
  for (const r of filtered.value) {
    const key = `${r.id_number || ''}|${r.fund_policy_number || ''}|${r.product_type || ''}`
    const g = r.potential_annual_gain || 0
    if (g > (best.get(key) || 0)) best.set(key, g)
  }
  let sum = 0
  for (const v of best.values()) sum += v
  return sum
})
const uniqueClients = computed(() => new Set(filtered.value.map((r) => r.id_number)).size)

// Sorted flat list for the per-client view.
const sortedFlat = computed(() => {
  const arr = [...filtered.value]
  if (sortBy.value === 'accum') return arr.sort((a, b) => (b.accumulation || 0) - (a.accumulation || 0))
  if (sortBy.value === 'client') return arr.sort((a, b) => (a.client_name || '').localeCompare(b.client_name || '', 'he'))
  return arr.sort((a, b) => (b.potential_annual_gain || 0) - (a.potential_annual_gain || 0))
})
const pagedFlat = computed(() => sortedFlat.value.slice(0, flatLimit.value))

// Max gain across the *currently visible* flat list — used to width the
// per-card magnitude bar so cards visibly differ even when every row has
// identical pills (e.g. all "אגרסיבי → חיסכון מניות"). The bar makes the
// magnitude story carry the visual weight.
const flatMaxGain = computed(() => {
  let m = 0
  for (const r of sortedFlat.value) {
    const v = Number(r?.potential_annual_gain) || 0
    if (v > m) m = v
  }
  return m
})
function gainPct(r) {
  const m = flatMaxGain.value
  if (!m) return 0
  const v = Math.max(0, Number(r?.potential_annual_gain) || 0)
  return Math.min(100, (v / m) * 100)
}

// Group view — bucket recommendations by destination track (track_id + risk
// + move_type) so the agent sees variety at a glance.
const grouped = computed(() => {
  const buckets = new Map()
  for (const r of filtered.value) {
    const key = `${r.recommended_track_id}|${r.risk_class}|${r.move_type}`
    if (!buckets.has(key)) {
      buckets.set(key, {
        track_id: r.recommended_track_id,
        track_name: r.recommended_track_name,
        fund_name: r.recommended_fund_name,
        risk: r.risk_class,
        move_type: r.move_type,
        y3: r.recommended_yield_3y,
        y5: r.recommended_yield_5y,
        clients: 0,
        accum: 0,
        gain: 0,
        items: [],
      })
    }
    const g = buckets.get(key)
    g.clients += 1
    g.accum += r.accumulation || 0
    g.gain += r.potential_annual_gain || 0
    g.items.push(r)
  }
  return [...buckets.values()].sort((a, b) => b.gain - a.gain)
})

function fmt(v) {
  if (v == null) return '—'
  return '₪' + Math.round(v).toLocaleString('he-IL')
}
function fmtPct(v) {
  if (v == null) return '—'
  return `${Number(v).toFixed(2)}%`
}
function confidenceHe(c) {
  if (c === 'high') return 'ביטחון גבוה'
  if (c === 'low') return 'ביטחון נמוך'
  return 'ביטחון בינוני'
}

// Signed yield-delta in percentage points (e.g. "+30.69"). Returns null when
// either side is missing — the template hides the chip in that case.
function deltaPp(r) {
  const cur = Number(r?.current_yield_3y)
  const rec = Number(r?.recommended_yield_3y)
  if (!Number.isFinite(cur) || !Number.isFinite(rec)) return null
  const d = rec - cur
  return (d > 0 ? '+' : '') + d.toFixed(2)
}

function close() {
  drilldownGroup.value = null
  emit('update:open', false)
}

async function onGenerate() {
  try {
    await insightsStore.generateRecommendations()
    flatLimit.value = 30
  } catch (e) { /* surfaced via store error */ }
}

async function onDownload() {
  downloading.value = true
  try {
    await insightsStore.downloadRecommendationsExcel()
  } catch (e) {
    console.error('[YieldRecommendationsModal] download failed', e)
  } finally {
    downloading.value = false
  }
}

watch(() => props.open, (isOpen) => {
  if (isOpen && !recommendations.value.length && !loading.value) {
    insightsStore.fetchRecommendations()
  }
})
// Reset pagination whenever filters change so the user doesn't lose context.
watch([filterMoveType, filterRisk, searchQuery, sortBy, viewMode], () => {
  flatLimit.value = 30
})
</script>

<style scoped>
.yr-overlay {
  position: fixed;
  inset: 0;
  z-index: 1010;
  background: rgba(17, 12, 6, 0.5);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
}
.yr-card {
  width: 100%;
  max-width: 1100px;
  height: 92vh;
  background: var(--bg-surface, #fff);
  border-radius: var(--radius-lg, 16px);
  border: 2px solid var(--primary-deep, #E65100);
  box-shadow:
    0 0 0 1px rgba(230, 81, 0, 0.08),
    0 30px 80px rgba(17, 12, 6, 0.32),
    0 8px 24px rgba(230, 81, 0, 0.12);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  position: relative;
}
/* Accent strip across the very top of the modal — gives the frame
   a deliberate, branded edge instead of a generic white box. */
.yr-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 4px;
  background: linear-gradient(90deg,
    var(--primary, #F57C00) 0%,
    var(--primary-deep, #E65100) 50%,
    var(--primary, #F57C00) 100%);
  z-index: 1;
}
.yr-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 22px;
  border-bottom: 1px solid var(--border, #DDDBDA);
  background: linear-gradient(135deg, #FFF3E0 0%, #FFFFFF 100%);
}
.yr-head-left { display: flex; align-items: center; gap: 12px; }
.yr-badge {
  width: 32px; height: 32px;
  border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  color: #fff;
  background: linear-gradient(135deg, #F57C00 0%, #FF9800 100%);
  box-shadow: 0 4px 10px rgba(245, 124, 0, 0.3);
}
.yr-titles { display: flex; flex-direction: column; }
.yr-title { font-size: 15px; font-weight: 700; color: var(--text, #181818); }
.yr-sub { font-size: 12px; color: var(--text-muted, #706E6B); margin-top: 2px; }
.yr-icon-btn {
  width: 32px; height: 32px;
  border-radius: 8px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text-muted, #706E6B);
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: background 0.18s ease, color 0.18s ease;
}
.yr-icon-btn:hover { background: var(--primary-light, #FFF3E0); color: var(--primary, #F57C00); }

.yr-body { padding: 18px 22px 22px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; flex: 1; min-height: 0; }

/* ── Summary strip ────────────────────────────────────────────────── */
.yr-summary {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
  gap: 12px;
  align-items: center;
}
.yr-summary-block {
  background: var(--primary-light, #FFF3E0);
  border-radius: var(--radius-md, 12px);
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.yr-summary-block--actions {
  background: transparent;
  flex-direction: row;
  gap: 10px;
  justify-content: flex-end;
  padding: 0;
}
.yr-summary-label { font-size: 12px; color: var(--text-muted, #706E6B); font-weight: 600; }
.yr-summary-value { font-size: 22px; font-weight: 800; color: var(--text, #181818); }
.yr-summary-of { font-size: 14px; color: var(--text-muted); font-weight: 500; margin-inline-start: 4px; }
.yr-gain { color: var(--green, #2E844A); }

.yr-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: background 0.18s ease, transform 0.1s ease, opacity 0.18s ease;
  border: 1px solid transparent;
}
.yr-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.yr-btn:not(:disabled):hover { transform: translateY(-1px); }
.yr-btn--primary {
  background: linear-gradient(135deg, #F57C00 0%, #E65100 100%);
  color: #fff;
  box-shadow: 0 4px 10px rgba(245, 124, 0, 0.3);
}
.yr-btn--ghost {
  background: var(--bg-surface, #fff);
  color: var(--primary-deep, #E65100);
  border-color: rgba(245, 124, 0, 0.3);
}
.yr-btn--ghost:not(:disabled):hover { background: var(--primary-light, #FFF3E0); }

/* ── Toolbar ──────────────────────────────────────────────────────── */
.yr-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  border: 1px solid var(--border-subtle, #E5E5E5);
  border-radius: var(--radius-md, 12px);
  padding: 8px 10px;
  background: var(--bg, #F3F3F3);
}
.yr-view-toggle {
  display: inline-flex;
  background: var(--bg-surface, #fff);
  border-radius: 10px;
  padding: 3px;
  gap: 2px;
}
.yr-view-btn {
  padding: 7px 14px;
  background: transparent;
  border: none;
  border-radius: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-muted, #706E6B);
  cursor: pointer;
  font-family: inherit;
  transition: background 0.18s ease, color 0.18s ease;
}
.yr-view-btn--active {
  background: var(--primary, #F57C00);
  color: #fff;
}
.yr-filters { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.yr-search, .yr-select {
  padding: 8px 12px;
  border: 1px solid var(--border, #DDDBDA);
  border-radius: 8px;
  font-size: 13px;
  background: var(--bg-surface, #fff);
  font-family: inherit;
  color: var(--text, #181818);
  outline: none;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}
.yr-search { min-width: 240px; }
.yr-search:focus, .yr-select:focus {
  border-color: var(--primary, #F57C00);
  box-shadow: 0 0 0 3px rgba(245, 124, 0, 0.12);
}

/* ── Pills ────────────────────────────────────────────────────────── */
/* Palette intent: green carries ONE semantic (high confidence / true positive).
   Risk-class pills (כללי / מניות) are temperature-coded — calm slate vs hot
   amber. Move-type (אותו סיכון / אגרסיבי) reuses the brand primary, never red:
   "aggressive" is spice, not error. */
.yr-pill {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.01em;
  white-space: nowrap;
  border: 1px solid transparent;
}
.yr-pill--general {
  background: rgba(112, 110, 107, 0.08);
  color: #706E6B;
  border-color: rgba(112, 110, 107, 0.18);
}
.yr-pill--stocks {
  background: rgba(245, 124, 0, 0.10);
  color: var(--primary-deep, #E65100);
  border-color: rgba(245, 124, 0, 0.28);
}
.yr-pill--same {
  background: rgba(112, 110, 107, 0.06);
  color: #706E6B;
  border-color: rgba(112, 110, 107, 0.14);
}
.yr-pill--aggressive {
  background: rgba(230, 81, 0, 0.10);
  color: var(--primary-deep, #E65100);
  border-color: rgba(230, 81, 0, 0.32);
}
.yr-pill--conf-high {
  background: rgba(46, 132, 74, 0.12);
  color: var(--green, #2E844A);
  border-color: rgba(46, 132, 74, 0.28);
}
.yr-pill--conf-medium {
  background: rgba(112, 110, 107, 0.08);
  color: #706E6B;
  border-color: rgba(112, 110, 107, 0.20);
}
.yr-pill--conf-low {
  background: rgba(112, 110, 107, 0.06);
  color: #706E6B;
  border-color: rgba(112, 110, 107, 0.16);
}

/* ── Group cards ──────────────────────────────────────────────────── */
.yr-groups {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 14px;
}
.yr-group-card {
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border, #DDDBDA);
  border-radius: var(--radius-md, 12px);
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.yr-group-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md, 0 2px 8px rgba(0,0,0,0.06)); }
.yr-group-card--aggressive { border-color: rgba(234, 0, 30, 0.25); background: linear-gradient(180deg, rgba(234, 0, 30, 0.02), #fff 30%); }
.yr-group-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.yr-group-titles { display: flex; flex-direction: column; gap: 6px; min-width: 0; }
.yr-group-title { display: flex; flex-direction: column; gap: 2px; }
.yr-group-name { font-size: 15px; font-weight: 700; color: var(--text, #181818); }
.yr-group-fund { font-size: 12px; color: var(--text-muted, #706E6B); }
.yr-group-pills { display: flex; gap: 6px; flex-wrap: wrap; }
.yr-group-metrics { display: flex; gap: 18px; }
.yr-group-metric { display: flex; flex-direction: column; gap: 2px; text-align: left; }
.yr-group-metric-label { font-size: 11px; color: var(--text-muted, #706E6B); }
.yr-group-metric-value { font-size: 15px; font-weight: 700; color: var(--text, #181818); }
.yr-group-metric--gain .yr-group-metric-value { color: var(--green, #2E844A); }
.yr-group-yields {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: var(--text-muted, #706E6B);
  padding-top: 8px;
  border-top: 1px dashed var(--border-subtle, #E5E5E5);
}
.yr-group-yields strong { color: var(--primary-deep, #E65100); }
.yr-group-expand {
  align-self: flex-end;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 10px;
  border-radius: 8px;
  border: 1px solid var(--border, #DDDBDA);
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary-deep, #E65100);
  cursor: pointer;
  font-family: inherit;
}
.yr-group-expand:hover { background: var(--primary-light, #FFF3E0); }

/* ── Flat (per-client) cards ──────────────────────────────────────── */
/* ── Per-client cinematic ticker card ────────────────────────────── */
.yr-list { display: flex; flex-direction: column; gap: 14px; }
.yr-row {
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border-subtle, #E5E5E5);
  border-radius: var(--radius-md, 12px);
  padding: 18px 22px;
  display: flex;
  flex-direction: column;
  gap: 14px;
  transition: transform 180ms cubic-bezier(0.4, 0, 0.2, 1),
              box-shadow 180ms cubic-bezier(0.4, 0, 0.2, 1),
              border-color 180ms ease;
  animation: yr-card-in 380ms cubic-bezier(0.2, 0.6, 0.3, 1) both;
  animation-delay: calc(var(--yr-stagger, 0ms) * 24);
}
.yr-row:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(17, 12, 6, 0.08);
  border-color: var(--primary, #F57C00);
}
.yr-row--low { border-inline-start: 3px solid rgba(112, 110, 107, 0.5); }
.yr-row--medium { border-inline-start: 3px solid var(--primary, #F57C00); }
.yr-row--high { border-inline-start: 3px solid var(--green, #2E844A); }

@keyframes yr-card-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}

.yr-row-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.yr-row-client { display: flex; flex-direction: column; gap: 3px; }
.yr-row-name {
  font-size: 17px;
  font-weight: 700;
  color: var(--text, #181818);
  letter-spacing: -0.01em;
  line-height: 1.2;
}
.yr-row-id { font-size: 11px; color: var(--text-muted, #706E6B); font-weight: 500; }
.yr-row-pills { display: flex; gap: 6px; flex-wrap: wrap; }

/* Ticker: text columns on top, then a single yield row whose arrow sits
   centered between the two 3Y figures so the comparison reads across. */
.yr-ticker {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 0;
  border-top: 1px dashed var(--border-subtle, #E5E5E5);
  border-bottom: 1px dashed var(--border-subtle, #E5E5E5);
}
.yr-ticker-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  align-items: start;
}
/* Yields aligned on one baseline with the arrow in the middle. The two
   figures hug the arrow so it reads "47.46% ← 73.79%". */
.yr-ticker-yields {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 12px;
}
.yr-ticker-yields .yr-ticker-yield:first-child { justify-self: end; }
.yr-ticker-yields .yr-ticker-yield:last-child { justify-self: start; }
.yr-ticker-slot {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.yr-ticker-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted, #706E6B);
  margin-bottom: 2px;
}
/* Line 1 of each slot: the parent company (e.g. הפניקס חברה לביטוח). */
.yr-ticker-company {
  font-size: 13px;
  font-weight: 600;
  color: var(--text, #181818);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Line 2: the track / recommendation headline. On the TO side this is the
   recommendation itself, so it gets the brand-deep color treatment. */
.yr-ticker-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text, #181818);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.yr-ticker-name--em {
  font-weight: 800;
  color: var(--primary-deep, #E65100);
  font-size: 14.5px;
}
/* Line 3: the specific product / fund name. */
.yr-ticker-product {
  font-size: 12px;
  color: var(--text-muted, #706E6B);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.yr-ticker-yield {
  display: flex;
  flex-direction: column;
  gap: 1px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text-muted, #706E6B);
  font-variant-numeric: tabular-nums;
}
.yr-ticker-yield--em .yr-yld:first-child { color: var(--green, #2E844A); font-weight: 800; font-size: 14px; }
.yr-yld--5y { font-size: 11px; font-weight: 600; opacity: 0.75; }
.yr-ticker-rule {
  color: var(--primary, #F57C00);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Hero: the headline number — annual potential gain — with a green delta chip. */
.yr-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 14px;
  flex-wrap: wrap;
}
.yr-hero-main { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.yr-hero-label {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-muted, #706E6B);
}
.yr-hero-value {
  font-size: 32px;
  font-weight: 800;
  color: var(--green, #2E844A);
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.02em;
  line-height: 1;
  animation: yr-tick 520ms cubic-bezier(0.2, 0.6, 0.3, 1) 120ms both;
}
@keyframes yr-tick {
  from { opacity: 0; transform: translateY(6px); }
  to   { opacity: 1; transform: translateY(0); }
}
.yr-hero-delta {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 11px;
  background: rgba(46, 132, 74, 0.12);
  color: var(--green, #2E844A);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  letter-spacing: 0.01em;
}
.yr-hero-delta svg { transform: translateY(-0.5px); }

.yr-foot {
  font-size: 11px;
  color: var(--text-muted, #706E6B);
  font-weight: 500;
}
.yr-foot .ltr-number {
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  color: var(--text, #181818);
}

/* Gain magnitude rail — sits flush at the very bottom of each card and
   reads as the card's "score bar". Slide-in animation runs once on mount. */
.yr-magnitude {
  margin: 4px -22px -18px;
  height: 4px;
  background: rgba(245, 124, 0, 0.06);
  border-radius: 0 0 var(--radius-md, 12px) var(--radius-md, 12px);
  overflow: hidden;
}
.yr-magnitude-fill {
  height: 100%;
  background: linear-gradient(90deg,
    var(--primary, #F57C00) 0%,
    var(--primary-deep, #E65100) 60%,
    #E65100 100%);
  border-radius: inherit;
  transform-origin: right center; /* RTL: bar grows from the right */
  animation: yr-mag-in 700ms cubic-bezier(0.2, 0.7, 0.2, 1) 220ms both;
}
@keyframes yr-mag-in {
  from { transform: scaleX(0); }
  to   { transform: scaleX(1); }
}

/* Narrow viewport: stack the text columns; keep the yield row across the arrow. */
@media (max-width: 620px) {
  .yr-ticker-info { grid-template-columns: 1fr; gap: 10px; }
  .yr-hero-value { font-size: 26px; }
  .yr-row { padding: 14px 16px; }
}

.yr-load-more { display: flex; justify-content: center; padding-top: 8px; }

/* ── Empty + loading + error ─────────────────────────────────────── */
.yr-state {
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; padding: 36px 12px;
  color: var(--text-muted, #706E6B);
  font-size: 14px;
}
.yr-state--error { color: var(--red, #EA001E); }
.yr-state--empty strong { color: var(--text, #181818); font-size: 15px; }
.yr-loader {
  width: 28px; height: 28px;
  border: 2.5px solid var(--primary-light, #FFF3E0);
  border-top-color: var(--primary, #F57C00);
  border-radius: 50%;
  animation: yr-spin 0.9s linear infinite;
}
@keyframes yr-spin { to { transform: rotate(360deg); } }

/* ── Drilldown sub-modal ──────────────────────────────────────────── */
.yr-drill-overlay {
  position: fixed;
  inset: 0;
  z-index: 1020;
  background: rgba(17, 12, 6, 0.45);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.yr-drill-card {
  width: 100%;
  max-width: 980px;
  max-height: 90vh;
  background: var(--bg-surface, #fff);
  border-radius: var(--radius-lg, 16px);
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.yr-mini-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.yr-mini-table th, .yr-mini-table td {
  padding: 9px 12px;
  text-align: right;
  border-bottom: 1px solid var(--border-subtle, #E5E5E5);
  white-space: nowrap;
}
.yr-mini-table th {
  position: sticky; top: 0;
  background: var(--primary-light, #FFF3E0);
  font-weight: 700;
  color: var(--primary-deep, #E65100);
  z-index: 1;
}
.yr-mini-table tbody tr:last-child td { border-bottom: none; }

.yr-modal-enter-active, .yr-modal-leave-active { transition: opacity 0.2s ease; }
.yr-modal-enter-from, .yr-modal-leave-to { opacity: 0; }

/* ── Responsive ─────────────────────────────────────────────────── */
@media (max-width: 900px) {
  .yr-overlay { padding: 8px; }
  .yr-card { height: 100vh; border-radius: 0; max-width: 100%; }
  .yr-summary { grid-template-columns: repeat(2, 1fr); }
  .yr-summary-block--actions { grid-column: 1 / -1; justify-content: stretch; }
  .yr-summary-block--actions .yr-btn { flex: 1; justify-content: center; }
  .yr-row-body { grid-template-columns: 1fr; }
  .yr-arrow { transform: rotate(90deg); }
}
</style>
