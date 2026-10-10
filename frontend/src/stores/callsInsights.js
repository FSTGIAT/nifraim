// Nifra Insights — what the agent's calls add up to (products-first board + analyst panel) and the
// promises to remind them of (15-minute heads-up + the morning brief). Every number comes from
// /api/calls-insights (backend/app/services/calls/{insights_board,reminders}.py).
import { defineStore } from 'pinia'
import api from '../api/client.js'

const VOICE_KEY = 'nifra_insights_voice'

function readVoicePref() {
  try { return localStorage.getItem(VOICE_KEY) !== '0' } catch { return true }
}

export const useCallsInsightsStore = defineStore('callsInsights', {
  state: () => ({
    board: null,
    boardDays: 0,
    loadingBoard: false,
    reminders: null,
    voiceOn: readVoicePref(),
    // hover = highlight across the studio: the call ids under the pointer (a bar, a customer, a task)
    hoverCalls: null,
    hoverTheme: null,   // a bar under the pointer: it alone stays lit (themes share calls)
    error: '',
  }),
  getters: {
    dueBadge: (s) => {
      const b = s.reminders && s.reminders.brief
      return b ? b.due_today.length + b.overdue.length : 0
    },
  },
  actions: {
    async loadBoard(days = this.boardDays) {
      this.boardDays = days
      this.loadingBoard = !this.board
      try {
        this.board = (await api.get('/calls-insights/board', { params: { days } })).data
        this.error = ''
      } catch {
        this.error = 'לא הצלחתי לטעון את התובנות'
      } finally {
        this.loadingBoard = false
      }
      return this.board
    },
    async loadReminders() {
      try {
        this.reminders = (await api.get('/calls-insights/reminders')).data
      } catch { /* the reminders are a nicety — never break the page */ }
      return this.reminders
    },
    async claim(key) {
      try {
        return (await api.post('/calls-insights/reminders/claim', { key })).data.claimed
      } catch {
        return false
      }
    },
    async markDone(callId, index) {
      await api.post(`/calls/${callId}/tasks/${index}`, { done: true })
      await Promise.all([this.loadReminders(), this.board ? this.loadBoard() : null])
    },
    async schedule(callId, index, date, time) {
      await api.post(`/calls/${callId}/tasks/${index}/schedule`, { date, time })
      await Promise.all([this.loadReminders(), this.board ? this.loadBoard() : null])
    },
    setVoice(on) {
      this.voiceOn = on
      try { localStorage.setItem(VOICE_KEY, on ? '1' : '0') } catch { /* private window */ }
    },
    hover(callIds, theme = null) {
      this.hoverCalls = callIds && callIds.length ? new Set(callIds) : null
      this.hoverTheme = this.hoverCalls ? theme : null
    },
  },
})
