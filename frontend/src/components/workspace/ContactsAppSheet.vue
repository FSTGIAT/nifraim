<template>
  <!-- The walk-in customers as an iPhone Contacts app: it grows out of the app
       icon that opened it (useOriginMorph), a large title, search, alphabetical
       sections with sticky letters and a letter index, and the contact card
       sliding in from the side. Closing folds it back into the icon. -->
  <Teleport to="body">
    <Transition name="cas-fade">
      <div v-if="open" class="cas-overlay" @click.self="close">
        <div ref="cardEl" class="cas-phone" role="dialog" aria-modal="true" :aria-label="title" dir="rtl">
          <Transition :name="detail ? 'cas-push' : 'cas-pop'">
            <!-- ── the list ── -->
            <section v-if="!detail" key="list" class="cas-view">
              <header class="cas-bar">
                <button type="button" class="cas-ico" aria-label="סגור" @click="close">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
                </button>
                <button type="button" class="cas-ico cas-ico--acc" :aria-label="isCo ? 'הוספת חברה' : 'לקוח חדש'" @click="$emit('add')">
                  <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
                </button>
              </header>
              <div ref="scrollEl" class="cas-scroll" @scroll.passive="onScroll">
                <h2 class="cas-title" :class="{ 'cas-title--small': scrolled }">{{ title }}</h2>
                <label class="cas-search">
                  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="M20 20l-3.5-3.5" /></svg>
                  <input v-model="q" placeholder="חיפוש" aria-label="חיפוש" />
                </label>
                <p v-if="!items.length" class="cas-empty">
                  {{ q ? 'לא נמצא' : isCo ? 'עוד אין כתובות לחברות.' : 'עוד אין לקוחות חדשים. הוסיפו לקוח, והשיחות איתו יגיעו לסיכום.' }}
                </p>
                <button v-if="isCo && !walkins.length && !q" type="button" class="cas-seed" @click="$emit('seed')">טעינת אנשי הקשר של החברות</button>
                <div v-for="(g, gi) in groups" :key="g.letter" :ref="(el) => (secEls[g.letter] = el)" class="cas-sec">
                  <h3 class="cas-letter">{{ g.letter }}</h3>
                  <ul class="cas-rows">
                    <li v-for="(w, i) in g.items" :key="w.id" class="cas-row" :style="{ '--d': Math.min(gi * 2 + i, 14) * 35 + 'ms' }">
                      <button type="button" class="cas-row-btn" @click="detail = w">
                        <CompanyLogo v-if="isCo" :company="w.name" :size="40" />
                        <span v-else class="cas-av">{{ initials(w) }}</span>
                        <span class="cas-row-id">
                          <strong>{{ w.name }}</strong>
                          <small class="ltr-number">{{ isCo ? w.email : phoneFmt(w.phone) }}</small>
                        </span>
                        <svg class="cas-chev" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" aria-hidden="true"><path d="M15 18l-6-6 6-6" /></svg>
                      </button>
                    </li>
                  </ul>
                </div>
                <!-- companies still without an address: one tap adds it -->
                <div v-if="isCo && missingShown.length" class="cas-sec">
                  <h3 class="cas-letter">חסרה כתובת</h3>
                  <ul class="cas-rows">
                    <li v-for="m in missingShown" :key="m" class="cas-row" style="--d: 0ms">
                      <button type="button" class="cas-row-btn" @click="$emit('add', m)">
                        <CompanyLogo :company="m" :size="40" />
                        <span class="cas-row-id"><strong>{{ m }}</strong><small>הוספת כתובת</small></span>
                        <svg class="cas-plus" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
                      </button>
                    </li>
                  </ul>
                </div>
                <p v-if="items.length" class="cas-count"><span class="ltr-number">{{ items.length }}</span>
                  {{ isCo ? 'חברות · לכאן נשלחים בירורי העמלות' : 'לקוחות · שיחות איתם נאספות מהטלפון' }}</p>
              </div>
              <!-- letter index, iOS-style on the side -->
              <nav v-if="groups.length > 1" class="cas-index" aria-label="אינדקס אותיות">
                <button v-for="g in groups" :key="g.letter" type="button" @click="jump(g.letter)">{{ g.letter }}</button>
              </nav>
            </section>

            <!-- ── one contact ── -->
            <section v-else key="detail" class="cas-view cas-detail">
              <header class="cas-bar">
                <button type="button" class="cas-back" @click="detail = null">
                  <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" aria-hidden="true"><path d="M9 6l6 6-6 6" /></svg>
                  {{ isCo ? 'חברות' : 'לקוחות' }}
                </button>
                <button type="button" class="cas-link" @click="$emit('edit', detail)">עריכה</button>
              </header>
              <div class="cas-scroll">
                <div class="cas-hero">
                  <CompanyLogo v-if="isCo" :company="detail.name" :size="96" />
                  <span v-else class="cas-av cas-av--big">{{ initials(detail) }}</span>
                  <h2>{{ detail.name }}</h2>
                  <span class="cas-tag">{{ isCo ? 'כתובת לבירורי עמלות' : 'לקוח חדש' }}</span>
                </div>
                <div class="cas-quick" :class="{ 'cas-quick--one': isCo }">
                  <a v-if="!isCo" class="cas-q" :href="'tel:' + detail.phone">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L8 9.9a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z" /></svg>
                    חיוג
                  </a>
                  <a class="cas-q" :class="{ 'cas-q--off': !detail.email }" :href="detail.email ? 'mailto:' + detail.email : undefined">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="4" width="20" height="16" rx="2" /><path d="m22 6-10 7L2 6" /></svg>
                    מייל
                  </a>
                </div>
                <dl v-if="isCo" class="cas-fields">
                  <div><dt>מייל</dt><dd class="ltr-number">{{ detail.email }}</dd></div>
                  <div v-if="detail.contact_name"><dt>איש קשר</dt><dd>{{ detail.contact_name }}</dd></div>
                  <div v-if="detail.notes"><dt>הערות</dt><dd>{{ detail.notes }}</dd></div>
                </dl>
                <dl v-else class="cas-fields">
                  <div><dt>נייד</dt><dd class="ltr-number">{{ phoneFmt(detail.phone) }}</dd></div>
                  <div v-if="detail.email"><dt>מייל</dt><dd class="ltr-number">{{ detail.email }}</dd></div>
                  <div><dt>ת.ז</dt><dd class="ltr-number">{{ detail.id_number }}</dd></div>
                  <div v-if="detail.created_at"><dt>נוסף</dt><dd class="ltr-number">{{ dateFmt(detail.created_at) }}</dd></div>
                </dl>
                <p v-if="!isCo" class="cas-note">שיחות עם המספר הזה עולות לבד מהטלפון ל-Nifra Calls.</p>
                <button type="button" class="cas-del" @click="remove">{{ isCo ? 'מחיקת כתובת' : 'מחיקת לקוח' }}</button>
              </div>
            </section>
          </Transition>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useOriginMorph } from '../../composables/useOriginMorph.js'
import CompanyLogo from './CompanyLogo.vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  origin: { type: Object, default: null },
  // the rows: walk-in customers, or (kind="companies") insurer contacts mapped to { id, name, email, … }
  walkins: { type: Array, default: () => [] },
  kind: { type: String, default: 'walkins' },
  title: { type: String, default: 'לקוחות חדשים' },
  missing: { type: Array, default: () => [] }, // companies with no address (kind="companies")
})
const emit = defineEmits(['close', 'add', 'edit', 'delete', 'seed'])
const isCo = computed(() => props.kind === 'companies')
const missingShown = computed(() => { const s = q.value.trim(); return s ? props.missing.filter((m) => m.includes(s)) : props.missing })

const cardEl = ref(null)
const scrollEl = ref(null)
const q = ref('')
const detail = ref(null)
const scrolled = ref(false)
const secEls = {}
const morph = useOriginMorph()

const initials = (w) => ((w?.first_name || '').charAt(0) + (w?.last_name || '').charAt(0)) || '?'
const phoneFmt = (p) => { const d = String(p || '').replace(/\D/g, ''); return d.length === 10 ? `${d.slice(0, 3)}-${d.slice(3)}` : p }
const dateFmt = (iso) => { const d = new Date(iso); return Number.isNaN(d.getTime()) ? '' : d.toLocaleDateString('he-IL') }

const items = computed(() => {
  const s = q.value.trim()
  const list = [...props.walkins].sort((a, b) => (a.name || '').localeCompare(b.name || '', 'he'))
  return s ? list.filter((w) => `${w.name} ${w.phone || ''} ${w.email || ''} ${w.id_number || ''} ${w.contact_name || ''}`.includes(s)) : list
})
const groups = computed(() => {
  const out = []
  for (const w of items.value) {
    const letter = (w.name || '#').trim().charAt(0).toUpperCase() || '#'
    const last = out[out.length - 1]
    if (last && last.letter === letter) last.items.push(w)
    else out.push({ letter, items: [w] })
  }
  return out
})

// a contact that was edited/deleted outside stays in sync
watch(() => props.walkins, (list) => {
  if (detail.value) detail.value = list.find((w) => w.id === detail.value.id) || null
})

watch(() => props.open, async (o) => {
  if (!o) return
  q.value = ''
  detail.value = null
  scrolled.value = false
  morph.remember(props.origin)
  await nextTick()
  morph.grow(cardEl.value)
})

function onScroll() { scrolled.value = (scrollEl.value?.scrollTop || 0) > 34 }
function jump(letter) { secEls[letter]?.scrollIntoView({ behavior: 'smooth', block: 'start' }) }

async function close() {
  if (morph.hasOrigin() && cardEl.value) await morph.shrink(cardEl.value)
  emit('close')
}
function remove() {
  const w = detail.value
  if (!w) return
  emit('delete', w.id)
  detail.value = null
}
</script>

<style scoped>
.cas-overlay { position: fixed; inset: 0; z-index: 1005; display: flex; align-items: center; justify-content: center;
  padding: 20px; background: rgba(15, 20, 30, 0.42); font-family: 'Heebo', sans-serif; }
.cas-phone {
  position: relative; width: min(400px, 100%); height: min(720px, calc(100dvh - 40px)); overflow: hidden;
  background: #F2F2F7; border-radius: 38px; box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35), 0 0 0 9px #181818, 0 0 0 10px #3a3a3c;
}
.cas-view { position: absolute; inset: 0; display: flex; flex-direction: column; }
.cas-bar { flex: none; display: flex; align-items: center; justify-content: space-between; padding: 18px 18px 4px; }
.cas-ico { width: 34px; height: 34px; display: grid; place-items: center; border: none; border-radius: 50%;
  background: rgba(118, 118, 128, 0.12); color: var(--text); cursor: pointer; }
.cas-ico--acc { color: var(--tab-emails-ink); }
.cas-ico:hover { background: rgba(118, 118, 128, 0.2); }
.cas-back, .cas-link { display: inline-flex; align-items: center; gap: 2px; border: none; background: none; cursor: pointer;
  font-family: inherit; font-size: 16px; font-weight: 500; color: var(--tab-emails-ink); padding: 6px 2px; }

.cas-scroll { flex: 1; overflow-y: auto; overscroll-behavior: contain; scroll-behavior: smooth; padding: 0 18px 28px; scrollbar-width: none; }
.cas-scroll::-webkit-scrollbar { display: none; }
.cas-title { margin: 6px 0 10px; font-size: 32px; font-weight: 900; letter-spacing: -0.03em; color: var(--text);
  transform-origin: right center; transition: transform 0.3s cubic-bezier(0.32, 0.72, 0, 1), opacity 0.3s; }
.cas-title--small { transform: scale(0.94); opacity: 0.85; }
.cas-search { display: flex; align-items: center; gap: 7px; height: 38px; padding: 0 11px; margin-bottom: 14px;
  border-radius: 11px; background: rgba(118, 118, 128, 0.12); color: #8E8E93; }
.cas-search input { flex: 1; min-width: 0; border: none; outline: none; background: none; font: inherit; font-size: 16px; color: var(--text); }
.cas-empty { margin: 30px 8px; text-align: center; font-size: 14.5px; line-height: 1.6; color: #8E8E93; }

.cas-sec { scroll-margin-top: 4px; }
.cas-letter { position: sticky; top: 0; z-index: 1; margin: 0; padding: 6px 4px 4px; font-size: 13px; font-weight: 800;
  color: #8E8E93; background: #F2F2F7; }
.cas-rows { list-style: none; margin: 0 0 10px; padding: 0; background: #fff; border-radius: 12px; overflow: hidden; }
.cas-row { opacity: 0; transform: translateY(10px); animation: casIn 0.5s cubic-bezier(0.32, 0.72, 0, 1) forwards; animation-delay: var(--d); }
@keyframes casIn { to { opacity: 1; transform: none; } }
.cas-row + .cas-row .cas-row-btn { border-top: 0.5px solid #E5E5EA; }
.cas-row-btn { width: 100%; display: flex; align-items: center; gap: 12px; padding: 10px 14px; border: none; background: none;
  cursor: pointer; font-family: inherit; text-align: start; }
.cas-row-btn:hover, .cas-row-btn:focus-visible { background: #F7F7FA; outline: none; }
.cas-row-btn:active { background: #EDEDF2; }
.cas-av { width: 40px; height: 40px; flex: none; border-radius: 50%; display: grid; place-items: center;
  font-size: 15px; font-weight: 800; color: #fff; background: linear-gradient(160deg, #B5B5BD, #8E8E96); }
.cas-row-id { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.cas-row-id strong { font-size: 16px; font-weight: 600; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.cas-row-id small { align-self: flex-start; font-size: 13px; color: #8E8E93; }
.cas-chev { flex: none; color: #C7C7CC; }
.cas-plus { flex: none; color: var(--tab-emails-ink); }
.cas-quick.cas-quick--one { grid-template-columns: 1fr; }
.cas-seed { width: 100%; margin-bottom: 14px; padding: 12px; border: none; border-radius: 12px; cursor: pointer;
  background: var(--tab-emails-ink); color: #fff; font-family: inherit; font-size: 15px; font-weight: 700; }
.cas-count { margin: 14px 0 0; text-align: center; font-size: 13px; color: #8E8E93; }

.cas-index { position: absolute; inset-inline-end: 3px; top: 50%; transform: translateY(-50%); display: flex; flex-direction: column; }
.cas-index button { border: none; background: none; padding: 1px 5px; font-family: inherit; font-size: 11px; font-weight: 700;
  color: var(--tab-emails-ink); cursor: pointer; line-height: 1.25; }

/* contact card */
.cas-hero { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 10px 0 16px; }
.cas-av--big { width: 96px; height: 96px; font-size: 36px; }
.cas-hero h2 { margin: 6px 0 0; font-size: 26px; font-weight: 800; letter-spacing: -0.02em; color: var(--text); text-align: center; }
.cas-tag { padding: 2px 10px; border-radius: 99px; font-size: 12px; font-weight: 700; color: var(--tab-emails-ink); background: var(--tab-emails-wash); }
.cas-quick { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; margin-bottom: 14px; }
.cas-q { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 10px 0 8px; border-radius: 12px;
  background: #fff; color: var(--tab-emails-ink); font-size: 12.5px; font-weight: 600; text-decoration: none; }
.cas-q:hover { background: #FBF6F8; }
.cas-q--off { color: #C7C7CC; pointer-events: none; }
.cas-fields { margin: 0 0 12px; padding: 0; background: #fff; border-radius: 12px; overflow: hidden; }
.cas-fields > div { padding: 10px 14px; }
.cas-fields > div + div { border-top: 0.5px solid #E5E5EA; }
.cas-fields dt { font-size: 13px; color: var(--text); }
.cas-fields dd { margin: 2px 0 0; font-size: 16px; color: var(--tab-emails-ink); text-align: right; }
.cas-note { margin: 0 4px 14px; font-size: 12.5px; line-height: 1.5; color: #8E8E93; }
.cas-del { width: 100%; padding: 12px; border: none; border-radius: 12px; background: #fff; color: var(--red, #D93025);
  font-family: inherit; font-size: 16px; cursor: pointer; }
.cas-del:hover { background: #FFF5F5; }

/* push / pop like iOS navigation (RTL: the new screen comes from the left) */
.cas-push-enter-active, .cas-push-leave-active, .cas-pop-enter-active, .cas-pop-leave-active {
  transition: transform 0.42s cubic-bezier(0.32, 0.72, 0, 1), opacity 0.42s; }
.cas-push-enter-from { transform: translateX(-100%); }
.cas-push-leave-to { transform: translateX(30%); opacity: 0; }
.cas-pop-enter-from { transform: translateX(30%); opacity: 0; }
.cas-pop-leave-to { transform: translateX(-100%); }
.cas-fade-enter-active, .cas-fade-leave-active { transition: opacity 0.25s; }
.cas-fade-enter-from, .cas-fade-leave-to { opacity: 0; }

@media (max-width: 460px) { .cas-overlay { padding: 0; } .cas-phone { width: 100%; height: 100dvh; border-radius: 0; box-shadow: none; } }
@media (prefers-reduced-motion: reduce) {
  .cas-row { animation: none; opacity: 1; transform: none; }
  .cas-push-enter-active, .cas-push-leave-active, .cas-pop-enter-active, .cas-pop-leave-active { transition: none; }
}
</style>
