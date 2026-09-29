<template>
  <!-- `inline`: rendered in the page itself, not as a popup — no overlay, no
       ✕, no Escape. Used while the agent still has to act on the שיוך, so it
       can't be dismissed into an empty tab, yet the tab strip stays usable. -->
  <Teleport to="body" :disabled="inline">
    <Transition name="modal">
      <div v-if="open" :class="inline ? 'ma-inline' : 'ma-overlay'" data-own-drop @click.self="close">
        <div
          class="ma-card"
          dir="rtl"
          :role="inline ? 'region' : 'dialog'"
          :aria-modal="inline ? undefined : 'true'"
          aria-labelledby="ma-title"
          @keydown.escape="close"
        >
          <!-- Form pane first in the DOM → the RIGHT side under `direction: rtl`,
               the photograph on the left: the same two-pane card as the
               contact and portal modals. Only this pane scrolls. -->
          <div class="ma-form">
          <button v-if="!inline" class="ma-close" type="button" aria-label="סגור" @click="close">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>

          <header class="ma-head">
            <h2 id="ma-title" class="ma-title">חיבור למסלקה הפנסיונית</h2>
            <p class="ma-sub">
              פעם אחת בלבד: המסלקה צריכה לשייך אתכם ל-Nifraim לפני שאפשר לבקש דרכנו מידע על לקוחות.
            </p>
          </header>

          <!-- A real sequence, so it is numbered. Steps behind the agent's
               progress stay clickable; steps ahead of it do not. -->
          <ol class="ma-track">
            <li
              v-for="(s, i) in STEPS"
              :key="s.id"
              class="ma-track-step"
              :class="{
                'ma-track-step--on': i === step,
                'ma-track-step--done': i < reached,
              }"
            >
              <button type="button" class="ma-track-btn" :disabled="i > reached" @click="step = i">
                <span class="ma-track-mark" aria-hidden="true">
                  <svg v-if="i < reached && i !== step" viewBox="0 0 24 24" width="12" height="12" fill="none"
                       stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
                    <path d="m5 13 4 4L19 7" />
                  </svg>
                  <span v-else class="ltr-number">{{ i + 1 }}</span>
                </span>
                <span class="ma-track-label">{{ s.label }}</span>
              </button>
            </li>
          </ol>

          <div class="ma-body">
            <!-- ── 1. Identity ───────────────────────────────────── -->
            <section v-if="step === 0" class="ma-pane">
              <div class="ma-fields">
                <div class="ma-field">
                  <label for="ma-name">שם הסוכן או הסוכנות</label>
                  <input id="ma-name" v-model="name" autocomplete="name" />
                  <span class="ma-help">כפי שיופיע בטופס</span>
                </div>
                <div class="ma-field">
                  <label for="ma-id">ת"ז או ח.פ</label>
                  <input
                    id="ma-id"
                    v-model="idNumber"
                    dir="ltr"
                    inputmode="numeric"
                    maxlength="9"
                    autocomplete="off"
                    :aria-invalid="showIdError"
                    :aria-describedby="showIdError ? 'ma-id-err' : 'ma-id-help'"
                    @blur="idTouched = true"
                  />
                  <span v-if="showIdError" id="ma-id-err" class="ma-help ma-help--bad">עד 9 ספרות</span>
                  <span v-else id="ma-id-help" class="ma-help">המספר שהמסלקה מכירה אתכם לפיו</span>
                </div>
              </div>
            </section>

            <!-- ── 2. Sign ───────────────────────────────────────── -->
            <section v-else-if="step === 1" class="ma-pane">
              <p class="ma-lead">
                מילאנו את כל הטופס בשבילכם. נשאר רק לחתום.
              </p>

              <div v-if="!assoc?.template_ready" class="ma-note ma-note--wait" role="status">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
                     stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
                </svg>
                <span>
                  הטופס עצמו עוד לא זמין במערכת. הפרטים שלכם נשמרו, ונעדכן כאן ברגע שיהיה אפשר להמשיך.
                </span>
              </div>

              <template v-else>
                <!-- The signer is the person, so their ת"ז — an agency's ח.פ
                     does not belong here. Pre-filled from step 1, editable. -->
                <div class="ma-fields">
                  <div class="ma-field">
                    <label for="ma-signer">שם החותם</label>
                    <input id="ma-signer" v-model="signerName" autocomplete="name" />
                  </div>
                  <div class="ma-field">
                    <label for="ma-signer-id">ת"ז החותם</label>
                    <input
                      id="ma-signer-id"
                      v-model="signerId"
                      dir="ltr"
                      inputmode="numeric"
                      maxlength="9"
                      autocomplete="off"
                    />
                  </div>
                </div>

                <div class="ma-sign">
                  <div class="ma-sign-head">
                    <span class="ma-sign-label">חתימה</span>
                    <span class="ma-help">
                      תאריך: <span class="ltr-number">{{ todayLabel }}</span>
                    </span>
                    <button v-if="hasInk" type="button" class="ma-link" @click="clearPad">ניקוי</button>
                  </div>
                  <div class="ma-pad" :class="{ 'ma-pad--ink': hasInk }">
                    <canvas
                      ref="padEl"
                      class="ma-pad-canvas"
                      aria-label="משטח חתימה"
                      @pointerdown="padDown"
                      @pointermove="padMove"
                      @pointerup="padUp"
                      @pointercancel="padUp"
                      @pointerleave="padUp"
                    ></canvas>
                    <span v-if="!hasInk" class="ma-pad-hint" aria-hidden="true">חתמו כאן, עם העכבר או האצבע</span>
                    <span class="ma-pad-line" aria-hidden="true"></span>
                  </div>
                </div>
              </template>
            </section>

            <!-- ── 3. Review + send ──────────────────────────────── -->
            <section v-else-if="step === 2" class="ma-pane">
              <p class="ma-lead">זה הטופס החתום שיישלח למסלקה. בדקו שהכול נכון ושלחו.</p>
              <!-- Phones: the side pane is hidden, so the form shows here. -->
              <div class="ma-preview">
                <img
                  v-for="(src, i) in previewPages"
                  :key="i"
                  :src="src"
                  :alt="`עמוד ${i + 1} של הטופס החתום`"
                  class="ma-preview-page"
                />
              </div>
            </section>

            <!-- ── 4. Waiting / rejected ─────────────────────────── -->
            <section v-else class="ma-pane">
              <div v-if="assoc?.status === 'rejected'" class="ma-state ma-state--bad">
                <span class="ma-state-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
                       stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="9" /><path d="M12 8v4M12 16h.01" />
                  </svg>
                </span>
                <div class="ma-state-texts">
                  <strong>המסלקה החזירה את הטופס</strong>
                  <span v-if="assoc.rejected_reason">{{ assoc.rejected_reason }}</span>
                  <span>תקנו, חתמו מחדש ושלחו שוב.</span>
                </div>
              </div>
              <div v-else-if="assoc?.status === 'approved'" class="ma-state ma-state--ok">
                <span class="ma-state-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
                       stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m5 13 4 4L19 7" /></svg>
                </span>
                <div class="ma-state-texts">
                  <strong>אתם משויכים ל-Nifraim במסלקה</strong>
                  <span>אפשר לשלוח בקשות מידע על לקוחות.</span>
                </div>
              </div>
              <div v-else class="ma-state">
                <span class="ma-state-icon" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor"
                       stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" />
                  </svg>
                </span>
                <div class="ma-state-texts">
                  <strong>ממתין לאישור המסלקה</strong>
                  <span>
                    הטופס נשלח<template v-if="assoc?.submitted_at"> ב-<span class="ltr-number">{{ formatDate(assoc.submitted_at) }}</span></template>.
                    המסלקה מאשרת במייל, בדרך כלל תוך כמה ימי עסקים, והלשונית תיפתח לבד כשהאישור יירשם.
                  </span>
                </div>
              </div>

              <!-- The helpdesk reply the watcher matched. Shown whenever there is
                   one: undecided → a person reads it; decided by the watcher →
                   the agent can see WHICH email it acted on and catch a misread. -->
              <div v-if="assoc?.reply_received_at" class="ma-reply">
                <div class="ma-reply-head">
                  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"
                       stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" />
                  </svg>
                  <strong>{{ replyTitle }}</strong>
                  <span class="ma-reply-date ltr-number">{{ formatDateTime(assoc.reply_received_at) }}</span>
                </div>
                <p v-if="assoc.reply_subject" class="ma-reply-subject">{{ assoc.reply_subject }}</p>
                <blockquote v-if="assoc.reply_snippet" class="ma-reply-body">{{ assoc.reply_snippet }}</blockquote>
                <p v-if="assoc.decided_via === 'mailbox'" class="ma-help">
                  זוהה אוטומטית מתוך המייל. אם זה לא מה שהמסלקה כתבה — פנו לתמיכה ונתקן.
                </p>
              </div>

              <!-- Verbatim: it is the only place a failed send shows up. -->
              <p
                v-if="deliveryNote"
                class="ma-note"
                :class="deliveryFailed ? 'ma-note--bad' : 'ma-note--ok'"
                role="status"
              >{{ deliveryNote }}</p>
            </section>

            <p v-if="error" class="ma-error" role="alert">{{ error }}</p>
          </div>

          <footer class="ma-foot">
            <template v-if="step === 0">
              <button class="ma-primary" type="button" :disabled="!canSaveIdentity || busy" @click="saveIdentity">
                <span v-if="busy" class="ma-spinner" aria-hidden="true"></span>
                <span>שמירה והמשך</span>
              </button>
            </template>

            <template v-else-if="step === 1">
              <button
                class="ma-primary"
                type="button"
                :disabled="!assoc?.template_ready || !canSign || busy"
                @click="makePreview"
              >
                <span v-if="busy" class="ma-spinner" aria-hidden="true"></span>
                <span>{{ busy ? 'מכין את הטופס…' : 'הצגת הטופס החתום' }}</span>
              </button>
            </template>

            <template v-else-if="step === 2">
              <button class="ma-primary" type="button" :disabled="!signatureData || busy" @click="submit">
                <span v-if="busy" class="ma-spinner" aria-hidden="true"></span>
                <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor"
                     stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="m22 2-7 20-4-9-9-4z" /><path d="M22 2 11 13" />
                </svg>
                <span>{{ busy ? 'שולח…' : 'שליחה למסלקה' }}</span>
              </button>
              <button class="ma-secondary" type="button" :disabled="busy" @click="step = 1">חתימה מחדש</button>
            </template>

            <template v-else>
              <button v-if="assoc?.status === 'rejected'" class="ma-primary" type="button" @click="step = 1">
                חתימה מחדש
              </button>
              <button v-if="assoc?.signed_pdf_filename" class="ma-secondary" type="button" @click="openSigned">
                הטופס שנשלח
              </button>
              <button v-if="assoc?.status !== 'rejected' && !inline" class="ma-secondary" type="button" @click="close">סגירה</button>
            </template>
          </footer>
          </div>

          <!-- On the review step the photo gives way to the signed form itself:
               the one thing the agent must look at before sending. -->
          <aside v-if="step === 2 && previewPages.length" class="ma-art ma-art--doc" aria-label="הטופס החתום">
            <img
              v-for="(src, i) in previewPages"
              :key="i"
              :src="src"
              :alt="`עמוד ${i + 1} של הטופס החתום`"
              class="ma-doc-page"
            />
          </aside>
          <aside v-else class="ma-art" aria-hidden="true">
            <img :src="artwork" alt="" />
            <div class="ma-art-veil"></div>
          </aside>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import api from '../../api/client.js'
import artwork from '../../assets/maslaka/association.webp'

const props = defineProps({
  open: { type: Boolean, default: false },
  // GET /maslaka/association payload — the single source of truth; this
  // component never keeps its own copy of the status.
  assoc: { type: Object, default: null },
  // In the page instead of a popup, and not dismissible (see the template).
  inline: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'changed'])

const STEPS = [
  { id: 'identity', label: 'הפרטים שלכם' },
  { id: 'sign', label: 'חתימה' },
  { id: 'review', label: 'בדיקה ושליחה' },
  { id: 'approval', label: 'אישור המסלקה' },
]

const step = ref(0)
const name = ref('')
const idNumber = ref('')
const idTouched = ref(false)
// Signing: the drawn signature, the signer, and the server-rendered pages the
// agent reviews before sending. None of it is stored until they press send.
const signerName = ref('')
const signerId = ref('')
const padEl = ref(null)
const hasInk = ref(false)
const signatureData = ref('')
const previewPages = ref([])
const busy = ref(false)
const error = ref('')
const deliveryNote = ref('')

// Furthest step the server-side status allows the agent to stand on.
const reached = computed(() => {
  const a = props.assoc
  if (!a) return 0
  if (['submitted', 'approved', 'rejected'].includes(a.status)) return 3
  if (!a.agent_id_number) return 0
  return previewPages.value.length ? 2 : 1
})

const idDigits = computed(() => idNumber.value.replace(/\D/g, ''))
const showIdError = computed(() => idTouched.value && !!idNumber.value && (idDigits.value.length === 0 || idDigits.value.length > 9))
const canSaveIdentity = computed(() => idDigits.value.length >= 5 && idDigits.value.length <= 9 && !!name.value.trim())
const signerDigits = computed(() => signerId.value.replace(/\D/g, ''))
const canSign = computed(() => hasInk.value && !!signerName.value.trim()
  && signerDigits.value.length >= 5 && signerDigits.value.length <= 9)
const todayLabel = computed(() => new Date().toLocaleDateString('en-GB', { timeZone: 'Asia/Jerusalem' }))
const deliveryFailed = computed(() => deliveryNote.value.includes('נכשל'))

// Open on the step the agent actually has to do next.
watch(() => props.open, (isOpen) => {
  if (!isOpen) return
  const a = props.assoc || {}
  name.value = a.agent_name || ''
  idNumber.value = a.agent_id_number || ''
  idTouched.value = false
  signerName.value = a.agent_name || ''
  signerId.value = a.agent_id_number || ''
  signatureData.value = ''
  previewPages.value = []
  hasInk.value = false
  error.value = ''
  // Prefer the server's note if it reports one; else keep the last submit's.
  deliveryNote.value = a.delivery_note || deliveryNote.value
  step.value = reached.value
}, { immediate: true })

const replyTitle = computed(() => {
  const a = props.assoc
  if (!a?.reply_received_at) return ''
  if (a.decided_via === 'mailbox' && a.status === 'approved') return 'האישור זוהה במייל מהמסלקה'
  if (a.decided_via === 'mailbox' && a.status === 'rejected') return 'ההחזרה זוהתה במייל מהמסלקה'
  return 'התקבלה תשובה מהמסלקה'
})

function formatDateTime(iso) {
  return new Date(iso + (iso.endsWith('Z') || iso.includes('+') ? '' : 'Z'))
    .toLocaleString('he-IL', { dateStyle: 'short', timeStyle: 'short' })
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('he-IL')
}

function close() {
  if (props.inline) return          // in-page wizard: nothing to close
  if (!busy.value) emit('close')
}

function detailOf(e, fallback) {
  const d = e?.response?.data?.detail
  return typeof d === 'string' ? d : fallback
}

async function saveIdentity() {
  error.value = ''
  busy.value = true
  try {
    await api.post('/maslaka/association/identity', {
      agent_id_number: idDigits.value,
      agent_name: name.value.trim(),
    })
    signerName.value = name.value.trim()
    signerId.value = idDigits.value
    emit('changed')
    step.value = 1
  } catch (e) {
    error.value = detailOf(e, 'שמירת הפרטים נכשלה')
  } finally {
    busy.value = false
  }
}

// ── Signature pad ────────────────────────────────────────────────
// Transparent background: the server trims the PNG to its ink and lays it on
// the form's signature line, so only the strokes may be opaque.
let drawing = false
let last = null

function setupPad() {
  const c = padEl.value
  if (!c) return
  const dpr = window.devicePixelRatio || 1
  const r = c.getBoundingClientRect()
  c.width = Math.round(r.width * dpr)
  c.height = Math.round(r.height * dpr)
  const ctx = c.getContext('2d')
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.lineWidth = 2.4
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.strokeStyle = '#14215a'
  hasInk.value = false
}

watch(step, async (s) => {
  if (s !== 1) return
  await nextTick()
  setupPad()
}, { immediate: true })
watch(() => props.assoc?.template_ready, async () => {
  if (step.value !== 1) return
  await nextTick()
  setupPad()
})

function padPoint(e) {
  const r = padEl.value.getBoundingClientRect()
  return { x: e.clientX - r.left, y: e.clientY - r.top }
}
function padDown(e) {
  if (!padEl.value) return
  padEl.value.setPointerCapture?.(e.pointerId)
  drawing = true
  last = padPoint(e)
  const ctx = padEl.value.getContext('2d')
  ctx.beginPath()
  ctx.arc(last.x, last.y, 1.1, 0, Math.PI * 2)
  ctx.fillStyle = ctx.strokeStyle
  ctx.fill()
}
function padMove(e) {
  if (!drawing) return
  const p = padPoint(e)
  const ctx = padEl.value.getContext('2d')
  ctx.beginPath()
  ctx.moveTo(last.x, last.y)
  ctx.lineTo(p.x, p.y)
  ctx.stroke()
  last = p
  hasInk.value = true
}
function padUp() {
  drawing = false
  last = null
}
function clearPad() {
  setupPad()
  signatureData.value = ''
  previewPages.value = []
}

async function makePreview() {
  if (!canSign.value || !padEl.value) return
  error.value = ''
  busy.value = true
  try {
    const signature = padEl.value.toDataURL('image/png')
    const { data } = await api.post('/maslaka/association/preview', {
      signature,
      signer_name: signerName.value.trim(),
      signer_id_number: signerDigits.value,
    })
    signatureData.value = signature
    previewPages.value = data.pages || []
    emit('changed')
    step.value = 2
  } catch (e) {
    error.value = detailOf(e, 'הכנת הטופס נכשלה')
  } finally {
    busy.value = false
  }
}

async function submit() {
  if (!signatureData.value) return
  error.value = ''
  busy.value = true
  try {
    const { data } = await api.post('/maslaka/association/sign', {
      signature: signatureData.value,
      signer_name: signerName.value.trim(),
      signer_id_number: signerDigits.value,
      // Monthly production (2100) opens on approval — always on, not a question for the agent.
      auto_production: true,
    })
    deliveryNote.value = data.delivery_note || ''
    signatureData.value = ''
    previewPages.value = []
    emit('changed')
    step.value = 3
  } catch (e) {
    error.value = detailOf(e, 'שליחת הטופס נכשלה')
  } finally {
    busy.value = false
  }
}

async function openSigned() {
  error.value = ''
  try {
    const { data } = await api.get('/maslaka/association/signed', { responseType: 'blob' })
    const url = URL.createObjectURL(data)
    window.open(url, '_blank', 'noopener')
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  } catch {
    error.value = 'פתיחת הטופס נכשלה'
  }
}
</script>

<style scoped>
.ma-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgba(0, 0, 0, 0.45);
}
.ma-inline { display: block; }
.ma-inline .ma-card { width: 100%; box-shadow: var(--shadow-sm); border: 1px solid var(--border-subtle); }
.ma-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 0.72fr;
  width: min(980px, 100%);
  /* FIXED height, not max: the steps differ in length, and a max-height made
     the card (and the photo) jump on every step. The form pane scrolls. */
  height: min(660px, calc(100vh - 32px));
  background: var(--card-bg);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  overflow: hidden;
}
.ma-form {
  position: relative;
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 0;
  overflow-y: auto;
  border-top: 4px solid var(--tab-maslaka);
}
.ma-form > .ma-foot { margin-top: auto; }
.ma-art { position: relative; overflow: hidden; background: var(--bg); }
.ma-art img { width: 100%; height: 100%; object-fit: cover; object-position: center 55%; display: block; }
/* A wash in the מסלקה tab's own teal, so the photograph reads as part of the
   product rather than dropped-in stock. */
.ma-art-veil {
  position: absolute; inset: 0; pointer-events: none;
  background:
    linear-gradient(200deg, color-mix(in srgb, var(--tab-maslaka) 26%, transparent) 0%, transparent 52%),
    linear-gradient(to left, rgba(255, 255, 255, 0.26), transparent 38%);
}
@media (max-width: 860px) {
  /* Below this the photo would squeeze the steps; the steps are the job. */
  .ma-card { grid-template-columns: 1fr; width: min(640px, 100%); height: auto; max-height: calc(100vh - 32px); }
  .ma-art { display: none; }
}
.ma-close {
  position: absolute;
  top: 14px;
  inset-inline-end: 14px;
  display: inline-flex;
  padding: 6px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}
.ma-close:hover { background: var(--bg); color: var(--text); }
.ma-close:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 1px; }

.ma-head { padding: 24px 28px 4px; padding-inline-end: 56px; }
.ma-title {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 800;
  letter-spacing: -0.015em;
  color: var(--text);
}
.ma-sub { margin: 6px 0 0; font-size: 0.88rem; line-height: 1.6; color: var(--text-muted); max-width: 56ch; }

/* ── Step track ─────────────────────────────────────────────── */
.ma-track {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  margin: 18px 28px 0;
  padding: 0;
  list-style: none;
}
.ma-track-btn {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 10px 0 0;
  border: none;
  border-top: 3px solid var(--border-subtle);
  background: none;
  font-family: inherit;
  text-align: start;
  color: var(--text-muted);
  cursor: pointer;
}
.ma-track-btn:disabled { cursor: default; }
.ma-track-btn:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }
.ma-track-step--done .ma-track-btn { border-top-color: color-mix(in srgb, var(--tab-maslaka) 45%, transparent); color: var(--text-secondary); }
.ma-track-step--on .ma-track-btn { border-top-color: var(--tab-maslaka); color: var(--text); }
.ma-track-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  font-size: 0.72rem;
  font-weight: 800;
  background: var(--bg);
  color: var(--text-muted);
}
.ma-track-step--done .ma-track-mark { background: var(--tab-maslaka-wash); color: var(--tab-maslaka); }
.ma-track-step--on .ma-track-mark { background: var(--tab-maslaka); color: #fff; }
.ma-track-label { font-size: 0.8rem; font-weight: 700; }

/* ── Body ───────────────────────────────────────────────────── */
.ma-body { padding: 20px 28px 8px; display: flex; flex-direction: column; gap: 12px; }
.ma-pane { display: flex; flex-direction: column; gap: 14px; }
.ma-lead { margin: 0; font-size: 0.9rem; line-height: 1.7; color: var(--text-secondary); max-width: 62ch; }

.ma-fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px; }
.ma-field { display: flex; flex-direction: column; gap: 5px; min-width: 0; }
.ma-field label { font-size: 0.78rem; font-weight: 600; color: var(--text-secondary); }
.ma-field input {
  height: 42px;
  padding: 0 12px;
  font-family: inherit;
  font-size: 0.9rem;
  color: var(--text);
  background: var(--bg-surface, var(--card-bg));
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}
.ma-field input:hover { border-color: var(--tab-maslaka); }
.ma-field input:focus { outline: none; border-color: var(--tab-maslaka); box-shadow: 0 0 0 3px var(--tab-maslaka-wash); }
.ma-field input[aria-invalid='true'] { border-color: var(--red-deep); }
.ma-help { font-size: 0.72rem; line-height: 1.4; color: var(--text-muted); }
.ma-help--bad { color: var(--red-deep); font-weight: 600; }

/* ── Signature ──────────────────────────────────────────────── */
.ma-sign { display: flex; flex-direction: column; gap: 6px; }
.ma-sign-head { display: flex; align-items: baseline; gap: 12px; }
.ma-sign-label { font-size: 0.78rem; font-weight: 600; color: var(--text-secondary); }
.ma-link {
  margin-inline-start: auto;
  padding: 0;
  border: none;
  background: none;
  font-family: inherit;
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--tab-maslaka);
  cursor: pointer;
}
.ma-link:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }
.ma-pad {
  position: relative;
  height: 170px;
  border: 1.5px dashed var(--border);
  border-radius: var(--radius-md);
  background: var(--card-bg);
  transition: border-color 0.15s;
}
.ma-pad:hover, .ma-pad--ink { border-color: var(--tab-maslaka); border-style: solid; }
.ma-pad-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  touch-action: none;
  cursor: crosshair;
  z-index: 1;
}
.ma-pad-hint {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.86rem;
  color: var(--text-muted);
  pointer-events: none;
}
.ma-pad-line {
  position: absolute;
  inset-inline: 28px;
  bottom: 38px;
  border-bottom: 1px solid var(--border);
  pointer-events: none;
}

/* ── Review ───────────────────────────────────────────────────── */
.ma-art--doc {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  overflow-y: auto;
  background: color-mix(in srgb, var(--tab-maslaka) 10%, var(--bg));
}
.ma-art .ma-doc-page {
  width: 100%;
  height: auto;
  object-fit: contain;
  flex-shrink: 0;
  border-radius: 3px;
  box-shadow: var(--shadow-md, var(--shadow-sm));
  background: #fff;
}
.ma-preview {
  display: none;
  flex-direction: column;
  gap: 10px;
  max-height: 320px;
  overflow-y: auto;
  padding: 10px;
  border-radius: var(--radius-md);
  background: var(--bg);
}
.ma-preview-page {
  width: 100%;
  display: block;
  border-radius: 3px;
  box-shadow: var(--shadow-sm);
  background: #fff;
}
@media (max-width: 860px) { .ma-preview { display: flex; } }

/* ── State + notes ──────────────────────────────────────────── */
.ma-state {
  display: flex;
  gap: 14px;
  padding: 16px;
  border-radius: var(--radius-md);
  background: var(--amber-light);
  --ma-ink: color-mix(in srgb, var(--amber) 62%, #000);
}
.ma-state--ok { background: var(--green-light); --ma-ink: color-mix(in srgb, var(--green) 82%, #000); }
.ma-state--bad { background: var(--red-light); --ma-ink: var(--red-deep); }
.ma-state-icon { color: var(--ma-ink); flex-shrink: 0; }
.ma-state-texts { display: flex; flex-direction: column; gap: 4px; font-size: 0.86rem; line-height: 1.6; color: var(--text-secondary); }
.ma-state-texts strong { font-size: 0.95rem; color: var(--ma-ink); }

.ma-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 0;
  padding: 10px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.82rem;
  line-height: 1.55;
}
.ma-note svg { flex-shrink: 0; margin-top: 2px; }
.ma-note--wait { background: var(--amber-light); color: color-mix(in srgb, var(--amber) 62%, #000); }
.ma-note--ok { background: var(--bg); color: var(--text-secondary); }
.ma-note--bad { background: var(--red-light); color: var(--red-deep); font-weight: 600; }
.ma-error { margin: 0; font-size: 0.84rem; font-weight: 600; color: var(--red-deep); }

.ma-reply {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-inline-start: 3px solid var(--tab-maslaka);
  border-radius: var(--radius-sm);
  background: var(--card-bg);
}
.ma-reply-head { display: flex; align-items: center; gap: 8px; font-size: 0.88rem; color: var(--text); }
.ma-reply-head svg { color: var(--tab-maslaka); flex-shrink: 0; }
.ma-reply-date { margin-inline-start: auto; font-size: 0.76rem; color: var(--text-muted); }
.ma-reply-subject { margin: 0; font-size: 0.82rem; font-weight: 600; color: var(--text-secondary); }
.ma-reply-body {
  margin: 0;
  padding: 10px 12px;
  max-height: 160px;
  overflow-y: auto;
  white-space: pre-wrap;
  font-size: 0.84rem;
  line-height: 1.6;
  color: var(--text-secondary);
  background: var(--bg);
  border-radius: var(--radius-sm);
}

/* ── Footer ─────────────────────────────────────────────────── */
.ma-foot {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  padding: 14px 28px 24px;
}
.ma-primary, .ma-secondary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 42px;
  padding: 0 22px;
  font-family: inherit;
  font-size: 0.88rem;
  font-weight: 700;
  border-radius: var(--radius-sm);
  cursor: pointer;
}
.ma-primary { color: #fff; background: var(--tab-maslaka); border: 1px solid var(--tab-maslaka); }
.ma-primary:hover:not(:disabled) { filter: brightness(1.1); }
.ma-primary:disabled { opacity: 0.45; cursor: not-allowed; }
.ma-secondary { color: var(--tab-maslaka); background: var(--card-bg); border: 1px solid color-mix(in srgb, var(--tab-maslaka) 35%, transparent); }
.ma-secondary:hover { background: var(--tab-maslaka-wash); }
.ma-primary:focus-visible, .ma-secondary:focus-visible { outline: 2px solid var(--tab-maslaka); outline-offset: 2px; }
.ma-spinner {
  width: 14px; height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.4);
  border-top-color: #fff;
  border-radius: 50%;
  animation: ma-spin 0.8s linear infinite;
}
@keyframes ma-spin { to { transform: rotate(360deg); } }

/* ── Transition ─────────────────────────────────────────────── */
.modal-enter-active, .modal-leave-active { transition: opacity 0.2s ease; }
.modal-enter-active .ma-card, .modal-leave-active .ma-card { transition: transform 0.24s ease, opacity 0.24s ease; }
.modal-enter-from, .modal-leave-to { opacity: 0; }
.modal-enter-from .ma-card, .modal-leave-to .ma-card { opacity: 0; transform: translateY(10px); }

@media (max-width: 560px) {
  .ma-head, .ma-body, .ma-foot { padding-inline: 16px; }
  .ma-track { margin-inline: 16px; }
  .ma-track-label { font-size: 0.7rem; }
}
@media (prefers-reduced-motion: reduce) {
  .ma-spinner { animation: none; }
  .modal-enter-active, .modal-leave-active,
  .modal-enter-active .ma-card, .modal-leave-active .ma-card { transition: none; }
}
</style>
