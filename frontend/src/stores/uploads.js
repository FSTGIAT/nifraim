import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '../api/client.js'

export const useUploadsStore = defineStore('uploads', () => {
  const uploads = ref([])
  const uploading = ref(false)

  async function fetchUploads() {
    const res = await api.get('/uploads')
    uploads.value = res.data
  }

  async function uploadFile(file, password = null) {
    uploading.value = true
    try {
      const formData = new FormData()
      formData.append('file', file)
      if (password) {
        formData.append('password', password)
      }
      const res = await api.post('/uploads', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      await fetchUploads()
      return res.data
    } finally {
      uploading.value = false
    }
  }

  async function deleteUpload(id) {
    await api.delete(`/uploads/${id}`)
    await fetchUploads()
  }

  return { uploads, uploading, fetchUploads, uploadFile, deleteUpload }
})
