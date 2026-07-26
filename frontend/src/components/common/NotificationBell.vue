<template>
  <v-menu v-model="open" :close-on-content-click="false" max-width="360" offset="8">
    <template #activator="{ props }">
      <v-btn v-bind="props" icon variant="text" size="small">
        <v-badge :content="unreadCount" :model-value="unreadCount > 0" color="error" max="9">
          <v-icon>{{ wsConnected ? 'mdi-bell' : 'mdi-bell-outline' }}</v-icon>
        </v-badge>
      </v-btn>
    </template>

    <v-card min-width="320">
      <v-card-title class="d-flex align-center justify-space-between pa-3">
        <span class="text-body-1 font-weight-medium">Уведомления</span>
        <v-btn
          v-if="unreadCount > 0"
          size="small"
          variant="text"
          color="primary"
          :loading="markingAll"
          @click="markAllRead"
        >
          Прочитать все
        </v-btn>
      </v-card-title>
      <v-divider />

      <div v-if="loading" class="d-flex justify-center pa-4">
        <v-progress-circular indeterminate color="primary" size="24" />
      </div>

      <v-list v-else-if="notifications.length" lines="two" density="compact" class="py-0">
        <v-list-item
          v-for="n in notifications"
          :key="n.id"
          :to="n.link || undefined"
          :class="n.is_read ? '' : 'unread-item'"
          @click="handleClick(n)"
        >
          <template #prepend>
            <v-icon :color="n.is_read ? 'grey' : 'primary'" size="18" class="mr-1">
              {{ n.is_read ? 'mdi-bell-outline' : 'mdi-bell' }}
            </v-icon>
          </template>
          <v-list-item-title class="text-body-2">{{ n.title }}</v-list-item-title>
          <v-list-item-subtitle class="text-caption">
            {{ n.body }} · {{ formatTimeAgo(n.created_at) }}
          </v-list-item-subtitle>
        </v-list-item>
      </v-list>

      <div v-else class="text-center text-medium-emphasis pa-6 text-body-2">
        Нет уведомлений
      </div>
    </v-card>
  </v-menu>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { formatDistanceToNow, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useAuthStore } from '@/stores/auth'
import api from '@/plugins/axios'

const auth = useAuthStore()
const open = ref(false)
const loading = ref(false)
const markingAll = ref(false)
const notifications = ref([])
const wsConnected = ref(false)
let ws = null
let fallbackInterval = null

const unreadCount = computed(() => notifications.value.filter(n => !n.is_read).length)

function formatTimeAgo(dateStr) {
  try {
    return formatDistanceToNow(parseISO(dateStr), { addSuffix: true, locale: ru })
  } catch {
    return ''
  }
}

async function fetchAll() {
  if (loading.value) return
  loading.value = true
  try {
    const { data } = await api.get('/api/v1/notifications/')
    notifications.value = data.results || data
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

function connectWs() {
  const token = auth.accessToken
  if (!token) return
  const proto = location.protocol === 'https:' ? 'wss' : 'ws'
  ws = new WebSocket(`${proto}://${location.host}/ws/notifications/?token=${token}`)

  ws.onopen = () => { wsConnected.value = true }
  ws.onclose = () => {
    wsConnected.value = false
    // reconnect after 5s
    setTimeout(connectWs, 5000)
  }
  ws.onerror = () => { ws.close() }
  ws.onmessage = (event) => {
    try {
      const n = JSON.parse(event.data)
      // prepend if not already in list
      if (!notifications.value.find(x => x.id === n.id)) {
        notifications.value.unshift(n)
      }
    } catch { /* ignore */ }
  }
}

async function markAllRead() {
  markingAll.value = true
  try {
    await api.post('/api/v1/notifications/mark-all-read/')
    notifications.value.forEach(n => { n.is_read = true })
  } finally {
    markingAll.value = false
  }
}

async function handleClick(n) {
  if (!n.is_read) {
    await api.patch(`/api/v1/notifications/${n.id}/read/`)
    n.is_read = true
  }
  open.value = false
}

onMounted(() => {
  fetchAll()
  connectWs()
  // fallback poll every 5 min for missed messages
  fallbackInterval = setInterval(fetchAll, 300000)
})

onUnmounted(() => {
  clearInterval(fallbackInterval)
  ws?.close()
})
</script>

<style scoped>
.unread-item {
  background: rgba(var(--v-theme-primary), 0.05);
}
</style>
