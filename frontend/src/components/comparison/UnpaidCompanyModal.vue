<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="ucm-overlay" @click.self="$emit('close')">
        <div class="ucm-card" role="dialog" aria-modal="true" aria-labelledby="ucm-title" @keydown.escape="$emit('close')">
          <header class="ucm-head">
            <div class="ucm-head-text">
              <h3 id="ucm-title" class="ucm-title">לא שולם — {{ company }}</h3>
              <p class="ucm-why">
                הלקוחות האלה מופיעים בפרודוקציה, אבל לא נמצאו בדוח הנפרעים של {{ company }} —
                כלומר החברה לא שילמה עליהם עמלה.
              </p>
            </div>
            <button class="ucm-close" type="button" aria-label="סגור" @click="$emit('close')">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
          </header>

          <div v-if="loading" class="ucm-state">טוען…</div>
          <div v-else-if="error" class="ucm-state ucm-state--error">{{ error }}</div>
          <template v-else-if="data">
            <div class="ucm-totals">
              <div class="ucm-total">
                <span class="ucm-total-label">לקוחות</span>
                <span class="ltr-number">{{ data.customers.length }}</span>
              </div>
              <div class="ucm-total">
                <span class="ucm-total-label">מוצרים</span>
                <span class="ltr-number">{{ productCount }}</span>
              </div>
              <div v-if="data.total_expected > 0" class="ucm-total ucm-total--gap">
                <span class="ucm-total-label">עמלה צפויה שלא התקבלה</span>
                <span class="ltr-number">{{ fmtMoney(data.total_expected) }}</span>
              </div>
            </div>
            <p v-if="noRateCount" class="ucm-note">
              ל-{{ noRateCount }} מוצרים אין שיעור עמלה מוגדר, ולכן הסכום הצפוי שלהם לא חושב.
              אפשר להוסיף שיעור ב"מדף ההסכמים".
            </p>

            <div class="ucm-list">
              <article v-for="c in data.customers" :key="c.id_number" class="ucm-cust">
                <div class="ucm-cust-head">
                  <span class="ucm-cust-name">{{ c.name }}</span>
                  <span class="ucm-cust-id">ת.ז <span class="ltr-number">{{ c.id_number }}</span></span>
                  <span v-if="c.expected > 0" class="ucm-cust-exp ltr-number">{{ fmtMoney(c.expected) }}</span>
                </div>
                <table class="ucm-table">
                  <thead>
                    <tr>
                      <th>מוצר</th>
                      <th>פוליסה</th>
                      <th>פרמיה</th>
                      <th>צבירה</th>
                      <th>עמלה צפויה</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(p, i) in c.products" :key="i">
                      <td>{{ p.product || '—' }}</td>
                      <td><span class="ltr-number">{{ p.policy_number || '—' }}</span></td>
                      <td><span v-if="p.premium > 0" class="ltr-number">{{ fmtMoney(p.premium) }}</span></td>
                      <td><span v-if="p.accumulation > 0" class="ltr-number">{{ fmtMoney(p.accumulation) }}</span></td>
                      <td>
                        <span v-if="p.expected > 0" class="ltr-number ucm-exp">{{ fmtMoney(p.expected) }}</span>
                        <span v-else class="ucm-norate">אין שיעור</span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </article>
            </div>
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  company: { type: String, default: '' },
  data: { type: Object, default: null }, // /comparison/company-unpaid response
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})
defineEmits(['close'])

const productCount = computed(() =>
  (props.data?.customers || []).reduce((n, c) => n + c.products.length, 0)
)
const noRateCount = computed(() =>
  (props.data?.customers || []).reduce((n, c) => n + c.products.filter((p) => !(p.expected > 0)).length, 0)
)

function fmtMoney(n) {
  return '₪' + Math.round(Number(n || 0)).toLocaleString('en-US')
}
</script>

<style scoped>
.ucm-overlay {
  position: fixed;
  inset: 0;
  z-index: 1010;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(24, 24, 24, 0.45);
}
.ucm-card {
  width: 100%;
  max-width: 820px;
  max-height: calc(100vh - 40px);
  overflow: auto;
  background: var(--card-bg, #fff);
  border-radius: var(--radius-md, 14px);
  box-shadow: 0 24px 64px rgba(24, 24, 24, 0.22);
  padding: 20px 22px;
  font-family: 'Heebo', sans-serif;
}
.ucm-head { display: flex; align-items: flex-start; gap: 12px; margin-bottom: 14px; }
.ucm-head-text { flex: 1; min-width: 0; }
.ucm-title { margin: 0 0 6px; font-size: 18px; font-weight: 800; color: var(--text, #181818); }
.ucm-why { margin: 0; font-size: 13px; line-height: 1.55; color: var(--text-secondary, #3E3E3C); max-width: 62ch; }
.ucm-close {
  flex-shrink: 0; width: 34px; height: 34px; display: grid; place-items: center;
  border: 1px solid var(--border-subtle, #e5e7eb); border-radius: 50%;
  background: #fff; color: var(--text-secondary, #3E3E3C); cursor: pointer;
}
.ucm-close:hover { background: var(--bg, #F3F3F3); }
.ucm-state { padding: 30px 0; text-align: center; color: var(--text-muted, #706E6B); font-size: 13px; }
.ucm-state--error { color: #C23934; }

.ucm-totals { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; }
.ucm-total {
  display: flex; flex-direction: column; gap: 2px;
  padding: 8px 14px; border-radius: 12px;
  background: var(--bg, #F3F3F3); font-size: 18px; font-weight: 800; color: var(--text, #181818);
}
.ucm-total-label { font-size: 11.5px; font-weight: 600; color: var(--text-muted, #706E6B); }
.ucm-total--gap { background: rgba(224, 75, 72, 0.08); color: #C23934; }
.ucm-note {
  margin: 0 0 12px; padding: 8px 12px; border-radius: 10px;
  background: rgba(217, 130, 15, 0.08); color: #8A5A0B; font-size: 12.5px; line-height: 1.5;
}

.ucm-list { display: flex; flex-direction: column; gap: 10px; }
.ucm-cust { border: 1px solid var(--border-subtle, #e5e7eb); border-radius: 12px; padding: 10px 12px; }
.ucm-cust-head { display: flex; align-items: baseline; gap: 10px; margin-bottom: 6px; }
.ucm-cust-name { font-size: 14px; font-weight: 700; color: var(--text, #181818); }
.ucm-cust-id { font-size: 12px; color: var(--text-muted, #706E6B); }
.ucm-cust-exp { margin-inline-start: auto; font-size: 13px; font-weight: 700; color: #C23934; }

.ucm-table { width: 100%; border-collapse: collapse; table-layout: fixed; font-size: 12.5px; }
.ucm-table th {
  text-align: start; font-weight: 600; color: var(--text-muted, #706E6B);
  padding: 4px 6px; border-bottom: 1px solid var(--border-subtle, #e5e7eb);
}
.ucm-table th:nth-child(n+2), .ucm-table td:nth-child(n+2) { width: 100px; text-align: center; }
.ucm-table td { padding: 5px 6px; color: var(--text-secondary, #3E3E3C); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ucm-exp { color: #C23934; font-weight: 700; }
.ucm-norate { font-size: 11px; color: var(--text-muted, #706E6B); }

@media (max-width: 640px) {
  .ucm-table th:nth-child(3), .ucm-table td:nth-child(3),
  .ucm-table th:nth-child(4), .ucm-table td:nth-child(4) { display: none; }
}
</style>
