import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/plugins/axios'

export const useBillingStore = defineStore('billing', () => {
  const timeEntries = ref([])
  const invoices = ref([])
  const currentInvoice = ref(null)
  const loading = ref(false)
  const pagination = ref({ total: 0 })

  async function fetchTimeEntries(params = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/billing/time-entries/', { params })
      timeEntries.value = data.results
      pagination.value.total = data.count
      return data
    } finally {
      loading.value = false
    }
  }

  async function createTimeEntry(payload) {
    const { data } = await api.post('/api/v1/billing/time-entries/', payload)
    timeEntries.value.unshift(data)
    return data
  }

  async function updateTimeEntry(id, payload) {
    const { data } = await api.patch(`/api/v1/billing/time-entries/${id}/`, payload)
    const idx = timeEntries.value.findIndex(e => e.id === id)
    if (idx !== -1) timeEntries.value[idx] = data
    return data
  }

  async function deleteTimeEntry(id) {
    await api.delete(`/api/v1/billing/time-entries/${id}/`)
    timeEntries.value = timeEntries.value.filter(e => e.id !== id)
  }

  async function fetchInvoices(params = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/billing/invoices/', { params })
      invoices.value = data.results
      pagination.value.total = data.count
      return data
    } finally {
      loading.value = false
    }
  }

  async function fetchInvoice(id) {
    const { data } = await api.get(`/api/v1/billing/invoices/${id}/`)
    currentInvoice.value = data
    return data
  }

  async function createInvoice(payload) {
    const { data } = await api.post('/api/v1/billing/invoices/', payload)
    invoices.value.unshift(data)
    return data
  }

  async function generateFromEntries(invoiceId) {
    const { data } = await api.post(`/api/v1/billing/invoices/${invoiceId}/generate-from-entries/`)
    currentInvoice.value = data
    return data
  }

  async function markSent(id) {
    const { data } = await api.patch(`/api/v1/billing/invoices/${id}/mark-sent/`)
    currentInvoice.value = data
    return data
  }

  async function markPaid(id, paidDate) {
    const { data } = await api.patch(`/api/v1/billing/invoices/${id}/mark-paid/`, { paid_date: paidDate })
    currentInvoice.value = data
    return data
  }

  async function downloadPDF(id, invoiceNumber) {
    const response = await api.get(`/api/v1/billing/invoices/${id}/pdf/`, {
      responseType: 'blob',
    })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `invoice_${invoiceNumber}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    timeEntries, invoices, currentInvoice, loading, pagination,
    fetchTimeEntries, createTimeEntry, updateTimeEntry, deleteTimeEntry,
    fetchInvoices, fetchInvoice, createInvoice, generateFromEntries,
    markSent, markPaid, downloadPDF,
  }
})
