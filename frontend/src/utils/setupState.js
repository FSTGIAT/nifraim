import { reactive } from 'vue'

/**
 * Shared signal for opening the setup wizard modal (SetupPipelineModal) from
 * anywhere — the home progress card, the notification-bell reminder, or an
 * empty-state CTA deep-linking to a specific step. The modal is teleported to
 * <body>, so opening works from any tab without switching views. Mirrors the
 * mailPreviewState pattern — sibling components, no prop drilling.
 */
export const setupState = reactive({
  modalOpen: false,
  requestedStep: null, // 'worker' | 'phone' | 'portal' | 'run' | null
  // A step whose action lives OUTSIDE the wizard (add a portal, Mail Agent,
  // מסלקה form, manual agreement upload). While set, the wizard reopens by
  // itself when that action finishes, and a "חזרה להפעלה" pill shows.
  away: null,
})

export function openSetup(stepId = null) {
  setupState.requestedStep = stepId
  setupState.modalOpen = true
}

/** Leave the wizard to do `stepId`'s action somewhere else in the app. */
export function leaveSetupFor(stepId) {
  setupState.away = stepId
  setupState.modalOpen = false
  setupState.requestedStep = null
}

/** Back to the wizard (after the away action finished, or from the pill). */
export function resumeSetup() {
  setupState.away = null
  openSetup()
}

/** Called by the away surfaces when their action completes. */
export function resumeSetupIfAway(stepId) {
  if (setupState.away && (!stepId || setupState.away === stepId)) resumeSetup()
}

export function closeSetup() {
  setupState.modalOpen = false
  setupState.requestedStep = null
}

// Kept under the old name so the notification-bell action wiring stays intact.
export function reopenActivation() {
  openSetup()
}
