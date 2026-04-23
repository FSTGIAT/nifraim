/**
 * Opens an email compose window using the user's preferred email provider.
 * Provider is stored in localStorage under 'emailProvider'.
 *
 * Returns 'clipboard' if body was too long and was copied to clipboard instead,
 * or 'ok' if opened normally.
 *
 * @param {{ to?: string, subject?: string, body?: string }} options
 * @returns {Promise<'ok'|'clipboard'>}
 */
export async function openMailCompose({ to = '', subject = '', body = '' }) {
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

  // URL-length thresholds that trigger the clipboard fallback. Gmail/Outlook
  // compose endpoints return Bad Request 400 when the body query param grows
  // past ~2KB, so keep the web providers only marginally higher than mailto's
  // ~2000-char OS limit.
  const maxLen = provider === 'mailto' ? 1800 : 1900

  // If URL is too long, open compose without body and copy body to clipboard
  if (url.length > maxLen) {
    let shortUrl
    if (provider === 'gmail') {
      const params = new URLSearchParams()
      params.set('view', 'cm')
      if (to) params.set('to', to)
      if (subject) params.set('su', subject)
      shortUrl = `https://mail.google.com/mail/?${params.toString()}`
    } else if (provider === 'outlook') {
      const params = new URLSearchParams()
      if (to) params.set('to', to)
      if (subject) params.set('subject', subject)
      shortUrl = `https://outlook.live.com/mail/0/deeplink/compose?${params.toString()}`
    } else {
      shortUrl = `mailto:${to}?subject=${encodeURIComponent(subject)}`
    }
    window.open(shortUrl, 'email_compose')
    try {
      await navigator.clipboard.writeText(body)
    } catch {
      // Fallback for older browsers
      const ta = document.createElement('textarea')
      ta.value = body
      ta.style.position = 'fixed'
      ta.style.opacity = '0'
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      document.body.removeChild(ta)
    }
    return 'clipboard'
  }

  window.open(url, 'email_compose')
  return 'ok'
}
