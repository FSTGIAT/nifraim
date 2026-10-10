<template>
  <!-- Nifra Market — the fund rankings as a place: your customers vs the market, the risk ladder, what moved
       this month, company duels, and a market-scoped ask box. Grows out of its circle and folds back into it. -->
  <Teleport to="body">
    <Transition name="nms" @enter="onEnter">
      <div v-if="open" class="nms-overlay" @click.self="close">
        <div ref="cardEl" class="nms" role="dialog" aria-label="Nifra Market">
          <header class="nms-head">
            <div class="nms-title">
              <h2 dir="ltr">Nifra <b>Market</b></h2>
              <p>הלקוחות שלך מול כל השוק — לפי רמת הסיכון האמיתית, מנתוני גמל-נט ופנסיה-נט<template v-if="store.overview && store.overview.data_month"> · {{ store.overview.data_month }}</template></p>
            </div>
            <div class="nms-pulse" aria-hidden="true">
              <RemotionLoopIsland component="MarketPulse" frames-key="MARKET_PULSE_FRAMES" :width="560" :height="180"
                                  :input-props="{ color: '#7A7F2A' }" />
            </div>
            <button type="button" class="nms-x" aria-label="סגירה" @click="close">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18" /></svg>
            </button>
          </header>

          <nav class="nms-nav" role="tablist">
            <span class="nms-pill" :style="pillStyle" aria-hidden="true"></span>
            <button v-for="(v, i) in VIEWS" :key="v.id" :ref="(el) => (navEls[i] = el)" type="button" role="tab"
                    :aria-selected="view === v.id" :class="{ on: view === v.id }" @click="view = v.id">{{ v.label }}</button>
          </nav>

          <main class="nms-body">
            <Transition name="nms-view" mode="out-in">
              <MarketHero v-if="view === 'book'" key="book" @open-customer="openCustomer" />
              <MarketLadder v-else-if="view === 'ladder'" key="ladder" @customers="openTrackCustomers" />
              <MarketMoves v-else-if="view === 'moves'" key="moves" @open-customer="openCustomer" />
              <CompanyDuel v-else key="duel" />
            </Transition>

            <section v-if="store.thread.length" class="nms-thread">
              <div v-for="(m, i) in store.thread" :key="i" class="nms-msg" :class="'nms-msg--' + m.role">
                <p>{{ m.text || (store.busy && i === store.thread.length - 1 ? (store.askStatus || 'חושב…') : '') }}</p>
                <InlineVizs v-if="m.vizs && m.vizs.length" :vizs="m.vizs" />
              </div>
            </section>
          </main>

          <form class="nms-ask" @submit.prevent="ask">
            <input v-model="q" type="text" :disabled="store.busy" placeholder="שאלו על השוק: מה הדירוג של מור פנסיה לבני 50? מי מוביל בגמל ברמת סיכון בינונית?" />
            <button type="submit" :disabled="store.busy || !q.trim()" aria-label="שליחה">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>
            </button>
          </form>
        </div>
      </div>
    </Transition>

    <CustomerMarketDrill :customer-id="drill.id" :customer-name="drill.name" :origin="drill.origin" @close="drill.id = null" />
    <DataModal :open="!!trackList" :origin="trackOrigin" :title="trackList ? trackList.fund : ''" :badge="trackList ? trackList.customers.length : null"
               subtitle="הלקוחות שלך במסלול הזה" accent="var(--tab-market)" size="sm" :layer="1035" @close="trackList = null">
      <ul v-if="trackList" class="nms-tl">
        <li v-for="c in trackList.customers" :key="c.id_number">
          <button type="button" @click="openCustomer(c, $event.currentTarget)">
            <span>{{ c.name }}</span>
            <span v-if="c.accumulation >= 0.5" class="ltr-number">₪{{ Math.round(c.accumulation).toLocaleString('he-IL') }}</span>
          </button>
        </li>
      </ul>
    </DataModal>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useOriginMorph } from '../../composables/useOriginMorph.js'
import { useMarketStore } from '../../stores/market.js'
import RemotionLoopIsland from '../workspace/RemotionLoopIsland.vue'
import DataModal from '../workspace/DataModal.vue'
import InlineVizs from '../ai/InlineVizs.vue'
import MarketHero from './MarketHero.vue'
import MarketLadder from './MarketLadder.vue'
import MarketMoves from './MarketMoves.vue'
import CompanyDuel from './CompanyDuel.vue'
import CustomerMarketDrill from './CustomerMarketDrill.vue'

const props = defineProps({ open: { type: Boolean, default: false }, originEl: { type: null, default: null } })
const emit = defineEmits(['update:open'])
const store = useMarketStore()

const VIEWS = [
  { id: 'book', label: 'הלקוחות שלך' },
  { id: 'ladder', label: 'סולם הסיכון' },
  { id: 'moves', label: 'מה זז החודש' },
  { id: 'duel', label: 'דו-קרב חברות' },
]
const view = ref('book')
const navEls = []
const pill = ref({ left: 0, top: 0, width: 0, height: 0 })
const pillStyle = computed(() => ({ transform: `translate(${pill.value.left}px, ${pill.value.top}px)`,
  width: pill.value.width + 'px', height: pill.value.height + 'px' }))
function placePill() {   // layout offsets (not rects) — right during the grow's transform and when the tabs wrap
  const i = VIEWS.findIndex((v) => v.id === view.value)
  const el = navEls[i]
  if (el) pill.value = { left: el.offsetLeft, top: el.offsetTop, width: el.offsetWidth, height: el.offsetHeight }
}
watch(view, () => nextTick(placePill))
onMounted(() => window.addEventListener('resize', placePill))
onBeforeUnmount(() => { window.removeEventListener('resize', placePill); document.body.classList.remove('mam-open') })
// the messenger pill hides under every window (RailWindow does the same) — it covered the ask box on phones
watch(() => props.open, (v) => document.body.classList.toggle('mam-open', !!v))

// iPhone-style: grow out of the circle in the Transition's enter hook (a tick later draws it full size first)
const morph = useOriginMorph()
const cardEl = ref(null)
function onEnter() {
  morph.remember(props.originEl)
  morph.grow(cardEl.value)
  nextTick(placePill)
  setTimeout(placePill, 900)   // after the grow settles
  store.loadOverview()
}
async function close() {
  if (morph.hasOrigin()) await morph.shrink(cardEl.value)
  emit('update:open', false)
}

const drill = reactive({ id: null, name: '', origin: null })
function openCustomer(c, el) {
  drill.origin = el || null
  drill.name = c.name || ''
  drill.id = String(c.id_number)
}
const trackList = ref(null)
const trackOrigin = ref(null)
function openTrackCustomers(t, el) { trackOrigin.value = el; trackList.value = t }

const q = ref('')
async function ask() {
  const text = q.value
  q.value = ''
  await store.ask(text)
}
</script>

<style scoped>
.nms-overlay {
  position: fixed; inset: 0; z-index: 1010; display: grid; place-items: center; padding: 16px;
  background: rgba(24, 26, 10, 0.36); backdrop-filter: blur(6px);
}
.nms {
  position: relative; width: min(1080px, 100%); height: min(860px, calc(100vh - 32px));
  display: flex; flex-direction: column; overflow: hidden; border-radius: 28px;
  /* its own light surface — a window, not the page: --app-canvas is the agent's chosen page colour and can be dark */
  background: #F4F4EE; box-shadow: 0 40px 100px rgba(30, 32, 8, 0.32);
  font-family: 'Heebo', sans-serif; color: var(--text-primary, #181818);
}
.nms-head { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 18px 24px 6px; }
.nms-title h2 { margin: 0; font-size: 26px; font-weight: 900; letter-spacing: -0.02em; text-align: right; }
.nms-title h2 b { color: var(--tab-market-ink); }
.nms-title p { margin: 2px 0 0; font-size: 13px; color: var(--text-secondary, #5C5C5C); }
.nms-pulse { width: 260px; flex-shrink: 0; margin-inline-start: auto; opacity: 0.95; }
.nms-pulse :deep(.rli-mount) { direction: ltr; }
.nms-x {
  width: 32px; height: 32px; flex-shrink: 0; border-radius: 10px; border: none; cursor: pointer;
  display: grid; place-items: center; background: rgba(255, 255, 255, 0.7); color: var(--text-secondary, #5C5C5C);
}
.nms-x:hover { background: #fff; color: var(--text-primary, #181818); }
.nms-nav { position: relative; display: flex; gap: 4px; margin: 6px 24px 0; padding: 4px; border-radius: 14px; background: rgba(255, 255, 255, 0.65); align-self: flex-start; flex-wrap: wrap; }
.nms-nav button { position: relative; z-index: 1; border: none; background: none; padding: 8px 16px; border-radius: 10px; font: inherit; font-size: 14px; font-weight: 700; cursor: pointer; color: var(--text-secondary, #5C5C5C); transition: color 0.4s; }
.nms-nav button.on { color: #fff; }
.nms-pill { position: absolute; top: 0; left: 0; border-radius: 10px; background: var(--tab-market-ink); transition: transform 0.75s cubic-bezier(0.2, 0.8, 0.2, 1), width 0.75s cubic-bezier(0.2, 0.8, 0.2, 1), height 0.3s; }
.nms-body { flex: 1; overflow-y: auto; padding: 14px 24px 16px; display: flex; flex-direction: column; gap: 14px; }
.nms-thread { display: flex; flex-direction: column; gap: 8px; padding-top: 6px; border-top: 1px solid rgba(0, 0, 0, 0.06); }
.nms-msg p { margin: 0; white-space: pre-wrap; font-size: 14px; line-height: 1.55; }
.nms-msg--user { align-self: flex-start; max-width: 80%; padding: 8px 14px; border-radius: 14px; background: var(--tab-market-ink); color: #fff; }
.nms-msg--agent { align-self: stretch; padding: 12px 16px; border-radius: 14px; background: #fff; }
.nms-ask { display: flex; gap: 8px; padding: 12px 24px 18px; }
.nms-ask input { flex: 1; min-width: 0; padding: 12px 16px; border-radius: 14px; border: 1px solid var(--border-subtle, #E5E5E5); background: #fff; font: inherit; font-size: 14px; }
.nms-ask input:focus { outline: 2px solid var(--tab-market); outline-offset: 1px; }
.nms-ask button { width: 46px; border-radius: 14px; border: none; cursor: pointer; background: var(--tab-market-ink); color: #fff; display: grid; place-items: center; box-shadow: 0 6px 16px rgba(94, 99, 32, 0.25); }
.nms-ask button:disabled { opacity: 0.45; cursor: default; box-shadow: none; }
.nms-tl { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 6px; }
.nms-tl button { width: 100%; display: flex; justify-content: space-between; gap: 10px; padding: 9px 12px; border: 1px solid var(--border-subtle, #E5E5E5); border-radius: 10px; background: #fff; font: inherit; cursor: pointer; text-align: start; }
.nms-tl button:hover { border-color: var(--tab-market); }
.nms-enter-active, .nms-leave-active { transition: opacity 0.3s ease; }
.nms-enter-from, .nms-leave-to { opacity: 0; }
.nms-view-enter-active { transition: opacity 0.5s ease 0.1s, transform 0.85s cubic-bezier(0.2, 0.8, 0.2, 1) 0.1s; }
.nms-view-leave-active { transition: opacity 0.2s ease; }
.nms-view-enter-from { opacity: 0; transform: translateX(-24px); }
.nms-view-leave-to { opacity: 0; }
@media (max-width: 720px) {
  .nms { border-radius: 20px; height: calc(100vh - 24px); }
  .nms-pulse { display: none; }
  .nms-head, .nms-body, .nms-ask { padding-inline: 14px; }
  .nms-nav { margin-inline: 14px; }
  .nms-nav button { padding: 7px 10px; font-size: 13px; }
}
@media (prefers-reduced-motion: reduce) { .nms-pill, .nms-view-enter-active { transition: none; } }
</style>
