import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const loading = ref(false)
  const error = ref(null)
  const sources = ref([])
  const sourcesLoaded = ref(false)

  const documents = ref([])
  const documentsLoaded = ref(false)
  const uploadingDoc = ref(false)
  const uploadError = ref(null)

  function authHeaders() {
    const token = localStorage.getItem('token')
    return token ? { Authorization: `Bearer ${token}` } : {}
  }

  async function loadDocuments() {
    try {
      const res = await fetch('/api/ai/documents', { headers: authHeaders() })
      if (res.ok) {
        documents.value = await res.json()
      }
    } catch {
      // silently ignore
    } finally {
      documentsLoaded.value = true
    }
  }

  async function uploadDocument(file) {
    if (!file) return null
    uploadError.value = null
    uploadingDoc.value = true
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/ai/documents/upload', {
        method: 'POST',
        headers: authHeaders(),
        body: form,
      })
      if (!res.ok) {
        let msg = 'העלאה נכשלה'
        try {
          const data = await res.json()
          if (data.detail) msg = data.detail
        } catch { /* ignore */ }
        throw new Error(msg)
      }
      const doc = await res.json()

      // Insert at the top of the list (dedupe if same id).
      documents.value = [doc, ...documents.value.filter(d => d.id !== doc.id)]

      // Surface the result inline in the conversation so the user sees
      // exactly what Claude understood from their PDF.
      const lines = [`**מסמך נוסף לידע ה-AI:** ${doc.filename}`]
      if (doc.status === 'error') {
        lines.push(`שגיאה בעיבוד: ${doc.error || 'לא ניתן לקרוא את המסמך'}`)
      } else {
        if (doc.summary) lines.push(doc.summary)
        if (doc.companies_mentioned?.length) {
          lines.push(`חברות: ${doc.companies_mentioned.join(', ')}`)
        }
        const rates = doc.structured_data?.rates || []
        if (rates.length) {
          lines.push(`חולצו **${rates.length}** שיעורי עמלה — נוספו לטבלת השיעורים.`)
        }
      }
      messages.value.push({ role: 'assistant', content: lines.join('\n\n') })
      return doc
    } catch (e) {
      uploadError.value = e.message
      messages.value.push({
        role: 'assistant',
        content: `**שגיאה בהעלאת המסמך:** ${e.message}`,
      })
      return null
    } finally {
      uploadingDoc.value = false
    }
  }

  async function removeDocument(id) {
    try {
      const res = await fetch(`/api/ai/documents/${id}`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
      if (res.ok) {
        documents.value = documents.value.filter(d => d.id !== id)
      }
    } catch {
      // silently ignore
    }
  }

  async function sendMessage(text, viewContext = null) {
    error.value = null
    loading.value = true

    messages.value.push({ role: 'user', content: text })
    messages.value.push({ role: 'assistant', content: '' })

    const assistantIdx = messages.value.length - 1

    // Build history (exclude last empty assistant message)
    const history = messages.value.slice(0, -2).map(m => ({
      role: m.role,
      content: m.content,
    }))

    try {
      const token = localStorage.getItem('token')
      const body = { question: text, history }
      if (viewContext) body.view_context = viewContext
      const res = await fetch('/api/ai/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      })

      if (!res.ok) {
        throw new Error(res.status === 403 ? 'נדרש מנוי פעיל' : 'שגיאה בשרת')
      }

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const data = JSON.parse(line.slice(6))
            if (data.text) {
              messages.value[assistantIdx].content += data.text
            }
            if (data.viz) {
              messages.value[assistantIdx].viz = data.viz
            }
            if (data.done) break
          } catch {
            // ignore parse errors
          }
        }
      }
    } catch (e) {
      error.value = e.message
      // Remove empty assistant message on error
      if (!messages.value[assistantIdx].content) {
        messages.value.splice(assistantIdx, 1)
      }
    } finally {
      loading.value = false
    }
  }

  function clearMessages() {
    messages.value = []
    error.value = null
  }

  async function fetchSources() {
    try {
      const token = localStorage.getItem('token')
      const res = await fetch('/api/ai/sources', {
        headers: { 'Authorization': `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        sources.value = data.sources || []
      }
    } catch {
      // silently ignore
    } finally {
      sourcesLoaded.value = true
    }
  }

  return {
    messages,
    loading,
    error,
    sources,
    sourcesLoaded,
    documents,
    documentsLoaded,
    uploadingDoc,
    uploadError,
    sendMessage,
    clearMessages,
    fetchSources,
    loadDocuments,
    uploadDocument,
    removeDocument,
  }
})
