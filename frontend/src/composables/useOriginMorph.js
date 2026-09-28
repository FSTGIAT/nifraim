/**
 * iPhone-style open/close for a MODAL that belongs to a tapped element (a KPI
 * card): the modal card grows out of the element's rectangle and folds back
 * into it on close. Same feel as useLaunchMorph (the home-card → tab launch):
 * iOS curve, a small press dip, travel on `transform` only (compositor-run),
 * corner radius counter-scaled so it reads constant.
 *
 * Usage:
 *   const om = useOriginMorph()
 *   open:  om.remember(el); modalOpen = true; await nextTick(); om.grow(cardEl)
 *   close: await om.shrink(cardEl); modalOpen = false
 * No remembered origin (opened from elsewhere) → both calls are no-ops, so the
 * modal's own CSS transition plays as before.
 */
const OPEN_MS = 560
const CLOSE_MS = 380
const EASE = 'cubic-bezier(0.32, 0.72, 0, 1)' // iOS launch curve
const DIP = 0.96

function reduced() {
  return !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
}

export function useOriginMorph() {
  let origin = null
  let originEl = null

  function remember(el) {
    originEl = el || null
    if (!el) { origin = null; return }
    const r = el.getBoundingClientRect()
    origin = {
      left: r.left, top: r.top, width: r.width, height: r.height,
      radius: parseFloat(getComputedStyle(el).borderTopLeftRadius) || 14,
    }
  }

  /** Keyframe that places `card` exactly over the origin rect (k = press dip). */
  function atOrigin(card, k = 1, opacity = 1) {
    const t = card.getBoundingClientRect()
    const w = origin.width * k, h = origin.height * k
    const left = origin.left + (origin.width - w) / 2
    const top = origin.top + (origin.height - h) / 2
    const sx = w / t.width, sy = h / t.height
    return {
      transformOrigin: '0 0',
      transform: `translate(${left - t.left}px, ${top - t.top}px) scale(${sx}, ${sy})`,
      borderRadius: `${origin.radius / sx}px / ${origin.radius / sy}px`,
      opacity,
    }
  }

  function grow(card) {
    if (!origin || !card || reduced()) return
    const radius = getComputedStyle(card).borderTopLeftRadius
    // the tapped element "hands over" to the modal
    if (originEl) originEl.style.visibility = 'hidden'
    const anim = card.animate(
      [
        atOrigin(card, DIP, 0.85),
        { transformOrigin: '0 0', transform: 'none', borderRadius: radius, opacity: 1 },
      ],
      { duration: OPEN_MS, easing: EASE },
    )
    anim.finished.finally(() => { if (originEl) originEl.style.visibility = '' })
  }

  async function shrink(card) {
    if (!origin || !card || reduced()) { restore(); return }
    // the element is still on screen (it's behind the overlay) — re-measure,
    // it may have moved (scroll / resize) while the modal was open
    if (originEl && document.body.contains(originEl)) remember(originEl)
    const radius = getComputedStyle(card).borderTopLeftRadius
    const anim = card.animate(
      [
        { transformOrigin: '0 0', transform: 'none', borderRadius: radius, opacity: 1 },
        atOrigin(card, 1, 0),
      ],
      { duration: CLOSE_MS, easing: EASE, fill: 'forwards' },
    )
    try { await anim.finished } catch { /* cancelled */ }
    restore()
  }

  function restore() {
    if (originEl) originEl.style.visibility = ''
    origin = null
    originEl = null
  }

  return { remember, grow, shrink, hasOrigin: () => !!origin }
}
