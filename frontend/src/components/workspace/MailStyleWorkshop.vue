<template>
  <!-- The first-run "writing style" workshop. Rendered INSIDE the Mail Agent
       modal in place of the inbox. Form pane first in the DOM → the right side
       under RTL; the letter on the left writes itself as the agent answers. -->
  <div class="mw" dir="rtl">
    <div class="mw-form">
      <header class="mw-head">
        <h2 class="mw-title">איך אתם כותבים?</h2>
        <p class="mw-sub">כמה שאלות קצרות, וה-AI יכתוב טיוטות שנשמעות כמוכם. שום מייל לא נשלח בלי האישור שלכם.</p>
      </header>

      <ol class="mw-track">
        <li
          v-for="(s, i) in STEPS" :key="s.id" class="mw-track-step"
          :class="{ 'mw-track-step--on': i === step, 'mw-track-step--done': i < reached }"
        >
          <button type="button" class="mw-track-btn" :disabled="i > reached || busy" @click="go(i)">
            <span class="mw-track-mark" aria-hidden="true">
              <svg v-if="i < reached && i !== step" viewBox="0 0 24 24" width="12" height="12" fill="none"
                   stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m5 13 4 4L19 7" /></svg>
              <span v-else class="ltr-number">{{ i + 1 }}</span>
            </span>
            <span class="mw-track-label">{{ s.label }}</span>
          </button>
        </li>
      </ol>

      <div class="mw-body">
        <!-- 1. Signature -->
        <section v-if="step === 0" class="mw-step">
          <label class="mw-q" for="mw-sig">החתימה שלכם</label>
          <p class="mw-hint">תופיע בסוף כל תשובה, בדיוק כך.</p>
          <textarea id="mw-sig" v-model="p.signature" class="mw-input mw-sig" rows="4"
                    placeholder="שם מלא&#10;סוכנות&#10;טלפון"></textarea>
        </section>

        <!-- 2. Voice -->
        <section v-else-if="step === 1" class="mw-step">
          <p class="mw-q">איזה טון?</p>
          <div class="mw-picks mw-picks--3" role="radiogroup" aria-label="טון">
            <button
              v-for="t in TONES" :key="t.id" type="button" role="radio" class="mw-pick"
              :aria-checked="p.tone === t.id" :class="{ 'mw-pick--on': p.tone === t.id }" @click="p.tone = t.id"
            >
              <span class="mw-pick-title">{{ t.label }}</span>
              <span class="mw-pick-eg">{{ t.eg }}</span>
            </button>
          </div>

          <p class="mw-q">אתם כותבים…</p>
          <div class="mw-seg" role="radiogroup" aria-label="גוף ראשון">
            <button
              v-for="a in WRITER" :key="a.id" type="button" role="radio" class="mw-seg-btn"
              :aria-checked="p.writer_form === a.id" :class="{ 'mw-seg-btn--on': p.writer_form === a.id }"
              @click="p.writer_form = a.id"
            >{{ a.label }}</button>
          </div>

          <p class="mw-q">פונים ללקוח ב…</p>
          <div class="mw-seg" role="radiogroup" aria-label="לשון פנייה">
            <button
              v-for="a in ADDRESS" :key="a.id" type="button" role="radio" class="mw-seg-btn"
              :aria-checked="p.address_form === a.id" :class="{ 'mw-seg-btn--on': p.address_form === a.id }"
              @click="p.address_form = a.id"
            >{{ a.label }}</button>
          </div>

          <div class="mw-two">
            <div class="mw-field">
              <label class="mw-q" for="mw-greet">פתיחה</label>
              <input id="mw-greet" v-model="p.greeting" class="mw-input" type="text" placeholder="שלום רב," />
              <div class="mw-chips">
                <button v-for="g in GREETINGS" :key="g" type="button" class="mw-chip"
                        :class="{ 'mw-chip--on': p.greeting === g }" @click="p.greeting = g">{{ g }}</button>
              </div>
            </div>
            <div class="mw-field">
              <label class="mw-q" for="mw-close">סיום</label>
              <input id="mw-close" v-model="p.closing" class="mw-input" type="text" placeholder="בברכה," />
              <div class="mw-chips">
                <button v-for="c in CLOSINGS" :key="c" type="button" class="mw-chip"
                        :class="{ 'mw-chip--on': p.closing === c }" @click="p.closing = c">{{ c }}</button>
              </div>
            </div>
          </div>
          <p class="mw-hint">‏{שם} יוחלף בשם הנמען.</p>
        </section>

        <!-- 3. Learn from sent mail (optional) -->
        <section v-else-if="step === 2" class="mw-step">
          <p class="mw-q">ללמוד מהמיילים ששלחתם?</p>
          <p class="mw-hint">
            ה-AI יקרא רק תשובות ששלחתם לשולחים שבחרתם, רק את המילים שלכם (בלי ההודעה המצוטטת),
            ויציע תיאור של הסגנון. אתם מאשרים או עורכים.
          </p>

          <div v-if="!state?.can_learn" class="mw-note">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2"
                 stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9" /><path d="M12 8v4M12 16h.01" /></svg>
            <span>יהיה זמין אחרי שתחברו את תיבת המייל ותבחרו שולחים. אפשר לחזור לזה מ״סגנון הכתיבה שלי״.</span>
          </div>

          <template v-else>
            <button v-if="!learned" type="button" class="mw-learn" :disabled="busy" @click="onLearn">
              <span v-if="busy" class="mw-spinner mw-spinner--ink" aria-hidden="true"></span>
              <svg v-else viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2"
                   stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                <rect x="3" y="5" width="18" height="14" rx="2" /><path d="m3 7 9 6 9-6" />
              </svg>
              <span>{{ busy ? 'קורא את המיילים שלכם…' : (state?.learned_at ? 'ללמוד שוב מהמיילים שלי' : 'ללמוד מהמיילים שלי') }}</span>
            </button>

            <template v-if="learned || p.style_notes">
              <p v-if="learned" class="mw-done">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.6"
                     stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 13 4 4L19 7" /></svg>
                נקראו <span class="ltr-number">{{ learned.read_count }}</span> תשובות שלכם
              </p>
              <label class="mw-q" for="mw-notes">כך אתם כותבים</label>
              <textarea id="mw-notes" v-model="p.style_notes" class="mw-input" rows="5"></textarea>
              <template v-if="p.examples?.length">
                <p class="mw-q">דוגמאות שה-AI ילמד מהן</p>
                <p class="mw-hint">לטון בלבד — הוא לא מעתיק מהן פרטים. הסירו כל מה שלא תרצו שיישמר.</p>
                <div v-for="(ex, i) in p.examples" :key="i" class="mw-example">
                  <textarea v-model="p.examples[i]" class="mw-input" rows="3" :aria-label="`דוגמה ${i + 1}`"></textarea>
                  <button type="button" class="mw-x-sm" aria-label="הסרת הדוגמה" @click="p.examples.splice(i, 1)">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.2"
                         stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
                  </button>
                </div>
              </template>
            </template>
          </template>
        </section>

        <!-- 4. What to add -->
        <section v-else-if="step === 3" class="mw-step">
          <div class="mw-seg" role="tablist" aria-label="למי">
            <button v-for="r in RULE_TABS" :key="r.id" type="button" role="tab" class="mw-seg-btn"
                    :aria-selected="ruleTab === r.id" :class="{ 'mw-seg-btn--on': ruleTab === r.id }"
                    @click="ruleTab = r.id">{{ r.label }}</button>
          </div>
          <label class="mw-q" :for="`mw-r-${ruleTab}`">{{ currentRule.q }}</label>
          <textarea :id="`mw-r-${ruleTab}`" ref="ruleEl" v-model="p[currentRule.field]" class="mw-input" rows="5"
                    :placeholder="currentRule.placeholder"></textarea>
          <div class="mw-chips">
            <button v-for="c in currentRule.chips" :key="c" type="button" class="mw-chip mw-chip--add" @click="addLine(c)">
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.6"
                   stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
              {{ c.trim() }}
            </button>
          </div>
        </section>

        <!-- 5. Preview -->
        <section v-else class="mw-step">
          <div class="mw-seg" role="tablist" aria-label="דוגמה">
            <button v-for="k in PREVIEW_KINDS" :key="k.id" type="button" role="tab" class="mw-seg-btn"
                    :aria-selected="previewKind === k.id" :class="{ 'mw-seg-btn--on': previewKind === k.id }"
                    :disabled="busy" @click="runPreview(k.id)">{{ k.label }}</button>
          </div>
          <div v-if="preview" class="mw-incoming">
            <span class="mw-incoming-from">{{ preview.incoming.sender_label }}</span>
            <p class="mw-incoming-text">{{ preview.incoming.text }}</p>
          </div>
          <p v-if="busy" class="mw-hint">ה-AI כותב בשמכם…</p>
          <p v-else-if="preview" class="mw-hint">
            לקוחה ונתונים לדוגמה. מה שמסומן [להשלים] הוא מידע שאין במערכת — ה-AI לא ממציא אותו, אתם משלימים.
          </p>
          <!-- Narrow screens have no letter pane — the reply shows here. -->
          <pre v-if="preview" class="mw-letter-inline">{{ preview.body }}</pre>
          <ul v-if="preview?.warnings?.length" class="mw-warn">
            <li v-for="(w, i) in preview.warnings" :key="i">{{ w }}</li>
          </ul>
        </section>

        <p v-if="error" class="mw-error" role="alert">{{ error }}</p>
      </div>

      <footer class="mw-foot">
        <template v-if="step < 4">
          <button type="button" class="mw-primary" :disabled="busy" @click="next">
            <span v-if="busy && step !== 2" class="mw-spinner" aria-hidden="true"></span>
            <span>{{ step === 2 && !learned && !p.style_notes ? 'דלגו' : 'המשך' }}</span>
          </button>
          <button v-if="step > 0" type="button" class="mw-secondary" :disabled="busy" @click="go(step - 1)">חזרה</button>
        </template>
        <template v-else>
          <button type="button" class="mw-primary" :disabled="busy || !preview" @click="finish">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.4"
                 stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 13 4 4L19 7" /></svg>
            <span>זה נשמע כמוני</span>
          </button>
          <button type="button" class="mw-secondary" :disabled="busy" @click="go(1)">לא בדיוק</button>
        </template>
        <span class="mw-gap"></span>
        <button v-if="!state?.completed_at" type="button" class="mw-text" :disabled="busy" @click="later">אחר כך</button>
        <button v-else type="button" class="mw-text" :disabled="busy" @click="emit('done')">ביטול</button>
      </footer>
    </div>

    <!-- The letter: the one memorable thing. It assembles from the answers,
         and on the last step it becomes the AI's actual draft. -->
    <aside class="mw-art" aria-hidden="true">
      <img :src="artwork" alt="" />
      <div class="mw-art-veil"></div>
      <div class="mw-letter" :class="{ 'mw-letter--real': step === 4 && preview }">
        <div class="mw-letter-head">
          <span class="mw-letter-dot"></span>
          <span class="mw-letter-to">{{ step === 4 && preview ? preview.subject : 'Re: שאלה על ביטוח הבריאות' }}</span>
        </div>
        <template v-if="step === 4 && preview">
          <p class="mw-letter-real">{{ preview.body }}</p>
        </template>
        <template v-else-if="step === 4 && busy">
          <span class="mw-bar mw-bar--shimmer"></span><span class="mw-bar mw-bar--shimmer mw-bar--s"></span>
          <span class="mw-bar mw-bar--shimmer"></span>
        </template>
        <template v-else>
          <p class="mw-letter-line" :class="{ 'mw-letter-line--empty': !p.greeting }">{{ greetingShown || 'פתיחה' }}</p>
          <span class="mw-bar"></span>
          <span class="mw-bar mw-bar--s"></span>
          <p v-if="ruleLine" class="mw-letter-rule">{{ ruleLine }}</p>
          <span v-else class="mw-bar mw-bar--m"></span>
          <p class="mw-letter-line" :class="{ 'mw-letter-line--empty': !p.closing }">{{ p.closing || 'סיום' }}</p>
          <p class="mw-letter-sig" :class="{ 'mw-letter-line--empty': !p.signature?.trim() }">{{ p.signature?.trim() || 'החתימה שלכם' }}</p>
        </template>
      </div>
    </aside>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useMailAgentStore } from '../../stores/mailAgent.js'
import artwork from '../../assets/mail/workshop.webp'

const emit = defineEmits(['done'])
const store = useMailAgentStore()
const state = computed(() => store.profileState)

const STEPS = [
  { id: 'signature', label: 'חתימה' },
  { id: 'voice', label: 'טון' },
  { id: 'learn', label: 'מהמיילים שלכם' },
  { id: 'rules', label: 'מה להוסיף' },
  { id: 'preview', label: 'ככה זה יישמע' },
]
const TONES = [
  { id: 'formal', label: 'רשמי', eg: 'בהמשך לפנייתך, הריני לעדכן…' },
  { id: 'warm', label: 'חם ואישי', eg: 'שמחתי שכתבת! בדקתי בשבילך…' },
  { id: 'short', label: 'קצר ולעניין', eg: 'בדקתי — הכל בתוקף.' },
]
const WRITER = [
  { id: 'male', label: 'אני כותב' },
  { id: 'female', label: 'אני כותבת' },
  { id: 'we', label: 'אנחנו (הסוכנות)' },
]
const ADDRESS = [
  { id: 'plural', label: 'אתם' },
  { id: 'female', label: 'את' },
  { id: 'male', label: 'אתה' },
  { id: 'name', label: 'בשם הפרטי' },
]
const GREETINGS = ['שלום רב,', 'היי {שם},', '{שם} שלום,']
const CLOSINGS = ['בברכה,', 'בברכה ובהצלחה,', 'תמיד כאן לכל שאלה,']
const RULE_TABS = [
  { id: 'customer', label: 'כשלקוח כותב' },
  { id: 'insurer', label: 'כשחברה כותבת' },
  { id: 'never', label: 'אסור לכתוב' },
]
const RULES = {
  customer: {
    field: 'customer_rules', q: 'מה תמיד להוסיף בתשובה ללקוח?',
    placeholder: 'שורה לכל דבר',
    chips: ['שעות פעילות: ', 'לתיאום פגישה: ', 'לכל שאלה אפשר להתקשר למשרד: ', 'המידע כללי; הפרטים המחייבים הם אלה שבפוליסה.'],
  },
  insurer: {
    field: 'insurer_rules', q: 'מה תמיד להוסיף בתשובה לחברת ביטוח?',
    placeholder: 'שורה לכל דבר',
    chips: ['מספר סוכן: ', 'נא לאשר קבלת מייל זה.', 'לציין את מספר הפוליסה בכל פנייה.'],
  },
  never: {
    field: 'never_say', q: 'מה ה-AI לא יכתוב או יבטיח לעולם?',
    placeholder: 'שורה לכל דבר',
    chips: ['לא להבטיח אישור תביעה.', 'לא להתחייב למועד תשלום.', 'לא לציין סכומי עמלה ללקוח.'],
  },
}
const PREVIEW_KINDS = [
  { id: 'customer', label: 'לקוחה שואלת' },
  { id: 'insurer', label: 'חברה מבקשת' },
]
const FIELDS = ['signature', 'tone', 'address_form', 'writer_form', 'greeting', 'closing', 'customer_rules', 'insurer_rules',
  'never_say', 'style_notes', 'examples']

const p = reactive({
  signature: '', tone: null, address_form: null, writer_form: null, greeting: '', closing: '',
  customer_rules: '', insurer_rules: '', never_say: '', style_notes: '', examples: [],
})
const step = ref(0)
const reached = ref(0)
const busy = ref(false)
const error = ref('')
const learned = ref(null)
const preview = ref(null)
const previewKind = ref('customer')
const ruleTab = ref('customer')
const ruleEl = ref(null)

const currentRule = computed(() => RULES[ruleTab.value])
const greetingShown = computed(() => (p.greeting || '').replace('{שם}', 'דנה'))
const ruleLine = computed(() => (p.customer_rules || '').split('\n').map((s) => s.trim()).find(Boolean) || '')

function payload() {
  const out = {}
  for (const f of FIELDS) out[f] = f === 'examples' ? (p.examples || []).filter((x) => x.trim()) : p[f]
  return out
}

onMounted(async () => {
  const s = state.value || (await store.fetchProfile())
  const prof = s?.profile || {}
  for (const f of FIELDS) {
    if (prof[f] != null) p[f] = f === 'examples' ? [...prof[f]] : prof[f]
  }
  // A returning agent (finished or skipped before) may jump anywhere.
  if (s?.completed_at || s?.skipped_at) reached.value = 4
})

async function persist() {
  await store.saveProfile(payload())
}

async function go(i) {
  error.value = ''
  step.value = i
  reached.value = Math.max(reached.value, i)
  if (i === 4 && !preview.value) await runPreview(previewKind.value)
}

async function next() {
  error.value = ''
  busy.value = true
  try {
    await persist()
  } catch (e) {
    error.value = e.message
    return
  } finally {
    busy.value = false
  }
  await go(step.value + 1)
}

async function onLearn() {
  error.value = ''
  busy.value = true
  try {
    const s = await store.learnStyle()
    learned.value = s
    p.style_notes = s.style_notes || p.style_notes
    p.examples = s.examples?.length ? [...s.examples] : p.examples
    // Suggestions fill only what the agent has not answered themselves.
    if (!p.greeting && s.greeting) p.greeting = s.greeting
    if (!p.closing && s.closing) p.closing = s.closing
    if (!p.tone && s.tone) p.tone = s.tone
    if (!p.address_form && s.address_form) p.address_form = s.address_form
    if (!p.writer_form && s.writer_form) p.writer_form = s.writer_form
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function addLine(text) {
  const f = currentRule.value.field
  const cur = (p[f] || '').replace(/\s+$/, '')
  const has = cur.split('\n').some((l) => l.trim().startsWith(text.trim()))
  if (!has) p[f] = cur ? `${cur}\n${text}` : text
  await nextTick()
  const el = ruleEl.value
  if (el) { el.focus(); el.setSelectionRange(el.value.length, el.value.length) }
}

async function runPreview(kind) {
  previewKind.value = kind
  error.value = ''
  busy.value = true
  preview.value = null
  try {
    preview.value = await store.previewStyle(payload(), kind)
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function finish() {
  busy.value = true
  error.value = ''
  try {
    await store.saveProfile({ ...payload(), complete: true })
    store.styleJustDone = true
    emit('done')
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}

async function later() {
  busy.value = true
  try {
    await store.saveProfile({ ...payload(), skip: true })
  } catch { /* the inbox still opens; the workshop will ask again */ }
  busy.value = false
  emit('done')
}
</script>

<style scoped>
.mw {
  --mw-acc: var(--tab-mail);
  --mw-ink: var(--tab-mail-ink);
  --mw-wash: var(--tab-mail-wash);
  display: grid; grid-template-columns: minmax(0, 1fr) 0.8fr;
  height: 100%; min-height: 0; background: var(--card-bg);
}
.mw-form {
  display: flex; flex-direction: column; min-width: 0; min-height: 0; overflow-y: auto;
  border-top: 4px solid var(--mw-acc);
}
.mw-form > .mw-foot { margin-top: auto; }

.mw-head { padding: 28px 32px 4px; padding-inline-end: 64px; }
.mw-title {
  margin: 0; font-family: 'Rubik', 'Heebo', sans-serif; font-size: clamp(26px, 2.6vw, 34px);
  font-weight: 700; letter-spacing: -0.03em; line-height: 1.1; color: var(--text);
}
.mw-sub { margin: 8px 0 0; font-size: 0.9rem; line-height: 1.6; color: var(--text-muted); max-width: 56ch; }

/* ── Step track (a real sequence → numbered) ─────────────────── */
.mw-track { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin: 20px 32px 0; padding: 0; list-style: none; }
.mw-track-btn {
  width: 100%; display: flex; flex-direction: column; align-items: flex-start; gap: 6px; padding: 10px 0 0;
  border: none; border-top: 3px solid var(--border-subtle); background: none; font-family: inherit;
  text-align: start; color: var(--text-muted); cursor: pointer;
}
.mw-track-btn:disabled { cursor: default; }
.mw-track-btn:focus-visible { outline: 2px solid var(--mw-acc); outline-offset: 2px; }
.mw-track-step--done .mw-track-btn { border-top-color: color-mix(in srgb, var(--mw-acc) 45%, transparent); color: var(--text-secondary); }
.mw-track-step--on .mw-track-btn { border-top-color: var(--mw-acc); color: var(--text); }
.mw-track-mark {
  display: inline-flex; align-items: center; justify-content: center; width: 22px; height: 22px; border-radius: 50%;
  font-size: 0.72rem; font-weight: 800; background: var(--bg); color: var(--text-muted);
}
.mw-track-step--done .mw-track-mark { background: var(--mw-wash); color: var(--mw-ink); }
.mw-track-step--on .mw-track-mark { background: var(--mw-acc); color: #fff; }
.mw-track-label { font-size: 0.78rem; font-weight: 700; }

/* ── Body ───────────────────────────────────────────────────── */
.mw-body { padding: 22px 32px 8px; }
.mw-step { display: flex; flex-direction: column; gap: 10px; }
.mw-q { margin: 6px 0 0; font-size: 0.95rem; font-weight: 700; color: var(--text); }
.mw-hint { margin: 0; font-size: 0.8rem; line-height: 1.55; color: var(--text-muted); max-width: 60ch; }
.mw-input {
  width: 100%; box-sizing: border-box; padding: 10px 12px; font-family: inherit; font-size: 0.92rem; line-height: 1.6;
  color: var(--text); background: var(--bg-surface, var(--card-bg)); border: 1px solid var(--border);
  border-radius: var(--radius-sm); resize: vertical;
}
input.mw-input { height: 42px; padding-block: 0; }
.mw-input:hover { border-color: var(--mw-acc); }
.mw-input:focus { outline: none; border-color: var(--mw-acc); box-shadow: 0 0 0 3px var(--mw-wash); }
.mw-sig { font-size: 1rem; }

.mw-picks { display: grid; gap: 10px; }
.mw-picks--3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.mw-pick {
  display: flex; flex-direction: column; align-items: flex-start; gap: 6px; padding: 14px; min-height: 96px;
  font-family: inherit; text-align: start; cursor: pointer; background: var(--card-bg);
  border: 1.5px solid var(--border); border-radius: var(--radius-md); transition: border-color 0.15s, background 0.15s;
}
.mw-pick:hover { border-color: var(--mw-acc); }
.mw-pick--on { border-color: var(--mw-acc); background: var(--mw-wash); }
.mw-pick:focus-visible, .mw-seg-btn:focus-visible, .mw-chip:focus-visible { outline: 2px solid var(--mw-acc); outline-offset: 2px; }
.mw-pick-title { font-size: 0.98rem; font-weight: 800; color: var(--text); }
.mw-pick--on .mw-pick-title { color: var(--mw-ink); }
.mw-pick-eg { font-size: 0.8rem; line-height: 1.5; color: var(--text-muted); }

.mw-seg { display: inline-flex; align-self: flex-start; flex-wrap: wrap; gap: 4px; padding: 4px; background: var(--bg); border-radius: 999px; }
.mw-seg-btn {
  padding: 7px 16px; border: none; border-radius: 999px; font-family: inherit; font-size: 0.86rem; font-weight: 700;
  color: var(--text-secondary); background: transparent; cursor: pointer;
}
.mw-seg-btn--on { background: var(--card-bg); color: var(--mw-ink); box-shadow: var(--shadow-sm); }
.mw-seg-btn:disabled { cursor: default; }

.mw-two { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.mw-field { display: flex; flex-direction: column; gap: 8px; min-width: 0; }
.mw-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.mw-chip {
  display: inline-flex; align-items: center; gap: 5px; padding: 5px 11px; font-family: inherit; font-size: 0.8rem; font-weight: 600;
  color: var(--text-secondary); background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: 999px; cursor: pointer;
}
.mw-chip:hover { border-color: var(--mw-acc); color: var(--mw-ink); }
.mw-chip--on { background: var(--mw-wash); border-color: transparent; color: var(--mw-ink); }
.mw-chip--add svg { color: var(--mw-acc); }

.mw-note {
  display: flex; gap: 8px; align-items: flex-start; padding: 12px 14px; border-radius: var(--radius-sm);
  font-size: 0.84rem; line-height: 1.55; background: var(--bg); color: var(--text-secondary);
}
.mw-note svg { flex-shrink: 0; margin-top: 2px; color: var(--mw-ink); }
.mw-learn {
  display: flex; align-items: center; justify-content: center; gap: 10px; padding: 18px; margin-top: 4px;
  font-family: inherit; font-size: 0.95rem; font-weight: 800; color: var(--mw-ink); cursor: pointer;
  background: var(--mw-wash); border: 1.5px dashed color-mix(in srgb, var(--mw-acc) 55%, transparent); border-radius: var(--radius-md);
}
.mw-learn:hover:not(:disabled) { border-style: solid; }
.mw-learn:disabled { cursor: progress; }
.mw-done { display: inline-flex; align-items: center; gap: 6px; margin: 0; font-size: 0.84rem; font-weight: 700; color: var(--mw-ink); }
.mw-example { position: relative; }
.mw-example .mw-input { padding-inline-end: 36px; font-size: 0.84rem; }
.mw-x-sm {
  position: absolute; top: 8px; inset-inline-end: 8px; display: inline-flex; padding: 4px; border: none; border-radius: 50%;
  background: var(--bg); color: var(--text-muted); cursor: pointer;
}
.mw-x-sm:hover { color: var(--red-deep); }

.mw-incoming { padding: 12px 14px; border-inline-start: 3px solid var(--border); background: var(--bg); border-radius: var(--radius-sm); }
.mw-incoming-from { font-size: 0.78rem; font-weight: 700; color: var(--text-muted); }
.mw-incoming-text { margin: 4px 0 0; font-size: 0.86rem; line-height: 1.6; color: var(--text-secondary); }
.mw-letter-inline { display: none; }
.mw-warn { margin: 0; padding: 10px 14px 10px 10px; padding-inline-start: 26px; border-radius: var(--radius-sm); background: var(--amber-light); font-size: 0.8rem; line-height: 1.55; color: var(--text-secondary); }
.mw-error { margin: 12px 0 0; font-size: 0.84rem; font-weight: 600; color: var(--red-deep); }

/* ── Footer ─────────────────────────────────────────────────── */
.mw-foot { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; padding: 16px 32px 26px; }
.mw-gap { flex: 1; }
.mw-primary, .mw-secondary {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px; height: 42px; padding: 0 24px;
  font-family: inherit; font-size: 0.9rem; font-weight: 700; border-radius: var(--radius-sm); cursor: pointer;
}
.mw-primary { color: #fff; background: var(--mw-acc); border: 1px solid var(--mw-acc); }
.mw-primary:hover:not(:disabled) { filter: brightness(1.08); }
.mw-primary:disabled, .mw-secondary:disabled { opacity: 0.45; cursor: not-allowed; }
.mw-secondary { color: var(--mw-ink); background: var(--card-bg); border: 1px solid color-mix(in srgb, var(--mw-acc) 35%, transparent); }
.mw-secondary:hover:not(:disabled) { background: var(--mw-wash); }
.mw-text { padding: 8px 10px; border: none; background: none; font-family: inherit; font-size: 0.86rem; font-weight: 600; color: var(--text-muted); cursor: pointer; }
.mw-text:hover { color: var(--text); }
.mw-primary:focus-visible, .mw-secondary:focus-visible, .mw-text:focus-visible, .mw-learn:focus-visible { outline: 2px solid var(--mw-acc); outline-offset: 2px; }
.mw-spinner {
  width: 14px; height: 14px; border: 2px solid rgba(255, 255, 255, 0.4); border-top-color: #fff; border-radius: 50%;
  animation: mw-spin 0.8s linear infinite;
}
.mw-spinner--ink { border-color: color-mix(in srgb, var(--mw-acc) 30%, transparent); border-top-color: var(--mw-ink); }
@keyframes mw-spin { to { transform: rotate(360deg); } }

/* ── The letter pane ────────────────────────────────────────── */
.mw-art { position: relative; overflow: hidden; background: var(--bg); display: flex; align-items: center; justify-content: center; }
.mw-art img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; display: block; }
.mw-art-veil {
  position: absolute; inset: 0; pointer-events: none;
  background:
    linear-gradient(200deg, color-mix(in srgb, var(--mw-acc) 30%, transparent) 0%, transparent 55%),
    linear-gradient(to top, rgba(0, 0, 0, 0.18), transparent 45%);
}
.mw-letter {
  position: relative; z-index: 1; width: min(78%, 360px); max-height: 78%; overflow: hidden;
  display: flex; flex-direction: column; gap: 9px; padding: 18px 20px 22px;
  background: #fff; color: #1f2933; border-radius: 6px; box-shadow: 0 18px 40px rgba(15, 40, 60, 0.28);
  transform: rotate(-1.4deg); transition: transform 0.35s ease;
}
.mw-letter--real { transform: rotate(0); overflow-y: auto; }
.mw-letter-head { display: flex; align-items: center; gap: 8px; padding-bottom: 10px; margin-bottom: 2px; border-bottom: 1px solid #e6ebef; }
.mw-letter-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--mw-acc); flex-shrink: 0; }
.mw-letter-to { font-size: 0.78rem; font-weight: 700; color: #52606d; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.mw-letter-line { margin: 0; font-size: 0.9rem; font-weight: 600; }
.mw-letter-line--empty { color: #b8c2cc; font-weight: 500; }
.mw-letter-rule { margin: 0; padding: 6px 8px; font-size: 0.8rem; border-radius: 4px; background: var(--mw-wash); color: var(--mw-ink); }
.mw-letter-sig { margin: 4px 0 0; font-size: 0.84rem; line-height: 1.5; white-space: pre-line; color: #3e4c59; }
.mw-letter-real { margin: 0; font-size: 0.84rem; line-height: 1.65; white-space: pre-wrap; }
.mw-bar { display: block; height: 8px; border-radius: 4px; background: #e9eef2; width: 100%; }
.mw-bar--s { width: 62%; }
.mw-bar--m { width: 80%; }
.mw-bar--shimmer {
  background: linear-gradient(90deg, #e9eef2 30%, color-mix(in srgb, var(--mw-acc) 25%, #fff) 50%, #e9eef2 70%);
  background-size: 250% 100%; animation: mw-shimmer 1.2s linear infinite;
}
@keyframes mw-shimmer { from { background-position: 150% 0; } to { background-position: -100% 0; } }

@media (max-width: 860px) {
  .mw { grid-template-columns: 1fr; }
  .mw-art { display: none; }
  .mw-letter-inline {
    display: block; margin: 0; padding: 14px 16px; white-space: pre-wrap; font-family: inherit; font-size: 0.86rem; line-height: 1.65;
    background: var(--card-bg); border: 1px solid var(--border); border-radius: var(--radius-sm);
  }
}
@media (max-width: 560px) {
  .mw-head, .mw-body, .mw-foot { padding-inline: 16px; }
  .mw-head { padding-top: 22px; padding-inline-end: 56px; }
  .mw-track { margin-inline: 16px; gap: 4px; }
  .mw-track-label { display: none; }
  .mw-picks--3, .mw-two { grid-template-columns: 1fr; }
  .mw-pick { min-height: 0; }
}
@media (prefers-reduced-motion: reduce) {
  .mw-spinner, .mw-bar--shimmer { animation: none; }
  .mw-letter { transition: none; }
}
</style>
