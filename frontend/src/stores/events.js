import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/plugins/axios'
import { EVENT_TYPES } from '@/utils/constants'

export const useEventsStore = defineStore('events', () => {
  const events = ref([])
  const loading = ref(false)

  const eventsForCalendar = computed(() =>
    events.value.map(e => {
      const typeInfo = EVENT_TYPES.find(t => t.value === e.event_type) || {}
      return {
        id: e.id,
        title: e.title,
        start: e.start_datetime,
        end: e.end_datetime,
        allDay: e.all_day,
        backgroundColor: getCalendarColor(e.event_type),
        borderColor: getCalendarColor(e.event_type),
        extendedProps: { ...e },
      }
    })
  )

  function getCalendarColor(type) {
    const colors = {
      court_hearing: '#D32F2F',
      meeting: '#1565C0',
      deadline: '#E65100',
      other: '#616161',
    }
    return colors[type] || '#616161'
  }

  async function fetchEvents(start, end, params = {}) {
    loading.value = true
    try {
      const { data } = await api.get('/api/v1/events/', {
        params: { start, end, ...params, page_size: 200 },
      })
      events.value = data.results
      return data.results
    } finally {
      loading.value = false
    }
  }

  async function createEvent(payload) {
    const { data } = await api.post('/api/v1/events/', payload)
    events.value.push(data)
    return data
  }

  async function updateEvent(id, payload) {
    const { data } = await api.patch(`/api/v1/events/${id}/`, payload)
    const idx = events.value.findIndex(e => e.id === id)
    if (idx !== -1) events.value[idx] = data
    return data
  }

  async function deleteEvent(id) {
    await api.delete(`/api/v1/events/${id}/`)
    events.value = events.value.filter(e => e.id !== id)
  }

  return {
    events, loading, eventsForCalendar,
    fetchEvents, createEvent, updateEvent, deleteEvent,
  }
})
