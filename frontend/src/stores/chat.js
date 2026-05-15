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
  // Progress UI state — surfaced via UploadProgressCard.
  const uploadFileName = ref('')
  const uploadFileSize = ref(0)
  const uploadProgress = ref(0)
  // 'uploading' (real bytes-over-wire) | 'extracting' (server-side, simulated)
  // | 'complete' | 'error'
  const uploadStage = ref('uploading')
  let activeXhr = null
  let extractionTimer = null

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

  function _stopExtractionTimer() {
    if (extractionTimer) {
      clearInterval(extractionTimer)
      extractionTimer = null
    }
  }

  // Server-side extraction takes ~20-40s and emits no progress events. We
  // time the bar based on elapsed seconds, not iteration count, so it feels
  // steady regardless of jitter in `setInterval`:
  //   • 0-25s after bytes-done  → 10% → 90% (linear ≈ 3.2 pp/s — visibly moving)
  //   • 25-55s                  → 90% → 95% (slow trickle, ~0.17 pp/s)
  //   • response arrives        → snap to 100%
  // The previous version decayed the increment asymptotically; that looked
  // like the bar was stuck around 93%, which it kind of was — math, not bug.
  const EXTRACT_FAST_MS = 25_000   // reach 90% in ~25 seconds
  const EXTRACT_SLOW_MS = 30_000   // 90 → 95 over the next 30 seconds
  function _startExtractionRamp() {
    uploadStage.value = 'extracting'
    uploadProgress.value = Math.max(uploadProgress.value, 10)
    _stopExtractionTimer()
    const startAt = performance.now()
    const startFrom = uploadProgress.value
    extractionTimer = setInterval(() => {
      const elapsed = performance.now() - startAt
      let target
      if (elapsed < EXTRACT_FAST_MS) {
        const t = elapsed / EXTRACT_FAST_MS
        target = startFrom + (90 - startFrom) * t
      } else {
        const t = Math.min(1, (elapsed - EXTRACT_FAST_MS) / EXTRACT_SLOW_MS)
        target = 90 + 5 * t
      }
      uploadProgress.value = Math.min(95, target)
    }, 250)
  }

  function cancelUpload() {
    if (activeXhr) {
      try { activeXhr.abort() } catch { /* ignore */ }
      activeXhr = null
    }
    _stopExtractionTimer()
    uploadingDoc.value = false
    uploadStage.value = 'uploading'
    uploadProgress.value = 0
  }

  function uploadDocument(file) {
    if (!file) return Promise.resolve(null)
    uploadError.value = null
    uploadingDoc.value = true
    uploadFileName.value = file.name
    uploadFileSize.value = file.size
    uploadProgress.value = 0
    uploadStage.value = 'uploading'

    return new Promise((resolve) => {
      const xhr = new XMLHttpRequest()
      activeXhr = xhr
      xhr.open('POST', '/api/ai/documents/upload', true)
      const headers = authHeaders()
      if (headers.Authorization) xhr.setRequestHeader('Authorization', headers.Authorization)

      // Phase 1: real upload progress. Cap at 10% so the bar doesn't claim
      // "done" while the server is still extracting.
      xhr.upload.onprogress = (e) => {
        if (!e.lengthComputable || uploadStage.value !== 'uploading') return
        const networkPct = (e.loaded / e.total) * 100
        uploadProgress.value = Math.min(10, networkPct * 0.1)
      }
      // Bytes done → server starts extraction. Switch to the simulated ramp.
      xhr.upload.onload = () => _startExtractionRamp()

      const finish = (ok, data) => {
        activeXhr = null
        _stopExtractionTimer()
        if (ok) {
          uploadProgress.value = 100
          uploadStage.value = 'complete'
        } else {
          uploadStage.value = 'error'
        }
        // Hold the completed/errored card on screen briefly so the user
        // registers the state change before the spinner ref clears.
        setTimeout(() => {
          uploadingDoc.value = false
          uploadFileName.value = ''
          uploadFileSize.value = 0
          uploadProgress.value = 0
          uploadStage.value = 'uploading'
        }, ok ? 900 : 1400)
        resolve(data)
      }

      xhr.onload = () => {
        let data = null
        try { data = JSON.parse(xhr.responseText) } catch { /* ignore */ }
        if (xhr.status >= 200 && xhr.status < 300 && data) {
          documents.value = [data, ...documents.value.filter(d => d.id !== data.id)]
          const lines = [`**מסמך נוסף לידע ה-AI:** ${data.filename}`]
          if (data.status === 'error') {
            lines.push(`שגיאה בעיבוד: ${data.error || 'לא ניתן לקרוא את המסמך'}`)
          } else {
            if (data.summary) lines.push(data.summary)
            if (data.companies_mentioned?.length) {
              lines.push(`חברות: ${data.companies_mentioned.join(', ')}`)
            }
            const rates = data.structured_data?.rates || []
            if (rates.length) {
              lines.push(`חולצו **${rates.length}** שיעורי עמלה — נוספו לטבלת השיעורים.`)
            }
          }
          messages.value.push({ role: 'assistant', content: lines.join('\n\n') })
          finish(true, data)
        } else {
          const msg = (data && data.detail) || 'העלאה נכשלה'
          uploadError.value = msg
          messages.value.push({ role: 'assistant', content: `**שגיאה בהעלאת המסמך:** ${msg}` })
          finish(false, null)
        }
      }
      xhr.onerror = () => {
        uploadError.value = 'תקלת רשת'
        messages.value.push({ role: 'assistant', content: '**שגיאה בהעלאת המסמך:** תקלת רשת' })
        finish(false, null)
      }
      xhr.onabort = () => {
        // No assistant message — user cancelled intentionally.
        finish(false, null)
      }

      const form = new FormData()
      form.append('file', file)
      xhr.send(form)
    })
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
    uploadFileName,
    uploadFileSize,
    uploadProgress,
    uploadStage,
    sendMessage,
    clearMessages,
    fetchSources,
    loadDocuments,
    uploadDocument,
    cancelUpload,
    removeDocument,
  }
})
