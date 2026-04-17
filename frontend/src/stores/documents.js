import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/plugins/axios'

export const useDocumentsStore = defineStore('documents', () => {
  const documents = ref([])
  const loading = ref(false)
  const uploadProgress = ref(0)

  async function fetchDocuments(caseId) {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/documents/', { params: { case: caseId } })
      documents.value = data.results
      return data.results
    } finally {
      loading.value = false
    }
  }

  async function uploadDocument(caseId, formData, onProgress) {
    const { data } = await api.post('/api/v1/documents/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        uploadProgress.value = Math.round((e.loaded * 100) / e.total)
        if (onProgress) onProgress(uploadProgress.value)
      },
    })
    documents.value.unshift(data)
    uploadProgress.value = 0
    return data
  }

  async function deleteDocument(id) {
    await api.delete(`/api/v1/documents/${id}/`)
    documents.value = documents.value.filter(d => d.id !== id)
  }

  async function downloadDocument(id, filename) {
    const response = await api.get(`/api/v1/documents/${id}/download/`, {
      responseType: 'blob',
    })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename || 'document'
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    documents, loading, uploadProgress,
    fetchDocuments, uploadDocument, deleteDocument, downloadDocument,
  }
})
