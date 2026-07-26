<template>
  <v-container fluid class="fill-height pa-0">
    <v-row no-gutters class="fill-height">
      <!-- Список диалогов -->
      <v-col cols="12" md="3" class="border-e h-100 bg-surface d-flex flex-column">
        <v-toolbar flat density="comfortable" color="transparent">
          <v-toolbar-title class="text-h6 font-weight-bold">Сообщения</v-toolbar-title>
        </v-toolbar>
        <v-divider />
        
        <v-list class="pa-0 overflow-y-auto flex-grow-1">
          <v-list-item
            v-for="lawyer in lawyers"
            :key="lawyer.id"
            :active="activeLawyer?.id === lawyer.id"
            :title="lawyer.full_name || lawyer.username"
            :subtitle="lawyer.role === 'admin' ? 'Администратор' : 'Юрист'"
            class="px-4 py-3"
            @click="selectLawyer(lawyer)"
          >
            <template #prepend>
              <v-avatar color="primary" size="48">
                <v-img v-if="lawyer.avatar" :src="lawyer.avatar" />
                <span v-else class="text-white text-h6">{{ (lawyer.full_name || lawyer.username)[0].toUpperCase() }}</span>
              </v-avatar>
            </template>
            <template #append v-if="lawyer.unread_count > 0">
              <v-badge
                color="error"
                :content="lawyer.unread_count"
                inline
              />
            </template>
          </v-list-item>
          
          <div v-if="!lawyers.length && !loading" class="pa-4 text-center text-medium-emphasis text-caption">
            Нет доступных юристов
          </div>
        </v-list>
      </v-col>

      <!-- Окно чата -->
      <v-col cols="12" md="9" class="h-100 d-flex flex-column bg-background">
        <template v-if="activeLawyer">
          <v-toolbar flat color="surface" class="border-b px-4">
            <v-avatar color="primary" size="36" class="mr-3">
              <v-img v-if="activeLawyer.avatar" :src="activeLawyer.avatar" />
              <span v-else class="text-white text-caption">{{ (activeLawyer.full_name || activeLawyer.username)[0].toUpperCase() }}</span>
            </v-avatar>
            <v-toolbar-title class="text-subtitle-1 font-weight-bold">
              {{ activeLawyer.full_name || activeLawyer.username }}
            </v-toolbar-title>
            <v-spacer />
            <v-chip
              :color="connected ? 'success' : 'error'"
              size="small"
              variant="flat"
            >
              {{ connected ? 'В сети' : 'Отключен' }}
            </v-chip>
          </v-toolbar>

          <v-card-text id="chat-container" class="flex-grow-1 overflow-y-auto pa-4 glass-panel">
            <div v-if="loading" class="d-flex justify-center align-center h-100">
              <v-progress-circular indeterminate color="primary" />
            </div>
            <div v-else class="messages-list">
              <div v-if="historyHasMore" class="d-flex justify-center mb-4">
                <v-btn size="small" variant="tonal" :loading="loadingOlder" @click="loadOlder">
                  Показать более ранние
                </v-btn>
              </div>
              <div
                v-for="msg in messages"
                :key="msg.id || msg.created_at" 
                :class="['d-flex mb-4', msg.user?.id === auth.user?.id ? 'justify-end' : 'justify-start']"
              >
                <div :class="['message-box', msg.user?.id === auth.user?.id ? 'sent' : 'received']">
                  <v-card 
                    :color="msg.user?.id === auth.user?.id ? 'primary' : 'surface'"
                    class="pa-3 rounded-lg elevation-1"
                  >
                    <div class="text-body-2">{{ msg.text }}</div>
                  </v-card>
                  <div class="text-caption text-medium-emphasis mt-1 mx-1">
                    {{ formatTime(msg.created_at) }}
                  </div>
                </div>
              </div>
            </div>
          </v-card-text>

          <v-divider />

          <div class="pa-4 bg-surface">
            <v-form @submit.prevent="sendMessage">
              <v-text-field
                v-model="newMessage"
                placeholder="Введите сообщение..."
                hide-details
                variant="solo-filled"
                flat
                rounded="xl"
              >
                <template #append-inner>
                  <v-btn
                    type="submit"
                    icon="mdi-send"
                    color="primary"
                    variant="elevated"
                    size="small"
                    :disabled="!newMessage.trim() || !connected"
                    class="ml-2"
                  />
                </template>
              </v-text-field>
            </v-form>
          </div>
        </template>

        <div v-else class="fill-height d-flex flex-column justify-center align-center text-medium-emphasis">
          <v-icon size="64" class="mb-4 opacity-20">mdi-message-text-outline</v-icon>
          <div class="text-h6 opacity-50">Выберите собеседника для начала чата</div>
        </div>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useNotification } from '@/composables/useNotification'
import api from '@/plugins/axios'

const auth = useAuthStore()
const { notify: showNotification } = useNotification()

const lawyers = ref([])
const activeLawyer = ref(null)
const messages = ref([])
const newMessage = ref('')
const loading = ref(false)
const connected = ref(false)
const historyHasMore = ref(false)
const loadingOlder = ref(false)
let historyPage = 1
let socket = null
let reconnectTimer = null
let reconnectAttempts = 0

onMounted(async () => {
  await fetchLawyers()
})

onUnmounted(() => {
  closeSocket()
})

async function fetchLawyers() {
  try {
    const response = await api.get('/api/v1/chat/lawyers/')
    lawyers.value = response.data
  } catch (error) {
    showNotification('Ошибка при загрузке списка юристов', 'error')
  }
}

async function selectLawyer(lawyer) {
  activeLawyer.value = lawyer
  loading.value = true
  messages.value = []
  
  // Mark as read in backend
  if (lawyer.unread_count > 0) {
    try {
      await api.post('/api/v1/chat/mark-read/', { sender_id: lawyer.id })
      lawyer.unread_count = 0
    } catch (e) {
      console.error('Error marking as read:', e)
    }
  }
  
  closeSocket()
  await fetchHistory()
  connectWebSocket()
}

async function fetchHistory() {
  if (!activeLawyer.value) return
  try {
    historyPage = 1
    const { data } = await api.get('/api/v1/chat/history/', {
      params: { recipient_id: activeLawyer.value.id, page: 1 }
    })
    // API отдаёт новые первыми — на экране разворачиваем в хронологию
    messages.value = (data.results || data).slice().reverse()
    historyHasMore.value = !!data.next
    loading.value = false
    scrollToBottom()
  } catch (error) {
    showNotification('Ошибка загрузки истории', 'error')
    loading.value = false
  }
}

async function loadOlder() {
  if (!activeLawyer.value || loadingOlder.value) return
  loadingOlder.value = true
  const container = document.getElementById('chat-container')
  const prevHeight = container ? container.scrollHeight : 0
  try {
    const { data } = await api.get('/api/v1/chat/history/', {
      params: { recipient_id: activeLawyer.value.id, page: historyPage + 1 }
    })
    historyPage += 1
    messages.value = [...(data.results || []).slice().reverse(), ...messages.value]
    historyHasMore.value = !!data.next
    // сохранить позицию: контент вырос сверху, держим взгляд на том же сообщении
    await nextTick()
    if (container) container.scrollTop += container.scrollHeight - prevHeight
  } catch {
    showNotification('Не удалось загрузить более ранние сообщения', 'error')
  } finally {
    loadingOlder.value = false
  }
}

function closeSocket() {
  clearTimeout(reconnectTimer)
  reconnectTimer = null
  reconnectAttempts = 0
  if (socket) {
    socket.onclose = null
    socket.close()
    socket = null
    connected.value = false
  }
}

function connectWebSocket() {
  if (!activeLawyer.value) return

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const host = window.location.host
  
  // Use session storage or auth store instead of direct localStorage if using Pinia
  const token = auth.accessToken
  
  if (!token) return

  const wsUrl = `${protocol}//${host}/ws/chat/${activeLawyer.value.id}/?token=${token}`

  socket = new WebSocket(wsUrl)

  socket.onopen = () => {
    connected.value = true
    reconnectAttempts = 0
  }

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.type === 'chat_message') {
        const msg = data.message
        
        // If message is from current conversation
        if (activeLawyer.value && (msg.user.id === activeLawyer.value.id || msg.user.id === auth.user?.id)) {
          messages.value.push(msg)
          scrollToBottom()
          
          // Notify backend it's read if we are the recipient
          if (msg.user.id !== auth.user?.id) {
            api.post('/api/v1/chat/mark-read/', { sender_id: msg.user.id }).catch(console.error)
          }
        } else {
          // Increment unread count in lawyer list
          const lawyer = lawyers.value.find(l => l.id === msg.user.id)
          if (lawyer) {
            lawyer.unread_count++
          }
        }
      }
    } catch (e) {
      console.error('Error parsing WS message:', e)
    }
  }

  socket.onclose = () => {
    if (socket) {
      connected.value = false
      // экспоненциальный backoff: 1с → 2с → 4с … максимум 30с,
      // чтобы лежащий бэкенд не получал шторм переподключений
      const delay = Math.min(30000, 1000 * 2 ** reconnectAttempts)
      reconnectAttempts += 1
      reconnectTimer = setTimeout(connectWebSocket, delay)
    }
  }

  socket.onerror = (error) => {
    console.error('WebSocket error:', error)
  }
}

function sendMessage() {
  if (!newMessage.value.trim() || !connected.value) return

  socket.send(JSON.stringify({
    message: newMessage.value
  }))
  newMessage.value = ''
}

function formatTime(timestamp) {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function scrollToBottom() {
  nextTick(() => {
    const container = document.getElementById('chat-container')
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  })
}
</script>

<style scoped>
.message-box {
  max-width: 80%;
}
.message-box.sent {
  text-align: right;
  margin-left: auto;
}
.message-box.received {
  text-align: left;
  margin-right: auto;
}
.glass-panel {
  background: rgba(var(--v-theme-surface), 0.05);
}
.messages-list {
  display: flex;
  flex-direction: column;
}
</style>
