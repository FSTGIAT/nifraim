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
                Android
              </button>
              <button
                class="pf-tab"
                :class="{ 'pf-tab--active': osTab === 'ios' }"
                @click="osTab = 'ios'"
              >
                iPhone (Shortcuts)
              </button>
            </div>

            <div v-if="osTab === 'android'" class="pf-android-setup">
              <div class="pf-apk-hero" :class="{ 'pf-apk-hero--pending': apkReady === false }">
                <!-- QR code -->
                <div class="pf-apk-qr">
                  <div v-if="apkReady === null" class="pf-qr-placeholder pf-qr-placeholder--loading">
                    <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#ccc" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="pf-qr-spin">
                      <path d="M21 12a9 9 0 11-6.219-8.56"/>
                    </svg>
                  </div>
                  <div v-else-if="apkReady === false" class="pf-qr-placeholder pf-qr-placeholder--soon">
                    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#9CA3AF" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                      <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
                      <rect x="3" y="14" width="7" height="7"/><rect x="14" y="14" width="4" height="4"/>
                    </svg>
                  </div>
                  <img
                    v-else
                    :src="`https://api.qrserver.com/v1/create-qr-code/?size=130x130&data=${encodeURIComponent(APK_URL)}`"
                    alt="QR להורדת האפליקציה"
                    width="130"
                    height="130"
                  />
                  <span class="pf-qr-label">{{ apkReady ? 'סרוק להורדה' : apkReady === null ? 'בודק...' : 'בקרוב' }}</span>
                </div>

                <div class="pf-apk-info">
                  <div class="pf-apk-name">Nifraim SMS</div>
                  <div class="pf-apk-desc">אפליקציה ייעודית — מעבירה כל SMS לשרת אוטומטית</div>

                  <!-- Ready -->
                  <a v-if="apkReady" :href="APK_URL" class="pf-btn pf-btn--primary pf-apk-download" download>
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                      <polyline points="7 10 12 15 17 10"/>
                      <line x1="12" y1="15" x2="12" y2="3"/>
                    </svg>
                    הורד APK
                  </a>

                  <!-- Not yet available -->
                  <div v-else-if="apkReady === false" class="pf-apk-pending">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                    </svg>
                    האפליקציה בהכנה — תהיה זמינה לאחר ה-build הראשון
                  </div>

                  <!-- Checking -->
                  <div v-else class="pf-apk-checking">בודק זמינות...</div>
                </div>
              </div>

              <ol class="pf-steps">
                <li>
                  <strong>הורד והתקן</strong> — לחץ "הורד APK" או סרוק את הקוד. בטלפון: פתח את הקובץ → אפשר "התקנה ממקורות לא ידועים" אם תישאל.
                </li>
                <li>
                  <strong>הדבק את כתובת ה-Webhook</strong> — העתק את הכתובת שלמעלה ואז פתח את Nifraim SMS בטלפון → הדבק → שמור.
                </li>
                <li>
                  <strong>זהו</strong> — האפליקציה פועלת ברקע. בפעם הבאה שהפורטל שולח SMS, הוא יועבר אוטומטית.
                </li>
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

const APK_URL = 'https://nifraim-production.up.railway.app/api/downloads/android'

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
const apkReady = ref(null) // null=checking, true=ready, false=not yet

const configured = computed(() => !!store.phoneForward?.token)

async function checkApkReady() {
  apkReady.value = null
  try {
    const res = await fetch(APK_URL, { method: 'HEAD' })
    apkReady.value = res.ok
  } catch {
    apkReady.value = false
  }
}

watch(
  () => props.open,
  async (v) => {
    if (v) {
      loading.value = true
      try { await store.fetchPhoneForward() } finally { loading.value = false }
      testResult.value = null
      checkApkReady()
    }
  },
  { immediate: true },
)

watch(osTab, (tab) => {
  if (tab === 'android' && apkReady.value === null) checkApkReady()
})

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
  color: #706E6B;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
}
.pf-close:hover { background: #F3F3F3; color: #181818; }

.pf-header h2 {
  margin: 0 0 6px;
  font-size: 20px;
  color: #181818;
  font-weight: 700;
}
.pf-sub {
  margin: 0;
  color: #706E6B;
  font-size: 13.5px;
  line-height: 1.55;
}

.pf-section {
  margin-top: 22px;
  padding-top: 18px;
  border-top: 1px solid #E5E5E5;
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
.pf-pill--ok { background: rgba(46, 132, 74, 0.12); color: #1B5E20; }
.pf-pill--off { background: rgba(112, 110, 107, 0.14); color: #3E3E3C; }

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
.pf-btn--primary:hover:not(:disabled) { background: #E65100; }
.pf-btn--ghost { background: #F3F3F3; color: #3E3E3C; }
.pf-btn--ghost:hover:not(:disabled) { background: #E5E5E5; }
.pf-btn--ghost-danger { background: transparent; color: #C23934; border: 1px solid #FEF1EE; }
.pf-btn--ghost-danger:hover:not(:disabled) { background: #FEF1EE; }
.pf-btn--danger { background: #C23934; color: #fff; }
.pf-btn--danger:hover:not(:disabled) { background: #C23934; }

.pf-label {
  display: block;
  margin: 14px 0 6px;
  font-size: 12px;
  font-weight: 600;
  color: #3E3E3C;
}

.pf-url-wrap { margin-top: 8px; }
.pf-url-row { display: flex; gap: 8px; }
.pf-url-input {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid #DDDBDA;
  border-radius: 6px;
  font-size: 12.5px;
  font-family: 'SF Mono', Menlo, monospace;
  background: #F3F3F3;
  direction: ltr;
}

.pf-tabs {
  display: flex;
  gap: 6px;
  border-bottom: 1px solid #E5E5E5;
  margin-bottom: 14px;
}
.pf-tab {
  background: transparent;
  border: 0;
  padding: 8px 14px;
  font-family: inherit;
  font-size: 13px;
  color: #706E6B;
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
  color: #3E3E3C;
  font-size: 13.5px;
  line-height: 1.7;
}
.pf-instructions li { margin-bottom: 6px; }
.pf-instructions code {
  background: #F3F3F3;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 12px;
  font-family: 'SF Mono', Menlo, monospace;
  direction: ltr;
  display: inline-block;
}
.pf-code {
  background: #181818;
  color: #E5E5E5;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-family: 'SF Mono', Menlo, monospace;
  margin: 6px 0;
  direction: ltr;
  text-align: left;
}

/* Android dedicated-app setup */
.pf-android-setup { }

.pf-apk-hero {
  display: flex;
  gap: 20px;
  align-items: flex-start;
  padding: 16px;
  background: #F9F9F9;
  border-radius: 10px;
  border: 1px solid #E5E5E5;
  margin-bottom: 18px;
}
.pf-apk-hero--pending {
  background: #FAFAFA;
  border-color: #E5E5E5;
  opacity: 0.85;
}
.pf-apk-qr {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}
.pf-apk-qr img {
  border-radius: 8px;
  border: 1px solid #E5E5E5;
}
.pf-qr-label {
  font-size: 11px;
  color: #706E6B;
}
.pf-apk-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pf-apk-name {
  font-size: 16px;
  font-weight: 700;
  color: #181818;
}
.pf-apk-desc {
  font-size: 12.5px;
  color: #706E6B;
  line-height: 1.5;
}
.pf-apk-download {
  align-self: flex-start;
  margin-top: 6px;
  text-decoration: none;
}
.pf-apk-pending {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 7px 12px;
  border-radius: 8px;
  font-size: 12px;
  color: #6B7280;
  background: #F3F4F6;
  border: 1px dashed #D1D5DB;
}
.pf-apk-checking {
  margin-top: 8px;
  font-size: 12px;
  color: #9CA3AF;
}
.pf-qr-placeholder {
  width: 130px;
  height: 130px;
  border-radius: 8px;
  border: 1px solid #E5E5E5;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F9FAFB;
}
.pf-qr-placeholder--loading { background: #F9FAFB; }
.pf-qr-placeholder--soon { background: #F3F4F6; }
@keyframes pf-spin { to { transform: rotate(360deg); } }
.pf-qr-spin { animation: pf-spin 1s linear infinite; }

.pf-steps {
  margin: 0;
  padding-right: 20px;
  color: #3E3E3C;
  font-size: 13.5px;
  line-height: 1.7;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pf-steps li { padding-right: 4px; }

.pf-test-row { display: flex; gap: 8px; }
.pf-test-input {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid #DDDBDA;
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
  background: rgba(194, 57, 52, 0.08);
  color: #C23934;
}
.pf-test-result.ok {
  background: rgba(46, 132, 74, 0.12);
  color: #1B5E20;
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
