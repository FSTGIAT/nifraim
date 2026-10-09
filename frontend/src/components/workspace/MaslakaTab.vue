<template>
  <div class="mk">
    <!-- Remotion: the insurers' files flowing through the clearinghouse into the
         agent's file — very faint, decorative only (family of the automation
         gears and the portal connections). -->
    <div v-if="!reducedMotion" class="mk-bg" aria-hidden="true">
      <div ref="bgEl" class="mk-bg-mount"></div>
    </div>
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
        <!-- the agent's dates: signup, שיוך submitted/approved, first production -->
        <div v-if="masLine" class="mk-dates" :title="MASLAKA_RULE">
          <span v-if="signup" class="mk-date">{{ signup }}</span>
          <span class="mk-date" :class="'mk-date--' + masLine.tone"><strong>{{ masLine.title }}</strong><template v-if="masLine.sub"> · {{ masLine.sub }}</template></span>
          <span class="mk-rule">{{ MASLAKA_RULE }}</span>
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
      <section ref="askCardEl" class="mk-card mk-ask" :class="{ 'mk-ask--off': blocked }">
        <div class="mk-ask-head">
          <h3 class="mk-card-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
            </svg>
            <span>חיפוש לקוח</span>
          </h3>
          <span class="mk-ask-note">
            כל המידע הפנסיוני של הלקוח, מכל הגופים.
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
              autocomplete="off"
              :disabled="blocked"
              aria-describedby="mk-name-help"
              @keyup.enter="ask"
            />
            <span id="mk-name-help" class="mk-help">לא חובה</span>
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

      <p v-if="askError" class="mk-error" role="alert">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"
             stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="9" /><path d="M12 8v4M12 16h.01" />
        </svg>
        <span>{{ askError }}</span>
      </p>


      <!-- Production files from the מסלקה: what arrived, the current one, what's next -->
      <section v-if="!loading" class="mk-card mk-files">
        <div class="mk-ask-head">
          <h3 class="mk-card-title">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" />
            </svg>
            <span>קבצי פרודוקציה מהמסלקה</span>
          </h3>
        </div>

        <div class="mk-files-grid" :class="{ 'mk-files-grid--cov': cov?.summary }">
        <ol class="mk-timeline">
          <!-- What's next: the next file, and the cycle that uses it -->
          <li class="mk-tl mk-tl--next">
            <span class="mk-tl-dot" aria-hidden="true"></span>
            <div class="mk-tl-body">
              <span class="mk-tl-kicker">הקובץ הבא</span>
              <strong class="mk-tl-title">עד <span class="ltr-number">{{ shortDay(nextDue) }}</span></strong>
              <span v-if="nextCycleLabel" class="mk-tl-meta">המחזור הבא <span class="ltr-number">{{ nextCycleLabel }}</span></span>
            </div>
          </li>
          <li
            v-for="(f, i) in files.files"
            :key="f.period"
            class="mk-tl"
            :class="{ 'mk-tl--current': i === 0 }"
          >
            <span class="mk-tl-dot" aria-hidden="true">
              <svg viewBox="0 0 24 24" width="10" height="10" fill="none" stroke="currentColor"
                   stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"><path d="m5 13 4 4L19 7" /></svg>
            </span>
            <div class="mk-tl-body">
              <span class="mk-tl-kicker">{{ i === 0 ? 'הקובץ הנוכחי' : 'הורד' }}</span>
              <strong class="mk-tl-title">{{ monthLabel(f.period) }}</strong>
              <span class="mk-tl-meta">
                <template v-if="f.received_at">הגיע ב-<span class="ltr-number">{{ shortDay(f.received_at) }}</span> · </template>
                <span class="ltr-number">{{ f.customers }}</span> לקוחות
              </span>
              <!-- what changed in this file — opens the delta drill (MaslakaDeltaDrill) -->
              <button
                v-if="deltas[f.as_of]" type="button" class="mk-tl-delta"
                @click="openDelta(f.as_of, $event.currentTarget)"
              >
                <span>מה השתנה</span>
                <span class="mk-tl-delta-n">
                  <span class="ltr-number">{{ deltas[f.as_of].new_count }}</span> חדשים ·
                  <span class="ltr-number">{{ deltas[f.as_of].removed_count }}</span> הוסרו ·
                  <span class="ltr-number">{{ deltas[f.as_of].changed_count }}</span> השתנו
                </span>
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
              </button>
            </div>
          </li>
          <li v-if="!files.files.length" class="mk-tl mk-tl--empty">
            <span class="mk-tl-dot" aria-hidden="true"></span>
            <div class="mk-tl-body">
              <span class="mk-tl-meta">עדיין לא הגיעו קבצים</span>
            </div>
          </li>
        </ol>

        <!-- The current file against the agent's production: who is already
             אצלך and who is not, per company. Bars grow in once loaded; the two
             counts, every bar and every segment drill (MaslakaCoverageDrill). -->
        <div v-if="cov?.summary" ref="covEl" class="mk-cov" :class="{ 'mk-cov--in': covGrown }">
          <div class="mk-cov-head">
            <span class="mk-tl-kicker">{{ monthLabel(cov.as_of) }} מול הפרודוקציה שלך</span>
          </div>
          <div class="mk-cov-kpis">
            <button type="button" class="mk-cov-kpi" @click="openCov('in', '', $event.currentTarget)">
              <span class="mk-cov-kpi-l"><i class="mk-cov-sw mk-cov-sw--in" aria-hidden="true"></i>אצלך</span>
              <strong class="mk-cov-kpi-n ltr-number">{{ num(covShown.in) }}</strong>
              <span class="mk-cov-kpi-s">לקוחות · <span class="ltr-number">{{ num(cov.summary.in_products) }}</span> מוצרים</span>
            </button>
            <button type="button" class="mk-cov-kpi mk-cov-kpi--out" @click="openCov('out', '', $event.currentTarget)">
              <span class="mk-cov-kpi-l"><i class="mk-cov-sw mk-cov-sw--out" aria-hidden="true"></i>לא אצלך</span>
              <strong class="mk-cov-kpi-n ltr-number">{{ num(covShown.out) }}</strong>
              <span class="mk-cov-kpi-s">
                לקוחות · <span class="ltr-number">{{ num(cov.summary.out_products) }}</span> מוצרים<template v-if="cov.summary.out_accumulation >= 0.5"> · <span class="ltr-number">₪{{ compact(cov.summary.out_accumulation) }}</span></template>
              </span>
            </button>
          </div>
          <ul class="mk-cov-bars">
            <li v-for="(c, i) in cov.by_company" :key="c.company" class="mk-cov-row" :style="{ '--i': i }">
              <button type="button" class="mk-cov-name" @click="openCov(c.out_customers ? 'out' : 'in', c.company, $event.currentTarget)">
                {{ shortCo(c.company) }}
              </button>
              <div class="mk-cov-track" :style="{ '--w': covWidth(c) + '%' }">
                <button
                  type="button" class="mk-cov-seg mk-cov-seg--in"
                  :style="{ flexGrow: c.in_customers }" :aria-label="`${shortCo(c.company)} · אצלך ${c.in_customers}`"
                  @click="openCov('in', c.company, $event.currentTarget)"
                ></button>
                <button
                  v-if="c.out_customers" type="button" class="mk-cov-seg mk-cov-seg--out"
                  :style="{ flexGrow: c.out_customers }" :aria-label="`${shortCo(c.company)} · לא אצלך ${c.out_customers}`"
                  @click="openCov('out', c.company, $event.currentTarget)"
                ></button>
              </div>
              <span class="mk-cov-nums">
                <span class="ltr-number">{{ num(c.in_customers) }}</span><template v-if="c.out_customers"> · <button type="button" class="mk-cov-out-n" @click="openCov('out', c.company, $event.currentTarget)"><span class="ltr-number">{{ num(c.out_customers) }}</span> לא אצלך</button></template>
              </span>
            </li>
          </ul>
          <!-- Bodies asked but not in this file yet: the file is partial until they answer. -->
          <div v-if="cov.waiting?.length" class="mk-cov-wait" :class="{ 'mk-cov-wait--open': waitOpen }">
            <button type="button" class="mk-cov-wait-h" :aria-expanded="waitOpen" @click="waitOpen = !waitOpen">
              <span>ממתינים למסלקה · <span class="ltr-number">{{ cov.waiting.length }}</span></span>
              <svg class="mk-cov-wait-chev" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor"
                   stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
            </button>
            <div class="mk-cov-wait-fold"><div class="mk-cov-wait-in">
            <ul class="mk-cov-bars mk-cov-bars--wait">
              <li v-for="(w, i) in cov.waiting" :key="w.code" class="mk-cov-row" :style="{ '--i': i }">
                <span class="mk-cov-name mk-cov-name--wait">{{ waitName(w.company) }}</span>
                <span class="mk-cov-ghost" aria-hidden="true"></span>
                <span class="mk-cov-nums">
                  <template v-if="w.due">עד <span class="ltr-number">{{ shortDay(w.due) }}</span></template>
                  <template v-else>בשליחה</template>
                </span>
              </li>
            </ul>
            </div></div>
          </div>
        </div>
        </div>
      </section>

      <MaslakaConsentModal
        :show="consent.show" :origin="consent.origin" :customer-id="consent.id" :customer-name="consent.name"
        :send="sendWithConsent" @close="consent = { ...consent, show: false }" @sent="onConsentSent"
      />
      <MaslakaCoverageDrill
        :open="covOpen" :as-of="cov?.as_of || ''" :origin="covOrigin"
        :initial-side="covSide" :initial-company="covCompany"
        @close="covOpen = false" @open-customer="openCustomer"
      />
      <MaslakaDeltaDrill
        :open="!!deltaAsOf" :as-of="deltaAsOf" :origin="deltaOrigin"
        @close="deltaAsOf = ''" @open-customer="openCustomer"
      />

      <p v-if="pictureError" class="mk-error" role="alert">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"
             stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="12" cy="12" r="9" /><path d="M12 8v4M12 16h.01" />
        </svg>
        <span>{{ pictureError }}</span>
      </p>

      <!-- One customer's pension picture — grows out of what was tapped
           (useOriginMorph), folds back into it on close. -->
      <Teleport to="body">
        <Transition name="modal">
          <div v-if="picture" class="mk-cm-overlay" @click.self="closeCustomer">
            <div ref="cmCardEl" class="mk-cm" dir="rtl" role="dialog" aria-modal="true" aria-labelledby="mk-cm-title"
                 @keydown.escape="closeCustomer">
              <header class="mk-cm-head">
                <span class="mk-cm-avatar" aria-hidden="true">{{ initials(picture.customer_name) }}</span>
                <div class="mk-cm-who">
                  <h3 id="mk-cm-title" class="mk-cm-name">{{ picture.customer_name || 'לקוח' }}</h3>
                  <span class="mk-cm-sub">
                    <span class="ltr-number">{{ picture.id_number }}</span>
                    <template v-if="picture.as_of"> · נכון ל-<span class="ltr-number">{{ formatDate(picture.as_of) }}</span></template>
                  </span>
                </div>
                <button class="mk-cm-close" type="button" aria-label="סגור" @click="closeCustomer">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
                       stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
                </button>
              </header>

              <div class="mk-cm-kpis">
                <div v-if="Number(picture.kpi?.total_accumulation) > 0" class="mk-cm-kpi mk-cm-kpi--hero">
                  <span class="mk-cm-kpi-l">סך צבירה</span>
                  <span class="mk-cm-kpi-n ltr-number">₪{{ money(picture.kpi?.total_accumulation) }}</span>
                </div>
                <div class="mk-cm-kpi">
                  <span class="mk-cm-kpi-l">מוצרים</span>
                  <span class="mk-cm-kpi-n ltr-number">{{ picture.kpi?.product_count ?? picture.products?.length ?? 0 }}</span>
                </div>
                <div v-if="newToUs" class="mk-cm-kpi">
                  <span class="mk-cm-kpi-l">לא אצלך</span>
                  <span class="mk-cm-kpi-n ltr-number">{{ newToUs }}</span>
                </div>
              </div>

              <div class="mk-cm-list">
                <article v-for="(p, i) in picture.products" :key="i" class="mk-cm-item">
                  <span class="mk-cm-logo" :style="{ '--c': companyColor(p.receiving_company) }" aria-hidden="true">
                    {{ (p.receiving_company || '?').trim().charAt(0) }}
                  </span>
                  <div class="mk-cm-item-main">
                    <strong class="mk-cm-item-title">{{ p.product || p.product_type || 'מוצר' }}</strong>
                    <span class="mk-cm-item-sub">
                      {{ p.receiving_company || '—' }}
                      <template v-if="p.fund_policy_number"> · <span class="ltr-number">{{ p.fund_policy_number }}</span></template>
                    </span>
                  </div>
                  <div class="mk-cm-item-end">
                    <span v-if="Number(p.accumulation) > 0" class="mk-cm-item-amt ltr-number">₪{{ money(p.accumulation) }}</span>
                    <span class="mk-cm-tag" :class="p.match_status === 'matched' ? 'mk-cm-tag--ok' : 'mk-cm-tag--new'">
                      {{ p.match_status === 'matched' ? 'אצלך' : 'לא אצלך' }}
                    </span>
                  </div>
                </article>
              </div>

              <footer class="mk-cm-foot">
                <button class="mk-ghost" :disabled="updateBusy || updateSent" @click="requestUpdate($event.currentTarget)">
                  <span>{{ updateSent ? 'נשלחה בקשת עדכון' : (updateBusy ? 'שולח…' : 'עדכון מהמסלקה') }}</span>
                </button>
              </footer>
            </div>
          </div>
        </Transition>
      </Teleport>
    </template>

    <!-- Reaching the bottom draws the same quiet growth chart as Production
         and השוואת נפרעים, behind the cards, in the tab's teal. -->
    <ProdScrollGraph color="var(--tab-maslaka)" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, onBeforeUnmount, nextTick, watch } from 'vue'
import api from '../../api/client.js'
import TabHeroLoop from './TabHeroLoop.vue'
import { resumeSetupIfAway } from '../../utils/setupState.js'
import { useCycleStore, signupLine, maslakaLine, MASLAKA_RULE } from '../../stores/cycle.js'
import MaslakaAssociationModal from './MaslakaAssociationModal.vue'
import MaslakaDeltaDrill from './MaslakaDeltaDrill.vue'
import MaslakaCoverageDrill from './MaslakaCoverageDrill.vue'
import MaslakaConsentModal from './MaslakaConsentModal.vue'
import ProdScrollGraph from './ProdScrollGraph.vue'
import { useOriginMorph } from '../../composables/useOriginMorph.js'
import { CHART_PALETTE } from '../../utils/chartPalette.js'

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
const cycleStore = useCycleStore()
const signup = computed(() => signupLine(cycleStore.status))
const masLine = computed(() => maslakaLine(cycleStore.status))
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
    // Sent here by the setup wizard and the שיוך form is now in → go back.
    if (['submitted', 'approved'].includes(data?.status)) resumeSetupIfAway('maslaka')
    cycleStore.fetchStatus()   // the dates (submitted/approved, first production) follow the status
  } catch {
    // Fail closed: if we cannot confirm the association, the ask form stays off.
    assoc.value = null
    assocError.value = 'לא הצלחנו לבדוק את מצב החיבור למסלקה. רעננו את הדף ונסו שוב.'
  } finally {
    assocLoaded.value = true
  }
}

const idDigits = computed(() => idNumber.value.replace(/\D/g, ''))
const idValid = computed(() => idDigits.value.length === 9)
// Validate on blur, not on keystroke — no error while the user is still typing.
const showIdError = computed(() => idTouched.value && !!idNumber.value && !idValid.value)
const canAsk = computed(() => !blocked.value && idValid.value && !busy.value)
const newToUs = computed(
  () => (picture.value?.products || []).filter((p) => p.match_status !== 'matched').length,
)

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


const updateBusy = ref(false)
const updateSent = ref(false)

// Search is DB-first: show what the monthly production files and earlier
// answers already brought in, instantly. Only a customer we have nothing on
// triggers a 9100 to the מסלקה (answer within hours).
async function ask() {
  if (!canAsk.value) return
  askError.value = ''
  busy.value = true
  const id = idDigits.value
  const name = customerName.value.trim() || null
  try {
    try {
      const { data } = await api.get(`/maslaka/customer/${encodeURIComponent(id)}`)
      await showPicture(data, askCardEl.value)
      idNumber.value = ''
      customerName.value = ''
      idTouched.value = false
      return
    } catch (e) {
      if (e?.response?.status !== 404) throw e
    }
    // Nothing on file yet → a 9100, which needs the signed נספח א' first.
    openConsent(id, name, askCardEl.value, () => {
      idNumber.value = ''
      customerName.value = ''
      idTouched.value = false
    })
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

// A 9100 needs the signed נספח א' — every send opens the consent form first.
const consent = ref({ show: false, id: '', name: '', origin: null, after: null })
function openConsent(id, name, originEl, after) {
  consent.value = { show: true, id, name: name || '', origin: originEl || null, after }
}
async function sendWithConsent(form) {
  await api.post('/maslaka/inquiry', {
    customer_id_number: consent.value.id,
    customer_name: consent.value.name || null,
    consent: form,
  })
}
async function onConsentSent() {
  const after = consent.value.after
  consent.value = { ...consent.value, show: false }
  await loadInquiries({ silent: true })
  if (after) after()
}

function requestUpdate(originEl) {
  if (!picture.value || updateBusy.value) return
  openConsent(picture.value.id_number, picture.value.customer_name, originEl, () => { updateSent.value = true })
}

// ── Customer modal: grows out of what was tapped, iPhone-style ──────────
const originMorph = useOriginMorph()
const askCardEl = ref(null)
const cmCardEl = ref(null)

async function showPicture(data, originEl) {
  originMorph.remember(originEl || null)
  picture.value = data
  pictureError.value = ''
  updateSent.value = false
  if (originEl) {
    await nextTick()
    originMorph.grow(cmCardEl.value)
  }
  nextTick(() => cmCardEl.value?.focus?.())
}

async function closeCustomer() {
  if (originMorph.hasOrigin()) await originMorph.shrink(cmCardEl.value)
  picture.value = null
}

async function openCustomer(id, originEl = null) {
  pictureError.value = ''
  try {
    const { data } = await api.get(`/maslaka/customer/${encodeURIComponent(id)}`)
    await showPicture(data, originEl)
  } catch (e) {
    pictureError.value = e?.response?.status === 404
      ? 'עדיין לא התקבלו נתונים עבור הלקוח הזה'
      : 'שגיאה בטעינת הנתונים'
  }
}

function initials(name) {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean)
  if (!parts.length) return ''
  return (parts[0][0] + (parts[1]?.[0] || '')).toUpperCase()
}

// A stable colour per company, from the shared categorical palette.
function companyColor(name) {
  const s = String(name || '')
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return CHART_PALETTE[h % CHART_PALETTE.length]
}

// ── Production files from the מסלקה ─────────────────────────────────────
const files = ref({ files: [], next_due: null, subscribed_bodies: 0 })
async function loadFiles() {
  try {
    const { data } = await api.get('/maslaka/production-files')
    files.value = data
    loadDeltas(data.files || [])
    loadCoverage(data.files?.[0]?.as_of)
  } catch {
    /* the section shows its empty state */
  }
}
// Each file's change counts (GET /maslaka/delta?as_of=), shown on its row.
const deltas = ref({})
async function loadDeltas(list) {
  for (const f of list) {
    if (!f.as_of || deltas.value[f.as_of]) continue
    try {
      const { data } = await api.get('/maslaka/delta', { params: { as_of: f.as_of } })
      if (data?.summary) deltas.value = { ...deltas.value, [f.as_of]: data.summary }
    } catch { /* the row just shows no delta */ }
  }
}
// ── The current file: אצלך / לא אצלך (GET /maslaka/coverage) ─────────────
const cov = ref(null)
const covEl = ref(null)
const covGrown = ref(false)
const covShown = ref({ in: 0, out: 0 })
async function loadCoverage(asOf) {
  if (!asOf) return
  try {
    const { data } = await api.get('/maslaka/coverage', { params: { as_of: asOf } })
    if (!data?.summary) return
    // the per-file list is drill-only; the card needs the counts
    cov.value = { as_of: data.as_of, summary: data.summary, by_company: data.by_company, waiting: data.waiting || [] }
    await nextTick()
    revealCoverage()
  } catch { /* the space stays with the timeline alone */ }
}
// Grow the bars and count up the first time the panel is on screen.
let covObs = null
let covRaf = 0
function revealCoverage() {
  const go = () => {
    covGrown.value = true
    const to = { in: cov.value.summary.in_customers || 0, out: cov.value.summary.out_customers || 0 }
    if (reducedMotion) { covShown.value = to; return }
    const t0 = performance.now(), dur = 1100
    const step = (t) => {
      const p = Math.min(1, (t - t0) / dur), e = 1 - Math.pow(1 - p, 3)
      covShown.value = { in: Math.round(to.in * e), out: Math.round(to.out * e) }
      if (p < 1) covRaf = requestAnimationFrame(step)
    }
    covRaf = requestAnimationFrame(step)
  }
  if (!covEl.value || typeof IntersectionObserver === 'undefined') return go()
  covObs = new IntersectionObserver((es) => {
    if (es.some((e) => e.isIntersecting)) { covObs.disconnect(); covObs = null; go() }
  }, { threshold: 0.3 })
  covObs.observe(covEl.value)
}
onBeforeUnmount(() => { covObs?.disconnect(); cancelAnimationFrame(covRaf) })
// Bar length = the company's customers against the biggest company's.
const covMax = computed(() => Math.max(1, ...(cov.value?.by_company || []).map((c) => c.in_customers + c.out_customers)))
const covWidth = (c) => Math.max(4, ((c.in_customers + c.out_customers) / covMax.value) * 100)
const covOpen = ref(false)
const covSide = ref('out')
const covCompany = ref('')
const covOrigin = ref(null)
function openCov(sideId, company, el) {
  covSide.value = sideId
  covCompany.value = company
  covOrigin.value = el
  covOpen.value = true
}
const num = (n) => Number(n || 0).toLocaleString('he-IL')
function compact(v) {
  const n = Number(v || 0)
  if (n >= 1e6) return (n / 1e6).toLocaleString('he-IL', { maximumFractionDigits: 1 }) + 'M'
  if (n >= 1e3) return Math.round(n / 1e3).toLocaleString('he-IL') + 'K'
  return Math.round(n).toLocaleString('he-IL')
}
// The next thing to arrive: a body still owed THIS file comes before next month's.
// closed by default — the agent opens it (not remembered)
const waitOpen = ref(false)
const nextDue = computed(() => {
  const owed = (cov.value?.waiting || []).map((w) => w.due).filter(Boolean).sort()[0]
  const next = files.value.next_due
  return owed && (!next || owed < next) ? owed : next
})
// A brand is often two bodies (פנסיה וגמל + ביטוח): name the kind only when both wait.
function waitName(company) {
  const short = shortCo(company)
  const brand = short.split(' ')[0]
  const twins = (cov.value?.waiting || []).filter((w) => shortCo(w.company).split(' ')[0] === brand).length > 1
  return twins ? `${short} · ${/ביטוח/.test(company) ? 'ביטוח' : 'גמל ופנסיה'}` : short
}
const shortCo = (c) => String(c || '').replace(/\s*(חברה לביטוח|פנסיה וגמל|גמל ופנסיה|פנסיה מקיפה|בע"מ|בעמ)\s*/g, ' ').trim() || c

const deltaAsOf = ref('')
const deltaOrigin = ref(null)
function openDelta(asOf, el) {
  deltaOrigin.value = el
  deltaAsOf.value = asOf
}
const HEB_MONTHS = ['ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני', 'יולי', 'אוגוסט', 'ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר']
function monthLabel(iso) {
  const [y, m] = String(iso || '').split('-').map(Number)
  return y && m ? `${HEB_MONTHS[m - 1]} ${y}` : ''
}
function shortDay(iso) {
  if (!iso) return '—'
  const d = new Date(String(iso).length === 10 ? iso + 'T12:00:00' : iso)
  return d.toLocaleDateString('he-IL', { day: 'numeric', month: 'numeric', timeZone: 'Asia/Jerusalem' })
}
const nextCycleLabel = computed(() => {
  const iso = cycleStore.status?.next_cycle_at
  return iso ? shortDay(iso) : ''
})

const OPEN = new Set(['pending', 'submitted', 'acknowledged', 'partial'])
let refreshTimer = null
function startRefresh() {
  refreshTimer = setInterval(() => {
    if (inquiries.value.some((q) => OPEN.has(q.status))) loadInquiries({ silent: true })
  }, 60000)
}
onUnmounted(() => { if (refreshTimer) clearInterval(refreshTimer) })

// ── Remotion backdrop (decorative — the tab works without it) ───────────
const bgEl = ref(null)
const reducedMotion =
  typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
let bgRoot = null
async function mountBg() {
  if (!bgEl.value || bgRoot) return
  try {
    const [rdClient, react, player, comp] = await Promise.all([
      import('react-dom/client'), import('react'), import('@remotion/player'),
      import('../../remotion/MaslakaBackdrop'),
    ])
    if (!bgEl.value || bgRoot) return
    // Remotion can't read CSS variables — resolve the tab's teal here.
    const teal = getComputedStyle(document.documentElement).getPropertyValue('--tab-maslaka').trim() || '#2C5F6B'
    bgRoot = rdClient.createRoot(bgEl.value)
    bgRoot.render(react.createElement(player.Player, {
      component: comp.MaslakaBackdrop,
      inputProps: { color: teal, ink: teal },
      durationInFrames: comp.MASLAKA_BG_FRAMES, fps: 30,
      compositionWidth: comp.MASLAKA_BG_W, compositionHeight: comp.MASLAKA_BG_H,
      autoPlay: true, loop: true, controls: false, clickToPlay: false,
      doubleClickToFullscreen: false, showPosterWhenUnplayed: false, acknowledgeRemotionLicense: true,
      style: { width: '100%', height: '100%', backgroundColor: 'transparent' },
    }))
  } catch (e) {
    console.error('[MaslakaTab] background failed', e)
  }
}
function unmountBg() {
  if (bgRoot) { try { bgRoot.unmount() } catch { /* ignore */ } bgRoot = null }
}
watch(bgEl, (el) => { if (el) mountBg(); else unmountBg() })
onBeforeUnmount(unmountBg)

onMounted(async () => {
  startRefresh()
  await Promise.all([loadInquiries(), loadAssociation(), loadFiles()])
})
</script>

<style scoped>
.mk {
  /* Own stacking layer: the backdrop and the bottom growth graph paint above the
     page canvas but behind every card. */
  position: relative; z-index: 0;
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

.mk-loading { display: flex; justify-content: center; padding: 44px; }

@media (prefers-reduced-motion: reduce) {
  .mk-btn-spinner { animation: none; }
  .mk-primary, .mk-field input, .mk-ghost, .mk-table tbody tr { transition: none; }
  .mk-primary:hover:not(:disabled) { transform: none; }
}
.mk-link {
  border: 0; background: none; padding: 0; cursor: pointer; font: inherit;
  font-size: 0.78rem; color: var(--tab-maslaka); text-decoration: underline;
}
.mk-link:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }
.mk-ask-sent { color: var(--text); margin-top: 8px; }
.mk-dates { position: relative; z-index: 1; display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 12px; }
.mk-date { display: inline-flex; align-items: center; gap: 4px; padding: 6px 12px; border-radius: 999px; background: #F4F3F1; color: #3E3E3C; font-size: 12.5px; font-weight: 600; }
.mk-date strong { font-weight: 800; }
.mk-date--ok { background: #EAF5EE; color: #2E844A; }
.mk-date--wait { background: #FBF4DC; color: #8A6300; }
.mk-date--todo { background: #E4EDEF; color: #2C5F6B; }
.mk-rule { flex-basis: 100%; font-size: 12px; color: var(--text-secondary, #8A8784); }

/* ── Production files timeline ────────────────────────────────── */
.mk-timeline { margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; }
.mk-tl { position: relative; display: flex; gap: 14px; padding-bottom: 18px; }
.mk-tl:last-child { padding-bottom: 0; }
/* the rail between dots */
.mk-tl:not(:last-child)::before {
  content: ''; position: absolute; inset-inline-start: 10px; top: 24px; bottom: 2px;
  width: 2px; background: var(--border-subtle);
}
.mk-tl-dot {
  flex-shrink: 0; width: 22px; height: 22px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--tab-maslaka-wash); color: var(--tab-maslaka);
  border: 2px solid var(--card-bg); box-shadow: 0 0 0 1px var(--mk-accent-30);
}
.mk-tl--next .mk-tl-dot { background: var(--card-bg); box-shadow: 0 0 0 2px var(--tab-maslaka); }
.mk-tl--next .mk-tl-dot::after {
  content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--tab-maslaka);
  animation: mk-tl-pulse 2.4s ease-in-out infinite;
}
.mk-tl--current .mk-tl-dot { background: var(--tab-maslaka); color: #fff; }
.mk-tl--empty .mk-tl-dot { background: var(--bg); box-shadow: 0 0 0 1px var(--border); }
.mk-tl-body { display: flex; flex-direction: column; gap: 1px; min-width: 0; padding-top: 1px; }
.mk-tl-kicker { font-size: 0.7rem; font-weight: 700; letter-spacing: 0.02em; color: var(--text-muted); }
.mk-tl--current .mk-tl-kicker, .mk-tl--next .mk-tl-kicker { color: var(--tab-maslaka); }
.mk-tl-title { font-size: 1rem; font-weight: 800; color: var(--text); }
.mk-tl--next .mk-tl-title { font-size: 1.15rem; }
.mk-tl-meta { font-size: 0.78rem; color: var(--text-muted); }
.mk-tl-delta { align-self: flex-start; margin-top: 6px; display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px;
  border: 1px solid color-mix(in srgb, var(--tab-maslaka) 30%, var(--border-subtle)); border-radius: 10px;
  background: var(--card-bg); cursor: pointer; font-family: inherit; font-size: 0.8rem; font-weight: 700; color: var(--tab-maslaka);
  transition: transform 0.15s, background 0.15s, border-color 0.15s; }
.mk-tl-delta:hover { transform: translateY(-1px); background: var(--tab-maslaka-wash); border-color: var(--tab-maslaka); }
.mk-tl-delta:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }
.mk-tl-delta-n { font-weight: 500; color: var(--text-secondary); }
/* the timeline and the אצלך / לא אצלך panel side by side */
.mk-files-grid { display: block; }
.mk-files-grid--cov { display: grid; grid-template-columns: minmax(220px, 300px) minmax(0, 1fr); gap: 28px; align-items: start; }
.mk-cov { display: flex; flex-direction: column; gap: 12px; min-width: 0; padding-inline-start: 28px;
  border-inline-start: 1px solid var(--border-subtle); }
.mk-cov-head .mk-tl-kicker { color: var(--tab-maslaka); }
.mk-cov-kpis { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.mk-cov-kpi { display: flex; flex-direction: column; align-items: flex-start; gap: 1px; padding: 10px 14px;
  border: 1px solid var(--border-subtle); border-radius: 12px; background: var(--card-bg); cursor: pointer;
  font-family: inherit; text-align: start; color: var(--text); transition: transform 0.15s, background 0.2s, border-color 0.2s; }
.mk-cov-kpi:hover { transform: translateY(-1px); background: var(--tab-maslaka-wash); border-color: var(--tab-maslaka); }
.mk-cov-kpi:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }
.mk-cov-kpi-l { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 700; color: var(--text-muted); }
.mk-cov-kpi-n { font-size: 24px; font-weight: 800; line-height: 1.15; }
.mk-cov-kpi--out .mk-cov-kpi-n { color: var(--tab-maslaka); }
.mk-cov-kpi-s { font-size: 12px; color: var(--text-muted); }
.mk-cov-sw { width: 9px; height: 9px; border-radius: 3px; }
.mk-cov-sw--in, .mk-cov-seg--in { background: var(--tab-maslaka); }
/* לא אצלך: the same teal, hatched — one colour, and the small slice still reads */
.mk-cov-sw--out, .mk-cov-seg--out {
  background: repeating-linear-gradient(-45deg, var(--mk-accent-30) 0 3px, color-mix(in srgb, var(--tab-maslaka) 62%, transparent) 3px 6px); }

.mk-cov-bars { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.mk-cov-row { display: grid; grid-template-columns: 92px minmax(0, 1fr) 128px; align-items: center; gap: 12px; }
.mk-cov-name { justify-self: start; max-width: 100%; padding: 0; border: none; background: none; cursor: pointer; font-family: inherit;
  font-size: 13px; font-weight: 700; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mk-cov-name:hover { color: var(--tab-maslaka); }
.mk-cov-track { display: flex; gap: 2px; height: 14px; width: 0; border-radius: 5px; overflow: hidden;
  transition: width 1.1s cubic-bezier(0.22, 1, 0.36, 1); transition-delay: calc(var(--i) * 120ms); }
.mk-cov--in .mk-cov-track { width: var(--w); }
.mk-cov-seg { flex-basis: 0; min-width: 5px; height: 100%; padding: 0; border: none; cursor: pointer; transition: filter 0.15s; }
.mk-cov-seg:hover { filter: brightness(1.15); }
.mk-cov-seg:focus-visible { outline: 2px solid var(--text); outline-offset: -2px; }
.mk-cov-nums { font-size: 12.5px; color: var(--text-muted); white-space: nowrap; opacity: 0;
  transition: opacity 0.5s ease; transition-delay: calc(0.6s + var(--i) * 120ms); }
.mk-cov--in .mk-cov-nums { opacity: 1; }
.mk-cov-nums > .ltr-number { font-weight: 700; color: var(--text); }
.mk-cov-out-n { padding: 0; border: none; background: none; cursor: pointer; font-family: inherit; font-size: inherit;
  color: var(--tab-maslaka); font-weight: 700; }
.mk-cov-out-n:hover { text-decoration: underline; }
.mk-cov-wait { display: flex; flex-direction: column; gap: 0; padding-top: 10px; border-top: 1px dashed var(--border-subtle); }
.mk-cov-wait-h { align-self: flex-start; display: inline-flex; align-items: center; gap: 6px; padding: 2px 0;
  border: none; background: none; cursor: pointer; font-family: inherit; font-size: 12.5px; font-weight: 700; color: var(--text-muted);
  transition: color 0.2s; }
.mk-cov-wait-h:hover, .mk-cov-wait--open .mk-cov-wait-h { color: var(--tab-maslaka); }
.mk-cov-wait-h:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; border-radius: 4px; }
.mk-cov-wait-chev { transition: transform 0.35s cubic-bezier(0.32, 0.72, 0, 1); }
.mk-cov-wait--open .mk-cov-wait-chev { transform: rotate(180deg); }
.mk-cov-wait-fold { display: grid; grid-template-rows: 0fr; transition: grid-template-rows 0.45s cubic-bezier(0.32, 0.72, 0, 1); }
.mk-cov-wait--open .mk-cov-wait-fold { grid-template-rows: 1fr; }
.mk-cov-wait-in { overflow: hidden; min-height: 0; }
.mk-cov-wait:not(.mk-cov-wait--open) .mk-cov-ghost { width: 0; }
.mk-cov-wait--open .mk-cov-ghost { transition-delay: calc(0.15s + var(--i) * 60ms); }
.mk-cov-bars--wait { gap: 6px; padding-top: 8px; }
.mk-cov-name--wait { cursor: default; font-weight: 600; color: var(--text-muted); }
/* an empty, breathing track: asked, not answered yet */
.mk-cov-ghost { height: 10px; width: 0; border-radius: 5px; border: 1px dashed var(--mk-accent-30);
  background: linear-gradient(90deg, transparent, var(--mk-accent-12), transparent) 0 0 / 200% 100%;
  transition: width 1.1s cubic-bezier(0.22, 1, 0.36, 1); transition-delay: calc(var(--i) * 80ms);
  animation: mk-cov-breathe 2.8s ease-in-out infinite; }
.mk-cov--in .mk-cov-ghost { width: 100%; }
@keyframes mk-cov-breathe { 0% { background-position: 100% 0; } 100% { background-position: -100% 0; } }
@media (max-width: 860px) {
  .mk-files-grid--cov { grid-template-columns: 1fr; gap: 18px; }
  .mk-cov { padding-inline-start: 0; padding-top: 16px; border-inline-start: none; border-top: 1px solid var(--border-subtle); }
}
@media (max-width: 480px) {
  .mk-cov-row { grid-template-columns: 72px minmax(0, 1fr); }
  .mk-cov-nums { grid-column: 2; }
}
@media (prefers-reduced-motion: reduce) {
  .mk-cov-track, .mk-cov-nums, .mk-cov-ghost { transition: none; animation: none; }
}
@keyframes mk-tl-pulse { 50% { transform: scale(0.6); opacity: 0.5; } }

/* ── Customer modal (iPhone-style grow from origin) ───────────── */
.mk-cm-overlay {
  /* above the "מה השתנה" drill (DataModal 1010) it can be opened from */
  position: fixed; inset: 0; z-index: 1030;
  display: flex; align-items: center; justify-content: center;
  padding: 16px; background: rgba(0, 0, 0, 0.42);
}
.mk-cm {
  width: min(560px, 100%); max-height: min(760px, calc(100vh - 32px));
  display: flex; flex-direction: column; overflow: hidden;
  background: var(--card-bg); border-radius: 22px; box-shadow: var(--shadow-lg);
  outline: none;
}
.mk-cm-head {
  display: flex; align-items: center; gap: 14px;
  padding: 22px 22px 16px;
  background: linear-gradient(180deg, var(--tab-maslaka-wash), var(--card-bg));
}
.mk-cm-avatar {
  flex-shrink: 0; width: 52px; height: 52px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  background: var(--tab-maslaka); color: #fff; font-size: 1.1rem; font-weight: 800;
}
.mk-cm-who { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.mk-cm-name { margin: 0; font-size: 1.25rem; font-weight: 800; color: var(--text); letter-spacing: -0.01em; }
.mk-cm-sub { font-size: 0.8rem; color: var(--text-muted); }
.mk-cm-close {
  flex-shrink: 0; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center;
  border: none; border-radius: 50%; background: var(--bg); color: var(--text-secondary); cursor: pointer;
}
.mk-cm-close:hover { background: var(--border-subtle); color: var(--text); }
.mk-cm-close:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }
.mk-cm-kpis { display: flex; gap: 10px; padding: 0 22px 16px; }
.mk-cm-kpi {
  flex: 1; display: flex; flex-direction: column; gap: 2px;
  padding: 12px 14px; border-radius: 14px; background: var(--bg);
}
.mk-cm-kpi--hero { flex: 1.6; background: var(--tab-maslaka); }
.mk-cm-kpi--hero .mk-cm-kpi-l { color: rgba(255, 255, 255, 0.78); }
.mk-cm-kpi--hero .mk-cm-kpi-n { color: #fff; }
.mk-cm-kpi-l { font-size: 0.72rem; color: var(--text-muted); }
.mk-cm-kpi-n { font-size: 1.3rem; font-weight: 800; color: var(--text); font-variant-numeric: tabular-nums; }
.mk-cm-list { flex: 1; overflow-y: auto; padding: 0 14px 8px; display: flex; flex-direction: column; }
.mk-cm-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px 8px; border-bottom: 1px solid var(--border-subtle);
  border-radius: 10px; transition: background 0.2s, border-color 0.2s;
}
/* hover colours the row in the tab's wash, like the מה השתנה cards */
.mk-cm-item:hover { background: var(--tab-maslaka-wash); border-bottom-color: transparent; }
.mk-cm-item:last-child { border-bottom: none; }
.mk-cm-logo {
  flex-shrink: 0; width: 38px; height: 38px; border-radius: 11px;
  display: inline-flex; align-items: center; justify-content: center;
  background: color-mix(in srgb, var(--c) 16%, #fff); color: color-mix(in srgb, var(--c) 80%, #000);
  font-weight: 800; font-size: 0.95rem;
}
.mk-cm-item-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.mk-cm-item-title { font-size: 0.9rem; font-weight: 700; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mk-cm-item-sub { font-size: 0.75rem; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mk-cm-item-end { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; flex-shrink: 0; }
.mk-cm-item-amt { font-size: 0.9rem; font-weight: 800; color: var(--text); }
.mk-cm-tag { font-size: 0.68rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; }
.mk-cm-tag--ok { background: var(--green-light); color: var(--mk-green-ink); }
.mk-cm-tag--new { background: var(--tab-maslaka-wash); color: var(--tab-maslaka); }
.mk-cm-foot { display: flex; justify-content: center; padding: 12px 22px 18px; border-top: 1px solid var(--border-subtle); }
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
@media (max-width: 560px) {
  .mk-cm-overlay { align-items: flex-end; padding: 0; }
  .mk-cm { width: 100%; max-height: 92vh; border-radius: 22px 22px 0 0; }
}
@media (prefers-reduced-motion: reduce) {
  .mk-tl--next .mk-tl-dot::after { animation: none; }
}

.mk-bg { position: fixed; inset: 0; z-index: -1; pointer-events: none; overflow: hidden; }
/* "cover" for the 16:9 composition: at least the viewport's width AND height. */
.mk-bg-mount {
  position: absolute; left: 50%; top: 50%;
  width: max(100vw, calc(100vh * 16 / 9));
  aspect-ratio: 1600 / 900;
  transform: translate(-50%, -50%);
  direction: ltr; /* RTL root would shift the Remotion composition */
}
</style>
