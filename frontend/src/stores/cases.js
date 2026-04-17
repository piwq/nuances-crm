import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/plugins/axios'

export const useCasesStore = defineStore('cases', () => {
  const cases = ref([])
  const currentCase = ref(null)
  const loading = ref(false)
  const pagination = ref({ total: 0 })

  const casesByStatus = computed(() => {
    return cases.value.reduce((acc, c) => {
      if (!acc[c.status]) acc[c.status] = []
      acc[c.status].push(c)
      return acc
    }, {})
  })

  async function fetchCases(params = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/cases/', { params })
      cases.value = data.results
      pagination.value.total = data.count
      return data
    } finally {
      loading.value = false
    }
  }

  async function fetchCase(id) {
    loading.value = true
    try {
      const { data } = await api.get(`/api/v1/cases/${id}/`)
      currentCase.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function createCase(payload) {
    const { data } = await api.post('/api/v1/cases/', payload)
    return data
  }

  async function updateCase(id, payload) {
    const { data } = await api.patch(`/api/v1/cases/${id}/`, payload)
    currentCase.value = data
    return data
  }

  async function changeStatus(id, status) {
    const { data } = await api.patch(`/api/v1/cases/${id}/change-status/`, { status })
    if (currentCase.value?.id === id) currentCase.value = data
    return data
  }

  async function assignLawyer(caseId, userId) {
    await api.post(`/api/v1/cases/${caseId}/assign-lawyer/`, { user_id: userId })
    await fetchCase(caseId)
  }

  async function removeLawyer(caseId, userId) {
    await api.delete(`/api/v1/cases/${caseId}/remove-lawyer/${userId}/`)
    await fetchCase(caseId)
  }

  async function fetchStats() {
    const { data } = await api.get('/api/v1/cases/stats/')
    return data
  }

  return {
    cases, currentCase, loading, pagination, casesByStatus,
    fetchCases, fetchCase, createCase, updateCase, changeStatus,
    assignLawyer, removeLawyer, fetchStats,
  }
})
