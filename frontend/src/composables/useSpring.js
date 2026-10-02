// A small critically-damped spring for Vue refs — the hover-trace number and
// reference line glide to the hovered value instead of jumping (the motion of
// the "hover trace" bar chart, ported from React/motion to plain Vue).
// stiffness/damping match the original (110 / 20). Reduced motion → snaps.
import { onBeforeUnmount, ref, watch } from 'vue'
import { prefersReducedMotion } from '../components/ai-charts/format.js'

export function useSpring(source, { stiffness = 110, damping = 20, mass = 1 } = {}) {
  const value = ref(Number(typeof source === 'function' ? source() : source.value) || 0)
  let v = 0
  let target = value.value
  let raf = 0
  let last = 0

  function step(t) {
    const dt = Math.min(0.064, (t - (last || t)) / 1000) || 1 / 60
    last = t
    const force = -stiffness * (value.value - target) - damping * v
    v += (force / mass) * dt
    value.value += v * dt
    if (Math.abs(v) < 0.01 && Math.abs(value.value - target) < Math.max(0.005, Math.abs(target) * 1e-5)) {
      value.value = target
      v = 0
      raf = 0
      last = 0
      return
    }
    raf = requestAnimationFrame(step)
  }

  watch(source, (n) => {
    target = Number(n) || 0
    if (prefersReducedMotion()) { value.value = target; return }
    if (!raf) raf = requestAnimationFrame(step)
  })
  onBeforeUnmount(() => cancelAnimationFrame(raf))
  return value
}
