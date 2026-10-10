// Nifra Market — the fund rankings studio (components/market/*). Every number comes from /api/market/*,
// which wraps the SAME tools Nifra's answers use (backend/app/services/agent/tools_market.py).
import { defineStore } from 'pinia'
import api from '../api/client.js'
import { streamAgent, stripMarkdown } from '../utils/agentStream.js'

export const MARKET_CATEGORIES = [
  { id: 'pension', label: 'פנסיה' },
  { id: 'gemel', label: 'גמל' },
  { id: 'hishtalmut', label: 'השתלמות' },
  { id: 'gemel_invest', label: 'גמל להשקעה' },
]
export const RISK_LEVELS = [
  { level: 1, label: 'נמוך' }, { level: 2, label: 'מתון' }, { level: 3, label: 'בינוני' },
  { level: 4, label: 'מוגבר' }, { level: 5, label: 'גבוה' },
]
export const MARKET_COMPANIES = ['כלל', 'הראל', 'מגדל', 'הפניקס', 'מנורה', 'מור', 'מיטב', 'אלטשולר', 'ילין', 'אינפיניטי', 'אנליסט', 'איילון']

export const useMarketStore = defineStore('market', {
  state: () => ({
    overview: null,
    loadingOverview: false,
    customers: {},   // id_number -> fund fit with ladders
    ladders: {},     // `${cat}:${level}` -> best_tracks_by_risk
    moves: {},       // cat -> market changes
    duels: {},       // `${cat}:${a}:${b}` -> compare_companies
    thread: [],      // the ask box: [{role, text, vizs}]
    busy: false,
    askStatus: '',
    error: '',
  }),
  actions: {
    async loadOverview(force = false) {
      if (this.overview && !force) return this.overview
      this.loadingOverview = true
      try {
        this.overview = (await api.get('/market/overview')).data
      } catch (e) {
        this.error = 'לא הצלחתי לטעון את נתוני השוק'
      } finally {
        this.loadingOverview = false
      }
      return this.overview
    },
    async loadCustomer(id) {
      if (!this.customers[id]) this.customers[id] = (await api.get(`/market/customer/${id}`)).data
      return this.customers[id]
    },
    async loadLadder(category, level) {
      const k = `${category}:${level}`
      if (!this.ladders[k]) this.ladders[k] = (await api.get('/market/ladder', { params: { category, level } })).data
      return this.ladders[k]
    },
    async loadMoves(category) {
      if (!this.moves[category]) this.moves[category] = (await api.get('/market/moves', { params: { category } })).data
      return this.moves[category]
    },
    async loadDuel(category, a, b) {
      const k = `${category}:${a}:${b}`
      if (!this.duels[k]) this.duels[k] = (await api.get('/market/duel', { params: { category, a, b } })).data
      return this.duels[k]
    },
    async ask(text) {
      const q = (text || '').trim()
      if (!q || this.busy) return
      const history = this.thread.slice(-6).map((m) => ({ role: m.role === 'agent' ? 'agent' : 'user', text: m.text }))
      this.thread.push({ role: 'user', text: q })
      const msg = { role: 'agent', text: '', vizs: [] }
      this.thread.push(msg)
      const live = this.thread[this.thread.length - 1]
      this.busy = true
      this.askStatus = ''
      try {
        await streamAgent({ question: q, history, surface: 'market' }, (ev) => {
          if (ev.status) this.askStatus = ev.status
          if (ev.text) live.text += ev.text
          if (ev.viz) live.vizs.push(ev.viz)
        })
        live.text = stripMarkdown(live.text)
      } catch (e) {
        live.text = e.message || 'לא הצלחתי לענות כרגע — נסו שוב בעוד רגע.'
      } finally {
        this.busy = false
        this.askStatus = ''
      }
    },
  },
})
