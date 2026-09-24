import { computed, reactive, ref } from 'vue'
import { defineStore } from 'pinia'
import { extractionOutcome } from '../utils/extractionReport'

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

  // Server-side extraction emits no progress events. We time the bar based on
  // elapsed seconds, not iteration count, so it feels steady regardless of
  // jitter in `setInterval`:
  //   • 0-120s after bytes-done → 10% → 90%
  //   • 120-240s                → 90% → 95% (slow trickle)
  //   • response arrives        → snap to 100%
  // Measured 74–238s per agreement in production (2026-09-24). The old 25s
  // ramp parked the bar at 95% for minutes, which read as a hang.
  const EXTRACT_FAST_MS = 120_000  // reach 90% in ~2 minutes
  const EXTRACT_SLOW_MS = 120_000  // 90 → 95 over the next 2 minutes
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

  // Add an uploaded document to the list and tell the AI chat what it holds.
  function _announceDocument(data) {
    documents.value = [data, ...documents.value.filter(d => d.id !== data.id)]
    const lines = [`**מסמך נוסף לידע ה-AI:** ${data.filename}`]
    if (data.status === 'error') {
      lines.push(`שגיאה בעיבוד: ${data.error || 'לא ניתן לקרוא את המסמך'}`)
    } else {
      if (data.summary) lines.push(data.summary)
      if (data.companies_mentioned?.length) {
        lines.push(`חברות: ${data.companies_mentioned.join(', ')}`)
      }
      // Always say what happened to the rates — including "nothing, and
      // here is why". Silence on the zero case is what made a correct
      // "this agreement has no rate table" read as a broken upload.
      const rates = data.structured_data?.rates || []
      lines.push(
        extractionOutcome(data.structured_data?.extraction, rates).text,
      )
    }
    messages.value.push({ role: 'assistant', content: lines.join('\n\n') })
  }

  // ── Multi-file queue (agreement shelf) ──
  // Extraction is 1–4 min per agreement, and the shelf used to take one file at
  // a time: kiko's 15 agreements were an hour of babysitting (2026-09-24). The
  // queue runs QUEUE_CONCURRENCY uploads at once; the server bounds its own
  // Anthropic concurrency, so a larger batch just waits its turn there.
  const QUEUE_CONCURRENCY = 3
  // [{ key, name, size, status: 'queued'|'extracting'|'done'|'error',
  //    startedAt, finishedAt, doc, error }]
  const docQueue = ref([])
  const queueBusy = computed(() =>
    docQueue.value.some(i => i.status === 'queued' || i.status === 'extracting'),
  )

  async function _postDocument(item) {
    item.status = 'extracting'
    item.startedAt = Date.now()
    try {
      const form = new FormData()
      form.append('file', item.file)
      // rates_only: the shelf needs the rates, not the long AI summary
      // (which was the slowest part of every upload).
      const res = await fetch('/api/ai/documents/upload?rates_only=true', {
        method: 'POST', headers: authHeaders(), body: form,
      })
      let data = null
      try { data = await res.json() } catch { /* ignore */ }
      if (res.ok && data) {
        _announceDocument(data)
        item.doc = data
        item.status = data.status === 'error' ? 'error' : 'done'
        if (data.status === 'error') item.error = data.error || 'לא ניתן לקרוא את המסמך'
      } else {
        item.status = 'error'
        item.error = (data && data.detail) || 'העלאה נכשלה'
      }
    } catch {
      item.status = 'error'
      item.error = 'תקלת רשת'
    } finally {
      item.finishedAt = Date.now()
      item.file = null
    }
  }

  // Upload several PDFs, QUEUE_CONCURRENCY at a time. Resolves with the
  // queue items once every file has finished (successfully or not).
  async function uploadDocuments(files) {
    const items = Array.from(files || []).map((file, i) => reactive({
      key: `${Date.now()}-${i}-${file.name}`,
      name: file.name, size: file.size, file,
      status: 'queued', startedAt: null, finishedAt: null, doc: null, error: null,
    }))
    if (!items.length) return []
    docQueue.value = [...docQueue.value.filter(i => i.status === 'queued' || i.status === 'extracting'), ...items]
    let next = 0
    const worker = async () => {
      while (next < items.length) {
        const item = items[next++]
        await _postDocument(item)
      }
    }
    await Promise.all(Array.from({ length: Math.min(QUEUE_CONCURRENCY, items.length) }, worker))
    return items
  }

  function clearDocQueue() {
    docQueue.value = docQueue.value.filter(i => i.status === 'queued' || i.status === 'extracting')
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
          _announceDocument(data)
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
              // Backend may emit 2-3 viz blocks per synthesis answer. Push
              // each into an array so the panel can render them as a
              // carousel. Keep `viz` set to the most recent one so any
              // older consumers still get a value.
              const msg = messages.value[assistantIdx]
              if (!Array.isArray(msg.vizs)) msg.vizs = []
              msg.vizs.push(data.viz)
              msg.viz = data.viz
            }
            if (Array.isArray(data.warnings) && data.warnings.length) {
              // Post-answer numeric validator flagged amounts that aren't
              // backed by source data. Render as a yellow chip on the
              // assistant message so the user knows which numbers to verify.
              messages.value[assistantIdx].warnings = data.warnings
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
    uploadDocuments,
    docQueue,
    queueBusy,
    clearDocQueue,
    cancelUpload,
    removeDocument,
  }
})
