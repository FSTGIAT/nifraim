import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { isImpersonating, getImpersonatedName, endImpersonation } from '../api/client.js'

const AGENCY_ROLES = ['agency_admin', 'agency_accountant']

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const isAuthenticated = computed(() => !!token.value)
  const isAgencyUser = computed(() => AGENCY_ROLES.includes(user.value?.role))
  // Truth comes from the JWT (user.impersonating, set server-side from the
  // `impersonator` claim). Fall back to the localStorage backup flag for the
  // brief window before /auth/me responds.
  const impersonating = computed(() => Boolean(user.value?.impersonating) || isImpersonating())
  const impersonatedName = computed(() => getImpersonatedName())
  // Where an authenticated user should land by default after login.
  // Both regular agents and agency super-users land at /workspace; the super-only
  // 'סוכנים' tab + agent folders in the AI library are the differentiator.
  const homePath = computed(() => '/workspace')

  async function login(email, password) {
    // Scrub any stale impersonation backup left over from a previous session
    // before installing the new token — otherwise homePath misroutes a fresh
    // agency-admin login to /workspace.
    endImpersonation()
    const res = await api.post('/auth/login', { email, password })
    token.value = res.data.access_token
    localStorage.setItem('token', token.value)
    await fetchUser()
    sessionStorage.setItem('justLoggedIn', '1')
  }

  async function register(email, password, fullName) {
    endImpersonation()
    const res = await api.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    })
    token.value = res.data.access_token
    localStorage.setItem('token', token.value)
    await fetchUser()
    sessionStorage.setItem('justLoggedIn', '1')
  }

  async function fetchUser() {
    try {
      const res = await api.get('/auth/me')
      user.value = res.data
    } catch {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
    endImpersonation()
  }

  return {
    token, user, isAuthenticated, isAgencyUser, impersonating, impersonatedName,
    homePath, login, register, fetchUser, logout,
  }
})
