import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/plugins/axios'

export const useClientsStore = defineStore('clients', () => {
  const clients = ref([])
  const currentClient = ref(null)
  const loading = ref(false)
  const pagination = ref({ total: 0, page: 1, pageSize: 25 })

  async function fetchClients(params = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/clients/', { params })
      clients.value = data.results
      pagination.value.total = data.count
      return data
    } finally {
      loading.value = false
    }
  }

  async function fetchClient(id) {
    loading.value = true
    try {
      const { data } = await api.get(`/api/v1/clients/${id}/`)
      currentClient.value = data
      return data
    } finally {
      loading.value = false
    }
  }

  async function createClient(payload) {
    const { data } = await api.post('/api/v1/clients/', payload)
    return data
  }

  async function updateClient(id, payload) {
    const { data } = await api.patch(`/api/v1/clients/${id}/`, payload)
    currentClient.value = data
    return data
  }

  async function deleteClient(id) {
    await api.delete(`/api/v1/clients/${id}/`)
    clients.value = clients.value.filter(c => c.id !== id)
  }

  async function fetchContactPersons(clientId) {
    const { data } = await api.get(`/api/v1/clients/${clientId}/contact-persons/`)
    return data
  }

  async function createContactPerson(clientId, payload) {
    const { data } = await api.post(`/api/v1/clients/${clientId}/contact-persons/`, payload)
    return data
  }

  async function deleteContactPerson(id) {
    await api.delete(`/api/v1/contact-persons/${id}/`)
  }

  return {
    clients, currentClient, loading, pagination,
    fetchClients, fetchClient, createClient, updateClient, deleteClient,
    fetchContactPersons, createContactPerson, deleteContactPerson,
  }
})
