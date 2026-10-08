// Nifra Agent ↔ הר הביטוח. After the agent approves a fetch (/office-agent/act kind=harb) the
// local worker logs in, the SMS code arrives by itself, and the portfolio is ingested. The chat
// follows GET /api/policies/harb-requests/{id} and reports each stage, then the result.
import api from '../api/client'

const FINAL = new Set(['done', 'failed', 'not_found'])

/** Poll until the request is final. `onTick(status)` gets every change. Resolves the final status. */
export async function followHarb(requestId, onTick, { everyMs = 3000, maxMs = 45 * 60 * 1000 } = {}) {
  const until = Date.now() + maxMs
  let last = ''
  while (Date.now() < until) {
    try {
      const { data } = await api.get(`/policies/harb-requests/${requestId}`)
      if (data.status !== last) { last = data.status; onTick?.(data) }
      if (FINAL.has(data.status)) return data
    } catch (e) {
      if (e?.response?.status === 404) return { status: 'failed', error: 'הבקשה לא נמצאה' }
    }
    await new Promise((r) => setTimeout(r, everyMs))
  }
  return { status: 'failed', error: 'השליפה לא הסתיימה בזמן — נסו שוב מאוחר יותר' }
}
