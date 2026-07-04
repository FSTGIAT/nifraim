<template>
  <div class="bell-wrap" ref="rootRef">
    <button
      class="bell-btn"
      :class="{ 'has-alerts': unreadCount > 0, 'is-open': open }"
      type="button"
      :title="`התראות (${unreadCount})`"
      :aria-label="`התראות, ${unreadCount} חדשות`"
      @click="toggle"
    >
      <span class="bell-glow" aria-hidden="true"></span>
      <svg class="bell-svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
        <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
        <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
      </svg>
      <span v-if="unreadCount > 0" class="bell-badge">
        <span class="ltr-number">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
      </span>
      <span v-if="store.loading" class="bell-spinner" aria-hidden="true"></span>
    </button>

    <!-- Panel teleported to body so it always sits above page chrome -->
    <Teleport to="body">
      <Transition name="bell-panel">
        <div v-if="open" class="bell-panel" role="dialog" aria-label="התראות">
          <header class="bp-head">
            <div class="bp-titles">
              <span class="bp-title">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
                </svg>
                התראות
              </span>
              <span class="bp-meta">
                <span v-if="store.lastRefreshedAt">עודכן {{ relTime(store.lastRefreshedAt) }}</span>
                <span v-else>טרם נטען</span>
              </span>
            </div>
            <div class="bp-head-actions">
              <button class="bp-link" type="button" :disabled="store.loading" @click="store.refresh()" title="רענן">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                </svg>
              </button>
              <button v-if="visibleAlerts.length" class="bp-link" type="button" @click="store.dismissAll()" title="נקה הכל">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
                נקה
              </button>
              <button class="bp-link bp-link--close" type="button" @click="close" title="סגור">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
          </header>

          <div class="bp-body">
            <!-- Loading -->
            <div v-if="store.loading && !visibleAlerts.length" class="bp-loading">
              <span class="dot-spinner" aria-hidden="true"></span>
              <span>בודק התראות…</span>
            </div>

            <!-- Empty — Remotion composition -->
            <div v-else-if="!visibleAlerts.length" class="bp-empty">
              <div ref="emptyMountEl" class="bp-empty-anim" aria-hidden="true">
                <!-- Fallback static art while React/Remotion stack loads -->
                <div v-if="!emptyRendered" class="bp-empty-fallback">
                  <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                    <polyline points="20 6 9 17 4 12"/>
                  </svg>
                </div>
              </div>
              <strong>אין התראות חדשות</strong>
              <span>כשיהיו שינויים — תקבל כאן את הפרטים</span>
            </div>

            <!-- Alerts list — card-style items -->
            <TransitionGroup v-else name="bp-card" tag="ul" class="bp-list">
              <li
                v-for="(a, i) in visibleAlerts"
                :key="a.id"
                class="bp-card"
                :class="`bp-card--${a.severity}`"
                :style="paintStyle(a, i)"
              >
                <div class="bp-card-wash">
                  <span class="bp-card-icon" aria-hidden="true">
                    <svg v-if="a.severity === 'error'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
                    </svg>
                    <svg v-else-if="a.severity === 'warning'" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                      <path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
                    </svg>
                    <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                    </svg>
                  </span>
                  <span class="bp-card-title">{{ a.title }}</span>
                </div>

                <div class="bp-card-body">
                  <p class="bp-card-text">{{ a.body }}</p>
                  <div class="bp-card-actions">
                    <button v-if="a.actions.includes('send_email')" class="bp-action bp-action--primary" type="button" @click="onSendEmail(a)">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>
                      </svg>
                      שלח אימייל
                    </button>
                    <button v-if="a.actions.includes('view_runs')" class="bp-action" type="button" @click="onOpenRuns()">פתח אוטומציה</button>
                    <button v-if="a.actions.includes('open_customer')" class="bp-action" type="button" @click="onOpenCustomer(a)">פתח לקוח</button>
                    <button v-if="a.actions.includes('open_comparison')" class="bp-action" type="button" @click="onOpenComparison(a)">פתח השוואה</button>
                    <button v-if="a.actions.includes('run_automation')" class="bp-action bp-action--primary" type="button" @click="onRunAutomation(a)">הרץ אוטומציה</button>
                    <button v-if="a.actions.includes('reopen_activation')" class="bp-action bp-action--primary" type="button" @click="onReopenActivation(a)">המשך הגדרה</button>
                    <button class="bp-action bp-action--ghost" type="button" @click="store.dismiss(a.id)">דחה</button>
                  </div>
                </div>
              </li>
            </TransitionGroup>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useNotificationsStore } from '../../stores/notifications.js'
import { reopenActivation } from '../../utils/setupState.js'
import { openMailCompose } from '../../utils/mailHelper.js'
import { showMailPreview } from '../../utils/mailPreviewState.js'
import { brandForLabel } from '../../utils/companyBrand.js'

/** Lighten a hex by `factor` (0..1) by interpolating each channel toward
 *  white. Used to brighten dark brand colors for the wash top-stop. */
function lighten(hex, factor) {
  const clean = (hex || '#706E6B').replace('#', '')
  const n = parseInt(clean.length === 3 ? clean.split('').map((c) => c + c).join('') : clean, 16)
  const r = Math.min(255, Math.floor(((n >> 16) & 0xff) + (255 - ((n >> 16) & 0xff)) * factor))
  const g = Math.min(255, Math.floor(((n >> 8)  & 0xff) + (255 - ((n >> 8)  & 0xff)) * factor))
  const b = Math.min(255, Math.floor((n & 0xff) + (255 - (n & 0xff)) * factor))
  return '#' + ((r << 16) | (g << 8) | b).toString(16).padStart(6, '0')
}
/** Perceived luminance 0..1 — used to decide how much to brighten very-dark
 *  brand colors (Phoenix navy, Clal deep-blue) extra. */
function luminance(hex) {
  const clean = (hex || '#706E6B').replace('#', '')
  const n = parseInt(clean.length === 3 ? clean.split('').map((c) => c + c).join('') : clean, 16)
  const r = ((n >> 16) & 0xff) / 255
  const g = ((n >> 8) & 0xff) / 255
  const b = (n & 0xff) / 255
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

/** Per-alert wash style — company brand color when the alert has one,
 *  otherwise fall back to a vivid severity palette. Gradient goes from a
 *  LIGHTER variant of the brand at the top → brand color at the bottom,
 *  so the card reads bright without losing the brand identity. */
const SEVERITY_PAINT = {
  error:   { base: '#EA001E', deep: '#C23934' },   // vivid red → deep red
  warning: { base: '#F57C00', deep: '#E65100' },   // orange → deep amber
  info:    { base: '#7F56D9', deep: '#7F56D9' },   // violet → violet
}
function paintFor(alert) {
  const co = alert?.meta?.companyName
  if (co) {
    const brand = brandForLabel(co)
    if (brand?.color) {
      // Darker brand colors (Phoenix #1F3D7A, Clal #003B7A) get a stronger
      // brighten boost so they don't read as muddy.
      const l = luminance(brand.color)
      const top = lighten(brand.color, l < 0.30 ? 0.42 : l < 0.50 ? 0.28 : 0.18)
      return { base: top, deep: brand.color }
    }
  }
  return SEVERITY_PAINT[alert.severity] || SEVERITY_PAINT.warning
}

const store = useNotificationsStore()
const open = ref(false)
const rootRef = ref(null)
const emptyMountEl = ref(null)
const emptyRendered = ref(false)

const visibleAlerts = computed(() => store.visibleAlerts)
const unreadCount = computed(() => store.unreadCount)

function toggle() {
  open.value = !open.value
  if (open.value) store.refresh().catch(() => {})
}
function close() { open.value = false }

function onClickOutside(e) {
  if (!open.value) return
  // The teleported panel lives outside rootRef — match by class so click-outside still works.
  if (e.target?.closest?.('.bell-panel')) return
  if (rootRef.value && !rootRef.value.contains(e.target)) close()
}
function onKey(e) { if (e.key === 'Escape') close() }

function relTime(iso) {
  try {
    const d = new Date(iso)
    const diff = (Date.now() - d.getTime()) / 1000
    if (diff < 60) return 'עכשיו'
    if (diff < 3600) return `לפני ${Math.round(diff / 60)} דק׳`
    if (diff < 86400) return `לפני ${Math.round(diff / 3600)} שע׳`
    return `לפני ${Math.round(diff / 86400)} ימים`
  } catch { return '' }
}

// ─── Action handlers ────────────────────────────────────
const fmtMoney = (n) => new Intl.NumberFormat('he-IL').format(Math.round(Number(n) || 0))

function onSendEmail(a) {
  // Per-company aggregate email
  if (a.kind === 'unpaid_company') {
    const subject = `החזר נפרעים — ${a.meta?.companyName || ''} · ${a.meta?.period || ''}`
    const namesList = (a.meta?.customerNames || []).map((n) => `  • ${n}`).join('\n')
    const lines = [
      'שלום,',
      '',
      `במסגרת בדיקה תקופתית של נפרעים מול תפוקה זוהו ${a.meta?.customersCount || 0} לקוחות שלא קיבלו עמלה בחברת ${a.meta?.companyName || ''} עבור תקופת ${a.meta?.period || ''}.`,
      a.meta?.totalUnpaidProducts ? `סה״כ ${a.meta.totalUnpaidProducts} מוצרים.` : null,
      a.meta?.totalPremium ? `סה״כ פרמיה לא משולמת: ₪${fmtMoney(a.meta.totalPremium)}.` : null,
      '',
      namesList ? `בין הלקוחות:\n${namesList}` : null,
      '',
      'מתבקש לבדוק ולהסדיר את התשלום בהקדם.',
      '',
      'תודה רבה.',
    ].filter(Boolean)
    const body = lines.join('\n')
    if (body.length > 800) {
      showMailPreview({ to: '', subject, body })
    } else {
      openMailCompose({ to: '', subject, body, skipIfTooLong: true }).catch(() => {
        showMailPreview({ to: '', subject, body })
      })
    }
    store.dismiss(a.id)
    close()
    return
  }

  // Legacy per-customer path (kept for any other future alert kinds)
  const subject = `הפניה לתשלום עמלה — ${a.meta?.fullName || a.title}`
  const lines = [
    'שלום,',
    '',
    `נמצא כי הלקוח ${a.meta?.fullName || ''} (ת.ז. ${a.meta?.idNumber || ''}) לא קיבל עמלה עבור ${a.meta?.unpaidCount || 0} מוצרים בתקופה ${a.meta?.period || ''}.`,
    a.meta?.unpaidSum ? `סך הפרמיה הלא משולמת: ₪${fmtMoney(a.meta.unpaidSum)}` : null,
    a.meta?.companies?.length ? `חברה: ${a.meta.companies.join(', ')}` : null,
    '',
    'מתבקש לבדוק ולעדכן בהקדם.',
    '',
    'תודה רבה.',
  ].filter(Boolean)
  const body = lines.join('\n')
  if (body.length > 800) {
    showMailPreview({ to: a.meta?.clientEmail || '', subject, body })
  } else {
    openMailCompose({ to: a.meta?.clientEmail || '', subject, body, skipIfTooLong: true }).catch(() => {
      showMailPreview({ to: a.meta?.clientEmail || '', subject, body })
    })
  }
  store.dismiss(a.id)
  close()
}
function onOpenRuns() { window.location.hash = '#automation'; close() }
function onOpenCustomer(a) { store.dismiss(a.id); close() }
function onOpenComparison() { window.location.hash = '#comparison'; close() }
function onRunAutomation() {
  // Jump to the automation tab — the user picks which credential to run.
  // (Auto-triggering a specific run would need a backend mapping company → credential.)
  window.location.hash = '#automation'
  close()
}

function onReopenActivation(a) {
  // Re-open the new-user activation checklist (it auto-hides after first view).
  reopenActivation()
  store.unpinAlert(a.id)
  close()
}

/** Inline styles per card: brand-or-severity wash + stagger delay. */
function paintStyle(a, i) {
  const p = paintFor(a)
  return {
    '--c-base': p.base,
    '--c-deep': p.deep,
    '--c-edge': p.base + '52',  // 32% alpha for the hover ring
    '--stagger': `${i * 60}ms`,
  }
}

// ─── Remotion empty-state composition (React island) ─────────────
let reactStack = null
let reactRoot = null
let currentEmptyEl = null

async function ensureReactStack() {
  if (reactStack) return reactStack
  const [rdClient, react, player, remotion] = await Promise.all([
    import('react-dom/client'),
    import('react'),
    import('@remotion/player'),
    import('../../remotion'),
  ])
  reactStack = {
    createRoot: rdClient.createRoot,
    createElement: react.createElement,
    Player: player.Player,
    NotificationsEmpty: remotion.NotificationsEmpty,
    NOTIFICATIONS_EMPTY_DURATION: remotion.NOTIFICATIONS_EMPTY_DURATION,
  }
  return reactStack
}

async function renderEmpty() {
  if (!emptyMountEl.value) return
  try {
    const stack = await ensureReactStack()
    if (!emptyMountEl.value) return
    if (reactRoot && currentEmptyEl !== emptyMountEl.value) {
      try { reactRoot.unmount() } catch { /* ignore */ }
      reactRoot = null
    }
    if (!reactRoot) {
      reactRoot = stack.createRoot(emptyMountEl.value)
      currentEmptyEl = emptyMountEl.value
    }
    const el = stack.createElement(stack.Player, {
      key: `notif-empty-${Date.now()}`,
      component: stack.NotificationsEmpty,
      durationInFrames: stack.NOTIFICATIONS_EMPTY_DURATION,
      fps: 30,
      compositionWidth: 360,
      compositionHeight: 200,
      autoPlay: true,
      loop: true,
      controls: false,
      clickToPlay: false,
      doubleClickToFullscreen: false,
      showPosterWhenUnplayed: false,
      showPosterWhenPaused: false,
      showPosterWhenEnded: false,
      showPosterWhenBuffering: false,
      acknowledgeRemotionLicense: true,
      style: { width: '100%', height: '100%' },
    })
    reactRoot.render(el)
    emptyRendered.value = true
  } catch (e) {
    console.warn('[notification-bell] empty-state render failed', e)
  }
}

function teardownEmpty() {
  if (reactRoot) {
    try { reactRoot.unmount() } catch { /* ignore */ }
    reactRoot = null
    currentEmptyEl = null
    emptyRendered.value = false
  }
}

// Render the empty composition only when the panel opens AND there are no alerts.
watch([open, visibleAlerts], ([isOpen, alerts]) => {
  if (isOpen && (!alerts || alerts.length === 0)) {
    nextTick(renderEmpty)
  } else {
    teardownEmpty()
  }
})

onMounted(() => {
  store.startBackground()
  document.addEventListener('mousedown', onClickOutside)
  document.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  store.stopBackground()
  teardownEmpty()
  document.removeEventListener('mousedown', onClickOutside)
  document.removeEventListener('keydown', onKey)
})
</script>

<style scoped>
.bell-wrap { position: relative; display: inline-flex; }

/* ─── Bell button ─── */
.bell-btn {
  position: relative;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border: 1px solid var(--border-subtle);
  border-radius: 12px;
  background: var(--card-bg, #fff);
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.18s, color 0.18s, border-color 0.18s, transform 0.15s, box-shadow 0.2s;
  box-shadow: 0 2px 6px rgba(26, 20, 16, 0.06), 0 8px 18px rgba(26, 20, 16, 0.05);
  backdrop-filter: blur(8px);
}
.bell-btn:hover {
  color: var(--text);
  border-color: var(--text-muted);
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(26, 20, 16, 0.10), 0 12px 24px rgba(26, 20, 16, 0.08);
}
.bell-btn:active { transform: scale(0.96); }
.bell-btn.is-open {
  color: var(--text);
  border-color: var(--primary, #F57C00);
  box-shadow: 0 0 0 4px rgba(245, 124, 0, 0.12), 0 8px 20px rgba(245, 124, 0, 0.18);
}
.bell-btn.has-alerts {
  color: var(--primary-deep, #E65100);
  border-color: rgba(245, 124, 0, 0.40);
  background: linear-gradient(135deg, rgba(245, 124, 0, 0.06) 0%, var(--card-bg, #fff) 100%);
}
.bell-btn.has-alerts .bell-svg { animation: bell-shake 2.2s ease-in-out infinite; transform-origin: 50% 4px; }
@keyframes bell-shake {
  0%, 88%, 100% { transform: rotate(0); }
  90% { transform: rotate(-10deg); }
  92% { transform: rotate(9deg); }
  94% { transform: rotate(-6deg); }
  96% { transform: rotate(4deg); }
  98% { transform: rotate(-2deg); }
}

.bell-glow {
  position: absolute;
  inset: -1px;
  border-radius: inherit;
  background: radial-gradient(circle at 30% 20%, rgba(245, 124, 0, 0.18), transparent 60%);
  opacity: 0;
  transition: opacity 0.25s;
  pointer-events: none;
}
.bell-btn.has-alerts .bell-glow { opacity: 1; }

.bell-badge {
  position: absolute;
  top: -5px;
  inset-inline-end: -5px;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  display: grid;
  place-items: center;
  border-radius: 12px;
  background: linear-gradient(135deg, #F57C00 0%, #E65100 100%);
  color: #fff;
  font-size: 10.5px;
  font-weight: 800;
  letter-spacing: 0.3px;
  box-shadow: 0 3px 8px rgba(230, 81, 0, 0.50), inset 0 -1px 0 rgba(0,0,0,0.18);
  animation: badge-pop 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
@keyframes badge-pop {
  0% { transform: scale(0.4); opacity: 0; }
  100% { transform: scale(1); opacity: 1; }
}
.bell-spinner {
  position: absolute;
  width: 8px;
  height: 8px;
  inset-inline-start: 4px;
  top: 4px;
  border: 1.5px solid currentColor;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  opacity: 0.7;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>

<!-- Panel is Teleported to body — must live in a global style block. -->
<style>
.bell-panel {
  position: fixed;
  top: 100px;
  inset-inline-start: 18px;  /* RTL: visual-RIGHT */
  width: 400px;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #FFFBF4 0%, #FFFFFF 100%);
  border: 1px solid #EADFCC;
  border-radius: 16px;
  box-shadow: 0 24px 60px rgba(26, 20, 16, 0.18), 0 6px 18px rgba(26, 20, 16, 0.08);
  z-index: 1500;
  overflow: hidden;
  font-family: 'Heebo', sans-serif;
  direction: rtl;
}
@media (max-width: 720px) {
  .bell-panel {
    inset-inline-start: 8px;
    inset-inline-end: 8px;
    width: auto;
  }
}

/* Panel opens with a snappy 3D-style burst from the bell anchor + closes with
 * a quick collapse upward. Origin set so the animation feels rooted to the
 * bell button (which sits at top-right in RTL). */
.bell-panel {
  transform-origin: 0% 0%;  /* RTL: 0% inline-start = visual-right (the bell) */
}
.bell-panel-enter-active {
  animation: bp-burst-in 0.42s cubic-bezier(0.34, 1.56, 0.64, 1) both;
}
.bell-panel-leave-active {
  animation: bp-collapse-out 0.24s cubic-bezier(0.55, 0, 0.68, 0.2) both;
}
@keyframes bp-burst-in {
  0%   { opacity: 0; transform: translateY(-24px) scale(0.55) rotateX(40deg); }
  50%  { opacity: 1; }
  70%  { transform: translateY(2px) scale(1.02) rotateX(-2deg); }
  100% { opacity: 1; transform: translateY(0) scale(1) rotateX(0); }
}
@keyframes bp-collapse-out {
  0%   { opacity: 1; transform: translateY(0) scale(1); }
  100% { opacity: 0; transform: translateY(-18px) scale(0.86); }
}

.bp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid #EADFCC;
  background:
    linear-gradient(180deg, rgba(245, 124, 0, 0.08) 0%, rgba(245, 124, 0, 0.02) 100%);
  flex-shrink: 0;
}
.bp-titles { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.bp-title {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 14px;
  font-weight: 800;
  color: #1A1410;
  letter-spacing: -0.2px;
}
.bp-title svg { color: #F57C00; }
.bp-meta { font-size: 11px; color: #6B5F50; }
.bp-head-actions { display: inline-flex; gap: 4px; align-items: center; }

.bp-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 700;
  color: #6B5F50;
  background: transparent;
  border: 1px solid #EADFCC;
  border-radius: 7px;
  padding: 4px 8px;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.bp-link:hover:not(:disabled) { color: #1A1410; border-color: #6B5F50; background: rgba(0,0,0,0.04); }
.bp-link:disabled { opacity: 0.5; cursor: not-allowed; }
.bp-link--close { padding: 4px 6px; }

.bp-body { flex: 1; overflow-y: auto; padding: 12px; }

.bp-loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px;
  color: #6B5F50;
  font-size: 12.5px;
  font-weight: 600;
}
.dot-spinner {
  width: 14px; height: 14px;
  border: 2px solid #EADFCC;
  border-top-color: #F57C00;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.bp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  text-align: center;
  color: #6B5F50;
  font-size: 12.5px;
  padding: 8px 8px 14px;
}
.bp-empty strong {
  color: #1A1410;
  font-size: 14px;
  font-weight: 800;
  margin-top: 4px;
}
.bp-empty-anim {
  width: 100%;
  aspect-ratio: 9 / 5;
  background: #FFFBF4;
  border: 1px solid #EADFCC;
  border-radius: 12px;
  overflow: hidden;
  position: relative;
}
.bp-empty-fallback {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: #2E844A;
  opacity: 0.6;
}

/* ─── Card-style alert items ─── */
.bp-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.bp-card {
  background: #fff;
  border: 1px solid #EADFCC;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 6px rgba(26, 20, 16, 0.04);
  transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.18s, border-color 0.18s;
  animation: bp-card-in 0.34s cubic-bezier(0.34, 1.56, 0.64, 1) both;
  animation-delay: var(--stagger, 0ms);
}
.bp-card:hover {
  transform: translateY(-2px);
  border-color: var(--c-edge, #EADFCC);
  box-shadow: 0 12px 24px rgba(26, 20, 16, 0.08), 0 4px 10px rgba(26, 20, 16, 0.04);
}
@keyframes bp-card-in {
  0% { opacity: 0; transform: translateY(8px) scale(0.97); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}

/* Severity defaults — overridden inline per-card via paintStyle() which
 * pulls the actual company brand color (Migdal red, Phoenix navy, etc.). */
.bp-card--error   { --c-base: #EA001E; --c-deep: #C23934; --c-edge: rgba(194, 57, 52, 0.32); }
.bp-card--warning { --c-base: #E8720A; --c-deep: #E65100; --c-edge: rgba(232, 114, 10, 0.32); }
.bp-card--info    { --c-base: #7F56D9; --c-deep: #7F56D9; --c-edge: rgba(127, 86, 217, 0.32); }

.bp-card-wash {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 12px;
  background: linear-gradient(135deg, var(--c-base) 0%, var(--c-deep) 100%);
  color: #fff;
  position: relative;
  overflow: hidden;
}
.bp-card-wash::after {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 90% 10%, rgba(255,255,255,0.20), transparent 50%);
  pointer-events: none;
}
.bp-card-icon {
  width: 26px; height: 26px;
  display: grid; place-items: center;
  /* Use the darker brand stop so the icon stays readable against the
   * lighter top of the wash. */
  background: var(--c-deep, rgba(255, 255, 255, 0.20));
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 7px;
  flex-shrink: 0;
  position: relative;
  z-index: 1;
  box-shadow: 0 2px 5px rgba(0, 0, 0, 0.18);
}
.bp-card-title {
  font-size: 13px;
  font-weight: 800;
  letter-spacing: -0.1px;
  /* Stronger shadow so white text stays legible against the brighter wash. */
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.35), 0 0 12px rgba(0, 0, 0, 0.15);
  position: relative;
  z-index: 1;
}

.bp-card-body { padding: 10px 12px 11px; }
.bp-card-text {
  margin: 0;
  font-size: 12px;
  color: #4A4035;
  line-height: 1.45;
  word-break: break-word;
}
.bp-card-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 9px;
  flex-wrap: wrap;
}

.bp-action {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: inherit;
  font-size: 11.5px;
  font-weight: 700;
  color: #1A1410;
  background: #fff;
  border: 1px solid #EADFCC;
  border-radius: 7px;
  padding: 5px 10px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s, border-color 0.15s, transform 0.12s;
}
.bp-action:hover { background: #FFFBF4; border-color: #6B5F50; }
.bp-action:active { transform: scale(0.97); }
.bp-action--primary {
  background: linear-gradient(135deg, #F57C00, #FF9800);
  color: #fff;
  border-color: transparent;
  box-shadow: 0 3px 8px rgba(245, 124, 0, 0.32);
}
.bp-action--primary:hover {
  background: linear-gradient(135deg, #F57C00, #FF9800);
  border-color: transparent;
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(245, 124, 0, 0.42);
}
.bp-action--ghost { color: #6B5F50; border-color: transparent; }
.bp-action--ghost:hover { color: #1A1410; background: rgba(0,0,0,0.04); }

/* Card dismiss = collapse + sweep. The leaving card shrinks vertically then
 * slides off to the visual-end edge with the cadence color trailing behind. */
.bp-card-enter-active { transition: opacity 0.28s, transform 0.28s; }
.bp-card-leave-active {
  animation: bp-card-collapse 0.42s cubic-bezier(0.6, -0.05, 0.45, 1.05) both;
  position: absolute;
  left: 12px;
  right: 12px;
  z-index: 1;
}
@keyframes bp-card-collapse {
  0%   { opacity: 1; transform: translateX(0)   scale(1);    max-height: 200px; margin-bottom: 0; }
  35%  { opacity: 1; transform: translateX(-12px) scale(0.98); max-height: 200px; }
  100% { opacity: 0; transform: translateX(-60px) scale(0.88); max-height: 0;   margin-bottom: -10px; }
}
.bp-card-move { transition: transform 0.36s cubic-bezier(0.34, 1.56, 0.64, 1); }
</style>
