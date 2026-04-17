import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/plugins/axios'
import { parseISO, isToday, isBefore, startOfToday } from 'date-fns'

export const useTasksStore = defineStore('tasks', () => {
  const tasks = ref([])
  const loading = ref(false)
  const pagination = ref({ total: 0 })

  const overdueTasks = computed(() =>
    tasks.value.filter(t =>
      t.due_date &&
      t.status !== 'done' &&
      t.status !== 'cancelled' &&
      isBefore(parseISO(t.due_date), startOfToday())
    )
  )

  const todayTasks = computed(() =>
    tasks.value.filter(t => t.due_date && isToday(parseISO(t.due_date)))
  )

  async function fetchTasks(params = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/tasks/', { params })
      tasks.value = data.results
      pagination.value.total = data.count
      return data
    } finally {
      loading.value = false
    }
  }

  async function createTask(payload) {
    const { data } = await api.post('/api/v1/tasks/', payload)
    tasks.value.unshift(data)
    return data
  }

  async function updateTask(id, payload) {
    const { data } = await api.patch(`/api/v1/tasks/${id}/`, payload)
    const idx = tasks.value.findIndex(t => t.id === id)
    if (idx !== -1) tasks.value[idx] = data
    return data
  }

  async function completeTask(id) {
    const { data } = await api.patch(`/api/v1/tasks/${id}/complete/`)
    const idx = tasks.value.findIndex(t => t.id === id)
    if (idx !== -1) tasks.value[idx] = data
    return data
  }

  async function deleteTask(id) {
    await api.delete(`/api/v1/tasks/${id}/`)
    tasks.value = tasks.value.filter(t => t.id !== id)
  }

  return {
    tasks, loading, pagination, overdueTasks, todayTasks,
    fetchTasks, createTask, updateTask, completeTask, deleteTask,
  }
})
