import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/plugins/axios'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const accessToken = ref(null)
  const refreshToken = ref(null)

  const isAuthenticated = computed(() => !!accessToken.value && !!user.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const isLawyer = computed(() => user.value?.role === 'lawyer')

  async function login(username, password) {
    const { data } = await api.post('/api/v1/auth/login/', { username, password })
    accessToken.value = data.access
    refreshToken.value = data.refresh
    await fetchMe()
  }

  async function fetchMe() {
    const { data } = await api.get('/api/v1/auth/me/')
    user.value = data
  }

  async function logout() {
    try {
      if (refreshToken.value) {
        await api.post('/api/v1/auth/logout/', { refresh: refreshToken.value })
      }
    } catch {}
    user.value = null
    accessToken.value = null
    refreshToken.value = null
  }

  function setTokens(access, refresh) {
    accessToken.value = access
    if (refresh) refreshToken.value = refresh
  }

  return {
    user, accessToken, refreshToken,
    isAuthenticated, isAdmin, isLawyer,
    login, fetchMe, logout, setTokens,
  }
}, {
  persist: {
    paths: ['accessToken', 'refreshToken', 'user'],
    key: 'auth',
  },
})
