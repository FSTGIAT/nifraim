/**
 * iPhone-style open for a modal that has no origin prop: it grows out of the
 * control the agent just pressed and folds back into it on close.
 *
 * The pressed control is taken from a document-level pointerdown capture kept
 * in a PLAIN variable (a reactive ref re-renders between mousedown and mouseup
 * and can swallow the click — see the nifraim-style skill). A press older than
 * PRESS_TTL means the modal was opened by code (e.g. back from Microsoft's
 * consent screen), so there is no origin and the modal's own CSS transition plays.
 *
 * Usage:
 *   const card = ref(null)
 *   const { closeWith } = usePressMorph(() => props.open, card)
 *   function close() { closeWith(() => emit('close')) }
 */
import { watch, nextTick } from 'vue'
import { useOriginMorph } from './useOriginMorph.js'

const PRESS_TTL = 800
let lastEl = null
let lastAt = 0
if (typeof document !== 'undefined') {
  document.addEventListener('pointerdown', (e) => {
    lastEl = e.target?.closest?.('button, a, [role="button"], [role="menuitem"], label') || null
    lastAt = performance.now()
  }, true)
}
function recentPress() {
  if (!lastEl || performance.now() - lastAt > PRESS_TTL) return null
  return document.body.contains(lastEl) ? lastEl : null
}

export function usePressMorph(isOpen, cardRef) {
  const morph = useOriginMorph()
  watch(isOpen, async (open) => {
    if (!open) return
    morph.remember(recentPress())
    await nextTick()
    morph.grow(cardRef.value)
  })
  async function closeWith(done) {
    await morph.shrink(cardRef.value)
    done()
  }
  return { closeWith }
}
