import { onMounted, onBeforeUnmount } from 'vue'

/*
 * Scroll reveal: every element under `rootRef` matching `selector` rises and
 * fades in, softly, the first time it enters the viewport (QA 2026-10-01:
 * "when the user scrolls down, open every div silky and discover it").
 *
 * - Sections rendered LATER (after data loads, after a tab switch) are picked
 *   up by a MutationObserver, so nothing is missed.
 * - Each element reveals once; elements already on screen reveal at once with
 *   a small stagger.
 * - prefers-reduced-motion: nothing is hidden, nothing moves.
 *
 * The styles live in App.vue (`.sr` / `.sr--in`) so any tab can use this.
 */
export function useScrollReveal(rootRef, selector) {
  let io = null
  let mo = null
  const seen = new WeakSet()
  let stagger = 0

  function reduced() {
    return !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  }

  function track(el) {
    if (seen.has(el)) return
    seen.add(el)
    el.classList.add('sr')
    io.observe(el)
  }

  function scan() {
    const root = rootRef.value
    if (!root) return
    root.querySelectorAll(selector).forEach(track)
  }

  onMounted(() => {
    if (typeof IntersectionObserver === 'undefined' || reduced()) return
    io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (!e.isIntersecting) continue
        const el = e.target
        // Cards entering together cascade instead of popping as one block.
        el.style.transitionDelay = `${Math.min(stagger++, 4) * 140}ms`
        requestAnimationFrame(() => el.classList.add('sr--in'))
        setTimeout(() => { stagger = Math.max(0, stagger - 1) }, 120)
        io.unobserve(el)
      }
    }, { threshold: 0.12, rootMargin: '0px 0px -12% 0px' })
    scan()
    mo = new MutationObserver(() => scan())
    if (rootRef.value) mo.observe(rootRef.value, { childList: true, subtree: true })
  })

  onBeforeUnmount(() => { io?.disconnect(); mo?.disconnect() })
}
