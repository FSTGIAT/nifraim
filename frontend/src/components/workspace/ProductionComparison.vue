<template>
  <div class="prod-comparison">
    <!-- No history -->
    <div v-if="!history.length && !comparisonResult" class="empty-state">
      <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
      </svg>
      <p>אין קבצים קודמים להשוואה — החלף את קובץ הפרודוקציה ותוכל להשוות</p>
    </div>

    <!-- File selector -->
    <div v-else-if="!comparisonResult && !comparing" class="selector-section">
      <h4 class="selector-title">בחר קובץ קודם להשוואה</h4>
      <div class="history-grid">
        <div
          v-for="f in history"
          :key="f.id"
          class="history-card"
          :class="{ selected: selectedFileId === f.id }"
          @click="selectedFileId = f.id"
        >
          <div class="hc-radio">
            <div class="hc-radio-inner" v-if="selectedFileId === f.id"></div>
          </div>
          <div class="hc-info">
            <span class="hc-name">{{ f.filename }}</span>
            <span class="hc-meta">
              <span class="ltr-number">{{ f.record_count.toLocaleString() }}</span> רשומות
              · {{ formatDate(f.uploaded_at) }}
            </span>
          </div>
        </div>
      </div>
      <button
        class="btn-compare"
        :disabled="!selectedFileId"
        @click="runCompare"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
        <span>השווה קבצים</span>
      </button>
    </div>

    <!-- Comparing -->
    <div v-else-if="comparing" class="loading-state">
      <div class="loader">
        <div class="loader-ring"></div>
        <div class="loader-ring delay"></div>
      </div>
      <span>משווה קבצים...</span>
    </div>

    <!-- Results -->
    <div v-else-if="comparisonResult" class="results-section">
      <div class="results-header">
        <h4>תוצאות השוואה</h4>
        <button class="btn-back" @click="$emit('reset')">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="19" y1="12" x2="5" y2="12"/>
            <polyline points="12 19 5 12 12 5"/>
          </svg>
          חזרה
        </button>
      </div>

      <!-- Summary KPI strip -->
      <div class="summary-strip">
        <div class="summary-badge badge-green">
          <span class="ltr-number">{{ comparisonResult.summary.new_count }}</span>
          <span>חדשים</span>
        </div>
        <div class="summary-badge badge-red">
          <span class="ltr-number">{{ comparisonResult.summary.removed_count }}</span>
          <span>הוסרו</span>
        </div>
        <div class="summary-badge badge-amber">
          <span class="ltr-number">{{ comparisonResult.summary.changed_count }}</span>
          <span>שונו</span>
        </div>
        <div class="summary-badge badge-gray">
          <span class="ltr-number">{{ comparisonResult.summary.unchanged_count }}</span>
          <span>ללא שינוי</span>
        </div>
      </div>

      <!-- New clients -->
      <div class="diff-section" v-if="comparisonResult.new_clients.length">
        <button class="diff-header diff-green" @click="toggleSection('new')">
          <span class="diff-title">לקוחות חדשים</span>
          <span class="diff-count">{{ comparisonResult.new_clients.length }}</span>
          <svg :class="{ rotated: !sections.new }" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>
        <Transition name="collapse">
          <div v-if="sections.new" class="diff-body">
            <table class="diff-table">
              <thead>
                <tr><th>שם</th><th>ת.ז.</th><th>חברה</th><th>פרמיה</th><th>צבירה</th><th>מוצרים</th></tr>
              </thead>
              <tbody>
                <tr v-for="c in comparisonResult.new_clients" :key="c.id_number">
                  <td>{{ c.name }}</td>
                  <td class="ltr-number">{{ c.id_number }}</td>
                  <td>{{ c.company }}</td>
                  <td class="ltr-number">{{ formatAmount(c.premium) }}</td>
                  <td class="ltr-number">{{ formatAmount(c.accumulation) }}</td>
                  <td class="ltr-number">{{ c.products_count }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Transition>
      </div>

      <!-- Removed clients -->
      <div class="diff-section" v-if="comparisonResult.removed_clients.length">
        <button class="diff-header diff-red" @click="toggleSection('removed')">
          <span class="diff-title">לקוחות שהוסרו</span>
          <span class="diff-count">{{ comparisonResult.removed_clients.length }}</span>
          <svg :class="{ rotated: !sections.removed }" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>
        <Transition name="collapse">
          <div v-if="sections.removed" class="diff-body">
            <table class="diff-table">
              <thead>
                <tr><th>שם</th><th>ת.ז.</th><th>חברה</th><th>פרמיה</th><th>צבירה</th><th>מוצרים</th></tr>
              </thead>
              <tbody>
                <tr v-for="c in comparisonResult.removed_clients" :key="c.id_number">
                  <td>{{ c.name }}</td>
                  <td class="ltr-number">{{ c.id_number }}</td>
                  <td>{{ c.company }}</td>
                  <td class="ltr-number">{{ formatAmount(c.premium) }}</td>
                  <td class="ltr-number">{{ formatAmount(c.accumulation) }}</td>
                  <td class="ltr-number">{{ c.products_count }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </Transition>
      </div>

      <!-- Changed clients -->
      <div class="diff-section" v-if="comparisonResult.changed_clients.length">
        <button class="diff-header diff-amber" @click="toggleSection('changed')">
          <span class="diff-title">לקוחות ששונו</span>
          <span class="diff-count">{{ comparisonResult.changed_clients.length }}</span>
          <svg :class="{ rotated: !sections.changed }" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>
        <Transition name="collapse">
          <div v-if="sections.changed" class="diff-body">
            <div
              v-for="c in comparisonResult.changed_clients"
              :key="c.id_number"
              class="changed-client"
            >
              <div class="cc-header" @click="toggleClient(c.id_number)">
                <span class="cc-name">{{ c.name }}</span>
                <span class="cc-id ltr-number">{{ c.id_number }}</span>
                <span class="cc-company">{{ c.company }}</span>
                <div class="cc-diffs-inline">
                  <span v-if="c.premium_diff" class="cc-diff" :class="c.premium_diff > 0 ? 'diff-up' : 'diff-down'">
                    פרמיה {{ c.premium_diff > 0 ? '+' : '' }}<span class="ltr-number">{{ formatAmount(c.premium_diff) }}</span>
                  </span>
                  <span v-if="c.accumulation_diff" class="cc-diff" :class="c.accumulation_diff > 0 ? 'diff-up' : 'diff-down'">
                    צבירה {{ c.accumulation_diff > 0 ? '+' : '' }}<span class="ltr-number">{{ formatAmount(c.accumulation_diff) }}</span>
                  </span>
                </div>
                <svg :class="{ rotated: !expandedClients[c.id_number] }" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="6 9 12 15 18 9"/>
                </svg>
              </div>
              <Transition name="collapse">
                <div v-if="expandedClients[c.id_number]" class="cc-details">
                  <div v-for="ch in c.changes" :key="ch.field" class="cc-change-row">
                    <span class="cc-field">{{ ch.field }}</span>
                    <span class="cc-old ltr-number">{{ formatVal(ch.old_val) }}</span>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <line x1="5" y1="12" x2="19" y2="12"/>
                      <polyline points="12 5 19 12 12 19"/>
                    </svg>
                    <span class="cc-new ltr-number">{{ formatVal(ch.new_val) }}</span>
                  </div>
                </div>
              </Transition>
            </div>
          </div>
        </Transition>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'

const props = defineProps({
  history: { type: Array, default: () => [] },
  comparisonResult: { type: Object, default: null },
  comparing: { type: Boolean, default: false },
  currentFileId: { type: String, default: null },
})

const emit = defineEmits(['compare', 'reset'])

const selectedFileId = ref(null)
const sections = reactive({ new: true, removed: true, changed: true })
const expandedClients = reactive({})

function toggleSection(key) {
  sections[key] = !sections[key]
}

function toggleClient(id) {
  expandedClients[id] = !expandedClients[id]
}

function runCompare() {
  if (selectedFileId.value && props.currentFileId) {
    emit('compare', props.currentFileId, selectedFileId.value)
  }
}

function formatDate(dateStr) {
  const d = new Date(dateStr)
  return d.toLocaleDateString('he-IL', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function formatAmount(val) {
  if (!val || val === 0) return '₪0'
  return '₪' + Math.round(val).toLocaleString()
}

function formatVal(val) {
  if (typeof val === 'number') return formatAmount(val)
  return val
}
</script>

<style scoped>
.prod-comparison {
  animation: slideUp 0.4s var(--transition);
}

.empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-muted);
}

.empty-state svg { margin-bottom: 12px; opacity: 0.3; }
.empty-state p { font-size: 14px; }

/* Selector */
.selector-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.selector-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}

.history-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 18px;
  background: var(--card-bg);
  border: 1.5px solid var(--border-subtle);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.25s var(--transition);
}

.history-card:hover {
  border-color: var(--border);
  background: var(--bg-surface);
}

.history-card.selected {
  border-color: var(--primary);
  background: var(--primary-light);
}

.hc-radio {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  border: 2px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: border-color 0.2s;
}

.history-card.selected .hc-radio {
  border-color: var(--primary);
}

.hc-radio-inner {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--primary);
}

.hc-info { display: flex; flex-direction: column; gap: 2px; }
.hc-name { font-size: 13px; font-weight: 600; color: var(--text); word-break: break-all; }
.hc-meta { font-size: 11px; color: var(--text-muted); }

.btn-compare {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 28px;
  background: linear-gradient(135deg, var(--accent-violet), var(--primary-deep));
  color: white;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 700;
  font-family: inherit;
  align-self: flex-start;
  transition: all 0.3s var(--transition);
}

.btn-compare:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(127, 86, 217, 0.15);
}

.btn-compare:disabled { opacity: 0.4; cursor: not-allowed; }

/* Loading */
.loading-state {
  text-align: center;
  padding: 48px;
  color: var(--text-secondary);
  font-size: 14px;
}

.loader {
  width: 36px;
  height: 36px;
  position: relative;
  margin: 0 auto 14px;
}

.loader-ring {
  position: absolute;
  inset: 0;
  border: 2px solid transparent;
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.loader-ring.delay {
  inset: 5px;
  border-top-color: var(--accent-cyan);
  animation-duration: 1.5s;
  animation-direction: reverse;
}

/* Results */
.results-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.results-header h4 {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
}

.btn-back {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  font-family: inherit;
  color: var(--text-muted);
  border: 1px solid var(--border);
  border-radius: 8px;
  transition: all 0.2s;
}

.btn-back:hover {
  color: var(--text);
  background: var(--bg-surface);
}

/* Summary strip */
.summary-strip {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.summary-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 600;
}

.badge-green { background: var(--green-light); color: var(--accent-emerald); }
.badge-red { background: var(--red-light); color: var(--red); }
.badge-amber { background: var(--amber-light); color: var(--amber); }
.badge-gray { background: var(--border-subtle); color: var(--text-muted); }

/* Diff sections */
.diff-section {
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--border-subtle);
}

.diff-header {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 18px;
  font-size: 13px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
  text-align: right;
}

.diff-green { background: rgba(16, 185, 129, 0.06); color: var(--accent-emerald); border-right: 3px solid var(--accent-emerald); }
.diff-red { background: rgba(239, 68, 68, 0.06); color: var(--red); border-right: 3px solid var(--red); }
.diff-amber { background: rgba(245, 158, 11, 0.06); color: var(--amber); border-right: 3px solid var(--amber); }

.diff-count {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 10px;
  background: rgba(0,0,0,0.06);
}

.diff-header svg {
  margin-inline-start: auto;
  transition: transform 0.25s;
  opacity: 0.5;
}

.diff-header svg.rotated { transform: rotate(-90deg); }

.diff-body {
  padding: 0;
  overflow: auto;
}

/* Table */
.diff-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.diff-table th {
  padding: 8px 14px;
  text-align: right;
  font-weight: 600;
  color: var(--text-muted);
  background: var(--bg-surface);
  border-bottom: 1px solid var(--border-subtle);
  font-size: 11px;
}

.diff-table td {
  padding: 8px 14px;
  border-bottom: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}

.diff-table tbody tr:hover { background: var(--bg-surface); }

/* Changed clients */
.changed-client {
  border-bottom: 1px solid var(--border-subtle);
}

.changed-client:last-child { border-bottom: none; }

.cc-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 18px;
  cursor: pointer;
  transition: background 0.2s;
}

.cc-header:hover { background: var(--bg-surface); }

.cc-name { font-size: 13px; font-weight: 600; color: var(--text); }
.cc-id { font-size: 11px; color: var(--text-muted); }
.cc-company { font-size: 11px; color: var(--text-muted); }

.cc-diffs-inline {
  display: flex;
  gap: 8px;
  margin-inline-start: auto;
}

.cc-diff {
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 6px;
}

.diff-up { background: var(--green-light); color: var(--accent-emerald); }
.diff-down { background: var(--red-light); color: var(--red); }

.cc-header svg {
  transition: transform 0.25s;
  opacity: 0.4;
  flex-shrink: 0;
}

.cc-header svg.rotated { transform: rotate(-90deg); }

.cc-details {
  padding: 0 18px 12px 18px;
}

.cc-change-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 0;
  font-size: 12px;
}

.cc-field {
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 60px;
}

.cc-old { color: var(--red); text-decoration: line-through; opacity: 0.7; }
.cc-new { color: var(--accent-emerald); font-weight: 600; }

.cc-change-row svg { color: var(--text-muted); opacity: 0.4; flex-shrink: 0; }

/* Transitions */
.collapse-enter-active { animation: collapseIn 0.25s ease; }
.collapse-leave-active { animation: collapseIn 0.2s ease reverse; }

@keyframes collapseIn {
  from { opacity: 0; max-height: 0; }
  to { opacity: 1; max-height: 2000px; }
}

.ltr-number {
  direction: ltr;
  unicode-bidi: embed;
  display: inline-block;
}
</style>
