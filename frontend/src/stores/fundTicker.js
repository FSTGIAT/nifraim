import { defineStore, acceptHMRUpdate } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

export const useFundTickerStore = defineStore('fundTicker', () => {
  const tracks = ref([])
  const updatedAt = ref(null)
  const loaded = ref(false)
  const detailCache = ref({})

  async function fetch() {
    try {
      const { data } = await api.get('/funds/ticker')
      tracks.value = data.tracks || []
      updatedAt.value = data.updated_at
    } finally {
      loaded.value = true
    }
  }

  async function fetchTrackDetail(trackId) {
    if (!trackId) return null
    if (detailCache.value[trackId]) return detailCache.value[trackId]
    const { data } = await api.get(`/funds/${encodeURIComponent(trackId)}`)
    detailCache.value = { ...detailCache.value, [trackId]: data }
    return data
  }

  return { tracks, updatedAt, loaded, fetch, fetchTrackDetail }
})

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useFundTickerStore, import.meta.hot))
}
