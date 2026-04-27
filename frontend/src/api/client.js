import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // If we're inside an impersonation session, fall back to the agency token
      // before bouncing to login — the impersonation token may have just expired
      // (15 minutes) and the parent session is still valid.
      const parent = localStorage.getItem('agency_token_backup')
      if (parent) {
        localStorage.setItem('token', parent)
        localStorage.removeItem('agency_token_backup')
        localStorage.removeItem('impersonating_name')
        window.location.href = '/agency'
        return Promise.reject(error)
      }
      localStorage.removeItem('token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// ─── Impersonation helpers ─────────────────────────────────────────────────
// An agency super-user can "drill into" one of their agents. We swap the JWT
// in localStorage to a short-lived impersonation token so the existing per-
// agent endpoints work unchanged. The original agency token is preserved in
// `agency_token_backup` so we can restore it on exit.

export function startImpersonation(impersonationToken, agentName) {
  const current = localStorage.getItem('token') || ''
  localStorage.setItem('agency_token_backup', current)
  localStorage.setItem('token', impersonationToken)
  localStorage.setItem('impersonating_name', agentName || '')
}

export function endImpersonation() {
  const backup = localStorage.getItem('agency_token_backup')
  if (backup) {
    localStorage.setItem('token', backup)
    localStorage.removeItem('agency_token_backup')
  }
  localStorage.removeItem('impersonating_name')
}

export function isImpersonating() {
  return Boolean(localStorage.getItem('agency_token_backup'))
}

export function getImpersonatedName() {
  return localStorage.getItem('impersonating_name') || ''
}

export default api
