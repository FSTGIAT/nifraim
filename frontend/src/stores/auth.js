import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api/client.js'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const isAuthenticated = computed(() => !!token.value)

  async function login(email, password) {
    const res = await api.post('/auth/login', { email, password })
    token.value = res.data.access_token
    localStorage.setItem('token', token.value)
    await fetchUser()
  }

  async function register(email, password, fullName) {
    const res = await api.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    })
    token.value = res.data.access_token
    localStorage.setItem('token', token.value)
    await fetchUser()
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
  }

  return { token, user, isAuthenticated, login, register, fetchUser, logout }
})
