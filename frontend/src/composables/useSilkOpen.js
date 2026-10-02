// The ONE definition of how an AI chart opens — "slow and silky", iPhone-sheet
// style. Every AI viz surface (AiVizPanel, FundTrackVizPanel, the Nifra Agent's
// charts) uses these tokens/classes instead of its own easing values.
//
// CSS side (App.vue :root):
//   --ease-silk: cubic-bezier(0.32, 0.72, 0, 1)   iOS sheet curve
//   --dur-silk: 650ms        panel open
//   --dur-silk-close: 450ms  panel close (~70%)
//   --silk-content-delay: 280ms  chart content starts when the panel has settled
//   --silk-stagger: 40ms     per bar / slice, RTL order (from the right)
// and the global transition classes `.silk-enter-*` / `.silk-leave-*` (overlay +
// `.silk-card` inside) plus `.silk-swap-*` for switching charts in a carousel.
export const SILK = Object.freeze({
  ease: 'cubic-bezier(0.32, 0.72, 0, 1)',
  openMs: 650,
  closeMs: 450,
  contentDelayMs: 280,
  staggerMs: 40,
  numberMs: 900,
})

/** Name of the shared <Transition> for an AI viz overlay. */
export const SILK_TRANSITION = 'silk'
