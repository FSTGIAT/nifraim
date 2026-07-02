// Per-user localStorage flags.
//
// Onboarding flags ('onboarding_completed', 'activation_closed', …) used to be
// browser-global, so a brand-new user logging in on a browser where ANY earlier
// account had finished onboarding inherited "already onboarded" and never saw
// the welcome tour or the activation checklist. Keys are now scoped by the
// JWT subject of the logged-in user (read synchronously from the stored token,
// so callers don't need to await the auth store).

function userSuffix() {
  try {
    const token = localStorage.getItem('token')
    if (!token) return ''
    const payload = JSON.parse(
      atob(token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')),
    )
    return payload.sub || payload.email || ''
  } catch (_) {
    return ''
  }
}

function scopedKey(base) {
  const sfx = userSuffix()
  return sfx ? `${base}:${sfx}` : base
}

export function getUserFlag(base) {
  try {
    return localStorage.getItem(scopedKey(base))
  } catch (_) {
    return null
  }
}

export function setUserFlag(base, value) {
  try {
    localStorage.setItem(scopedKey(base), value)
    // Drop the legacy global key so it can't shadow anyone again.
    localStorage.removeItem(base)
  } catch (_) {
    /* storage unavailable — flags just won't persist */
  }
}
