import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const loading = ref(false)
  const error = ref(null)
  const sources = ref([])
  const sourcesLoaded = ref(false)

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
            if (data.done) break
            if (data.text) {
              messages.value[assistantIdx].content += data.text
            }
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

  return { messages, loading, error, sources, sourcesLoaded, sendMessage, clearMessages, fetchSources }
})
