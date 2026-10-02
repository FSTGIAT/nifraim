// שיחות — record a conversation in the browser, ship it to the calls pipeline
// (API → calls-gateway → Redis queue → ivrit.ai transcriber → Claude summary)
// and follow it until it comes back. Recording state (MediaRecorder + the live
// AnalyserNode the recorder's animated lines read) lives here so it survives a
// tab switch; the canvas only reads `analyser`.
import { defineStore } from 'pinia'
import { ref, shallowRef, computed } from 'vue'
import api from '../api/client'

export const CALL_TERMINAL = new Set(['done', 'failed'])
export const NO_SPEECH_NOTICE = 'לא זוהה דיבור בהקלטה — נסו שוב קרוב יותר למיקרופון'

// A finished call with nothing in it ("לא זוהה דיבור", no summary, no title):
// never shown in the history.
export function isNoSpeech(c) {
  if (!c || c.status !== 'done') return false
  if (c.error && /דיבור/.test(c.error)) return true
  // A full call (the list omits the transcript) whose transcript is only filler —
  // Whisper turns a tone, a hum or silence into "אההההה" / "תודה רבה" / "פרקס פרקס".
  // Fewer than three DIFFERENT real words = nothing was said.
  if (typeof c.transcript_text === 'string' || Array.isArray(c.segments)) {
    const text = c.transcript_text || (c.segments || []).map((x) => x.text).join(' ')
    const real = new Set(text.split(/\s+/).map((w) => w.replace(/[^\u0590-\u05FFa-zA-Z0-9]/g, ''))
      .filter((w) => new Set(w).size >= 2 && w.length >= 2))
    if (real.size < 3) return true
  }
  return !c.summary && !c.title && !!c.error
}
export const MAX_RECORD_SECONDS = 90 * 60
const POLL_MS = 3000
const MAX_POLL_FAILURES = 20

function pickMimeType() {
  if (typeof MediaRecorder === 'undefined') return ''
  const prefs = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg;codecs=opus', 'audio/mp4']
  return prefs.find((t) => MediaRecorder.isTypeSupported?.(t)) || ''
}

export const useCallsStore = defineStore('calls', () => {
  const enabled = ref(null)            // null = not checked yet
  const calls = ref([])                // CallOut[] newest first
  const current = ref(null)            // the call being processed / viewed (full CallOut)
  const loadingList = ref(false)
  const error = ref(null)

  // ── recording ──
  const recState = ref('idle')         // idle | requesting | recording | uploading
  const elapsed = ref(0)               // seconds
  const uploadProgress = ref(0)        // 0..1
  const analyser = shallowRef(null)    // AnalyserNode while recording
  let recorder = null
  let stream = null
  let audioCtx = null
  let chunks = []
  let tickHandle = null
  let startedAt = 0

  const isRecording = computed(() => recState.value === 'recording')

  // Live microphone level for the dithered ring, read every frame: RMS of the
  // time-domain signal, scaled so normal speech lands around 0.4–0.9 (max 1.2).
  let timeBuf = null
  function micLevel() {
    const node = analyser.value
    if (!node) return 0
    if (!timeBuf || timeBuf.length !== node.fftSize) timeBuf = new Uint8Array(node.fftSize)
    node.getByteTimeDomainData(timeBuf)
    let sum = 0
    for (let i = 0; i < timeBuf.length; i++) {
      const v = (timeBuf[i] - 128) / 128
      sum += v * v
    }
    return Math.min(1.2, Math.sqrt(sum / timeBuf.length) * 6)
  }

  async function fetchStatus() {
    try {
      const res = await api.get('/calls/status')
      enabled.value = !!res.data?.enabled
    } catch (_) {
      enabled.value = false
    }
    return enabled.value
  }

  async function fetchList() {
    loadingList.value = true
    try {
      const res = await api.get('/calls')
      calls.value = Array.isArray(res.data) ? res.data : []
    } catch (e) {
      error.value = e.response?.data?.detail || 'טעינת השיחות נכשלה'
    } finally {
      loadingList.value = false
    }
  }

  async function fetchCall(id) {
    const res = await api.get(`/calls/${id}`)
    _upsert(res.data)
    return res.data
  }

  function _upsert(call) {
    if (!call?.id) return
    const idx = calls.value.findIndex((c) => c.id === call.id)
    if (idx >= 0) calls.value[idx] = { ...calls.value[idx], ...call }
    else calls.value = [call, ...calls.value]
    if (current.value?.id === call.id) current.value = { ...current.value, ...call }
  }

  async function startRecording() {
    error.value = null
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') {
      error.value = 'הדפדפן הזה לא תומך בהקלטה. נסו Chrome או Edge.'
      return false
    }
    recState.value = 'requesting'
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
      })
    } catch (e) {
      recState.value = 'idle'
      error.value = e?.name === 'NotAllowedError'
        ? 'לא ניתנה הרשאה למיקרופון. אשרו גישה בסרגל הכתובת ונסו שוב.'
        : 'לא נמצא מיקרופון זמין.'
      return false
    }
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext
      audioCtx = new Ctx()
      const src = audioCtx.createMediaStreamSource(stream)
      const node = audioCtx.createAnalyser()
      node.fftSize = 1024
      node.smoothingTimeConstant = 0.8
      src.connect(node)
      analyser.value = node
    } catch (_) {
      analyser.value = null // lines fall back to the idle breath
    }
    const mimeType = pickMimeType()
    recorder = new MediaRecorder(stream, mimeType ? { mimeType, audioBitsPerSecond: 32000 } : undefined)
    chunks = []
    recorder.ondataavailable = (ev) => { if (ev.data?.size) chunks.push(ev.data) }
    recorder.start(1000)
    startedAt = Date.now()
    elapsed.value = 0
    tickHandle = setInterval(() => {
      elapsed.value = Math.floor((Date.now() - startedAt) / 1000)
      if (elapsed.value >= MAX_RECORD_SECONDS) stopAndUpload()
    }, 250)
    recState.value = 'recording'
    return true
  }

  function _teardownAudio() {
    clearInterval(tickHandle)
    tickHandle = null
    stream?.getTracks().forEach((t) => t.stop())
    stream = null
    try { audioCtx?.close() } catch (_) { /* already closed */ }
    audioCtx = null
    analyser.value = null
  }

  function _stopRecorder() {
    return new Promise((resolve) => {
      if (!recorder || recorder.state === 'inactive') return resolve()
      recorder.onstop = () => resolve()
      recorder.stop()
    })
  }

  // Discard without sending.
  async function cancelRecording() {
    await _stopRecorder()
    _teardownAudio()
    chunks = []
    recorder = null
    recState.value = 'idle'
  }

  async function stopAndUpload() {
    if (recState.value !== 'recording') return null
    const type = recorder?.mimeType || 'audio/webm'
    await _stopRecorder()
    _teardownAudio()
    const duration = Math.max(1, Math.round((Date.now() - startedAt) / 1000))
    const blob = new Blob(chunks, { type })
    chunks = []
    recorder = null
    if (blob.size < 1024) {
      recState.value = 'idle'
      error.value = 'ההקלטה קצרה מדי.'
      return null
    }
    recState.value = 'uploading'
    uploadProgress.value = 0
    const form = new FormData()
    form.append('audio', blob, type.includes('mp4') ? 'call.m4a' : 'call.webm')
    form.append('duration_s', String(duration))
    try {
      const res = await api.post('/calls', form, {
        onUploadProgress: (ev) => { if (ev.total) uploadProgress.value = ev.loaded / ev.total },
      })
      current.value = res.data
      lastRecordedId = res.data.id
      _upsert(res.data)
      recState.value = 'idle'
      if (!CALL_TERMINAL.has(res.data.status)) pollCall(res.data.id)
      else if (isNoSpeech(res.data)) { lastRecordedId = null; showNotice(NO_SPEECH_NOTICE); deleteCall(res.data.id).catch(() => {}) }
      return res.data
    } catch (e) {
      recState.value = 'idle'
      error.value = e.response?.data?.detail || 'שליחת ההקלטה נכשלה. נסו שוב.'
      return null
    }
  }

  // ── a short calm notice under the orb (e.g. no speech) ──
  const notice = ref('')
  let noticeTimer = null
  let lastRecordedId = null
  function showNotice(text) {
    notice.value = text
    clearTimeout(noticeTimer)
    noticeTimer = setTimeout(() => { notice.value = '' }, 5500)
  }

  // ── polling (one handle per call id) ──
  const pollers = new Map()

  function pollCall(id) {
    if (pollers.has(id)) return
    let failures = 0
    const handle = setInterval(async () => {
      try {
        const data = await fetchCall(id)
        failures = 0
        if (CALL_TERMINAL.has(data.status)) {
          stopPolling(id)
          // the agent's own just-recorded call came back empty: say so calmly,
          // then remove it so empty calls never pile up in the history
          if (id === lastRecordedId && isNoSpeech(data)) {
            lastRecordedId = null
            showNotice(NO_SPEECH_NOTICE)
            deleteCall(id).catch(() => {})
          }
        }
      } catch (e) {
        failures += 1
        if (e.response?.status === 404 || failures >= MAX_POLL_FAILURES) stopPolling(id)
      }
    }, POLL_MS)
    pollers.set(id, handle)
  }

  function stopPolling(id) {
    clearInterval(pollers.get(id))
    pollers.delete(id)
  }

  function stopAllPolling() {
    for (const id of [...pollers.keys()]) stopPolling(id)
  }

  // After a reload: load the list and re-attach to anything still in flight.
  async function hydrate() {
    if (enabled.value === null) await fetchStatus()
    if (!enabled.value) return
    await fetchList()
    for (const c of calls.value) {
      if (!CALL_TERMINAL.has(c.status)) pollCall(c.id)
    }
    if (!current.value) {
      const inflight = calls.value.find((c) => !CALL_TERMINAL.has(c.status))
      if (inflight) current.value = inflight
    }
  }

  async function openCall(id) {
    const data = await fetchCall(id)
    current.value = data
    return data
  }

  async function deleteCall(id) {
    await api.delete(`/calls/${id}`)
    stopPolling(id)
    calls.value = calls.value.filter((c) => c.id !== id)
    if (current.value?.id === id) current.value = null
  }

  function clearCurrent() { current.value = null }

  return {
    enabled, calls, current, loadingList, error,
    recState, elapsed, uploadProgress, analyser, isRecording, micLevel,
    fetchStatus, fetchList, fetchCall, startRecording, cancelRecording, stopAndUpload,
    pollCall, stopPolling, stopAllPolling, hydrate, openCall, deleteCall, clearCurrent, notice, showNotice,
  }
})
