// Nifra AI v2 — the ONE client for POST /api/ai/agent (backend/app/services/agent/loop.py).
// Server-sent events, one JSON object per `data:` line:
//   {status}  a tool is running ("בודק עמלות שלא שולמו") — show it as a chip
//   {text}    answer text, streamed
//   {viz}     a chart payload for the native registry (components/ai-charts)
//   {proposal} an action awaiting the agent's click → POST /office-agent/act
//   {done, lane, ms}
export async function streamAgent({ question, history = [], mentions = [], viewContext = null, surface = 'chat' }, onEvent, { signal } = {}) {
  const token = localStorage.getItem('token')
  const body = { question, history, mentions, surface }
  if (viewContext) body.view_context = String(viewContext).slice(0, 6000)
  const res = await fetch('/api/ai/agent', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify(body),
    signal,
  })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    return
  }
  if (!res.ok) throw new Error(res.status === 403 ? 'נדרש מנוי פעיל' : 'שגיאה בשרת')
  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() || ''
    for (const line of lines) {
      if (!line.startsWith('data: ')) continue
      let ev
      try { ev = JSON.parse(line.slice(6)) } catch { continue }
      onEvent(ev)
      if (ev.done) return ev
    }
  }
}

/** Plain text for surfaces that don't render Markdown (the Nifra Agent panel). */
export function stripMarkdown(t) {
  return String(t || '')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/(^|\s)\*([^*\n]+)\*(?=\s|$)/g, '$1$2')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^\s*[*•]\s+/gm, '- ')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
}
