import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

/**
 * Mailbox intake — how the emailed הכשרה production file reaches the app.
 *
 * The user only ever types their email address. `detect` resolves the domain's
 * MX record server-side and answers microsoft / google / other, because the mail
 * client someone names ("Outlook") says nothing about who actually hosts their
 * custom domain.
 */
export const useMailboxStore = defineStore('mailbox', () => {
  const config = ref(null)
  const detected = ref(null)
  // Which paths this deployment can serve. A Connect button that 503s, or a
  // forwarding address that never gets created, is worse than an honest message.
  const capabilities = ref({ microsoft: false, forwarding: false })
  const loading = ref(false)
  const saving = ref(false)
  const polling = ref(false)
  const error = ref(null)

  async function fetchConfig() {
    loading.value = true
    error.value = null
    try {
      const { data } = await api.get('/mailbox')
      config.value = data
      if (data) {
        detected.value = data.mail_host
        capabilities.value = { microsoft: data.microsoft_available, forwarding: data.forwarding_available }
      }
    } catch (e) {
      error.value = e.response?.data?.detail || 'לא הצלחנו לטעון את הגדרות המייל'
    } finally {
      loading.value = false
    }
  }

  async function detect(emailAddress) {
    try {
      const { data } = await api.post('/mailbox/detect', { email_address: emailAddress })
      detected.value = data.mail_host
      capabilities.value = {
        microsoft: data.microsoft_available,
        forwarding: data.forwarding_available,
      }
      return data.mail_host
    } catch {
      // Detection is a hint, never a gate. `other` (forwarding) works everywhere.
      detected.value = 'other'
      return 'other'
    }
  }

  async function save({ emailAddress, appPassword, mailHost }) {
    saving.value = true
    error.value = null
    try {
      const { data } = await api.put('/mailbox', {
        email_address: emailAddress,
        app_password: appPassword || null,
        mail_host: mailHost || null,
      })
      config.value = data
      return data
    } catch (e) {
      error.value = e.response?.data?.detail || 'לא הצלחנו לשמור את ההגדרות'
      throw e
    } finally {
      saving.value = false
    }
  }

  /** Returns the Microsoft consent URL to send the browser to. */
  async function microsoftConsentUrl() {
    const { data } = await api.get('/mailbox/oauth/microsoft/start')
    return data
  }

  async function pollNow() {
    polling.value = true
    try {
      const { data } = await api.post('/mailbox/poll-now')
      await fetchConfig()
      return data
    } finally {
      polling.value = false
    }
  }

  async function disconnect() {
    await api.delete('/mailbox')
    config.value = null
    detected.value = null
  }

  return { config, detected, capabilities, loading, saving, polling, error, fetchConfig, detect, save, microsoftConsentUrl, pollNow, disconnect }
})
