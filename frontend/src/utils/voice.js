// Hebrew speech for Nifra reminders. FIRST the server's voice — Azure "Hila", a woman's voice, the same
// for every agent and browser (POST /calls-insights/speak → MP3). If the server can't (free monthly quota
// used up, offline), the browser's own voice (speechSynthesis — a woman's voice preferred) takes over.
// Browsers only play sound after the user has interacted with the page, so `speak` reports whether it
// could, and the caller falls back to a toast / Notification.
import api from '../api/client.js'

let voices = []
function loadVoices() {
  try { voices = window.speechSynthesis ? window.speechSynthesis.getVoices() : [] } catch { voices = [] }
}
if (typeof window !== 'undefined' && window.speechSynthesis) {
  loadVoices()
  window.speechSynthesis.addEventListener?.('voiceschanged', loadVoices)
}

// A WOMAN's voice first (the agent's choice, 2026-10-10): Edge's "Hila" (neural, Windows), Apple's
// "Carmit" (Mac/iPhone). Only then any natural voice, then whatever Hebrew voice exists (Windows' "Asaf" is male).
const FEMALE = [/hila/i, /carmit/i, /female|woman|אישה/i]

export function hebrewVoice() {
  if (!voices.length) loadVoices()
  const he = voices.filter((v) => /^he|^iw/i.test(v.lang))
  for (const rx of FEMALE) {
    const v = he.find((x) => rx.test(x.name))
    if (v) return v
  }
  return he.find((v) => /natural|online/i.test(v.name)) || he[0] || null
}

let current = null   // the <audio> playing now (server voice)

function browserSpeak(list) {
  const voice = hebrewVoice()
  if (!list.length || !window.speechSynthesis || !voice) return false
  try {
    window.speechSynthesis.cancel()
    for (const s of list) {
      const u = new SpeechSynthesisUtterance(s)
      u.voice = voice
      u.lang = voice.lang
      window.speechSynthesis.speak(u)
    }
    return true
  } catch {
    return false
  }
}

/** Speak sentences — Hila from the server, else the browser's voice. Resolves true when sound started. */
export async function speak(sentences) {
  const list = (Array.isArray(sentences) ? sentences : [sentences]).filter(Boolean)
  if (!list.length) return false
  stopSpeaking()
  try {
    const res = await api.post('/calls-insights/speak', { text: list.join(' ') }, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = new Audio(url)
    current = a
    a.onended = () => { URL.revokeObjectURL(url); if (current === a) current = null }
    await a.play()
    return true
  } catch {
    current = null
    return browserSpeak(list)
  }
}

export function isSpeaking() {
  return !!(current && !current.paused && !current.ended) || !!(window.speechSynthesis && window.speechSynthesis.speaking)
}

export function stopSpeaking() {
  try { if (current) { current.pause(); current = null } } catch { /* already gone */ }
  try { window.speechSynthesis && window.speechSynthesis.cancel() } catch { /* nothing to stop */ }
}

/** A desktop notification — the fallback when the tab is hidden or no Hebrew voice exists. */
export function notify(title, body) {
  try {
    if (!('Notification' in window) || Notification.permission !== 'granted') return false
    new Notification(title, { body, lang: 'he', dir: 'rtl', tag: 'nifra-reminder' })
    return true
  } catch {
    return false
  }
}

export async function askNotifyPermission() {
  try {
    if ('Notification' in window && Notification.permission === 'default') await Notification.requestPermission()
  } catch { /* the browser said no — the toast still works */ }
}
