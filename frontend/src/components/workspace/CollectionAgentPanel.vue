<template>
  <!-- The collection agent's panel: a hand-drawn diagram (the agent in the
       middle, one drawn branch per insurer with unpaid customers) and, for the
       picked insurer, ONE suggested step + the draft to approve. Straight to
       the point — not a chat. Opens out of the icon (useOriginMorph). -->
  <Teleport to="body">
    <Transition name="cap-fade">
      <div v-if="open" class="cap-overlay" @click.self="close">
        <section ref="cardEl" class="cap" role="dialog" aria-modal="true" aria-label="סוכן גבייה">
          <header class="cap-head">
            <div class="cap-titles">
              <span class="cap-kicker">סוכן גבייה<template v-if="b?.period_label"> · {{ b.period_label }}</template></span>
              <h3 class="cap-title">
                <template v-if="b?.open_count">{{ b.open_count }} חברות לא שילמו <span class="cap-acc ltr-number">{{ money(b.expected) }}</span></template>
                <template v-else>הכל מטופל</template>
              </h3>
            </div>
            <button class="cap-x" type="button" aria-label="סגור" @click="close">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
            </button>
          </header>

          <div class="cap-body">
            <!-- the drawing -->
            <div class="cap-diagram">
              <!-- viewBox matches the box's 1.2 aspect, so strokes scale uniformly -->
              <svg class="cap-lines" viewBox="0 0 120 100" preserveAspectRatio="none" aria-hidden="true">
                <path v-for="(n, i) in nodes" :key="n.c.id"
                      :d="curve(n)" pathLength="1"
                      class="cap-line" :class="'cap-line--' + n.c.status"
                      :style="{ '--i': i }" />
              </svg>
              <div class="cap-me" :style="{ left: '50%', top: '52%' }">
                <Avatar :name="auth.user?.full_name || ''" :username="auth.user?.username || ''" :avatar-seed="seedFor(auth.user)" :size="58" />
                <span>אתם</span>
              </div>
              <button
                v-for="(n, i) in nodes" :key="n.c.id" type="button"
                class="cap-node" :class="['cap-node--' + n.c.status, { on: sel?.id === n.c.id }]"
                :style="{ left: n.x + '%', top: n.y + '%', '--i': i }"
                @click="selId = n.c.id"
              >
                <span class="cap-node-dot">{{ initials(n.c.company) }}</span>
                <span class="cap-node-name">{{ n.c.company }}</span>
                <span class="cap-node-meta"><b class="ltr-number">{{ n.c.customers }}</b> לקוחות · <b class="ltr-number">{{ money(n.c.expected) }}</b></span>
                <span class="cap-node-chip">{{ STATUS[n.c.status] }}</span>
              </button>
            </div>

            <!-- the picked insurer: one step, then the draft -->
            <aside v-if="sel" class="cap-card">
              <div class="cap-step" :class="'cap-step--' + sel.next.kind">
                <span class="cap-step-ic" aria-hidden="true">
                  <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                    <path v-if="sel.next.kind === 'done'" d="M20 6 9 17l-5-5" />
                    <template v-else><path d="M5 12h14" /><path d="m12 5 7 7-7 7" transform="scale(-1,1) translate(-24,0)" /></template>
                  </svg>
                </span>
                <strong>{{ sel.next.text }}</strong>
              </div>

              <label v-if="sel.status === 'draft'" class="cap-field">
                <span>מייל של איש קשר ב{{ sel.company }}</span>
                <input v-model.trim="emailDraft" type="email" dir="ltr" placeholder="name@insurer.co.il" @blur="saveEmail" @keydown.enter="saveEmail" />
              </label>
              <p v-else-if="sel.to_email" class="cap-to">אל: <span dir="ltr">{{ sel.to_email }}</span></p>

              <details class="cap-draft" :open="sel.status === 'draft'">
                <summary>{{ sel.status === 'draft' ? 'הטיוטה' : 'הפנייה שנשלחה' }} · <span class="ltr-number">{{ sel.items.length }}</span> פוליסות</summary>
                <p class="cap-subject">{{ sel.draft_subject }}</p>
                <textarea v-if="sel.status === 'draft'" v-model="bodyDraft" class="cap-bodytext" rows="9" @blur="saveBody"></textarea>
                <pre v-else class="cap-bodytext cap-bodytext--ro">{{ sel.draft_body }}</pre>
              </details>

              <p v-if="store.error" class="cap-err">{{ store.error }}</p>

              <div class="cap-actions">
                <button v-if="sel.status === 'draft'" type="button" class="cap-btn cap-btn--go"
                        :disabled="!sel.to_email || store.busyId === sel.id" @click="store.send(sel.id)">
                  {{ store.busyId === sel.id ? 'שולח…' : 'אישור ושליחה' }}
                </button>
                <button v-if="sel.status === 'sent' && sel.next.kind === 'remind'" type="button" class="cap-btn cap-btn--go"
                        :disabled="store.busyId === sel.id" @click="store.remind(sel.id)">
                  {{ store.busyId === sel.id ? 'שולח…' : 'שליחת תזכורת' }}
                </button>
                <button v-if="sel.status === 'sent' || sel.status === 'replied'" type="button" class="cap-btn"
                        :disabled="store.busyId === sel.id" @click="store.resolve(sel.id)">סימון כטופל</button>
              </div>
              <p v-if="!b?.mailbox?.can_send && sel.status === 'draft'" class="cap-note">
                השליחה יוצאת מהמייל שלכם — חברו את Nifraim Mail Agent (Gmail) בהגדרות.
              </p>
            </aside>
          </div>
        </section>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import Avatar from '../Avatar.vue'
import { useAuthStore } from '../../stores/auth.js'
import { useCollectionAgentStore } from '../../stores/collectionAgent.js'
import { seedFor } from '../../utils/avatarSeed.js'
import { useOriginMorph } from '../../composables/useOriginMorph.js'

const props = defineProps({ open: { type: Boolean, default: false }, originEl: { type: Object, default: null } })
const emit = defineEmits(['update:open'])
const auth = useAuthStore()
const store = useCollectionAgentStore()
const b = computed(() => store.brief)

const STATUS = { draft: 'טיוטה', sent: 'נשלח', replied: 'נענה', resolved: 'טופל' }

// One node per insurer, spread around the agent (starting at the top).
const nodes = computed(() => {
  const cs = store.cases
  const n = cs.length || 1
  return cs.map((c, i) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / n + (n === 2 ? Math.PI / 2 : 0)
    return { c, x: 50 + Math.cos(a) * 36, y: 52 + Math.sin(a) * 34 }
  })
})
// a hand-drawn curve from the agent to the node (bowed sideways)
function curve(n) {
  // node % → the 120×100 drawing space
  const x0 = 60, y0 = 52, x1 = n.x * 1.2, y1 = n.y
  const mx = (x0 + x1) / 2, my = (y0 + y1) / 2, dx = x1 - x0, dy = y1 - y0
  return `M${x0} ${y0} Q ${mx - dy * 0.18} ${my + dx * 0.18} ${x1} ${y1}`
}

const selId = ref(null)
const sel = computed(() => store.cases.find((c) => c.id === selId.value) || null)
watch(() => store.cases, (cs) => {
  if (!cs.length) { selId.value = null; return }
  if (!sel.value) {
    // start on the case that needs the agent most
    const order = { remind: 0, approve: 1, contact: 2, read: 3, wait: 4, done: 5 }
    selId.value = [...cs].sort((a, b) => (order[a.next.kind] ?? 9) - (order[b.next.kind] ?? 9))[0].id
  }
}, { immediate: true })

const emailDraft = ref('')
const bodyDraft = ref('')
watch(sel, (c) => { emailDraft.value = c?.to_email || ''; bodyDraft.value = c?.draft_body || '' }, { immediate: true })
function saveEmail() {
  if (!sel.value || (emailDraft.value || '') === (sel.value.to_email || '')) return
  store.edit(sel.value.id, { to_email: emailDraft.value })
}
function saveBody() {
  if (!sel.value || bodyDraft.value === sel.value.draft_body) return
  store.edit(sel.value.id, { body: bodyDraft.value })
}

function money(v) {
  const n = Math.round(Number(v) || 0)
  if (n >= 1000) return `₪${(n / 1000).toFixed(n >= 10000 ? 0 : 1)}K`
  return `₪${n.toLocaleString()}`
}
function initials(name) {
  return (name || '').replace(/[״"׳']/g, '').trim().slice(0, 2)
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
.cap-overlay {
  position: fixed; inset: 0; z-index: 1010; background: rgba(24, 24, 24, 0.32);
  display: grid; place-items: center; padding: 16px;
}
.cap {
  width: min(1100px, 100%); max-height: min(760px, calc(100vh - 32px)); overflow: auto;
  display: flex; flex-direction: column; gap: 6px; padding: 20px 22px 22px;
  background: #fff; border-radius: 24px; border: 1px solid var(--border-subtle);
  box-shadow: 0 30px 80px rgba(24, 24, 24, 0.22);
  font-family: 'Heebo', sans-serif;
}
.cap-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; }
.cap-titles { display: flex; flex-direction: column; gap: 4px; }
.cap-kicker {
  align-self: flex-start; padding: 4px 11px; border-radius: 999px; font-size: 12px; font-weight: 800;
  color: var(--tab-comparison, #2E844A); background: color-mix(in srgb, var(--tab-comparison, #2E844A) 10%, #fff);
}
.cap-title { margin: 0; font-size: clamp(22px, 2.4vw, 30px); font-weight: 900; letter-spacing: -0.03em; color: var(--text-primary, #181818); }
.cap-acc { color: #E04B48; }
.cap-x {
  width: 32px; height: 32px; border-radius: 10px; border: none; background: transparent; cursor: pointer;
  display: grid; place-items: center; color: var(--text-secondary, #706E6B);
}
.cap-x:hover { background: var(--bg, #F3F3F3); color: var(--text-primary, #181818); }

.cap-body { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(300px, 1fr); gap: 18px; align-items: start; }

/* ── the drawing ── */
.cap-diagram {
  position: relative; aspect-ratio: 1.2; min-height: 380px; border-radius: 20px;
  background:
    radial-gradient(circle at 50% 52%, color-mix(in srgb, var(--tab-comparison, #2E844A) 7%, transparent) 0, transparent 55%),
    #FCFCFB;
  border: 1px dashed color-mix(in srgb, var(--tab-comparison, #2E844A) 25%, transparent);
}
.cap-lines { position: absolute; inset: 0; width: 100%; height: 100%; }
.cap-line {
  fill: none; stroke: #181818; stroke-width: 0.45; stroke-linecap: round;
  stroke-dasharray: 1; stroke-dashoffset: 1;
  animation: capDraw 0.9s cubic-bezier(0.22, 1, 0.36, 1) forwards; animation-delay: calc(0.15s + var(--i) * 0.12s);
}
@keyframes capDraw { to { stroke-dashoffset: 0; } }
.cap-line--draft { stroke: #A9A6A2; }
.cap-line--sent { stroke: var(--tab-comparison, #2E844A); }
.cap-line--replied { stroke: var(--tab-comparison, #2E844A); stroke-width: 0.6; }
.cap-line--resolved { stroke: #D9D7D3; }

.cap-me {
  position: absolute; transform: translate(-50%, -50%); display: flex; flex-direction: column; align-items: center; gap: 4px;
  font-size: 12px; font-weight: 800; color: var(--text-primary, #181818);
}
.cap-node {
  position: absolute; transform: translate(-50%, -50%); width: 150px;
  display: flex; flex-direction: column; align-items: center; gap: 3px;
  padding: 0; border: none; background: none; cursor: pointer; font-family: inherit;
  opacity: 0; animation: capPop 0.45s cubic-bezier(0.34, 1.56, 0.64, 1) forwards; animation-delay: calc(0.55s + var(--i) * 0.12s);
}
@keyframes capPop { from { opacity: 0; transform: translate(-50%, -50%) scale(0.6); } to { opacity: 1; transform: translate(-50%, -50%) scale(1); } }
.cap-node-dot {
  width: 56px; height: 56px; border-radius: 50%; display: grid; place-items: center;
  font-size: 17px; font-weight: 900; color: var(--text-primary, #181818);
  background: #fff; border: 2.4px solid #A9A6A2; box-shadow: 0 6px 16px rgba(24, 24, 24, 0.08);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.cap-node:hover .cap-node-dot { transform: scale(1.06); }
.cap-node.on .cap-node-dot { box-shadow: 0 0 0 5px color-mix(in srgb, var(--tab-comparison, #2E844A) 18%, transparent), 0 8px 20px rgba(24, 24, 24, 0.12); }
.cap-node--sent .cap-node-dot, .cap-node--replied .cap-node-dot { border-color: var(--tab-comparison, #2E844A); }
.cap-node--replied .cap-node-dot { background: color-mix(in srgb, var(--tab-comparison, #2E844A) 10%, #fff); }
.cap-node--resolved { filter: grayscale(1); opacity: 0.55; }
.cap-node-name { font-size: 14px; font-weight: 900; color: var(--text-primary, #181818); }
.cap-node-name, .cap-node-meta { background: #FCFCFB; padding: 0 5px; border-radius: 6px; }
.cap-node-meta { font-size: 12px; color: var(--text-secondary, #5C5A58); white-space: nowrap; }
.cap-node-meta b { font-weight: 800; color: var(--text-primary, #181818); }
.cap-node-chip {
  font-size: 11px; font-weight: 800; padding: 2px 9px; border-radius: 999px;
  background: #F1F0EE; color: #5C5A58;
}
.cap-node--sent .cap-node-chip { background: color-mix(in srgb, var(--tab-comparison, #2E844A) 12%, #fff); color: var(--tab-comparison, #2E844A); }
.cap-node--replied .cap-node-chip { background: var(--tab-comparison, #2E844A); color: #fff; }

/* ── the card ── */
.cap-card {
  display: flex; flex-direction: column; gap: 12px; padding: 16px;
  border-radius: 18px; background: #fff; border: 1px solid var(--border-subtle); box-shadow: var(--shadow-sm);
}
.cap-step {
  display: flex; align-items: center; gap: 10px; padding: 12px 14px; border-radius: 14px;
  background: #F6F5F3; font-size: 15px; color: var(--text-primary, #181818);
}
.cap-step-ic { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; background: #181818; color: #fff; flex-shrink: 0; }
.cap-step--remind, .cap-step--contact { background: #FBF4DC; }
.cap-step--remind .cap-step-ic, .cap-step--contact .cap-step-ic { background: #8A6300; }
.cap-step--read { background: color-mix(in srgb, var(--tab-comparison, #2E844A) 10%, #fff); }
.cap-step--read .cap-step-ic, .cap-step--done .cap-step-ic { background: var(--tab-comparison, #2E844A); }
.cap-field { display: flex; flex-direction: column; gap: 5px; font-size: 12.5px; font-weight: 700; color: var(--text-secondary, #5C5A58); }
.cap-field input {
  height: 40px; padding: 0 12px; border-radius: 10px; border: 1px solid var(--border-subtle);
  font-family: inherit; font-size: 14px; outline: none;
}
.cap-field input:focus { border-color: var(--tab-comparison, #2E844A); box-shadow: 0 0 0 3px color-mix(in srgb, var(--tab-comparison, #2E844A) 14%, transparent); }
.cap-to { margin: 0; font-size: 13px; color: var(--text-secondary, #5C5A58); }
.cap-draft summary { cursor: pointer; font-size: 13px; font-weight: 800; color: var(--text-primary, #181818); }
.cap-subject { margin: 8px 0 6px; font-size: 13px; font-weight: 700; }
.cap-bodytext {
  width: 100%; resize: vertical; padding: 10px 12px; border-radius: 12px; border: 1px solid var(--border-subtle);
  font-family: inherit; font-size: 13px; line-height: 1.6; background: #FCFCFB; outline: none; white-space: pre-wrap;
}
.cap-bodytext--ro { max-height: 220px; overflow: auto; margin: 0; }
.cap-actions { display: flex; flex-wrap: wrap; gap: 8px; }
.cap-btn {
  height: 40px; padding: 0 16px; border-radius: 12px; cursor: pointer; font-family: inherit; font-size: 14px; font-weight: 800;
  background: #fff; color: var(--text-primary, #181818); border: 1px solid var(--border-subtle);
}
.cap-btn--go { background: var(--tab-comparison, #2E844A); color: #fff; border-color: transparent; box-shadow: 0 6px 16px color-mix(in srgb, var(--tab-comparison, #2E844A) 30%, transparent); }
.cap-btn:disabled { opacity: 0.45; cursor: default; box-shadow: none; }
.cap-err { margin: 0; font-size: 13px; font-weight: 700; color: #C23934; }
.cap-note { margin: 0; font-size: 12.5px; color: #8A6300; }

.cap-fade-enter-active, .cap-fade-leave-active { transition: opacity 0.2s ease; }
.cap-fade-enter-from, .cap-fade-leave-to { opacity: 0; }
@media (max-width: 860px) {
  .cap-body { grid-template-columns: 1fr; }
  .cap-node { width: 120px; }
}
@media (prefers-reduced-motion: reduce) {
  .cap-line { animation: none; stroke-dashoffset: 0; }
  .cap-node { animation: none; opacity: 1; }
}
</style>
