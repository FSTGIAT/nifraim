<template>
  <div class="portal-tab-root">
    <!-- Toolbar (hero: title + actions on the inline-start, animation on the inline-end) -->
    <div class="toolbar">
      <div class="toolbar-main">
      <div class="toolbar-title">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/>
          <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/>
        </svg>
        <div>
          <h2 class="pl-wordmark"><span dir="ltr">Nifraim</span> <span class="pl-wordmark-acc">פורטל לקוחות</span></h2>
          <p>נהל את הקישורים המשותפים לכל הלקוחות שלך</p>
        </div>
      </div>

      <div class="toolbar-actions">
        <div class="search-wrap">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            type="text"
            :value="portalStore.searchQuery"
            @input="e => portalStore.setSearch(e.target.value)"
            placeholder="חיפוש לפי שם, ת.ז. או אימייל..."
          />
          <button v-if="portalStore.searchQuery" class="search-clear" @click="portalStore.setSearch('')" title="נקה">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"/>
              <line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <button class="btn-generate" @click="showGenerateModal = true">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          צור קישור חדש
        </button>
      </div>
      </div>
      <TabHeroLoop scene="portal" flow="ltr" class="toolbar-art" />
    </div>

    <!-- Status filter pills -->
    <div v-if="portalStore.links.length" class="filter-pills">
      <button
        v-for="opt in filterOptions"
        :key="opt.id"
        class="pill"
        :class="{ active: portalStore.statusFilter === opt.id }"
        @click="portalStore.setStatusFilter(opt.id)"
      >
        {{ opt.label }}
        <span class="pill-count ltr-number">{{ portalStore.statusCounts[opt.id] }}</span>
      </button>
    </div>

    <!-- Table / States -->
    <div class="table-wrap">
      <!-- Skeleton loading -->
      <div v-if="portalStore.loading && !portalStore.links.length" class="skeleton">
        <div v-for="i in 5" :key="i" class="skeleton-row">
          <div class="sk-cell sk-name"></div>
          <div class="sk-cell sk-status"></div>
          <div class="sk-cell sk-date"></div>
          <div class="sk-cell sk-date"></div>
          <div class="sk-cell sk-actions"></div>
        </div>
      </div>

      <!-- No links yet: show the customer's side of the portal — what the
           link actually gives them. The action is the hero's "צור קישור חדש". -->
      <section v-else-if="!portalStore.links.length" class="pl-show">
        <!-- The surreal Kling picture (agent laptop ↔ customer phone, joined by a
             stream of light) as the section's backdrop, dissolving into the card. -->
        <div v-if="plShowArt.still" class="pl-show-photo" aria-hidden="true">
          <video v-if="plShowArt.video && !plReduced" :src="plShowArt.video" :poster="plShowArt.still"
                 autoplay muted loop playsinline preload="auto" disablepictureinpicture></video>
          <img v-else :src="plShowArt.still" alt="" />
        </div>
        <div class="pl-show-copy">
          <h3 class="pl-show-title">מה הלקוח שלכם<br><span>רואה בפורטל</span></h3>

          <!-- Slides: one feature at a time, each with its own Remotion scene;
               story bars below. Hover pauses, a bar jumps. Reduced motion → a
               plain numbered list. -->
          <div v-if="!plReduced" class="pl-slider" aria-live="polite"
               @mouseenter="plPaused = true" @mouseleave="plPaused = false">
            <div ref="plSceneEl" class="pl-scene" aria-hidden="true"></div>
            <div class="pl-slide-track">
              <Transition name="pl-slide" mode="out-in">
                <div :key="plStep" class="pl-slide">
                  <span class="pl-feat-n ltr-number">{{ String(plStep + 1).padStart(2, '0') }}</span>
                  <div><strong>{{ PL_FEATURES[plStep].title }}</strong><span>{{ PL_FEATURES[plStep].text }}</span></div>
                </div>
              </Transition>
            </div>
            <div class="pl-bars">
              <button v-for="(ft, n) in PL_FEATURES" :key="n" type="button" class="pl-bar"
                      :class="{ 'pl-bar--done': n < plStep, 'pl-bar--on': n === plStep, 'pl-bar--paused': plPaused }"
                      :aria-label="ft.title" :aria-current="n === plStep ? 'step' : undefined" @click="plGo(n)">
                <span :key="n === plStep ? plCycle : 'x'" class="pl-bar-fill"></span>
              </button>
            </div>
          </div>
          <ol v-else class="pl-feats">
            <li v-for="(ft, n) in PL_FEATURES" :key="n">
              <span class="pl-feat-n ltr-number">{{ String(n + 1).padStart(2, '0') }}</span>
              <div><strong>{{ ft.title }}</strong><span>{{ ft.text }}</span></div>
            </li>
          </ol>
        </div>
      </section>

      <!-- Empty: filter/search no matches -->
      <div v-else-if="!portalStore.sortedLinks.length" class="empty-state compact">
        <div class="empty-icon small">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"/>
            <line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
        </div>
        <h3 v-if="portalStore.searchQuery">לא נמצאו תוצאות עבור "{{ portalStore.searchQuery }}"</h3>
        <h3 v-else>אין קישורים ב-{{ filterLabel(portalStore.statusFilter) }}</h3>
        <p>נסו לשנות את החיפוש או את מסנן הסטטוס</p>
        <button class="btn-text" @click="resetFilters">נקה חיפוש וסינון</button>
      </div>

      <!-- Table -->
      <table v-else class="links-table">
        <thead>
          <tr>
            <th class="sortable" @click="portalStore.setSort('customer_name')">
              <span>לקוח</span>
              <SortArrow :active="portalStore.sortBy === 'customer_name'" :dir="portalStore.sortDir" />
            </th>
            <th class="sortable" @click="portalStore.setSort('status')">
              <span>סטטוס</span>
              <SortArrow :active="portalStore.sortBy === 'status'" :dir="portalStore.sortDir" />
            </th>
            <th class="sortable" @click="portalStore.setSort('created_at')">
              <span>נוצר</span>
              <SortArrow :active="portalStore.sortBy === 'created_at'" :dir="portalStore.sortDir" />
            </th>
            <th class="sortable" @click="portalStore.setSort('last_accessed_at')">
              <span>פעילות אחרונה</span>
              <SortArrow :active="portalStore.sortBy === 'last_accessed_at'" :dir="portalStore.sortDir" />
            </th>
            <th class="actions-col">פעולות</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="link in portalStore.paginatedLinks"
            :key="link.id"
            :class="{ inactive: link._status !== 'active' }"
          >
            <td class="customer-cell">
              <div class="customer-name">{{ link.customer_name }}</div>
              <div class="customer-meta">
                <span class="ltr-number">ת.ז. {{ link.customer_id_number }}</span>
                <span v-if="link.customer_email" class="ltr-number">· {{ link.customer_email }}</span>
              </div>
            </td>
            <td>
              <span class="status-badge" :class="link._status">
                <span class="status-dot"></span>
                {{ statusLabel(link._status) }}
              </span>
            </td>
            <td class="muted">{{ formatDate(link.created_at) }}</td>
            <td class="muted">
              <span v-if="link.last_accessed_at">{{ relativeTime(link.last_accessed_at) }}</span>
              <span v-else class="dim">טרם נצפה</span>
            </td>
            <td class="actions-cell">
              <div class="row-actions" v-if="link._status === 'active'">
                <button class="action-btn" @click="copyUrl(link)" :title="copiedToken === link.token ? 'הועתק!' : 'העתק קישור'">
                  <svg v-if="copiedToken !== link.token" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
                  </svg>
                  <svg v-else width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                </button>
                <button
                  v-if="link.customer_email"
                  class="action-btn"
                  @click="sendEmail(link)"
                  title="שלח באימייל"
                >
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                    <polyline points="22,6 12,13 2,6"/>
                  </svg>
                </button>
                <button class="action-btn danger" @click="confirmRevoke(link)" title="בטל קישור">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="18" y1="6" x2="6" y2="18"/>
                    <line x1="6" y1="6" x2="18" y2="18"/>
                  </svg>
                </button>
              </div>
              <span v-else class="row-actions-empty">—</span>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div v-if="portalStore.sortedLinks.length && portalStore.totalPages > 1" class="pagination">
        <div class="pg-info ltr-number">
          מציג <strong>{{ pageStart }}</strong>–<strong>{{ pageEnd }}</strong> מתוך <strong>{{ portalStore.sortedLinks.length }}</strong>
        </div>
        <div class="pg-nav">
          <button class="pg-btn" :disabled="portalStore.currentPage === 1" @click="portalStore.setPage(portalStore.currentPage - 1)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="9 18 15 12 9 6"/>
            </svg>
          </button>
          <button
            v-for="n in visiblePageRange"
            :key="n.key"
            class="pg-btn"
            :class="{ active: n.page === portalStore.currentPage, gap: n.gap }"
            :disabled="n.gap"
            @click="!n.gap && portalStore.setPage(n.page)"
          >
            {{ n.gap ? '…' : n.page }}
          </button>
          <button class="pg-btn" :disabled="portalStore.currentPage === portalStore.totalPages" @click="portalStore.setPage(portalStore.currentPage + 1)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="15 18 9 12 15 6"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <PortalGenerateModal
      :show="showGenerateModal"
      @close="showGenerateModal = false"
      @generated="onGenerated"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, h , watch, onBeforeUnmount } from 'vue'
import TabHeroLoop from './TabHeroLoop.vue'
import { usePortalStore } from '../../stores/portal.js'
import PortalGenerateModal from './PortalGenerateModal.vue'

defineProps({
  show: { type: Boolean, default: true },
  embedded: { type: Boolean, default: true },
})
defineEmits(['close'])

const portalStore = usePortalStore()
const showGenerateModal = ref(false)
const copiedToken = ref(null)

// ── "What your customer sees" slides (no links yet) ──
const plShowAssets = import.meta.glob('../../assets/welcome/portal-show.{webp,mp4}', { eager: true, import: 'default' })
const plShowArt = {
  still: Object.entries(plShowAssets).find(([k]) => k.endsWith('.webp'))?.[1] || '',
  video: Object.entries(plShowAssets).find(([k]) => k.endsWith('.mp4'))?.[1] || '',
}
const plReduced = typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
const PL_FEATURES = [
  { title: 'תמונת מצב', text: 'פרמיה, צבירה ומספר המוצרים — במבט אחד.' },
  { title: 'גרפים', text: 'פיזור לפי חברה ומגמה לאורך החודשים.' },
  { title: 'מה השתנה', text: 'עדכונים בתיק מאז הביקור הקודם.' },
  { title: 'שאלות ל-AI', text: 'הלקוח שואל — ה-AI עונה מתוך התיק שלו.' },
  { title: 'דוח מסלקה', text: 'החיסכון הפנסיוני מהמסלקה — צבירה ומגמה.' },
]
const PL_MS = 2800 // = PORTAL_SCENE_FRAMES / 30fps; keep in sync with .pl-bar--on
const plStep = ref(0)
const plCycle = ref(0)
const plPaused = ref(false)
const plSceneEl = ref(null)
let plTimer = null
let plRoot = null
let plMods = null
function plArm() {
  clearTimeout(plTimer)
  if (plReduced) return
  plTimer = setTimeout(() => { if (plPaused.value) return plArm(); plGo((plStep.value + 1) % PL_FEATURES.length) }, PL_MS)
}
function plGo(n) { plStep.value = n; plCycle.value++; plPaint(); plArm() }
let plMounting = false
async function plMount() {
  if (plReduced || plRoot || plMounting || !plSceneEl.value) return
  plMounting = true
  try {
    const [rd, react, player, comp] = await Promise.all([
      import('react-dom/client'), import('react'), import('@remotion/player'), import('../../remotion/PortalFeatureScene'),
    ])
    if (!plSceneEl.value) return
    plMods = { react, player, comp }
    plRoot = rd.createRoot(plSceneEl.value)
    plPaint()
  } catch (e) { console.error('[PortalLinksManager] scene failed', e) } finally { plMounting = false }
}
function plPaint() {
  if (!plRoot || !plMods) return
  const { react, player, comp } = plMods
  plRoot.render(react.createElement(player.Player, {
    key: plCycle.value, // restart the scene on every slide
    component: comp.PortalFeatureScene,
    inputProps: { step: plStep.value },
    durationInFrames: comp.PORTAL_SCENE_FRAMES, fps: 30,
    compositionWidth: comp.PORTAL_SCENE_W, compositionHeight: comp.PORTAL_SCENE_H,
    autoPlay: true, loop: true, controls: false, clickToPlay: false, doubleClickToFullscreen: false,
    showPosterWhenUnplayed: false, acknowledgeRemotionLicense: true,
    style: { width: '100%', height: '100%', backgroundColor: 'transparent' },
  }))
}
function plUnmount() { clearTimeout(plTimer); try { plRoot?.unmount() } catch { /* ignore */ } plRoot = null }
watch(plPaused, (p) => { if (!p) plArm() })
// The section only exists with no links; mount when its scene box appears.
watch(plSceneEl, (el) => { if (el) { plMount(); plGo(0) } else plUnmount() })
onBeforeUnmount(plUnmount)

const filterOptions = [
  { id: 'all', label: 'הכל' },
  { id: 'active', label: 'פעיל' },
  { id: 'expired', label: 'פג תוקף' },
  { id: 'revoked', label: 'מבוטל' },
]

// Sort arrow tiny component
const SortArrow = {
  props: { active: Boolean, dir: String },
  setup(props) {
    return () => h('span', { class: ['sort-arrow', { active: props.active, asc: props.dir === 'asc' }] }, [
      h('svg', {
        width: 10, height: 10, viewBox: '0 0 24 24', fill: 'none',
        stroke: 'currentColor', 'stroke-width': 3, 'stroke-linecap': 'round', 'stroke-linejoin': 'round',
      }, [
        h('polyline', { points: '6 9 12 15 18 9' }),
      ]),
    ])
  },
}

const pageStart = computed(() => (portalStore.currentPage - 1) * portalStore.pageSize + 1)
const pageEnd = computed(() =>
  Math.min(portalStore.currentPage * portalStore.pageSize, portalStore.sortedLinks.length)
)

const visiblePageRange = computed(() => {
  const total = portalStore.totalPages
  const cur = portalStore.currentPage
  const out = []
  const push = (page, gap = false) => out.push({ key: gap ? `gap-${page}` : `p-${page}`, page, gap })
  if (total <= 7) {
    for (let i = 1; i <= total; i++) push(i)
    return out
  }
  push(1)
  if (cur > 3) push(-1, true)
  for (let i = Math.max(2, cur - 1); i <= Math.min(total - 1, cur + 1); i++) push(i)
  if (cur < total - 2) push(-2, true)
  push(total)
  return out
})

onMounted(() => {
  portalStore.fetchLinks()
})

function statusLabel(status) {
  return status === 'active' ? 'פעיל' : status === 'expired' ? 'פג תוקף' : 'מבוטל'
}
function filterLabel(id) {
  return filterOptions.find(o => o.id === id)?.label || id
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('he-IL', { day: 'numeric', month: 'short', year: 'numeric' })
}

function relativeTime(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffMs = now - d
  const diffDay = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDay === 0) {
    const diffHr = Math.floor(diffMs / (1000 * 60 * 60))
    if (diffHr === 0) return 'לפני דקות'
    return `לפני ${diffHr} שעות`
  }
  if (diffDay === 1) return 'אתמול'
  if (diffDay < 7) return `לפני ${diffDay} ימים`
  return formatDate(dateStr)
}

async function copyUrl(link) {
  const url = `${window.location.origin}/portal/${link.token}`
  try {
    await navigator.clipboard.writeText(url)
    copiedToken.value = link.token
    setTimeout(() => { copiedToken.value = null }, 2000)
  } catch { /* ignore */ }
}

async function sendEmail(link) {
  try {
    await portalStore.sendEmail(link.token)
  } catch { /* error stored in store */ }
}

async function confirmRevoke(link) {
  if (!confirm(`לבטל את הקישור של ${link.customer_name}?`)) return
  try {
    await portalStore.revokeLink(link.token)
  } catch { /* error stored in store */ }
}

function resetFilters() {
  portalStore.setSearch('')
  portalStore.setStatusFilter('all')
}

function onGenerated() {
  // Link added by the modal's store call; nothing else needed
}
</script>

<style scoped>
/* ── No links yet: the customer's side of the portal ── */
.pl-show { position: relative; overflow: hidden; min-height: 420px; display: flex; align-items: center; margin: -4px 0 0; border-radius: var(--radius-md); }
.pl-show-photo {
  position: absolute; top: 0; bottom: 0; inset-inline-end: 0; width: 60%; z-index: 0; pointer-events: none;
  -webkit-mask-image: linear-gradient(to right, #000 0%, #000 45%, transparent 95%);
          mask-image: linear-gradient(to right, #000 0%, #000 45%, transparent 95%);
}
.pl-show-photo video, .pl-show-photo img { width: 100%; height: 100%; object-fit: cover; object-position: left center; display: block; }
.pl-show-copy { position: relative; z-index: 1; width: min(420px, 48%); padding: 32px 28px; display: flex; flex-direction: column; gap: 16px; }
.pl-show-title {
  margin: 0; font-family: 'Heebo', sans-serif; font-weight: 900;
  font-size: clamp(26px, 2.8vw, 36px); line-height: 1.1; letter-spacing: -0.03em; color: var(--text);
}
.pl-show-title span { color: var(--tab-portal-ink); }
.pl-slider { display: flex; flex-direction: column; gap: 12px; }
.pl-scene { width: 100%; aspect-ratio: 360 / 220; direction: ltr; }
.pl-slide-track { min-height: 52px; }
.pl-slide, .pl-feats li { display: flex; align-items: baseline; gap: 14px; }
.pl-feat-n { flex-shrink: 0; font-size: 13px; font-weight: 800; letter-spacing: 0.06em; color: var(--tab-portal); }
.pl-slide div, .pl-feats div { display: flex; flex-direction: column; gap: 2px; }
.pl-slide strong, .pl-feats strong { font-size: 18px; font-weight: 700; color: var(--text); }
.pl-slide div span, .pl-feats div span { font-size: 13.5px; color: var(--text-muted); line-height: 1.5; }
.pl-slide-enter-active { transition: opacity 0.26s ease-out, transform 0.3s cubic-bezier(0.16, 1, 0.3, 1); }
.pl-slide-leave-active { transition: opacity 0.16s ease-in, transform 0.18s ease-in; }
.pl-slide-enter-from { opacity: 0; transform: translateY(12px); }
.pl-slide-leave-to { opacity: 0; transform: translateY(-8px); }
.pl-bars { display: flex; gap: 6px; }
.pl-bar { position: relative; flex: 1; height: 16px; padding: 0; border: none; background: none; cursor: pointer; }
.pl-bar::before, .pl-bar-fill { position: absolute; inset-inline: 0; top: 6px; height: 4px; border-radius: 99px; }
.pl-bar::before { content: ''; background: color-mix(in srgb, var(--tab-portal) 18%, white); }
.pl-bar-fill { display: block; width: 0; inset-inline-end: auto; background: var(--tab-portal-ink); }
.pl-bar--done .pl-bar-fill { width: 100%; }
.pl-bar--on .pl-bar-fill { animation: pl-fill 2.8s linear forwards; }
.pl-bar--on.pl-bar--paused .pl-bar-fill { animation-play-state: paused; }
.pl-bar:focus-visible { outline: 2px solid var(--tab-portal); outline-offset: 2px; border-radius: 6px; }
@keyframes pl-fill { from { width: 0; } to { width: 100%; } }
.pl-feats { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 14px; }
@media (max-width: 760px) {
  .pl-show { flex-direction: column; align-items: stretch; min-height: 0; }
  .pl-show-photo { position: relative; width: 100%; height: 190px;
    -webkit-mask-image: linear-gradient(to bottom, #000 55%, transparent 100%);
            mask-image: linear-gradient(to bottom, #000 55%, transparent 100%); }
  .pl-show-copy { width: auto; padding: 8px 12px 20px; }
}

.portal-tab-root {
  background: var(--card-bg, #fff);
  border: 1px solid var(--border, #DDDBDA);
  border-radius: var(--radius-lg, 16px);
  padding: 24px;
  min-height: 480px;
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.08));
}

/* ── Toolbar ── */
.toolbar {
  position: relative;
  overflow: hidden;
  display: block;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-subtle, #E5E5E5);
  margin-bottom: 16px;
}

.toolbar-main {
  position: relative;
  z-index: 1;
  max-width: 66%;
  display: flex;
  flex-direction: column;
  gap: 16px;
  align-items: flex-start;
}

.toolbar-art {
  position: absolute;
  inset-inline-end: 0;
  top: 50%;
  transform: translateY(-50%);
  width: min(240px, 30%);
  aspect-ratio: 420 / 300;
  pointer-events: none;
  z-index: 0;
}

@media (max-width: 760px) {
  .toolbar-main { max-width: 100%; }
  .toolbar-art { display: none; }
}

.toolbar-title {
  display: flex;
  align-items: center;
  gap: 14px;
  color: var(--text, #181818);
}

.toolbar-title > svg {
  color: var(--tab-portal-ink);
  flex-shrink: 0;
  margin-top: 2px;
}

.toolbar-title h2.pl-wordmark {
  /* The product wordmark, same as "Nifraim המסלקה" (MaslakaTab .mk-hero-title). */
  font-family: 'Rubik', 'Heebo', sans-serif; font-size: clamp(28px, 3.3vw, 40px); font-weight: 700;
  letter-spacing: -0.03em; line-height: 1.05;
}
.pl-wordmark-acc { color: var(--tab-portal-ink); }
.toolbar-title h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 800;
  letter-spacing: -0.3px;
}

.toolbar-title p {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--text-muted, #706E6B);
  font-weight: 500;
}

.toolbar-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.search-wrap {
  position: relative;
  display: flex;
  align-items: center;
}

.search-wrap > svg {
  position: absolute;
  right: 12px;
  color: var(--text-muted, #706E6B);
  pointer-events: none;
}

.search-wrap input {
  width: 280px;
  padding: 10px 36px 10px 36px;
  border: 1px solid var(--border, #DDDBDA);
  border-radius: 10px;
  font-family: 'Heebo', sans-serif;
  font-size: 14px;
  color: var(--text, #181818);
  background: var(--bg-surface, #fff);
  transition: border-color 0.2s, box-shadow 0.2s;
}

.search-wrap input:focus {
  outline: none;
  border-color: var(--tab-portal-ink);
  box-shadow: 0 0 0 3px var(--tab-portal-wash);
}

.search-wrap input::placeholder {
  color: var(--text-muted, #706E6B);
}

.search-clear {
  position: absolute;
  left: 10px;
  background: none;
  border: none;
  padding: 4px;
  border-radius: 4px;
  color: var(--text-muted, #706E6B);
  cursor: pointer;
  display: flex;
}

.search-clear:hover {
  background: rgba(0, 0, 0, 0.05);
  color: var(--text, #181818);
}

.btn-generate {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: var(--tab-portal-ink);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-family: 'Heebo', sans-serif;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: var(--shadow-sm, 0 1px 3px rgba(0, 0, 0, 0.08));
}

.btn-generate:hover {
  background: var(--tab-portal-ink);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(78, 157, 208, 0.3);
}

.btn-generate.large {
  padding: 14px 28px;
  font-size: 15px;
  border-radius: 12px;
}

/* ── Filter pills ── */
.filter-pills {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  background: var(--bg, #F3F3F3);
  border: 1px solid transparent;
  border-radius: 100px;
  font-family: 'Heebo', sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted, #706E6B);
  cursor: pointer;
  transition: all 0.2s;
}

.pill:hover {
  background: var(--bg-surface, #fff);
  border-color: var(--border, #DDDBDA);
}

.pill.active {
  background: var(--tab-portal-ink);
  border-color: var(--tab-portal-ink);
  color: #fff;
  box-shadow: 0 2px 8px rgba(78, 157, 208, 0.25);
}

.pill-count {
  padding: 1px 8px;
  border-radius: 100px;
  font-size: 11px;
  font-weight: 700;
  background: rgba(0, 0, 0, 0.06);
  color: var(--text-muted, #706E6B);
}

.pill.active .pill-count {
  background: rgba(255, 255, 255, 0.25);
  color: #fff;
}

/* ── Table ── */
.table-wrap {
  overflow-x: auto;
}

.links-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-family: 'Heebo', sans-serif;
}

.links-table thead th {
  position: sticky;
  top: 0;
  background: var(--bg, #F3F3F3);
  padding: 11px 14px;
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted, #706E6B);
  text-align: start;
  border-bottom: 1px solid var(--border, #DDDBDA);
  letter-spacing: 0.02em;
  white-space: nowrap;
  user-select: none;
}

.links-table th.sortable {
  cursor: pointer;
  transition: color 0.15s;
}

.links-table th.sortable:hover {
  color: var(--text, #181818);
}

.links-table th .sort-arrow {
  display: inline-flex;
  margin-inline-start: 6px;
  opacity: 0.3;
  vertical-align: middle;
  transition: all 0.2s;
}

.links-table th .sort-arrow.active {
  opacity: 1;
  color: var(--tab-portal-ink);
}

.links-table th .sort-arrow.active.asc svg {
  transform: rotate(180deg);
}

.links-table th.actions-col {
  width: 130px;
  text-align: end;
}

.links-table tbody tr {
  transition: background 0.15s;
}

.links-table tbody tr:hover {
  background: var(--bg, #F3F3F3);
}

.links-table tbody tr.inactive {
  opacity: 0.6;
}

.links-table td {
  padding: 14px;
  font-size: 14px;
  color: var(--text, #181818);
  border-bottom: 1px solid var(--border-subtle, #E5E5E5);
  vertical-align: middle;
}

.customer-cell .customer-name {
  font-weight: 700;
  color: var(--text, #181818);
  margin-bottom: 3px;
}

.customer-cell .customer-meta {
  display: flex;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted, #706E6B);
  direction: ltr;
  text-align: start;
}

.customer-cell .customer-meta > span {
  direction: ltr;
}

td.muted {
  font-size: 13px;
  color: var(--text-muted, #706E6B);
}

.dim { color: var(--text-muted, #706E6B); opacity: 0.6; }

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.02em;
}

.status-badge .status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}

.status-badge.active {
  background: rgba(46, 132, 74, 0.12);
  color: var(--green, #2E844A);
}
.status-badge.active .status-dot { background: var(--green, #2E844A); box-shadow: 0 0 0 3px rgba(46, 132, 74, 0.15); }

.status-badge.expired {
  background: rgba(201, 162, 39, 0.12);
  color: var(--amber, #8A6300);
}
.status-badge.expired .status-dot { background: var(--amber, #8A6300); }

.status-badge.revoked {
  background: rgba(234, 0, 30, 0.08);
  color: var(--red, #EA001E);
}
.status-badge.revoked .status-dot { background: var(--red, #EA001E); }

/* Actions */
.actions-cell { text-align: end; }

.row-actions {
  display: inline-flex;
  gap: 4px;
}

.row-actions-empty {
  color: var(--text-muted, #706E6B);
  opacity: 0.4;
}

.action-btn {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 8px;
  color: var(--text-muted, #706E6B);
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: var(--bg, #F3F3F3);
  border-color: var(--border, #DDDBDA);
  color: var(--tab-portal-ink);
}

.action-btn.danger:hover {
  background: rgba(234, 0, 30, 0.06);
  border-color: rgba(234, 0, 30, 0.18);
  color: var(--red, #EA001E);
}

/* ── Skeleton ── */
.skeleton {
  padding: 8px 0;
}

.skeleton-row {
  display: grid;
  grid-template-columns: 2fr 1fr 1fr 1fr 130px;
  gap: 16px;
  padding: 14px;
  border-bottom: 1px solid var(--border-subtle, #E5E5E5);
}

.sk-cell {
  height: 14px;
  border-radius: 6px;
  background: linear-gradient(90deg, var(--bg, #F3F3F3) 0%, #E5E5E5 50%, var(--bg, #F3F3F3) 100%);
  background-size: 200% 100%;
  animation: shimmer 1.4s ease-in-out infinite;
}

.sk-name { height: 16px; width: 80%; }
.sk-status { width: 70px; }
.sk-date { width: 50%; }
.sk-actions { width: 96px; margin-inline-start: auto; }

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ── Empty states ── */
.empty-state {
  text-align: center;
  padding: 72px 24px;
  max-width: 440px;
  margin: 0 auto;
}

.empty-state.compact {
  padding: 56px 24px;
}

.empty-art-loop {
  display: block;
  width: min(320px, 90%);
  aspect-ratio: 420 / 300;
  margin: 0 auto 12px;
  pointer-events: none;
}

.empty-icon {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: var(--tab-portal-wash);
  color: var(--tab-portal-ink);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 20px;
}

.empty-icon.small {
  width: 56px;
  height: 56px;
  margin-bottom: 14px;
}

.empty-state h3 {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 800;
  color: var(--text, #181818);
  letter-spacing: -0.2px;
}

.empty-state p {
  margin: 0 0 20px;
  font-size: 14px;
  color: var(--text-muted, #706E6B);
  line-height: 1.6;
}

.btn-text {
  background: none;
  border: none;
  color: var(--tab-portal-ink);
  font-family: 'Heebo', sans-serif;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 8px;
  transition: background 0.15s;
}

.btn-text:hover {
  background: var(--tab-portal-wash);
}

/* ── Pagination ── */
.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 4px 4px;
  flex-wrap: wrap;
  gap: 12px;
}

.pg-info {
  font-size: 13px;
  color: var(--text-muted, #706E6B);
}

.pg-info strong {
  color: var(--text, #181818);
  font-weight: 700;
}

.pg-nav {
  display: flex;
  gap: 4px;
}

.pg-btn {
  min-width: 34px;
  height: 34px;
  padding: 0 10px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-surface, #fff);
  border: 1px solid var(--border, #DDDBDA);
  border-radius: 8px;
  font-family: 'Heebo', sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: var(--text, #181818);
  cursor: pointer;
  transition: all 0.15s;
}

.pg-btn:hover:not(:disabled):not(.active):not(.gap) {
  border-color: var(--tab-portal-ink);
  color: var(--tab-portal-ink);
}

.pg-btn.active {
  background: var(--tab-portal-ink);
  border-color: var(--tab-portal-ink);
  color: #fff;
  box-shadow: 0 2px 6px rgba(78, 157, 208, 0.28);
}

.pg-btn.gap {
  border: none;
  background: transparent;
  color: var(--text-muted, #706E6B);
  cursor: default;
  padding: 0;
  min-width: 20px;
}

.pg-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ── Responsive ── */
@media (max-width: 900px) {
  .toolbar { flex-direction: column; align-items: stretch; }
  .toolbar-actions { justify-content: space-between; }
  .search-wrap input { width: 100%; min-width: 200px; }
}

@media (max-width: 640px) {
  .portal-tab-root { padding: 16px; }
  .toolbar-title { flex-direction: column; gap: 8px; align-items: flex-start; }
  .toolbar-actions { flex-direction: column; align-items: stretch; }
  .btn-generate { justify-content: center; }
  .links-table thead { display: none; }
  .links-table tbody tr {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 6px 12px;
    padding: 14px 0;
  }
  .links-table td { border-bottom: none; padding: 2px 0; }
  .customer-cell { grid-column: 1 / -1; padding-bottom: 6px; border-bottom: 1px solid var(--border-subtle, #E5E5E5) !important; }
  .actions-cell { grid-column: 2; grid-row: 2 / 4; align-self: center; }
  td.muted { font-size: 12px; }
  .pagination { flex-direction: column-reverse; align-items: center; }
}

.ltr-number { direction: ltr; unicode-bidi: embed; display: inline-block; }
</style>
