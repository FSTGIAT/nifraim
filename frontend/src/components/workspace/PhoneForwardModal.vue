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

          <div class="pf-layout">
            <!-- ── CONTENT (right pane in RTL) ── -->
            <div class="pf-main">
              <header class="pf-header">
                <span class="pf-kicker">העברת SMS אוטומטית</span>
                <h2 class="pf-title">{{ active.title }}</h2>
                <p class="pf-sub">{{ SUBS[step] }}</p>
                <div class="pf-progress" role="progressbar" :aria-valuenow="step" aria-valuemin="1" aria-valuemax="3">
                  <button
                    v-for="s in STEPS"
                    :key="s.id"
                    class="pf-progress-seg"
                    :class="{ 'pf-progress-seg--filled': s.id <= step }"
                    :style="s.id <= step ? { background: s.accent } : null"
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
                      <div class="pf-qr-name">אפליקציית Nifraim</div>
                      <div class="pf-qr-desc">פִתחו את המצלמה בטלפון, סרקו את הקוד, והורידו את האפליקציה.</div>
                      <a class="pf-qr-link ltr-number" :href="APK_URL" target="_blank" rel="noopener">{{ APK_URL }}</a>
                    </div>
                  </div>

                  <ol class="pf-steps">
                    <li><strong>סרקו והורידו</strong> — פִתחו את המצלמה, סרקו את הקוד, והורידו את קובץ ההתקנה.</li>
                    <li><strong>התקינו</strong> — הפעילו את הקובץ. אם Windows/אנדרואיד מזהיר על "מקור לא מוכר" — אשרו והמשיכו.</li>
                    <li><strong>פתחו את האפליקציה</strong> — ואז המשיכו לשלב הבא כדי לחבר אותה.</li>
                  </ol>

                  <details class="pf-fallback">
                    <summary>התקנה מ-Google Play (כשהאפליקציה תפורסם)</summary>
                    <div class="pf-qr-card pf-qr-card--muted">
                      <div class="pf-qr-frame"><img :src="qrSrc(playInstallUrl)" alt="QR ל-Google Play" width="130" height="130" /></div>
                      <div class="pf-qr-info">
                        <div class="pf-qr-name">Nifraim ב-Google Play</div>
                        <div class="pf-qr-auto">
                          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                          הכתובת המאובטחת מוגדרת אוטומטית בהתקנה
                        </div>
                        <div class="pf-qr-desc">זמין רק לאחר פרסום האפליקציה. אם מוצג "הפריט לא נמצא" — השתמשו בהתקנה הישירה למעלה.</div>
                      </div>
                    </div>
                  </details>
                </div>

                <!-- iPhone: no app to install -->
                <div v-else class="pf-ios-note">
                  <div class="pf-ios-badge" :style="{ background: active.soft, color: active.deep }">
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="7" y="2" width="10" height="20" rx="2.5"/><path d="M11 18h2"/></svg>
                  </div>
                  <div>
                    <div class="pf-ios-title">באייפון אין מה להתקין</div>
                    <p class="pf-ios-desc">נשתמש באפליקציית <strong>Shortcuts</strong> המובנית של אפל — כבר מותקנת אצלכם. המשיכו לשלב הבא ונגדיר אותה יחד.</p>
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
                  <p class="pf-create-desc">כתובת אישית ומוצפנת שדרכה הטלפון שולח אלינו את קודי האימות. אף אחד אחר לא יכול להשתמש בה.</p>
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
                      <span class="pf-url-hint">סרקו עם הטלפון או העתיקו — נדביק אותה בשלב הבא.</span>
                    </div>
                  </div>

                  <!-- Android wiring -->
                  <ol v-if="osTab === 'android'" class="pf-steps">
                    <li><strong>הדביקו את הכתובת</strong> — פתחו את האפליקציה, הדביקו את הכתובת שהעתקתם, ושמרו.</li>
                    <li><strong>אשרו הרשאות</strong> — אשרו הרשאת קריאת SMS וכבו אופטימיזציית סוללה (כפתורים באפליקציה).</li>
                    <li><strong>זהו</strong> — כל SMS עם קוד מהפורטל יועבר אלינו אוטומטית, מיד.</li>
                  </ol>

                  <!-- iPhone Shortcuts wiring -->
                  <ol v-else class="pf-steps pf-steps--tight">
                    <li>פתחו את <strong>Shortcuts</strong> ← לשונית <strong>Automation</strong>.</li>
                    <li>הקישו <strong>+</strong> ← <strong>Create Personal Automation</strong> ← בחרו <strong>Message</strong>.</li>
                    <li>ב-<strong>Message contains</strong> כתבו את שם החברה (למשל <code>Migdal</code>).</li>
                    <li>בחרו <strong>Run Immediately</strong> (לא Run After Confirmation) ← Next.</li>
                    <li>הוסיפו פעולה <strong>Get Contents of URL</strong> ← הדביקו את הכתובת שלמעלה.</li>
                    <li>פתחו את החצים: Method = <strong>POST</strong>, Request Body = <strong>JSON</strong>.</li>
                    <li>Add field ← Key = <code>message</code>, Value = <strong>Shortcut Input</strong> ← Done.</li>
                  </ol>

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

                <!-- Advanced: company SMS templates (progressive disclosure) -->
                <button class="pf-tpl-toggle" @click="showTemplates = !showTemplates">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" :style="{ transform: showTemplates ? 'rotate(90deg)' : 'none', transition: 'transform .15s' }"><polyline points="9 18 15 12 9 6"/></svg>
                  תבניות זיהוי SMS של חברות
                  <span class="pf-tpl-count">{{ templates.length }}</span>
                </button>

                <div v-if="showTemplates" class="pf-tpl-body">
                  <p class="pf-tpl-intro">
                    כך האפליקציה יודעת אילו הודעות להעביר. הדביקו הודעת SMS אמיתית של חברה — נבנה ממנה תבנית.
                    הודעה עם קוד שלא תואמת אף תבנית <strong>תועבר בכל זאת</strong> (ברירת מחדל בטוחה).
                    תבנית "חסימה" עוצרת הודעה אישית עם קוד מלהישלח.
                  </p>

                  <div class="pf-tpl-form">
                    <div class="pf-tpl-form-row">
                      <input v-model="tplForm.company_name" class="pf-tpl-input" placeholder="שם חברה (למשל מגדל)" />
                      <label class="pf-tpl-block"><input type="checkbox" v-model="tplForm.is_block" /> חסימה (אל תעביר)</label>
                    </div>
                    <input v-model="tplForm.example" class="pf-tpl-input ltr-number" placeholder="הדביקו הודעת SMS אמיתית, למשל: קוד האימות שלך במגדל 482917" @input="onExampleInput" />
                    <input v-model="tplForm.pattern" class="pf-tpl-input pf-tpl-pattern ltr-number" placeholder="תבנית (regex) — נוצרת אוטומטית, ניתן לערוך" />
                    <div class="pf-tpl-form-actions">
                      <button class="pf-btn pf-btn--primary" :style="ctaStyle" :disabled="tplBusy || !tplForm.company_name || !tplForm.pattern" @click="saveTemplate">
                        {{ editingTplId ? 'עדכן' : 'הוסף תבנית' }}
                      </button>
                      <button v-if="editingTplId" class="pf-linkbtn" @click="resetTplForm">ביטול</button>
                      <button v-if="!templates.length" class="pf-linkbtn" :disabled="tplBusy" @click="seedTemplates">טען תבניות ברירת מחדל</button>
                    </div>
                  </div>

                  <div class="pf-tpl-testbox">
                    <input v-model="tplTest" class="pf-tpl-input ltr-number" placeholder="בדקו הודעה: יישלח / לא יישלח" />
                    <span v-if="tplTest" class="pf-tpl-verdict" :class="{ ok: tplVerdict.forward, no: !tplVerdict.forward }">
                      {{ tplVerdict.forward ? 'יישלח' : 'לא יישלח' }} · {{ tplVerdict.reason }}
                    </span>
                  </div>

                  <ul class="pf-tpl-list">
                    <li v-for="t in templates" :key="t.id" class="pf-tpl-item">
                      <span class="pf-tpl-badge" :class="t.is_block ? 'block' : 'allow'">{{ t.is_block ? 'חסימה' : 'העברה' }}</span>
                      <div class="pf-tpl-item-main">
                        <div class="pf-tpl-item-name">{{ t.company_name }}</div>
                        <div class="pf-tpl-item-pattern ltr-number">{{ t.pattern }}</div>
                      </div>
                      <button class="pf-tpl-icon" title="ערוך" @click="editTemplate(t)">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                      </button>
                      <button class="pf-tpl-icon pf-tpl-icon--danger" title="מחק" @click="deleteTemplate(t)">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg>
                      </button>
                    </li>
                    <li v-if="!templates.length" class="pf-tpl-empty">אין תבניות עדיין — הוסיפו אחת או טענו ברירת מחדל.</li>
                  </ul>
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
                <button v-else class="pf-btn pf-btn--primary" :style="ctaStyle" @click="$emit('close')">
                  סיום
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                </button>
              </div>
            </div>

            <!-- ── VISUAL (left pane in RTL) ── -->
            <div class="pf-visual" :style="{ background: visualBg }">
              <span v-for="n in 6" :key="n" class="pf-orb" :style="orbStyle(n)" />
              <Transition :name="reducedMotion ? 'pf-fade' : 'pf-pop'" mode="out-in">
                <div :key="step" class="pf-visual-inner">
                  <!-- Step 1: download -->
                  <svg v-if="step === 1" class="pf-glyph" viewBox="0 0 120 120" fill="none">
                    <rect x="38" y="14" width="44" height="80" rx="9" :stroke="active.accent" stroke-width="3.5"/>
                    <line x1="54" y1="24" x2="66" y2="24" :stroke="active.accent" stroke-width="3.5" stroke-linecap="round"/>
                    <path d="M60 44v26" :stroke="active.accent" stroke-width="4" stroke-linecap="round"/>
                    <path d="M50 60l10 10 10-10" :stroke="active.accent" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
                    <circle cx="60" cy="86" r="3" :fill="active.accent"/>
                  </svg>
                  <!-- Step 2: secure connect -->
                  <svg v-else-if="step === 2" class="pf-glyph" viewBox="0 0 120 120" fill="none">
                    <path d="M60 16l30 11v22c0 20-13 34-30 41-17-7-30-21-30-41V27l30-11z" :stroke="active.accent" stroke-width="3.5" stroke-linejoin="round"/>
                    <rect x="48" y="54" width="24" height="18" rx="3.5" :stroke="active.accent" stroke-width="3.5"/>
                    <path d="M53 54v-5a7 7 0 0114 0v5" :stroke="active.accent" stroke-width="3.5"/>
                    <circle cx="60" cy="63" r="2.6" :fill="active.accent"/>
                  </svg>
                  <!-- Step 3: done -->
                  <svg v-else class="pf-glyph" viewBox="0 0 120 120" fill="none">
                    <circle cx="60" cy="60" r="34" :stroke="active.accent" stroke-width="3.5"/>
                    <path d="M45 61l11 11 20-23" :stroke="active.accent" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
                    <circle cx="60" cy="60" r="46" :stroke="active.accent" stroke-width="1.5" stroke-dasharray="4 7" opacity="0.5"/>
                  </svg>
                  <span class="pf-visual-chip" :style="{ color: active.deep, borderColor: active.accent + '55' }">{{ active.title }}</span>
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

// ── Wizard steps (colored like the welcome wizard: install→connect→done) ──
const STEPS = [
  { id: 1, title: 'התקנת האפליקציה', accent: '#E8930C', deep: '#9A5B00', soft: '#FDF1DC', tint: '#FFFAF1' },
  { id: 2, title: 'חיבור מאובטח',    accent: '#4E9DD0', deep: '#2C6E9E', soft: '#E7F2FA', tint: '#F5FAFD' },
  { id: 3, title: 'בדיקה וסיום',      accent: '#1FA88C', deep: '#0E7A64', soft: '#E4F5F0', tint: '#F3FBF8' },
]
const SUBS = {
  1: 'התקנה חד-פעמית של האפליקציה שמעבירה את קודי ה-SMS אלינו.',
  2: 'מחברים את האפליקציה לכתובת מאובטחת — ומשם הכול אוטומטי.',
  3: 'בודקים שהכול עובד — ומכאן ההורדות רצות לבד.',
}
const step = ref(1)
const active = computed(() => STEPS[step.value - 1])
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

function goStep(n) { step.value = Math.min(3, Math.max(1, n)) }
function next() { goStep(step.value + 1) }
function back() { goStep(step.value - 1) }

const ctaStyle = computed(() => ({
  background: active.value.accent,
  boxShadow: `0 4px 12px ${active.value.accent}55`,
}))
const cardStyle = computed(() => ({
  background: active.value.tint,
  borderColor: active.value.accent + '33',
}))
const visualBg = computed(() => `linear-gradient(165deg, ${active.value.tint} 0%, ${active.value.soft} 100%)`)
function orbStyle(n) {
  const a = active.value.accent
  const sizes = [120, 70, 90, 54, 100, 64]
  const pos = [[8, 12], [72, 20], [20, 74], [80, 66], [46, 40], [60, 88]]
  return {
    width: `${sizes[n - 1]}px`,
    height: `${sizes[n - 1]}px`,
    left: `${pos[n - 1][0]}%`,
    top: `${pos[n - 1][1]}%`,
    background: a,
    opacity: 0.08 + (n % 3) * 0.03,
    animationDelay: `${n * 0.4}s`,
  }
}

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
      step.value = 1
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
    if (configured.value) loadTemplates()
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
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--primary-deep, #E65100);
  background: var(--primary-light, #FFF3E0);
  border-radius: 999px;
  padding: 4px 12px;
  margin-bottom: 10px;
}
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
.pf-qr-card--muted { background: #FAFAF9 !important; border-color: #ECE9E4 !important; }
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
.pf-qr-link { font-size: 11.5px; color: var(--primary, #F57C00); word-break: break-all; text-decoration: none; }
.pf-qr-link:hover { text-decoration: underline; }
.pf-qr-auto {
  display: inline-flex; align-items: center; gap: 5px;
  font-size: 12px; font-weight: 700; color: #2E844A;
  background: #EAF5EE; border-radius: 999px; padding: 3px 10px; margin-bottom: 6px;
}

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
.pf-steps code, .pf-tpl-body code {
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

/* Fallback details */
.pf-fallback { margin-top: 4px; }
.pf-fallback summary {
  font-size: 12.5px; font-weight: 600; color: var(--text-tertiary, #706E6B);
  cursor: pointer; padding: 6px 0; list-style: none;
}
.pf-fallback summary::-webkit-details-marker { display: none; }
.pf-fallback summary::before { content: '＋ '; color: var(--primary, #F57C00); }
.pf-fallback[open] summary::before { content: '－ '; }

/* ── Visual pane ── */
.pf-visual {
  position: relative;
  overflow: hidden;
  display: grid;
  place-items: center;
  border-right: 1px solid rgba(24, 24, 24, 0.06);
  transition: background 0.4s ease;
}
.pf-orb {
  position: absolute;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  filter: blur(2px);
  animation: pfFloat 7s ease-in-out infinite;
}
@keyframes pfFloat {
  0%, 100% { transform: translate(-50%, -50%); }
  50% { transform: translate(-50%, calc(-50% - 14px)); }
}
.pf-visual-inner {
  position: relative; z-index: 1;
  display: flex; flex-direction: column; align-items: center; gap: 20px;
}
.pf-glyph { width: 148px; height: 148px; }
.pf-glyph { animation: pfBob 5s ease-in-out infinite; }
@keyframes pfBob { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-8px); } }
.pf-visual-chip {
  font-size: 13px; font-weight: 700;
  background: rgba(255, 255, 255, 0.75);
  border: 1.5px solid; border-radius: 999px; padding: 5px 16px;
  backdrop-filter: blur(4px);
}

.pf-pop-enter-active, .pf-pop-leave-active { transition: opacity 0.32s ease, transform 0.32s cubic-bezier(0.34, 1.56, 0.64, 1); }
.pf-pop-enter-from { opacity: 0; transform: scale(0.85) translateY(10px); }
.pf-pop-leave-to { opacity: 0; transform: scale(0.9) translateY(-6px); }
.pf-fade-enter-active, .pf-fade-leave-active { transition: opacity 0.2s ease; }
.pf-fade-enter-from, .pf-fade-leave-to { opacity: 0; }

/* ── Templates manager ── */
.pf-tpl-toggle {
  display: flex; align-items: center; gap: 8px; width: 100%;
  border: none; background: none; padding: 10px 0; cursor: pointer;
  font-family: inherit; font-size: 13.5px; font-weight: 700; color: var(--text-secondary, #3E3E3C);
  border-top: 1px solid #F0EDE8;
}
.pf-tpl-count {
  margin-right: auto; font-size: 11.5px; font-weight: 700; color: var(--text-tertiary, #706E6B);
  background: #F4F2EF; border-radius: 999px; padding: 2px 9px;
}
.pf-tpl-body { padding-top: 4px; }
.pf-tpl-intro { font-size: 12.5px; color: var(--text-tertiary, #706E6B); line-height: 1.55; margin: 0 0 14px; }
.pf-tpl-form { display: flex; flex-direction: column; gap: 8px; margin-bottom: 12px; }
.pf-tpl-form-row { display: flex; gap: 8px; align-items: center; }
.pf-tpl-input {
  width: 100%; padding: 9px 11px; border: 1.5px solid #E3E0DB; border-radius: 9px;
  font-family: inherit; font-size: 13px;
}
.pf-tpl-pattern { font-size: 12px; color: var(--text-tertiary, #706E6B); }
.pf-tpl-block { display: inline-flex; align-items: center; gap: 5px; font-size: 12.5px; color: var(--text-secondary, #3E3E3C); white-space: nowrap; }
.pf-tpl-form-actions { display: flex; gap: 10px; align-items: center; }
.pf-tpl-testbox { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.pf-tpl-verdict { font-size: 12px; font-weight: 700; white-space: nowrap; }
.pf-tpl-verdict.ok { color: #1B7F5E; }
.pf-tpl-verdict.no { color: #C0392B; }
.pf-tpl-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 7px; }
.pf-tpl-item {
  display: flex; align-items: center; gap: 10px;
  padding: 9px 12px; background: #FAFAF9; border: 1px solid #F0EDE8; border-radius: 11px;
}
.pf-tpl-badge { flex-shrink: 0; font-size: 11px; font-weight: 700; border-radius: 999px; padding: 3px 9px; }
.pf-tpl-badge.allow { color: #1B7F5E; background: #E4F5F0; }
.pf-tpl-badge.block { color: #C0392B; background: #FBEAE7; }
.pf-tpl-item-main { flex: 1; min-width: 0; }
.pf-tpl-item-name { font-size: 13px; font-weight: 700; color: var(--text, #181818); }
.pf-tpl-item-pattern { font-size: 11px; color: var(--text-tertiary, #706E6B); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; direction: ltr; }
.pf-tpl-icon {
  flex-shrink: 0; display: inline-flex; padding: 6px; border: none; border-radius: 8px;
  background: transparent; color: var(--text-tertiary, #706E6B); cursor: pointer; transition: background 0.15s, color 0.15s;
}
.pf-tpl-icon:hover { background: #F0EDE8; color: var(--text, #181818); }
.pf-tpl-icon--danger:hover { background: #FBEAE7; color: #C0392B; }
.pf-tpl-empty { font-size: 12.5px; color: var(--text-tertiary, #706E6B); text-align: center; padding: 12px; }

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
