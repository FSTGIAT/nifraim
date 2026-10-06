<template>
  <!-- A call's follow-up email to the customer, opened like a letter: the
       envelope grows out of the pressed pill (useOriginMorph), the Mail
       Agent's own envelope opening plays (MailEnvelopeIntro — same island,
       same Remotion composition), and then only the letter is left to edit
       and send. Closing mirrors it: the letter folds into the envelope, the
       envelope seals and shrinks back into the pill. -->
  <Teleport to="body">
    <Transition name="cfl-fade" appear>
      <div class="cfl-overlay" :class="{ 'cfl-overlay--closing': closing }" @click.self="close">
        <div ref="stageEl" class="cfl-stage">
          <MailEnvelopeIntro
            v-if="!introDone || closing" :key="closing ? 'close' : 'open'"
            :name="toLabel" :initial="initialOf(toLabel)" :reverse="closing"
            @done="closing ? afterFold() : (introDone = true)"
          />
          <Transition name="cfl-letter" appear>
            <article v-if="introDone" class="cfl-letter" :class="{ 'cfl-letter--folding': closing }" dir="rtl"
                     role="dialog" aria-modal="true" aria-labelledby="cfl-title">
              <header class="cfl-head">
                <span class="cfl-avatar" aria-hidden="true">{{ initialOf(toLabel) }}</span>
                <div class="cfl-titles">
                  <h4 id="cfl-title">סיכום שיחה אל {{ fu.toName || 'הלקוח' }}</h4>
                  <span class="cfl-sub">{{ card.call_title || card.title }}</span>
                </div>
                <button class="cfl-x" type="button" aria-label="סגור" @click="close">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
                </button>
              </header>

              <div class="cfl-body">
                <div class="cfl-to">
                  <label class="cfl-field cfl-field--name">
                    <span class="cfl-label">אל</span>
                    <input v-model.trim="fu.toName" class="cfl-in" placeholder="שם הלקוח" />
                  </label>
                  <label class="cfl-field">
                    <span class="cfl-label">מייל</span>
                    <input v-model.trim="fu.toEmail" class="cfl-in" type="email" dir="ltr" placeholder="name@example.com" />
                  </label>
                </div>
                <template v-if="!card.customer_matched || !card.to_email">
                  <p class="cfl-hint">לא זיהיתי את הלקוח — הקלידו מייל</p>
                  <div class="cfl-pick">
                    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
                    <input v-model="fu.search" placeholder="או חפשו לקוח לפי שם או ת.ז" aria-label="חיפוש לקוח" @input="searchContact" />
                  </div>
                  <ul v-if="fu.results.length" class="cfl-pick-list">
                    <li v-for="(c, k) in fu.results" :key="k">
                      <button type="button" @click="pickContact(c)">
                        <strong>{{ c.name }}</strong>
                        <small v-if="c.email" dir="ltr">{{ c.email }}</small>
                        <small v-else>אין מייל במערכת</small>
                      </button>
                    </li>
                  </ul>
                </template>
                <label class="cfl-field cfl-field--subject">
                  <span class="cfl-label">נושא</span>
                  <input v-model="fu.subject" class="cfl-in cfl-in--subject" />
                </label>
                <textarea v-model="fu.body" class="cfl-text" rows="12" aria-label="תוכן המייל"></textarea>
                <p v-if="store.error" class="cfl-err" role="alert">
                  {{ store.error }}
                  <button v-if="store.errorCode === 'not_connected' || store.errorCode === 'cannot_send'" type="button" class="cfl-link" @click="$emit('open-mail')">חיבור Mail Agent</button>
                </p>
              </div>

              <footer class="cfl-foot">
                <button type="button" class="cfl-send" :disabled="!canSend || !!store.busy" @click="send">
                  {{ store.busy === card.id + ':send_followup' ? 'שולח…' : 'אישור ושליחה' }}
                </button>
                <button type="button" class="cfl-quiet" :disabled="!!store.busy" @click="dismiss">טופל</button>
                <button v-if="nextCount" type="button" class="cfl-quiet cfl-next" :disabled="!!store.busy" @click="$emit('next')">
                  הבא <span class="cfl-next-n ltr-number">{{ nextCount }}</span>
                  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>
                </button>
                <span class="cfl-gap"></span>
                <button type="button" class="cfl-plain" @click="$emit('open-call', card.ref)">לסיכום המלא</button>
              </footer>
            </article>
          </Transition>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useOfficeAgentStore } from '../../stores/officeAgent.js'
import { useOriginMorph } from '../../composables/useOriginMorph.js'
import MailEnvelopeIntro from './MailEnvelopeIntro.vue'

const props = defineProps({
  card: { type: Object, required: true },
  origin: { type: Object, default: null }, // the pressed pill
  nextCount: { type: Number, default: 0 }, // more follow-ups waiting → "הבא"
  skipIntro: { type: Boolean, default: false }, // reached with "הבא": the envelope already opened once
})
const emit = defineEmits(['close', 'sent', 'dismissed', 'open-call', 'open-mail', 'next'])
const store = useOfficeAgentStore()
const reduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

const known = props.card.customer_matched && props.card.to_email
const fu = reactive({
  toName: props.card.to_name || '',
  toEmail: known ? props.card.to_email : (props.card.to_email || ''),
  subject: props.card.draft_subject || '',
  body: props.card.draft_body || '',
  search: '',
  results: [],
})
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
const canSend = computed(() => EMAIL_RE.test(fu.toEmail) && !!fu.subject.trim() && !!fu.body.trim())
const toLabel = computed(() => fu.toName || fu.toEmail || 'הלקוח')
const initialOf = (s) => (s || '?').trim().charAt(0).toUpperCase() || '?'

let searchTimer = 0
function searchContact() {
  clearTimeout(searchTimer)
  const q = fu.search.trim()
  if (!q) { fu.results = []; return }
  searchTimer = setTimeout(async () => {
    fu.results = (await store.searchContacts(q)).filter((c) => c.kind !== 'company').slice(0, 6)
  }, 150)
}
function pickContact(c) {
  fu.toName = c.name || ''
  if (c.email) fu.toEmail = c.email
  fu.search = ''
  fu.results = []
}

// ── open: grow from the pill, the envelope opens, then the letter alone ──
const stageEl = ref(null)
const morph = useOriginMorph()
const introDone = ref(reduced || props.skipIntro)
const closing = ref(false)
onMounted(async () => {
  store.error = ''
  store.errorCode = ''
  if (reduced || props.skipIntro) return
  morph.remember(props.origin)
  await nextTick()
  morph.grow(stageEl.value)
})

// ── close: the letter folds into the envelope, it seals, and shrinks into the pill ──
let done = false
let outcome = null
function close() {
  if (done) return
  if (reduced || closing.value) { finish(); return }
  closing.value = true
}
async function afterFold() {
  if (morph.hasOrigin() && stageEl.value) await morph.shrink(stageEl.value)
  finish()
}
function finish() {
  if (done) return
  done = true
  if (outcome) emit(outcome.kind, outcome.value)
  emit('close')
}

async function send() {
  const ok = await store.act(props.card, 'send_followup', { to_email: fu.toEmail, to_name: fu.toName, subject: fu.subject, body: fu.body })
  if (ok) advanceOr({ kind: 'sent', value: fu.toName || fu.toEmail })
}
async function dismiss() {
  if (await store.act(props.card, 'dismiss_followup')) advanceOr({ kind: 'dismissed', value: null })
}
// handled one → straight to the next waiting letter; the last one folds the envelope closed
function advanceOr(o) {
  if (props.nextCount) { emit(o.kind, o.value); emit('next'); return }
  outcome = o
  close()
}

// Escape closes the letter (not the agent behind it)
function onKey(e) {
  if (e.key !== 'Escape') return
  e.preventDefault()
  e.stopPropagation()
  close()
}
onMounted(() => window.addEventListener('keydown', onKey, true))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey, true))
</script>

<style scoped>
.cfl-overlay {
  --ml-acc: var(--tab-mail, #4E9DD0); --ml-ink: var(--tab-mail-ink, #2F6C94); --ml-wash: var(--tab-mail-wash, rgba(78, 157, 208, 0.12));
  position: fixed; inset: 0; z-index: 1450; display: flex; align-items: center; justify-content: center;
  padding: 16px; background: rgba(15, 30, 45, 0.5); font-family: 'Heebo', sans-serif;
}
.cfl-overlay--closing { background: rgba(15, 30, 45, 0); transition: background 0.6s ease-in 0.5s; }
.cfl-stage { position: relative; display: grid; place-items: center; width: min(680px, 100%); }
.cfl-stage > * { grid-area: 1 / 1; }

.cfl-letter {
  position: relative; z-index: 1; width: 100%; max-height: calc(100dvh - 32px);
  display: flex; flex-direction: column; overflow: hidden;
  background: var(--card-bg); border-radius: var(--radius-lg, 16px); box-shadow: var(--shadow-lg, 0 24px 60px rgba(0, 0, 0, 0.25));
}
/* air-mail edge — the same stripe as the envelope and the Mail Agent letter */
.cfl-letter::before { content: ''; flex-shrink: 0; height: 6px; background: repeating-linear-gradient(-45deg, var(--ml-acc) 0 12px, var(--ml-ink) 12px 24px); }
/* folding back into the envelope (matches MailTab's .ml-letter--folding) */
.cfl-letter--folding {
  pointer-events: none; transform: translateY(-78px) scale(0.46); opacity: 0;
  transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1), opacity 0.16s ease-in 0.14s;
}
.cfl-head { display: flex; align-items: center; gap: 12px; padding: 18px 24px 10px; }
.cfl-avatar { width: 40px; height: 40px; flex: none; border-radius: 50%; display: grid; place-items: center; font-weight: 800; color: var(--ml-ink); background: var(--ml-wash); }
.cfl-titles { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.cfl-titles h4 { margin: 0; font-size: 17px; font-weight: 800; color: var(--text); }
.cfl-sub { font-size: 13px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.cfl-next { display: inline-flex; align-items: center; gap: 6px; }
.cfl-next-n { min-width: 20px; height: 20px; padding: 0 6px; border-radius: 999px; display: inline-grid; place-items: center;
  font-size: 12px; font-weight: 800; color: var(--ml-ink); background: var(--ml-wash); }
.cfl-x { display: inline-flex; padding: 8px; background: none; border: none; border-radius: 10px; color: var(--text-muted); cursor: pointer; }
.cfl-x:hover { background: var(--bg); color: var(--text); }

.cfl-body { flex: 1; overflow-y: auto; padding: 4px 24px 16px; display: flex; flex-direction: column; gap: 12px; }
.cfl-to { display: grid; grid-template-columns: minmax(0, 0.8fr) minmax(0, 1.2fr); gap: 12px; }
.cfl-field { display: flex; align-items: baseline; gap: 10px; padding-bottom: 6px; border-bottom: 1px solid var(--border-subtle); }
.cfl-label { flex: none; font-size: 13px; font-weight: 700; color: var(--text-muted); }
.cfl-in { flex: 1; min-width: 0; padding: 4px 0; font-family: inherit; font-size: 15px; color: var(--text); background: none; border: none; border-bottom: 2px solid transparent; }
.cfl-in:focus { outline: none; border-bottom-color: var(--ml-acc); }
.cfl-in--subject { font-weight: 700; }
.cfl-hint { margin: -4px 0 0; font-size: 13px; color: var(--text-secondary); }
.cfl-pick { display: flex; align-items: center; gap: 8px; height: 38px; padding: 0 12px; border-radius: 10px; background: var(--bg); color: var(--text-muted); }
.cfl-pick:focus-within { box-shadow: 0 0 0 2px var(--ml-acc); background: var(--card-bg); }
.cfl-pick input { flex: 1; min-width: 0; border: none; background: none; outline: none; font: inherit; font-size: 14px; color: var(--text); }
.cfl-pick-list { list-style: none; margin: -4px 0 0; padding: 4px; border-radius: 12px; border: 1px solid var(--border-subtle); }
.cfl-pick-list button { width: 100%; display: flex; align-items: baseline; justify-content: space-between; gap: 10px; padding: 8px 10px; border: none; background: none; border-radius: 8px; cursor: pointer; font-family: inherit; text-align: start; }
.cfl-pick-list button:hover { background: var(--bg); }
.cfl-pick-list strong { font-size: 14px; color: var(--text); }
.cfl-pick-list small { font-size: 12px; color: var(--text-muted); }
.cfl-text {
  min-height: 240px; resize: vertical; padding: 10px 2px; font-family: inherit; font-size: 16px; line-height: 1.75;
  color: var(--text); background: none; border: none; border-radius: 8px;
}
.cfl-text:focus { outline: 2px solid var(--ml-wash); outline-offset: 2px; }
.cfl-err { margin: 0; font-size: 13.5px; font-weight: 600; color: var(--red); display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.cfl-link { border: none; background: var(--ml-wash); color: var(--ml-ink); font: inherit; font-size: 13px; font-weight: 700; padding: 3px 10px; border-radius: 999px; cursor: pointer; }

.cfl-foot { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 14px 24px; border-top: 1px solid var(--border-subtle); background: var(--bg); }
.cfl-gap { flex: 1; }
.cfl-send {
  min-height: 44px; padding: 0 22px; border: none; border-radius: 10px; cursor: pointer; font-family: inherit; font-size: 15px; font-weight: 800;
  color: #fff; background: #181818; transition: transform 0.15s ease;
}
.cfl-send:hover:not(:disabled) { background: #000; transform: translateY(-1px); }
.cfl-send:disabled { opacity: 0.38; cursor: default; }
.cfl-quiet { min-height: 44px; padding: 0 16px; border: 1px solid var(--border-subtle); border-radius: 10px; background: var(--card-bg); color: var(--text-secondary); font-family: inherit; font-size: 14px; font-weight: 600; cursor: pointer; }
.cfl-quiet:hover:not(:disabled) { color: var(--text); border-color: #D5D2CE; }
.cfl-plain { border: none; background: none; color: var(--ml-ink); font-family: inherit; font-size: 14px; font-weight: 700; text-decoration: underline; text-underline-offset: 3px; cursor: pointer; padding: 8px 4px; }

.cfl-fade-enter-active { transition: opacity 0.2s ease-out; }
.cfl-fade-leave-active { transition: opacity 0.16s ease-in; }
.cfl-fade-enter-from, .cfl-fade-leave-to { opacity: 0; }
.cfl-letter-enter-active { transition: opacity 0.24s ease-out, transform 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.cfl-letter-enter-from { opacity: 0; transform: translateY(14px) scale(0.97); }

@media (max-width: 600px) {
  .cfl-overlay { padding: 0; align-items: stretch; }
  .cfl-stage { width: 100%; }
  .cfl-letter { max-height: 100dvh; height: 100dvh; border-radius: 0; }
  .cfl-to { grid-template-columns: 1fr; }
  .cfl-head, .cfl-body, .cfl-foot { padding-inline: 16px; }
}
@media (prefers-reduced-motion: reduce) {
  .cfl-letter--folding, .cfl-letter-enter-active, .cfl-send { transition: none; }
}
</style>
