<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="pf-overlay" @click.self="close()">
        <div ref="cardEl" class="pf-card">
          <button class="pf-close" @click="close()" aria-label="סגור">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>

          <div class="pf-layout">
            <!-- ── CONTENT (right pane in RTL) ── -->
            <div class="pf-main">
              <header class="pf-header">
                <span class="pf-kicker" dir="ltr">Nifraim <b>App</b></span>
                <h2 class="pf-title"><StepTitle :title="active.title" split :accent="A.deep" /></h2>
                <p class="pf-sub">{{ SUBS[step] }}</p>
                <div class="pf-progress" role="progressbar" :aria-valuenow="step" aria-valuemin="1" aria-valuemax="3">
                  <button
                    v-for="s in STEPS"
                    :key="s.id"
                    class="pf-progress-seg"
                    :class="{ 'pf-progress-seg--filled': s.id <= step }"
                    :style="s.id <= step ? { background: A.accent } : null"
                    :aria-label="`שלב ${s.id}: ${s.title}`"
                    @click="goStep(s.id)"
                  />
                  <span class="pf-progress-label">שלב {{ step }} מתוך 3</span>
                </div>
              </header>

              <!-- ══════════ STEP 1 · DOWNLOAD ══════════ -->
              <section v-show="step === 1" class="pf-body">
                <div class="pf-os-toggle" role="tablist" aria-label="בחירת סוג טלפון">
                  <button class="pf-os" :class="{ 'pf-os--active': osTab === 'android' }" role="tab" :aria-selected="osTab === 'android'" @click="osTab = 'android'">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 9l1.5-3M19 9l-1.5-3M7 9h10M6 9v7a2 2 0 002 2h8a2 2 0 002-2V9M9 18v2M15 18v2"/></svg>
                    Android
                  </button>
                  <button class="pf-os" :class="{ 'pf-os--active': osTab === 'ios' }" role="tab" :aria-selected="osTab === 'ios'" @click="osTab = 'ios'">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18h2"/></svg>
                    iPhone
                  </button>
                </div>

                <!-- Android: scan → install APK -->
                <div v-if="osTab === 'android'">
                  <div class="pf-qr-card" :style="cardStyle">
                    <div class="pf-qr-frame">
                      <img :src="qrSrc(APK_URL)" alt="QR להורדת האפליקציה" width="150" height="150" />
                    </div>
                    <div class="pf-qr-info">
                      <div class="pf-qr-name">Nifraim App <span v-if="apkVersion" class="pf-qr-ver ltr-number">גרסה {{ apkVersion }}</span></div>
                      <div class="pf-qr-desc">סרקו במצלמה של הטלפון והתקינו.</div>
                      <a class="pf-qr-link" :href="APK_URL" target="_blank" rel="noopener">או הורידו מכאן</a>
                    </div>
                  </div>

                  <p class="pf-upgrade-note">מותקנת גרסה מ-Google Play? הסירו אותה קודם.</p>
                </div>

                <!-- iPhone: no app to install -->
                <div v-else class="pf-ios-note">
                  <div class="pf-ios-badge" :style="{ background: active.soft, color: active.deep }">
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18h2"/></svg>
                  </div>
                  <div>
                    <div class="pf-ios-title">באייפון אין מה להתקין</div>
                    <p class="pf-ios-desc">משתמשים ב-<strong>Shortcuts</strong> שכבר באייפון. המשיכו.</p>
                  </div>
                </div>
              </section>

              <!-- ══════════ STEP 2 · CONNECT ══════════ -->
              <section v-show="step === 2" class="pf-body">
                <!-- Not yet configured: create the secure address -->
                <div v-if="!configured" class="pf-create">
                  <div class="pf-create-glyph" :style="{ background: active.soft, color: active.deep }">
                    <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg>
                  </div>
                  <div class="pf-create-title">ניצור לכם כתובת מאובטחת</div>
                  <p class="pf-create-desc">כתובת אישית ומוצפנת — רק הטלפון שלכם משתמש בה.</p>
                  <button class="pf-btn pf-btn--primary" :style="ctaStyle" :disabled="loading" @click="onRegenerate">
                    {{ loading ? 'רגע…' : 'צור כתובת מאובטחת' }}
                  </button>
                </div>

                <!-- Configured: show URL + per-OS wiring -->
                <div v-else>
                  <div class="pf-url-card" :style="cardStyle">
                    <div class="pf-qr-frame">
                      <img :src="qrSrc(store.phoneForward.url)" alt="QR לכתובת המאובטחת" width="132" height="132" />
                    </div>
                    <div class="pf-url-right">
                      <label class="pf-label">הכתובת המאובטחת שלכם</label>
                      <div class="pf-url-row">
                        <input
                          ref="urlInputRef"
                          class="pf-url-input ltr-number"
                          :value="store.phoneForward.url"
                          readonly
                          @focus="$event.target.select()"
                        />
                        <button class="pf-btn pf-btn--copy" :style="ctaStyle" @click="copyUrl">
                          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
                          {{ copied ? 'הועתק!' : 'העתק' }}
                        </button>
                      </div>
                      <span class="pf-url-hint">סרקו או העתיקו לאפליקציה.</span>
                    </div>
                  </div>

                  <!-- Android wiring -->
                  <ol v-if="osTab === 'android'" class="pf-steps">
                    <li>הדביקו את הכתובת באפליקציה ושמרו.</li>
                    <li>אשרו הרשאת SMS וכבו חיסכון בסוללה.</li>
                    <li><strong>שיחות:</strong> הפעילו "שיחות עם לקוחות" והקלטה בחייגן.</li>
                  </ol>

                  <!-- iPhone: two Shortcuts, folded so the first view stays short -->
                  <details v-if="osTab !== 'android'" class="pf-fold">
                    <summary>קודי אימות</summary>
                    <ol class="pf-steps pf-steps--tight">
                    <li>פתחו את <strong>Shortcuts</strong> ← לשונית <strong>Automation</strong>.</li>
                    <li>הקישו <strong>+</strong> ← <strong>Create Personal Automation</strong> ← בחרו <strong>Message</strong>.</li>
                    <li>ב-<strong>Message contains</strong> כתבו את שם החברה (למשל <code>Migdal</code>).</li>
                    <li>בחרו <strong>Run Immediately</strong> (לא Run After Confirmation) ← Next.</li>
                    <li>הוסיפו פעולה <strong>Get Contents of URL</strong> ← הדביקו את הכתובת שלמעלה.</li>
                    <li>פתחו את החצים: Method = <strong>POST</strong>, Request Body = <strong>JSON</strong>.</li>
                    <li>Add field ← Key = <code>message</code>, Value = <strong>Shortcut Input</strong> ← Done.</li>
                  </ol>
                  </details>

                  <!-- iPhone: recorded calls (iOS 18.1+ saves them in Notes) — one tap via the Share sheet -->
                  <details v-if="osTab !== 'android'" class="pf-fold">
                    <summary>שיחות מוקלטות <span class="pf-fold-note" dir="ltr">iOS 18+</span></summary>
                    <ol class="pf-steps pf-steps--tight">
                      <li>ב-<strong>Shortcuts</strong> הקישו <strong>+</strong> ← קראו לקיצור <strong>שלח לנפרעים</strong>.</li>
                      <li>בהגדרות הקיצור הפעילו <strong>Show in Share Sheet</strong> וסוג קלט <strong>Media / Files</strong>.</li>
                      <li>הוסיפו פעולה <strong>Get Contents of URL</strong> והדביקו: <code class="ltr-number">{{ callUrl }}</code></li>
                      <li>Method = <strong>POST</strong>, Request Body = <strong>Form</strong>.</li>
                      <li>Add field ← <strong>File</strong>: Key = <code>audio</code>, Value = <strong>Shortcut Input</strong>.</li>
                      <li>Add field ← <strong>Text</strong>: Key = <code>source</code>, Value = <code>phone_ios</code>.</li>
                      <li>אחרי שיחה: Notes ← ההקלטה ← שיתוף ← <strong>שלח לנפרעים</strong>.</li>
                    </ol>
                  </details>

                  <button class="pf-linkbtn pf-linkbtn--danger" @click="confirmRegenOpen = true">החלף מפתח אבטחה</button>
                </div>
              </section>

              <!-- ══════════ STEP 3 · TEST & DONE ══════════ -->
              <section v-show="step === 3" class="pf-body">
                <div class="pf-status-line">
                  <span class="pf-pill" :class="configured ? 'pf-pill--ok' : 'pf-pill--off'">
                    <svg v-if="configured" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                    <svg v-else width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/></svg>
                    {{ configured ? 'הכתובת מוגדרת' : 'עדיין לא מוגדר' }}
                  </span>
                  <span v-if="!configured" class="pf-status-note">חזרו לשלב 2 כדי ליצור כתובת מאובטחת.</span>
                </div>

                <div class="pf-test">
                  <label class="pf-label">בדיקה מהירה — בלי הטלפון</label>
                  <div class="pf-test-row">
                    <input v-model="testMessage" class="pf-test-input ltr-number" placeholder="Migdal verification code: 482917" />
                    <button class="pf-btn pf-btn--primary" :style="ctaStyle" :disabled="testing || !configured" @click="onTest">
                      {{ testing ? '…' : 'בדיקה' }}
                    </button>
                  </div>
                  <div v-if="testResult" class="pf-test-result" :class="{ ok: testResult.extracted_otp }">
                    {{ testResult.extracted_otp
                      ? `זוהה קוד ${testResult.extracted_otp} — הודעה כזו תתקבל אצלנו.`
                      : 'לא נמצא קוד בן 4–8 ספרות בהודעה.' }}
                  </div>
                </div>

              </section>

              <!-- ── Footer navigation ── -->
              <div class="pf-nav">
                <button v-if="step > 1" class="pf-btn pf-btn--ghost" @click="back">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6l6 6-6 6"/></svg>
                  חזרה
                </button>
                <span class="pf-nav-spacer" />
                <button v-if="step < 3" class="pf-btn pf-btn--primary" :style="ctaStyle" @click="next">
                  {{ step === 1 ? 'התקנתי — המשך' : 'המשך' }}
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 6l-6 6 6 6"/></svg>
                </button>
                <button v-else class="pf-btn pf-btn--primary" :style="ctaStyle" @click="close()">
                  סיום
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                </button>
              </div>
            </div>

            <!-- ── VISUAL (left pane in RTL): the welcome wizard's Nifraim App picture, entering ── -->
            <div class="pf-visual" :style="{ background: A.soft }">
              <div class="pf-visual-media" :class="{ 'pf-visual-media--in': mediaIn }">
                <!-- one picture per step; the new one zooms in as the old one zooms out -->
                <Transition :name="reducedMotion ? 'pf-fade' : 'pf-zoom'">
                  <video
                    v-if="step === 1 && !reducedMotion" key="v1" :src="phoneVideo" :poster="STEP_PICS[1]"
                    class="pf-visual-img" autoplay muted loop playsinline preload="auto"
                    aria-hidden="true" disablepictureinpicture
                  ></video>
                  <img v-else :key="'p' + step" :src="STEP_PICS[step]" alt="" class="pf-visual-img" />
                </Transition>
              </div>
              <div class="pf-visual-scrim" :style="{ background: `linear-gradient(to top, ${A.soft} 0%, transparent 40%)` }"></div>
              <Transition :name="reducedMotion ? 'pf-fade' : 'pf-num'" mode="out-in">
                <div :key="step" class="pf-visual-num" aria-hidden="true">
                  <span class="pf-visual-num-n ltr-number">0{{ step }}</span>
                  <span class="pf-visual-num-of ltr-number">/03</span>
                </div>
              </Transition>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Regenerate confirmation -->
    <Transition name="modal">
      <div v-if="confirmRegenOpen" class="pf-overlay pf-overlay--confirm" @click.self="confirmRegenOpen = false">
        <div class="pf-confirm">
          <h3>החלפת מפתח האבטחה</h3>
          <p>המפתח הקיים יפסיק לעבוד מיד, ותצטרכו לעדכן את הכתובת החדשה באפליקציה שבטלפון.</p>
          <div class="pf-confirm-actions">
            <button class="pf-btn pf-btn--ghost" @click="confirmRegenOpen = false">ביטול</button>
            <button class="pf-btn pf-btn--danger" :disabled="loading" @click="onRegenerate">החלף עכשיו</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { usePortalAutomationStore } from '../../stores/portalAutomation.js'
import { SETUP_ACCENTS } from '../../composables/useSetupPipeline.js'
import StepTitle from './StepTitle.vue'
import { usePressMorph } from '../../composables/usePressMorph.js'
import phoneVideo from '../../assets/welcome/step-phone.mp4'
import phoneStill from '../../assets/welcome/step-phone.webp'
import connectStill from '../../assets/welcome/app-connect.webp'
import doneStill from '../../assets/welcome/app-done.webp'

const STEP_PICS = { 1: phoneStill, 2: connectStill, 3: doneStill }
import api from '../../api/client.js'

const APK_BASE = 'https://nifraim-production.up.railway.app/api/downloads/android'
// the version rides in the link so each release is a NEW url — phones/browsers never hand back a cached older APK
const apkVersion = ref('')
const APK_URL = computed(() => APK_BASE + (apkVersion.value ? `?v=${apkVersion.value}` : ''))

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])
// iPhone-style: grows out of the pressed button, folds back into it
const cardEl = ref(null)
const { closeWith } = usePressMorph(() => props.open, cardEl)
function close() { closeWith(() => emit('close')) }

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
// iPhone Share-sheet shortcut posts recorded calls here (api/portal_automation.py phone_forward_call)
const callUrl = computed(() => (store.phoneForward?.url || '').replace(/\/+$/, '') + '/call')

// ── Wizard steps: ONE colour throughout — the app's own sky (same as the welcome wizard's phone step) ──
const A = SETUP_ACCENTS.phone
const STEPS = [
  { id: 1, title: 'התקנת האפליקציה' },
  { id: 2, title: 'חיבור מאובטח' },
  { id: 3, title: 'בדיקה וסיום' },
]
const SUBS = {
  1: 'קודי אימות ושיחות מוקלטות — מהטלפון אלינו, לבד.',
  2: 'מחברים את האפליקציה לחשבון שלכם.',
  3: 'בדיקה קצרה — וזהו.',
}
const step = ref(1)
const active = computed(() => ({ ...STEPS[step.value - 1], ...A }))
// the picture's entrance: it rises and settles a beat after the card opens
const mediaIn = ref(false)
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

function goStep(n) { step.value = Math.min(3, Math.max(1, n)) }
function next() { goStep(step.value + 1) }
function back() { goStep(step.value - 1) }

// solid buttons take the DEEP sky: white on the light accent fails 4.5:1
const ctaStyle = computed(() => ({
  background: A.deep,
  boxShadow: `0 4px 12px ${A.deep}44`,
}))
const cardStyle = computed(() => ({
  background: active.value.tint,
  borderColor: active.value.accent + '33',
}))

const qrSrc = (data) =>
  `https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=${encodeURIComponent(data)}`

watch(
  () => props.open,
  async (v) => {
    if (v) {
      step.value = 1
      mediaIn.value = false
      requestAnimationFrame(() => requestAnimationFrame(() => { mediaIn.value = true }))
      loading.value = true
      api.get('/downloads/android/version').then((r) => { apkVersion.value = r.data?.version || '' }).catch(() => {})
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
  z-index: 1300;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(24, 24, 24, 0.5);
  backdrop-filter: blur(5px);
}

.pf-card {
  position: relative;
  width: 100%;
  max-width: 960px;
  max-height: calc(100vh - 40px);
  overflow: hidden;
  background: #fff;
  border-radius: var(--radius-xl, 24px);
  box-shadow: 0 26px 70px rgba(24, 24, 24, 0.28);
  font-family: 'Heebo', sans-serif;
}

.pf-close {
  position: absolute;
  top: 14px;
  left: 14px;
  z-index: 4;
  display: inline-flex;
  padding: 7px;
  border: none;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 1px 4px rgba(24, 24, 24, 0.12);
  color: var(--text-secondary, #3E3E3C);
  cursor: pointer;
  transition: background 0.15s;
}
.pf-close:hover { background: #fff; }

/* ── Two panes ── */
.pf-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(0, 0.88fr);
  min-height: 560px;
  max-height: calc(100vh - 40px);
}
.pf-main {
  display: flex;
  flex-direction: column;
  padding: 30px 34px 22px 28px;
  overflow-y: auto;
}

/* ── Header ── */
.pf-header { margin-bottom: 16px; }
.pf-kicker {
  display: inline-block;
  font-family: 'Rubik', 'Heebo', sans-serif;
  font-size: 12.5px;
  font-weight: 800;
  color: var(--text-primary, #181818);
  background: #EAF3F9; /* = SETUP_ACCENTS.phone.soft */
  border-radius: 999px;
  padding: 4px 12px;
  margin-bottom: 10px;
  unicode-bidi: isolate;
}
.pf-kicker b { color: #35719A; } /* = SETUP_ACCENTS.phone.deep */
.pf-title { margin: 0 0 4px; font-size: 24px; font-weight: 800; color: var(--text, #181818); }
.pf-sub { margin: 0; font-size: 14px; color: var(--text-tertiary, #706E6B); line-height: 1.5; }

.pf-progress { display: flex; align-items: center; gap: 6px; margin-top: 14px; }
.pf-progress-seg {
  height: 7px;
  width: 46px;
  padding: 0;
  border: none;
  border-radius: 4px;
  background: #F0EDE8;
  cursor: pointer;
  transition: background 0.4s ease, transform 0.15s ease;
}
.pf-progress-seg:hover { transform: translateY(-1px); }
.pf-progress-label { font-size: 12.5px; font-weight: 700; color: var(--text-tertiary, #706E6B); margin-right: 6px; }

/* ── Step body ── */
.pf-body { flex: 1; }

/* OS toggle */
.pf-os-toggle {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  margin-bottom: 18px;
  background: #F4F2EF;
  border-radius: 12px;
}
.pf-os {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: 9px;
  background: transparent;
  font-family: inherit;
  font-size: 13.5px;
  font-weight: 600;
  color: var(--text-secondary, #3E3E3C);
  cursor: pointer;
  transition: background 0.18s, color 0.18s, box-shadow 0.18s;
}
.pf-os--active {
  background: #fff;
  color: var(--text, #181818);
  box-shadow: 0 2px 6px rgba(24, 24, 24, 0.1);
}

/* QR / URL cards */
.pf-qr-card,
.pf-url-card {
  display: flex;
  gap: 18px;
  align-items: center;
  padding: 18px;
  border: 1.5px solid;
  border-radius: var(--radius-lg, 16px);
  margin-bottom: 16px;
}
.pf-qr-frame {
  flex-shrink: 0;
  padding: 8px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(24, 24, 24, 0.08);
  line-height: 0;
}
.pf-qr-info, .pf-url-right { min-width: 0; flex: 1; }
.pf-qr-name { font-size: 16px; font-weight: 800; color: var(--text, #181818); margin-bottom: 4px; }
.pf-qr-desc { font-size: 13px; color: var(--text-tertiary, #706E6B); line-height: 1.5; margin-bottom: 8px; }
.pf-qr-link { font-size: 13px; font-weight: 700; color: #35719A; text-decoration: none; }
.pf-qr-link:hover { text-decoration: underline; }

.pf-label { display: block; font-size: 12.5px; font-weight: 700; color: var(--text-secondary, #3E3E3C); margin-bottom: 7px; }
.pf-url-row { display: flex; gap: 8px; }
.pf-url-input {
  flex: 1; min-width: 0;
  padding: 10px 12px;
  border: 1.5px solid #E3E0DB;
  border-radius: 10px;
  background: #fff;
  font-size: 12.5px;
  color: var(--text-secondary, #3E3E3C);
  direction: ltr;
  text-align: left;
}
.pf-url-hint { display: block; margin-top: 8px; font-size: 12px; color: var(--text-tertiary, #706E6B); }

/* Steps ordered list */
.pf-steps {
  list-style: none;
  counter-reset: pf;
  margin: 4px 0 16px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.pf-steps--tight { gap: 7px; }
.pf-qr-ver { margin-inline-start: 6px; padding: 1px 8px; border-radius: 999px; font-size: 12px; font-weight: 700; color: #35719A; background: #EAF3F9; }
.pf-upgrade-note { margin: 10px 0 0; font-size: 12.5px; line-height: 1.55; color: var(--text-tertiary, #706E6B); }
/* iPhone instructions, folded */
.pf-fold { margin-top: 10px; border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 12px; padding: 0 14px; background: #fff; }
.pf-fold + .pf-fold { margin-top: 8px; }
.pf-fold summary {
  list-style: none; cursor: pointer; padding: 12px 0; font-size: 14px; font-weight: 700; color: var(--text-primary, #181818);
  display: flex; align-items: center; gap: 8px;
}
.pf-fold summary::-webkit-details-marker { display: none; }
.pf-fold summary::after { content: ''; margin-inline-start: auto; width: 8px; height: 8px; border: solid #35719A; border-width: 0 2px 2px 0; transform: rotate(45deg); transition: transform 0.2s ease; }
.pf-fold[open] summary::after { transform: rotate(-135deg); }
.pf-fold[open] { padding-bottom: 10px; }
.pf-fold-note { font-size: 11.5px; font-weight: 600; color: var(--text-tertiary, #706E6B); }
.pf-fold code.ltr-number { direction: ltr; unicode-bidi: embed; word-break: break-all; }
.pf-steps li {
  counter-increment: pf;
  position: relative;
  padding-right: 34px;
  font-size: 13.5px;
  color: var(--text-secondary, #3E3E3C);
  line-height: 1.5;
}
.pf-steps li::before {
  content: counter(pf);
  position: absolute;
  right: 0;
  top: 0;
  width: 24px;
  height: 24px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  background: #F4F2EF;
  font-size: 12px;
  font-weight: 800;
  color: var(--text-secondary, #3E3E3C);
}
.pf-steps li strong { color: var(--text, #181818); }
.pf-steps code {
  background: #F4F2EF; border-radius: 5px; padding: 1px 6px;
  font-size: 12px; direction: ltr; display: inline-block;
}

/* iPhone no-install note */
.pf-ios-note {
  display: flex; gap: 16px; align-items: flex-start;
  padding: 20px; background: #FAFAF9;
  border: 1.5px solid #ECE9E4; border-radius: var(--radius-lg, 16px);
}
.pf-ios-badge { flex-shrink: 0; display: grid; place-items: center; width: 54px; height: 54px; border-radius: 14px; }
.pf-ios-title { font-size: 16px; font-weight: 800; color: var(--text, #181818); margin-bottom: 5px; }
.pf-ios-desc { margin: 0; font-size: 13.5px; color: var(--text-tertiary, #706E6B); line-height: 1.55; }

/* Create-address block */
.pf-create { text-align: center; padding: 22px 12px; }
.pf-create-glyph { display: inline-grid; place-items: center; width: 66px; height: 66px; border-radius: 18px; margin-bottom: 14px; }
.pf-create-title { font-size: 18px; font-weight: 800; color: var(--text, #181818); margin-bottom: 6px; }
.pf-create-desc { font-size: 13.5px; color: var(--text-tertiary, #706E6B); line-height: 1.55; max-width: 380px; margin: 0 auto 18px; }

/* Status / test (step 3) */
.pf-status-line { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; flex-wrap: wrap; }
.pf-pill {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12.5px; font-weight: 700; border-radius: 999px; padding: 5px 12px;
}
.pf-pill--ok { color: #1B7F5E; background: #E4F5F0; }
.pf-pill--off { color: #8A6D3B; background: #FBF3E2; }
.pf-status-note { font-size: 12.5px; color: var(--text-tertiary, #706E6B); }

.pf-test { margin-bottom: 18px; }
.pf-test-row { display: flex; gap: 8px; }
.pf-test-input {
  flex: 1; min-width: 0; padding: 10px 12px;
  border: 1.5px solid #E3E0DB; border-radius: 10px; font-size: 13px;
  direction: ltr; text-align: left;
}
.pf-test-result {
  margin-top: 10px; padding: 9px 12px; border-radius: 10px;
  font-size: 13px; font-weight: 600; background: #FBF3E2; color: #8A6D3B;
}
.pf-test-result.ok { background: #E4F5F0; color: #1B7F5E; }

/* ── Footer nav ── */
.pf-nav {
  display: flex; align-items: center; gap: 10px;
  margin-top: 18px; padding-top: 16px;
  border-top: 1px solid #F0EDE8;
}
.pf-nav-spacer { flex: 1; }

/* Buttons */
.pf-btn {
  display: inline-flex; align-items: center; gap: 7px;
  padding: 10px 18px; border: none; border-radius: 11px;
  font-family: inherit; font-size: 14px; font-weight: 700; cursor: pointer;
  transition: transform 0.12s ease, box-shadow 0.15s ease, opacity 0.15s;
}
.pf-btn:hover:not(:disabled) { transform: translateY(-1px); }
.pf-btn:disabled { opacity: 0.5; cursor: default; }
.pf-btn--primary { color: #fff; }
.pf-btn--copy { color: #fff; padding: 10px 14px; }
.pf-btn--ghost {
  background: #F4F2EF; color: var(--text-secondary, #3E3E3C);
}
.pf-btn--ghost:hover:not(:disabled) { background: #ECE9E4; }
.pf-btn--danger { background: #C0392B; color: #fff; box-shadow: 0 4px 12px rgba(192, 57, 43, 0.3); }
.pf-linkbtn {
  border: none; background: none; padding: 6px 2px; margin-top: 4px;
  font-family: inherit; font-size: 12.5px; font-weight: 600;
  color: var(--text-tertiary, #706E6B); cursor: pointer; text-decoration: underline;
}
.pf-linkbtn:hover:not(:disabled) { color: var(--text, #181818); }
.pf-linkbtn--danger { color: #C0392B; }

/* ── Visual pane: the welcome wizard's phone picture ── */
.pf-visual {
  position: relative;
  overflow: hidden;
  border-right: 1px solid rgba(24, 24, 24, 0.06);
}
.pf-visual-media {
  position: absolute; inset: 0;
  opacity: 0; transform: scale(1.08) translateY(18px);
  transition: opacity 0.9s ease, transform 1.4s cubic-bezier(0.16, 1, 0.3, 1);
}
.pf-visual-media--in { opacity: 1; transform: none; }
.pf-visual-img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.pf-visual-scrim { position: absolute; inset: 0; pointer-events: none; }
.pf-visual-num {
  position: absolute; top: 28px; right: 30px; z-index: 2;
  display: flex; align-items: baseline; gap: 6px; direction: ltr; pointer-events: none;
}
.pf-visual-num-n {
  font-family: 'Heebo', sans-serif; font-size: clamp(80px, 9vw, 130px); font-weight: 900; line-height: 0.9;
  color: rgba(255, 255, 255, 0.14); -webkit-text-stroke: 2px rgba(255, 255, 255, 0.92);
  text-shadow: 0 6px 30px rgba(24, 24, 24, 0.12); letter-spacing: -0.04em;
}
.pf-visual-num-of { font-size: 20px; font-weight: 800; color: rgba(255, 255, 255, 0.92); text-shadow: 0 2px 10px rgba(24, 24, 24, 0.18); }
.pf-zoom-enter-active, .pf-zoom-leave-active { transition: opacity 0.7s ease, transform 1.1s cubic-bezier(0.16, 1, 0.3, 1); }
.pf-zoom-enter-from { opacity: 0; transform: scale(1.14); }
.pf-zoom-leave-to { opacity: 0; transform: scale(0.92); }
.pf-num-enter-active, .pf-num-leave-active { transition: opacity 0.35s ease, transform 0.45s cubic-bezier(0.16, 1, 0.3, 1); }
.pf-num-enter-from { opacity: 0; transform: translateY(22px); }
.pf-num-leave-to { opacity: 0; transform: translateY(-14px); }
.pf-fade-enter-active, .pf-fade-leave-active { transition: opacity 0.2s ease; }
.pf-fade-enter-from, .pf-fade-leave-to { opacity: 0; }
@media (prefers-reduced-motion: reduce) { .pf-visual-media { transition: none; opacity: 1; transform: none; } }

/* ── Confirm dialog ── */
.pf-overlay--confirm { z-index: 1310; }
.pf-confirm {
  width: 100%; max-width: 400px; background: #fff; border-radius: 18px;
  padding: 26px; box-shadow: 0 20px 50px rgba(24, 24, 24, 0.25); text-align: center;
}
.pf-confirm h3 { margin: 0 0 8px; font-size: 18px; font-weight: 800; color: var(--text, #181818); }
.pf-confirm p { margin: 0 0 20px; font-size: 13.5px; color: var(--text-tertiary, #706E6B); line-height: 1.55; }
.pf-confirm-actions { display: flex; gap: 10px; justify-content: center; }

/* ── Modal transition ── */
.modal-enter-active, .modal-leave-active { transition: opacity 0.25s ease; }
.modal-enter-active .pf-card, .modal-leave-active .pf-card { transition: transform 0.28s cubic-bezier(0.34, 1.4, 0.64, 1), opacity 0.28s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .pf-card, .modal-leave-to .pf-card { transform: scale(0.94) translateY(12px); opacity: 0; }

/* ── Responsive: collapse the visual pane ── */
@media (max-width: 820px) {
  .pf-layout { grid-template-columns: 1fr; min-height: 0; }
  .pf-visual { display: none; }
  .pf-main { padding: 26px 22px 20px; }
}
</style>
