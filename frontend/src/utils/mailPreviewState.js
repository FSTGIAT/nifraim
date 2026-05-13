import { reactive } from 'vue'

export const mailPreviewState = reactive({
  open: false,
  to: '',
  subject: '',
  body: '',
})

export function showMailPreview({ to = '', subject = '', body = '' }) {
  mailPreviewState.to = to
  mailPreviewState.subject = subject
  mailPreviewState.body = body
  mailPreviewState.open = true
}

export function closeMailPreview() {
  mailPreviewState.open = false
}
