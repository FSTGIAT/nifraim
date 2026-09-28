<template>
  <!-- סוכן המשרד — the agent's back-office AI. It speaks first: a greeting, how
       many things wait, then one card per thing (a mail that arrived, an insurer
       that didn't pay) with the ONE action that moves it. A short ask box for
       quick questions. Opens out of its icon (useOriginMorph). -->
  <Teleport to="body">
    <Transition name="oa-fade">
      <div v-if="open" class="oa-overlay" @click.self="close">
        <section ref="cardEl" class="oa" role="dialog" aria-modal="true" aria-label="סוכן המשרד">
          <header class="oa-head">
            <span class="oa-avatar" aria-hidden="true"><OfficeAgentGlyph /></span>
            <div class="oa-titles">
              <strong class="oa-name">סוכן המשרד</strong>
              <span class="oa-sub">עובד בשבילך על המיילים והעמלות</span>
            </div>
            <button class="oa-x" type="button" aria-label="סגור" @click="close">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
            </button>
          </header>

          <div ref="feedEl" class="oa-feed">
            <div v-if="!b" class="oa-msg oa-msg--agent"><p class="oa-typing"><i></i><i></i><i></i></p></div>
            <template v-else>
              <!-- the agent speaks first -->
              <div class="oa-msg oa-msg--agent">
                <p class="oa-hello">{{ b.greeting }}</p>
                <p class="oa-headline">{{ b.headline }}</p>
              </div>

              <article v-for="c in b.cards" :key="c.id" class="oa-card" :class="['oa-card--' + c.kind, 'oa-card--' + c.sub]">
                <header class="oa-card-head">
                  <span class="oa-card-ic" aria-hidden="true">
                    <svg v-if="c.kind === 'unpaid'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M15 8.5h-4a2 2 0 0 0 0 4h2a2 2 0 0 1 0 4H9M12 6.5v2M12 16.5v2"/></svg>
                    <svg v-else-if="c.sub === 'customer_question'" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"/></svg>
                    <svg v-else viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="m3 7 9 6 9-6"/></svg>
                  </span>
                  <div class="oa-card-titles">
                    <strong>{{ c.title }}</strong>
                    <span class="oa-card-meta">{{ c.meta }}</span>
                  </div>
                </header>
                <p class="oa-card-text">{{ c.text }}</p>

                <!-- insurer contact missing -->
                <div v-if="c.actions.includes('set_email')" class="oa-inline">
                  <input v-model.trim="emails[c.id]" type="email" dir="ltr" placeholder="name@insurer.co.il" @keydown.enter="setEmail(c)" />
                  <button type="button" class="oa-btn oa-btn--go" :disabled="!emails[c.id] || isBusy(c, 'set_email')" @click="setEmail(c)">שמירה</button>
                </div>

                <!-- the draft behind the action -->
                <details v-if="c.draft_body && (c.actions.includes('send_reply') || c.actions.includes('send_case'))" class="oa-draft">
                  <summary>{{ c.kind === 'unpaid' ? `הפנייה לחברה · ${c.policies} פוליסות` : 'הטיוטה שהכנתי' }}</summary>
                  <textarea v-model="bodies[c.id]" rows="7" @blur="saveCaseBody(c)"></textarea>
                </details>

                <div v-if="primary(c) || c.actions.includes('done')" class="oa-actions">
                  <button v-if="primary(c)" type="button" class="oa-btn oa-btn--go" :disabled="primary(c).disabled || isBusy(c, primary(c).action)"
                          @click="run(c, primary(c).action)">
                    {{ isBusy(c, primary(c).action) ? '…' : primary(c).label }}
                  </button>
                  <button v-if="c.actions.includes('done')" type="button" class="oa-btn" :disabled="isBusy(c, 'done')" @click="run(c, 'done')">טופל</button>
                </div>
              </article>

              <p v-if="store.error" class="oa-err">{{ store.error }}</p>

              <!-- the short Q&A -->
              <div v-for="(m, i) in store.thread" :key="i" class="oa-msg" :class="'oa-msg--' + m.role">
                <p>{{ m.text }}</p>
              </div>
              <div v-if="store.busy === 'ask'" class="oa-msg oa-msg--agent"><p class="oa-typing"><i></i><i></i><i></i></p></div>
            </template>
          </div>

          <form class="oa-ask" @submit.prevent="askNow">
            <input v-model="q" class="oa-ask-input" placeholder="שאלו את סוכן המשרד…" maxlength="500" />
            <button class="oa-ask-send" type="submit" :disabled="!q.trim() || store.busy === 'ask'" aria-label="שלח">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="14 9 9 4 4 9"/><path d="M20 20h-7a4 4 0 0 1-4-4V4"/></svg>
            </button>
          </form>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useOfficeAgentStore } from '../../stores/officeAgent.js'
import { useOriginMorph } from '../../composables/useOriginMorph.js'
import OfficeAgentGlyph from './OfficeAgentGlyph.vue'

const props = defineProps({ open: { type: Boolean, default: false }, originEl: { type: Object, default: null } })
const emit = defineEmits(['update:open'])
const store = useOfficeAgentStore()
const b = computed(() => store.brief)

const emails = reactive({})
const bodies = reactive({})
watch(() => store.cards, (cs) => {
  for (const c of cs) {
    if (!(c.id in bodies)) bodies[c.id] = c.draft_body || ''
    if (!(c.id in emails)) emails[c.id] = c.to_email || ''
  }
}, { immediate: true })

// the ONE action that moves each card
function primary(c) {
  const canSend = !!b.value?.mailbox?.can_send
  if (c.actions.includes('send_reply')) return { action: 'send_reply', label: 'שליחת התשובה', disabled: !canSend }
  if (c.actions.includes('make_draft')) return { action: 'make_draft', label: 'הכנת טיוטה' }
  if (c.actions.includes('import')) return { action: 'import', label: 'טעינת הקובץ' }
  if (c.actions.includes('send_case')) return { action: 'send_case', label: 'אישור ושליחה', disabled: !canSend }
  if (c.actions.includes('remind')) return { action: 'remind', label: 'שליחת תזכורת', disabled: !canSend }
  if (c.actions.includes('resolve')) return { action: 'resolve', label: 'סימון כטופל' }
  return null
}
const isBusy = (c, a) => store.busy === c.id + ':' + a
function run(c, action) {
  if (action === 'send_reply') return store.act(c, action, { body: bodies[c.id] })
  return store.act(c, action)
}
function setEmail(c) { if (emails[c.id]) store.act(c, 'set_email', { email: emails[c.id] }) }
function saveCaseBody(c) {
  if (c.kind === 'unpaid' && bodies[c.id] !== c.draft_body) store.act(c, 'save_case_body', { body: bodies[c.id] })
}

const q = ref('')
const feedEl = ref(null)
async function askNow() {
  const text = q.value
  q.value = ''
  await store.ask(text)
  await nextTick()
  feedEl.value?.scrollTo({ top: feedEl.value.scrollHeight, behavior: 'smooth' })
}

// iPhone-style open/close out of the icon
const morph = useOriginMorph()
const cardEl = ref(null)
watch(() => props.open, async (v) => {
  if (!v) return
  store.load()
  morph.remember(props.originEl)
  await nextTick()
  morph.grow(cardEl.value)
})
async function close() {
  if (morph.hasOrigin()) await morph.shrink(cardEl.value)
  emit('update:open', false)
}
</script>

<style scoped>
.oa-overlay { position: fixed; inset: 0; z-index: 1010; background: rgba(24, 24, 24, 0.32); display: grid; place-items: center; padding: 16px; }
.oa {
  width: min(760px, 100%); height: min(780px, calc(100vh - 32px));
  display: flex; flex-direction: column; overflow: hidden;
  background: #fff; border-radius: 24px; border: 1px solid var(--border-subtle);
  box-shadow: 0 30px 80px rgba(24, 24, 24, 0.22); font-family: 'Heebo', sans-serif;
}
.oa-head { display: flex; align-items: center; gap: 12px; padding: 16px 20px; border-bottom: 1px solid var(--border-subtle); }
.oa-avatar { width: 46px; height: 46px; color: var(--tab-comparison, #2E844A); flex-shrink: 0; }
.oa-titles { flex: 1; display: flex; flex-direction: column; }
.oa-name { font-size: 18px; font-weight: 900; letter-spacing: -0.02em; color: var(--text-primary, #181818); }
.oa-sub { font-size: 12.5px; color: var(--text-secondary, #706E6B); }
.oa-x { width: 32px; height: 32px; border-radius: 10px; border: none; background: transparent; cursor: pointer; display: grid; place-items: center; color: var(--text-secondary, #706E6B); }
.oa-x:hover { background: var(--bg, #F3F3F3); color: var(--text-primary, #181818); }

.oa-feed { flex: 1; overflow-y: auto; padding: 18px 20px; display: flex; flex-direction: column; gap: 12px; background: #FBFBFA; }
.oa-msg { max-width: 88%; }
.oa-msg p { margin: 0; }
.oa-msg--agent { align-self: flex-start; padding: 12px 16px; border-radius: 18px; border-start-start-radius: 6px; background: #fff; border: 1px solid var(--border-subtle); }
.oa-msg--user { align-self: flex-start; padding: 10px 14px; border-radius: 18px; border-start-start-radius: 6px; background: #EAF4EC; font-size: 14.5px; }
.oa-hello { font-size: 17px; font-weight: 900; color: var(--text-primary, #181818); }
.oa-headline { font-size: 15px; color: var(--text-secondary, #3E3E3C); margin-top: 2px !important; }

.oa-card {
  display: flex; flex-direction: column; gap: 10px; padding: 14px 16px;
  background: #fff; border-radius: 16px; border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm);
  border-inline-start: 4px solid #D9D7D3;
}
.oa-card--unpaid { border-inline-start-color: #E04B48; }
.oa-card--customer_question { border-inline-start-color: var(--tab-portal-ink, #35719A); }
.oa-card--commission_reply, .oa-card--read { border-inline-start-color: var(--tab-comparison, #2E844A); }
.oa-card-head { display: flex; align-items: center; gap: 10px; }
.oa-card-ic { width: 32px; height: 32px; border-radius: 10px; display: grid; place-items: center; background: #F3F2EF; color: #3E3E3C; flex-shrink: 0; }
.oa-card--unpaid .oa-card-ic { background: #FDECEC; color: #C23934; }
.oa-card--customer_question .oa-card-ic { background: #EAF4FA; color: #35719A; }
.oa-card--commission_reply .oa-card-ic { background: #EAF4EC; color: #2E844A; }
.oa-card-titles { display: flex; flex-direction: column; min-width: 0; }
.oa-card-titles strong { font-size: 15px; font-weight: 800; color: var(--text-primary, #181818); }
.oa-card-meta { font-size: 12px; color: var(--text-secondary, #706E6B); }
.oa-card-text { margin: 0; font-size: 15px; line-height: 1.6; color: var(--text-primary, #181818); }
.oa-inline { display: flex; gap: 8px; }
.oa-inline input { flex: 1; height: 38px; padding: 0 12px; border-radius: 10px; border: 1px solid var(--border-subtle); font-family: inherit; font-size: 14px; outline: none; }
.oa-inline input:focus { border-color: var(--tab-comparison, #2E844A); }
.oa-draft summary { cursor: pointer; font-size: 13px; font-weight: 800; color: var(--text-secondary, #3E3E3C); }
.oa-draft textarea { width: 100%; margin-top: 8px; padding: 10px 12px; border-radius: 12px; border: 1px solid var(--border-subtle); font-family: inherit; font-size: 13.5px; line-height: 1.6; resize: vertical; background: #FCFCFB; outline: none; }
.oa-actions { display: flex; gap: 8px; flex-wrap: wrap; }
.oa-btn { height: 38px; padding: 0 16px; border-radius: 12px; border: 1px solid var(--border-subtle); background: #fff; cursor: pointer; font-family: inherit; font-size: 14px; font-weight: 800; color: var(--text-primary, #181818); }
.oa-btn--go { background: #181818; color: #fff; border-color: transparent; }
.oa-btn--go:hover:not(:disabled) { background: #000; }
.oa-btn:disabled { opacity: 0.4; cursor: default; }
.oa-err { margin: 0; font-size: 13px; font-weight: 700; color: #C23934; }

.oa-typing { display: inline-flex; gap: 4px; }
.oa-typing i { width: 7px; height: 7px; border-radius: 50%; background: #A9A6A2; animation: oaDot 1s ease-in-out infinite; }
.oa-typing i:nth-child(2) { animation-delay: 0.15s; } .oa-typing i:nth-child(3) { animation-delay: 0.3s; }
@keyframes oaDot { 50% { opacity: 0.3; transform: translateY(-2px); } }

.oa-ask { position: relative; margin: 12px 16px 16px; border-radius: 26px; background: rgba(24, 24, 24, 0.05); }
.oa-ask:focus-within { background: #fff; box-shadow: inset 0 0 0 1px rgba(46, 132, 74, 0.35); }
.oa-ask-input { width: 100%; height: 50px; padding: 0 18px 0 52px; border: none; outline: none; background: transparent; font-family: inherit; font-size: 15px; }
.oa-ask-send { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); width: 32px; height: 32px; border-radius: 12px; border: none; cursor: pointer; display: grid; place-items: center; color: #fff; background: #181818; }
.oa-ask-send:disabled { opacity: 0.3; cursor: default; }

.oa-fade-enter-active, .oa-fade-leave-active { transition: opacity 0.2s ease; }
.oa-fade-enter-from, .oa-fade-leave-to { opacity: 0; }
</style>
