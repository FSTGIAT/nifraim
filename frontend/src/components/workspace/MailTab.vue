<template>
  <div class="ml">
    <!-- Hero — same shape as the other tabs: copy at the start edge, the
         looping scene at the end. The counters are the "what the AI did" beat. -->
    <header class="ml-hero" :class="{ 'ml-hero--scan': store.polling }">
      <div class="ml-hero-copy">
        <span class="ml-kicker">דואר חכם</span>
        <h2 class="ml-hero-title" dir="ltr">Nifraim <span class="ml-hero-title-acc">Mail Agent</span></h2>

        <div v-if="ready" class="ml-stats">
          <button type="button" class="ml-stat" :class="{ 'ml-stat--on': listFilter === 'ai' }" @click="showList('ai')">
            <span class="ml-stat-n ltr-number">{{ shown.processed }}</span>
            <span class="ml-stat-l">טופלו ע״י ה-AI</span>
          </button>
          <button type="button" class="ml-stat" :class="{ 'ml-stat--on': listFilter === 'sent' }" @click="showList('sent')">
            <span class="ml-stat-n ltr-number">{{ shown.sent }}</span>
            <span class="ml-stat-l">נשלחו</span>
          </button>
        </div>

        <div v-if="summary?.mailbox_connected" class="ml-meta">
          <span class="ml-chip">
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.4"
                 stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 13 4 4L19 7" /></svg>
            <span class="ltr-number">{{ summary.mailbox_address }}</span>
          </span>
          <button class="ml-icon-btn" type="button" :disabled="store.polling" :title="'בדיקה עכשיו'" @click="onPoll">
            <svg :class="{ 'ml-rot': store.polling }" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor"
                 stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M21 12a9 9 0 1 1-3-6.7L21 8" /><path d="M21 3v5h-5" />
            </svg>
            <span>{{ store.polling ? 'סורק…' : 'בדיקה' }}</span>
          </button>
          <button class="ml-icon-btn" type="button" @click="openSenders">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <circle cx="9" cy="8" r="4" /><path d="M2 21a7 7 0 0 1 14 0" /><path d="M19 8v6M16 11h6" />
            </svg>
            <span>שולחים</span>
            <span class="ml-count ltr-number">{{ summary.watched_senders }}</span>
          </button>
          <Transition name="fade"><span v-if="pollNote" class="ml-poll-note" role="status">{{ pollNote }}</span></Transition>
        </div>
      </div>
      <TabHeroLoop scene="mail" class="ml-hero-art" />
    </header>

    <p v-if="store.error && !store.selected && !sendersOpen" class="ml-error" role="alert">{{ store.error }}</p>

    <div v-if="!summary" class="ml-loading"><div class="spinner"></div></div>

    <!-- No mailbox -->
    <section v-else-if="!summary.mailbox_connected" class="ml-empty">
      <BigAddButton label="חיבור תיבת המייל" color="var(--tab-mail)" :size="156" @click="mailboxOpen = true">
        <AppIcon name="mail" :size="52" />
      </BigAddButton>
      <p class="ml-empty-title">חברו את תיבת המייל</p>
    </section>

    <!-- Connected, nobody watched -->
    <section v-else-if="!summary.watched_senders" class="ml-empty">
      <BigAddButton label="בחירת שולחים" color="var(--tab-mail)" :size="156" @click="openSenders">
        <svg viewBox="0 0 24 24" width="46" height="46" fill="none" stroke="currentColor" stroke-width="1.6"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <circle cx="9" cy="8" r="4" /><path d="M2 21a7 7 0 0 1 14 0" /><path d="M19 8v6M16 11h6" />
        </svg>
      </BigAddButton>
      <p class="ml-empty-title">ממי ה-AI יקרא?</p>
    </section>

    <template v-else>
      <!-- 1. The stage: what needs you (or, when nothing does, the AI at work)
           beside the live "listening" panel. -->
      <section class="ml-stage">
        <div class="ml-panel ml-pending" :class="{ 'ml-pending--zero': !queue.length }">
          <div class="ml-big">
            <!-- Clickable: with mail waiting it opens the first one; at 0 it
                 checks the inbox now. -->
            <button
              type="button" class="ml-big-n ltr-number"
              :class="{ 'ml-big-n--zero': !queue.length, 'ml-big-n--busy': store.polling }"
              :disabled="store.polling"
              :aria-label="queue.length ? 'פתיחת המייל הראשון שממתין לאישור' : 'בדיקת תיבת המייל עכשיו'"
              @click="onBigNumber"
            >{{ shown.pending }}</button>
            <span class="ml-big-l">ממתין לאישורכם</span>
            <span v-if="!queue.length" class="ml-big-calm">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.6"
                   stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 13 4 4L19 7" /></svg>
              הכל מטופל
            </span>
            <span class="ml-big-hint">{{ store.polling ? 'בודק…' : (queue.length ? 'לחצו לפתיחה' : 'לחצו לבדיקה עכשיו') }}</span>
          </div>
          <TransitionGroup v-if="queue.length" name="card" tag="div" class="ml-queue" appear>
            <button
              v-for="(it, i) in queue" :key="it.id" type="button" class="ml-card"
              :style="{ '--i': i }" @click="store.openItem(it.id)"
            >
              <span class="ml-card-top">
                <span class="ml-avatar">{{ initial(it) }}</span>
                <span class="ml-card-who">
                  <span class="ml-card-name">{{ nameOf(it) }}</span>
                  <span class="ml-card-time ltr-number">{{ shortTime(it.received_at) }}</span>
                </span>
              </span>
              <span class="ml-card-summary">{{ it.summary || it.subject }}</span>
              <span class="ml-card-cta">
                <AppIcon name="mail" :size="13" />
                {{ it.status === 'drafted' ? 'תשובה מוכנה — לבדיקה' : 'לטיפול' }}
              </span>
            </button>
          </TransitionGroup>
        </div>

        <aside class="ml-panel ml-listen">
          <MailListenRadar :senders="store.senders" :scanning="store.polling" />
          <p class="ml-listen-title">
            <span>{{ store.polling ? 'סורק…' : 'מאזין' }}</span>
            <span v-if="!store.polling" class="ml-listen-n ltr-number">{{ summary.watched_senders }}</span>
          </p>
          <div v-if="topSuggestions.length" class="ml-quick">
            <span class="ml-quick-label">להוסיף?</span>
            <button
              v-for="s in topSuggestions" :key="s.address" type="button" class="ml-quick-chip"
              :title="s.address" @click="store.addSender(s)"
            >
              <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.6"
                   stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
              {{ s.label || s.address }}
            </button>
          </div>
        </aside>
      </section>

      <!-- 2. By sender -->
      <section v-if="store.items.length" ref="listEl" class="ml-section">
        <h3 class="ml-section-title">
          {{ listFilter === 'ai' ? 'כל מה שה-AI טיפל בו' : listFilter === 'sent' ? 'תשובות שנשלחו' : 'לפי שולח' }}
          <button v-if="listFilter" type="button" class="ml-clear" @click="listFilter = null">
            הצג הכל
            <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.6"
                 stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
          </button>
        </h3>
        <p v-if="!groups.length" class="ml-calm ml-calm--muted">עוד לא נשלחו תשובות.</p>
        <ul class="ml-groups">
          <li v-for="g in groups" :key="g.key" class="ml-group" :class="{ 'ml-group--open': isOpen(g) }">
            <button type="button" class="ml-group-head" :aria-expanded="isOpen(g)" @click="toggleGroup(g.key)">
              <span class="ml-avatar ml-avatar--sm">{{ g.initial }}</span>
              <span class="ml-group-name">{{ g.name }}</span>
              <span v-if="g.pending" class="ml-dot" :title="`${g.pending} לטיפול`"></span>
              <span class="ml-group-n ltr-number">{{ g.items.length }}</span>
              <span class="ml-group-time ltr-number">{{ shortTime(g.latest) }}</span>
              <svg class="ml-chev" viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor"
                   stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6" /></svg>
            </button>
            <ul v-if="isOpen(g)" class="ml-group-rows">
              <li v-for="it in g.items" :key="it.id">
                <button type="button" class="ml-mini" @click="store.openItem(it.id)">
                  <span class="ml-status" :class="`ml-status--${it.status}`" :title="STATUS[it.status]"></span>
                  <span class="ml-mini-text">{{ it.summary || it.subject || '(ללא נושא)' }}</span>
                  <span class="ml-mini-time ltr-number">{{ shortTime(it.received_at) }}</span>
                </button>
              </li>
            </ul>
          </li>
        </ul>
      </section>
    </template>

    <!-- The open mail — a drawer, so the inbox stays in view behind it. -->
    <Teleport to="body">
      <Transition name="drawer">
        <div v-if="sel" class="ml-drawer-overlay" @click.self="store.selected = null">
          <aside class="ml-drawer" dir="rtl" role="dialog" aria-modal="true" aria-labelledby="ml-d-title"
                 @keydown.escape="store.selected = null">
            <header class="ml-d-head">
              <span class="ml-avatar">{{ initial(sel) }}</span>
              <div class="ml-d-titles">
                <h4 id="ml-d-title">{{ nameOf(sel) }}</h4>
                <span class="ml-d-sub">{{ sel.subject || '(ללא נושא)' }}</span>
              </div>
              <button class="ml-x" type="button" aria-label="סגור" @click="store.selected = null">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"
                     stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
              </button>
            </header>

            <div class="ml-d-body">
              <!-- What the AI understood — typed in, once -->
              <section class="ml-ai">
                <span class="ml-ai-badge">
                  <svg viewBox="0 0 24 24" width="13" height="13" aria-hidden="true">
                    <path fill="currentColor" d="M12 2c.6 4.6 2.4 6.4 7 7-4.6.6-6.4 2.4-7 7-.6-4.6-2.4-6.4-7-7 4.6-.6 6.4-2.4 7-7Z" />
                  </svg>
                  {{ CATEGORY[sel.category] || 'סיכום' }}
                </span>
                <p class="ml-ai-summary">
                  <Typewriter v-if="sel.summary" :key="sel.id" :text="sel.summary" :speed="14" :loop="false" cursor="" />
                  <template v-else>{{ skippedText(sel) }}</template>
                </p>
                <div v-if="entityChips.length" class="ml-entities">
                  <span v-for="(c, i) in entityChips" :key="i" class="ml-entity">
                    <span class="ml-entity-k">{{ c.k }}</span><span class="ltr-number">{{ c.v }}</span>
                  </span>
                </div>
              </section>

              <section v-if="sel.attachments?.length" class="ml-files">
                <div v-for="a in sel.attachments" :key="a.name" class="ml-file">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"
                       stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" /><path d="M14 3v5h5" />
                  </svg>
                  <span class="ml-file-name" dir="auto">{{ a.name }}</span>
                  <button
                    v-if="isImportable(a.name)" type="button" class="ml-btn ml-btn--soft"
                    :disabled="!!store.busy || !!sel.imported_upload_id" @click="onImport(a.name)"
                  >{{ sel.imported_upload_id ? 'יובא' : (store.busy === 'import' ? 'מייבא…' : 'ייבוא') }}</button>
                </div>
              </section>

              <!-- The reply -->
              <section class="ml-reply">
                <template v-if="sel.status === 'sent'">
                  <p class="ml-sent">
                    <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.4"
                         stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 13 4 4L19 7" /></svg>
                    נשלח <span class="ltr-number">{{ longTime(sel.sent_at) }}</span>
                  </p>
                  <pre class="ml-body">{{ sel.draft_body }}</pre>
                </template>

                <template v-else-if="sel.draft_body || editing">
                  <ul v-if="sel.draft_warnings?.length" class="ml-warn">
                    <li v-for="(w, i) in sel.draft_warnings" :key="i">{{ w }}</li>
                  </ul>
                  <input v-model="draftSubject" class="ml-input" type="text" aria-label="נושא" />
                  <textarea v-model="draftBody" class="ml-input ml-textarea" rows="12" aria-label="התשובה"></textarea>
                  <p v-if="hasPlaceholder" class="ml-hint">השלימו את החלקים שמסומנים [להשלים] לפני שליחה.</p>
                  <p v-if="store.error" class="ml-error" role="alert">{{ store.error }}</p>
                </template>

                <p v-else class="ml-calm ml-calm--muted">ה-AI לא זיהה שצריך לענות.</p>
              </section>

              <details class="ml-original">
                <summary>המייל המקורי</summary>
                <pre class="ml-body">{{ sel.body || '(נמחק לאחר תקופת השמירה)' }}</pre>
              </details>
            </div>

            <footer v-if="sel.status !== 'sent'" class="ml-d-foot">
              <template v-if="sel.draft_body || editing">
                <button
                  type="button" class="ml-btn ml-btn--primary"
                  :disabled="!!store.busy || !draftBody.trim() || hasPlaceholder || !summary.can_send"
                  :title="!summary.can_send ? 'שליחה נתמכת כרגע מ-Gmail בלבד' : ''"
                  @click="onSend"
                >
                  <span v-if="store.busy === 'send'" class="ml-spinner" aria-hidden="true"></span>
                  <svg v-else viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2"
                       stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                    <path d="m22 2-7 20-4-9-9-4z" /><path d="M22 2 11 13" />
                  </svg>
                  <span>{{ store.busy === 'send' ? 'שולח…' : 'אישור ושליחה' }}</span>
                </button>
                <button type="button" class="ml-btn ml-btn--ghost" :disabled="!!store.busy || !dirty" @click="onSave">
                  {{ store.busy === 'save' ? 'שומר…' : 'שמירה' }}
                </button>
                <button type="button" class="ml-btn ml-btn--ghost" :disabled="!!store.busy" @click="onRegenerate">
                  {{ store.busy === 'draft' ? 'כותב…' : 'טיוטה חדשה' }}
                </button>
              </template>
              <template v-else>
                <button type="button" class="ml-btn ml-btn--primary" :disabled="!!store.busy" @click="onRegenerate">
                  {{ store.busy === 'draft' ? 'כותב…' : 'הכנת תשובה' }}
                </button>
                <button type="button" class="ml-btn ml-btn--ghost" :disabled="!!store.busy" @click="startManual">כתיבה ידנית</button>
              </template>
              <span class="ml-gap"></span>
              <button type="button" class="ml-btn ml-btn--text" :disabled="!!store.busy" @click="onDone">טופל</button>
            </footer>
          </aside>
        </div>
      </Transition>
    </Teleport>

    <!-- Watch-list -->
    <Teleport to="body">
      <Transition name="fade">
        <div v-if="sendersOpen" class="ml-overlay" @click.self="sendersOpen = false">
          <div class="ml-modal" dir="rtl" role="dialog" aria-modal="true" aria-labelledby="ml-senders-title"
               @keydown.escape="sendersOpen = false">
            <button class="ml-x ml-x--abs" type="button" aria-label="סגור" @click="sendersOpen = false">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"
                   stroke-linecap="round" aria-hidden="true"><path d="M18 6 6 18M6 6l12 12" /></svg>
            </button>
            <h3 id="ml-senders-title">ממי ה-AI קורא</h3>
            <p class="ml-modal-sub">כתובת, או ‎@דומיין לחברה שלמה.</p>

            <form class="ml-add" @submit.prevent="onAdd">
              <input v-model="newAddress" dir="ltr" type="text" placeholder="name@company.co.il" aria-label="כתובת" />
              <input v-model="newLabel" type="text" placeholder="שם" aria-label="שם" />
              <select v-model="newKind" aria-label="סוג">
                <option value="insurer">חברה</option>
                <option value="customer">לקוח</option>
                <option value="other">אחר</option>
              </select>
              <button type="submit" class="ml-btn ml-btn--primary" :disabled="!newAddress.trim()">הוספה</button>
            </form>
            <p v-if="store.error" class="ml-error" role="alert">{{ store.error }}</p>

            <ul v-if="store.senders.length" class="ml-senders">
              <li v-for="s in store.senders" :key="s.id" class="ml-sender">
                <span class="ml-avatar ml-avatar--sm">{{ (s.label || s.address).trim()[0] }}</span>
                <span class="ml-sender-label">{{ s.label || s.address }}</span>
                <span class="ml-sender-addr ltr-number">{{ s.address }}</span>
                <button type="button" class="ml-btn ml-btn--text" @click="store.removeSender(s.id)">הסרה</button>
              </li>
            </ul>

            <template v-if="store.suggestions.length">
              <h4 class="ml-sugg-title">הצעות</h4>
              <ul class="ml-senders ml-senders--sugg">
                <li v-for="s in store.suggestions.slice(0, 40)" :key="s.address" class="ml-sender">
                  <span class="ml-avatar ml-avatar--sm ml-avatar--ghost">{{ (s.label || s.address).trim()[0] }}</span>
                  <span class="ml-sender-label">{{ s.label || s.address }}</span>
                  <span class="ml-sender-addr ltr-number">{{ s.address }}</span>
                  <button type="button" class="ml-btn ml-btn--soft" @click="store.addSender(s)">הוספה</button>
                </li>
              </ul>
            </template>
          </div>
        </div>
      </Transition>
    </Teleport>

    <HachsharaMailModal :open="mailboxOpen" @close="onMailboxClosed" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useMailAgentStore } from '../../stores/mailAgent.js'
import AppIcon from '../icons/AppIcon.vue'
import BigAddButton from './BigAddButton.vue'
import HachsharaMailModal from './HachsharaMailModal.vue'
import TabHeroLoop from './TabHeroLoop.vue'
import Typewriter from '../common/Typewriter.vue'
import MailListenRadar from './MailListenRadar.vue'

const store = useMailAgentStore()
const summary = computed(() => store.summary)
const sel = computed(() => store.selected)
const ready = computed(() => !!summary.value?.mailbox_connected && !!summary.value?.watched_senders)

const CATEGORY = {
  commission_reply: 'תשובת עמלות', report_file: 'קובץ / דוח', customer_question: 'שאלת לקוח',
  info: 'לידיעה', other: 'מייל',
}
const STATUS = {
  new: 'חדש', needs_reply: 'דורש תשובה', drafted: 'טיוטה מוכנה', sent: 'נשלח', done: 'טופל', dismissed: 'הוסתר',
}

const topSuggestions = computed(() => store.suggestions.slice(0, 3))

const sendersOpen = ref(false)
const mailboxOpen = ref(false)
const pollNote = ref('')
const openGroup = ref(null)
const newAddress = ref('')
const newLabel = ref('')
const newKind = ref('insurer')
const draftSubject = ref('')
const draftBody = ref('')
const editing = ref(false)

// ── derived views ──
const queue = computed(() =>
  store.items.filter((i) => i.status === 'drafted' || i.status === 'needs_reply'))

// What the bottom list shows: null = by sender (hidden items left out),
// 'ai' = everything the AI handled, 'sent' = replies the agent sent.
const listFilter = ref(null)
const listEl = ref(null)
const groups = computed(() => {
  const map = new Map()
  for (const it of store.items) {
    if (listFilter.value === 'sent' && it.status !== 'sent') continue
    if (!listFilter.value && it.status === 'dismissed') continue
    const key = it.from_address
    if (!map.has(key)) map.set(key, { key, name: nameOf(it), initial: initial(it), items: [], pending: 0, latest: it.received_at })
    const g = map.get(key)
    g.items.push(it)
    if (['new', 'needs_reply', 'drafted'].includes(it.status)) g.pending++
    if (it.received_at > g.latest) g.latest = it.received_at
  }
  return [...map.values()].sort((a, b) => (b.pending > 0) - (a.pending > 0) || b.latest.localeCompare(a.latest))
})

// ── counters: count up once when the numbers arrive ──
const shown = reactive({ pending: 0, processed: 0, sent: 0 })
const reduced = typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
function countTo(key, target) {
  if (reduced) { shown[key] = target; return }
  const from = shown[key]
  const t0 = performance.now()
  const step = (t) => {
    const p = Math.min(1, (t - t0) / 700)
    shown[key] = Math.round(from + (target - from) * (1 - Math.pow(1 - p, 3)))
    if (p < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}
watch(() => [queue.value.length, summary.value?.processed || 0, summary.value?.sent || 0], ([q, p, s]) => {
  countTo('pending', q); countTo('processed', p); countTo('sent', s)
}, { immediate: true })

watch(sel, (s) => {
  draftSubject.value = s?.draft_subject || (s ? `Re: ${s.subject || ''}` : '')
  draftBody.value = s?.draft_body || ''
  editing.value = false
})

const dirty = computed(() => !!sel.value && (draftSubject.value !== (sel.value.draft_subject || '') || draftBody.value !== (sel.value.draft_body || '')))
const hasPlaceholder = computed(() => draftBody.value.includes('[להשלים'))
const entityChips = computed(() => {
  const e = sel.value?.entities || {}
  const out = []
  for (const v of e.id_numbers || []) out.push({ k: 'ת.ז', v })
  for (const v of e.policy_numbers || []) out.push({ k: 'פוליסה', v })
  if (e.company) out.push({ k: 'חברה', v: e.company })
  for (const v of e.amounts_quoted || []) out.push({ k: 'סכום', v })
  return out
})

// ── helpers ──
function nameOf(it) { return it.from_name || it.from_address }
function initial(it) { return (nameOf(it) || '?').trim()[0]?.toUpperCase() || '?' }
function skippedText(it) {
  if (it.ai_skipped_reason === 'daily_cap') return 'לא נותח — מכסת ה-AI היומית'
  if (it.ai_skipped_reason === 'ai_unavailable') return 'לא נותח — ה-AI לא היה זמין'
  return ''
}
function isImportable(name) { return /\.(xlsx|xls|zip|csv)$/i.test(name || '') }
function asDate(iso) { return new Date(iso && !/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso + 'Z' : iso) }
function shortTime(iso) {
  if (!iso) return ''
  const d = asDate(iso)
  return new Date().toDateString() === d.toDateString()
    ? d.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' })
    : d.toLocaleDateString('he-IL', { day: 'numeric', month: 'numeric' })
}
function longTime(iso) { return iso ? asDate(iso).toLocaleString('he-IL', { dateStyle: 'short', timeStyle: 'short' }) : '' }

// ── actions ──
function isOpen(g) { return !!listFilter.value || openGroup.value === g.key }
function toggleGroup(key) {
  if (listFilter.value) return
  openGroup.value = openGroup.value === key ? null : key
}
async function showList(kind) {
  listFilter.value = listFilter.value === kind ? null : kind
  await nextTick()
  listEl.value?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' })
}
async function onPoll() {
  pollNote.value = ''
  const n = await store.pollNow()
  if (n !== null) pollNote.value = n ? `${n} חדשים` : 'אין חדש'
  setTimeout(() => { pollNote.value = '' }, 3500)
}
function onBigNumber() {
  if (queue.value.length) store.openItem(queue.value[0].id)
  else onPoll()
}
async function openSenders() {
  store.error = ''
  sendersOpen.value = true
  await Promise.all([store.fetchSenders(), store.fetchSuggestions()])
}
async function onAdd() {
  const ok = await store.addSender({ address: newAddress.value.trim(), label: newLabel.value.trim() || null, kind: newKind.value })
  if (ok) { newAddress.value = ''; newLabel.value = '' }
}
async function onMailboxClosed() { mailboxOpen.value = false; await store.fetchSummary() }
function startManual() { editing.value = true; draftSubject.value = `Re: ${sel.value?.subject || ''}`; draftBody.value = '' }
const onSave = () => store.saveDraft(sel.value.id, draftSubject.value, draftBody.value)
const onRegenerate = () => store.regenerate(sel.value.id)
const onImport = (name) => store.importFile(sel.value.id, name)
async function onSend() {
  if (await store.send(sel.value.id, draftSubject.value, draftBody.value)) await store.fetchItems()
}
async function onDone() {
  await store.dismiss(sel.value.id, true)
  await store.fetchItems()
}

// Escape closes the innermost layer first (drawer → senders list), whatever
// has focus. Capture phase + preventDefault so the Mail Agent modal (which
// listens after us) knows the key was already used.
function onKey(e) {
  if (e.key !== 'Escape') return
  if (store.selected) { store.selected = null; e.preventDefault() }
  else if (sendersOpen.value) { sendersOpen.value = false; e.preventDefault() }
}
onMounted(() => window.addEventListener('keydown', onKey, true))
onUnmounted(() => window.removeEventListener('keydown', onKey, true))

onMounted(async () => {
  store.selected = null
  store.filter = 'all'
  await store.refreshAll()
  if (summary.value?.mailbox_connected) await Promise.all([store.fetchSenders(), store.fetchSuggestions()])
})
</script>

<style scoped>
/* The drawer and the senders modal are teleported to <body>, outside .ml —
   they need the tab's tokens declared on their own roots too. */
.ml, .ml-drawer-overlay, .ml-overlay {
  --ml-ink: var(--tab-mail-ink);
  --ml-acc: var(--tab-mail);
  --ml-wash: var(--tab-mail-wash);
}
.ml { display: flex; flex-direction: column; gap: 18px; }

/* ── Hero ───────────────────────────────────────────────────── */
.ml-hero {
  position: relative; overflow: hidden; display: flex; align-items: center; min-height: 190px;
  padding: 22px 24px; background: var(--card-bg);
  border: 1px solid var(--border-subtle); border-radius: var(--radius-md); box-shadow: var(--shadow-sm);
}
.ml-hero::before {
  content: ''; position: absolute; inset-inline-end: -6%; top: -60%; width: 44%; height: 220%;
  background: radial-gradient(circle, var(--ml-wash), transparent 70%); pointer-events: none;
}
/* scanning sweep while the AI checks the inbox */
.ml-hero--scan::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(100deg, transparent 30%, color-mix(in srgb, var(--ml-acc) 18%, transparent) 50%, transparent 70%);
  background-size: 250% 100%; animation: ml-sweep 1.3s linear infinite;
}
@keyframes ml-sweep { from { background-position: 150% 0; } to { background-position: -100% 0; } }
.ml-hero-copy { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 6px; max-width: 60%; min-width: 0; }
.ml-kicker {
  align-self: flex-start; padding: 4px 11px; border-radius: 999px; font-size: 11.5px; font-weight: 800;
  background: var(--ml-wash); color: var(--ml-ink);
}
/* Wordmark: Rubik (already loaded app-wide; the landing's display face). */
.ml-hero-title {
  align-self: flex-start; margin: 4px 0 0;
  font-family: 'Rubik', 'Heebo', sans-serif; font-size: clamp(28px, 3.3vw, 40px); font-weight: 700;
  letter-spacing: -0.035em; line-height: 1.05; color: var(--text);
}
.ml-hero-title-acc { color: var(--ml-ink); }
.ml-hero-art {
  position: absolute; inset-inline-end: 4px; top: 50%; transform: translateY(-50%);
  width: min(270px, 36%); aspect-ratio: 420 / 300; pointer-events: none; z-index: 0;
}

.ml-stats { display: flex; gap: 22px; margin-top: 10px; }
.ml-stat {
  display: flex; flex-direction: column; gap: 0; align-items: flex-start; padding: 4px 8px; margin: -4px -8px;
  font-family: inherit; text-align: start; background: none; border: none; border-radius: var(--radius-sm); cursor: pointer;
}
.ml-stat:hover { background: var(--ml-wash); }
.ml-stat:hover .ml-stat-l, .ml-stat--on .ml-stat-l { color: var(--ml-ink); text-decoration: underline; text-underline-offset: 3px; }
.ml-stat--on { background: var(--ml-wash); }
.ml-stat:focus-visible { outline: 2px solid var(--ml-acc); outline-offset: 2px; }
.ml-clear {
  display: inline-flex; align-items: center; gap: 5px; height: 26px; padding: 0 10px; border-radius: 999px;
  font-family: inherit; font-size: 12px; font-weight: 700; color: var(--ml-ink); background: var(--ml-wash);
  border: none; cursor: pointer;
}
.ml-clear:hover { filter: brightness(0.96); }
.ml-stat-n { font-size: 26px; font-weight: 800; line-height: 1.1; color: var(--text); font-variant-numeric: tabular-nums; }
.ml-stat--hot .ml-stat-n { color: var(--ml-ink); }
.ml-stat-l { font-size: 11.5px; font-weight: 600; color: var(--text-muted); }

.ml-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
.ml-chip {
  display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border-radius: 999px;
  background: var(--ml-wash); color: var(--ml-ink); font-size: 12px; font-weight: 700;
}
.ml-icon-btn {
  display: inline-flex; align-items: center; gap: 6px; height: 30px; padding: 0 11px;
  font-family: inherit; font-size: 12px; font-weight: 700; color: var(--text-secondary);
  background: var(--card-bg); border: 1px solid var(--border); border-radius: 999px; cursor: pointer;
}
.ml-icon-btn:hover:not(:disabled) { border-color: var(--ml-acc); color: var(--ml-ink); }
.ml-icon-btn:disabled { opacity: 0.6; cursor: default; }
.ml-icon-btn:focus-visible { outline: 2px solid var(--ml-acc); outline-offset: 2px; }
.ml-rot { animation: ml-spin 0.9s linear infinite; }
.ml-poll-note { font-size: 12px; font-weight: 700; color: var(--ml-ink); }

/* ── Shared bits ────────────────────────────────────────────── */
.ml-count {
  min-width: 20px; padding: 1px 7px; border-radius: 999px; font-size: 11px; font-weight: 800; text-align: center;
  background: var(--ml-wash); color: var(--ml-ink);
}
.ml-count--hot { background: var(--ml-ink); color: #fff; }
.ml-avatar {
  flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center;
  width: 34px; height: 34px; border-radius: 50%; font-size: 14px; font-weight: 800;
  background: var(--ml-wash); color: var(--ml-ink);
}
.ml-avatar--sm { width: 28px; height: 28px; font-size: 12px; }
.ml-avatar--ghost { background: var(--bg); color: var(--text-muted); }
.ml-error { margin: 0; font-size: 13px; font-weight: 600; color: var(--red-deep); }
.ml-hint { margin: 0; font-size: 12.5px; color: color-mix(in srgb, var(--amber) 62%, #000); }
.ml-loading { display: flex; justify-content: center; padding: 24px; }
.ml-calm { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 14px; font-weight: 700; color: color-mix(in srgb, var(--green) 82%, #000); }
.ml-calm--muted { color: var(--text-muted); font-weight: 500; }

.ml-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 7px;
  height: 38px; padding: 0 16px; font-family: inherit; font-size: 13px; font-weight: 700;
  border-radius: var(--radius-sm); cursor: pointer; border: 1px solid transparent; white-space: nowrap;
}
.ml-btn:disabled { opacity: 0.45; cursor: not-allowed; }
.ml-btn:focus-visible { outline: 2px solid var(--ml-acc); outline-offset: 2px; }
.ml-btn--primary { background: var(--ml-ink); color: #fff; }
.ml-btn--primary:hover:not(:disabled) { filter: brightness(1.12); }
.ml-btn--ghost { background: var(--card-bg); color: var(--text-secondary); border-color: var(--border); }
.ml-btn--ghost:hover:not(:disabled) { border-color: var(--ml-acc); color: var(--ml-ink); }
.ml-btn--soft { height: 30px; padding: 0 12px; font-size: 12px; background: var(--ml-wash); color: var(--ml-ink); }
.ml-btn--text { background: none; color: var(--text-muted); padding: 0 8px; }
.ml-btn--text:hover:not(:disabled) { color: var(--text); }
.ml-spinner {
  width: 13px; height: 13px; border-radius: 50%;
  border: 2px solid rgba(255,255,255,.35); border-top-color: #fff; animation: ml-spin 0.8s linear infinite;
}
@keyframes ml-spin { to { transform: rotate(360deg); } }

/* ── Empty ──────────────────────────────────────────────────── */
.ml-empty {
  display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 40px 16px 34px;
  background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  color: var(--ml-acc);
}
.ml-empty-title { margin: 12px 0 0; font-size: 16px; font-weight: 800; color: var(--text); }

/* ── Sections ───────────────────────────────────────────────── */
.ml-section { display: flex; flex-direction: column; gap: 12px; }
.ml-section-title { display: flex; align-items: center; gap: 8px; margin: 0; font-size: 15px; font-weight: 800; color: var(--text); }

/* stage */
.ml-stage { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(260px, 1fr); gap: 14px; align-items: stretch; }
.ml-panel {
  display: flex; flex-direction: column; gap: 12px; padding: 18px 20px;
  background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); box-shadow: var(--shadow-sm);
}
.ml-listen { align-items: center; text-align: center; justify-content: center; gap: 6px;
  background: radial-gradient(90% 70% at 50% 35%, var(--ml-wash), transparent 70%), var(--card-bg); }
.ml-listen-title { margin: 4px 0 0; font-size: 16px; font-weight: 800; color: var(--text); }
.ml-quick { display: flex; flex-wrap: wrap; justify-content: center; align-items: center; gap: 6px; margin-top: 10px; }
.ml-quick-label { font-size: 12px; font-weight: 700; color: var(--text-muted); }
.ml-quick-chip {
  display: inline-flex; align-items: center; gap: 5px; height: 28px; padding: 0 11px; border-radius: 999px;
  font-family: inherit; font-size: 12px; font-weight: 700; cursor: pointer;
  color: var(--ml-ink); background: var(--card-bg); border: 1px dashed color-mix(in srgb, var(--ml-acc) 55%, transparent);
}
.ml-quick-chip:hover { background: var(--ml-wash); border-style: solid; }
.ml-quick-chip:focus-visible { outline: 2px solid var(--ml-acc); outline-offset: 2px; }

/* the big number */
.ml-pending { justify-content: flex-start; }
.ml-pending--zero { justify-content: center; align-items: center; }
.ml-pending--zero .ml-big { flex-direction: column; align-items: center; gap: 8px; }
.ml-pending--zero .ml-big-n { font-size: clamp(120px, 13vw, 180px); line-height: 0.85; }
.ml-pending--zero .ml-big-l { font-size: 24px; }
.ml-listen-title { display: inline-flex; align-items: center; gap: 8px; }
.ml-listen-n {
  min-width: 30px; padding: 2px 10px; border-radius: 999px; font-size: 15px; font-weight: 800;
  background: var(--ml-ink); color: #fff;
}
.ml-big { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
.ml-big-n {
  font-size: clamp(64px, 7vw, 92px); font-weight: 800; line-height: 0.95; letter-spacing: -0.04em;
  color: var(--ml-ink); font-variant-numeric: tabular-nums;
}
.ml-big-n--zero { color: color-mix(in srgb, var(--ml-acc) 45%, var(--border)); }
button.ml-big-n {
  padding: 0 6px; font-family: inherit; background: none; border: none; border-radius: var(--radius-md);
  cursor: pointer; transition: transform 0.18s var(--transition), color 0.18s var(--transition);
}
button.ml-big-n:hover:not(:disabled) { transform: scale(1.05); color: var(--ml-ink); }
button.ml-big-n:focus-visible { outline: 3px solid var(--ml-acc); outline-offset: 4px; }
button.ml-big-n:disabled { cursor: progress; }
.ml-big-n--busy { animation: ml-big-pulse 1s ease-in-out infinite; }
@keyframes ml-big-pulse { 50% { opacity: 0.45; } }
.ml-big-hint { font-size: 12px; font-weight: 600; color: var(--text-muted); }
@media (prefers-reduced-motion: reduce) { .ml-big-n--busy { animation: none; } button.ml-big-n:hover:not(:disabled) { transform: none; } }
.ml-big-l { font-size: 20px; font-weight: 800; color: var(--text); }
.ml-big-calm { display: inline-flex; align-items: center; gap: 5px; font-size: 13px; font-weight: 700; color: color-mix(in srgb, var(--green) 82%, #000); }

/* approval queue */
.ml-queue { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 12px; }
.ml-card {
  position: relative; overflow: hidden; display: flex; flex-direction: column; gap: 10px;
  padding: 14px 16px; text-align: start; font-family: inherit; cursor: pointer;
  background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
  box-shadow: var(--shadow-sm); border-top: 3px solid var(--ml-acc);
  transition: transform 0.18s var(--transition), box-shadow 0.18s var(--transition);
}
.ml-card:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
.ml-card:focus-visible { outline: 2px solid var(--ml-acc); outline-offset: 2px; }
/* one shimmer pass when a card arrives — "the AI just did this" */
.ml-card::after {
  content: ''; position: absolute; inset: 0; pointer-events: none;
  background: linear-gradient(105deg, transparent 35%, color-mix(in srgb, var(--ml-acc) 22%, transparent) 50%, transparent 65%);
  background-size: 260% 100%; background-position: 160% 0;
  animation: ml-shine 1.1s ease-out calc(var(--i, 0) * 90ms + 250ms) 1 both;
}
@keyframes ml-shine {
  from { background-position: 160% 0; opacity: 1; }
  80% { opacity: 1; }
  to { background-position: -60% 0; opacity: 0; }
}
.ml-card-top { display: flex; align-items: center; gap: 10px; }
.ml-card-who { display: flex; flex-direction: column; min-width: 0; }
.ml-card-name { font-size: 14px; font-weight: 800; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ml-card-time { font-size: 11.5px; color: var(--text-muted); }
.ml-card-summary {
  font-size: 13px; line-height: 1.55; color: var(--text-secondary);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.ml-card-cta { display: inline-flex; align-items: center; gap: 6px; font-size: 12px; font-weight: 800; color: var(--ml-ink); }

.card-enter-active { transition: opacity 0.4s ease, transform 0.4s cubic-bezier(0.2, 0.8, 0.2, 1); transition-delay: calc(var(--i, 0) * 70ms); }
.card-enter-from { opacity: 0; transform: translateY(12px); }
.card-leave-active { transition: opacity 0.2s ease; }
.card-leave-to { opacity: 0; }

/* by sender */
.ml-groups { list-style: none; margin: 0; padding: 0; background: var(--card-bg); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); box-shadow: var(--shadow-sm); overflow: hidden; }
.ml-group + .ml-group { border-top: 1px solid var(--border-subtle); }
.ml-group-head {
  width: 100%; display: flex; align-items: center; gap: 10px; padding: 11px 16px;
  font-family: inherit; background: none; border: none; cursor: pointer; text-align: start;
}
.ml-group-head:hover { background: var(--bg); }
.ml-group-head:focus-visible { outline: 2px solid var(--ml-acc); outline-offset: -2px; }
.ml-group-name { flex: 1; min-width: 0; font-size: 14px; font-weight: 700; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ml-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--ml-acc); box-shadow: 0 0 0 3px var(--ml-wash); }
.ml-group-n { font-size: 12px; font-weight: 700; color: var(--text-muted); }
.ml-group-time { font-size: 12px; color: var(--text-muted); min-width: 44px; text-align: end; }
.ml-chev { color: var(--text-muted); transition: transform 0.2s ease; }
.ml-group--open .ml-chev { transform: rotate(180deg); }
.ml-group-rows { list-style: none; margin: 0; padding: 0 0 8px; }
.ml-mini {
  width: 100%; display: flex; align-items: center; gap: 10px; padding: 8px 16px 8px 16px; padding-inline-start: 54px;
  font-family: inherit; background: none; border: none; cursor: pointer; text-align: start;
}
.ml-mini:hover { background: var(--bg); }
.ml-mini-text { flex: 1; min-width: 0; font-size: 13px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ml-mini-time { font-size: 11.5px; color: var(--text-muted); }
.ml-status { width: 8px; height: 8px; border-radius: 50%; background: var(--border); flex-shrink: 0; }
.ml-status--needs_reply, .ml-status--drafted, .ml-status--new { background: var(--ml-acc); }
.ml-status--sent, .ml-status--done { background: var(--green); }

/* ── Drawer ─────────────────────────────────────────────────── */
.ml-drawer-overlay { position: fixed; inset: 0; z-index: 1010; background: rgba(0, 0, 0, 0.32); }
.ml-drawer {
  position: absolute; top: 0; bottom: 0; inset-inline-end: 0; width: min(560px, 100%);
  display: flex; flex-direction: column; background: var(--card-bg); box-shadow: var(--shadow-lg);
  border-inline-start: 3px solid var(--ml-acc);
}
.ml-d-head { display: flex; align-items: center; gap: 12px; padding: 18px 20px; border-bottom: 1px solid var(--border-subtle); }
.ml-d-titles { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.ml-d-titles h4 { margin: 0; font-size: 16px; font-weight: 800; color: var(--text); }
.ml-d-sub { font-size: 12.5px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ml-x {
  display: inline-flex; padding: 6px; background: none; border: none; border-radius: var(--radius-sm);
  color: var(--text-muted); cursor: pointer;
}
.ml-x:hover { background: var(--bg); color: var(--text); }
.ml-x--abs { position: absolute; top: 16px; inset-inline-end: 16px; }
.ml-d-body { flex: 1; overflow-y: auto; padding: 18px 20px; display: flex; flex-direction: column; gap: 14px; }
.ml-d-foot { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; padding: 14px 20px; border-top: 1px solid var(--border-subtle); }
.ml-gap { flex: 1; }

.ml-ai { display: flex; flex-direction: column; gap: 8px; padding: 14px 16px; background: var(--ml-wash); border-radius: var(--radius-md); }
.ml-ai-badge { align-self: flex-start; display: inline-flex; align-items: center; gap: 5px; font-size: 12px; font-weight: 800; color: var(--ml-ink); }
.ml-ai-summary { margin: 0; min-height: 1.6em; font-size: 15px; line-height: 1.65; color: var(--text); }
.ml-entities { display: flex; gap: 6px; flex-wrap: wrap; }
.ml-entity { display: inline-flex; gap: 5px; padding: 2px 9px; border-radius: 999px; font-size: 12px; background: var(--card-bg); color: var(--text-secondary); }
.ml-entity-k { color: var(--text-muted); }

.ml-files { display: flex; flex-direction: column; gap: 6px; }
.ml-file { display: flex; align-items: center; gap: 8px; padding: 8px 12px; border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); color: var(--text-muted); }
.ml-file-name { flex: 1; min-width: 0; font-size: 13px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.ml-reply { display: flex; flex-direction: column; gap: 10px; }
.ml-sent { display: flex; align-items: center; gap: 6px; margin: 0; font-size: 13px; font-weight: 700; color: color-mix(in srgb, var(--green) 82%, #000); }
.ml-warn {
  margin: 0; padding: 10px 14px; padding-inline-start: 28px; font-size: 12.5px; line-height: 1.55;
  color: color-mix(in srgb, var(--amber) 62%, #000); background: var(--amber-light); border-radius: var(--radius-sm);
}
.ml-input {
  font-family: inherit; font-size: 14px; line-height: 1.6; color: var(--text); padding: 9px 12px;
  border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--card-bg);
}
.ml-input:focus { outline: none; border-color: var(--ml-acc); box-shadow: 0 0 0 3px var(--ml-wash); }
.ml-textarea { resize: vertical; min-height: 220px; }
.ml-original summary { cursor: pointer; font-size: 12.5px; font-weight: 700; color: var(--text-muted); }
.ml-body {
  margin: 8px 0 0; padding: 12px 14px; max-height: 280px; overflow-y: auto; white-space: pre-wrap; word-break: break-word;
  font-family: inherit; font-size: 13px; line-height: 1.65; color: var(--text-secondary); background: var(--bg); border-radius: var(--radius-sm);
}

.drawer-enter-active, .drawer-leave-active { transition: background-color 0.25s ease; }
.drawer-enter-active .ml-drawer, .drawer-leave-active .ml-drawer { transition: transform 0.3s cubic-bezier(0.2, 0.8, 0.2, 1); }
.drawer-enter-from, .drawer-leave-to { background-color: transparent; }
.drawer-enter-from .ml-drawer, .drawer-leave-to .ml-drawer { transform: translateX(-100%); }

/* ── Watch-list modal ───────────────────────────────────────── */
.ml-overlay { position: fixed; inset: 0; z-index: 1000; display: flex; align-items: center; justify-content: center; padding: 16px; background: rgba(0, 0, 0, 0.45); }
.ml-modal {
  position: relative; width: min(640px, 100%); max-height: calc(100vh - 32px); overflow-y: auto;
  padding: 24px 26px; background: var(--card-bg); border-radius: var(--radius-lg);
  border-top: 4px solid var(--ml-acc); box-shadow: var(--shadow-lg); display: flex; flex-direction: column; gap: 12px;
}
.ml-modal h3 { margin: 0; font-size: 18px; font-weight: 800; color: var(--text); padding-inline-end: 36px; }
.ml-modal-sub { margin: 0; font-size: 13px; color: var(--text-muted); }
.ml-add { display: grid; grid-template-columns: 1.5fr 1fr auto auto; gap: 8px; }
.ml-add input, .ml-add select {
  height: 38px; padding: 0 10px; font-family: inherit; font-size: 13px; color: var(--text);
  border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--card-bg);
}
.ml-add input:focus, .ml-add select:focus { outline: none; border-color: var(--ml-acc); box-shadow: 0 0 0 3px var(--ml-wash); }
.ml-senders { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }
.ml-senders--sugg { max-height: 260px; overflow-y: auto; }
.ml-sender { display: grid; grid-template-columns: auto minmax(0, 1fr) minmax(0, 1fr) auto; gap: 10px; align-items: center; padding: 6px 10px; border-radius: var(--radius-sm); background: var(--bg); }
.ml-sender-label { font-size: 13.5px; font-weight: 700; color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ml-sender-addr { font-size: 12px; color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ml-sugg-title { margin: 6px 0 0; font-size: 13px; font-weight: 800; color: var(--text-muted); }

.fade-enter-active, .fade-leave-active { transition: opacity 0.2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }

@media (max-width: 980px) {
  .ml-stage { grid-template-columns: 1fr; }
}
@media (max-width: 760px) {
  .ml-hero-art { display: none; }
  .ml-hero-copy { max-width: none; }
  .ml-add { grid-template-columns: 1fr 1fr; }
  .ml-sender { grid-template-columns: auto minmax(0, 1fr) auto; }
  .ml-sender-addr { display: none; }
}
@media (prefers-reduced-motion: reduce) {
  .ml-hero--scan::after, .ml-card::after, .ml-rot, .ml-spinner { animation: none; }
  .ml-card, .card-enter-active, .drawer-enter-active .ml-drawer, .drawer-leave-active .ml-drawer { transition: none; }
}
</style>
