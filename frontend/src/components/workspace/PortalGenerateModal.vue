<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="show" class="modal-overlay" @click.self="requestClose" @keydown.esc="requestClose">
        <div class="modal-card" role="dialog" aria-modal="true" aria-labelledby="pgw-title">
          <!-- Form first in the DOM so it lands on the RIGHT under `direction:
               rtl`, with the picture (+ live preview) on the left. -->
          <div class="pane pane--form">
            <div class="modal-header">
              <div class="modal-heading">
                <h3 id="pgw-title">{{ isEdit ? 'מה הלקוח רואה בפורטל' : 'פורטל חדש ללקוח' }}</h3>
                <p class="modal-sub">
                  {{ isEdit ? editLink.customer_name : 'שלושה צעדים קצרים — והלקוח מקבל תיק אישי, מאחורי סיסמה.' }}
                </p>
              </div>
              <button class="close-btn" type="button" @click="requestClose" aria-label="סגור">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>

            <!-- Step rail -->
            <ol v-if="step <= 3" class="steps" aria-label="שלבי יצירת הפורטל">
              <li
                v-for="s in visibleSteps"
                :key="s.n"
                class="step"
                :class="{ 'step--on': step === s.n, 'step--done': step > s.n }"
                :aria-current="step === s.n ? 'step' : undefined"
              >
                <button type="button" class="step-btn" :disabled="s.n > maxReached" @click="goTo(s.n)">
                  <span class="step-n ltr-number">{{ s.n }}</span>
                  <span class="step-text">
                    <span class="step-title">{{ s.title }}</span>
                    <span class="step-desc">{{ s.desc }}</span>
                  </span>
                </button>
              </li>
            </ol>

            <div class="step-body">
              <!-- ── 1. למי פותחים ─────────────────────────────── -->
              <section v-if="step === 1" class="step-panel" aria-labelledby="pgw-s1" @input="dirty = true">
                <!-- Narrow screens hide the side picture — bring it in as a banner -->
                <div class="welcome-banner" aria-hidden="true"><img :src="artwork" alt="" /></div>
                <div class="welcome">
                  <h4 id="pgw-s1" ref="headingEl" tabindex="-1" class="welcome-title">
                    תיק אישי ללקוח,<br><span>בשלוש דקות</span>
                  </h4>
                </div>

                <!-- Lookup -->
                <div class="lookup" :class="{ 'lookup--found': lookup === 'found' }">
                  <label for="pgw-id" class="lookup-label">תעודת זהות של הלקוח</label>
                  <div class="lookup-row">
                    <span class="lookup-icon" aria-hidden="true">
                      <span v-if="lookup === 'searching'" class="mini-spinner"></span>
                      <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                    </span>
                    <input
                      id="pgw-id" v-model="form.customer_id_number" dir="ltr" inputmode="numeric" autocomplete="off"
                      placeholder="012345678" @blur="autoFill" @keydown.enter.prevent="autoFill"
                    />
                  </div>

                  <Transition name="fade" mode="out-in">
                    <div v-if="lookup === 'found'" key="found" class="found-card" aria-live="polite">
                      <span class="found-avatar" aria-hidden="true">{{ initials }}</span>
                      <div class="found-text">
                        <span class="found-kicker">נמצא בתיק שלכם</span>
                        <span class="found-name">{{ form.customer_name }}</span>
                        <span v-if="mixTotal" class="found-meta"><span class="ltr-number">{{ mixTotal }}</span> מוצרים<template v-if="productMix.savings && productMix.insurance"> · חיסכון וביטוח</template><template v-else-if="productMix.savings"> · חיסכון</template><template v-else-if="productMix.insurance"> · ביטוח</template></span>
                      </div>
                      <button type="button" class="btn-link" @click="editName = !editName">{{ editName ? 'סגור' : 'שינוי שם' }}</button>
                    </div>
                    <p v-else-if="lookup === 'notfound'" key="nf" class="lookup-note" aria-live="polite">
                      לא מצאנו את הלקוח בקובץ הפרודוקציה — הקלידו את שמו כדי להמשיך.
                    </p>
                  </Transition>

                  <div v-if="lookup === 'notfound' || editName" class="field">
                    <label for="pgw-name">שם הלקוח</label>
                    <input id="pgw-name" v-model="form.customer_name" placeholder="שם מלא" autocomplete="off" />
                  </div>
                </div>

                <!-- Access -->
                <div class="q-card access">
                  <div class="access-row">
                    <div class="access-pass">
                      <label for="pgw-pass" class="access-sub">סיסמה</label>
                      <div class="password-row">
                        <input id="pgw-pass" :type="showPass ? 'text' : 'password'" v-model="form.password" dir="ltr" autocomplete="new-password" class="pass-input" />
                        <button type="button" class="icon-btn" @click="generatePassword" title="סיסמה חדשה" aria-label="צור סיסמה אוטומטית">
                          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/></svg>
                        </button>
                        <button type="button" class="icon-btn icon-btn--text" @click="showPass = !showPass" :aria-pressed="showPass">
                          {{ showPass ? 'הסתר' : 'הצג' }}
                        </button>
                      </div>
                    </div>
                  </div>
                  <div class="access-days">
                    <span class="access-sub" id="pgw-days-l">הקישור בתוקף ל־</span>
                    <div class="chips" role="radiogroup" aria-labelledby="pgw-days-l">
                      <button
                        v-for="d in DAY_OPTIONS" :key="d.days" type="button" role="radio"
                        class="chip" :class="{ 'chip--on': form.expires_days === d.days }"
                        :aria-checked="form.expires_days === d.days" @click="form.expires_days = d.days; dirty = true"
                      >{{ d.label }}</button>
                    </div>
                  </div>
                </div>
              </section>

              <!-- ── 2. מה הלקוח יראה ──────────────────────────── -->
              <section v-else-if="step === 2" class="step-panel" aria-labelledby="pgw-s2">
                <h4 id="pgw-s2" ref="headingEl" tabindex="-1" class="q-title">מה {{ firstName }} יראה בפורטל?</h4>

                <div class="q-card">
                  <p class="q-label" id="pgw-scope">אילו מוצרים להציג?</p>
                  <div class="chips" role="radiogroup" aria-labelledby="pgw-scope">
                    <button
                      v-for="o in scopeOptions" :key="o.id" type="button" role="radio"
                      class="chip" :class="{ 'chip--on': settings.product_scope === o.id }"
                      :aria-checked="settings.product_scope === o.id"
                      @click="setScope(o.id)"
                    >
                      {{ o.label }}<span v-if="o.count !== null" class="chip-count ltr-number">{{ o.count }}</span>
                    </button>
                  </div>
                  <p v-if="hiddenByScope > 0" class="q-note">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                    {{ hiddenByScope }} מוצרים לא יוצגו ללקוח בבחירה הזו
                  </p>
                </div>

                <div class="q-card">
                  <p class="q-label">אילו סכומים להציג?</p>
                  <div class="toggle-list toggle-list--inline">
                    <label v-for="a in amountOptions" :key="a.id" class="switch-row">
                      <span class="switch-text">{{ a.label }}</span>
                      <button type="button" role="switch" class="switch" :aria-checked="settings.show_amounts[a.id]" :aria-label="a.label" @click="toggleAmount(a.id)"><span class="switch-knob"></span></button>
                    </label>
                  </div>
                </div>

                <div class="q-card">
                  <p class="q-label">אילו חלקים יופיעו בתיק?</p>
                  <div class="toggle-list">
                    <label v-for="sec in SECTIONS" :key="sec.id" class="switch-row switch-row--rich">
                      <span class="sec-icon" v-html="sec.icon" aria-hidden="true"></span>
                      <span class="switch-text">
                        <span class="sec-title">{{ sec.label }}<span v-if="recommended.has(sec.id)" class="badge">מומלץ</span></span>
                        <span class="sec-desc">{{ sec.desc }}</span>
                      </span>
                      <button type="button" role="switch" class="switch" :aria-checked="settings.sections[sec.id]" :aria-label="sec.label" @click="toggleSection(sec.id)"><span class="switch-knob"></span></button>
                    </label>
                  </div>
                </div>
              </section>

              <!-- ── 3. שירותים נוספים ────────────────────────── -->
              <section v-else-if="step === 3" class="step-panel" aria-labelledby="pgw-s3">
                <div class="welcome-banner welcome-banner--pitch" aria-hidden="true">
                  <img :src="offersArtwork" alt="" />
                  <span>על מספר הסוכן שלכם</span>
                </div>
                <h4 id="pgw-s3" ref="headingEl" tabindex="-1" class="q-title">להציע ל{{ firstName }} שירותים נוספים?</h4>
                <p class="q-lead">
                  הציעו ללקוחות לרכוש עצמאית ביטוח נסיעות לחו"ל ופוליסת חיסכון, על מספר הסוכן שלכם.
                  בפורטל יופיעו כרטיסי שירות — לחיצה פותחת את <strong>קישור הרכישה האישי שלכם</strong>, כך שכל רכישה נרשמת אצלכם.
                </p>
                <div class="choice-cards" role="radiogroup" aria-label="הצעות מסחריות">
                  <button type="button" role="radio" class="choice" :class="{ 'choice--on': offersEnabled }" :aria-checked="offersEnabled" @click="setOffersEnabled(true)">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 12v10H4V12"/><path d="M2 7h20v5H2z"/><path d="M12 22V7"/><path d="M12 7H7.5a2.5 2.5 0 0 1 0-5C11 2 12 7 12 7z"/><path d="M12 7h4.5a2.5 2.5 0 0 0 0-5C13 2 12 7 12 7z"/></svg>
                    <span><strong>כן, להציע שירותים</strong><small>תבחרו אילו ותוסיפו קישור</small></span>
                  </button>
                  <button type="button" role="radio" class="choice" :class="{ 'choice--on': !offersEnabled }" :aria-checked="!offersEnabled" @click="setOffersEnabled(false)">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="8" y1="12" x2="16" y2="12"/></svg>
                    <span><strong>לא הפעם</strong><small>אפשר להוסיף בכל רגע</small></span>
                  </button>
                </div>

                <Transition name="fade">
                  <div v-if="offersEnabled" class="q-card">
                    <p class="q-label">אילו שירותים?</p>
                    <div v-if="offersLoading" class="auto-hint auto-hint--static"><span class="mini-spinner"></span>טוען…</div>
                    <div v-else-if="offersError" class="retry-row" role="alert">
                      <span>השירותים לא נטענו כרגע.</span>
                      <button type="button" class="btn-link" @click="loadOffers">נסו שוב</button>
                    </div>
                    <div v-else class="toggle-list">
                      <div v-for="o in offerRows" :key="o.service_key" class="offer-row">
                        <label class="switch-row">
                          <span class="switch-text">
                            <span class="sec-title">{{ o.title }}</span>
                            <span v-if="o.clicks" class="sec-desc">לקוחות פתחו את ההצעה <span class="ltr-number">{{ o.clicks }}</span> פעמים</span>
                          </span>
                          <button type="button" role="switch" class="switch" :aria-checked="o.on" :aria-label="o.title" @click="toggleOffer(o)"><span class="switch-knob"></span></button>
                        </label>
                        <div v-if="o.on" class="field field--offer">
                          <label :for="'pgw-o-' + o.service_key" class="sr-only">קישור רכישה — {{ o.title }}</label>
                          <input
                            :id="'pgw-o-' + o.service_key" v-model="o.url" dir="ltr" inputmode="url"
                            placeholder="https://… הקישור האישי שלכם" :aria-invalid="o.touched && !validUrl(o.url)"
                            :aria-describedby="'pgw-oe-' + o.service_key" @blur="o.touched = true"
                          />
                          <span v-if="o.touched && !validUrl(o.url)" :id="'pgw-oe-' + o.service_key" class="field-error" role="alert">הקישור צריך להתחיל ב-https://</span>
                        </div>
                      </div>
                    </div>
                    <p class="q-note q-note--muted">הקישורים נשמרים אצלכם ויחכו מוכנים גם ללקוח הבא.</p>
                  </div>
                </Transition>
              </section>

              <!-- ── Done ─────────────────────────────────────── -->
              <section v-else class="step-panel success-section" aria-live="polite">
                <div class="success-icon" aria-hidden="true">
                  <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                </div>
                <h4 ref="headingEl" tabindex="-1" class="success-text">{{ isEdit ? 'השינויים נשמרו' : 'הפורטל של ' + firstName + ' מוכן' }}</h4>
                <template v-if="!isEdit">
                  <p class="q-lead">שלחו ללקוח את הקישור, ואת הסיסמה — בנפרד.</p>
                  <div class="link-box">
                    <input :value="portalUrl" readonly dir="ltr" aria-label="קישור לפורטל" />
                    <button type="button" class="copy-btn" @click="copyLink">{{ copied ? 'הועתק' : 'העתק' }}</button>
                  </div>
                </template>
              </section>
            </div>

            <Transition name="fade">
              <p v-if="error" class="error-text" role="alert">{{ error }}</p>
            </Transition>

            <!-- Leave-without-saving guard -->
            <div v-if="confirmClose" class="confirm-bar" role="alertdialog" aria-label="לסגור בלי לשמור?">
              <span>לסגור בלי לשמור? הבחירות לא יישמרו.</span>
              <button type="button" class="btn-link" @click="confirmClose = false">להמשיך</button>
              <button type="button" class="btn-link btn-link--danger" @click="forceClose">לסגור</button>
            </div>

            <div class="modal-actions">
              <template v-if="step <= 3">
                <button type="button" class="btn-primary" :disabled="!canNext || busy" @click="next">
                  <span v-if="busy" class="btn-spinner" aria-hidden="true"></span>
                  <span>{{ primaryLabel }}</span>
                </button>
                <button v-if="step > firstStep" type="button" class="btn-secondary" @click="back">הקודם</button>
                <button v-else type="button" class="btn-secondary" @click="requestClose">ביטול</button>
              </template>
              <button v-else type="button" class="btn-primary" @click="forceClose">סיום</button>
            </div>
          </div>

          <!-- Left in RTL: the surreal picture; from step 2 the live phone
               preview floats over it. Hidden below 820px (the form is the job). -->
          <aside class="pane pane--art" aria-hidden="true">
            <Transition name="art-swap">
              <img :key="artSrc" :src="artSrc" alt="" class="art-img" />
            </Transition>
            <div class="art-veil" :class="{ 'art-veil--deep': showPreview, 'art-veil--pitch': step === 3 }"></div>
            <div v-show="showPreview" ref="previewEl" class="preview-mount"></div>
            <!-- Step 3 is the commercial moment: its own picture + the pitch. -->
            <Transition name="fade">
              <div v-if="step === 3" class="art-pitch">
                <span class="art-kicker">שירותים נוספים</span>
                <p>הציעו ללקוחות לרכוש עצמאית ביטוח נסיעות לחו"ל ופוליסת חיסכון, על מספר הסוכן שלכם</p>
              </div>
            </Transition>
          </aside>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import artwork from '../../assets/portal/portal-setup-surreal.webp'
import offersArtwork from '../../assets/portal/portal-offers-surreal.webp'

import { ref, reactive, computed, watch, nextTick, onBeforeUnmount } from 'vue'
import { usePortalStore } from '../../stores/portal.js'
import { CHART_PALETTE } from '../../utils/chartPalette.js'

const props = defineProps({
  show: Boolean,
  // Edit mode: reopen steps 2–3 for an existing link (PortalLinksManager "הגדרות").
  editLink: { type: Object, default: null },
})
const emit = defineEmits(['close', 'generated', 'saved'])

const portalStore = usePortalStore()
const isEdit = computed(() => !!props.editLink)

const STEPS = [
  { n: 1, title: 'למי', desc: 'לקוח וכניסה מאובטחת' },
  { n: 2, title: 'מה יוצג', desc: 'דוחות ונתונים' },
  { n: 3, title: 'שירותים', desc: 'הצעות משלימות' },
]
const firstStep = computed(() => (isEdit.value ? 2 : 1))
const visibleSteps = computed(() => STEPS.filter((s) => s.n >= firstStep.value))

// Section catalogue — research: every one is backed by data the portal
// already serves (services/portal_view.SECTION_KEYS). No "דוח מסלקה": nothing
// serves it yet.
const ic = (d) => `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`
const SECTIONS = [
  { id: 'summary', label: 'סיכום', desc: 'מוצרים, פרמיה וצבירה — במבט אחד', icon: ic('<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>') },
  { id: 'products', label: 'המוצרים שלי', desc: 'כל פוליסה וקופה, עם הפרטים המלאים', icon: ic('<path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>') },
  { id: 'companies', label: 'פיזור לפי חברות', desc: 'איך התיק מתחלק בין חברות הביטוח', icon: ic('<path d="M21.21 15.89A10 10 0 1 1 8 2.83"/><path d="M22 12A10 10 0 0 0 12 2v10z"/>') },
  { id: 'trend', label: 'מגמה לאורך זמן', desc: 'איך הצבירה והפרמיה משתנות מחודש לחודש', icon: ic('<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>') },
  { id: 'changes', label: 'מה השתנה', desc: 'מוצרים חדשים, שהוסרו או שהשתנו מהפעם הקודמת', icon: ic('<path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/>') },
  { id: 'ai_chat', label: 'עוזר אישי', desc: 'הלקוח שואל על התיק ומקבל תשובה מיד', icon: ic('<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>') },
  { id: 'print', label: 'הדפסת דוח', desc: 'הדפסה או שמירה של התיק כ-PDF', icon: ic('<polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/>') },
  { id: 'agent_card', label: 'כרטיס סוכן', desc: 'השם והטלפון שלכם, לחיוג בלחיצה', icon: ic('<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72c.13.96.36 1.9.7 2.81a2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45c.91.34 1.85.57 2.81.7A2 2 0 0 1 22 16.92z"/>') },
]

const defaultSettings = () => ({
  sections: Object.fromEntries(SECTIONS.map((s) => [s.id, true])),
  product_scope: 'all',
  show_amounts: { premium: true, accumulation: true },
  offers: [],
})

const form = reactive({ customer_id_number: '', customer_name: '', customer_email: '', password: '', expires_days: 30 })
const settings = reactive(defaultSettings())
const step = ref(1)
const maxReached = ref(1)
const showPass = ref(false)
const busy = ref(false)
const error = ref(null)
const copied = ref(false)
const autoFilling = ref(false)
const generatedLink = ref(null)
const productMix = ref(null)
const dirty = ref(false)
const confirmClose = ref(false)
const headingEl = ref(null)

const offersEnabled = ref(false)
const offersLoading = ref(false)
const offerRows = ref([])   // [{service_key,title,url,on,clicks,touched}]
let offersLoaded = false

// ── reset / open ──
function resetAll() {
  Object.assign(form, { customer_id_number: '', customer_name: '', customer_email: '', password: '', expires_days: 30 })
  Object.assign(settings, defaultSettings())
  error.value = null; generatedLink.value = null; productMix.value = null
  copied.value = false; dirty.value = false; confirmClose.value = false
  offersEnabled.value = false; offersLoaded = false; offerRows.value = []
  lastChanged.value = 'all'
  recommendationsApplied = false; settingsTouched = false
  if (props.editLink) {
    const s = props.editLink.settings
    if (s) {
      Object.assign(settings.sections, s.sections || {})
      settings.product_scope = s.product_scope || 'all'
      Object.assign(settings.show_amounts, s.show_amounts || {})
      settings.offers = [...(s.offers || [])]
      offersEnabled.value = settings.offers.length > 0
    } else {
      // A pre-wizard link: the server shows it without the agent card
      // (portal_view) — the wizard must say so too, not claim it's on.
      settings.sections.agent_card = false
    }
    form.customer_name = props.editLink.customer_name
    form.customer_id_number = props.editLink.customer_id_number
    step.value = 2; maxReached.value = 3
    loadMix()
    if (offersEnabled.value) loadOffers()
  } else {
    step.value = 1; maxReached.value = 1
    lookup.value = 'idle'; editName.value = false; lastLookedUp = ''
    generatePassword()          // ready before the agent even looks
    showPass.value = false
  }
}
watch(() => props.show, (v) => { if (v) { resetAll(); focusHeading() } else unmountPreview() })

// ── step 1 ──
const firstName = computed(() => (form.customer_name || '').trim().split(/\s+/)[0] || 'הלקוח')
const DAY_OPTIONS = [{ days: 30, label: 'חודש' }, { days: 90, label: '3 חודשים' }, { days: 365, label: 'שנה' }]
const lookup = ref('idle') // idle | searching | found | notfound
const editName = ref(false)
const initials = computed(() => (form.customer_name || '').trim().split(/\s+/).map((w) => w[0]).slice(0, 2).join('') || '?')
const step1Valid = computed(() => form.customer_id_number && form.customer_name && form.password && form.expires_days >= 1)
const mixTotal = computed(() => (productMix.value ? productMix.value.savings + productMix.value.insurance + productMix.value.unknown : 0))

function generatePassword() {
  let pass = ''
  const buf = new Uint32Array(6)
  crypto.getRandomValues(buf)
  for (const n of buf) pass += String(n % 10)
  form.password = pass
  showPass.value = true
}

async function loadMix() {
  if (!form.customer_id_number || form.customer_id_number.length < 5) return
  const info = await portalStore.getCustomerInfo(form.customer_id_number)
  productMix.value = info.product_mix || null
  return info
}
let lastLookedUp = ''
async function autoFill() {
  const id = (form.customer_id_number || '').trim()
  if (id.length < 5 || id === lastLookedUp) return
  lastLookedUp = id
  autoFilling.value = true
  lookup.value = 'searching'
  try {
    const info = await loadMix()
    const found = !!(info && (info.name || (info.product_mix && (info.product_mix.savings + info.product_mix.insurance + info.product_mix.unknown))))
    if (info?.name) form.customer_name = info.name
    lookup.value = found && form.customer_name ? 'found' : 'notfound'
    applyRecommendations()
  } finally {
    autoFilling.value = false
  }
}

// ── step 2 ──
const scopeOptions = computed(() => {
  const m = productMix.value
  return [
    { id: 'all', label: 'הכל', count: m ? mixTotal.value : null },
    { id: 'savings', label: 'חיסכון', count: m ? m.savings : null },
    { id: 'insurance', label: 'ביטוח', count: m ? m.insurance : null },
  ]
})
const hiddenByScope = computed(() => {
  const m = productMix.value
  if (!m || settings.product_scope === 'all') return 0
  return settings.product_scope === 'savings' ? m.insurance + m.unknown : m.savings + m.unknown
})
const amountOptions = [
  { id: 'accumulation', label: 'צבירה' },
  { id: 'premium', label: 'פרמיה חודשית' },
]
// Research-driven hint: savings customers care about growth and spread;
// insurance-only customers about their policies and what changed.
const recommended = computed(() => {
  const m = productMix.value
  if (!m) return new Set()
  if (m.savings > 0) return new Set(['trend', 'companies', 'summary'])
  return new Set(['products', 'changes', 'agent_card'])
})
let recommendationsApplied = false
let settingsTouched = false
function applyRecommendations() {
  // Only a first nudge, never over the agent's own clicks.
  if (recommendationsApplied || settingsTouched || isEdit.value || !productMix.value) return
  recommendationsApplied = true
  if (productMix.value.savings === 0) settings.sections.trend = false
}

const lastChanged = ref('all')
function setScope(id) { settings.product_scope = id; mark('products') }
function toggleAmount(id) { settings.show_amounts[id] = !settings.show_amounts[id]; mark('summary') }
function toggleSection(id) { settings.sections[id] = !settings.sections[id]; mark(id) }
function mark(key) { dirty.value = true; settingsTouched = true; lastChanged.value = key }

// ── step 3 ──
const offersError = ref(false)
async function loadOffers() {
  if (offersLoaded) return
  offersLoading.value = true
  offersError.value = false
  try {
    const { catalog, offers } = await portalStore.fetchOffers()
    const saved = Object.fromEntries(offers.map((o) => [o.service_key, o]))
    offerRows.value = catalog.map((c) => ({
      service_key: c.service_key,
      title: saved[c.service_key]?.title || c.title,
      url: saved[c.service_key]?.url || '',
      clicks: saved[c.service_key]?.clicks || 0,
      on: settings.offers.includes(c.service_key),
      touched: false,
    }))
    offersLoaded = true
  } catch {
    offersError.value = true
  } finally {
    offersLoading.value = false
  }
}
function setOffersEnabled(v) {
  offersEnabled.value = v
  dirty.value = true
  lastChanged.value = 'offers'
  if (v) loadOffers()
}
function toggleOffer(o) { o.on = !o.on; mark('offers') }
function validUrl(u) {
  try {
    const x = new URL((u || '').trim())
    return x.protocol === 'https:' && !!x.hostname && !/\s/.test(u.trim())
  } catch { return false }
}
const enabledOffers = computed(() => (offersEnabled.value ? offerRows.value.filter((o) => o.on) : []))
const step3Valid = computed(() => enabledOffers.value.every((o) => validUrl(o.url)))

// ── navigation ──
const canNext = computed(() => (step.value === 1 ? step1Valid.value : step.value === 3 ? step3Valid.value : true))
const primaryLabel = computed(() => {
  if (step.value < 3) return 'המשך'
  if (busy.value) return isEdit.value ? 'שומר…' : 'יוצר…'
  return isEdit.value ? 'שמירה' : 'צור פורטל'
})
function focusHeading() { nextTick(() => headingEl.value?.focus?.()) }
function goTo(n) {
  if (n < firstStep.value || n > maxReached.value) return
  step.value = n; error.value = null; focusHeading()
}
function back() { goTo(step.value - 1) }
async function next() {
  if (!canNext.value || busy.value) return
  if (step.value === 3) {
    enabledOffers.value.forEach((o) => { o.touched = true })
    return submit()
  }
  step.value += 1
  maxReached.value = Math.max(maxReached.value, step.value)
  if (step.value === 2 && !productMix.value) loadMix().then(applyRecommendations)
  focusHeading()
}

function buildSettings() {
  return {
    sections: { ...settings.sections },
    product_scope: settings.product_scope,
    show_amounts: { ...settings.show_amounts },
    offers: enabledOffers.value.map((o) => o.service_key),
  }
}
async function submit() {
  if (!step3Valid.value) return
  busy.value = true; error.value = null
  try {
    if (enabledOffers.value.length) {
      await portalStore.saveOffers(enabledOffers.value.map((o) => ({
        service_key: o.service_key, title: o.title, url: o.url.trim(), is_active: true,
      })))
    }
    if (isEdit.value) {
      const link = await portalStore.updateLinkSettings(props.editLink.token, buildSettings())
      emit('saved', link)
    } else {
      const link = await portalStore.generateLink({
        customer_id_number: form.customer_id_number,
        customer_name: form.customer_name,
        customer_email: null, // no email field in the wizard — never store an address the agent didn't see
        password: form.password,
        expires_days: form.expires_days,
        settings: buildSettings(),
      })
      generatedLink.value = link
      emit('generated', link)
    }
    dirty.value = false
    step.value = 4
    focusHeading()
  } catch {
    error.value = portalStore.error || 'משהו השתבש — נסו שוב'
  } finally {
    busy.value = false
  }
}

function requestClose() {
  if (busy.value) return
  if (dirty.value && step.value <= 3) { confirmClose.value = true; return }
  forceClose()
}
function forceClose() { confirmClose.value = false; emit('close') }

// ── done ──
const portalUrl = computed(() => (generatedLink.value ? `${window.location.origin}/portal/${generatedLink.value.token}` : ''))
async function copyLink() {
  try {
    await navigator.clipboard.writeText(portalUrl.value)
  } catch {
    const input = document.createElement('input')
    input.value = portalUrl.value
    document.body.appendChild(input); input.select(); document.execCommand('copy'); document.body.removeChild(input)
  }
  copied.value = true
  setTimeout(() => { copied.value = false }, 2000)
}

// ── Remotion live preview (React island, like SetupProgressCard) ──
const previewEl = ref(null)
const reducedMotion = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
// Phone preview in step 2; step 3 hands the pane to its own picture + pitch.
const showPreview = computed(() => step.value === 2)
const artSrc = computed(() => (step.value === 3 ? offersArtwork : artwork))
let previewRoot = null
let previewMods = null
let previewNonce = 0 // new key per change → the Player remounts and replays the entrance

function cssVar(name, fallback) {
  try { return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback } catch { return fallback }
}
const previewProps = computed(() => ({
  customerName: firstName.value,
  sections: { ...settings.sections },
  scope: settings.product_scope,
  showPremium: settings.show_amounts.premium,
  showAccumulation: settings.show_amounts.accumulation,
  offers: enabledOffers.value.map((o) => o.title),
  highlight: lastChanged.value,
  ink: cssVar('--tab-portal-ink', '#35719A'),
  accent: cssVar('--tab-portal', '#4E9DD0'),
  wash: 'rgba(78, 157, 208, 0.12)',
  palette: [CHART_PALETTE[1], CHART_PALETTE[9], CHART_PALETTE[3], CHART_PALETTE[6], CHART_PALETTE[2]],
}))

async function mountPreview() {
  if (!previewEl.value || previewRoot) return
  // The art pane is hidden below 820px — don't download/run the island there.
  if (window.matchMedia?.('(max-width: 820px)').matches) return
  try {
    const [rdClient, react, player, comp] = await Promise.all([
      import('react-dom/client'),
      import('react'),
      import('@remotion/player'),
      import('../../remotion/PortalPreviewPhone'),
    ])
    if (!previewEl.value || previewRoot) return
    previewMods = { react, player, comp }
    previewRoot = rdClient.createRoot(previewEl.value)
    paintPreview()
  } catch (e) {
    console.error('[PortalGenerateModal] preview failed', e) // decorative — wizard works without it
  }
}
function paintPreview() {
  if (!previewRoot || !previewMods) return
  const { react, player, comp } = previewMods
  previewRoot.render(
    react.createElement(player.Player, {
      key: previewNonce,
      component: comp.PortalPreviewPhone,
      inputProps: previewProps.value,
      durationInFrames: comp.PORTAL_PREVIEW_FRAMES,
      fps: 30,
      compositionWidth: comp.PORTAL_PREVIEW_W,
      compositionHeight: comp.PORTAL_PREVIEW_H,
      // Reduced motion: render the final frame, no entrance animation.
      initialFrame: reducedMotion ? comp.PORTAL_PREVIEW_FRAMES - 1 : 0,
      autoPlay: !reducedMotion,
      loop: false,
      // Default is true: on end the Player jumps back to frame 0 — the
      // "before the entrance" state — and the block that just changed vanished.
      moveToBeginningWhenEnded: false,
      controls: false,
      clickToPlay: false,
      doubleClickToFullscreen: false,
      acknowledgeRemotionLicense: true,
      style: { width: '100%', height: '100%', backgroundColor: 'transparent' },
    }),
  )
}
function unmountPreview() {
  if (previewRoot) { try { previewRoot.unmount() } catch { /* ignore */ } }
  previewRoot = null
}
watch(showPreview, (v) => { if (v) nextTick(mountPreview) })
// Compare by value: typing an offer's URL rebuilds the arrays without changing
// anything the phone shows — replaying the entrance per keystroke flickers.
watch(() => JSON.stringify(previewProps.value), () => {
  if (!reducedMotion) previewNonce += 1
  paintPreview()
})
onBeforeUnmount(unmountPreview)
</script>

<style scoped>
.modal-overlay {
  position: fixed; inset: 0; z-index: 1010;
  background: rgba(0, 0, 0, 0.45);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
/* Two panes: the workshop on the right (first in the DOM under rtl) and the
   picture + live preview on the left. Only the form pane scrolls. */
.modal-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 0.78fr;
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  width: 100%; max-width: 980px;
  height: min(720px, 92vh);
  overflow: hidden;
}
.pane--form {
  display: flex; flex-direction: column;
  padding: 26px 28px 20px;
  min-width: 0; min-height: 0;
}
.pane--art { position: relative; overflow: hidden; background: #6f8e99; }
.art-img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; object-position: 30% 40%; display: block; }
.art-swap-enter-active { transition: opacity 0.45s ease-out; }
.art-swap-leave-active { transition: opacity 0.3s ease-in; }
.art-swap-enter-from, .art-swap-leave-to { opacity: 0; }
.art-veil--pitch {
  /* dark wash under the pitch so white text holds ≥4.5:1 on the sky-blue wall */
  background: linear-gradient(to bottom, rgba(18, 28, 36, 0.62) 0%, rgba(18, 28, 36, 0.28) 34%, transparent 58%);
}
.art-pitch {
  position: absolute; top: 0; inset-inline: 0; padding: 30px 28px;
  direction: rtl; color: #fff; display: flex; flex-direction: column; gap: 8px;
}
.art-kicker {
  align-self: flex-start; font-size: 12px; font-weight: 700; letter-spacing: 0.02em;
  padding: 3px 10px; border-radius: 999px; background: rgba(255, 255, 255, 0.16); border: 1px solid rgba(255, 255, 255, 0.28);
}
.art-pitch p { margin: 0; font-size: 22px; font-weight: 800; line-height: 1.35; letter-spacing: -0.01em; text-shadow: 0 1px 12px rgba(0, 0, 0, 0.25); }
.art-veil {
  position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(to left, rgba(255, 255, 255, 0.28), transparent 34%);
  transition: background 0.4s ease;
}
.art-veil--deep {
  background:
    linear-gradient(to left, rgba(255, 255, 255, 0.28), transparent 34%),
    radial-gradient(ellipse at 50% 55%, rgba(24, 24, 24, 0.18), transparent 70%);
}
.preview-mount {
  position: absolute; inset: 4% 6%;
  direction: ltr; /* RTL root would shift the Remotion composition */
}
@media (max-width: 820px) {
  /* A fixed height so only the step body scrolls — with `auto` the whole card
     scrolled and the header + step rail slid out of view. Bottom padding keeps
     the footer clear of MessengerDock's pill (bottom 20px, 52px tall). */
  .modal-overlay { padding: 12px 12px 84px; }
  .modal-card { grid-template-columns: 1fr; max-width: 520px; height: 100%; max-height: 760px; }
  .pane--art { display: none; }
  .pane--form { padding: 18px 16px 14px; }
  .step-desc { display: none; }
  .step-n { font-size: 24px; }
}

/* ── header ── */
.modal-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 16px; }
.modal-heading { min-width: 0; }
.modal-header h3 { font-size: 19px; font-weight: 800; color: var(--text); margin: 0; }
.modal-sub { margin: 4px 0 0; font-size: 13px; line-height: 1.6; color: var(--text-muted); }
.close-btn {
  flex-shrink: 0; width: 36px; height: 36px; display: grid; place-items: center;
  border-radius: 10px; color: var(--text-muted); background: transparent; border: 0; cursor: pointer;
}
.close-btn:hover { color: var(--text); background: var(--bg); }
.close-btn:focus-visible { outline: 2px solid var(--tab-portal-ink); outline-offset: 2px; }

/* ── step 1: welcome ── */
.welcome-banner { display: none; }
.welcome { display: flex; flex-direction: column; gap: 4px; }
.welcome-title {
  margin: 0; outline: none;
  font-size: clamp(24px, 2.6vw, 30px); font-weight: 900; line-height: 1.15; letter-spacing: -0.03em; color: var(--text);
}
.welcome-title span { color: var(--tab-portal-ink); }
.lookup {
  display: flex; flex-direction: column; gap: 10px; padding: 14px;
  border-radius: 16px; background: var(--tab-portal-wash); border: 1px solid transparent;
  transition: border-color 0.25s, background 0.25s;
}
.lookup--found { background: var(--card-bg); border-color: color-mix(in srgb, var(--tab-portal-ink) 35%, transparent); }
.lookup-label { font-size: 13px; font-weight: 700; color: var(--text); }
.lookup-row { position: relative; }
.lookup-icon { position: absolute; top: 50%; right: 14px; transform: translateY(-50%); color: var(--tab-portal-ink); display: grid; place-items: center; pointer-events: none; }
.lookup-row input {
  width: 100%; min-height: 52px; padding: 0 44px 0 16px; box-sizing: border-box;
  border: 1px solid var(--border); border-radius: 12px; background: var(--card-bg);
  font: inherit; font-size: 18px; font-weight: 700; letter-spacing: 0.06em; color: var(--text);
}
.lookup-row input:focus { outline: none; border-color: var(--tab-portal-ink); box-shadow: 0 0 0 3px color-mix(in srgb, var(--tab-portal) 22%, transparent); }
.found-card { display: flex; align-items: center; gap: 12px; }
.found-avatar {
  width: 44px; height: 44px; flex-shrink: 0; display: grid; place-items: center; border-radius: 50%;
  background: var(--tab-portal-ink); color: #fff; font-weight: 800; font-size: 15px;
}
.found-text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.found-kicker { font-size: 11.5px; font-weight: 700; color: var(--green, #2E844A); }
.found-name { font-size: 16px; font-weight: 800; color: var(--text); }
.found-meta { font-size: 12.5px; color: var(--text-muted); }
.lookup-note { margin: 0; font-size: 12.5px; color: var(--text-muted); }
.access { gap: 12px; }
.access-sub { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.access-pass { display: flex; flex-direction: column; gap: 5px; flex: 1; }
.access-row { display: flex; gap: 12px; }
.pass-input {
  flex: 1; min-width: 0; min-height: 44px; padding: 0 14px; border: 1px solid var(--border); border-radius: var(--radius-sm);
  font-family: ui-monospace, monospace; font-size: 18px; letter-spacing: 0.3em; background: var(--bg-surface); color: var(--text);
}
.pass-input:focus { outline: none; border-color: var(--tab-portal-ink); }
.access-days { display: flex; flex-direction: column; gap: 6px; }
.retry-row { display: flex; align-items: center; gap: 10px; font-size: 12.5px; color: var(--text-muted); }
@media (max-width: 820px) {
  .welcome-banner {
    display: block; margin: -4px -2px 4px; height: 120px; border-radius: 14px; overflow: hidden; position: relative;
  }
  .welcome-banner img { width: 100%; height: 100%; object-fit: cover; object-position: 22% 28%; display: block; }
  .welcome-banner--pitch img { object-position: 50% 62%; }
  .welcome-banner--pitch span {
    position: absolute; top: 10px; right: 12px; z-index: 1; font-size: 12px; font-weight: 700; color: #fff;
    padding: 3px 10px; border-radius: 999px; background: rgba(18, 28, 36, 0.55);
  }
  .welcome-banner::after { content: ''; position: absolute; inset: 0; background: linear-gradient(to bottom, transparent 40%, var(--card-bg)); }
}

/* ── step rail — big light numerals, like the product's marketing steps ── */
.steps { list-style: none; margin: 0 0 16px; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(0, 1fr)); gap: 8px; }
.step-btn {
  width: 100%; display: flex; align-items: center; gap: 10px; text-align: start;
  padding: 10px 12px; border-radius: 12px; border: 1px solid var(--border-subtle);
  background: var(--card-bg); font-family: inherit; cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}
.step-btn:disabled { cursor: default; opacity: 0.55; }
.step-btn:focus-visible { outline: 2px solid var(--tab-portal-ink); outline-offset: 2px; }
.step-n { font-size: 30px; font-weight: 200; line-height: 1; color: var(--text-muted); min-width: 18px; }
.step-text { display: flex; flex-direction: column; min-width: 0; }
.step-title { font-size: 13px; font-weight: 800; color: var(--text); }
.step-desc { font-size: 11px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.step--on .step-btn { border-color: var(--tab-portal-ink); background: var(--tab-portal-wash); }
.step--on .step-n { color: var(--tab-portal-ink); }
.step--done .step-n { color: var(--tab-portal-ink); }

/* ── body ── */
.step-body { flex: 1; min-height: 0; overflow-y: auto; padding: 2px 2px 8px; margin: 0 -2px; }
.step-panel { display: flex; flex-direction: column; gap: 14px; }
.q-title { font-size: 16px; font-weight: 800; color: var(--text); margin: 2px 0 0; outline: none; }
.q-lead { margin: -4px 0 0; font-size: 13px; line-height: 1.7; color: var(--text-secondary, #3E3E3C); }
.q-card { border: 1px solid var(--border-subtle); border-radius: 14px; padding: 14px; background: var(--card-bg); display: flex; flex-direction: column; gap: 10px; }
.q-label { margin: 0; font-size: 13px; font-weight: 700; color: var(--text); }
.q-note { margin: 0; display: flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 600; color: var(--amber, #8A6300); }
.q-note--muted { color: var(--text-muted); font-weight: 500; }

/* chips (radio) */
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  min-height: 40px; display: inline-flex; align-items: center; gap: 8px;
  padding: 0 16px; border-radius: 999px; border: 1px solid var(--border);
  background: var(--card-bg); color: var(--text); font: inherit; font-size: 13px; font-weight: 600; cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}
.chip:hover { border-color: var(--tab-portal-ink); }
.chip:focus-visible { outline: 2px solid var(--tab-portal-ink); outline-offset: 2px; }
.chip--on { background: var(--tab-portal-ink); border-color: var(--tab-portal-ink); color: #fff; }
.chip-count { font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: 999px; background: rgba(24, 24, 24, 0.07); }
.chip--on .chip-count { background: rgba(255, 255, 255, 0.22); }

/* switches */
.toggle-list { display: flex; flex-direction: column; gap: 2px; }
.toggle-list--inline { flex-direction: row; flex-wrap: wrap; gap: 8px 22px; }
.switch-row { display: flex; align-items: center; gap: 10px; min-height: 44px; cursor: pointer; }
.switch-row--rich { padding: 4px 0; border-top: 1px solid var(--border-subtle); }
.switch-row--rich:first-child { border-top: 0; }
.switch-text { flex: 1; display: flex; flex-direction: column; min-width: 0; font-size: 13px; font-weight: 600; color: var(--text); }
.toggle-list--inline .switch-text { flex: 0 1 auto; }
.sec-title { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 700; color: var(--text); }
.sec-desc { font-size: 11.5px; font-weight: 400; color: var(--text-muted); line-height: 1.5; }
.sec-icon {
  width: 32px; height: 32px; flex-shrink: 0; display: grid; place-items: center;
  border-radius: 9px; background: var(--tab-portal-wash); color: var(--tab-portal-ink);
}
.badge { font-size: 10px; font-weight: 700; padding: 1px 7px; border-radius: 999px; background: var(--tab-portal-wash); color: var(--tab-portal-ink); }
.switch {
  position: relative; flex-shrink: 0; width: 40px; height: 24px; border-radius: 999px;
  border: 0; padding: 0; background: rgba(24, 24, 24, 0.18); cursor: pointer; transition: background 0.2s ease;
}
.switch::before { content: ''; position: absolute; inset: -10px -4px; } /* 44px hit area */
.switch-knob {
  position: absolute; top: 3px; right: 3px; width: 18px; height: 18px; border-radius: 50%;
  background: #fff; box-shadow: 0 1px 3px rgba(24, 24, 24, 0.25); transition: transform 0.2s cubic-bezier(0.34, 1.4, 0.64, 1);
}
.switch[aria-checked="true"] { background: var(--tab-portal-ink); }
.switch[aria-checked="true"] .switch-knob { transform: translateX(-16px); }
.switch:focus-visible { outline: 2px solid var(--tab-portal-ink); outline-offset: 2px; }

/* choice cards (step 3) */
.choice-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
.choice {
  display: flex; align-items: center; gap: 10px; text-align: start; min-height: 64px;
  padding: 12px 14px; border-radius: 14px; border: 1px solid var(--border);
  background: var(--card-bg); color: var(--text-muted); font: inherit; cursor: pointer;
  transition: border-color 0.2s, background 0.2s, color 0.2s;
}
.choice span { display: flex; flex-direction: column; gap: 2px; }
.choice strong { font-size: 13.5px; color: var(--text); }
.choice small { font-size: 11.5px; color: var(--text-muted); }
.choice:hover { border-color: var(--tab-portal-ink); }
.choice:focus-visible { outline: 2px solid var(--tab-portal-ink); outline-offset: 2px; }
.choice--on { border-color: var(--tab-portal-ink); background: var(--tab-portal-wash); color: var(--tab-portal-ink); }
@media (max-width: 520px) { .choice-cards { grid-template-columns: 1fr; } }

.offer-row { border-top: 1px solid var(--border-subtle); padding: 2px 0 6px; }
.offer-row:first-child { border-top: 0; }
.field--offer { margin-top: 2px; }

/* fields */
.field { display: flex; flex-direction: column; gap: 5px; position: relative; }
.field-row { display: flex; gap: 12px; align-items: flex-end; }
.field--grow { flex: 1; min-width: 0; }
.field--days { width: 110px; }
.field label { font-size: 12px; font-weight: 600; color: var(--text-muted); }
.opt { font-weight: 400; }
.field input {
  min-height: 44px; padding: 10px 14px; border: 1px solid var(--border); border-radius: var(--radius-sm);
  font-size: 14px; font-family: inherit; background: var(--bg-surface); color: var(--text);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.field input:focus {
  outline: none; border-color: var(--tab-portal-ink);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--tab-portal) 20%, transparent);
}
.field input[aria-invalid="true"] { border-color: var(--red); }
.field-help { font-size: 11.5px; color: var(--tab-portal-ink); font-weight: 600; }
.field-error { font-size: 11.5px; color: var(--red); font-weight: 600; }
.password-row { display: flex; gap: 8px; }
.password-row input { flex: 1; min-width: 0; }
.icon-btn {
  min-width: 44px; min-height: 44px; display: grid; place-items: center; padding: 0 10px;
  border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--bg);
  color: var(--text-muted); font: inherit; font-size: 12px; font-weight: 600; cursor: pointer; white-space: nowrap;
}
.icon-btn:hover { border-color: var(--tab-portal-ink); color: var(--tab-portal-ink); }
.icon-btn:focus-visible { outline: 2px solid var(--tab-portal-ink); outline-offset: 2px; }
.auto-hint { display: flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--text-muted); }
.mini-spinner { width: 12px; height: 12px; border: 1.5px solid var(--border-subtle); border-top-color: var(--tab-portal-ink); border-radius: 50%; animation: spin 0.8s linear infinite; }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }

.error-text { font-size: 13px; color: var(--red); background: var(--red-light); padding: 8px 12px; border-radius: 8px; margin: 8px 0 0; }
.confirm-bar {
  margin-top: 8px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
  padding: 8px 12px; border-radius: 10px; background: var(--amber-light, #FBF4DC); color: var(--amber, #8A6300);
  font-size: 12.5px; font-weight: 600;
}
.btn-link { border: 0; background: none; font: inherit; font-weight: 700; color: var(--text); cursor: pointer; padding: 4px 2px; min-height: 32px; }
.btn-link--danger { color: var(--red); }

/* footer */
.modal-actions { display: flex; gap: 10px; justify-content: flex-start; padding-top: 14px; margin-top: 8px; border-top: 1px solid var(--border-subtle); }
.btn-primary {
  display: inline-flex; align-items: center; gap: 8px; min-height: 44px; padding: 0 26px;
  background: var(--tab-portal-ink); color: #fff; border: 0; border-radius: 10px;
  font: inherit; font-size: 14px; font-weight: 700; cursor: pointer;
  box-shadow: 0 6px 16px -6px color-mix(in srgb, var(--tab-portal-ink) 60%, transparent);
  transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s;
}
.btn-primary:hover:not(:disabled) { transform: translateY(-1px); }
.btn-primary:disabled { opacity: 0.45; cursor: not-allowed; box-shadow: none; }
.btn-primary:focus-visible, .btn-secondary:focus-visible { outline: 2px solid var(--tab-portal-ink); outline-offset: 2px; }
.btn-secondary {
  min-height: 44px; padding: 0 20px; border: 1px solid var(--border); border-radius: 10px;
  font: inherit; font-size: 14px; font-weight: 600; color: var(--text-muted); background: var(--card-bg); cursor: pointer;
}
.btn-secondary:hover:not(:disabled) { border-color: var(--text-muted); color: var(--text); }
.btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-with-icon { display: inline-flex; align-items: center; gap: 6px; }
.btn-spinner { width: 14px; height: 14px; border: 2px solid rgba(255, 255, 255, 0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.8s linear infinite; }

/* success */
.success-section { align-items: center; text-align: center; padding-top: 24px; }
.success-icon { color: var(--green); }
.success-text { font-size: 18px; font-weight: 800; color: var(--text); margin: 0; outline: none; }
.link-box { display: flex; gap: 8px; width: 100%; }
.link-box input {
  flex: 1; min-width: 0; min-height: 44px; padding: 0 12px; border: 1px solid var(--border); border-radius: var(--radius-sm);
  font-size: 12px; font-family: monospace; background: var(--bg); color: var(--text-secondary, #3E3E3C);
}
.copy-btn {
  min-height: 44px; padding: 0 18px; border: 0; border-radius: var(--radius-sm);
  background: var(--tab-portal-ink); color: #fff; font: inherit; font-size: 13px; font-weight: 700; cursor: pointer;
}
.success-actions { display: flex; gap: 10px; justify-content: center; }

/* transitions */
.modal-enter-active { animation: modalIn 0.25s ease-out; }
.modal-leave-active { animation: modalIn 0.16s ease-in reverse; }
@keyframes modalIn { from { opacity: 0; } to { opacity: 1; } }
.modal-enter-active .modal-card { animation: slideUp 0.28s cubic-bezier(0.34, 1.2, 0.64, 1); }
@keyframes slideUp { from { opacity: 0; transform: translateY(20px) scale(0.98); } to { opacity: 1; transform: none; } }
.fade-enter-active { transition: opacity 0.2s ease-out; }
.fade-leave-active { transition: opacity 0.14s ease-in; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) {
  .modal-enter-active .modal-card, .switch-knob { animation: none; transition: none; }
}
</style>
