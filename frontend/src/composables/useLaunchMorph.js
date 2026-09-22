import { ref } from 'vue'

/**
 * iOS-style app launch / dismiss for the home card grid.
 *
 * The pressed card's rectangle grows to fill the viewport and its corner
 * radius flattens; going home reverses it back into the same card.
 *
 * Two things this file exists to get right, both learned the hard way:
 *
 * 1. **It travels on `transform`, not on `left/top/width/height`.** The rect
 *    version was geometrically perfect and visibly rough — animating box
 *    metrics forces layout every frame. The surface is now always a full-
 *    viewport box that scales down, which the compositor can run by itself.
 *    The corner radius is divided by the current scale, so it still *reads*
 *    as 14px the whole way across instead of shrinking with the box. Scaling
 *    down from the viewport (rather than up from the card) also keeps this
 *    RTL-safe: every position is a viewport coordinate, never a direction.
 *
 * 2. **The view commits while the surface is holding still.** Mounting a tab
 *    is heavy — charts, stores, a Remotion island — and doing it mid-travel
 *    dropped frames exactly where the eye was following. The surface now
 *    finishes travelling, holds opaque while the tab mounts behind it, and
 *    only then cross-dissolves. Any hitch happens under cover.
 */

// 420/290 was measurably correct and perceptually wrong: the travel was over
// in ~260ms and what you saw was a box blink, not a launch.
const OPEN_MS = 680
const CLOSE_MS = 460
// iOS's own launch curve: leaves fast, settles long. Not a symmetric ease.
const EASE = 'cubic-bezier(0.32, 0.72, 0, 1)'
// The dip before the launch. iOS compresses the icon under your finger first;
// doing it inside the animation buys the same read without adding latency.
const DIP = 0.955
// Travel ends here; the hold runs to the dissolve; the dissolve runs to 1.
const OPEN_ARRIVE = 0.62
const OPEN_DISSOLVE = 0.82
const CLOSE_ARRIVE = 0.72

function prefersReduced() {
  return !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

function nextFrame() {
  return new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))
}

function viewportRect() {
  return { left: 0, top: 0, width: window.innerWidth, height: window.innerHeight }
}

/** Shrink a rect about its own centre — the press dip. */
function dipped(r, k) {
  return {
    left: r.left + (r.width * (1 - k)) / 2,
    top: r.top + (r.height * (1 - k)) / 2,
    width: r.width * k,
    height: r.height * k,
  }
}

/** One keyframe of the travel, expressed as a scale down from the viewport. */
function frame(r, radius, opacity, vw, vh) {
  const sx = r.width / vw
  const sy = r.height / vh
  return {
    transform: `translate(${r.left}px, ${r.top}px) scale(${sx}, ${sy})`,
    // Counter-scaled, so the corner looks the same size throughout. Slightly
    // elliptical while sx ≠ sy, which nobody can see on a 14px corner.
    borderRadius: `${sx > 0 ? radius / sx : radius}px`,
    opacity,
  }
}

/**
 * Read a card's live geometry from the DOM by tab id.
 *
 * The grid replays its staggered `cardEnter` scale-up every time home mounts,
 * so a naive measurement catches the card mid-entrance and the app folds into
 * a box 28px short of where the card settles. Finishing the entrance first is
 * also what the moment wants: coming back, the springboard is already there —
 * it does not re-deal itself card by card.
 */
export function measureCard(tabId) {
  const el = document.querySelector(`.card[data-tab="${tabId}"]`)
  if (!el) return null
  for (const card of document.querySelectorAll('.card')) {
    for (const a of card.getAnimations?.() || []) {
      try { a.finish() } catch { /* an infinite animation cannot finish */ }
    }
  }
  const r = el.getBoundingClientRect()
  if (!r.width || !r.height) return null
  return {
    rect: { left: r.left, top: r.top, width: r.width, height: r.height },
    radius: parseFloat(getComputedStyle(el).borderRadius) || 14,
  }
}

export function useLaunchMorph() {
  /** The morph surface is mounted only while a morph is in flight. */
  const running = ref(false)
  const accent = ref('')
  const surfaceEl = ref(null)
  const glyphEl = ref(null)
  /** Which tab is launching — the surface carries its icon. */
  const tab = ref('')
  /** The transform the surface mounts with, before the animation takes over. */
  const seed = ref(null)
  /**
   * Which view falls back behind the launching app: '' | 'home' | 'content'.
   * A card launches out of the home grid; a strip pill launches out of the
   * tab you are already in. Naming the target matters — leaving it a boolean
   * receded whichever view happened to be mounted, so a card launch scaled the
   * INCOMING tab down the moment it committed.
   */
  const receding = ref('')

  let current = null

  function cancel() {
    current?.cancel()
    current = null
  }

  function seedFrom(r, radius) {
    const { width: vw, height: vh } = viewportRect()
    const f = frame(r, radius, 1, vw, vh)
    seed.value = { transform: f.transform, borderRadius: f.borderRadius }
  }

  async function play(from, to, fromRadius, toRadius, ms, opening) {
    const el = surfaceEl.value
    if (!el) return
    const { width: vw, height: vh } = viewportRect()
    const at = (r, rad, op) => frame(r, rad, op, vw, vh)
    cancel()

    const frames = opening
      ? [
          // Compress, then launch. The dip is 8% of the travel and is the
          // difference between "a box appeared" and "I pressed something".
          { ...at(from, fromRadius, 1), easing: 'ease-out' },
          { ...at(dipped(from, DIP), fromRadius, 1), offset: 0.08, easing: EASE },
          { ...at(to, toRadius, 1), offset: OPEN_ARRIVE, easing: 'linear' },
          { ...at(to, toRadius, 1), offset: OPEN_DISSOLVE, easing: 'ease-in' },
          at(to, toRadius, 0),
        ]
      : [
          { ...at(from, fromRadius, 1), easing: EASE },
          { ...at(to, toRadius, 1), offset: CLOSE_ARRIVE, easing: 'ease-in' },
          at(to, toRadius, 0),
        ]
    // `easing` MUST stay linear at the options level. Setting it here as well
    // as on the keyframes compounds the two: the whole 680ms ran on a curve
    // that is ~86% complete at 20% of the time, so the travel finished almost
    // immediately, the hold never happened, and the glyph was gone before it
    // could be seen. That double-easing is what read as "too quick".
    current = el.animate(frames, { duration: ms, easing: 'linear', fill: 'both' })

    // The glyph is what the eye actually follows across the screen — without
    // it the travel is a featureless box and reads as a flash. It lives inside
    // the surface, so it inherits the surface's scale and has to be counter-
    // scaled to stay the size it looks.
    const g = glyphEl.value
    if (g) {
      const counter = (r) => (r.width > 0 ? vw / r.width : 1)
      g.animate(
        opening
          ? [
              { opacity: 0, transform: `scale(${counter(from).toFixed(3)})` },
              { opacity: 0.9, transform: `scale(${counter(from).toFixed(3)})`, offset: 0.12 },
              { opacity: 0, transform: 'scale(1.6)', offset: 0.5 },
              { opacity: 0, transform: 'scale(1)' },
            ]
          : [
              { opacity: 0, transform: 'scale(1.6)' },
              { opacity: 0.9, transform: `scale(${counter(to).toFixed(3)})`, offset: CLOSE_ARRIVE },
              { opacity: 0, transform: `scale(${counter(to).toFixed(3)})` },
            ],
        { duration: ms, easing: 'linear', fill: 'both' },
      )
    }

    try {
      await current.finished
    } catch {
      /* cancelled by a newer morph — the newer one owns the surface now */
    }
  }

  /**
   * Launch: card rect → viewport. `commit` swaps the view underneath, fired
   * once the surface has arrived and is holding still.
   */
  async function launch({ rect, radius = 14, accent: ink = '', tabId = '', from = 'home', commit }) {
    if (!rect || prefersReduced()) {
      commit?.()
      return
    }
    accent.value = ink
    tab.value = tabId
    seedFrom(rect, radius)
    running.value = true
    receding.value = from
    // Let the surface mount at the card's position before it moves.
    await nextFrame()

    const done = play(rect, viewportRect(), radius, 0, OPEN_MS, true)
    // Mount the tab under cover of the hold, not mid-travel.
    setTimeout(() => commit?.(), Math.round(OPEN_MS * (OPEN_ARRIVE + 0.02)))
    await done
    running.value = false
    receding.value = ''
    tab.value = ''
  }

  /**
   * Dismiss: viewport → card rect. The view goes home FIRST so the grid is
   * laid out and the destination card can be measured for real — a rect
   * remembered from launch time is stale the moment the window is resized or
   * the grid reflows.
   */
  async function dismiss({ tabId, commit }) {
    if (prefersReduced()) {
      commit?.()
      return
    }
    const full = viewportRect()
    tab.value = tabId
    seedFrom(full, 0)
    running.value = true
    // No recede on the way back: iOS shows the springboard already in place
    // under the shrinking app, and a scaled home would move the very card we
    // are trying to land on.
    commit?.()

    // The grid sits behind an out-in Transition, so it is not in the DOM the
    // frame after `commit`. Wait for the card itself, not for a frame count —
    // a fixed wait was the difference between the app folding into its icon
    // and it just vanishing.
    let target = null
    for (let i = 0; i < 12 && !target; i++) {
      await nextFrame()
      target = measureCard(tabId)
    }
    if (!target) {
      running.value = false
      tab.value = ''
      return
    }
    await play(full, target.rect, 0, target.radius, CLOSE_MS, false)
    running.value = false
    tab.value = ''
  }

  return {
    running, receding, accent, tab, seed,
    surfaceEl, glyphEl, launch, dismiss, cancel,
  }
}
