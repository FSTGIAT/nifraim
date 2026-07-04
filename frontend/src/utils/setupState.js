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
})

export function openSetup(stepId = null) {
  setupState.requestedStep = stepId
  setupState.modalOpen = true
}

export function closeSetup() {
  setupState.modalOpen = false
  setupState.requestedStep = null
}

// Kept under the old name so the notification-bell action wiring stays intact.
export function reopenActivation() {
  openSetup()
}
