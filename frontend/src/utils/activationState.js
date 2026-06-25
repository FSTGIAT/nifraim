import { reactive } from 'vue'

/**
 * Shared signal for re-opening the new-user activation checklist after the user
 * has closed it. The notification-bell reminder calls reopenActivation();
 * WorkspaceView switches to the home view and ActivationChecklist shows itself
 * (then resets the flag). Mirrors the mailPreviewState pattern — sibling
 * components, no prop drilling.
 */
export const activationState = reactive({
  forceShow: false,
})

export function reopenActivation() {
  activationState.forceShow = true
}
