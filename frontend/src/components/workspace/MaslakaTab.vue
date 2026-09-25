<template>
  <div class="mk">
    <!-- Identity hero — same shape as the other tabs: copy at the start edge,
         looping deep-teal scene anchored to the inline-end. The art is
         absolutely positioned and TabHeroLoop removes itself entirely under
         prefers-reduced-motion, so the layout never depends on it. -->
    <header class="mk-hero">
      <div class="mk-hero-copy">
        <span class="mk-kicker">מסלקה פנסיונית</span>
        <h2 class="mk-hero-title"><span dir="ltr">Nifraim</span> <span class="mk-hero-title-acc">המסלקה</span></h2>
        <div class="mk-hero-meta">
          <span v-if="blocked && !loading" class="mk-chip mk-chip--wait">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor"
                 stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
            </svg>
            <span>{{ chipText }}</span>
          </span>
          <span v-else-if="!loading && assocLoaded" class="mk-chip mk-chip--live">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor"
                 stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M4 12h4l2.5-6 3 12L16 12h4" />
            </svg>
            <span>{{ inquiries.length ? `${inquiries.length} בקשות מידע` : 'מוכן לבקשת מידע' }}</span>
          </span>
          <!-- The association is the agent's to finish, so its next step lives
               here in the hero, not in a checklist card. -->
          <button
            v-if="needsAssoc && assoc && !loading && !wizardInline"
            class="mk-next"
            :class="{ 'mk-next--calm': assoc.status === 'submitted' && !assoc.reply_received_at }"
            type="button"
            @click="assocOpen = true"
          >
            <span>{{ assocCta }}</span>
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor"
                 stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M14 6 8 12l6 6" />
            </svg>
          </button>
          <!-- An approval the WATCHER decided stays inspectable: the agent is the
               person best placed to notice a misread reply. -->
          <button
            v-if="assoc?.status === 'approved' && assoc.decided_via === 'mailbox' && !loading"
            class="mk-why"
            type="button"
            @click="assocOpen = true"
          >איך זוהה האישור?</button>
          <span v-if="assocError" class="mk-hero-err">{{ assocError }}</span>
        </div>
      </div>
      <TabHeroLoop scene="maslaka" class="mk-hero-art" />
    </header>

    <!-- The agent still has to act (details / form / resend after a return):
         the wizard lives IN the page — it can't be dismissed into an empty tab,
         and the tab strip stays usable. -->
    <MaslakaAssociationModal
      v-if="wizardInline"
      inline
      open
      :assoc="assoc"
      @changed="loadAssociation"
    />
    <!-- Otherwise a popup, opened from the hero ("פרטי הבקשה" / "איך זוהה"). -->
    <MaslakaAssociationModal
      v-else
      :open="assocOpen"
      :assoc="assoc"
      @close="assocOpen = false"
      @changed="loadAssociation"
    />

    <!-- Service gate (ours: feature flag → 503 on /inquiries). The per-agent
         association gate is surfaced in the hero instead. -->
    <section v-if="gate && !loading" class="mk-card mk-gate">
      <h3 class="mk-card-title">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
             stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <path d="M12 9v4M12 17h.01" /><circle cx="12" cy="12" r="9" />
        </svg>
        <span>השירות עדיין לא פעיל</span>
      </h3>
      <p class="mk-gate-detail">{{ gate }}</p>
    </section>

    <!-- Waiting for the מסלקה to approve the שיוך: nothing below is usable
         yet, so it is hidden — one big clock says where things stand. -->
    <section v-if="needsAssoc && assoc?.status === 'submitted' && !loading" class="mk-card mk-wait">
      <svg class="mk-clock" viewBox="0 0 200 200" aria-hidden="true">
        <circle class="mk-clock-halo" cx="100" cy="100" r="92" />
        <circle class="mk-clock-face" cx="100" cy="100" r="78" />
        <g class="mk-clock-ticks">
          <line v-for="i in 12" :key="i" x1="100" y1="30" x2="100" :y2="i % 3 === 1 ? 44 : 38"
                :transform="`rotate(${(i - 1) * 30} 100 100)`" />
        </g>
        <line class="mk-clock-hour" x1="100" y1="100" x2="100" y2="62" />
        <line class="mk-clock-min" x1="100" y1="100" x2="100" y2="42" />
        <circle class="mk-clock-pin" cx="100" cy="100" r="6" />
      </svg>
      <p class="mk-wait-title">ממתין לאישור המסלקה</p>
      <p class="mk-wait-sub">נעדכן כאן ברגע שהאישור יגיע</p>
    </section>

    <template v-if="!needsAssoc">
      <!-- Request a customer's picture -->
      <section class="mk-card mk-ask" :class="{ 'mk-ask--off': blocked }">
        <div class="mk-ask-head">
          <h3 class="mk-card-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
            </svg>
            <span>חיפוש לקוח</span>
          </h3>
          <span class="mk-ask-note">
            מציג מיד את מה שכבר התקבל מהמסלקה. לקוח שעדיין לא במאגר — נשלחת עבורו בקשה, והתשובה מגיעה תוך כמה שעות.
          </span>
        </div>

        <div class="mk-fields">
          <div class="mk-field">
            <label for="mk-id">מספר זהות</label>
            <input
              id="mk-id"
              v-model="idNumber"
              dir="ltr"
              inputmode="numeric"
              autocomplete="off"
              placeholder="381788223"
              maxlength="9"
              :disabled="blocked"
              :aria-invalid="showIdError"
              :aria-describedby="showIdError ? 'mk-id-err' : 'mk-id-help'"
              @blur="idTouched = true"
              @keyup.enter="ask"
            />
            <span v-if="showIdError" id="mk-id-err" class="mk-help mk-help--bad">
              מספר זהות הוא 9 ספרות
            </span>
            <span v-else id="mk-id-help" class="mk-help">9 ספרות, כולל ספרת ביקורת</span>
          </div>

          <div class="mk-field">
            <label for="mk-name">שם הלקוח</label>
            <input
              id="mk-name"
              v-model="customerName"
              placeholder="לא חובה"
              autocomplete="off"
              :disabled="blocked"
              aria-describedby="mk-name-help"
              @keyup.enter="ask"
            />
            <span id="mk-name-help" class="mk-help">לזיהוי מהיר ברשימת הבקשות</span>
          </div>

          <button class="mk-primary" :disabled="!canAsk" @click="ask">
            <span v-if="busy" class="mk-btn-spinner" aria-hidden="true"></span>
            <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
                 stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M4 12h13" /><path d="m12 6 6 6-6 6" />
            </svg>
            <span>{{ busy ? 'מחפש…' : 'חפש לקוח' }}</span>
          </button>
        </div>

        <p v-if="blocked && !loading" class="mk-ask-blocked">
          {{ needsAssoc ? 'אפשר יהיה לשלוח בקשות אחרי שהמסלקה תאשר את השיוך.' : 'לא ניתן לשלוח בקשות עד שהשירות יופעל.' }}
        </p>
      </section>

      <p v-if="askNote" class="mk-help mk-ask-sent" role="status">{{ askNote }}</p>
      <p v-if="askError" class="mk-error" role="alert">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"
             stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="9" /><path d="M12 8v4M12 16h.01" />
        </svg>
        <span>{{ askError }}</span>
      </p>


      <!-- Production reports: the agent's whole book, per body — no ייפוי כוח needed -->
      <section v-if="!blocked && !loading" class="mk-card mk-prod">
        <div class="mk-ask-head">
          <h3 class="mk-card-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M3 3v18h18" /><path d="M7 15l4-4 3 3 5-6" />
            </svg>
            <span>דוחות פרודוקציה</span>
          </h3>
          <span class="mk-ask-note">
            כל הלקוחות שלך אצל הגופים שבחרת, בבקשה אחת לכל גוף. לא נדרש ייפוי כוח.
          </span>
        </div>
        <label v-if="assoc?.status === 'approved'" class="mk-auto">
          <input type="checkbox" :checked="!!assoc?.auto_production" :disabled="autoBusy" @change="toggleAuto" />
          <span>
            <strong>מנוי חודשי אוטומטי</strong> — גוף חדש שיופיע אצלך יתווסף לבד, והנתונים יגיעו עד ה-15 בכל חודש.
          </span>
        </label>

        <div class="mk-seg" role="radiogroup" aria-label="תדירות">
          <button type="button" role="radio" :aria-checked="prodFreq === 'once'"
                  :class="{ 'is-on': prodFreq === 'once' }" @click="prodFreq = 'once'">חד-פעמי</button>
          <button type="button" role="radio" :aria-checked="prodFreq === 'monthly'"
                  :class="{ 'is-on': prodFreq === 'monthly' }" @click="prodFreq = 'monthly'">מנוי חודשי</button>
        </div>
        <p class="mk-prod-terms" :class="{ 'mk-prod-terms--commit': prodFreq === 'monthly' }">
          <template v-if="prodFreq === 'once'">הדוח מגיע עד ה-15 בחודש הבא, עם נתונים לסוף החודש.</template>
          <template v-else>דוח חדש עד ה-15 בכל חודש. לפי כללי המסלקה, מנוי חודשי מחייב לפחות 5 חודשים.</template>
        </p>

        <div v-if="!prodBodies.length" class="mk-help">טוען גופים…</div>
        <ul v-else class="mk-bodies">
          <li v-for="b in visibleBodies" :key="b.id">
            <label class="mk-body" :class="{ 'is-off': bodyLocked(b) }">
              <input type="checkbox" :value="b.id" v-model="prodSel" :disabled="bodyLocked(b)" />
              <span class="mk-body-name">{{ b.name }}</span>
              <span class="mk-body-meta">
                <template v-if="bodyLocked(b)">מנוי פעיל</template>
                <template v-else-if="b.clients"><span class="ltr-number">{{ b.clients }}</span> לקוחות</template>
              </span>
            </label>
          </li>
        </ul>
        <button v-if="hiddenBodies" type="button" class="mk-link" @click="showAllBodies = !showAllBodies">
          {{ showAllBodies ? 'הצג רק גופים עם לקוחות' : `הצג עוד ${hiddenBodies} גופים` }}
        </button>

        <div class="mk-fields mk-prod-foot">
          <div class="mk-field">
            <label for="mk-asof">נכון לתאריך</label>
            <input id="mk-asof" v-model="prodDate" type="date" dir="ltr" aria-describedby="mk-asof-help" />
            <span id="mk-asof-help" class="mk-help">לא חובה. ריק = סוף החודש הנוכחי</span>
          </div>
          <button class="mk-primary" :disabled="!canSendProd" @click="sendProd">
            <span v-if="prodBusy" class="mk-btn-spinner" aria-hidden="true"></span>
            <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
                 stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M4 12h13" /><path d="m12 6 6 6-6 6" />
            </svg>
            <span>{{ prodButtonLabel }}</span>
          </button>
        </div>
        <p v-if="prodDone" class="mk-help mk-prod-done" role="status">{{ prodDone }}</p>
        <p v-if="prodError" class="mk-help mk-help--bad" role="alert">{{ prodError }}</p>
      </section>

      <!-- Inquiries -->
      <div v-if="loading" class="mk-loading"><div class="spinner"></div></div>

      <section v-else-if="!inquiries.length" class="mk-card mk-empty">
        <span class="mk-empty-art" aria-hidden="true">
          <svg viewBox="0 0 64 64" width="52" height="52" fill="none" stroke="currentColor"
               stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round">
            <rect x="12" y="10" width="40" height="44" rx="6" />
            <path d="M22 24h20M22 34h20M22 44h12" />
          </svg>
        </span>
        <p class="mk-empty-title">עדיין לא נשלחו בקשות מידע</p>
        <p class="mk-empty-note">
          הזינו מספר זהות של לקוח כדי למשוך את התמונה הפנסיונית המלאה שלו מכל הגופים המנהלים.
        </p>
      </section>

      <section v-else class="mk-card mk-list">
        <h3 class="mk-card-title">
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M4 7h16M4 12h16M4 17h10" />
          </svg>
          <span>בקשות מידע</span>
          <span class="mk-count ltr-number">{{ inquiries.length }}</span>
        </h3>
        <table class="mk-table">
          <thead>
            <tr>
              <th>לקוח</th><th>מספר זהות</th><th>סטטוס</th>
              <th>נשלח</th><th>גופים שהשיבו</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="q in inquiries" :key="q.id">
              <td class="mk-name">
                <span>{{ q.customer_name || '—' }}</span>
                <span v-if="kindLabel(q)" class="mk-kind">{{ kindLabel(q) }}</span>
              </td>
              <td><span class="ltr-number">{{ q.customer_id_number }}</span></td>
              <td>
                <span class="mk-status" :class="`mk-status--${q.status}`">
                  <span class="mk-status-dot" aria-hidden="true"></span>
                  <span>{{ statusLabel(q.status) }}</span>
                </span>
                <span v-if="expectedText(q)" class="mk-eta" :class="{ 'mk-eta--late': isLate(q) }">
                  {{ expectedText(q) }}
                </span>
              </td>
              <td><span class="ltr-number">{{ formatDate(q.submitted_at) }}</span></td>
              <td>
                <span class="mk-providers">
                  <span class="ltr-number">
                    {{ q.providers_received || 0 }}<template v-if="q.providers_expected">/{{ q.providers_expected }}</template>
                  </span>
                  <span v-if="q.providers_expected" class="mk-meter" aria-hidden="true">
                    <span class="mk-meter-fill" :style="{ width: providerPct(q) + '%' }"></span>
                  </span>
                </span>
              </td>
              <td class="mk-actions">
                <button class="mk-ghost" @click="openCustomer(q.customer_id_number)">
                  <span>הצג נתונים</span>
                  <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor"
                       stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M14 6 8 12l6 6" />
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </section>

      <!-- Holdings for one customer -->
      <p v-if="pictureError" class="mk-error" role="alert">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"
             stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="9" /><path d="M12 8v4M12 16h.01" />
        </svg>
        <span>{{ pictureError }}</span>
      </p>

      <section v-if="picture" class="mk-card mk-picture">
        <div class="mk-picture-head">
          <div>
            <h3 class="mk-picture-name">{{ picture.customer_name || picture.id_number }}</h3>
            <span class="mk-picture-sub">
              התמונה הפנסיונית שהתקבלה מהמסלקה<template v-if="picture.as_of">, נכון ל-<span class="ltr-number">{{ formatDate(picture.as_of) }}</span></template>
            </span>
          </div>
          <div class="mk-picture-actions">
          <button class="mk-ghost" :disabled="updateBusy || updateSent" @click="requestUpdate">
            <span>{{ updateSent ? 'נשלחה בקשת עדכון' : (updateBusy ? 'שולח…' : 'בקש עדכון מהמסלקה') }}</span>
          </button>
          <button class="mk-ghost" @click="picture = null">
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor"
                 stroke-width="2.2" stroke-linecap="round" aria-hidden="true">
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
            <span>סגור</span>
          </button>
          </div>
        </div>

        <div class="mk-kpis">
          <div class="mk-kpi">
            <span class="mk-kpi-n ltr-number">{{ money(picture.kpi?.total_accumulation) }}</span>
            <span class="mk-kpi-l">סך צבירה</span>
          </div>
          <div class="mk-kpi">
            <span class="mk-kpi-n ltr-number">{{ picture.kpi?.product_count ?? picture.products?.length ?? 0 }}</span>
            <span class="mk-kpi-l">מוצרים</span>
          </div>
          <div class="mk-kpi">
            <span class="mk-kpi-n ltr-number">{{ newToUs }}</span>
            <span class="mk-kpi-l">לא נמצאו אצלנו</span>
          </div>
        </div>

        <table class="mk-table mk-table--products">
          <thead>
            <tr><th>חברה</th><th>מוצר</th><th>מספר פוליסה</th><th>צבירה</th><th>סטטוס התאמה</th></tr>
          </thead>
          <tbody>
            <tr v-for="(p, i) in picture.products" :key="i">
              <td>{{ p.receiving_company || '—' }}</td>
              <td>{{ p.product || p.product_type || '—' }}</td>
              <td><span class="ltr-number">{{ p.fund_policy_number || '—' }}</span></td>
              <td><span class="ltr-number">{{ money(p.accumulation) }}</span></td>
              <td>
                <!-- icon + text, never colour alone -->
                <span class="mk-match" :class="p.match_status === 'matched' ? 'mk-match--ok' : 'mk-match--new'">
                  <svg v-if="p.match_status === 'matched'" viewBox="0 0 24 24" width="12" height="12" fill="none"
                       stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="m5 13 4 4L19 7" />
                  </svg>
                  <svg v-else viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor"
                       stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M12 5v14M5 12h14" />
                  </svg>
                  <span>{{ p.match_status === 'matched' ? 'תואם לפרודוקציה' : 'לא נמצא אצלנו' }}</span>
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </section>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '../../api/client.js'
import TabHeroLoop from './TabHeroLoop.vue'
import MaslakaAssociationModal from './MaslakaAssociationModal.vue'

const idNumber = ref('')
const customerName = ref('')
const idTouched = ref(false)
const inquiries = ref([])
const picture = ref(null)
const loading = ref(true)
const busy = ref(false)
const askError = ref('')
// Kept separate from askError: this one renders down beside the picture panel,
// where the row the user clicked is — the page is too tall for a top banner.
const pictureError = ref('')
const gate = ref('')

// ── Association (שיוך לבית תוכנה) ─────────────────────────────────────
// Server-side status is the only source of truth — nothing here is cached
// in localStorage.
const assoc = ref(null)
const assocError = ref('')
const assocOpen = ref(false)
const assocLoaded = ref(false)

const needsAssoc = computed(() => assocLoaded.value && assoc.value?.status !== 'approved')
// Statuses where the agent still has to act on the שיוך → wizard in the page.
const wizardInline = computed(() =>
  !!assoc.value && needsAssoc.value && ['not_started', 'form_downloaded', 'rejected'].includes(assoc.value.status))
const blocked = computed(() => !!gate.value || needsAssoc.value)

const chipText = computed(() => {
  if (needsAssoc.value) {
    const st = assoc.value?.status
    if (st === 'submitted') return assoc.value?.reply_received_at ? 'התקבלה תשובה מהמסלקה' : 'ממתין לאישור המסלקה'
    if (st === 'rejected') return 'המסלקה החזירה את הטופס'
    return 'נדרש חיבור למסלקה'
  }
  return 'השירות עדיין לא פעיל'
})

const assocCta = computed(() => {
  const a = assoc.value
  if (!a || !a.agent_id_number) return 'התחלת החיבור'
  if (a.status === 'submitted') return a.reply_received_at ? 'לקריאת התשובה' : 'פרטי הבקשה'
  if (a.status === 'rejected') return 'תיקון ושליחה מחדש'
  return 'המשך בחיבור'
})

async function loadAssociation() {
  try {
    const { data } = await api.get('/maslaka/association')
    assoc.value = data
    assocError.value = ''
  } catch {
    // Fail closed: if we cannot confirm the association, the ask form stays off.
    assoc.value = null
    assocError.value = 'לא הצלחנו לבדוק את מצב החיבור למסלקה. רעננו את הדף ונסו שוב.'
  } finally {
    assocLoaded.value = true
  }
}

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

// Request type, from the action code the server records (events_v007:<code>).
const KIND = { '9100': 'מידע על לקוח', '9101': 'מידע על לקוח', '2000': 'דוח פרודוקציה', '2100': 'דוח פרודוקציה חודשי' }
function kindLabel(q) { return KIND[(q.interface_code || '').split(':')[1]] || '' }

// When the answer is due under Swiftness's rules — computed by the server
// (expected_by). "Now" ticks every minute so a row turns late on its own.
const nowTs = ref(Date.now())
function isLate(q) {
  return !!q.expected_by && !(q.providers_received > 0) && nowTs.value > new Date(q.expected_by).getTime()
}
function expectedText(q) {
  if (!q.expected_by || q.providers_received > 0) return ''
  const due = new Date(q.expected_by)
  if (isLate(q)) return 'חלף הזמן הצפוי'
  if (q.expected_basis === 'production_15th') return `מועד אחרון לפי כללי המסלקה: ${due.toLocaleDateString('he-IL')}`
  const sameDay = due.toDateString() === new Date(nowTs.value).toDateString()
  const hhmm = due.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })
  return sameDay ? `מידע צפוי עד ${hhmm} היום` : `מידע צפוי עד ${due.toLocaleDateString('he-IL')} ${hhmm}`
}

const idDigits = computed(() => idNumber.value.replace(/\D/g, ''))
const idValid = computed(() => idDigits.value.length === 9)
// Validate on blur, not on keystroke — no error while the user is still typing.
const showIdError = computed(() => idTouched.value && !!idNumber.value && !idValid.value)
const canAsk = computed(() => !blocked.value && idValid.value && !busy.value)
const newToUs = computed(
  () => (picture.value?.products || []).filter((p) => p.match_status !== 'matched').length,
)

function providerPct(q) {
  if (!q.providers_expected) return 0
  return Math.min(100, Math.round(((q.providers_received || 0) / q.providers_expected) * 100))
}

function money(v) {
  const n = Number(v || 0)
  return n ? n.toLocaleString('he-IL', { maximumFractionDigits: 0 }) : '—'
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('he-IL')
}

async function loadInquiries({ silent = false } = {}) {
  // The minute refresh is silent: flipping `loading` would swap the table for
  // a spinner every 60s.
  if (!silent) loading.value = true
  try {
    const { data } = await api.get('/maslaka/inquiries')
    inquiries.value = data
  } catch (e) {
    // A 503 here means the feature is gated, not that the request failed.
    if (e?.response?.status === 503) gate.value = e.response.data.detail
  } finally {
    if (!silent) loading.value = false
  }
}


// ── Production reports (2000 one-off / 2100 monthly), one request per body ──
const prodBodies = ref([])
const prodSel = ref([])
const prodFreq = ref('once')
const prodDate = ref('')
const prodBusy = ref(false)
const prodError = ref('')
const prodDone = ref('')
const showAllBodies = ref(false)

const visibleBodies = computed(() =>
  showAllBodies.value ? prodBodies.value : prodBodies.value.filter((b) => b.clients > 0 || prodSel.value.includes(b.id)),
)
const hiddenBodies = computed(() => prodBodies.value.length - prodBodies.value.filter((b) => b.clients > 0).length)
// A body that already has an open monthly subscription can't get a second one.
function bodyLocked(b) { return prodFreq.value === 'monthly' && b.monthly }
const prodTargets = computed(() => prodSel.value.filter((id) => {
  const b = prodBodies.value.find((x) => x.id === id)
  return b && !bodyLocked(b)
}))
const canSendProd = computed(() => !blocked.value && !prodBusy.value && prodTargets.value.length > 0)
const prodButtonLabel = computed(() => {
  if (prodBusy.value) return 'שולח…'
  const n = prodTargets.value.length
  if (prodFreq.value === 'monthly') return n === 1 ? 'הרשמה למנוי לגוף אחד' : `הרשמה למנוי ל-${n} גופים`
  return n === 1 ? 'בקש דוח מגוף אחד' : `בקש דוחות מ-${n} גופים`
})

async function loadProdBodies() {
  try {
    const { data } = await api.get('/maslaka/production-report/bodies')
    prodBodies.value = data
    if (!prodSel.value.length) prodSel.value = data.filter((b) => b.clients > 0).map((b) => b.id)
  } catch {
    prodBodies.value = []
  }
}

async function sendProd() {
  if (!canSendProd.value) return
  prodError.value = ''
  prodDone.value = ''
  prodBusy.value = true
  try {
    const { data } = await api.post('/maslaka/production-report', {
      yatzran_ids: prodTargets.value,
      frequency: prodFreq.value,
      information_date: prodDate.value ? prodDate.value.replaceAll('-', '') : null,
    })
    const n = data.length
    prodDone.value = prodFreq.value === 'monthly'
      ? (n === 1 ? 'נרשם מנוי חודשי לגוף אחד.' : `נרשם מנוי חודשי ל-${n} גופים.`) + ' הבקשות מופיעות ברשימה למטה.'
      : (n === 1 ? 'נשלחה בקשה אחת.' : `נשלחו ${n} בקשות.`) + ' הן מופיעות ברשימה למטה.'
    await Promise.all([loadInquiries({ silent: true }), loadProdBodies()])
  } catch (e) {
    prodError.value = e?.response?.data?.detail || 'השליחה נכשלה. נסו שוב.'
  } finally {
    prodBusy.value = false
  }
}

const askNote = ref('')
const updateBusy = ref(false)
const updateSent = ref(false)

// Search is DB-first: show what the monthly production files and earlier
// answers already brought in, instantly. Only a customer we have nothing on
// triggers a 9100 to the מסלקה (answer within hours).
async function ask() {
  if (!canAsk.value) return
  askError.value = ''
  askNote.value = ''
  busy.value = true
  const id = idDigits.value
  const name = customerName.value.trim() || null
  try {
    try {
      const { data } = await api.get(`/maslaka/customer/${encodeURIComponent(id)}`)
      picture.value = data
      pictureError.value = ''
      updateSent.value = false
      idNumber.value = ''
      customerName.value = ''
      idTouched.value = false
      return
    } catch (e) {
      if (e?.response?.status !== 404) throw e
    }
    await api.post('/maslaka/inquiry', { customer_id_number: id, customer_name: name })
    askNote.value = 'הלקוח עדיין לא במאגר — נשלחה בקשה למסלקה. התשובה צפויה תוך כמה שעות, והיא תופיע ברשימה למטה.'
    idNumber.value = ''
    customerName.value = ''
    idTouched.value = false
    await loadInquiries({ silent: true })
  } catch (e) {
    // 403 + X-Maslaka-Association-Status: the server's association gate held
    // (status changed under the tab, e.g. an approval was revoked). Re-read the
    // truth so the card and wizard reflect it, not just an error line.
    if (e?.response?.status === 403 && e.response.headers?.['x-maslaka-association-status']) {
      await loadAssociation()
    }
    askError.value = e?.response?.data?.detail || 'החיפוש נכשל'
  } finally {
    busy.value = false
  }
}

async function requestUpdate() {
  if (!picture.value || updateBusy.value) return
  updateBusy.value = true
  try {
    await api.post('/maslaka/inquiry', {
      customer_id_number: picture.value.id_number,
      customer_name: picture.value.customer_name || null,
    })
    updateSent.value = true
    await loadInquiries({ silent: true })
  } catch (e) {
    pictureError.value = e?.response?.data?.detail || 'שליחת בקשת העדכון נכשלה'
  } finally {
    updateBusy.value = false
  }
}

// Automatic monthly production (consent on the שיוך form; switchable here).
const autoBusy = ref(false)
async function toggleAuto(ev) {
  const enabled = ev.target.checked
  autoBusy.value = true
  prodError.value = ''
  try {
    const { data } = await api.post('/maslaka/association/auto-production', { enabled })
    if (assoc.value) assoc.value.auto_production = data.auto_production
    if (data.created) {
      prodDone.value = `נפתחו ${data.created} מנויים חודשיים חדשים.`
      await Promise.all([loadInquiries({ silent: true }), loadProdBodies()])
    }
  } catch (e) {
    ev.target.checked = !enabled
    prodError.value = e?.response?.data?.detail || 'השינוי נכשל'
  } finally {
    autoBusy.value = false
  }
}

async function openCustomer(id) {
  picture.value = null
  pictureError.value = ''
  try {
    const { data } = await api.get(`/maslaka/customer/${encodeURIComponent(id)}`)
    picture.value = data
  } catch (e) {
    pictureError.value = e?.response?.status === 404
      ? 'עדיין לא התקבלו נתונים עבור הלקוח הזה'
      : 'שגיאה בטעינת הנתונים'
  }
}

const OPEN = new Set(['pending', 'submitted', 'acknowledged', 'partial'])
let refreshTimer = null
function startRefresh() {
  refreshTimer = setInterval(() => {
    nowTs.value = Date.now()
    if (inquiries.value.some((q) => OPEN.has(q.status))) loadInquiries({ silent: true })
  }, 60000)
}
onUnmounted(() => { if (refreshTimer) clearInterval(refreshTimer) })

onMounted(async () => {
  startRefresh()
  loadProdBodies()
  await Promise.all([loadInquiries(), loadAssociation()])
})
</script>

<style scoped>
.mk {
  display: flex;
  flex-direction: column;
  gap: 16px;
  /* Derived from App.vue tokens — nothing below hardcodes a colour. */
  --mk-accent-12: color-mix(in srgb, var(--tab-maslaka) 12%, transparent);
  --mk-accent-22: color-mix(in srgb, var(--tab-maslaka) 22%, transparent);
  --mk-accent-30: color-mix(in srgb, var(--tab-maslaka) 30%, transparent);
  /* text-safe amber ink: 6.2:1 on --amber-light, 6.8:1 on white */
  --mk-amber-ink: color-mix(in srgb, var(--amber) 62%, #000);
  /* --green on --green-light is 4.2:1 — under AA for a 12px pill. This is 5.8:1. */
  --mk-green-ink: color-mix(in srgb, var(--green) 82%, #000);
}

/* ── Hero ───────────────────────────────────────────────────── */
.mk-hero {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  min-height: 158px;
  padding: 20px 24px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}
.mk-hero::before {
  content: '';
  position: absolute;
  inset-inline-end: -6%;
  top: -60%;
  width: 44%;
  height: 220%;
  background: radial-gradient(circle, var(--tab-maslaka-wash), transparent 70%);
  pointer-events: none;
}
.mk-hero-copy {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
  max-width: 62%;
}
.mk-kicker {
  align-self: flex-start;
  padding: 4px 11px;
  border-radius: 999px;
  background: var(--tab-maslaka-wash);
  color: var(--tab-maslaka);
  font-size: 11.5px;
  font-weight: 800;
  letter-spacing: 0.03em;
}
.mk-hero-title {
  margin: 2px 0 0;
  font-size: clamp(19px, 2.2vw, 24px);
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.2;
  color: var(--text);
}
/* Wordmark — Rubik, same as the Mail Agent's "Nifraim Mail Agent". */
.mk-hero-title {
  font-family: 'Rubik', 'Heebo', sans-serif;
  font-size: clamp(28px, 3.3vw, 40px);
  font-weight: 700;
  letter-spacing: -0.03em;
  line-height: 1.05;
}
.mk-hero-title-acc { color: var(--tab-maslaka); }

/* ── Waiting for approval: one extra-big clock ─────────────── */
.mk-wait {
  display: flex; flex-direction: column; align-items: center; text-align: center;
  padding: 36px 20px 40px; gap: 6px;
}
.mk-clock { width: min(260px, 60vw); height: auto; overflow: visible; }
.mk-clock-halo { fill: var(--tab-maslaka-wash); transform-origin: 100px 100px; animation: mk-halo 3s ease-in-out infinite; }
.mk-clock-face { fill: var(--card-bg); stroke: var(--tab-maslaka); stroke-width: 5; }
.mk-clock-ticks line { stroke: var(--mk-accent-30); stroke-width: 4; stroke-linecap: round; }
.mk-clock-hour, .mk-clock-min { stroke: var(--tab-maslaka); stroke-linecap: round; transform-origin: 100px 100px; }
.mk-clock-hour { stroke-width: 8; animation: mk-spin-hand 48s linear infinite; }
.mk-clock-min { stroke-width: 5; animation: mk-spin-hand 4s linear infinite; }
.mk-clock-pin { fill: var(--tab-maslaka); }
@keyframes mk-spin-hand { to { transform: rotate(360deg); } }
@keyframes mk-halo { 50% { transform: scale(1.06); opacity: 0.6; } }
.mk-wait-title { margin: 14px 0 0; font-size: 24px; font-weight: 800; color: var(--text); }
.mk-wait-sub { margin: 0; font-size: 14px; color: var(--text-muted); }
@media (prefers-reduced-motion: reduce) {
  .mk-clock-halo, .mk-clock-hour, .mk-clock-min { animation: none; }
  .mk-clock-hour { transform: rotate(300deg); }
}
.mk-hero-meta { margin-top: 6px; display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.mk-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
}
.mk-chip--live {
  background: var(--tab-maslaka-wash);
  color: var(--tab-maslaka);
  border-color: var(--mk-accent-22);
}
.mk-chip--wait {
  background: var(--amber-light);
  color: var(--mk-amber-ink);
  border-color: color-mix(in srgb, var(--amber) 30%, transparent);
}
.mk-hero-art {
  position: absolute;
  inset-inline-end: 4px;
  top: 50%;
  transform: translateY(-50%);
  width: min(260px, 36%);
  aspect-ratio: 420 / 300;
  pointer-events: none;
  z-index: 0;
}
@media (max-width: 720px) {
  .mk-hero-art { display: none; }
  .mk-hero-copy { max-width: none; }
}

/* ── Card shell ─────────────────────────────────────────────── */
.mk-card {
  padding: 18px 20px;
  background: var(--card-bg);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm);
}
.mk-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--text);
}
.mk-card-title svg { color: var(--tab-maslaka); flex-shrink: 0; }
.mk-count {
  margin-inline-start: auto;
  padding: 2px 9px;
  border-radius: 999px;
  background: var(--tab-maslaka-wash);
  color: var(--tab-maslaka);
  font-size: 0.78rem;
  font-weight: 700;
}

/* ── Gate ───────────────────────────────────────────────────── */
.mk-gate { border-inline-start: 3px solid var(--amber); }
.mk-gate .mk-card-title svg { color: var(--amber); }
.mk-gate-detail {
  margin: 0 0 12px;
  font-size: 0.86rem;
  line-height: 1.65;
  color: var(--text-secondary);
}
.mk-steps { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 8px; }
.mk-step {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: var(--radius-sm);
  background: var(--bg);
  font-size: 0.84rem;
  line-height: 1.5;
  color: var(--text-secondary);
}
.mk-step-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  flex-shrink: 0;
}
.mk-step-text { min-width: 0; }
.mk-step-tag {
  margin-inline-start: auto;
  flex-shrink: 0;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
}
.mk-step--done .mk-step-mark { background: var(--green-light); color: var(--mk-green-ink); }
.mk-step--done .mk-step-tag { background: var(--green-light); color: var(--mk-green-ink); }
.mk-step--wait .mk-step-mark { background: var(--amber-light); color: var(--mk-amber-ink); }
.mk-step--wait .mk-step-tag { background: var(--amber-light); color: var(--mk-amber-ink); }
.mk-step--req .mk-step-mark { background: var(--tab-maslaka-wash); color: var(--tab-maslaka); }
.mk-step--req .mk-step-tag { background: var(--tab-maslaka-wash); color: var(--tab-maslaka); }
.mk-hero-err { font-size: 0.78rem; font-weight: 600; color: var(--red-deep); }
.mk-next {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 14px;
  font-family: inherit;
  font-size: 12.5px;
  font-weight: 700;
  color: #fff;
  background: var(--tab-maslaka);
  border: none;
  border-radius: 999px;
  cursor: pointer;
  transition: filter 0.15s var(--transition), transform 0.15s var(--transition);
}
/* A ring that breathes out from the button — asks for the click without
   moving the text. Calmed once the agent is only waiting on the מסלקה. */
.mk-next::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: inherit;
  box-shadow: 0 0 0 0 color-mix(in srgb, var(--tab-maslaka) 45%, transparent);
  animation: mk-next-pulse 2.2s ease-out infinite;
  pointer-events: none;
}
.mk-next--calm::after { animation: none; }
.mk-why {
  padding: 0;
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  color: var(--tab-maslaka);
  background: none;
  border: none;
  text-decoration: underline;
  text-underline-offset: 3px;
  cursor: pointer;
}
.mk-why:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }
.mk-next svg { transition: transform 0.2s var(--transition); }
.mk-next:hover { filter: brightness(1.12); }
.mk-next:hover svg { transform: translateX(-3px); }
.mk-next:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 3px; }
@keyframes mk-next-pulse {
  0% { box-shadow: 0 0 0 0 color-mix(in srgb, var(--tab-maslaka) 45%, transparent); }
  70%, 100% { box-shadow: 0 0 0 10px color-mix(in srgb, var(--tab-maslaka) 0%, transparent); }
}
@media (prefers-reduced-motion: reduce) {
  .mk-next::after { animation: none; }
  .mk-next svg { transition: none; }
}

/* ── Ask form ───────────────────────────────────────────────── */
.mk-ask-head { display: flex; flex-direction: column; gap: 2px; margin-bottom: 14px; }
.mk-ask-head .mk-card-title { margin: 0; }
.mk-ask-note { font-size: 0.8rem; line-height: 1.55; color: var(--text-muted); max-width: 70ch; }
.mk-fields { display: flex; flex-wrap: wrap; gap: 14px; align-items: flex-start; }
.mk-field { display: flex; flex-direction: column; gap: 5px; min-width: 190px; }
.mk-field label { font-size: 0.78rem; font-weight: 600; color: var(--text-secondary); }
.mk-field input {
  height: 42px;
  padding: 0 12px;
  font-family: inherit;
  font-size: 0.9rem;
  color: var(--text);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  transition: border-color 0.16s var(--transition), box-shadow 0.16s var(--transition);
}
.mk-field input::placeholder { color: color-mix(in srgb, var(--text-muted) 68%, #fff); }
.mk-field input:hover:not(:disabled) { border-color: var(--tab-maslaka); }
.mk-field input:focus {
  outline: none;
  border-color: var(--tab-maslaka);
  box-shadow: 0 0 0 3px var(--tab-maslaka-wash);
}
.mk-field input:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 1px; }
.mk-field input:disabled { background: var(--bg); color: var(--text-muted); cursor: not-allowed; opacity: 0.7; }
.mk-field input[aria-invalid='true'] { border-color: var(--red-deep); }
.mk-help { font-size: 0.72rem; line-height: 1.4; color: var(--text-muted); }
.mk-help--bad { color: var(--red-deep); font-weight: 600; }

.mk-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 42px;
  margin-top: 22px;
  padding: 0 22px;
  font-family: inherit;
  font-size: 0.88rem;
  font-weight: 700;
  color: #fff;
  background: var(--tab-maslaka);
  border: 1px solid var(--tab-maslaka);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: transform 0.15s var(--transition), box-shadow 0.15s var(--transition), filter 0.15s var(--transition);
}
.mk-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  filter: brightness(1.1);
  box-shadow: 0 6px 16px color-mix(in srgb, var(--tab-maslaka) 26%, transparent);
}
.mk-primary:active:not(:disabled) { transform: translateY(0); }
.mk-primary:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }
.mk-primary:disabled { opacity: 0.45; cursor: not-allowed; }
.mk-btn-spinner {
  width: 14px; height: 14px; flex-shrink: 0;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: mk-spin 0.8s linear infinite;
}
@keyframes mk-spin { to { transform: rotate(360deg); } }

.mk-ask--off { background: var(--bg); }
.mk-ask-blocked {
  margin: 12px 0 0;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--mk-amber-ink);
}

/* ── Error ──────────────────────────────────────────────────── */
.mk-error {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  padding: 11px 14px;
  font-size: 0.85rem;
  color: var(--red-deep);
  background: var(--red-light);
  border: 1px solid color-mix(in srgb, var(--red-deep) 25%, transparent);
  border-radius: var(--radius-sm);
}
.mk-error svg { flex-shrink: 0; }

/* ── Tables ─────────────────────────────────────────────────── */
.mk-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; table-layout: fixed; }
.mk-table th, .mk-table td {
  padding: 10px; border-bottom: 1px solid var(--border-subtle); text-align: right;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.mk-table thead th {
  font-size: 0.75rem; font-weight: 700; color: var(--text-muted);
  border-bottom-color: var(--border);
}
.mk-table tbody tr { transition: background 0.14s var(--transition); }
.mk-table tbody tr:hover { background: var(--tab-maslaka-wash); }
.mk-table tbody tr:last-child td { border-bottom: none; }
.mk-name { font-weight: 600; color: var(--text); }
.mk-name > span:first-child { display: block; }
.mk-kind {
  display: inline-block; margin-top: 3px;
  font-size: 0.7rem; font-weight: 500; color: var(--text-secondary);
}
.mk-eta {
  display: block; margin: 4px auto 0; max-width: 170px;
  font-size: 0.72rem; line-height: 1.35; color: var(--text-secondary);
  white-space: normal;
}
.mk-eta--late { color: var(--red-deep); font-weight: 600; }
.mk-table td:nth-child(2), .mk-table td:nth-child(4), .mk-table td:nth-child(5),
.mk-table th:nth-child(2), .mk-table th:nth-child(4), .mk-table th:nth-child(5) {
  text-align: center; width: 100px;
}
.mk-table--products td:nth-child(3), .mk-table--products td:nth-child(4),
.mk-table--products th:nth-child(3), .mk-table--products th:nth-child(4) {
  text-align: center; width: 110px;
}
.mk-table--products td:nth-child(2), .mk-table--products th:nth-child(2) { text-align: right; width: auto; }
/* fixed layout: pin the status column too, so the pill can't be squeezed into
   an ellipsis at narrow widths — the name column absorbs the slack instead */
.mk-list .mk-table td:nth-child(3), .mk-list .mk-table th:nth-child(3) { width: 150px; }
.mk-table--products td:nth-child(5), .mk-table--products th:nth-child(5) { text-align: right; width: 150px; }

.mk-status {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 10px; border-radius: 999px; font-size: 0.76rem; font-weight: 600;
}
.mk-status-dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex-shrink: 0; }
/* --gray on this wash is 4.3:1 — under AA at 12px. --text-secondary is 10.9:1. */
.mk-status--pending {
  background: color-mix(in srgb, var(--text-muted) 14%, transparent);
  color: var(--text-secondary);
}
.mk-status--submitted, .mk-status--acknowledged, .mk-status--partial {
  /* chart-9 itself is only 4.2:1 on its own 10% wash — darken the ink, keep the hue */
  background: color-mix(in srgb, var(--chart-9) 10%, transparent);
  color: color-mix(in srgb, var(--chart-9) 78%, #000);
}
.mk-status--complete { background: var(--green-light); color: var(--mk-green-ink); }
.mk-status--failed, .mk-status--expired { background: var(--red-light); color: var(--red-deep); }

.mk-providers { display: inline-flex; flex-direction: column; align-items: center; gap: 4px; }
.mk-meter {
  display: block; width: 62px; height: 4px; border-radius: 2px;
  background: var(--mk-accent-12); overflow: hidden;
}
.mk-meter-fill { display: block; height: 100%; background: var(--tab-maslaka); border-radius: 2px; }

/* holds a button, not text — never let the cell ellipsis it */
.mk-table td.mk-actions { text-align: left; width: 140px; overflow: visible; text-overflow: clip; }
.mk-ghost {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 6px 11px; font-family: inherit; font-size: 0.8rem; font-weight: 600;
  color: var(--tab-maslaka); background: transparent;
  border: 1px solid var(--mk-accent-30); border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.15s var(--transition), border-color 0.15s var(--transition);
}
.mk-ghost:hover { background: var(--tab-maslaka-wash); border-color: var(--tab-maslaka); }
.mk-ghost:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }

/* ── Empty ──────────────────────────────────────────────────── */
.mk-empty { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 40px 20px; text-align: center; }
.mk-empty-art {
  display: inline-flex; align-items: center; justify-content: center;
  width: 78px; height: 78px; margin-bottom: 4px;
  border-radius: 50%; background: var(--tab-maslaka-wash); color: var(--tab-maslaka);
}
.mk-empty-title { margin: 0; font-size: 0.95rem; font-weight: 700; color: var(--text); }
.mk-empty-note { margin: 0; max-width: 52ch; font-size: 0.83rem; line-height: 1.6; color: var(--text-muted); }

/* ── Customer picture ───────────────────────────────────────── */
.mk-picture-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.mk-picture-name { margin: 0 0 2px; font-size: 1.02rem; font-weight: 700; color: var(--text); }
.mk-picture-sub { font-size: 0.78rem; color: var(--text-muted); }
.mk-kpis { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 16px; }
.mk-kpi {
  flex: 1 1 140px; display: flex; flex-direction: column; gap: 3px;
  padding: 12px 14px; background: var(--bg);
  border: 1px solid var(--border-subtle); border-radius: var(--radius-sm);
  border-top: 3px solid var(--tab-maslaka);
}
.mk-kpi-n { font-size: 1.3rem; font-weight: 800; color: var(--text); font-variant-numeric: tabular-nums; }
.mk-kpi-l { font-size: 0.74rem; color: var(--text-muted); }

.mk-match { display: inline-flex; align-items: center; gap: 5px; font-size: 0.78rem; font-weight: 600; }
.mk-match--ok { color: var(--green); }
.mk-match--new { color: var(--tab-maslaka); }

.mk-loading { display: flex; justify-content: center; padding: 44px; }

@media (prefers-reduced-motion: reduce) {
  .mk-btn-spinner { animation: none; }
  .mk-primary, .mk-field input, .mk-ghost, .mk-table tbody tr { transition: none; }
  .mk-primary:hover:not(:disabled) { transform: none; }
}

/* ── Production reports ── */
.mk-seg {
  display: inline-flex; padding: 3px; gap: 3px; margin-bottom: 8px;
  border: 1px solid var(--border); border-radius: 999px; background: var(--bg);
}
.mk-seg button {
  border: 0; background: transparent; cursor: pointer; font: inherit;
  font-size: 0.8rem; font-weight: 600; color: var(--text-secondary);
  padding: 6px 16px; border-radius: 999px;
}
.mk-seg button.is-on { background: var(--tab-maslaka); color: #fff; }
.mk-seg button:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 1px; }
.mk-prod-terms { margin: 0 0 14px; font-size: 0.8rem; color: var(--text-muted); }
.mk-prod-terms--commit {
  color: var(--text); font-weight: 600;
  padding: 8px 12px; border-radius: 8px;
  border-inline-start: 3px solid var(--tab-maslaka);
  background: color-mix(in srgb, var(--tab-maslaka) 8%, transparent);
}
.mk-bodies {
  list-style: none; margin: 0 0 8px; padding: 0;
  display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 6px;
}
.mk-body {
  display: flex; align-items: center; gap: 8px; cursor: pointer;
  padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px;
}
.mk-body:hover { border-color: var(--tab-maslaka); }
.mk-body:has(input:checked) { border-color: var(--tab-maslaka); background: color-mix(in srgb, var(--tab-maslaka) 6%, transparent); }
.mk-body.is-off { cursor: not-allowed; opacity: 0.6; }
.mk-body input { accent-color: var(--tab-maslaka); margin: 0; flex-shrink: 0; }
.mk-body-name { font-size: 0.82rem; color: var(--text); flex: 1; min-width: 0; }
.mk-body-meta { font-size: 0.72rem; color: var(--text-muted); white-space: nowrap; }
.mk-link {
  border: 0; background: none; padding: 0; cursor: pointer; font: inherit;
  font-size: 0.78rem; color: var(--tab-maslaka); text-decoration: underline;
}
.mk-link:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }
.mk-prod-foot { margin-top: 14px; align-items: flex-end; }
.mk-prod-done { color: var(--text); margin-top: 10px; }
.mk-ask-sent { color: var(--text); margin-top: 8px; }
.mk-auto {
  display: flex; gap: 8px; align-items: flex-start; margin: 0 0 12px; cursor: pointer;
  font-size: 0.8rem; line-height: 1.5; color: var(--text-secondary);
}
.mk-auto strong { color: var(--text); font-weight: 600; }
.mk-auto input { accent-color: var(--tab-maslaka); margin-top: 3px; }
.mk-picture-actions { display: flex; gap: 8px; align-items: center; }
</style>
