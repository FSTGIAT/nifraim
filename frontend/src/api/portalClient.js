import axios from 'axios'

const portalApi = axios.create({
  baseURL: '/api/portal',
})

portalApi.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('portal_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

portalApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem('portal_token')
    }
    return Promise.reject(error)
  }
)

export default portalApi
