import api from '../api/client.js'

/**
 * Download a file from an authenticated API route.
 *
 * An `<a download href="/api/...">` drops the Bearer token, so the request has
 * to go through the axios client as a blob and be handed to the browser as a
 * temporary object URL. That pattern was copy-pasted into six components; new
 * callers use this instead of adding a seventh.
 *
 * Prefers the server's own `Content-Disposition` filename — the backend sends
 * Hebrew names (`נפרעים מאוחד 09-2026.xlsx`) that carry the period, which a
 * hardcoded fallback cannot.
 */
export async function downloadViaApi(path, fallbackName, mime) {
  const res = await api.get(path, { responseType: 'blob' })

  let filename = fallbackName
  const cd = res.headers?.['content-disposition'] || ''
  const star = cd.match(/filename\*=UTF-8''([^;]+)/i)
  if (star) {
    try { filename = decodeURIComponent(star[1]) } catch { /* keep fallback */ }
  } else {
    const plain = cd.match(/filename="?([^";]+)"?/i)
    if (plain) filename = plain[1]
  }

  const url = URL.createObjectURL(new Blob([res.data], mime ? { type: mime } : undefined))
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  // Revoke on the next tick: revoking synchronously races the click in Safari.
  setTimeout(() => URL.revokeObjectURL(url), 1000)
  return filename
}

export const XLSX_MIME =
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
