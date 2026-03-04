/**
 * Opens an email compose window using the user's preferred email provider.
 * Provider is stored in localStorage under 'emailProvider'.
 *
 * @param {{ to?: string, subject?: string, body?: string }} options
 */
export function openMailCompose({ to = '', subject = '', body = '' }) {
  const provider = localStorage.getItem('emailProvider') || 'mailto'

  let url
  if (provider === 'gmail') {
    const params = new URLSearchParams()
    params.set('view', 'cm')
    if (to) params.set('to', to)
    if (subject) params.set('su', subject)
    if (body) params.set('body', body)
    url = `https://mail.google.com/mail/?${params.toString()}`
  } else if (provider === 'outlook') {
    const params = new URLSearchParams()
    if (to) params.set('to', to)
    if (subject) params.set('subject', subject)
    if (body) params.set('body', body)
    url = `https://outlook.live.com/mail/0/deeplink/compose?${params.toString()}`
  } else {
    // Default mailto
    url = `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
  }

  window.open(url, '_blank')
}
