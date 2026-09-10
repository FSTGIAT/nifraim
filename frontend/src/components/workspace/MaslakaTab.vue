<template>
  <div class="mk-wrap">
    <header class="mk-head">
      <div>
        <h3>מסלקה פנסיונית</h3>
        <span class="mk-sub">משיכת התמונה הפנסיונית המלאה של לקוח — כל המוצרים שלו בכל הגופים, גם כאלה שלא מופיעים באף דוח שאנחנו מורידים.</span>
      </div>
    </header>

    <!-- Honest gate. The button would 503 today; say why instead. -->
    <div v-if="gate" class="mk-gate">
      <h4>השירות עדיין לא פעיל</h4>
      <p>{{ gate }}</p>
      <!-- Updated 2026-09-10: the first two are DONE. The vault connects, uploads
           succeed in ~150ms, and MASLAKA_AGENT_ID is issued. Leaving them listed
           would misreport where we actually are. -->
      <ul>
        <li>כספת הבדיקות (TST) מחוברת — קבצים נשלחים בהצלחה</li>
        <li>ממתינים להפעלה שלנו כבעל רישיון <strong>שולח</strong> אצל המסלקה</li>
        <li>לכל לקוח נדרש ייפוי כוח חתום לפני בקשת מידע</li>
      </ul>
    </div>

    <div class="mk-ask">
      <label>
        <span>מספר זהות</span>
        <input v-model="idNumber" dir="ltr" placeholder="381788223" maxlength="9" @keyup.enter="ask" />
      </label>
      <label>
        <span>שם הלקוח</span>
        <input v-model="customerName" placeholder="לא חובה" @keyup.enter="ask" />
      </label>
      <button class="mk-primary" :disabled="!idNumber || busy" @click="ask">
        {{ busy ? 'שולח…' : 'בקש מידע' }}
      </button>
    </div>

    <p v-if="askError" class="mk-error">{{ askError }}</p>

    <div v-if="loading" class="mk-loading"><div class="spinner"></div></div>

    <div v-else-if="!inquiries.length" class="mk-empty">
      <p>עדיין לא נשלחו בקשות מידע.</p>
      <p class="mk-empty-note">בקשה נשלחת פעם אחת ללקוח, והתשובות מגיעות מכל הגופים המנהלים תוך ימי עסקים ספורים.</p>
    </div>

    <table v-else class="mk-table">
      <thead>
        <tr>
          <th>לקוח</th><th>מספר זהות</th><th>סטטוס</th>
          <th>נשלח</th><th>גופים שהשיבו</th><th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="q in inquiries" :key="q.id">
          <td>{{ q.customer_name || '—' }}</td>
          <td><span class="ltr-number">{{ q.customer_id_number }}</span></td>
          <td><span class="mk-status" :class="`mk-status--${q.status}`">{{ statusLabel(q.status) }}</span></td>
          <td><span class="ltr-number">{{ formatDate(q.submitted_at) }}</span></td>
          <td>
            <span class="ltr-number">
              {{ q.providers_received || 0 }}<template v-if="q.providers_expected">/{{ q.providers_expected }}</template>
            </span>
          </td>
          <td class="mk-actions">
            <button class="mk-link" @click="openCustomer(q.customer_id_number)">הצג נתונים</button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Holdings for one customer -->
    <div v-if="picture" class="mk-picture">
      <div class="mk-picture-head">
        <h4>{{ picture.customer_name || picture.id_number }}</h4>
        <button class="mk-link" @click="picture = null">סגור</button>
      </div>
      <div class="mk-kpis">
        <div class="mk-kpi">
          <span class="mk-kpi-n ltr-number">{{ money(picture.total_accumulation) }}</span>
          <span class="mk-kpi-l">סך צבירה</span>
        </div>
        <div class="mk-kpi">
          <span class="mk-kpi-n ltr-number">{{ picture.products_count }}</span>
          <span class="mk-kpi-l">מוצרים</span>
        </div>
      </div>
      <table class="mk-table">
        <thead>
          <tr><th>חברה</th><th>מוצר</th><th>מספר פוליסה</th><th>צבירה</th><th>סטטוס התאמה</th></tr>
        </thead>
        <tbody>
          <tr v-for="(p, i) in picture.products" :key="i">
            <td>{{ p.receiving_company || '—' }}</td>
            <td>{{ p.product || p.product_type || '—' }}</td>
            <td><span class="ltr-number">{{ p.fund_policy_number || '—' }}</span></td>
            <td><span class="ltr-number">{{ money(p.accumulation) }}</span></td>
            <td>{{ p.match_status === 'matched' ? 'תואם לפרודוקציה' : 'לא נמצא אצלנו' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../../api/client.js'

const idNumber = ref('')
const customerName = ref('')
const inquiries = ref([])
const picture = ref(null)
const loading = ref(true)
const busy = ref(false)
const askError = ref('')
const gate = ref('')

const STATUS = {
  pending: 'ממתין לשליחה',
  submitted: 'נשלח למסלקה',
  acknowledged: 'התקבל אישור',
  partial: 'תשובות חלקיות',
  complete: 'הושלם',
  failed: 'נכשל',
  expired: 'פג תוקף',
}
function statusLabel(s) { return STATUS[s] || s }

function money(v) {
  const n = Number(v || 0)
  return n ? n.toLocaleString('he-IL', { maximumFractionDigits: 0 }) : '—'
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('he-IL')
}

async function loadInquiries() {
  loading.value = true
  try {
    const { data } = await api.get('/maslaka/inquiries')
    inquiries.value = data
  } catch (e) {
    // A 503 here means the feature is gated, not that the request failed.
    if (e?.response?.status === 503) gate.value = e.response.data.detail
  } finally {
    loading.value = false
  }
}

async function ask() {
  askError.value = ''
  busy.value = true
  try {
    await api.post('/maslaka/inquiry', {
      customer_id_number: idNumber.value.trim(),
      customer_name: customerName.value.trim() || null,
    })
    idNumber.value = ''
    customerName.value = ''
    await loadInquiries()
  } catch (e) {
    askError.value = e?.response?.data?.detail || 'הבקשה נכשלה'
  } finally {
    busy.value = false
  }
}

async function openCustomer(id) {
  picture.value = null
  try {
    const { data } = await api.get(`/maslaka/customer/${encodeURIComponent(id)}`)
    picture.value = data
  } catch (e) {
    askError.value = e?.response?.status === 404
      ? 'עדיין לא התקבלו נתונים עבור הלקוח הזה'
      : 'שגיאה בטעינת הנתונים'
  }
}

onMounted(loadInquiries)
</script>

<style scoped>
.mk-wrap { display: flex; flex-direction: column; gap: 16px; }
.mk-head h3 { margin: 0 0 4px; font-size: 1.35rem; font-weight: 700; color: var(--text-primary); }
.mk-sub { font-size: 0.85rem; color: var(--text-secondary); max-width: 66ch; line-height: 1.55; }

.mk-gate {
  padding: 14px 16px; border-radius: var(--radius-md);
  background: rgba(249, 169, 55, 0.08); border: 1px solid rgba(249, 169, 55, 0.35);
}
.mk-gate h4 { margin: 0 0 6px; font-size: 0.95rem; color: var(--text-primary); }
.mk-gate p { margin: 0 0 8px; font-size: 0.85rem; color: var(--text-primary); line-height: 1.6; }
.mk-gate ul { margin: 0; padding-inline-start: 18px; }
.mk-gate li { font-size: 0.83rem; color: var(--text-secondary); line-height: 1.7; }

.mk-ask {
  display: flex; flex-wrap: wrap; gap: 12px; align-items: flex-end;
  padding: 16px; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius-md);
}
.mk-ask label { display: flex; flex-direction: column; gap: 4px; font-size: 0.78rem; color: var(--text-secondary); }
.mk-ask input {
  padding: 8px 11px; font-family: inherit; font-size: 0.9rem; min-width: 170px;
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  background: var(--bg); color: var(--text-primary);
}
.mk-primary {
  padding: 9px 20px; font-family: inherit; font-size: 0.88rem; font-weight: 600;
  cursor: pointer; color: #fff; background: var(--tab-maslaka);
  border: 1px solid var(--tab-maslaka); border-radius: var(--radius-sm);
}
.mk-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.mk-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; table-layout: fixed; }
.mk-table th, .mk-table td {
  padding: 9px 10px; border-bottom: 1px solid var(--border); text-align: right;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.mk-table thead th { font-size: 0.77rem; font-weight: 600; color: var(--text-secondary); }
.mk-table td:nth-child(2), .mk-table td:nth-child(4), .mk-table td:nth-child(5),
.mk-table th:nth-child(2), .mk-table th:nth-child(4), .mk-table th:nth-child(5) { text-align: center; width: 100px; }

.mk-status { padding: 2px 9px; border-radius: 999px; font-size: 0.76rem; font-weight: 600; }
.mk-status--pending { background: var(--tab-maslaka-wash); color: var(--tab-maslaka); }
.mk-status--submitted, .mk-status--acknowledged, .mk-status--partial { background: rgba(47,115,196,0.1); color: #2F73C4; }
.mk-status--complete { background: rgba(46,132,74,0.1); color: #2E844A; }
.mk-status--failed, .mk-status--expired { background: rgba(198,40,40,0.08); color: #C62828; }

.mk-actions { text-align: left; }
.mk-link {
  background: none; border: none; padding: 0; cursor: pointer;
  font-family: inherit; font-size: 0.84rem; color: var(--tab-maslaka);
}

.mk-picture {
  padding: 16px; background: var(--surface);
  border: 1px solid var(--border); border-radius: var(--radius-md);
}
.mk-picture-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.mk-picture-head h4 { margin: 0; font-size: 1rem; font-weight: 700; color: var(--text-primary); }
.mk-kpis { display: flex; gap: 10px; margin-bottom: 14px; }
.mk-kpi {
  flex: 1 1 120px; padding: 11px 13px; background: var(--bg);
  border: 1px solid var(--border); border-radius: var(--radius-sm);
  display: flex; flex-direction: column; gap: 3px;
}
.mk-kpi-n { font-size: 1.3rem; font-weight: 700; color: var(--text-primary); }
.mk-kpi-l { font-size: 0.74rem; color: var(--text-secondary); }

.mk-empty { padding: 34px 16px; text-align: center; }
.mk-empty p { margin: 0 0 6px; font-size: 0.9rem; color: var(--text-primary); }
.mk-empty-note { font-size: 0.82rem !important; color: var(--text-secondary) !important; max-width: 56ch; margin: 0 auto !important; line-height: 1.6; }

.mk-loading { display: flex; justify-content: center; padding: 40px; }
.mk-error {
  margin: 0; padding: 11px 14px; font-size: 0.85rem; color: #C62828;
  background: rgba(198,40,40,0.06); border: 1px solid rgba(198,40,40,0.2);
  border-radius: var(--radius-sm);
}
</style>
