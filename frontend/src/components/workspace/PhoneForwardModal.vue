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
              <label class="pf-label">כתובת ה-webhook — סרוק עם הטלפון או העתק</label>
              <div class="pf-url-main-row">
                <div class="pf-url-qr-wrap">
                  <img
                    :src="`https://api.qrserver.com/v1/create-qr-code/?size=90x90&data=${encodeURIComponent(store.phoneForward.url)}`"
                    width="90"
                    height="90"
                    alt="QR לכתובת ה-webhook"
                  />
                  <span class="pf-url-qr-hint">סרוק → העתק את הכתובת → הדבק באפליקציה</span>
                </div>
                <div class="pf-url-right">
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
              <!-- Primary: direct APK download (the Play Store app is not yet
                   published — its link shows "הפריט לא נמצא"). Webhook is pasted
                   manually using the copy button above. -->
              <div class="pf-apk-hero">
                <div class="pf-apk-qr">
                  <img
                    :src="qrSrc(APK_URL)"
                    alt="QR להורדת האפליקציה (APK)"
                    width="150"
                    height="150"
                  />
                </div>
                <div class="pf-apk-info">
                  <div class="pf-apk-name">Nifraim (APK)</div>
                  <div class="pf-apk-desc">סרוק את הקוד או פתח את הקישור בטלפון → הורד את ה-APK → התקן (אשר "מקור לא מוכר").</div>
                  <a class="pf-apk-link ltr-number" :href="APK_URL" target="_blank" rel="noopener">{{ APK_URL }}</a>
                  <div class="pf-apk-scan-hint">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#F57C00" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z"/>
                    </svg>
                    פתח מצלמה בטלפון וסרוק את הקוד להורדת האפליקציה
                  </div>
                </div>
              </div>

              <ol class="pf-steps">
                <li>
                  <strong>התקן</strong> — סרוק את הקוד ← הורד את ה-APK ← התקן (אשר "מקור לא מוכר" אם תתבקש).
                </li>
                <li>
                  <strong>הדבק כתובת</strong> — לחץ "העתק" למעלה והדבק את כתובת ה-Webhook באפליקציה ← שמור.
                </li>
                <li>
                  <strong>אשר הרשאות</strong> — אשר הרשאת SMS וכבה אופטימיזציית סוללה (כפתורים באפליקציה).
                </li>
                <li>
                  <strong>זהו</strong> — כל SMS עם קוד מהפורטל מועבר אוטומטית, מיד, ואתה לא צריך לעשות כלום.
                </li>
              </ol>

              <!-- Fallback: Google Play (auto-configures webhook) — only once the
                   app is published to the user's Play account. -->
              <details class="pf-apk-fallback">
                <summary>התקנה מ-Google Play (כשהאפליקציה תפורסם)</summary>
                <div class="pf-apk-hero pf-apk-hero--fallback">
                  <div class="pf-apk-qr">
                    <img
                      :src="qrSrc(playInstallUrl)"
                      alt="QR להתקנה מ-Google Play"
                      width="150"
                      height="150"
                    />
                  </div>
                  <div class="pf-apk-info">
                    <div class="pf-apk-name">Nifraim (Google Play)</div>
                    <div class="pf-apk-badge-auto">
                      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="20 6 9 17 4 12"/>
                      </svg>
                      כתובת ה-Webhook מוגדרת אוטומטית בהתקנה
                    </div>
                    <div class="pf-apk-desc">זמין רק לאחר פרסום האפליקציה ב-Google Play לחשבון שלך. אם מוצג "הפריט לא נמצא" — השתמש בהתקנת ה-APK למעלה.</div>
                  </div>
                </div>
              </details>
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

          <!-- Company SMS templates manager -->
          <section v-if="configured" class="pf-section">
            <button class="pf-tpl-toggle" @click="showTemplates = !showTemplates">
              <svg
                width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
                :style="{ transform: showTemplates ? 'rotate(90deg)' : 'none', transition: 'transform .15s' }"
              >
                <polyline points="9 18 15 12 9 6"/>
              </svg>
              תבניות זיהוי SMS של חברות
              <span class="pf-tpl-count">{{ templates.length }}</span>
            </button>

            <div v-if="showTemplates" class="pf-tpl-body">
              <p class="pf-tpl-intro">
                כך האפליקציה יודעת אילו הודעות להעביר. הדבק הודעת SMS אמיתית של חברה —
                נבנה ממנה תבנית. הודעה עם קוד שלא תואמת אף תבנית <strong>תועבר בכל זאת</strong>
                (ברירת מחדל בטוחה). תבנית "חסימה" עוצרת הודעה אישית עם קוד מלהישלח.
              </p>

              <!-- Add / edit form -->
              <div class="pf-tpl-form">
                <div class="pf-tpl-form-row">
                  <input v-model="tplForm.company_name" class="pf-tpl-input" placeholder="שם חברה (למשל מגדל)" />
                  <label class="pf-tpl-block">
                    <input type="checkbox" v-model="tplForm.is_block" />
                    חסימה (אל תעביר)
                  </label>
                </div>
                <input
                  v-model="tplForm.example"
                  class="pf-tpl-input ltr-number"
                  placeholder="הדבק כאן הודעת SMS אמיתית, למשל: קוד האימות שלך במגדל 482917"
                  @input="onExampleInput"
                />
                <input
                  v-model="tplForm.pattern"
                  class="pf-tpl-input pf-tpl-pattern ltr-number"
                  placeholder="תבנית (regex) — נוצרת אוטומטית מההודעה, ניתן לערוך"
                />
                <div class="pf-tpl-form-actions">
                  <button class="pf-btn pf-btn--primary" :disabled="tplBusy || !tplForm.company_name || !tplForm.pattern" @click="saveTemplate">
                    {{ editingTplId ? 'עדכן' : 'הוסף תבנית' }}
                  </button>
                  <button v-if="editingTplId" class="pf-btn pf-btn--ghost" @click="resetTplForm">ביטול</button>
                  <button v-if="!templates.length" class="pf-btn pf-btn--ghost" :disabled="tplBusy" @click="seedTemplates">
                    טען תבניות ברירת מחדל
                  </button>
                </div>
              </div>

              <!-- Test box -->
              <div class="pf-tpl-testbox">
                <input
                  v-model="tplTest"
                  class="pf-tpl-input ltr-number"
                  placeholder="בדוק הודעה: יישלח / לא יישלח"
                />
                <span v-if="tplTest" class="pf-tpl-verdict" :class="{ ok: tplVerdict.forward, no: !tplVerdict.forward }">
                  {{ tplVerdict.forward ? 'יישלח' : 'לא יישלח' }} · {{ tplVerdict.reason }}
                </span>
              </div>

              <!-- List -->
              <ul class="pf-tpl-list">
                <li v-for="t in templates" :key="t.id" class="pf-tpl-item">
                  <span class="pf-tpl-badge" :class="t.is_block ? 'block' : 'allow'">
                    {{ t.is_block ? 'חסימה' : 'העברה' }}
                  </span>
                  <div class="pf-tpl-item-main">
                    <div class="pf-tpl-item-name">{{ t.company_name }}</div>
                    <div class="pf-tpl-item-pattern ltr-number">{{ t.pattern }}</div>
                  </div>
                  <button class="pf-tpl-icon" title="ערוך" @click="editTemplate(t)">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
                      <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                  </button>
                  <button class="pf-tpl-icon pf-tpl-icon--danger" title="מחק" @click="deleteTemplate(t)">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="3 6 5 6 21 6"/>
                      <path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                    </svg>
                  </button>
                </li>
                <li v-if="!templates.length" class="pf-tpl-empty">אין תבניות עדיין — הוסף אחת או טען ברירת מחדל.</li>
              </ul>
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
import { computed, ref, reactive, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import api from '../../api/client.js'

const APK_URL = 'https://nifraim-production.up.railway.app/api/downloads/android'
const PLAY_PACKAGE = 'com.nifraim.smsforwarder'

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

// Personalized Google Play link. The `referrer=token=<token>` rides through the
// Play Store and the app reads it on first launch to auto-fill this agent's webhook
// (no copy/paste). Only the agent who opens THIS link gets THIS token.
const playInstallUrl = computed(() => {
  const token = store.phoneForward?.token
  if (!token) return ''
  const referrer = encodeURIComponent(`token=${token}`)
  return `https://play.google.com/store/apps/details?id=${PLAY_PACKAGE}&referrer=${referrer}`
})
const qrSrc = (data) =>
  `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(data)}`

// ---- Company SMS templates ----
const showTemplates = ref(false)
const templates = ref([])
const tplBusy = ref(false)
const editingTplId = ref(null)
const tplForm = reactive({ company_name: '', example: '', pattern: '', is_block: false })
const tplTest = ref('')

watch(
  () => props.open,
  async (v) => {
    if (v) {
      loading.value = true
      try { await store.fetchPhoneForward() } finally { loading.value = false }
      testResult.value = null
      if (configured.value) loadTemplates()
    }
  },
  { immediate: true },
)

async function loadTemplates() {
  try {
    const { data } = await api.get('/sms-otp-templates')
    templates.value = data
  } catch { /* ignore */ }
}

function resetTplForm() {
  editingTplId.value = null
  tplForm.company_name = ''
  tplForm.example = ''
  tplForm.pattern = ''
  tplForm.is_block = false
}

/** Build a tolerant starter regex from a pasted SMS: escape literals, loosen
 *  whitespace, and turn the 4-8 digit code into \d{4,8}. The user can edit it. */
function suggestPattern(text) {
  if (!text) return ''
  let p = text.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  p = p.replace(/[ \t]+/g, '\\s+')
  p = p.replace(/\d{4,8}/g, '\\d{4,8}')
  return p
}

function onExampleInput() {
  // Only auto-fill while the pattern is empty or still matches the prior suggestion,
  // so we never clobber a hand-edited pattern.
  if (!tplForm.pattern || tplForm.pattern === suggestPattern(tplForm._lastExample || '')) {
    tplForm.pattern = suggestPattern(tplForm.example)
  }
  tplForm._lastExample = tplForm.example
}

async function saveTemplate() {
  tplBusy.value = true
  try {
    const payload = {
      company_name: tplForm.company_name.trim(),
      pattern: tplForm.pattern.trim(),
      example: tplForm.example.trim() || null,
      is_block: tplForm.is_block,
    }
    if (editingTplId.value) {
      await api.put(`/sms-otp-templates/${editingTplId.value}`, payload)
    } else {
      await api.post('/sms-otp-templates', payload)
    }
    resetTplForm()
    await loadTemplates()
  } finally {
    tplBusy.value = false
  }
}

function editTemplate(t) {
  editingTplId.value = t.id
  tplForm.company_name = t.company_name
  tplForm.example = t.example || ''
  tplForm.pattern = t.pattern
  tplForm.is_block = t.is_block
}

async function deleteTemplate(t) {
  if (!confirm(`למחוק את התבנית של ${t.company_name}?`)) return
  await api.delete(`/sms-otp-templates/${t.id}`)
  await loadTemplates()
}

async function seedTemplates() {
  tplBusy.value = true
  try {
    await api.post('/sms-otp-templates/seed')
    await loadTemplates()
  } finally {
    tplBusy.value = false
  }
}

function safeRegex(pattern) {
  try { return new RegExp(pattern, 'is') } catch { return null }
}

// Mirror of the Android OtpFilter decision (block -> allow -> fail-open).
const tplVerdict = computed(() => {
  const hay = tplTest.value || ''
  const active = templates.value
  for (const t of active) {
    if (!t.is_block) continue
    const re = safeRegex(t.pattern)
    if (re && re.test(hay)) return { forward: false, reason: `חסימה: ${t.company_name}` }
  }
  for (const t of active) {
    if (t.is_block) continue
    const re = safeRegex(t.pattern)
    if (re && re.test(hay)) return { forward: true, reason: `תואם ${t.company_name}` }
  }
  if (/\d{4,8}/.test(hay)) return { forward: true, reason: 'יש קוד (ברירת מחדל בטוחה)' }
  return { forward: false, reason: 'אין קוד' }
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
.pf-url-main-row {
  display: flex;
  gap: 14px;
  align-items: flex-start;
}
.pf-url-qr-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  flex-shrink: 0;
}
.pf-url-qr-wrap img {
  border-radius: 6px;
  border: 1px solid #E5E5E5;
}
.pf-url-qr-hint {
  font-size: 10px;
  color: #9CA3AF;
  text-align: center;
  max-width: 90px;
  line-height: 1.4;
}
.pf-url-right {
  flex: 1;
  min-width: 0;
}
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
.pf-apk-link {
  display: inline-block;
  align-self: flex-start;
  direction: ltr;
  font-size: 11.5px;
  color: #F57C00;
  word-break: break-all;
  text-decoration: underline;
}
.pf-apk-badge-auto {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  font-size: 12px;
  font-weight: 600;
  color: #1B5E20;
  background: rgba(46, 132, 74, 0.12);
  border-radius: 999px;
  padding: 3px 10px;
}
.pf-apk-fallback {
  margin-top: 16px;
  border-top: 1px dashed #E5E5E5;
  padding-top: 12px;
}
.pf-apk-fallback summary {
  font-size: 12.5px;
  color: #706E6B;
  cursor: pointer;
  user-select: none;
}
.pf-apk-fallback summary:hover { color: #181818; }
.pf-apk-hero--fallback { background: #FAFAFA; opacity: 0.92; }
.pf-apk-scan-hint {
  display: flex;
  align-items: flex-start;
  gap: 7px;
  margin-top: 10px;
  font-size: 13px;
  color: #374151;
  line-height: 1.5;
}
.pf-qr-label { display: none; }
.pf-apk-soon {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  margin-top: 10px;
  font-size: 13px;
  color: #92400E;
  background: #FEF3C7;
  border: 1px solid #FCD34D;
  border-radius: 8px;
  padding: 8px 14px;
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

/* Templates manager */
.pf-tpl-toggle {
  display: flex;
  align-items: center;
  gap: 8px;
  background: transparent;
  border: 0;
  padding: 0;
  font-family: inherit;
  font-size: 14px;
  font-weight: 600;
  color: #181818;
  cursor: pointer;
}
.pf-tpl-count {
  background: #F3F3F3;
  color: #706E6B;
  border-radius: 999px;
  padding: 1px 9px;
  font-size: 12px;
  font-weight: 600;
}
.pf-tpl-body { margin-top: 14px; }
.pf-tpl-intro {
  margin: 0 0 14px;
  font-size: 12.5px;
  color: #706E6B;
  line-height: 1.6;
}
.pf-tpl-form { display: flex; flex-direction: column; gap: 8px; }
.pf-tpl-form-row { display: flex; gap: 10px; align-items: center; }
.pf-tpl-input {
  flex: 1;
  padding: 8px 10px;
  border: 1px solid #DDDBDA;
  border-radius: 6px;
  font-size: 13px;
  font-family: inherit;
}
.pf-tpl-input.ltr-number { direction: ltr; text-align: left; }
.pf-tpl-pattern {
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 12px;
  background: #F9F9F9;
}
.pf-tpl-block {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: #3E3E3C;
  white-space: nowrap;
  cursor: pointer;
}
.pf-tpl-form-actions { display: flex; gap: 8px; margin-top: 2px; }
.pf-tpl-testbox {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 14px 0;
  padding: 10px;
  background: #F9F9F9;
  border-radius: 8px;
}
.pf-tpl-verdict { font-size: 12.5px; font-weight: 600; white-space: nowrap; }
.pf-tpl-verdict.ok { color: #1B5E20; }
.pf-tpl-verdict.no { color: #C23934; }

.pf-tpl-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.pf-tpl-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: 1px solid #E5E5E5;
  border-radius: 8px;
}
.pf-tpl-badge {
  flex-shrink: 0;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 999px;
}
.pf-tpl-badge.allow { background: rgba(46, 132, 74, 0.12); color: #1B5E20; }
.pf-tpl-badge.block { background: rgba(194, 57, 52, 0.1); color: #C23934; }
.pf-tpl-item-main { flex: 1; min-width: 0; }
.pf-tpl-item-name { font-size: 13px; font-weight: 600; color: #181818; }
.pf-tpl-item-pattern {
  font-size: 11px;
  color: #9CA3AF;
  font-family: 'SF Mono', Menlo, monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.pf-tpl-icon {
  flex-shrink: 0;
  background: transparent;
  border: 0;
  color: #706E6B;
  cursor: pointer;
  padding: 5px;
  border-radius: 6px;
}
.pf-tpl-icon:hover { background: #F3F3F3; color: #181818; }
.pf-tpl-icon--danger:hover { background: #FEF1EE; color: #C23934; }
.pf-tpl-empty { font-size: 12.5px; color: #9CA3AF; padding: 8px 2px; }

.modal-enter-active, .modal-leave-active { transition: opacity 0.18s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
</style>
