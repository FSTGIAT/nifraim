<template>
  <!-- Nifra Agent — the agent's back-office AI, alive. No tickets: it WRITES to
       you — a greeting, then ≤5 streamed lines (what arrived, what waits, what
       to do). A line that points at something ends with one small link that
       opens it inline (the draft to approve, the contact to add). A glass ask
       box for quick questions. Opens out of its icon (useOriginMorph). -->
  <Teleport to="body">
    <Transition name="na-fade">
      <div v-if="open" class="na-overlay" @click.self="close">
        <section ref="cardEl" class="na" role="dialog" aria-modal="true" aria-label="Nifra Agent">
          <div class="na-aurora" aria-hidden="true"><i></i><i></i><i></i></div>

          <button class="na-x" type="button" aria-label="סגור" @click="close">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>

          <!-- the agent -->
          <header class="na-stage">
            <div class="na-orb-wrap">
              <span class="na-halo" aria-hidden="true"></span>
              <span class="na-halo na-halo--2" aria-hidden="true"></span>
              <ThinkingOrbIsland class="na-orb" :state="orbState" :size="64" color="#0E8C8A" :dot-size="1.3" :dots="1.15" />
            </div>
            <strong class="na-name" dir="ltr">Nifra <b>Agent</b></strong>
            <span class="na-status"><i aria-hidden="true"></i>{{ statusText }}</span>
          </header>

          <div ref="feedEl" class="na-feed">
            <!-- what the agent writes -->
            <template v-if="store.narration">
              <div :key="runId" class="na-run">
              <h2 class="na-greeting">
                <AiStreamingText :text="store.narration.greeting" mode="word" :speed="38" :show-cursor="false" @complete="onGreetingDone" />
              </h2>
              <ol class="na-lines">
                <li v-for="(l, i) in store.narration.lines" v-show="i <= step" :key="i" class="na-line"
                    :class="{ 'is-handled': l.ref && !l.ref.startsWith('setup:') && lineDone[i] && !cardOf(l) }">
                  <span class="na-line-dot" aria-hidden="true"></span>
                  <div class="na-line-body">
                    <AiStreamingText :text="l.text" :speed="7" :start="i <= step" :show-cursor="i === step" @complete="onLineDone(i)" />
                    <span v-if="sentNote[i]" class="na-sent na-sent--line">
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>
                      {{ sentNote[i] }}
                    </span>
                    <!-- the action this line points at -->
                    <button v-if="lineDone[i] && l.ref === 'setup:mail'" type="button" class="na-link" @click="emit('open-mail')">
                      חיבור Mail Agent
                      <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>
                    </button>
                    <template v-if="lineDone[i] && cardOf(l)">
                      <button v-if="primary(cardOf(l))" type="button" class="na-link" :data-line-pill="i" @click="onPrimary(i, cardOf(l), $event)">
                        {{ openLine === i ? 'סגירה' : primary(cardOf(l)).label }}
                        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6"/></svg>
                      </button>
                      <button v-if="hasFinish(cardOf(l))" type="button" class="na-link na-link--quiet" :disabled="!!store.busy" @click="finish(cardOf(l))">טופל</button>
                    </template>
                    <!-- inline: the draft to approve / the contact to add -->
                    <Transition name="na-sheet">
                      <div v-if="openLine === i && cardOf(l)" :id="'na-sheet-' + i" class="na-sheet">
                        <template v-if="cardOf(l).actions.includes('set_email')">
                          <label class="na-sheet-label">המייל של איש הקשר ב{{ cardOf(l).title }}</label>
                          <div class="na-row">
                            <input v-model.trim="email" type="email" dir="ltr" placeholder="name@insurer.co.il" @keydown.enter="saveEmail(cardOf(l))" />
                            <button type="button" class="na-go" :disabled="!email || !!store.busy" @click="saveEmail(cardOf(l))">שמירה</button>
                          </div>
                        </template>
                        <template v-else-if="cardOf(l).draft_body && isSend(cardOf(l))">
                          <label class="na-sheet-label">{{ cardOf(l).kind === 'unpaid' ? `הפנייה לחברה · ${cardOf(l).policies} פוליסות` : 'התשובה שהכנתי' }}</label>
                          <textarea v-model="body" rows="7"></textarea>
                          <div class="na-row">
                            <button type="button" class="na-go" :disabled="!canSend || !!store.busy" @click="sendIt(cardOf(l))">
                              {{ store.busy ? 'שולח…' : 'אישור ושליחה' }}
                            </button>
                            <span v-if="!canSend" class="na-hint">כדי לשלוח — חברו את Nifraim Mail Agent (Gmail) בהגדרות</span>
                          </div>
                        </template>
                        <div v-else class="na-row">
                          <button type="button" class="na-go" :disabled="!!store.busy" @click="runPrimary(cardOf(l))">{{ primary(cardOf(l)).label }}</button>
                        </div>
                        <p v-if="store.error" class="na-err">{{ store.error }}</p>
                      </div>
                    </Transition>
                  </div>
                </li>
              </ol>

              <!-- everything that waits, by AREA: a tile per area (count + one line); one opens at a time -->
              <section v-if="briefDone && store.cards.length" class="na-inbox" aria-label="כל מה שמחכה לך">
                <h3 class="na-inbox-title">כל מה שמחכה לך <span class="ltr-number">{{ store.cards.length }}</span></h3>
                <div class="na-areas">
                  <button v-for="(a, ai) in areas" :key="a.key" type="button" class="na-area" :class="{ 'is-on': openArea === a.key }" :style="{ '--i': ai }"
                          :aria-expanded="openArea === a.key" @click="toggleArea(a.key)">
                    <span class="na-area-icon" aria-hidden="true">
                      <svg v-if="a.key === 'calls'" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg>
                      <svg v-else-if="a.key === 'unpaid'" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="8" r="6"/><path d="M18.1 10.4A6 6 0 1 1 10.3 18"/><path d="M7 6h1v4"/></svg>
                      <svg v-else viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/></svg>
                    </span>
                    <span class="na-area-text">
                      <span class="na-area-name">{{ a.label }} <b class="ltr-number">{{ a.n }}</b></span>
                      <span class="na-area-sub">{{ a.sub }}</span>
                    </span>
                    <svg class="na-area-chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>
                  </button>
                </div>

                <div class="na-fold" :class="{ 'is-open': !!openArea }">
                  <div class="na-fold-inner">
                  <div v-if="listArea" :key="listArea" class="na-area-list">
                    <template v-for="g in groups" :key="g.key">
                      <h4 class="na-group" :style="{ '--i': g.offset }">{{ g.label }} <span class="ltr-number">{{ g.cards.length }}</span></h4>
                      <ul class="na-items">
                        <li v-for="(c, ci) in g.cards.slice(0, g.shown)" :key="c.id" class="na-item" :class="{ 'is-open': openCard === c.id }" :style="{ '--i': g.offset + ci }">
                          <div class="na-item-main">
                            <div class="na-item-text">
                              <strong class="na-item-title">{{ c.title }}</strong>
                              <span class="na-item-sub">{{ c.text }}</span>
                              <span v-if="c.meta" class="na-item-kind">{{ c.meta }}</span>
                            </div>
                            <div class="na-item-acts">
                              <span v-if="sentNote['c:' + c.id]" class="na-sent">
                                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>
                                {{ sentNote['c:' + c.id] }}
                              </span>
                              <button v-if="primary(c)" type="button" class="na-link" :disabled="!!store.busy && c.kind === 'promise'" @click="rowPrimary(c, $event)">
                                {{ openCard === c.id ? 'סגירה' : primary(c).label }}
                              </button>
                              <button v-if="hasFinish(c)" type="button" class="na-link na-link--quiet" :disabled="!!store.busy" @click="finish(c)">טופל</button>
                            </div>
                          </div>
                          <Transition name="na-sheet">
                            <div v-if="openCard === c.id" class="na-sheet">
                              <template v-if="c.actions.includes('set_email')">
                                <label class="na-sheet-label">המייל של איש הקשר ב{{ c.title }}</label>
                                <div class="na-row">
                                  <input v-model.trim="email" type="email" dir="ltr" placeholder="name@insurer.co.il" @keydown.enter="saveEmail(c)" />
                                  <button type="button" class="na-go" :disabled="!email || !!store.busy" @click="saveEmail(c)">שמירה</button>
                                </div>
                              </template>
                              <template v-else-if="c.draft_body && isSend(c)">
                                <label class="na-sheet-label">{{ c.kind === 'unpaid' ? `הפנייה לחברה · ${c.policies} פוליסות` : 'התשובה שהכנתי' }}</label>
                                <textarea v-model="body" rows="7"></textarea>
                                <div class="na-row">
                                  <button type="button" class="na-go" :disabled="!canSend || !!store.busy" @click="sendIt(c)">{{ store.busy ? 'שולח…' : 'אישור ושליחה' }}</button>
                                  <span v-if="!canSend" class="na-hint">כדי לשלוח — חברו את Nifraim Mail Agent (Gmail) בהגדרות</span>
                                </div>
                              </template>
                              <div v-else class="na-row">
                                <button type="button" class="na-go" :disabled="!!store.busy" @click="runPrimary(c)">{{ primary(c).label }}</button>
                              </div>
                              <p v-if="store.error" class="na-err">{{ store.error }}</p>
                            </div>
                          </Transition>
                        </li>
                      </ul>
                      <button v-if="g.cards.length > g.shown" type="button" class="na-more" @click="more[g.key] = (more[g.key] || 0) + 5">
                        עוד <span class="ltr-number">{{ g.cards.length - g.shown }}</span>
                      </button>
                    </template>
                  </div>
                  </div>
                </div>
              </section>
              </div>
            </template>
            <p v-else class="na-thinking" aria-label="כותב"><i></i><i></i><i></i></p>

            <!-- the short Q&A -->
            <div v-for="(m, i) in store.thread" :key="'t' + i" class="na-qa" :class="'na-qa--' + m.role">
              <AiStreamingText v-if="m.role === 'agent'" :text="m.text" :speed="7" :show-cursor="i === store.thread.length - 1" />
              <span v-else>{{ m.text }}</span>
              <AgentCallCard v-if="m.call" :call="m.call" :notify="store.notifyCall" />
              <InlineVizs v-if="m.vizs && m.vizs.length" :vizs="m.vizs" class="na-vizs" @open-legacy="(v) => emit('open-vizs', v)" />
              <!-- what the agent prepared: editable, sent only on approve -->
              <Transition name="na-sheet">
                <div v-if="m.proposal && m.proposal.status !== 'dropped'" class="na-sheet na-prop" :class="{ 'is-sent': m.proposal.status === 'sent' }">
                  <div class="na-prop-head">
                    <AgentCreateDrawing :kind="m.proposal.kind" :state="m.proposal.status === 'sent' ? 'sent' : 'open'" />
                    <div class="na-prop-titles">
                      <strong>{{ propTitle(m.proposal) }}</strong>
                      <span v-if="m.proposal.status === 'sent'" class="na-sent">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"/></svg>
                        {{ m.proposal.kind === 'meeting' ? 'הזימון נשלח' : m.proposal.kind === 'call_task' ? 'סומן כבוצע' : 'נשלח' }}
                      </span>
                      <span v-else class="na-prop-sub">הכנתי — עברו, שנו מה שצריך ואשרו</span>
                    </div>
                  </div>
                  <fieldset :disabled="m.proposal.status === 'sent'" class="na-prop-fields">
                    <p v-if="m.proposal.kind === 'maslaka'" class="na-prop-sum">
                      בקשת <b dir="ltr">{{ m.proposal.code }}</b> — {{ m.proposal.code_he }}
                      ל{{ m.proposal.customer_name || 'ת.ז ' + m.proposal.customer_id_number }}. התשובה מגיעה תוך שעות.
                    </p>
                    <p v-else-if="m.proposal.kind === 'call_task'" class="na-prop-sum">
                      לסמן כבוצע: <b>{{ m.proposal.text }}</b>{{ m.proposal.customer ? ' · ' + m.proposal.customer : '' }}
                    </p>
                    <p v-else-if="m.proposal.kind === 'collection'" class="na-prop-sum">
                      {{ m.proposal.case_status === 'sent' ? 'תזכורת' : 'פנייה' }} ל{{ m.proposal.company }} על {{ m.proposal.customers }} לקוחות
                      · צפי <span class="ltr-number">₪{{ Number(m.proposal.expected || 0).toLocaleString('he-IL') }}</span>
                    </p>
                    <label v-else-if="m.proposal.kind !== 'call_task'" class="na-f"><span>אל</span><input v-model.trim="m.proposal.to_email" type="email" dir="ltr" /></label>
                    <template v-if="m.proposal.kind === 'maslaka' || m.proposal.kind === 'collection' || m.proposal.kind === 'call_task'"></template>
                    <template v-else-if="m.proposal.kind === 'meeting'">
                      <label class="na-f"><span>נושא</span><input v-model="m.proposal.title" /></label>
                      <div class="na-f-row">
                        <label class="na-f"><span>תאריך</span><input :value="m.proposal.start.slice(0, 10)" type="date" dir="ltr" @input="setStart(m.proposal, $event.target.value, null)" /></label>
                        <label class="na-f"><span>שעה</span><input :value="m.proposal.start.slice(11, 16)" type="time" dir="ltr" step="300" @input="setStart(m.proposal, null, $event.target.value)" /></label>
                        <label class="na-f na-f--s"><span>דקות</span><input v-model.number="m.proposal.duration_min" type="number" min="10" max="480" step="5" dir="ltr" /></label>
                      </div>
                      <label class="na-f"><span>מיקום</span><input v-model="m.proposal.location" placeholder="משרד · טלפון · קישור לזום" /></label>
                    </template>
                    <template v-else>
                      <label class="na-f"><span>נושא</span><input v-model="m.proposal.subject" /></label>
                      <textarea v-model="m.proposal.body" rows="6"></textarea>
                    </template>
                  </fieldset>
                  <div v-if="m.proposal.status !== 'sent'" class="na-row">
                    <button type="button" class="na-go" :disabled="(!['maslaka', 'call_task'].includes(m.proposal.kind) && !canSend) || store.busy === 'act'" @click="store.approve(m)">
                      {{ store.busy === 'act' ? 'שולח…' : m.proposal.kind === 'meeting' ? 'אישור ושליחת זימון' : m.proposal.kind === 'maslaka' ? 'אישור ושליחה למסלקה' : m.proposal.kind === 'call_task' ? 'אישור — בוצע' : 'אישור ושליחה' }}
                    </button>
                    <button type="button" class="na-link na-link--quiet" @click="m.proposal.status = 'dropped'">ביטול</button>
                    <span v-if="!canSend && !['maslaka', 'call_task'].includes(m.proposal.kind)" class="na-hint">כדי לשלוח — חברו את Nifraim Mail Agent (Gmail) בהגדרות</span>
                  </div>
                  <p v-if="store.error && i === store.thread.length - 1" class="na-err">{{ store.error }}</p>
                </div>
              </Transition>
            </div>
            <p v-if="store.busy === 'ask'" class="na-thinking"><i></i><i></i><i></i></p>
          </div>

          <form class="na-ask" @submit.prevent="askNow">
            <!-- @ — the agent's contacts: customers (name · ת.ז), insurer contacts, mail senders -->
            <Transition name="na-sheet">
              <div v-if="men.open" class="na-men" role="listbox" aria-label="אנשי קשר">
                <div class="na-men-head">
                  <span>אנשי קשר</span>
                  <b v-if="men.query" class="na-men-q">{{ men.query }}</b>
                </div>
                <ul v-if="men.items.length" class="na-men-list">
                  <li v-for="(c, k) in men.items" :key="c.kind + (c.id_number || c.email) + k"
                      class="na-men-row" :class="{ 'is-active': k === men.active }" role="option" :aria-selected="k === men.active"
                      @mousedown.prevent="pick(c)" @mouseenter="men.active = k">
                    <span class="na-men-ic" :class="'na-men-ic--' + c.kind" aria-hidden="true">
                      <svg v-if="c.kind === 'company'" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6"/></svg>
                      <svg v-else-if="c.kind === 'mail'" viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="5" width="19" height="14" rx="2.5"/><path d="m3 7 9 6 9-6"/></svg>
                      <template v-else>{{ (c.name || '?').trim().charAt(0) }}</template>
                    </span>
                    <span class="na-men-txt">
                      <strong>{{ c.name }}</strong>
                      <small>
                        <span v-if="c.id_number">ת.ז <span class="ltr-number">{{ c.id_number }}</span></span>
                        <span v-if="c.email" class="na-men-mail" dir="ltr">{{ c.email }}</span>
                        <span v-else-if="c.sub">{{ c.sub }}</span>
                      </small>
                    </span>
                  </li>
                </ul>
                <p v-else class="na-men-empty">{{ men.loading ? 'מחפש…' : 'לא נמצא איש קשר' }}</p>
              </div>
            </Transition>
            <button type="button" class="na-at" aria-label="בחירת איש קשר" title="איש קשר (@)" @click="openAt">@</button>
            <input ref="askEl" v-model="q" class="na-ask-input" placeholder="דברו עם Nifra Agent… (@ לאנשי קשר)" maxlength="500"
                   @input="onAskInput" @keydown="onAskKey" @click="onAskInput" @blur="closeMenSoon" />
            <button class="na-ask-send" type="submit" :disabled="!q.trim() || store.busy === 'ask'" aria-label="שלח">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="14 9 9 4 4 9"/><path d="M20 20h-7a4 4 0 0 1-4-4V4"/></svg>
            </button>
          </form>
        </section>
      </div>
    </Transition>
  </Teleport>
  <!-- a call's follow-up email: opens as a letter out of its pill -->
  <CallFollowupLetter v-if="letter" :key="letter.card.id" :card="letter.card" :origin="letter.origin"
                      @close="letter = null" @sent="(name) => (sentNote[letter.i] = 'נשלח ל' + name)"
                      @dismissed="() => {}" @open-call="(id) => { letter = null; emit('open-call', id) }"
                      @open-mail="letter = null; emit('open-mail')" />
</template>

<script setup>
import AgentCallCard from '../ai/AgentCallCard.vue'
import InlineVizs from '../ai/InlineVizs.vue'
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { useOfficeAgentStore } from '../../stores/officeAgent.js'
import { useOriginMorph } from '../../composables/useOriginMorph.js'
import ThinkingOrbIsland from './ThinkingOrbIsland.vue'
import AiStreamingText from '../ui/AiStreamingText.vue'
import AgentCreateDrawing from './AgentCreateDrawing.vue'
import CallFollowupLetter from './CallFollowupLetter.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  originEl: { type: Object, default: null },
  focusCard: { type: String, default: null }, // opened by itself on a call card → expand that line
})
const emit = defineEmits(['update:open', 'open-mail', 'open-vizs', 'open-call'])
const propTitle = (p) => p.kind === 'call_task' ? 'משימה משיחה' : p.kind === 'maslaka' ? 'בקשה למסלקה' : p.kind === 'collection' ? 'פנייה לחברה' : p.kind === 'meeting' ? (isSelf(p) ? 'תזכורת ביומן' : 'זימון לפגישה') : 'מייל'
const store = useOfficeAgentStore()

// sequential streaming: greeting → line 0 → line 1 …
const step = ref(-1)
const lineDone = reactive({})
function onGreetingDone() { if (step.value < 0) step.value = 0 }
function onLineDone(i) {
  lineDone[i] = true
  if (i === step.value) step.value = i + 1
}
const writing = computed(() => store.narrating || (!!store.narration && step.value < store.narration.lines.length))
// 'composing' only while really waiting on the server; writing is calm
// 'solving' for a beat when the agent just created something
const justMade = ref(false)
let madeTimer = 0
watch(() => store.thread.length, () => {
  const last = store.thread[store.thread.length - 1]
  if (last?.proposal) {
    justMade.value = true
    clearTimeout(madeTimer)
    madeTimer = setTimeout(() => { justMade.value = false }, 2200)
  }
})
const orbState = computed(() => (justMade.value ? 'solving'
  : store.busy === 'ask' || (store.narrating && !store.narration) ? 'composing' : 'connecting'))
const isSelf = (p) => !!store.brief?.mailbox?.mailbox_address && p.to_email?.toLowerCase() === store.brief.mailbox.mailbox_address.toLowerCase()
const statusText = computed(() => {
  if (store.narrating && !store.narration) return 'עובר על המיילים והעמלות…'
  if (store.busy === 'ask') return store.askStatus ? store.askStatus + '…' : 'בודק…'
  if (writing.value) return 'כותב לך…'
  return 'עובד בשבילך'
})

const cardOf = (l) => (l?.ref ? store.cards.find((c) => c.id === l.ref) : null)
const canSend = computed(() => !!store.brief?.mailbox?.can_send)
const isSend = (c) => c.actions.includes('send_reply') || c.actions.includes('send_case')
const hasFinish = (c) => c.actions.includes('done') || c.actions.includes('resolve') || c.actions.includes('dismiss_followup')
function primary(c) {
  if (c.actions.includes('task_done')) return { action: 'task_done', label: 'סימנתי שבוצע' }
  if (c.actions.includes('send_followup')) return { action: 'send_followup', label: 'לסיכום שהכנתי' }
  if (c.actions.includes('send_reply')) return { action: 'send_reply', label: 'לתשובה שהכנתי' }
  if (c.actions.includes('send_case')) return { action: 'send_case', label: 'לפנייה לחברה' }
  if (c.actions.includes('set_email')) return { action: 'set_email', label: 'הוספת מייל' }
  if (c.actions.includes('remind')) return { action: 'remind', label: 'שליחת תזכורת' }
  if (c.actions.includes('make_draft')) return { action: 'make_draft', label: 'הכנת טיוטה' }
  if (c.actions.includes('import')) return { action: 'import', label: 'טעינת הקובץ' }
  return null
}

const openLine = ref(-1)
const body = ref('')
const email = ref('')
const sentNote = reactive({})
// a call card opens as a letter (CallFollowupLetter), not the inline sheet
const letter = ref(null) // { card, origin, i }
function openLetter(i, c, origin) { letter.value = { card: c, origin: origin || null, i } }
function onPrimary(i, c, ev) {
  if (c.kind === 'call') { openLetter(i, c, ev?.currentTarget); return }
  // a call promise has one action and nothing to edit — tick it right here
  if (c.kind === 'promise') { store.act(c, 'task_done').then((ok) => { if (ok) sentNote[i] = 'סומן כבוצע' }); return }
  toggle(i, c)
}
function toggle(i, c) {
  openLine.value = openLine.value === i ? -1 : i
  body.value = c.draft_body || ''
  email.value = c.to_email || ''
  store.error = ''
  store.errorCode = ''
}
function closeSheets() { openLine.value = -1; openCard.value = null }
async function saveEmail(c) { if (email.value && (await store.act(c, 'set_email', { email: email.value }))) closeSheets() }
async function runPrimary(c) { if (await store.act(c, primary(c).action)) closeSheets() }
// approve the (edited) draft: a mail reply sends the text as edited; a company case saves the edit first
async function sendIt(c) {
  const action = primary(c).action
  if (action === 'send_case' && body.value !== (c.draft_body || '') && !(await store.act(c, 'save_case_body', { body: body.value }))) return
  if (await store.act(c, action, { body: body.value, subject: c.draft_subject })) closeSheets()
}
async function finish(c) {
  const action = c.actions.includes('dismiss_followup') ? 'dismiss_followup' : c.actions.includes('resolve') ? 'resolve' : 'done'
  if (await store.act(c, action)) closeSheets()
}

// ── everything that waits, by area ──
const AREA = { call: 'calls', promise: 'calls', mail: 'mail', unpaid: 'unpaid' }
const openArea = ref(null)
const openCard = ref(null)
const more = reactive({})
const briefDone = computed(() => !!store.narration && step.value >= store.narration.lines.length)
const ils = (n) => '₪' + Math.round(n || 0).toLocaleString('he-IL')
const areas = computed(() => {
  const by = { unpaid: [], calls: [], mail: [] }
  for (const c of store.cards) if (AREA[c.kind]) by[AREA[c.kind]].push(c)
  const late = by.calls.filter((c) => c.kind === 'promise' && c.sub === 'overdue').length
  const toSend = by.calls.filter((c) => c.kind === 'call').length
  const out = []
  if (by.unpaid.length) {
    const exp = store.brief?.unpaid?.expected
    out.push({ key: 'unpaid', label: 'עמלות', n: by.unpaid.length,
      sub: `${by.unpaid.length} חברות לגבייה` + (exp >= 1 ? ` · ${ils(exp)} צפי` : '') })
  }
  if (by.calls.length) {
    out.push({ key: 'calls', label: 'שיחות', n: by.calls.length,
      sub: [late && `${late} הבטחות באיחור`, toSend && `${toSend} סיכומים לשליחה`].filter(Boolean).join(' · ') || 'הבטחות להיום' })
  }
  if (by.mail.length) out.push({ key: 'mail', label: 'מיילים', n: by.mail.length, sub: `${by.mail.length} מחכים לטיפול` })
  return out
})
// inside an open area: small named groups, 3 shown, "עוד" adds 5
const groups = computed(() => {
  const area = listArea.value
  const mine = store.cards.filter((c) => AREA[c.kind] === area)
  const defs = area === 'calls'
    ? [['late', 'הבטחות שעבר מועדן', (c) => c.kind === 'promise' && c.sub === 'overdue'],
       ['today', 'הבטחות להיום', (c) => c.kind === 'promise' && c.sub !== 'overdue'],
       ['send', 'סיכומים מוכנים לשליחה ללקוח', (c) => c.kind === 'call']]
    : area === 'unpaid' ? [['unpaid', 'חברות שלא שילמו', () => true]]
    : [['mail', 'מיילים שמחכים לך', () => true]]
  let offset = 0
  return defs.map(([key, label, f]) => ({ key, label, cards: mine.filter(f), shown: 3 + (more[key] || 0) }))
    .filter((g) => g.cards.length)
    .map((g) => { const o = { ...g, offset }; offset += Math.min(g.cards.length, g.shown) + 1; return o })
})
// the list stays mounted while it folds shut, then empties
const listArea = ref(null)
let foldTimer = 0
watch(openArea, (k) => {
  clearTimeout(foldTimer)
  if (k) listArea.value = k
  else foldTimer = setTimeout(() => { listArea.value = null }, 650)
})
function toggleArea(k) {
  openArea.value = openArea.value === k ? null : k
  openCard.value = null
  // glide the feed so the tiles rise to the top WHILE the list unfolds under them — the fold
  // grows over 0.6s, so the scroll target is re-read each frame (it isn't reachable at once)
  if (openArea.value) nextTick(() => glideTo(() => feedEl.value?.querySelector('.na-inbox')?.offsetTop - 12))
}
function glideTo(target, ms = 750) {
  const feed = feedEl.value
  if (!feed) return
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) { setTimeout(() => { feed.scrollTop = target() || 0 }, 650); return }
  const from = feed.scrollTop
  const t0 = performance.now()
  const ease = (x) => 1 - Math.pow(1 - x, 3)
  const tick = (now) => {
    const k = Math.min(1, (now - t0) / ms)
    const to = Math.min(target() || 0, feed.scrollHeight - feed.clientHeight)
    feed.scrollTop = from + (to - from) * ease(k)
    if (k < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}
watch(areas, (a) => { if (openArea.value && !a.some((x) => x.key === openArea.value)) openArea.value = null })
function rowPrimary(c, ev) {
  if (c.kind === 'call') { openLetter('c:' + c.id, c, ev?.currentTarget); return }
  if (c.kind === 'promise') { store.act(c, 'task_done').then((ok) => { if (ok) sentNote['c:' + c.id] = 'סומן כבוצע' }); return }
  if (openCard.value === c.id) { openCard.value = null; return }
  openLine.value = -1
  openCard.value = c.id
  body.value = c.draft_body || ''
  email.value = c.to_email || ''
  store.error = ''
  store.errorCode = ''
}

// opened by itself on a call card: once that line has been written, expand it
const focusIndex = computed(() => (props.focusCard && store.narration ? store.narration.lines.findIndex((l) => l.ref === props.focusCard) : -1))
let focusedFor = null
watch(() => [focusIndex.value, focusIndex.value >= 0 && lineDone[focusIndex.value], props.open], ([i, done, open]) => {
  if (!open || i < 0 || !done || focusedFor === props.focusCard) return
  const c = cardOf(store.narration.lines[i])
  if (!c) return
  focusedFor = props.focusCard
  // let the panel settle and the pill appear, then the envelope grows out of it
  setTimeout(() => {
    const pill = cardEl.value?.querySelector(`[data-line-pill="${i}"]`)
    pill?.scrollIntoView({ block: 'nearest' })
    openLetter(i, c, pill)
  }, 700)
})

function setStart(p, date, time) {
  p.start = `${date || p.start.slice(0, 10)}T${time || p.start.slice(11, 16)}`
}

const q = ref('')
const feedEl = ref(null)
// ── @ mentions ──
const askEl = ref(null)
const picked = ref([]) // contacts chosen with @ — sent with the question as exact context
const men = reactive({ open: false, query: '', start: -1, items: [], active: 0, loading: false })
let menTimer = 0
let menSeq = 0
function onAskInput() {
  const el = askEl.value
  if (!el) return
  const caret = el.selectionStart ?? q.value.length
  // "ל@דנה" works too; only an email's @ (a latin letter/digit before it) doesn't open it
  const m = /(^|[^A-Za-z0-9._%+-])@([^\s@]{0,30})$/.exec(q.value.slice(0, caret))
  if (!m) { men.open = false; return }
  men.open = true
  men.start = caret - m[2].length - 1
  if (m[2] === men.query && men.items.length) return
  men.query = m[2]
  men.active = 0
  men.loading = true
  clearTimeout(menTimer)
  const seq = ++menSeq
  menTimer = setTimeout(async () => {
    const items = await store.searchContacts(men.query)
    if (seq !== menSeq) return
    men.items = items
    men.loading = false
  }, 120)
}
function onAskKey(e) {
  if (!men.open) return
  if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
    e.preventDefault()
    const n = men.items.length || 1
    men.active = (men.active + (e.key === 'ArrowDown' ? 1 : n - 1)) % n
  } else if ((e.key === 'Enter' || e.key === 'Tab') && men.items[men.active]) {
    e.preventDefault()
    pick(men.items[men.active])
  } else if (e.key === 'Escape') {
    e.preventDefault()
    e.stopPropagation()
    men.open = false
  }
}
async function pick(c) {
  const el = askEl.value
  const caret = el?.selectionStart ?? q.value.length
  const tag = '@' + c.name + ' '
  q.value = q.value.slice(0, men.start) + tag + q.value.slice(caret)
  if (!picked.value.some((p) => p.name === c.name && p.id_number === c.id_number)) picked.value.push(c)
  men.open = false
  men.query = ''
  men.items = []
  await nextTick()
  const pos = men.start + tag.length
  el?.focus()
  el?.setSelectionRange(pos, pos)
}
async function openAt() {
  const el = askEl.value
  const caret = el?.selectionStart ?? q.value.length
  const before = q.value.slice(0, caret)
  const pad = before && !/\s$/.test(before) ? ' ' : ''
  q.value = before + pad + '@' + q.value.slice(caret)
  await nextTick()
  const pos = caret + pad.length + 1
  el?.focus()
  el?.setSelectionRange(pos, pos)
  men.items = []
  onAskInput()
}
function closeMenSoon() { setTimeout(() => { men.open = false }, 120) }

async function askNow() {
  if (men.open) return
  const text = q.value
  const mentions = picked.value
    .filter((c) => text.includes('@' + c.name))
    .map(({ kind, name, id_number, email }) => ({ kind, name, id_number, email }))
  q.value = ''
  picked.value = []
  const p = store.ask(text, mentions)
  await nextTick()
  feedEl.value?.scrollTo({ top: feedEl.value.scrollHeight, behavior: 'smooth' })
  await p
  await nextTick()
  feedEl.value?.scrollTo({ top: feedEl.value.scrollHeight, behavior: 'smooth' })
}

// iPhone-style open/close out of the icon. The brief is prefetched by the icon,
// so the agent starts writing at once; a silent re-narrate refreshes it behind.
const runId = ref(0)
const morph = useOriginMorph()
const cardEl = ref(null)
watch(() => props.open, async (v) => {
  if (!v) return
  step.value = -1
  for (const k of Object.keys(lineDone)) delete lineDone[k]
  openLine.value = -1
  focusedFor = null
  letter.value = null
  for (const k of Object.keys(sentNote)) delete sentNote[k]
  runId.value++
  morph.remember(props.originEl)
  await nextTick()
  morph.grow(cardEl.value)
  store.narrate()
})
async function close() {
  if (morph.hasOrigin()) await morph.shrink(cardEl.value)
  emit('update:open', false)
}
</script>

<style scoped>
.na-overlay {
  position: fixed; inset: 0; z-index: 1010; display: grid; place-items: center; padding: 16px;
  background: rgba(10, 20, 22, 0.38); backdrop-filter: blur(6px);
}
.na {
  position: relative; width: min(820px, 100%); height: min(780px, calc(100vh - 32px));
  display: flex; flex-direction: column; overflow: hidden;
  border-radius: 30px; background: #F7FBFA;
  box-shadow: 0 40px 100px rgba(8, 40, 38, 0.35), inset 0 0 0 1px rgba(255, 255, 255, 0.6);
  font-family: 'Heebo', sans-serif; color: #10201F;
}
/* aurora: three soft blobs drifting behind glass */
.na-aurora { position: absolute; inset: 0; overflow: hidden; pointer-events: none; }
.na-aurora i { position: absolute; border-radius: 50%; filter: blur(64px); opacity: 0.55; }
.na-aurora i:nth-child(1) { width: 420px; height: 420px; top: -150px; right: -90px; background: #8FD9C6; animation: naDrift1 18s ease-in-out infinite; }
.na-aurora i:nth-child(2) { width: 380px; height: 380px; top: 90px; left: -150px; background: #BFE6F2; animation: naDrift2 22s ease-in-out infinite; }
.na-aurora i:nth-child(3) { width: 360px; height: 360px; bottom: -170px; right: 30%; background: #D6F0E8; animation: naDrift1 26s ease-in-out infinite reverse; }
@keyframes naDrift1 { 50% { transform: translate(-60px, 40px) scale(1.12); } }
@keyframes naDrift2 { 50% { transform: translate(70px, -30px) scale(0.92); } }

.na-x {
  position: absolute; top: 16px; left: 16px; z-index: 3; width: 34px; height: 34px; border-radius: 12px;
  border: none; background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(8px); cursor: pointer;
  display: grid; place-items: center; color: #3E4B4A;
}
.na-x:hover { background: #fff; color: #10201F; }

.na-stage { position: relative; z-index: 1; display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 26px 20px 4px; }
.na-orb-wrap { position: relative; width: 128px; height: 128px; display: grid; place-items: center; }
.na-orb-wrap::before {
  content: ''; position: absolute; inset: 12px; border-radius: 50%;
  background: radial-gradient(circle at 38% 32%, rgba(255, 255, 255, 0.98), rgba(226, 244, 240, 0.8) 58%, rgba(14, 140, 138, 0.1));
  box-shadow: 0 18px 44px rgba(14, 140, 138, 0.24), inset 0 0 0 1px rgba(255, 255, 255, 0.85);
  animation: naBreathe 4.8s ease-in-out infinite;
}
.na-orb { position: relative; transform: scale(1.6); }
.na-halo { position: absolute; inset: 0; border-radius: 50%; border: 1px solid rgba(14, 140, 138, 0.3); animation: naHalo 3.6s ease-out infinite; }
.na-halo--2 { animation-delay: 1.8s; }
@keyframes naHalo { from { transform: scale(0.74); opacity: 0.9; } to { transform: scale(1.35); opacity: 0; } }
@keyframes naBreathe { 50% { transform: scale(1.04); } }
.na-name { font-size: 22px; font-weight: 900; letter-spacing: -0.03em; }
.na-name b { color: #0E8C8A; font-weight: 900; }
.na-status { display: inline-flex; align-items: center; gap: 7px; font-size: 13px; font-weight: 600; color: #4A5B5A; }
.na-status i { width: 7px; height: 7px; border-radius: 50%; background: #1DB39E; box-shadow: 0 0 0 4px rgba(29, 179, 158, 0.18); animation: naPulse 2s ease-in-out infinite; }
@keyframes naPulse { 50% { box-shadow: 0 0 0 7px rgba(29, 179, 158, 0.04); } }

.na-feed { position: relative; z-index: 1; flex: 1; overflow-y: auto; padding: 8px clamp(20px, 7vw, 72px) 18px;
  -webkit-mask-image: linear-gradient(to bottom, transparent 0, #000 28px); mask-image: linear-gradient(to bottom, transparent 0, #000 28px); }
.na-greeting { margin: 12px 0 16px; font-size: clamp(26px, 3.2vw, 34px); font-weight: 900; letter-spacing: -0.03em; line-height: 1.2; }
.na-lines { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 14px; }
.na-line { display: flex; gap: 12px; align-items: flex-start; animation: naIn 0.35s ease both; transition: opacity 0.3s ease; }
@keyframes naIn { from { opacity: 0; transform: translateY(6px); } }
.na-line-dot { flex-shrink: 0; width: 8px; height: 8px; margin-top: 11px; border-radius: 50%; background: #0E8C8A; box-shadow: 0 0 0 4px rgba(14, 140, 138, 0.14); }
.na-line-body { flex: 1; min-width: 0; font-size: 17px; line-height: 1.7; color: #1B2A29; }
.na-line.is-handled { opacity: 0.45; }
.na-line.is-handled .na-line-body { text-decoration: line-through; text-decoration-color: rgba(14, 140, 138, 0.5); }
.na-line.is-handled .na-line-dot { background: #9BB; box-shadow: none; }
.na-link {
  display: inline-flex; align-items: center; gap: 3px; margin-inline-start: 8px; padding: 2px 11px; border-radius: 999px;
  border: none; cursor: pointer; font-family: inherit; font-size: 13.5px; font-weight: 800; color: #0A6664;
  background: rgba(14, 140, 138, 0.1); animation: naIn 0.3s ease both; vertical-align: 1px;
}
.na-link:hover { background: rgba(14, 140, 138, 0.18); }
.na-link--quiet { color: #4A5B5A; background: rgba(24, 24, 24, 0.05); }
.na-link--quiet:hover { background: rgba(24, 24, 24, 0.09); }
.na-sheet {
  margin-top: 10px; padding: 14px; border-radius: 18px;
  background: rgba(255, 255, 255, 0.78); backdrop-filter: blur(12px);
  box-shadow: 0 10px 30px rgba(8, 40, 38, 0.1), inset 0 0 0 1px rgba(255, 255, 255, 0.9);
  display: flex; flex-direction: column; gap: 8px; text-decoration: none;
}
.na-sheet-label { font-size: 12.5px; font-weight: 800; color: #4A5B5A; }
.na-sheet .na-f input { height: 38px; }
.na-sheet textarea {
  width: 100%; box-sizing: border-box; resize: vertical; padding: 10px 12px; border-radius: 12px; border: 1px solid rgba(14, 140, 138, 0.18);
  font-family: inherit; font-size: 14px; line-height: 1.6; background: rgba(255, 255, 255, 0.9); outline: none; color: #10201F;
}
.na-sheet textarea:focus, .na-row input:focus { border-color: rgba(14, 140, 138, 0.5); }
.na-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.na-row input { flex: 1; min-width: 180px; height: 40px; padding: 0 12px; border-radius: 12px; border: 1px solid rgba(14, 140, 138, 0.2); font-family: inherit; font-size: 14px; outline: none; background: #fff; }
.na-go { height: 40px; padding: 0 18px; border-radius: 12px; border: none; cursor: pointer; font-family: inherit; font-size: 14px; font-weight: 800; color: #fff; background: #10201F; transition: transform 0.15s ease; }
.na-go:hover:not(:disabled) { background: #000; transform: translateY(-1px); }
.na-go:disabled { opacity: 0.35; cursor: default; }
.na-hint { font-size: 12.5px; color: #8A6300; }
.na-hint--calm { margin: 0; color: #4A5B5A; }
.na-link--plain { background: none; color: #0A6664; text-decoration: underline; text-underline-offset: 3px; font-weight: 700; }
.na-link--plain:hover { background: rgba(14, 140, 138, 0.08); }
/* the full list */
.na-inbox { margin-top: 28px; padding-top: 18px; border-top: 1px solid rgba(14, 140, 138, 0.14); animation: naIn 0.4s ease both; }
.na-inbox-title { margin: 0 0 10px; font-size: 15px; font-weight: 800; color: #10201F; display: flex; align-items: baseline; gap: 8px; }
.na-inbox-title span { font-size: 13px; font-weight: 700; color: #0A6664; }
.na-areas { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 8px; }
.na-area { display: flex; align-items: center; gap: 10px; padding: 12px 14px; border: none; border-radius: 14px; cursor: pointer;
  font-family: inherit; text-align: start; color: #10201F; background: rgba(255, 255, 255, 0.72);
  box-shadow: inset 0 0 0 1px rgba(16, 32, 31, 0.06); transition: background 0.2s ease, box-shadow 0.2s ease, transform 0.15s ease; }
.na-area:hover { background: rgba(255, 255, 255, 0.92); transform: translateY(-1px); }
.na-area.is-on { background: #fff; box-shadow: inset 0 0 0 1.5px #0E8C8A; }
.na-area-icon { flex-shrink: 0; width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; color: #0A6664; background: rgba(14, 140, 138, 0.1); }
.na-area-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
.na-area-name { font-size: 15px; font-weight: 800; }
.na-area-name b { font-weight: 800; color: #0A6664; margin-inline-start: 4px; }
.na-area-sub { font-size: 12.5px; color: #4A5B5A; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.na-area-chev { flex-shrink: 0; color: #6B7A79; transition: transform 0.25s ease; }
.na-area.is-on .na-area-chev { transform: rotate(180deg); }
.na-area-list { padding-top: 12px; display: flex; flex-direction: column; gap: 8px; }
/* silky: tiles rise in one after another; an area's list unfolds (grid rows 0fr → 1fr) and its
   rows follow in a cascade; folding back is the same curve, reversed */
.na-area { animation: naRise 0.7s cubic-bezier(0.22, 1, 0.36, 1) both; animation-delay: calc(var(--i, 0) * 90ms + 80ms); }
.na-fold { display: grid; grid-template-rows: 0fr; opacity: 0; transition: grid-template-rows 0.6s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.45s ease; }
.na-fold.is-open { grid-template-rows: 1fr; opacity: 1; }
.na-fold-inner { min-height: 0; overflow: hidden; }
.na-fold.is-open .na-item, .na-fold.is-open .na-group, .na-fold.is-open .na-more {
  animation: naRise 0.6s cubic-bezier(0.22, 1, 0.36, 1) both; animation-delay: calc(var(--i, 0) * 55ms + 120ms); }
@keyframes naRise { from { opacity: 0; transform: translateY(14px) scale(0.985); } }
.na-area-chev { transition: transform 0.45s cubic-bezier(0.22, 1, 0.36, 1) !important; }
.na-group { margin: 6px 0 0; font-size: 13px; font-weight: 800; color: #4A5B5A; display: flex; gap: 6px; }
.na-group span { color: #6B7A79; font-weight: 700; }
.na-more { align-self: flex-start; border: none; background: none; cursor: pointer; font-family: inherit; font-size: 13px; font-weight: 800;
  color: #0A6664; padding: 2px 4px; text-decoration: underline; text-underline-offset: 3px; }
.na-items { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
.na-item { border-radius: 14px; background: rgba(255, 255, 255, 0.72); box-shadow: inset 0 0 0 1px rgba(16, 32, 31, 0.06); padding: 12px 14px; }
.na-item.is-open { background: rgba(255, 255, 255, 0.9); }
.na-item-main { display: flex; align-items: center; gap: 12px; }
.na-item-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.na-item-kind { font-size: 12px; font-weight: 600; color: #6B7A79; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.na-item-title { font-size: 15px; font-weight: 800; color: #10201F; line-height: 1.35; }
.na-item-sub { font-size: 13.5px; color: #3E4F4E; line-height: 1.5; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.na-item-acts { flex-shrink: 0; display: flex; align-items: center; gap: 6px; }
.na-item-acts .na-link { margin: 0; }
@media (max-width: 560px) { .na-item-main { flex-direction: column; align-items: stretch; } .na-item-acts { justify-content: flex-start; } }
.na-sent--line { display: inline-flex; margin-inline-start: 10px; animation: naIn 0.4s ease both; }
.na-err .na-link { margin-inline-start: 8px; }
.na-err { margin: 0; font-size: 13px; font-weight: 700; color: #C23934; }
.na-sheet-enter-active { transition: opacity 0.45s ease, transform 0.55s cubic-bezier(0.22, 1, 0.36, 1); }
.na-sheet-leave-active { transition: opacity 0.25s ease, transform 0.3s ease; }
.na-sheet-enter-from, .na-sheet-leave-to { opacity: 0; transform: translateY(-8px); }

.na-prop { margin-top: 12px; }
.na-prop-head { display: flex; align-items: center; gap: 14px; padding-bottom: 4px; }
.na-prop-titles { display: flex; flex-direction: column; gap: 2px; }
.na-prop-titles strong { color: #10201F; font-size: 17px; font-weight: 900; letter-spacing: -0.02em; }
.na-prop-sub { font-size: 13px; color: #4A5B5A; animation: naIn .4s ease 1.2s both; }
.na-vizs { --viz-accent: var(--tab-automation, #0E8C8A); }   /* Nifra Agent's own colour */
.na-prop-sum { margin: 0; font-size: 14px; line-height: 1.6; color: var(--text-primary, #181818); }
.na-prop-sum b { font-weight: 800; }
.na-sent { display: inline-flex; align-items: center; gap: 4px; font-size: 13.5px; font-weight: 800; color: #1E7D4A; animation: naIn .4s ease 1.3s both; }
/* the fields appear once the drawing is made */
.na-prop:not(.is-sent) .na-prop-fields > *, .na-prop:not(.is-sent) > .na-row { animation: naIn .4s ease both; animation-delay: calc(.9s + var(--i, 0) * 70ms); }
.na-prop-fields > :nth-child(2) { --i: 1; } .na-prop-fields > :nth-child(3) { --i: 2; } .na-prop-fields > :nth-child(4) { --i: 3; }
.na-prop > .na-row { --i: 5; }
.na-prop.is-sent { opacity: 0.8; }
.na-prop-fields { border: none; margin: 0; padding: 0; min-width: 0; display: flex; flex-direction: column; gap: 8px; }
.na-f { display: flex; flex-direction: column; gap: 3px; flex: 1; min-width: 0; }
.na-f span { font-size: 12px; font-weight: 800; color: #4A5B5A; }
.na-f input, .na-prop textarea {
  width: 100%; box-sizing: border-box; height: 38px; padding: 0 11px; border-radius: 11px; border: 1px solid rgba(14, 140, 138, 0.2);
  font-family: inherit; font-size: 14px; color: #10201F; background: #fff; outline: none;
}
.na-prop textarea { height: auto; padding: 9px 11px; line-height: 1.6; resize: vertical; }
.na-f input:focus, .na-prop textarea:focus { border-color: rgba(14, 140, 138, 0.55); }
.na-f-row { display: flex; gap: 8px; flex-wrap: wrap; }
.na-f-row .na-f { min-width: 120px; }
.na-f--s { flex: 0 0 90px; min-width: 90px !important; }
.na-prop-fields:disabled input, .na-prop-fields:disabled textarea { background: rgba(255, 255, 255, 0.6); color: #3E4B4A; }
.na-qa { margin-top: 18px; font-size: 16px; line-height: 1.7; }
.na-qa--user { display: table; padding: 8px 14px; border-radius: 16px; background: rgba(14, 140, 138, 0.1); font-weight: 600; }
.na-qa--agent { color: #1B2A29; }
.na-thinking { display: inline-flex; gap: 5px; margin: 16px 0 0; }
.na-thinking i { width: 7px; height: 7px; border-radius: 50%; background: #0E8C8A; opacity: 0.5; animation: naDot 1s ease-in-out infinite; }
.na-thinking i:nth-child(2) { animation-delay: 0.15s; }
.na-thinking i:nth-child(3) { animation-delay: 0.3s; }
@keyframes naDot { 50% { opacity: 1; transform: translateY(-3px); } }

.na-ask {
  position: relative; z-index: 1; margin: 0 clamp(16px, 6vw, 64px) 20px; border-radius: 26px;
  background: rgba(255, 255, 255, 0.72); backdrop-filter: blur(14px);
  box-shadow: 0 12px 34px rgba(8, 40, 38, 0.12), inset 0 0 0 1px rgba(255, 255, 255, 0.9);
}
.na-ask:focus-within { box-shadow: 0 14px 38px rgba(8, 40, 38, 0.16), inset 0 0 0 1px rgba(14, 140, 138, 0.4); }
.na-ask-input { width: 100%; box-sizing: border-box; height: 54px; padding: 0 20px 0 96px; border: none; outline: none; background: transparent; font-family: inherit; font-size: 15.5px; color: #10201F; }
.na-ask-send { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); width: 36px; height: 36px; border-radius: 13px; border: none; cursor: pointer; display: grid; place-items: center; color: #fff; background: #0E8C8A; }
.na-ask-send:disabled { opacity: 0.3; cursor: default; }
.na-at {
  position: absolute; left: 52px; top: 50%; transform: translateY(-50%); z-index: 1;
  width: 34px; height: 34px; border-radius: 12px; border: none; cursor: pointer;
  font-family: inherit; font-size: 17px; font-weight: 800; color: #0A6664; background: rgba(14, 140, 138, 0.1);
}
.na-at:hover { background: rgba(14, 140, 138, 0.18); }
/* @ contacts popover — floats above the ask pill */
.na-men {
  position: absolute; bottom: calc(100% + 10px); inset-inline: 0; z-index: 4;
  max-height: 320px; display: flex; flex-direction: column; overflow: hidden;
  border-radius: 20px; background: rgba(255, 255, 255, 0.92); backdrop-filter: blur(16px);
  box-shadow: 0 18px 50px rgba(8, 40, 38, 0.2), inset 0 0 0 1px rgba(255, 255, 255, 0.9);
}
.na-men-head { display: flex; align-items: center; gap: 8px; padding: 10px 16px 6px; font-size: 12px; font-weight: 800; color: #4A5B5A; }
.na-men-q { padding: 1px 8px; border-radius: 999px; background: rgba(14, 140, 138, 0.1); color: #0A6664; font-size: 12px; }
.na-men-list { list-style: none; margin: 0; padding: 4px 6px 8px; overflow-y: auto; }
.na-men-row { display: flex; align-items: center; gap: 11px; padding: 7px 10px; border-radius: 13px; cursor: pointer; }
.na-men-row.is-active { background: rgba(14, 140, 138, 0.1); }
.na-men-ic {
  flex-shrink: 0; width: 32px; height: 32px; border-radius: 50%; display: grid; place-items: center;
  font-size: 14px; font-weight: 800; color: #0A6664; background: rgba(14, 140, 138, 0.12);
}
.na-men-ic--company { color: #2C5F6B; background: rgba(44, 95, 107, 0.12); border-radius: 10px; }
.na-men-ic--mail { color: #2F6C94; background: rgba(47, 108, 148, 0.12); border-radius: 10px; }
.na-men-txt { min-width: 0; display: flex; flex-direction: column; }
.na-men-txt strong { font-size: 14px; font-weight: 800; color: #10201F; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.na-men-txt small { display: flex; gap: 10px; font-size: 12px; color: #5A6968; white-space: nowrap; overflow: hidden; }
.na-men-mail { overflow: hidden; text-overflow: ellipsis; }
.na-men-empty { margin: 0; padding: 6px 16px 14px; font-size: 13px; color: #5A6968; }

.na-fade-enter-active, .na-fade-leave-active { transition: opacity 0.25s ease; }
.na-fade-enter-from, .na-fade-leave-to { opacity: 0; }
@media (max-width: 600px) {
  .na { border-radius: 22px; }
  .na-line-body { font-size: 15.5px; }
}
@media (prefers-reduced-motion: reduce) {
  .na-aurora i, .na-halo, .na-status i, .na-line, .na-link, .na-orb-wrap::before, .na-area, .na-fold .na-item, .na-fold .na-group, .na-fold .na-more { animation: none !important; }
  .na-fold, .na-area-chev { transition: none !important; }
}
</style>
