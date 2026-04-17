import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '',
  headers: { 'Content-Type': 'application/json' },
})

let isRefreshing = false
let failedQueue = []

function processQueue(error, token = null) {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) reject(error)
    else resolve(token)
  })
  failedQueue = []
}

api.interceptors.request.use((config) => {
  // Auth store can't be imported at module init time — read from localStorage directly
  const authData = JSON.parse(localStorage.getItem('auth') || '{}')
  const token = authData?.accessToken
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject })
      }).then((token) => {
        originalRequest.headers.Authorization = `Bearer ${token}`
        return api(originalRequest)
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    const authData = JSON.parse(localStorage.getItem('auth') || '{}')
    const refreshToken = authData?.refreshToken

    if (!refreshToken) {
      isRefreshing = false
      window.dispatchEvent(new CustomEvent('auth:logout'))
      return Promise.reject(error)
    }

    try {
      const { data } = await axios.post(
        `${import.meta.env.VITE_API_BASE_URL || ''}/api/v1/auth/refresh/`,
        { refresh: refreshToken }
      )
      const newAccess = data.access

      const stored = JSON.parse(localStorage.getItem('auth') || '{}')
      stored.accessToken = newAccess
      localStorage.setItem('auth', JSON.stringify(stored))

      api.defaults.headers.common.Authorization = `Bearer ${newAccess}`
      originalRequest.headers.Authorization = `Bearer ${newAccess}`

      processQueue(null, newAccess)
      return api(originalRequest)
    } catch (refreshError) {
      processQueue(refreshError, null)
      window.dispatchEvent(new CustomEvent('auth:logout'))
      return Promise.reject(refreshError)
    } finally {
      isRefreshing = false
    }
  }
)

export default api
