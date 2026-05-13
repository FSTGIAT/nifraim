import { showMailPreview } from './mailPreviewState.js'

/**
 * Opens an email compose window using the user's preferred email provider.
 * Provider is stored in localStorage under 'emailProvider'.
 *
 * Return values:
 *   - 'ok'        — compose opened with full body
 *   - 'preview'   — body was too long; a global preview modal was opened so
 *                    the user can copy the body and open compose themselves.
 *   - 'too_long'  — body was too long and skipIfTooLong=true was passed;
 *                    caller should handle (e.g. show an in-app preview)
 *
 * @param {{ to?: string, subject?: string, body?: string, skipIfTooLong?: boolean }} options
 * @returns {Promise<'ok'|'preview'|'too_long'>}
 */
export async function openMailCompose({ to = '', subject = '', body = '', skipIfTooLong = false }) {
  const provider = localStorage.getItem('emailProvider') || 'mailto'

  let url
  if (provider === 'gmail') {
    // fs=1 + tf=cm force Gmail's full compose window; without them the body
    // param is silently dropped on some accounts even for short URLs.
    const params = new URLSearchParams()
    params.set('view', 'cm')
    params.set('fs', '1')
    params.set('tf', 'cm')
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

  // URL-length thresholds: Gmail/Outlook compose endpoints return 400 when the
  // body query param grows past ~2KB; mailto OS handlers cap around 2000.
  const maxLen = provider === 'mailto' ? 1800 : 1900

  // Caller wants to render its own preview UI (e.g. ProductionComparison).
  if (url.length > maxLen && skipIfTooLong) {
    return 'too_long'
  }

  // URL is too long for the compose endpoint. Show the global preview modal
  // so the user can review + copy the body manually. We do NOT try to write
  // to the clipboard here — many browsers block writeText() when the page
  // isn't focused or when the user has dismissed the permission prompt
  // (which is exactly when this branch fires), and silent failure makes the
  // customer list "disappear" from the email.
  if (url.length > maxLen) {
    showMailPreview({ to, subject, body })
    return 'preview'
  }

  window.open(url, 'email_compose')
  return 'ok'
}
