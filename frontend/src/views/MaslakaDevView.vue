<template>
  <div class="mt-wrap">
    <header class="mt-head">
      <div>
        <router-link to="/workspace" class="mt-back">חזרה למערכת</router-link>
        <h3>קונסולת מסלקה — פנימי</h3>
        <span class="mt-sub">כלי פיתוח. שני חלקים: מה אנחנו <strong>שולחים</strong> (בונה בקשה אמיתית בלי לשלוח), ומה אנחנו <strong>מקבלים</strong> (קבצי מסלקה אמיתיים מול הפרסר).</span>
      </div>
      <div class="mt-env" :class="{ 'mt-env--prod': envIsProd }">
        <span class="mt-env-dot"></span>{{ envIsProd ? 'ייצור' : 'בדיקות' }}
      </div>
    </header>

    <div v-if="loading && !samples.length" class="mt-loading"><div class="spinner"></div></div>

    <p v-if="error" class="mt-error">{{ error }}</p>

    <div v-else class="mt-modes">
      <button class="mt-mode" :class="{ 'mt-mode--on': mode === 'out' }" @click="mode = 'out'">בקשות יוצאות</button>
      <button class="mt-mode" :class="{ 'mt-mode--on': mode === 'in' }" @click="mode = 'in'">קבצים נכנסים</button>
      <button class="mt-mode" :class="{ 'mt-mode--on': mode === 'log' }" @click="mode = 'log'; loadLog()">מה נשלח בפועל</button>
    </div>

    <!-- OUTBOUND: build the exact request, per action code, per environment -->
    <div v-if="!loading && !error && mode === 'out'" class="mt-body">
      <nav class="mt-rail" aria-label="קודי פעולה">
        <div class="mt-group">
          <h4>קוד פעולה</h4>
          <button
            v-for="a in actions"
            :key="a.code"
            class="mt-item"
            :class="{ 'mt-item--on': a.code === actionCode }"
            @click="actionCode = a.code; runPreview()"
          >
            <span class="mt-item-title">{{ a.label }}</span>
            <span class="mt-item-meta ltr-number">{{ a.code }}</span>
          </button>
        </div>
      </nav>

      <section class="mt-main">
        <div class="mt-panel">
          <div class="mt-form">
            <label>
              <span>סביבה</span>
              <select v-model="environment" @change="runPreview()">
                <option value="TST">בדיקות (TST)</option>
                <option value="PRD">ייצור (PRD)</option>
              </select>
            </label>
            <label v-if="currentAction && currentAction.needs_customer">
              <span>מספר זהות לקוח</span>
              <input v-model="customerId" dir="ltr" placeholder="381788223" @keyup.enter="runPreview()" />
            </label>
            <label v-if="currentAction && currentAction.needs_customer">
              <span>שם פרטי</span>
              <input v-model="firstName" @keyup.enter="runPreview()" />
            </label>
            <label v-if="currentAction && currentAction.needs_customer">
              <span>שם משפחה</span>
              <input v-model="lastName" @keyup.enter="runPreview()" />
            </label>
            <button class="mt-primary" @click="runPreview()">בנה בקשה</button>
          </div>
          <p v-if="currentAction" class="mt-note">{{ currentAction.note }}</p>
        </div>

        <p v-if="previewError" class="mt-error">{{ previewError }}</p>

        <template v-if="preview">
          <div class="mt-ruler-card">
            <div class="mt-ruler-name ltr-number">{{ preview.filename }}</div>
            <div v-if="preview.filename_decoded" class="mt-ruler">
              <div v-for="seg in previewSegments" :key="seg.key" class="mt-seg" :style="{ flexGrow: seg.len }">
                <span class="mt-seg-raw ltr-number">{{ seg.raw }}</span>
                <span class="mt-seg-label">{{ seg.label }}</span>
                <span class="mt-seg-val">{{ seg.value }}</span>
              </div>
            </div>
          </div>

          <!-- The verdict that matters: does Swiftness's own schema accept this? -->
          <div v-if="preview.validation" class="mt-valid" :class="validClass">
            <div class="mt-valid-head">
              <span class="mt-valid-badge">{{ validLabel }}</span>
              <span class="mt-valid-schema ltr-number" v-if="preview.validation.schema">{{ preview.validation.schema }}</span>
            </div>
            <p v-if="preview.validation.ok === true" class="mt-valid-note">
              הקובץ עומד בסכימה הרשמית של סוויפטנס. זו הבדיקה שחשפה ארבעה פגמים קטלניים ב-10/09 —
              בקשה שלא נבדקה מול הסכימה לא אומרת דבר על האם המסלקה תקבל אותה.
            </p>
            <ul v-else-if="preview.validation.errors.length" class="mt-valid-errs">
              <li v-for="(e, i) in preview.validation.errors" :key="i" dir="ltr">{{ e }}</li>
            </ul>
          </div>

          <div v-if="preview.blockers.length" class="mt-blockers">
            <h4>לא נשלח — מה עוד חסר</h4>
            <ul><li v-for="(b, i) in preview.blockers" :key="i">{{ b }}</li></ul>
          </div>

          <div class="mt-panel">
            <h4>ה-XML שהיינו שולחים</h4>
            <pre class="mt-xml" dir="ltr">{{ prettyXml }}</pre>
          </div>
        </template>
      </section>
    </div>

    <!-- What we ACTUALLY put on the wire. Six files were sent by hand on 10/09
         and the only record was a terminal scrollback. -->
    <div v-else-if="!loading && !error && mode === 'log'" class="mt-body mt-body--wide">
      <section class="mt-main">
        <div class="mt-panel">
          <h4>מצב הכספת</h4>
          <div v-if="vault" class="mt-vault">
            <div class="mt-vault-row">
              <span class="mt-vault-k">שרת כספת</span>
              <span class="mt-vault-v" :class="vault.is_vault_host ? 'ok' : 'warn'">
                {{ vault.is_vault_host ? 'כן' : 'לא — זהו שרת פיתוח' }}
              </span>
            </div>
            <div class="mt-vault-row">
              <span class="mt-vault-k">סביבה</span>
              <span class="mt-vault-v ltr-number">{{ vault.environment }}</span>
            </div>
            <div class="mt-vault-row">
              <span class="mt-vault-k">קבצים בתיבה הנכנסת</span>
              <span class="mt-vault-v ltr-number">{{ vault.inbox.length }}</span>
            </div>
          </div>
          <p v-if="vault && vault.note" class="mt-vault-note">{{ vault.note }}</p>
          <p v-if="vault && vault.error" class="mt-error">{{ vault.error }}</p>
        </div>

        <div class="mt-panel">
          <h4>בקשות שנשלחו</h4>
          <p v-if="!sends.length" class="mt-vault-note">
            עדיין לא נשלחה אף בקשה דרך האפליקציה. שליחה מתבצעת רק מה-Gateway
            (MASLAKA_VAULT_HOST=true) — הבקשות שנשלחו ידנית ב-10/09 אינן מופיעות כאן.
          </p>
          <div v-else class="mt-table-scroll">
            <table class="mt-table">
              <thead>
                <tr>
                  <th>לקוח</th><th>קוד</th><th>סטטוס</th><th>שם הקובץ</th>
                  <th>נשלח</th><th>אושר</th><th>גופים</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in sends" :key="r.id">
                  <td><span class="ltr-number">{{ r.customer_id_number }}</span></td>
                  <td><span class="ltr-number">{{ r.action_code || '—' }}</span></td>
                  <td>{{ r.status }}</td>
                  <td><span class="ltr-number mt-fn">{{ r.filename || '—' }}</span></td>
                  <td><span class="ltr-number">{{ shortTime(r.submitted_at) }}</span></td>
                  <td><span class="ltr-number">{{ shortTime(r.acknowledged_at) }}</span></td>
                  <td><span class="ltr-number">{{ r.providers_received }}<template v-if="r.providers_expected">/{{ r.providers_expected }}</template></span></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>

    <div v-else-if="!loading && !error && mode === 'in'" class="mt-body">
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
          <!-- Validate the inbound file too: a parser will happily produce
               plausible numbers from a malformed file. -->
          <div v-if="detail.validation" class="mt-valid" :class="detailValidClass">
            <div class="mt-valid-head">
              <span class="mt-valid-badge">{{ detailValidLabel }}</span>
              <span class="mt-valid-schema ltr-number" v-if="detail.validation.schema">{{ detail.validation.schema }}</span>
            </div>
            <ul v-if="detail.validation.ok === false && detail.validation.errors.length" class="mt-valid-errs">
              <li v-for="(e, i) in detail.validation.errors.slice(0, 12)" :key="i" dir="ltr">{{ e }}</li>
            </ul>
          </div>

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
import api from '../api/client.js'

const samples = ref([])
const selectedName = ref('')
const detail = ref(null)
const loading = ref(true)
const detailLoading = ref(false)
const error = ref('')
const showXml = ref(false)

// Two halves of one protocol: what we send, and what comes back.
const mode = ref('out')
const sends = ref([])
const vault = ref(null)

// `ok === null` is NOT the same as false: it means nobody validated this file.
// A console that shows a green tick for an unchecked file is worse than useless.
function verdict(v) {
  if (!v) return { cls: '', label: '' }
  if (v.ok === true) return { cls: 'mt-valid--ok', label: 'תקין מול הסכימה הרשמית' }
  if (v.ok === false) return { cls: 'mt-valid--bad', label: `לא תקין — ${v.errors.length} שגיאות` }
  return { cls: 'mt-valid--unknown', label: 'לא נבדק מול סכימה' }
}
const validClass = computed(() => verdict(preview.value?.validation).cls)
const validLabel = computed(() => verdict(preview.value?.validation).label)
const detailValidClass = computed(() => verdict(detail.value?.validation).cls)
const detailValidLabel = computed(() => verdict(detail.value?.validation).label)

function shortTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.toLocaleDateString('he-IL')} ${d.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })}`
}

async function loadLog() {
  try {
    const [s, v] = await Promise.all([api.get('/maslaka/sends'), api.get('/maslaka/vault')])
    sends.value = s.data
    vault.value = v.data
  } catch (e) {
    error.value = e?.response?.data?.detail || 'שגיאה בטעינת יומן השליחות'
  }
}
const actions = ref([])
const actionCode = ref('9100')
const environment = ref('TST')
const customerId = ref('381788223')
const firstName = ref('שמעון')
const lastName = ref('לוי')
const preview = ref(null)
const previewError = ref('')

const currentAction = computed(() => actions.value.find(a => a.code === actionCode.value) || null)

const previewSegments = computed(() => buildSegments(preview.value?.filename_decoded))

// Indent the flat XML so the envelope is readable. The builder emits it
// unindented because whitespace between elements is not ours to invent on a
// file a regulator parses — this is display only.
const prettyXml = computed(() => {
  const raw = preview.value?.xml || ''
  if (!raw) return ''
  let depth = 0
  return raw
    .replace(/></g, '>\n<')
    .split('\n')
    .map(line => {
      if (/^<\//.test(line)) depth = Math.max(0, depth - 1)
      const out = '  '.repeat(depth) + line
      if (/^<[^/?!][^>]*[^/]>$/.test(line) && !/^<\//.test(line)) depth += 1
      return out
    })
    .join('\n')
})

async function loadActions() {
  try {
    const { data } = await api.get('/maslaka/actions')
    actions.value = data
    if (data.length && !data.some(a => a.code === actionCode.value)) actionCode.value = data[0].code
    await runPreview()
  } catch (e) {
    previewError.value = 'לא ניתן לטעון את קודי הפעולה'
  }
}

async function runPreview() {
  previewError.value = ''
  try {
    const { data } = await api.post('/maslaka/preview', {
      action_code: actionCode.value,
      environment: environment.value,
      customer_id_number: customerId.value,
      first_name: firstName.value,
      last_name: lastName.value,
    })
    preview.value = data
  } catch (e) {
    preview.value = null
    previewError.value = e?.response?.data?.detail || 'בניית הבקשה נכשלה'
  }
}

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
const segments = computed(() => buildSegments(detail.value?.filename))

function buildSegments(f) {
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
}

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

onMounted(() => { load(); loadActions() })
</script>

<style scoped>
.mt-wrap {
  display: flex; flex-direction: column; gap: 18px;
  max-width: 1320px; margin: 0 auto; padding: 28px 24px 60px;
}
.mt-back {
  display: inline-block; margin-bottom: 8px; font-size: 0.8rem;
  color: var(--text-secondary); text-decoration: none;
}
.mt-back:hover { color: var(--tab-maslaka); }

.mt-modes { display: flex; gap: 8px; }
.mt-mode {
  padding: 8px 16px; font-family: inherit; font-size: 0.86rem; cursor: pointer;
  background: var(--surface); color: var(--text-secondary);
  border: 1px solid var(--border); border-radius: var(--radius-sm);
}
.mt-mode--on {
  background: var(--tab-maslaka-wash); color: var(--tab-maslaka);
  border-color: var(--tab-maslaka); font-weight: 600;
}

.mt-form { display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end; }
.mt-form label { display: flex; flex-direction: column; gap: 4px; font-size: 0.78rem; color: var(--text-secondary); }
.mt-form input, .mt-form select {
  padding: 7px 10px; font-family: inherit; font-size: 0.86rem; min-width: 150px;
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  background: var(--bg); color: var(--text-primary);
}
.mt-primary {
  padding: 8px 18px; font-family: inherit; font-size: 0.86rem; font-weight: 600;
  cursor: pointer; color: #fff; background: var(--tab-maslaka);
  border: 1px solid var(--tab-maslaka); border-radius: var(--radius-sm);
}

.mt-blockers {
  padding: 14px 16px; border-radius: var(--radius-md);
  background: rgba(249, 169, 55, 0.08); border: 1px solid rgba(249, 169, 55, 0.35);
}
.mt-blockers h4 { margin: 0 0 8px; font-size: 0.9rem; color: var(--text-primary); }
.mt-blockers ul { margin: 0; padding-inline-start: 18px; }
.mt-blockers li { font-size: 0.83rem; color: var(--text-primary); line-height: 1.7; }

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
.mt-valid {
  padding: 12px 14px; border-radius: var(--radius-md);
  border: 1px solid var(--border); background: var(--surface);
}
.mt-valid-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.mt-valid-badge { font-size: 0.88rem; font-weight: 700; }
.mt-valid-schema { font-size: 0.74rem; color: var(--text-secondary); }
.mt-valid--ok { background: rgba(46,132,74,0.07); border-color: rgba(46,132,74,0.35); }
.mt-valid--ok .mt-valid-badge { color: #2E844A; }
.mt-valid--bad { background: rgba(198,40,40,0.06); border-color: rgba(198,40,40,0.3); }
.mt-valid--bad .mt-valid-badge { color: #C62828; }
.mt-valid--unknown { background: rgba(249,169,55,0.08); border-color: rgba(249,169,55,0.35); }
.mt-valid--unknown .mt-valid-badge { color: #B26B00; }
.mt-valid-note { margin: 8px 0 0; font-size: 0.82rem; color: var(--text-secondary); line-height: 1.6; max-width: 78ch; }
.mt-valid-errs { margin: 8px 0 0; padding-inline-start: 18px; }
.mt-valid-errs li { font-size: 0.78rem; color: #C62828; line-height: 1.65; }

.mt-vault { display: flex; flex-wrap: wrap; gap: 10px; }
.mt-vault-row {
  flex: 1 1 150px; padding: 10px 12px; background: var(--bg);
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  display: flex; flex-direction: column; gap: 3px;
}
.mt-vault-k { font-size: 0.73rem; color: var(--text-secondary); }
.mt-vault-v { font-size: 1rem; font-weight: 700; color: var(--text-primary); }
.mt-vault-v.ok { color: #2E844A; }
.mt-vault-v.warn { color: #B26B00; }
.mt-vault-note { margin: 10px 0 0; font-size: 0.82rem; color: var(--text-secondary); line-height: 1.65; max-width: 78ch; }
.mt-fn { font-size: 0.72rem; }
.mt-body--wide { display: block; }
</style>
