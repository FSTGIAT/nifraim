<template>
  <div class="mt-wrap">
    <header class="mt-head">
      <div>
        <h3>בדיקות מסלקה</h3>
        <span class="mt-sub">קבצי מסלקה אמיתיים, מפוענחים מול הקוד שלנו — שם הקובץ, ה-XML המקורי, והשורות שהיו נשמרות</span>
      </div>
      <div class="mt-env" :class="{ 'mt-env--prod': envIsProd }">
        <span class="mt-env-dot"></span>{{ envIsProd ? 'ייצור' : 'בדיקות' }}
      </div>
    </header>

    <div v-if="loading && !samples.length" class="mt-loading"><div class="spinner"></div></div>

    <p v-else-if="error" class="mt-error">{{ error }}</p>

    <div v-else class="mt-body">
      <!-- Sample picker -->
      <nav class="mt-rail" aria-label="קבצי דוגמה">
        <div v-for="group in grouped" :key="group.label" class="mt-group">
          <h4>{{ group.label }}</h4>
          <button
            v-for="s in group.items"
            :key="s.name"
            class="mt-item"
            :class="{ 'mt-item--on': s.name === selectedName }"
            @click="select(s.name)"
          >
            <span class="mt-item-title">{{ s.filename ? s.filename.product_label : s.name }}</span>
            <span class="mt-item-meta ltr-number">{{ formatKb(s.size) }} KB</span>
          </button>
        </div>
      </nav>

      <section class="mt-main">
        <div v-if="detailLoading" class="mt-loading"><div class="spinner"></div></div>

        <template v-else-if="detail">
          <!-- The filename ruler: the מסלקה validates this before it parses anything -->
          <div class="mt-ruler-card">
            <div class="mt-ruler-name ltr-number">{{ detail.name }}</div>
            <div v-if="detail.filename" class="mt-ruler">
              <div v-for="seg in segments" :key="seg.key" class="mt-seg" :style="{ flexGrow: seg.len }">
                <span class="mt-seg-raw ltr-number">{{ seg.raw }}</span>
                <span class="mt-seg-label">{{ seg.label }}</span>
                <span class="mt-seg-val">{{ seg.value }}</span>
              </div>
            </div>
            <p v-else class="mt-ruler-bad">שם הקובץ לא תואם את מבנה נספח ו' — המסלקה דוחה קובץ כזה לפני שהיא קוראת את התוכן</p>
          </div>

          <!-- Diagnostics -->
          <div v-if="detail.diagnostics && detail.diagnostics.kind === 'holdings'" class="mt-stats">
            <div class="mt-stat">
              <span class="mt-stat-n ltr-number">{{ detail.diagnostics.rows }}</span>
              <span class="mt-stat-l">שורות</span>
            </div>
            <div class="mt-stat">
              <span class="mt-stat-n ltr-number">{{ detail.diagnostics.distinct_customers }}</span>
              <span class="mt-stat-l">לקוחות</span>
            </div>
            <div class="mt-stat" :class="{ 'mt-stat--bad': detail.diagnostics.rows_missing_id > 0 }">
              <span class="mt-stat-n ltr-number">{{ detail.diagnostics.rows_missing_id }}</span>
              <span class="mt-stat-l">ללא ת״ז</span>
            </div>
            <div class="mt-stat" :class="{ 'mt-stat--bad': detail.diagnostics.duplicate_rows > 0 }">
              <span class="mt-stat-n ltr-number">{{ detail.diagnostics.duplicate_rows }}</span>
              <span class="mt-stat-l">כפילויות</span>
            </div>
            <div class="mt-stat mt-stat--wide">
              <span class="mt-stat-n ltr-number">{{ formatMoney(detail.diagnostics.total_accumulation) }}</span>
              <span class="mt-stat-l">סך צבירה</span>
            </div>
            <div class="mt-stat mt-stat--wide">
              <span class="mt-stat-n mt-stat-n--text">{{ detail.diagnostics.product_types.join(' · ') }}</span>
              <span class="mt-stat-l">סוגי מוצר</span>
            </div>
          </div>

          <p v-if="detail.error" class="mt-error">{{ detail.error }}</p>

          <!-- Feedback files carry no holdings — show the correlation keys -->
          <div v-if="detail.diagnostics && detail.diagnostics.kind === 'feedback'" class="mt-panel">
            <h4>שדות המשוב</h4>
            <p class="mt-note">
              <strong>SHEM-HAKOVETZ</strong> מחזיר את שם הקובץ ששלחנו, ו-<strong>MISPAR-MISLAKA</strong>
              הוא המזהה שהמסלקה נותנת לבקשה. אלה שני המפתחות לשיוך התשובה — לא מספר שאנחנו ממציאים.
            </p>
            <table class="mt-table">
              <tbody>
                <tr v-for="(v, k) in detail.diagnostics.fields" :key="k">
                  <th scope="row" class="ltr-number">{{ k }}</th>
                  <td><span class="ltr-number">{{ v || '—' }}</span></td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Parsed rows -->
          <div v-if="detail.rows && detail.rows.length" class="mt-panel">
            <h4>שורות שהיו נשמרות</h4>
            <div class="mt-table-scroll">
              <table class="mt-table mt-table--rows">
                <thead>
                  <tr>
                    <th>ת״ז</th><th>שם</th><th>חברה</th><th>סוג מוצר</th>
                    <th>מספר פוליסה</th><th>צבירה</th><th>תאריך הצטרפות</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(r, i) in detail.rows" :key="i">
                    <td><span class="ltr-number">{{ r.id_number || '—' }}</span></td>
                    <td>{{ [r.first_name, r.last_name].filter(Boolean).join(' ') || '—' }}</td>
                    <td>{{ r.receiving_company || '—' }}</td>
                    <td>{{ r.product_type || '—' }}</td>
                    <td><span class="ltr-number">{{ r.fund_policy_number || '—' }}</span></td>
                    <td><span class="ltr-number">{{ formatMoney(r.accumulation) }}</span></td>
                    <td><span class="ltr-number">{{ r.sign_date || '—' }}</span></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Source -->
          <div class="mt-panel">
            <div class="mt-panel-head">
              <h4>ה-XML המקורי</h4>
              <button class="mt-toggle" @click="showXml = !showXml">{{ showXml ? 'הסתר' : 'הצג' }}</button>
            </div>
            <pre v-if="showXml" class="mt-xml" dir="ltr">{{ detail.xml }}</pre>
            <p v-if="showXml && detail.xml_truncated" class="mt-note">התצוגה קוצרה — הקובץ המלא ארוך יותר.</p>
          </div>
        </template>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../../api/client.js'

const samples = ref([])
const selectedName = ref('')
const detail = ref(null)
const loading = ref(true)
const detailLoading = ref(false)
const error = ref('')
const showXml = ref(false)

// A sample is only "production" if its file type says DAT. The TST/DAT switch is
// the one thing that decides whether a real request reaches the live vault, so it
// is stated on screen rather than inferred.
const envIsProd = computed(() => detail.value?.filename?.is_test === false)

const grouped = computed(() => {
  const by = new Map()
  for (const s of samples.value) {
    const label = s.filename ? s.filename.service_label : 'לא מזוהה'
    if (!by.has(label)) by.set(label, [])
    by.get(label).push(s)
  }
  return [...by.entries()].map(([label, items]) => ({ label, items }))
})

// The נספח ו' grammar, in file order. `len` drives each segment's width so the
// ruler is proportional to the real character budget.
const segments = computed(() => {
  const f = detail.value?.filename
  if (!f) return []
  return [
    { key: 'dir', len: 3, raw: f.direction, label: 'כיוון', value: f.direction_label },
    { key: 'snd', len: 12, raw: f.sender_id, label: 'מזהה שולח', value: f.sender_id_stripped },
    { key: 'svc', len: 6, raw: f.service, label: 'ממשק', value: f.service_label },
    { key: 'prd', len: 3, raw: f.product_family, label: 'משפחת מוצר', value: f.product_label },
    { key: 'ver', len: 3, raw: f.version, label: 'גרסה', value: `v${f.version}` },
    { key: 'ts', len: 14, raw: f.timestamp, label: 'חותמת זמן', value: formatStamp(f.sent_at) },
    { key: 'seq', len: 4, raw: f.sequence, label: 'רץ יומי', value: f.sequence },
    { key: 'typ', len: 3, raw: f.file_type, label: 'סוג', value: f.file_type_label },
  ]
})

function formatKb(bytes) {
  return Math.max(1, Math.round((bytes || 0) / 1024))
}

function formatMoney(v) {
  const n = Number(v || 0)
  if (!n) return '—'
  return n.toLocaleString('he-IL', { maximumFractionDigits: 0 })
}

function formatStamp(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('he-IL', { dateStyle: 'short', timeStyle: 'short' })
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const { data } = await api.get('/maslaka/samples')
    samples.value = data
    if (data.length) await select(data[0].name)
  } catch (e) {
    error.value = 'לא ניתן לטעון את קבצי הדוגמה'
  } finally {
    loading.value = false
  }
}

async function select(name) {
  selectedName.value = name
  detailLoading.value = true
  showXml.value = false
  try {
    const { data } = await api.get(`/maslaka/samples/${encodeURIComponent(name)}`)
    detail.value = data
  } catch (e) {
    error.value = 'לא ניתן לפענח את הקובץ'
  } finally {
    detailLoading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.mt-wrap { display: flex; flex-direction: column; gap: 18px; }

.mt-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; }
.mt-head h3 { margin: 0 0 4px; font-size: 1.35rem; font-weight: 700; color: var(--text-primary); }
.mt-sub { font-size: 0.85rem; color: var(--text-secondary); max-width: 62ch; line-height: 1.5; }

.mt-env {
  display: inline-flex; align-items: center; gap: 7px; flex-shrink: 0;
  padding: 6px 12px; border-radius: 999px; font-size: 0.78rem; font-weight: 600;
  background: var(--tab-maslaka-wash); color: var(--tab-maslaka);
  border: 1px solid var(--tab-maslaka-wash);
}
.mt-env-dot { width: 7px; height: 7px; border-radius: 50%; background: currentColor; }
.mt-env--prod { background: rgba(198, 40, 40, 0.10); color: #C62828; border-color: rgba(198, 40, 40, 0.22); }

.mt-body { display: grid; grid-template-columns: 232px 1fr; gap: 18px; align-items: start; }

.mt-rail { display: flex; flex-direction: column; gap: 16px; position: sticky; top: 120px; }
.mt-group h4 {
  margin: 0 0 6px; font-size: 0.74rem; font-weight: 700;
  color: var(--text-secondary); letter-spacing: 0.01em;
}
.mt-item {
  display: flex; align-items: baseline; justify-content: space-between; gap: 8px;
  width: 100%; padding: 8px 11px; margin-bottom: 3px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-sm); cursor: pointer; text-align: right;
  font-family: inherit; font-size: 0.84rem; color: var(--text-primary);
  transition: border-color 0.15s ease, background 0.15s ease;
}
.mt-item:hover { border-color: var(--tab-maslaka); }
.mt-item--on { background: var(--tab-maslaka-wash); border-color: var(--tab-maslaka); font-weight: 600; }
.mt-item-meta { font-size: 0.72rem; color: var(--text-secondary); }

.mt-main { display: flex; flex-direction: column; gap: 16px; min-width: 0; }

/* The filename ruler — the hero. The מסלקה validates this before parsing. */
.mt-ruler-card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-md); padding: 16px;
}
.mt-ruler-name {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 0.9rem; color: var(--text-primary); word-break: break-all;
  margin-bottom: 12px; direction: ltr; text-align: left;
}
.mt-ruler { display: flex; gap: 3px; direction: ltr; }
.mt-seg {
  flex-basis: 0; min-width: 0; padding: 8px 6px;
  border-top: 3px solid var(--tab-maslaka);
  background: var(--tab-maslaka-wash);
  display: flex; flex-direction: column; gap: 2px;
}
.mt-seg-raw {
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 0.76rem; font-weight: 700; color: var(--tab-maslaka);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.mt-seg-label { font-size: 0.66rem; color: var(--text-secondary); direction: rtl; }
.mt-seg-val {
  font-size: 0.72rem; color: var(--text-primary); direction: rtl;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.mt-ruler-bad { margin: 0; font-size: 0.85rem; color: #C62828; line-height: 1.5; }

.mt-stats { display: flex; flex-wrap: wrap; gap: 10px; }
.mt-stat {
  flex: 1 1 96px; padding: 11px 13px; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  display: flex; flex-direction: column; gap: 3px;
}
.mt-stat--wide { flex: 2 1 190px; }
.mt-stat--bad { border-color: rgba(198, 40, 40, 0.35); background: rgba(198, 40, 40, 0.05); }
.mt-stat--bad .mt-stat-n { color: #C62828; }
.mt-stat-n { font-size: 1.3rem; font-weight: 700; color: var(--text-primary); }
.mt-stat-n--text { font-size: 0.92rem; font-weight: 600; }
.mt-stat-l { font-size: 0.74rem; color: var(--text-secondary); }

.mt-panel {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: var(--radius-md); padding: 16px; min-width: 0;
}
.mt-panel h4 { margin: 0 0 10px; font-size: 0.95rem; font-weight: 700; color: var(--text-primary); }
.mt-panel-head { display: flex; align-items: center; justify-content: space-between; }
.mt-panel-head h4 { margin: 0; }
.mt-note { margin: 8px 0 0; font-size: 0.8rem; color: var(--text-secondary); line-height: 1.6; }

.mt-toggle {
  padding: 5px 12px; font-size: 0.78rem; font-family: inherit; cursor: pointer;
  background: transparent; color: var(--tab-maslaka);
  border: 1px solid var(--tab-maslaka); border-radius: var(--radius-sm);
}

.mt-table-scroll { overflow-x: auto; }
.mt-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 0.83rem; }
.mt-table th, .mt-table td {
  padding: 7px 9px; border-bottom: 1px solid var(--border);
  text-align: right; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.mt-table thead th { color: var(--text-secondary); font-weight: 600; font-size: 0.76rem; }
.mt-table--rows { min-width: 720px; }
.mt-table--rows td:nth-child(1), .mt-table--rows td:nth-child(5),
.mt-table--rows td:nth-child(6), .mt-table--rows td:nth-child(7),
.mt-table--rows th:nth-child(1), .mt-table--rows th:nth-child(5),
.mt-table--rows th:nth-child(6), .mt-table--rows th:nth-child(7) { text-align: center; width: 100px; }
.mt-table tbody th { width: 240px; color: var(--text-secondary); font-weight: 600; text-align: left; }

.mt-xml {
  margin: 10px 0 0; padding: 12px; max-height: 460px; overflow: auto;
  background: var(--bg); border: 1px solid var(--border); border-radius: var(--radius-sm);
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  font-size: 0.74rem; line-height: 1.5; white-space: pre; color: var(--text-primary);
}

.mt-loading { display: flex; justify-content: center; padding: 44px; }
.mt-error { margin: 0; padding: 12px 14px; font-size: 0.86rem; color: #C62828;
  background: rgba(198, 40, 40, 0.06); border: 1px solid rgba(198, 40, 40, 0.2);
  border-radius: var(--radius-sm); }

@media (max-width: 900px) {
  .mt-body { grid-template-columns: 1fr; }
  .mt-rail { position: static; flex-direction: row; flex-wrap: wrap; }
  .mt-ruler { flex-wrap: wrap; }
  .mt-seg { flex: 1 1 110px; }
}
</style>
