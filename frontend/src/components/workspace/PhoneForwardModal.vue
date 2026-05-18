<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="pf-overlay" @click.self="$emit('close')">
        <div class="pf-card">
          <button class="pf-close" @click="$emit('close')" aria-label="סגור">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>

          <header class="pf-header">
            <h2>העברת SMS אוטומטית</h2>
            <p class="pf-sub">
              הפורטל שולח SMS לטלפון שלך — הטלפון שולח אותו אלינו — ההפעלה ממשיכה לבד.
              הגדרה חד-פעמית.
            </p>
          </header>

          <!-- Status + webhook URL -->
          <section class="pf-section">
            <div class="pf-status-row">
              <span
                class="pf-pill"
                :class="{ 'pf-pill--ok': configured, 'pf-pill--off': !configured }"
              >
                <svg v-if="configured" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                <svg v-else width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                  <circle cx="12" cy="12" r="10"/>
                </svg>
                {{ configured ? 'מוגדר' : 'לא מוגדר' }}
              </span>
              <button
                v-if="!configured"
                class="pf-btn pf-btn--primary"
                :disabled="loading"
                @click="onRegenerate"
              >
                צור כתובת מאובטחת
              </button>
              <button
                v-else
                class="pf-btn pf-btn--ghost-danger"
                :disabled="loading"
                @click="confirmRegenOpen = true"
              >
                החלף מפתח
              </button>
            </div>

            <div v-if="configured" class="pf-url-wrap">
              <label class="pf-label">כתובת ה-webhook (העתק אל אפליקציית הטלפון)</label>
              <div class="pf-url-row">
                <input
                  ref="urlInputRef"
                  class="pf-url-input ltr-number"
                  :value="store.phoneForward.url"
                  readonly
                  @focus="$event.target.select()"
                />
                <button class="pf-btn pf-btn--ghost" @click="copyUrl">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                  </svg>
                  {{ copied ? 'הועתק!' : 'העתק' }}
                </button>
              </div>
            </div>
          </section>

          <!-- Mobile OS setup tabs -->
          <section v-if="configured" class="pf-section">
            <div class="pf-tabs">
              <button
                class="pf-tab"
                :class="{ 'pf-tab--active': osTab === 'android' }"
                @click="osTab = 'android'"
              >
                Android (SMS Forwarder)
              </button>
              <button
                class="pf-tab"
                :class="{ 'pf-tab--active': osTab === 'ios' }"
                @click="osTab = 'ios'"
              >
                iPhone (Shortcuts)
              </button>
            </div>

            <div v-if="osTab === 'android'" class="pf-instructions">
              <ol>
                <li>התקן מ-Google Play את <strong>SMS Forwarder</strong> (חיפוש "SMS Forwarder" של frzinapps).</li>
                <li>פתח את האפליקציה, צור Forwarding Rule חדש.</li>
                <li>סנן: <code>Sender contains</code> = שם החברה שמופיע ב-SMS (למשל <code>Migdal</code>, <code>מגדל</code>, <code>Phoenix</code>).</li>
                <li>בחר Target type = <strong>Webhook (HTTP POST)</strong>.</li>
                <li>הדבק את הכתובת שלמעלה בשדה URL.</li>
                <li>Body type = <strong>JSON</strong>, Body content:
                  <pre class="pf-code">{ "message": "[content]" }</pre>
                  (<code>[content]</code> הוא placeholder שהאפליקציה ממלאת בתוכן ה-SMS — אם השם שונה, השתמש במה שהאפליקציה מציעה.)
                </li>
                <li>שמור והפעל את הכלל.</li>
              </ol>
            </div>

            <div v-if="osTab === 'ios'" class="pf-instructions">
              <ol>
                <li>פתח את אפליקציית <strong>Shortcuts</strong> (מותקנת כברירת מחדל) → לשונית <strong>Automation</strong>.</li>
                <li>הקש <strong>+</strong> → <strong>Create Personal Automation</strong> → בחר <strong>Message</strong>.</li>
                <li>בשדה <strong>Message contains</strong> כתוב את שם החברה (למשל <code>Migdal</code>).</li>
                <li>חשוב: בחר <strong>Run Immediately</strong> (לא Run After Confirmation) → Next.</li>
                <li>הוסף פעולה: <strong>Get Contents of URL</strong>.</li>
                <li>בשדה URL הדבק את הכתובת שלמעלה.</li>
                <li>פתח את החצים: Method = <strong>POST</strong>, Request Body = <strong>JSON</strong>.</li>
                <li>Add new field → Text → Key = <code>message</code>, Value = <strong>Shortcut Input</strong> (מהמשתנים).</li>
                <li>הקש Done.</li>
              </ol>
            </div>
          </section>

          <!-- Test button -->
          <section v-if="configured" class="pf-section pf-test-section">
            <label class="pf-label">בדיקה מהירה (לא צריך טלפון)</label>
            <div class="pf-test-row">
              <input
                v-model="testMessage"
                class="pf-test-input"
                placeholder="Migdal verification code: 482917"
              />
              <button class="pf-btn pf-btn--primary" :disabled="testing" @click="onTest">
                {{ testing ? '...' : 'בדיקה' }}
              </button>
            </div>
            <div v-if="testResult" class="pf-test-result" :class="{ ok: testResult.extracted_otp }">
              {{
                testResult.extracted_otp
                  ? `קוד שזוהה: ${testResult.extracted_otp} — המערכת תקבל את ההודעה כרגע`
                  : 'לא נמצא קוד 4-8 ספרות בהודעה'
              }}
            </div>
          </section>
        </div>
      </div>
    </Transition>

    <!-- Regenerate confirmation -->
    <Transition name="modal">
      <div v-if="confirmRegenOpen" class="pf-overlay" @click.self="confirmRegenOpen = false">
        <div class="pf-card pf-card--sm">
          <h3>החלפת המפתח</h3>
          <p>המפתח הקיים יפסיק לעבוד מיד. תצטרך לעדכן את האפליקציה בטלפון עם הכתובת החדשה.</p>
          <div class="pf-modal-actions">
            <button class="pf-btn pf-btn--ghost" @click="confirmRegenOpen = false">ביטול</button>
            <button class="pf-btn pf-btn--danger" :disabled="loading" @click="onRegenerate">
              החלף עכשיו
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'

const props = defineProps({
  open: { type: Boolean, default: false },
})
defineEmits(['close'])

const store = usePortalAutomationStore()
const loading = ref(false)
const copied = ref(false)
const urlInputRef = ref(null)
const osTab = ref('android')
const testMessage = ref('Migdal verification code: 482917')
const testing = ref(false)
const testResult = ref(null)
const confirmRegenOpen = ref(false)

const configured = computed(() => !!store.phoneForward?.token)

watch(
  () => props.open,
  async (v) => {
    if (v) {
      loading.value = true
      try { await store.fetchPhoneForward() } finally { loading.value = false }
      testResult.value = null
    }
  },
  { immediate: true },
)

async function onRegenerate() {
  loading.value = true
  try {
    await store.regeneratePhoneForwardToken()
    confirmRegenOpen.value = false
  } finally {
    loading.value = false
  }
}

async function copyUrl() {
  const url = store.phoneForward?.url
  if (!url) return
  try {
    await navigator.clipboard.writeText(url)
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  } catch {
    urlInputRef.value?.select()
  }
}

async function onTest() {
  testing.value = true
  testResult.value = null
  try {
    testResult.value = await store.testPhoneForward(testMessage.value)
  } finally {
    testing.value = false
  }
}
</script>

<style scoped>
.pf-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.55);
  display: flex;
  align-items: center;
  justify-content: center;
  /* Higher than EmailSettingsModal (1100) and its cancel-sub overlay (1200)
     so the phone-forward setup floats on top when opened from settings. */
  z-index: 1300;
  padding: 20px;
  font-family: 'Heebo', sans-serif;
}
.pf-card {
  position: relative;
  background: #fff;
  border-radius: 14px;
  padding: 28px 32px 24px;
  max-width: 640px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 30px 80px rgba(15, 23, 42, 0.25);
  direction: rtl;
}
.pf-card--sm {
  max-width: 420px;
}
.pf-close {
  position: absolute;
  top: 14px;
  left: 14px;
  background: transparent;
  border: 0;
  color: #64748b;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
}
.pf-close:hover { background: #f1f5f9; color: #0f172a; }

.pf-header h2 {
  margin: 0 0 6px;
  font-size: 20px;
  color: #0f172a;
  font-weight: 700;
}
.pf-sub {
  margin: 0;
  color: #64748b;
  font-size: 13.5px;
  line-height: 1.55;
}

.pf-section {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid #e2e8f0;
}
.pf-section:first-of-type { border-top: 0; padding-top: 0; }

.pf-status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.pf-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border-radius: 999px;
  font-size: 12.5px;
  font-weight: 600;
}
.pf-pill--ok { background: rgba(34, 197, 94, 0.12); color: #15803d; }
.pf-pill--off { background: rgba(100, 116, 139, 0.14); color: #475569; }

.pf-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 8px;
  border: 0;
  font-family: inherit;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.pf-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.pf-btn--primary { background: #f57c00; color: #fff; }
.pf-btn--primary:hover:not(:disabled) { background: #ef6c00; }
.pf-btn--ghost { background: #f1f5f9; color: #334155; }
.pf-btn--ghost:hover:not(:disabled) { background: #e2e8f0; }
.pf-btn--ghost-danger { background: transparent; color: #b91c1c; border: 1px solid #fecaca; }
.pf-btn--ghost-danger:hover:not(:disabled) { background: #fef2f2; }
.pf-btn--danger { background: #dc2626; color: #fff; }
.pf-btn--danger:hover:not(:disabled) { background: #b91c1c; }

.pf-label {
  display: block;
  margin: 14px 0 6px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
}

.pf-url-wrap { margin-top: 8px; }
.pf-url-row { display: flex; gap: 8px; }
.pf-url-input {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 12.5px;
  font-family: 'SF Mono', Menlo, monospace;
  background: #f8fafc;
  direction: ltr;
}

.pf-tabs {
  display: flex;
  gap: 6px;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 14px;
}
.pf-tab {
  background: transparent;
  border: 0;
  padding: 8px 14px;
  font-family: inherit;
  font-size: 13px;
  color: #64748b;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.pf-tab--active {
  color: #f57c00;
  border-bottom-color: #f57c00;
  font-weight: 600;
}

.pf-instructions ol {
  margin: 0;
  padding-right: 18px;
  color: #334155;
  font-size: 13.5px;
  line-height: 1.7;
}
.pf-instructions li { margin-bottom: 6px; }
.pf-instructions code {
  background: #f1f5f9;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
  font-family: 'SF Mono', Menlo, monospace;
  direction: ltr;
  display: inline-block;
}
.pf-code {
  background: #0f172a;
  color: #e2e8f0;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-family: 'SF Mono', Menlo, monospace;
  margin: 6px 0;
  direction: ltr;
  text-align: left;
}

.pf-test-row { display: flex; gap: 8px; }
.pf-test-input {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
  direction: ltr;
  text-align: left;
}
.pf-test-result {
  margin-top: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 12.5px;
  background: rgba(220, 38, 38, 0.08);
  color: #991b1b;
}
.pf-test-result.ok {
  background: rgba(34, 197, 94, 0.12);
  color: #15803d;
}

.pf-modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 18px;
}

.modal-enter-active, .modal-leave-active { transition: opacity 0.18s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
